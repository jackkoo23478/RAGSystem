"""Compare three ways of searching the same chunks: meaning (the embedding model, what the app does), keywords (BM25) and both
together (hybrid, merged with reciprocal rank fusion).

    python -m evaluation.hybrid_eval --dataset wikiqa-yue    # Cantonese Wikipedia (500 questions, chunks cut like the app does)
    python -m evaluation.hybrid_eval --dataset drcd          # Traditional Chinese Wikipedia
    python -m evaluation.hybrid_eval --dataset pdf           # a question bank in your own database: look up a question by its words

The first two use the question sets of the chunking comparison (a chunk is right when it comes from the question's article and covers the
answer). The third reads the chunks (and their stored vectors) of one uploaded document from the database, read-only: the questions are
taken from the document itself (the text before the first option), so it measures "find the question I am looking at", asked in full
and with only the first half of its words. That test favours keywords by construction; read it as a check of exact look-up, not of
understanding.
"""
import argparse
import json
import re
import sqlite3
import time
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.features.ingestion.pipeline.chunker import recursive_spans
from evaluation import drcd, metrics, wikiqa
from evaluation.chunk_eval import covers
from evaluation.embedders import load_embedder
from evaluation.hybrid import BM25, reciprocal_rank_fusion, tokenize
from evaluation.run import RESULTS_DIR

TOP_K = 4
METHODS = ["meaning (embedding)", "keywords (BM25)", "hybrid (both, RRF)"]
STEM = re.compile(r"\d{1,4}\s*\(\d\)\s+(.+?)\s*\(1\)", re.S)  # "831 (3) the question text (1) first option ..."


def normalize(matrix: np.ndarray) -> np.ndarray:
    return matrix / np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)


def evaluate_methods(question_vectors, chunk_vectors, chunk_texts, question_texts, relevant, top_k: int = TOP_K) -> dict:
    """relevant(question index, chunk index) -> bool. Every method ranks all the chunks for every question."""
    dense = normalize(np.asarray(question_vectors, dtype=float)) @ normalize(np.asarray(chunk_vectors, dtype=float)).T
    bm25 = BM25([tokenize(t) for t in chunk_texts])
    keyword = np.vstack([bm25.scores(tokenize(q)) for q in question_texts])
    matrices = {METHODS[0]: dense, METHODS[1]: keyword, METHODS[2]: reciprocal_rank_fusion([dense, keyword])}

    results = {}
    for name, scores in matrices.items():
        order = np.argsort(-scores, axis=1, kind="stable")[:, :top_k]
        ranks = [metrics.first_true_rank([relevant(q, c) for c in row]) for q, row in enumerate(order)]
        results[name] = {
            "hit_at_1": metrics.rate([metrics.hit_at(r, 1) for r in ranks]),
            "hit_at_k": metrics.rate([metrics.hit_at(r, top_k) for r in ranks]),
            "mrr": metrics.mean([metrics.reciprocal_rank(r) for r in ranks]),
            "hits": [metrics.hit_at(r, top_k) for r in ranks],
        }

    base = np.array(results[METHODS[0]]["hits"])
    for name, r in results.items():
        now = np.array(r["hits"])
        r["gained"], r["lost"] = int((now & ~base).sum()), int((~now & base).sum())
        r["p"] = metrics.sign_test_p(r["gained"], r["lost"])
    return results


def span_case(dataset: dict, model: str, size: int = 500, overlap: int = 50) -> dict:
    """Wikipedia sets: chunk with the app's recursive chunker, embed, and judge by the answer's characters."""
    embed_documents, embed_query = load_embedder(model)
    chunks = []  # (document id, start, end, text)
    for doc in dataset["documents"]:
        chunks.extend((doc["id"], s, e, doc["text"][s:e]) for s, e in recursive_spans(doc["text"], size, overlap))
    questions = dataset["questions"]

    def relevant(q: int, c: int) -> bool:
        document, start, end, _ = chunks[c]
        return document == questions[q]["document"] and covers((start, end), questions[q]["answer_spans"])

    return {
        "label": f"{len(questions)} questions, {len(chunks)} chunks",
        "results": evaluate_methods(
            embed_query([q["question"] for q in questions]), embed_documents([c[3] for c in chunks]),
            [c[3] for c in chunks], [q["question"] for q in questions], relevant,
        ),
    }


def pdf_cases(db_path: str, document_name: str, model: str, how_many: int = 150, seed: int = 0) -> list[dict]:
    """Questions copied from a question bank in the database; the vectors stored by the app are used as they are."""
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)  # read-only: nothing in the database changes
    rows = connection.execute(
        "select c.content, c.embedding from document_chunks c join documents d on d.id = c.document_id "
        "where d.original_name = ? order by c.id", (document_name,),
    ).fetchall()
    if not rows:
        raise SystemExit(f"no chunks found for the document {document_name!r} in {db_path}")
    texts = [r[0] for r in rows]
    vectors = [json.loads(r[1]) for r in rows]

    stems = sorted({m.group(1).strip() for t in texts for m in STEM.finditer(t) if 15 <= len(m.group(1).strip()) <= 200})
    rng = np.random.default_rng(seed)
    stems = [stems[i] for i in rng.permutation(len(stems))[:how_many]]
    _, embed_query = load_embedder(model)

    cases = []
    for label, make in [("the whole question", lambda s: s), ("only the first half of the question", lambda s: s[: len(s) // 2])]:
        asked = [make(s) for s in stems]
        # right: a chunk that holds the complete question (the half is cut from it, so it is inside too)
        cases.append({
            "label": f"{label}: {len(stems)} questions from {document_name}, {len(texts)} chunks",
            "results": evaluate_methods(
                embed_query(asked), vectors, texts, asked, lambda q, c, stems=stems: stems[q] in texts[c]
            ),
        })
    return cases


def render(case: dict) -> str:
    lines = [
        f"### {case['label']}",
        "",
        "| search | hit@1 | hit@4 | MRR | vs meaning: found / lost (hit@4) | sign test p |",
        "|---|---|---|---|---|---|",
    ]
    for name, r in case["results"].items():
        versus = "-" if name == METHODS[0] else f"+{r['gained']} / -{r['lost']}"
        p = "-" if name == METHODS[0] else f"{r['p']:.3f}"
        lines.append(f"| {name} | {r['hit_at_1'] * 100:.0f}% | {r['hit_at_k'] * 100:.0f}% | {r['mrr']:.2f} | {versus} | {p} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", choices=["wikiqa-yue", "drcd", "pdf"], default="wikiqa-yue")
    parser.add_argument("--model", default=settings.embedding_model)
    parser.add_argument("--max-questions", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--db", default="app.db", help="pdf: the database to read (opened read-only)")
    parser.add_argument("--document", default="Download.ashx.pdf", help="pdf: original name of the uploaded document")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    if args.dataset == "pdf":
        cases = pdf_cases(args.db, args.document, args.model, seed=args.seed)
    else:
        builder = drcd if args.dataset == "drcd" else wikiqa
        rows = drcd.download_rows("dev") if args.dataset == "drcd" else wikiqa.download_rows("yue")
        cases = [span_case(builder.build_span_dataset(rows, max_questions=args.max_questions, seed=args.seed), args.model)]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    saved = [{"label": c["label"], "results": {n: {k: v for k, v in r.items() if k != "hits"} for n, r in c["results"].items()}} for c in cases]
    (RESULTS_DIR / f"hybrid_{args.dataset}.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"# Hybrid search comparison ({args.dataset}, model {args.model}, {time.perf_counter() - started:.0f}s)\n")
    for case in cases:
        print(render(case))


if __name__ == "__main__":
    main()
