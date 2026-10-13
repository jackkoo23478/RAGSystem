"""Compare ways of cutting documents into chunks (fixed-size, recursive, semantic) on the same questions.

    python -m evaluation.chunk_eval                          # Cantonese Wikipedia, all strategies
    python -m evaluation.chunk_eval --dataset drcd           # Traditional Chinese Wikipedia
    python -m evaluation.chunk_eval --strategies fixed-500 recursive-500 semantic-85

A strategy is a name and a number: fixed-500 (windows of 500 characters, 10% overlap), recursive-500 (the same size, cut at
natural breaks), semantic-85 (cut where the gap between neighbouring sentences is in the top 15% of the document),
gap-40 (cut where that gap is bigger than the fixed number 0.40).

The questions never change: a chunk is right when it belongs to the question's article and covers the characters where the
answer sits, so every chunker is judged by the same yardstick. Only the chunking changes; the ranking is plain cosine similarity,
the same arithmetic as the app, computed for all questions at once with NumPy.
"""
import argparse
import json
import time

import numpy as np

from app.core.config import settings
from evaluation import chunking, drcd, metrics, wikiqa
from evaluation.embedders import load_embedder
from evaluation.run import RESULTS_DIR

TOP_K = 4
BASELINE = "fixed-500"  # what the app does today
DEFAULT_STRATEGIES = [
    "fixed-300", "fixed-500", "fixed-800",
    "recursive-300", "recursive-500", "recursive-800",
    "semantic-75", "semantic-90",
]


def make_chunker(name: str, embed):
    kind, number = name.rsplit("-", 1)
    number = int(number)
    if kind == "fixed":
        return lambda text: chunking.fixed_spans(text, number, number // 10)
    if kind == "recursive":
        return lambda text: chunking.recursive_spans(text, number, number // 10)
    if kind == "semantic":
        return lambda text: chunking.semantic_spans(text, embed, percentile=number)
    if kind == "gap":  # gap-40: cut where the gap between neighbouring sentences is bigger than 0.40
        return lambda text: chunking.semantic_spans(text, embed, gap_limit=number / 100)
    raise ValueError(f"unknown strategy {name!r}: use fixed-N, recursive-N, semantic-N or gap-N")


def covers(chunk_span: tuple[int, int], answer_spans: list[tuple[int, int]]) -> bool:
    """The chunk holds every character of at least one of the answers."""
    start, end = chunk_span
    return any(start <= a and b <= end for a, b in answer_spans)


def rank_top_k(question_vectors: np.ndarray, chunk_vectors: np.ndarray, top_k: int = TOP_K):
    """Indices of the best chunks for every question, best first, plus their cosine scores."""
    q = question_vectors / np.maximum(np.linalg.norm(question_vectors, axis=1, keepdims=True), 1e-12)
    m = chunk_vectors / np.maximum(np.linalg.norm(chunk_vectors, axis=1, keepdims=True), 1e-12)
    scores = q @ m.T
    order = np.argsort(-scores, axis=1)[:, :top_k]
    return order, np.take_along_axis(scores, order, axis=1)


def evaluate_chunker(dataset: dict, chunker, embed_documents, question_vectors: np.ndarray, top_k: int = TOP_K) -> dict:
    texts = {doc["id"]: doc["text"] for doc in dataset["documents"]}
    chunks = []  # (document id, start, end)
    for doc in dataset["documents"]:
        chunks.extend((doc["id"], s, e) for s, e in chunker(doc["text"]))

    vectors = np.array(embed_documents([texts[d][s:e] for d, s, e in chunks]), dtype=float)
    order, _ = rank_top_k(question_vectors, vectors, top_k)

    by_document: dict[str, list[tuple[int, int]]] = {}
    for d, s, e in chunks:
        by_document.setdefault(d, []).append((s, e))

    hit1, hit_k, reciprocal, reachable, sent = [], [], [], [], []
    for q, ranked in zip(dataset["questions"], order):
        flags = [chunks[i][0] == q["document"] and covers((chunks[i][1], chunks[i][2]), q["answer_spans"]) for i in ranked]
        rank = metrics.first_true_rank(flags)
        hit1.append(metrics.hit_at(rank, 1))
        hit_k.append(metrics.hit_at(rank, top_k))
        reciprocal.append(metrics.reciprocal_rank(rank))
        reachable.append(any(covers(span, q["answer_spans"]) for span in by_document.get(q["document"], [])))
        sent.append(sum(chunks[i][2] - chunks[i][1] for i in ranked))

    lengths = [e - s for _, s, e in chunks]
    return {
        "chunks": len(chunks),
        "mean_chars": float(np.mean(lengths)),
        "answer_kept_whole": metrics.rate(reachable),
        "hit_at_1": metrics.rate(hit1),
        "hit_at_k": metrics.rate(hit_k),
        "mrr": metrics.mean(reciprocal),
        "chars_sent_to_llm": metrics.mean(sent),
        "hits_at_k": hit_k,  # per question, for the paired comparison with the baseline
    }


def cached(embed):
    """Remember vectors by text: the two semantic strategies cut the same sentences, so those are embedded once."""
    memory: dict[str, list[float]] = {}

    def embed_cached(texts: list[str]) -> list[list[float]]:
        missing = list(dict.fromkeys(t for t in texts if t not in memory))
        if missing:
            memory.update(zip(missing, embed(missing)))
        return [memory[t] for t in texts]

    return embed_cached


def run(dataset: dict, strategies: list[str], model: str) -> list[dict]:
    embed_documents, embed_query = load_embedder(model)
    embed_sentences = cached(embed_documents)
    question_vectors = np.array(embed_query([q["question"] for q in dataset["questions"]]), dtype=float)

    results = []
    for name in strategies:
        print(f"... {name}", flush=True)
        started = time.perf_counter()
        result = evaluate_chunker(dataset, make_chunker(name, embed_sentences), embed_documents, question_vectors)
        result.update(strategy=name, seconds=time.perf_counter() - started)
        results.append(result)

    baseline = next((r for r in results if r["strategy"] == BASELINE), None)
    for r in results:
        if baseline is not None:
            was, now = np.array(baseline["hits_at_k"]), np.array(r["hits_at_k"])
            r["gained_vs_baseline"] = int((now & ~was).sum())
            r["lost_vs_baseline"] = int((~now & was).sum())
    return results


def _pct(value) -> str:
    return "-" if value is None else f"{value * 100:.0f}%"


def render(results: list[dict], questions: int, documents: int, model: str) -> str:
    has_baseline = "gained_vs_baseline" in results[0]
    lines = [
        "# Chunking comparison (retrieval only)",
        "",
        f"{questions} questions over {documents} documents, embedding model {model}, top {TOP_K} chunks per question.",
        "",
        "| strategy | chunks | mean chars | answer kept whole | hit@1 | hit@4 | MRR | chars sent to the LLM (top 4) |"
        + (f" vs {BASELINE}: gained / lost (hit@4) |" if has_baseline else ""),
        "|---|---|---|---|---|---|---|---|" + ("---|" if has_baseline else ""),
    ]
    for r in results:
        row = (
            f"| {r['strategy']} | {r['chunks']} | {r['mean_chars']:.0f} | {_pct(r['answer_kept_whole'])} | "
            f"{_pct(r['hit_at_1'])} | {_pct(r['hit_at_k'])} | {r['mrr']:.2f} | {r['chars_sent_to_llm']:.0f} |"
        )
        if has_baseline:
            row += f" +{r['gained_vs_baseline']} / -{r['lost_vs_baseline']} |"
        lines.append(row)
    lines += [
        "",
        "answer kept whole: some chunk of the right article contains all the characters of the answer (the cut did not split it); no ranking can beat this.",
        "hit@k: one of the top k chunks is from the right article and covers the answer. Bigger chunks cover answers more easily, so read hit@4 together with the characters sent to the LLM.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", choices=["wikiqa-yue", "drcd"], default="wikiqa-yue")
    parser.add_argument("--model", default=settings.embedding_model)
    parser.add_argument("--max-questions", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--strategies", nargs="*", default=DEFAULT_STRATEGIES)
    args = parser.parse_args(argv)

    if args.dataset == "drcd":
        dataset = drcd.build_span_dataset(drcd.download_rows("dev"), max_questions=args.max_questions, seed=args.seed)
    else:
        dataset = wikiqa.build_span_dataset(wikiqa.download_rows("yue"), max_questions=args.max_questions, seed=args.seed)

    results = run(dataset, args.strategies, args.model)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    saved = [{k: v for k, v in r.items() if k != "hits_at_k"} for r in results]
    (RESULTS_DIR / f"chunking_{args.dataset}.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(render(results, len(dataset["questions"]), len(dataset["documents"]), args.model))


if __name__ == "__main__":
    main()
