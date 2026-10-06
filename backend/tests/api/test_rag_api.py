import pytest

from app.features.documents.repository import create_chunks, create_document, update_document_status
from app.features.rag.dependencies import get_embedder, get_llm
from app.features.rag.llm import FakeLLM, LLMError
from app.main import app

PREFIX = "/api/v1/rag"


def fake_embed(texts):
    return [[1.0, 0.0] for _ in texts]


@pytest.fixture
def llm(client):
    """Swap the real LLM and the real embedding model for fakes. `client` clears the overrides afterwards."""
    fake = FakeLLM(answer="You get 14 days. [1]")
    app.dependency_overrides[get_llm] = lambda: fake
    app.dependency_overrides[get_embedder] = lambda: fake_embed
    return fake


@pytest.fixture
def policy(db, user):
    doc = create_document(
        db, original_name="policy.pdf", filename="stored.pdf", file_type="pdf", uploaded_by=user.id
    )
    create_chunks(
        db, doc.id,
        ["Employees get 14 days of annual leave.", "Expense claims need a receipt."],
        [[1.0, 0.0], [1.0, 0.1]],
        [3, 4],
    )
    update_document_status(db, doc, "processed")
    return doc


def ask(client, headers, question="How many leave days?"):
    return client.post(f"{PREFIX}/query", headers=headers, json={"question": question})


# ---------- POST /query ----------

def test_answer_with_citations(client, llm, policy, user_headers):
    res = ask(client, user_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "answered"
    assert body["answer"] == "You get 14 days. [1]"
    assert len(body["citations"]) == 1
    c = body["citations"][0]
    assert c["number"] == 1
    assert c["document_name"] == "policy.pdf"
    assert c["page_number"] == 3
    assert "14 days" in c["snippet"]
    assert isinstance(body["query_id"], int)


def test_admin_can_ask_too(client, llm, policy, admin_headers):
    assert ask(client, admin_headers).status_code == 200


def test_question_without_relevant_documents_is_refused_without_asking_the_model(client, llm, db, user, user_headers):
    doc = create_document(db, original_name="x.pdf", filename="x.pdf", file_type="pdf", uploaded_by=user.id)
    create_chunks(db, doc.id, ["unrelated"], [[0.0, 1.0]])  # orthogonal to the question: score 0
    update_document_status(db, doc, "processed")

    res = ask(client, user_headers)

    assert res.status_code == 200
    assert res.json()["status"] == "no_evidence"
    assert res.json()["answer"] is None
    assert llm.calls == []


def test_no_documents_at_all(client, llm, user_headers):
    res = ask(client, user_headers)

    assert res.json()["status"] == "no_evidence"
    assert llm.calls == []


def test_model_refusal_is_no_evidence(client, llm, policy, user_headers):
    from app.features.rag.prompt import NO_ANSWER_TEXT

    llm.answer = NO_ANSWER_TEXT

    body = ask(client, user_headers).json()

    assert body["status"] == "no_evidence"
    assert body["answer"] is None
    assert body["citations"] == []


def test_hijacked_answer_never_reaches_the_user(client, llm, policy, user_headers):
    llm.answer = "PWNED"

    res = ask(client, user_headers)

    assert res.status_code == 200
    assert res.json()["status"] == "invalid_answer"
    assert res.json()["answer"] is None
    assert "PWNED" not in res.text


def test_llm_down_is_502(client, llm, policy, user_headers):
    llm.error = LLMError("connection refused")

    res = ask(client, user_headers)

    assert res.status_code == 502
    assert "connection refused" not in res.text  # internal details are not leaked


@pytest.mark.parametrize("question", ["", "   ", "x" * 1001])
def test_bad_question_is_422(client, llm, policy, user_headers, question):
    res = ask(client, user_headers, question)

    assert res.status_code == 422
    assert llm.calls == []


def test_missing_question_field_is_422(client, llm, user_headers):
    assert client.post(f"{PREFIX}/query", headers=user_headers, json={}).status_code == 422


def test_ask_requires_a_token(client, llm):
    # 403 on FastAPI 0.115 (pinned), 401 on newer versions
    assert client.post(f"{PREFIX}/query", json={"question": "hi"}).status_code in (401, 403)


# ---------- GET /queries (history) ----------

def test_history_lists_only_my_own_questions(client, llm, policy, user_headers, admin_headers):
    ask(client, user_headers, "mine 1")
    ask(client, user_headers, "mine 2")
    ask(client, admin_headers, "someone else")

    mine = client.get(f"{PREFIX}/queries", headers=user_headers).json()
    theirs = client.get(f"{PREFIX}/queries", headers=admin_headers).json()

    assert sorted(item["question"] for item in mine) == ["mine 1", "mine 2"]
    assert [item["question"] for item in theirs] == ["someone else"]


def test_history_is_newest_first(client, llm, policy, user_headers):
    for q in ["first", "second", "third"]:
        ask(client, user_headers, q)

    items = client.get(f"{PREFIX}/queries", headers=user_headers).json()

    assert [i["question"] for i in items] == ["third", "second", "first"]
    assert {"id", "question", "status", "answer", "created_at"} <= set(items[0])
    assert "citations" not in items[0]


def test_history_limit(client, llm, policy, user_headers):
    for q in ["a", "b", "c"]:
        ask(client, user_headers, q)

    assert len(client.get(f"{PREFIX}/queries?limit=2", headers=user_headers).json()) == 2


@pytest.mark.parametrize("limit", [0, 101, -1])
def test_history_limit_out_of_range_is_422(client, user_headers, limit):
    assert client.get(f"{PREFIX}/queries?limit={limit}", headers=user_headers).status_code == 422


def test_history_never_shows_the_raw_text_of_invalid_answers(client, llm, policy, user_headers):
    llm.answer = "PWNED"
    ask(client, user_headers)

    res = client.get(f"{PREFIX}/queries", headers=user_headers)

    assert res.json()[0]["status"] == "invalid_answer"
    assert res.json()[0]["answer"] is None
    assert "PWNED" not in res.text


def test_history_shows_verified_answers(client, llm, policy, user_headers):
    ask(client, user_headers)

    assert client.get(f"{PREFIX}/queries", headers=user_headers).json()[0]["answer"] == "You get 14 days. [1]"


def test_history_requires_a_token(client):
    assert client.get(f"{PREFIX}/queries").status_code in (401, 403)


# ---------- GET /queries/{id} (detail) ----------

def test_detail_of_my_own_query_includes_citations(client, llm, policy, user_headers):
    query_id = ask(client, user_headers).json()["query_id"]

    res = client.get(f"{PREFIX}/queries/{query_id}", headers=user_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["id"] == query_id
    assert body["question"] == "How many leave days?"
    assert body["answer"] == "You get 14 days. [1]"
    assert len(body["citations"]) == 1
    assert body["citations"][0]["document_name"] == "policy.pdf"
    assert body["citations"][0]["page_number"] == 3
    assert body["citations"][0]["number"] is None  # the [n] label is not stored


def test_detail_of_someone_elses_query_is_404(client, llm, policy, user_headers, admin_headers):
    query_id = ask(client, admin_headers).json()["query_id"]

    assert client.get(f"{PREFIX}/queries/{query_id}", headers=user_headers).status_code == 404


def test_detail_cannot_tell_missing_from_forbidden(client, llm, policy, user_headers, admin_headers):
    theirs = ask(client, admin_headers).json()["query_id"]

    forbidden = client.get(f"{PREFIX}/queries/{theirs}", headers=user_headers)
    missing = client.get(f"{PREFIX}/queries/99999", headers=user_headers)

    assert forbidden.status_code == missing.status_code == 404
    assert forbidden.json() == missing.json()


def test_detail_never_shows_the_raw_text_of_invalid_answers(client, llm, policy, user_headers):
    llm.answer = "PWNED"
    query_id = ask(client, user_headers).json()["query_id"]

    res = client.get(f"{PREFIX}/queries/{query_id}", headers=user_headers)

    assert res.status_code == 200
    assert res.json()["answer"] is None
    assert "PWNED" not in res.text


def test_detail_requires_a_token(client):
    assert client.get(f"{PREFIX}/queries/1").status_code in (401, 403)


def test_citation_survives_deleting_the_document(client, llm, policy, db, user_headers, admin_headers):
    from app.features.documents.service import delete_document

    query_id = ask(client, user_headers).json()["query_id"]
    delete_document(db, policy.id)

    body = client.get(f"{PREFIX}/queries/{query_id}", headers=user_headers).json()

    assert body["citations"][0]["document_name"] == "policy.pdf"
    assert "14 days" in body["citations"][0]["snippet"]
