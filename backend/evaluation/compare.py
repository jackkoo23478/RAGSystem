"""Compare embedding models on the same questions (retrieval only: no LLM, so it is fast and repeatable).

    python -m evaluation.compare
    python -m evaluation.compare intfloat/multilingual-e5-small BAAI/bge-m3

Models are downloaded from Hugging Face the first time. Different models score on different scales (a good match is
0.4 for one and 0.8 for another), so each model is also shown at its own best min_score.
"""
import argparse
import json
import time

from evaluation import metrics, wikiqa
from evaluation.drcd import build_dataset, download_rows, load_cantonese_rewrites, with_cantonese
from evaluation.embedders import load_embedder
from evaluation.run import RESULTS_DIR, load_dataset, run_evaluation

DEFAULT_MODELS = [
    "all-MiniLM-L6-v2",  # what the app used before bge-m3
    "paraphrase-multilingual-MiniLM-L12-v2",
    "intfloat/multilingual-e5-small",
    "BAAI/bge-m3",
]

def best_threshold(details: list[dict]) -> dict:
    """The min_score that keeps most answerable questions AND rejects most unanswerable ones.

    Balanced score = (answerable found + unanswerable rejected) / 2, so a threshold that refuses everything
    (or accepts everything) cannot win. The lowest threshold wins a tie, because a lower one refuses fewer real questions.
    """
    answerable = [d for d in details if d["kind"] == "answerable"]
    unanswerable = [d for d in details if d["kind"] == "unanswerable"]
    best = None
    for step in range(0, 100):
        threshold = step / 100
        found = metrics.rate([d["rank"] is not None and d["scores"][d["rank"] - 1] >= threshold for d in answerable])
        false_evidence = metrics.rate([bool(d["scores"]) and d["scores"][0] >= threshold for d in unanswerable])
        if found is None or false_evidence is None:
            continue
        balanced = (found + (1 - false_evidence)) / 2
        if best is None or balanced > best["balanced"] + 1e-9:
            best = {"min_score": threshold, "found": found, "false_evidence": false_evidence, "balanced": balanced}
    return best


def _pct(value) -> str:
    return "-" if value is None else f"{value * 100:.0f}%"


def render_comparison(results: list[dict]) -> str:
    cfg = results[0]["report"]["config"]
    groups = sorted(results[0]["report"]["retrieval"]["by_group"])
    show_groups = len(groups) > 1
    header = "| model | hit@1 | hit@4 | MRR |"
    divider = "|---|---|---|---|"
    if show_groups:
        header += " " + " | ".join(f"hit@4 {g}" for g in groups) + " |"
        divider += "---|" * len(groups)
    lines = [
        "# Embedding model comparison (retrieval only)",
        "",
        f"{cfg['questions']} questions over {cfg['documents']} documents.",
        "",
        "## Ranking quality (independent of any threshold)",
        "",
        header + " time |",
        divider + "---|",
    ]
    for r in results:
        overall = r["report"]["retrieval"]["overall"]
        by_group = r["report"]["retrieval"]["by_group"]
        cells = ""
        if show_groups:
            cells = " | ".join(_pct(by_group.get(g, {}).get("hit_at_k")) for g in groups) + " | "
        lines.append(
            f"| {r['model']} | {_pct(overall['hit_at_1'])} | {_pct(overall['hit_at_k'])} | {overall['mrr']:.2f} | "
            f"{cells}{r['seconds']:.0f}s |"
        )
    lines += [
        "",
        "hit@4: the right passage is among the 4 passages sent to the LLM. "
        "`zh-en` is a Chinese question about an English document.",
    ]
    if all(r["best"] for r in results):
        lines += [
            "",
            "## At the model's own best min_score (the app's 0.3 only suits one scale)",
            "",
            "| model | best min_score | answerable questions found | unanswerable questions given evidence |",
            "|---|---|---|---|",
        ]
        for r in results:
            b = r["best"]
            lines.append(f"| {r['model']} | {b['min_score']:.2f} | {_pct(b['found'])} | {_pct(b['false_evidence'])} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("models", nargs="*", default=DEFAULT_MODELS)
    parser.add_argument("--dataset", choices=["handwritten", "drcd", "drcd-yue", "wikiqa-yue"], default="handwritten",
                        help="drcd: Traditional Chinese Wikipedia questions, downloaded once from Hugging Face. "
                             "drcd-yue: 60 of them asked twice, as written and in Cantonese. "
                             "wikiqa-yue: Cantonese Wikipedia articles with Cantonese questions (multi-wiki-qa)")
    parser.add_argument("--split", default="dev", help="DRCD split: dev or test")
    parser.add_argument("--max-questions", type=int, default=300, help="DRCD: how many questions to sample")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    if args.dataset == "wikiqa-yue":
        dataset = wikiqa.build_dataset(wikiqa.download_rows("yue"), max_questions=args.max_questions, seed=args.seed)
    elif args.dataset == "drcd-yue":
        everything = build_dataset(download_rows(args.split), max_questions=10**9)
        dataset = with_cantonese(everything, load_cantonese_rewrites())
    elif args.dataset == "drcd":
        dataset = build_dataset(download_rows(args.split), max_questions=args.max_questions, seed=args.seed)
    else:
        dataset = load_dataset()
    results = []
    for name in args.models:
        print(f"... {name}", flush=True)
        started = time.perf_counter()
        embed, embed_query = load_embedder(name)
        report = run_evaluation(dataset, embed=embed, embed_query=embed_query, embedder_name=name)
        results.append(
            {
                "model": name,
                "report": report,
                "best": best_threshold(report["retrieval"]["details"]),
                "seconds": time.perf_counter() - started,
            }
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"compare_{args.dataset}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(render_comparison(results))


if __name__ == "__main__":
    main()
