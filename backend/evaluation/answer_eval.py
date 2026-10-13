"""The answers of the LLM on the large question sets: Cantonese Wikipedia and DRCD, 500 questions each.

    python -m evaluation.answer_eval                 # the app as it is now: hybrid search, reranker, the LLM of the settings
    python -m evaluation.answer_eval --no-rerank     # the same without the reranker, to see what it changes in the answers
    python -m evaluation.answer_eval --dataset drcd --max-questions 100

Every question goes through the same steps as in the app: the threshold, the search, the reranker, the prompt, the LLM, OpenCC, the refusal
check and the check of the [n] citations. The steps are the app's own functions (search and reranker as in pipeline_eval; build_prompt,
to_traditional, is_refusal and extract_cited_numbers from the service); only the database is left out, because reading 4,770 JSON vectors per
question would make 1,000 questions take hours.

An answer is correct when it contains the text of the right answer (the characters of the answer in the article, after turning simplified
characters into traditional ones and dropping spaces and punctuation). That is strict: a right answer in other words ("培英中學" for
"PUI YING MIDDLE SCHOOL") counts as wrong, so the percentages are a floor. These sets have no question without an answer, so refusals and wrong
answers to such questions are measured only by the hand-written set (evaluation.run --answers).
"""
import argparse
import json
import re
import time

import numpy as np

from app.core.config import settings
from app.features.ingestion.pipeline.chunker import recursive_spans
from app.features.ingestion.pipeline.embedder import embed_texts
from app.features.rag.language import to_traditional
from app.features.rag.llm import LLMError, OllamaClient
from app.features.rag.prompt import build_prompt
from app.features.rag.rerank import rerank_scores
from app.features.rag.retrieval import RetrievedChunk, cosine_scores, rank_hybrid
from app.features.rag.service import extract_cited_numbers, is_refusal
from evaluation import drcd, metrics, wikiqa
from evaluation.run import RESULTS_DIR

_NOT_LETTERS = re.compile(r"[\s\W_]+")


def normalize(text: str) -> str:
    return _NOT_LETTERS.sub("", to_traditional(text).lower())


def contains_answer(text: str, answers: list[str]) -> bool:
    """The text holds at least one of the right answers (case, spaces, punctuation and simplified/traditional do not matter)."""
    haystack = normalize(text)
    return any(needle and needle in haystack for needle in (normalize(a) for a in answers))


def evaluate_answers_at_scale(dataset: dict, llm, embed=embed_texts, rerank=rerank_scores, top_k: int = 4, candidates: int = 10,
                              min_score: float | None = None, size: int = 500, overlap: int = 50, progress=None) -> dict:
    """dataset: {"documents": [{"id", "title", "text"}], "questions": [{"id", "question", "document", "answer_spans"}]}.
    rerank=None searches without the reranker (the first top_k of the search go to the LLM)."""
    if min_score is None:
        min_score = settings.rag_min_score
    titles = {d["id"]: d.get("title", str(d["id"])) for d in dataset["documents"]}
    texts_by_document = {d["id"]: d["text"] for d in dataset["documents"]}
    chunks = []  # (document id, text)
    for doc in dataset["documents"]:
        chunks.extend((doc["id"], doc["text"][s:e]) for s, e in recursive_spans(doc["text"], size, overlap))
    texts = [text for _, text in chunks]
    vectors = [np.asarray(v, dtype=float) for v in embed(texts)]
    questions = dataset["questions"]
    query_vectors = embed([q["question"] for q in questions])

    records = []
    for number, (q, query_vector) in enumerate(zip(questions, query_vectors), start=1):
        answers = list({texts_by_document[q["document"]][s:e] for s, e in q["answer_spans"]})
        started = time.perf_counter()
        pool = rank_hybrid(query_vector, vectors, texts, q["question"], candidates if rerank else top_k, min_score)
        if rerank and len(pool) > 1:
            scores = rerank(q["question"], [texts[i] for i, _ in pool])
            pool = [pool[k] for k in sorted(range(len(pool)), key=lambda k: -scores[k])][:top_k]

        record = {"id": q["id"], "question": q["question"], "answers": answers, "answer": None, "in_context": False}
        if not pool:  # not even the best chunk reaches min_score: the app refuses without asking the LLM
            record["status"] = "below_threshold"
        else:
            given = [
                RetrievedChunk(chunk_id=i, document_id=0, document_name=titles[chunks[i][0]], page_number=None,
                               chunk_index=i, content=texts[i], score=score)
                for i, score in pool
            ]
            record["in_context"] = contains_answer("\n".join(c.content for c in given), answers)
            try:
                answer = to_traditional(llm.generate(build_prompt(q["question"], given)))
            except LLMError:
                record["status"] = "failed"
            else:
                record["answer"] = answer
                if is_refusal(answer):
                    record["status"] = "no_evidence"
                elif not extract_cited_numbers(answer, len(given)):
                    record["status"] = "invalid_answer"
                else:
                    record["status"] = "answered"
        record["correct"] = record["status"] == "answered" and contains_answer(record["answer"], answers)
        record["seconds"] = time.perf_counter() - started
        records.append(record)
        if progress and number % 50 == 0:
            progress(number, len(questions))

    return {"config": {"top_k": top_k, "candidates": candidates if rerank else None, "min_score": min_score,
                       "llm": getattr(llm, "model", type(llm).__name__), "reranker": settings.rerank_model if rerank else None},
            "summary": summarize(records), "details": records}


def summarize(records: list[dict]) -> dict:
    n = len(records)
    count = lambda flag: sum(1 for r in records if flag(r))  # noqa: E731
    in_context = [r for r in records if r["in_context"]]
    correct = count(lambda r: r["correct"])
    low, high = metrics.wilson_interval(correct, n)
    return {
        "questions": n,
        "correct": correct / n if n else None,
        "correct_interval_95": [low, high],
        "answer_in_the_chunks_given": len(in_context) / n if n else None,
        "correct_when_the_answer_was_given": metrics.rate([r["correct"] for r in in_context]),
        "statuses": {s: count(lambda r, s=s: r["status"] == s) for s in ("answered", "no_evidence", "invalid_answer", "below_threshold", "failed")},
        "refused_by_the_llm_though_the_answer_was_given": count(lambda r: r["in_context"] and r["status"] == "no_evidence"),
        "wrong_answer_though_the_answer_was_given": count(lambda r: r["in_context"] and r["status"] == "answered" and not r["correct"]),
        "mean_seconds": metrics.mean([r["seconds"] for r in records]),
    }


def render(name: str, report: dict) -> str:
    s, cfg = report["summary"], report["config"]
    pct = lambda v: "-" if v is None else f"{v * 100:.0f}%"  # noqa: E731
    low, high = s["correct_interval_95"]
    st = s["statuses"]
    lines = [
        f"### {name}: {s['questions']} questions",
        "",
        f"LLM {cfg['llm']}, top {cfg['top_k']}" + (f" of {cfg['candidates']} reranked by {cfg['reranker']}" if cfg["reranker"] else ", no reranker")
        + f", min_score {cfg['min_score']}.",
        "",
        "| | |",
        "|---|---|",
        f"| **answer correct** | **{pct(s['correct'])}** (95% interval {pct(low)} to {pct(high)}) |",
        f"| the answer was among the 4 chunks given to the LLM | {pct(s['answer_in_the_chunks_given'])} |",
        f"| correct, when the answer was among them | {pct(s['correct_when_the_answer_was_given'])} |",
        f"| answered / refused by the LLM / no valid [n] / below the threshold / failed | {st['answered']} / {st['no_evidence']} / {st['invalid_answer']} / {st['below_threshold']} / {st['failed']} |",
        f"| the LLM had the answer but refused | {s['refused_by_the_llm_though_the_answer_was_given']} |",
        f"| the LLM had the answer but answered wrongly | {s['wrong_answer_though_the_answer_was_given']} |",
        f"| mean time per question | {s['mean_seconds']:.1f}s |",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", choices=["wikiqa-yue", "drcd", "both"], default="both")
    parser.add_argument("--max-questions", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-rerank", action="store_true", help="search without the reranker")
    args = parser.parse_args(argv)

    wanted = {"wikiqa-yue": ["wikiqa-yue"], "drcd": ["drcd"], "both": ["wikiqa-yue", "drcd"]}[args.dataset]
    llm = OllamaClient()
    suffix = "-no-rerank" if args.no_rerank else ""
    saved = {}
    started = time.perf_counter()
    for name in wanted:
        if name == "drcd":
            label, dataset = "DRCD (Traditional Chinese Wikipedia)", drcd.build_span_dataset(drcd.download_rows("dev"), max_questions=args.max_questions, seed=args.seed)
        else:
            label, dataset = "Cantonese Wikipedia", wikiqa.build_span_dataset(wikiqa.download_rows("yue"), max_questions=args.max_questions, seed=args.seed)
        report = evaluate_answers_at_scale(
            dataset, llm, rerank=None if args.no_rerank else rerank_scores,
            progress=lambda done, total, label=label: print(f"   {label}: {done}/{total} questions", flush=True),
        )
        print(render(label, report), flush=True)
        saved[name] = report
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)  # saved after every set: a run that is stopped halfway keeps what it finished
        (RESULTS_DIR / f"answer_eval{suffix}.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"({time.perf_counter() - started:.0f}s)")


if __name__ == "__main__":
    main()
