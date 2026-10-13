"""The whole search of the app on the large question sets, step by step: by meaning only, then with keywords (hybrid), then with the
reranker (what the app does now).

    python -m evaluation.pipeline_eval                       # Cantonese Wikipedia and DRCD, 500 questions each
    python -m evaluation.pipeline_eval --dataset drcd

The chunks are cut by the app's chunker and embedded by the app's embedder; the ranking is done by the app's own functions
(retrieval.rank_hybrid, rank_by_cosine, rerank.rerank_scores), only without the database, whose JSON vectors would make 500 questions slow.
A chunk is right when it comes from the question's article and covers the answer (the same judgement as the chunking comparison).
No LLM is used.
"""
import argparse
import json
import time

import numpy as np

from app.core.config import settings
from app.features.ingestion.pipeline.chunker import recursive_spans
from app.features.ingestion.pipeline.embedder import embed_texts
from app.features.rag.rerank import rerank_scores
from app.features.rag.retrieval import cosine_scores, rank_by_cosine, rank_hybrid
from evaluation import drcd, metrics, wikiqa
from evaluation.chunk_eval import covers
from evaluation.run import RESULTS_DIR

STEPS = ["by meaning only", "hybrid (meaning + keywords)", "hybrid + reranker (the app)"]


def evaluate_pipeline(dataset: dict, embed=embed_texts, rerank=rerank_scores, top_k: int = 4, candidates: int = 10,
                      min_score: float | None = None, size: int = 500, overlap: int = 50) -> dict:
    """dataset: {"documents": [{"id", "text"}], "questions": [{"question", "document", "answer_spans"}]}"""
    if min_score is None:
        min_score = settings.rag_min_score
    chunks = []  # (document id, start, end, text)
    for doc in dataset["documents"]:
        chunks.extend((doc["id"], s, e, doc["text"][s:e]) for s, e in recursive_spans(doc["text"], size, overlap))
    questions = dataset["questions"]
    texts = [c[3] for c in chunks]
    vectors = [np.asarray(v, dtype=float) for v in embed(texts)]
    query_vectors = embed([q["question"] for q in questions])

    def relevant(q: int, c: int) -> bool:
        document, start, end, _ = chunks[c]
        return document == questions[q]["document"] and covers((start, end), questions[q]["answer_spans"])

    ranks = {step: [] for step in STEPS}
    kept = []  # the app refuses a question when not even the best chunk reaches min_score
    for q, (question, query_vector) in enumerate(zip(questions, query_vectors)):
        kept.append(float(cosine_scores(query_vector, vectors).max()) >= min_score)
        order = {
            STEPS[0]: [i for i, _ in rank_by_cosine(query_vector, vectors, candidates)],
            STEPS[1]: [i for i, _ in rank_hybrid(query_vector, vectors, texts, question["question"], candidates, 0.0)],
        }
        pool = order[STEPS[1]]
        scores = rerank(question["question"], [texts[i] for i in pool])
        order[STEPS[2]] = [pool[k] for k in sorted(range(len(pool)), key=lambda k: -scores[k])]
        for step in STEPS:
            ranks[step].append(metrics.first_true_rank([relevant(q, c) for c in order[step]]))

    results = {}
    for step in STEPS:
        found = [metrics.hit_at(r, top_k) for r in ranks[step]]
        results[step] = {
            "hit_at_1": metrics.rate([metrics.hit_at(r, 1) for r in ranks[step]]),
            "hit_at_k": metrics.rate(found),
            "mrr": metrics.mean([metrics.reciprocal_rank(min_rank(r, top_k)) for r in ranks[step]]),
            "found_by_app": metrics.rate([hit and keep for hit, keep in zip(found, kept)]),
            "hits": found,
        }
    for step in STEPS:
        for other, key in [(STEPS[0], "vs_meaning"), (STEPS[1], "vs_hybrid")]:
            now, before = np.array(results[step]["hits"]), np.array(results[other]["hits"])
            gained, lost = int((now & ~before).sum()), int((~now & before).sum())
            results[step][key] = {"gained": gained, "lost": lost, "p": metrics.sign_test_p(gained, lost)}
    return {"questions": len(questions), "chunks": len(chunks), "top_k": top_k, "candidates": candidates,
            "min_score": min_score, "kept_by_threshold": metrics.rate(kept), "results": results}


def min_rank(rank, top_k):
    """The rank, or None when it is beyond the chunks the LLM would get (the reciprocal rank is only counted within top_k)."""
    return rank if rank is not None and rank <= top_k else None


def render(name: str, report: dict) -> str:
    k = report["top_k"]
    lines = [
        f"### {name}: {report['questions']} questions, {report['chunks']} chunks",
        "",
        f"top {k} given to the LLM; the reranker chooses among {report['candidates']} candidates. "
        f"{report['kept_by_threshold'] * 100:.0f}% of the questions reach min_score={report['min_score']} (the others are refused by the app).",
        "",
        f"| search | hit@1 | hit@{k} | MRR | hit@{k} and not refused | against meaning only (found / lost, p) | against hybrid (found / lost, p) |",
        "|---|---|---|---|---|---|---|",
    ]
    for number, (step, r) in enumerate(report["results"].items()):
        def versus(key):
            v = r[key]
            return f"+{v['gained']} / -{v['lost']}, p = {v['p']:.3f}"

        against_meaning = versus("vs_meaning") if number >= 1 else "-"  # a step is not compared with itself or with a later one
        against_hybrid = versus("vs_hybrid") if number >= 2 else "-"
        lines.append(
            f"| {step} | {r['hit_at_1'] * 100:.0f}% | {r['hit_at_k'] * 100:.0f}% | {r['mrr']:.2f} | {r['found_by_app'] * 100:.0f}% | "
            f"{against_meaning} | {against_hybrid} |"
        )
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", choices=["wikiqa-yue", "drcd", "both"], default="both")
    parser.add_argument("--max-questions", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    wanted = {"wikiqa-yue": ["wikiqa-yue"], "drcd": ["drcd"], "both": ["wikiqa-yue", "drcd"]}[args.dataset]
    saved = {}
    started = time.perf_counter()
    for name in wanted:
        if name == "drcd":
            label, dataset = "DRCD (Traditional Chinese Wikipedia)", drcd.build_span_dataset(drcd.download_rows("dev"), max_questions=args.max_questions, seed=args.seed)
        else:
            label, dataset = "Cantonese Wikipedia", wikiqa.build_span_dataset(wikiqa.download_rows("yue"), max_questions=args.max_questions, seed=args.seed)
        report = evaluate_pipeline(dataset)
        print(render(label, report), flush=True)
        saved[name] = {**report, "results": {s: {k: v for k, v in r.items() if k != "hits"} for s, r in report["results"].items()}}
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)  # saved after every set: a run that is stopped halfway keeps what it finished
        (RESULTS_DIR / "pipeline_eval.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"({time.perf_counter() - started:.0f}s; embedder {settings.embedding_model}, reranker {settings.rerank_model})")


if __name__ == "__main__":
    main()
