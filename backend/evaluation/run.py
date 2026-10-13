"""Measure how well retrieval and answers work on a fixed set of documents and questions.

    python -m evaluation.run              # retrieval only: fast, needs no LLM
    python -m evaluation.run --answers    # also asks the LLM (Ollama must be running)

Everything happens in an in-memory database, so your real data is never touched.
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.all_models import Base, Query, User
from app.features.documents.repository import create_chunks, create_document, update_document_status
from app.features.ingestion.pipeline.chunker import chunk_pages
from app.features.ingestion.pipeline.embedder import MODEL_NAME, embed_texts
from app.features.rag.llm import LLMError, OllamaClient
from app.features.rag.rerank import rerank_scores
from app.features.rag.retrieval import search_chunks
from app.features.rag.service import answer_question, extract_cited_numbers
from evaluation import metrics

DATASET_DIR = Path(__file__).parent / "dataset"
RESULTS_DIR = Path(__file__).parent / "results"
SWEEP_THRESHOLDS = [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]


def load_dataset(dataset_dir: Path = DATASET_DIR) -> dict:
    data = json.loads((dataset_dir / "questions.json").read_text(encoding="utf-8"))
    documents = [
        {**doc, "text": (dataset_dir / "documents" / doc["file"]).read_text(encoding="utf-8")}
        for doc in data["documents"]
    ]
    return {"documents": documents, "questions": data["questions"]}


def make_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def build_index(db, documents: list[dict], embed) -> int:
    """Chunk, embed and store the documents the way the ingestion service does. Returns the user id."""
    admin = User(email="evaluation@example.com", password_hash="not-a-real-hash", role="admin")
    db.add(admin)
    db.commit()
    db.refresh(admin)

    for doc in documents:
        document = create_document(db, doc["file"], doc["file"], "txt", admin.id)
        # a dataset can bring its own passages ("chunks"); otherwise the text is cut like the app does
        pieces = [(None, text) for text in doc["chunks"]] if "chunks" in doc else chunk_pages([(None, doc["text"])])
        contents = [text for _, text in pieces]
        create_chunks(db, document.id, contents, embed(contents), [page for page, _ in pieces])
        update_document_status(db, document, "processed")
    return admin.id


def _chunk_is_relevant(question: dict, chunk) -> bool:
    """The chunk holds the evidence and, when the question says so, comes from the question's own document."""
    if question.get("same_document") and chunk.document_name != question["document"]:
        return False
    return metrics.is_relevant(chunk.content, question["evidence"])


def _group_rows(records: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for record in records:
        groups.setdefault(record["group"], []).append(record)
    return groups


def evaluate_retrieval(db, questions: list[dict], embed_query, top_k: int, min_score: float, like_the_app: bool = False, rerank=None) -> dict:
    """like_the_app: search the way the app does (keywords as well as meaning, and the reranker when there is one) and apply the
    threshold the way it does: to the best meaning score of the whole question. Otherwise the chunks are found by meaning only,
    which is what the comparison of embedding models needs."""
    records = []
    vectors = embed_query([q["question"] for q in questions])  # one batch: much faster than one call per question
    for q, vector in zip(questions, vectors):
        # min_score 0 on purpose: rank quality is judged first, the threshold is judged separately below
        if like_the_app:
            ranked = search_chunks(
                db, vector, top_k=top_k, min_score=0.0,
                query_text=q["question"] if settings.rag_hybrid_search else None, rerank=rerank, candidates=settings.rag_candidates,
            )
        else:
            ranked = search_chunks(db, vector, top_k=top_k, min_score=0.0)
        scores = [chunk.score for chunk in ranked]
        best_meaning = search_chunks(db, vector, top_k=1, min_score=0.0)[0].score  # what the app's threshold looks at
        record = {
            "id": q["id"],
            "group": q["group"],
            "kind": q["kind"],
            "question": q["question"],
            "scores": [round(s, 3) for s in scores],
            "best_meaning": round(best_meaning, 3),
            "retrieved": [
                {
                    "document": chunk.document_name,
                    "score": round(chunk.score, 3),
                    "relevant": _chunk_is_relevant(q, chunk),
                }
                for chunk in ranked
            ],
        }
        if q["kind"] == "answerable":
            rank = metrics.first_true_rank([_chunk_is_relevant(q, chunk) for chunk in ranked])
            record["rank"] = rank
            record["hit_at_1"] = metrics.hit_at(rank, 1)
            record["hit_at_k"] = metrics.hit_at(rank, top_k)
            record["reciprocal_rank"] = metrics.reciprocal_rank(rank)
            # the score the threshold is applied to: the chunk's own, or (like the app's hybrid search) the best of the question
            record["gate_score"] = None if rank is None else (best_meaning if like_the_app else scores[rank - 1])
            record["found_by_app"] = record["gate_score"] is not None and record["gate_score"] >= min_score
        else:
            # the app would call the LLM with this evidence, although there is no answer in the documents
            record["false_evidence"] = best_meaning >= min_score
        records.append(record)

    def summarize(rows: list[dict]) -> dict:
        answerable = [r for r in rows if r["kind"] == "answerable"]
        unanswerable = [r for r in rows if r["kind"] == "unanswerable"]
        out = {"questions": len(rows)}
        if answerable:
            out.update(
                {
                    "answerable": len(answerable),
                    "hit_at_1": metrics.rate([r["hit_at_1"] for r in answerable]),
                    "hit_at_k": metrics.rate([r["hit_at_k"] for r in answerable]),
                    "mrr": metrics.mean([r["reciprocal_rank"] for r in answerable]),
                    "found_by_app": metrics.rate([r["found_by_app"] for r in answerable]),
                }
            )
        if unanswerable:
            out.update(
                {
                    "unanswerable": len(unanswerable),
                    "false_evidence": metrics.rate([r["false_evidence"] for r in unanswerable]),
                }
            )
        return out

    sweep = []
    answerable = [r for r in records if r["kind"] == "answerable"]
    unanswerable = [r for r in records if r["kind"] == "unanswerable"]
    for threshold in SWEEP_THRESHOLDS:
        sweep.append(
            {
                "min_score": threshold,
                "found_by_app": metrics.rate(
                    [r["gate_score"] is not None and r["gate_score"] >= threshold for r in answerable]
                ),
                "false_evidence": metrics.rate(
                    [r["best_meaning"] >= threshold for r in unanswerable]
                ),
            }
        )

    return {
        "overall": summarize(records),
        "by_group": {name: summarize(rows) for name, rows in _group_rows(records).items()},
        "sweep": sweep,
        "details": records,
    }


def evaluate_answers(db, user_id: int, questions: list[dict], embed_query, llm, top_k: int, min_score: float, rerank=None) -> dict:
    records = []
    for q in questions:
        # the chunks the LLM is given: found exactly as the app finds them, or [n] in the answer would point at the wrong chunk
        chunks = search_chunks(
            db, embed_query([q["question"]])[0], top_k=top_k, min_score=min_score,
            query_text=q["question"] if settings.rag_hybrid_search else None, rerank=rerank, candidates=settings.rag_candidates,
        )
        started = time.perf_counter()
        try:
            result = answer_question(
                db, user_id, q["question"], llm, embed=embed_query, top_k=top_k, min_score=min_score, rerank=rerank
            )
            status, answer, query_id = result.status, result.answer, result.query_id
        except LLMError:
            status, answer, query_id = "failed", None, None
        latency_ms = int((time.perf_counter() - started) * 1000)

        record = {
            "id": q["id"],
            "group": q["group"],
            "kind": q["kind"],
            "question": q["question"],
            "status": status,
            "answer": answer,
            "latency_ms": latency_ms,
        }
        if status == "answered":
            record["language_ok"] = metrics.language_matches(q["question"], answer)
        if query_id is not None and status == "invalid_answer":
            record["raw_answer"] = db.get(Query, query_id).answer  # hidden from users, useful for diagnosis
        if q["kind"] == "answerable":
            cited = extract_cited_numbers(answer, len(chunks)) if answer else []
            record["correct"] = status == "answered" and metrics.answer_is_correct(answer, q["must_contain"])
            record["supported"] = (
                status == "answered"
                and metrics.citations_are_supported([chunks[n - 1].content for n in cited], q["evidence"])
            )
        records.append(record)

    def summarize(rows: list[dict]) -> dict:
        answerable = [r for r in rows if r["kind"] == "answerable"]
        unanswerable = [r for r in rows if r["kind"] == "unanswerable"]
        statuses: dict[str, int] = {}
        for r in rows:
            statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        latencies = [r["latency_ms"] for r in rows]
        out = {
            "questions": len(rows),
            "statuses": statuses,
            "latency_ms_mean": metrics.mean(latencies),
            "latency_ms_p95": metrics.percentile(latencies, 95),
        }
        shown = [r for r in rows if r["status"] == "answered"]
        if shown:
            out["right_language"] = metrics.rate([r["language_ok"] for r in shown])
        if answerable:
            answered = [r for r in answerable if r["status"] == "answered"]
            out.update(
                {
                    "answerable": len(answerable),
                    "correct": metrics.rate([r["correct"] for r in answerable]),
                    "answered": metrics.rate([r["status"] == "answered" for r in answerable]),
                    "invalid_answer": metrics.rate([r["status"] == "invalid_answer" for r in answerable]),
                    "no_evidence": metrics.rate([r["status"] == "no_evidence" for r in answerable]),
                    "citation_supported": metrics.rate([r["supported"] for r in answered]),
                }
            )
        if unanswerable:
            out.update(
                {
                    "unanswerable": len(unanswerable),
                    "refused": metrics.rate([r["status"] == "no_evidence" for r in unanswerable]),
                    "wrong_answer_shown": metrics.rate([r["status"] == "answered" for r in unanswerable]),
                }
            )
        return out

    return {
        "overall": summarize(records),
        "by_group": {name: summarize(rows) for name, rows in _group_rows(records).items()},
        "details": records,
    }


def run_evaluation(dataset: dict, embed=embed_texts, llm=None, top_k: int = 4, min_score: float | None = None,
                   embedder_name: str = MODEL_NAME, embed_query=None, rerank=None, like_the_app: bool = False) -> dict:
    """embed turns the document chunks into vectors; embed_query does the same for questions (some models want a
    different prefix for each). By default both are the same function, and min_score is the app's own setting."""
    embed_query = embed_query or embed
    if min_score is None:
        min_score = settings.rag_min_score
    db = make_session()
    try:
        user_id = build_index(db, dataset["documents"], embed)
        report = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "config": {"top_k": top_k, "min_score": min_score, "embedder": embedder_name,
                       "search": _describe_search(like_the_app, rerank),
                       "questions": len(dataset["questions"]), "documents": len(dataset["documents"])},
            "retrieval": evaluate_retrieval(db, dataset["questions"], embed_query, top_k, min_score, like_the_app, rerank),
        }
        if llm is not None:
            report["config"]["llm_model"] = getattr(llm, "model", type(llm).__name__)
            report["config"]["reranker"] = settings.rerank_model if rerank else None
            report["answers"] = evaluate_answers(db, user_id, dataset["questions"], embed_query, llm, top_k, min_score, rerank)
        return report
    finally:
        db.close()


def _describe_search(like_the_app: bool, rerank) -> str:
    if not like_the_app:
        return "by meaning only"
    parts = ["meaning + keywords (hybrid)" if settings.rag_hybrid_search else "by meaning only"]
    if rerank:
        parts.append(f"reranked from {settings.rag_candidates} candidates by {settings.rerank_model}")
    return ", ".join(parts)


def _pct(value) -> str:
    return "-" if value is None else f"{value * 100:.0f}%"


def _num(value) -> str:
    return "-" if value is None else f"{value:.2f}"


def render_markdown(report: dict) -> str:
    cfg = report["config"]
    lines = [
        "# RAG evaluation",
        "",
        f"{cfg['questions']} questions over {cfg['documents']} documents. top_k={cfg['top_k']}, "
        f"min_score={cfg['min_score']}, embedder={cfg['embedder']}, search: {cfg['search']}"
        + (f", LLM={cfg['llm_model']}" if "llm_model" in cfg else "")
        + ".",
        "",
        "## Retrieval (does the right passage come back?)",
        "",
        "| group | questions | hit@1 | hit@k | MRR | found by the app (score >= min_score) | false evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    retrieval = report["retrieval"]
    for name, row in [("**all**", retrieval["overall"])] + sorted(retrieval["by_group"].items()):
        lines.append(
            f"| {name} | {row['questions']} | {_pct(row.get('hit_at_1'))} | {_pct(row.get('hit_at_k'))} | "
            f"{_num(row.get('mrr'))} | {_pct(row.get('found_by_app'))} | {_pct(row.get('false_evidence'))} |"
        )
    lines += [
        "",
        "hit@1 / hit@k: the right passage is the first / among the top k results. "
        "False evidence: a question with no answer in the documents still gets passages above min_score, so the LLM would be called.",
        "",
        "### Choosing min_score",
        "",
        "| min_score | answerable questions still found | unanswerable questions wrongly given evidence |",
        "|---|---|---|",
    ]
    for row in retrieval["sweep"]:
        lines.append(f"| {row['min_score']} | {_pct(row['found_by_app'])} | {_pct(row['false_evidence'])} |")

    if "answers" in report:
        answers = report["answers"]
        lines += [
            "",
            "## Answers (what the user gets)",
            "",
            "| group | questions | correct | right language | answered | no evidence | invalid (no [n]) | citation supported | refused (no answer exists) | wrong answer shown | mean latency |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for name, row in [("**all**", answers["overall"])] + sorted(answers["by_group"].items()):
            latency = row["latency_ms_mean"]
            lines.append(
                f"| {name} | {row['questions']} | {_pct(row.get('correct'))} | {_pct(row.get('right_language'))} | "
                f"{_pct(row.get('answered'))} | "
                f"{_pct(row.get('no_evidence'))} | {_pct(row.get('invalid_answer'))} | "
                f"{_pct(row.get('citation_supported'))} | {_pct(row.get('refused'))} | "
                f"{_pct(row.get('wrong_answer_shown'))} | {'-' if latency is None else f'{latency / 1000:.1f}s'} |"
            )
        lines += [
            "",
            "correct: answered, and the key facts are in the answer. right language: among the answers shown, the answer is in "
            "the language of the question. citation supported: among answered questions, the cited passage really contains the evidence.",
        ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--answers", action="store_true", help="also ask the LLM (slow, needs Ollama)")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--min-score", type=float, default=None, help="default: RAG_MIN_SCORE from the settings")
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "latest.json", help="where to save the full JSON report")
    args = parser.parse_args(argv)

    report = run_evaluation(
        load_dataset(),
        llm=OllamaClient() if args.answers else None,
        top_k=args.top_k,
        min_score=args.min_score,
        rerank=rerank_scores if settings.rag_rerank else None,
        like_the_app=True,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(render_markdown(report))
    print(f"Full report with every question: {args.output}")


if __name__ == "__main__":
    main()
