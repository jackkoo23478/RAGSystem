import pytest

from app.features.documents.repository import create_chunks, create_document, update_document_status
from app.features.rag.llm import FakeLLM, LLMError
from app.features.rag.models import Query, QueryCitation
from app.features.rag.prompt import NO_ANSWER_TEXT
from app.features.rag.service import answer_question


def fake_embed(texts):
    return [[1.0, 0.0] for _ in texts]


def add_doc(db, user, name, chunks, status="processed", page_numbers=None):
    doc = create_document(db, original_name=name, filename=f"stored-{name}", file_type="pdf", uploaded_by=user.id)
    create_chunks(db, doc.id, [t for t, _ in chunks], [v for _, v in chunks], page_numbers)
    update_document_status(db, doc, status)
    return doc


@pytest.fixture
def policy(db, user):
    return add_doc(
        db, user, "policy.pdf",
        [("Employees get 14 days of annual leave.", [1.0, 0.0]),
         ("Expense claims need a receipt.", [1.0, 0.1])],
        page_numbers=[3, 4],
    )


def ask(db, user, llm, question="How many leave days?", **kwargs):
    return answer_question(db, user.id, question, llm, embed=fake_embed, **kwargs)


def test_answered_with_citations(db, user, policy):
    llm = FakeLLM(answer="You get 14 days. [1]")

    result = ask(db, user, llm)

    assert result.status == "answered"
    assert result.answer == "You get 14 days. [1]"
    assert len(result.citations) == 1
    c = result.citations[0]
    assert c.number == 1
    assert c.document_name == "policy.pdf"
    assert c.page_number == 3
    assert "14 days" in c.snippet
    saved = db.query(Query).one()
    assert saved.id == result.query_id
    assert saved.user_id == user.id
    assert saved.status == "answered"
    assert db.query(QueryCitation).filter_by(query_id=saved.id).count() == 1


def test_only_the_cited_chunks_are_stored(db, user, policy):
    ask(db, user, FakeLLM(answer="Receipts are needed. [2]"))

    rows = db.query(QueryCitation).all()
    assert [r.snippet for r in rows] == ["Expense claims need a receipt."]
    assert rows[0].page_number == 4


def test_no_relevant_chunk_refuses_without_calling_the_llm(db, user, policy):
    llm = FakeLLM()

    result = ask(db, user, llm, min_score=1.5)  # nothing can reach this score

    assert result.status == "no_evidence"
    assert result.answer is None and result.citations == []
    assert llm.calls == []  # the model was never asked
    assert db.query(Query).one().status == "no_evidence"


def test_empty_database_is_no_evidence(db, user):
    llm = FakeLLM()

    assert ask(db, user, llm).status == "no_evidence"
    assert llm.calls == []


def test_model_refusal_is_no_evidence(db, user, policy):
    result = ask(db, user, FakeLLM(answer=NO_ANSWER_TEXT))

    assert result.status == "no_evidence"
    assert result.answer is None and result.citations == []
    assert db.query(QueryCitation).count() == 0


def test_answer_without_citation_is_invalid_and_hidden(db, user, policy):
    result = ask(db, user, FakeLLM(answer="PWNED"))

    assert result.status == "invalid_answer"
    assert result.answer is None and result.citations == []
    saved = db.query(Query).one()
    assert saved.status == "invalid_answer"
    assert saved.answer == "PWNED"  # kept in the DB for debugging


def test_citation_number_out_of_range_is_invalid(db, user, policy):
    assert ask(db, user, FakeLLM(answer="14 days [9]")).status == "invalid_answer"


def test_llm_error_is_recorded_as_failed_and_reraised(db, user, policy):
    with pytest.raises(LLMError, match="down"):
        ask(db, user, FakeLLM(error=LLMError("down")))

    saved = db.query(Query).one()
    assert saved.status == "failed"
    assert saved.answer is None


@pytest.mark.parametrize("question", ["", "   ", "\n"])
def test_empty_question_is_rejected_and_not_stored(db, user, policy, question):
    llm = FakeLLM()

    with pytest.raises(ValueError):
        ask(db, user, llm, question=question)

    assert db.query(Query).count() == 0
    assert llm.calls == []


def test_prompt_sent_to_the_model_contains_question_and_sources(db, user, policy):
    llm = FakeLLM(answer="x [1]")

    ask(db, user, llm, question="How many leave days?")

    user_message = llm.calls[0][1]["content"]
    assert "How many leave days?" in user_message
    assert "Employees get 14 days of annual leave." in user_message
    assert 'name="policy.pdf"' in user_message


def test_unprocessed_documents_are_not_used(db, user):
    add_doc(db, user, "draft.pdf", [("secret draft", [1.0, 0.0])], status="pending")
    llm = FakeLLM()

    result = ask(db, user, llm)

    assert result.status == "no_evidence"
    assert llm.calls == []


def test_question_is_trimmed_before_it_is_stored(db, user, policy):
    ask(db, user, FakeLLM(answer="x [1]"), question="  How many leave days?  ")

    assert db.query(Query).one().question == "How many leave days?"


def test_top_k_limits_how_many_sources_reach_the_model(db, user, policy):
    llm = FakeLLM(answer="x [1]")

    ask(db, user, llm, top_k=1)

    assert llm.calls[0][1]["content"].count("<source ") == 1


# ---------- latency ----------

def test_latency_is_the_time_between_receiving_the_question_and_saving_the_query(db, user, policy, monkeypatch):
    clock = iter([100.0, 100.25])  # first call: question received, second call: query saved
    monkeypatch.setattr("app.features.rag.service.time.perf_counter", lambda: next(clock))

    result = ask(db, user, FakeLLM(answer="You get 14 days. [1]"))

    assert db.get(Query, result.query_id).latency_ms == 250


@pytest.mark.parametrize(
    "answer, expected_status",
    [
        ("You get 14 days. [1]", "answered"),
        (NO_ANSWER_TEXT, "no_evidence"),
        ("PWNED", "invalid_answer"),
    ],
)
def test_latency_is_recorded_for_every_outcome(db, user, policy, answer, expected_status):
    result = ask(db, user, FakeLLM(answer=answer))

    saved = db.get(Query, result.query_id)
    assert saved.status == expected_status
    assert isinstance(saved.latency_ms, int) and saved.latency_ms >= 0


def test_latency_is_recorded_when_nothing_relevant_is_found(db, user):
    result = ask(db, user, FakeLLM())

    assert db.get(Query, result.query_id).latency_ms >= 0


def test_latency_is_recorded_when_the_model_fails(db, user, policy):
    with pytest.raises(LLMError):
        ask(db, user, FakeLLM(error=LLMError("down")))

    saved = db.query(Query).one()
    assert saved.status == "failed"
    assert saved.latency_ms >= 0
