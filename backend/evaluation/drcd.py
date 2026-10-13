"""Use DRCD (Delta Reading Comprehension Dataset: Traditional Chinese questions about Wikipedia articles) as a
bigger retrieval test: the paragraphs are the collection, a question should find the paragraph it was written from.

Source: https://huggingface.co/datasets/voidful/DRCD (CC BY 3.0 on the Hub; the DRCD authors publish it under CC BY-SA 3.0).
The rows are downloaded once from the Hugging Face dataset viewer API and kept in evaluation/data/ (not committed).
"""
import json
import random
from pathlib import Path

from evaluation.hub import fetch_page

DATA_DIR = Path(__file__).parent / "data"
CANTONESE_FILE = Path(__file__).parent / "dataset" / "drcd_cantonese.json"
DATASET = "voidful/DRCD"


def download_rows(split: str = "dev", cache_dir: Path = DATA_DIR) -> list[dict]:
    """The articles of one split ("dev" or "test"), downloaded once and then read from disk."""
    path = cache_dir / f"drcd_{split}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    rows, offset = [], 0
    while True:
        page = fetch_page(DATASET, "default", split, offset)
        rows += [item["row"] for item in page["rows"]]
        offset += len(page["rows"])
        if not page["rows"] or offset >= page["num_rows_total"]:
            break

    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def build_dataset(rows: list[dict], max_questions: int = 300, seed: int = 0) -> dict:
    """Same shape as evaluation/dataset: every article is a document whose chunks are its paragraphs, and a question
    is relevant to the chunk that holds the paragraph it came from (the paragraph text is the evidence)."""
    documents, candidates = [], []
    for article in rows:
        paragraphs = article["paragraphs"]
        documents.append(
            {
                "file": f"{article['title']} ({article['id']})",
                "language": "zh",
                "chunks": [p["context"] for p in paragraphs],
                "text": "\n".join(p["context"] for p in paragraphs),
            }
        )
        for paragraph in paragraphs:
            for qa in paragraph["qas"]:
                answers = [a["text"] for a in qa["answers"] if a["text"]]
                candidates.append(
                    {
                        "id": f"drcd-{qa['id']}",
                        "group": "drcd-zh",
                        "kind": "answerable",
                        "question": qa["question"],
                        "document": f"{article['title']} ({article['id']})",
                        "evidence": [paragraph["context"]],
                        "must_contain": [answers[:1]] if answers else [],
                    }
                )

    candidates.sort(key=lambda q: q["id"])  # a fixed order, so the same seed always picks the same questions
    if len(candidates) > max_questions:
        candidates = random.Random(seed).sample(candidates, max_questions)
    return {"documents": documents, "questions": candidates}


def load_cantonese_rewrites(path: Path = CANTONESE_FILE) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))["rewrites"]


def with_cantonese(dataset: dict, rewrites: dict[str, str]) -> dict:
    """Keep only the questions that have a Cantonese rewrite, and ask each one twice: as DRCD wrote it
    (group "written") and in colloquial Cantonese (group "cantonese"). Same passages, same answers, so any
    difference between the two groups comes from the wording of the question."""
    questions = []
    for q in dataset["questions"]:
        if q["id"] in rewrites:
            questions.append({**q, "group": "written"})
            questions.append({**q, "id": q["id"] + "-yue", "group": "cantonese", "question": rewrites[q["id"]]})
    return {"documents": dataset["documents"], "questions": questions}


def build_span_dataset(rows: list[dict], max_questions: int = 400, seed: int = 0) -> dict:
    """Whole articles (the paragraphs joined by a blank line) instead of ready-made paragraphs, so a chunker has to
    decide where to cut. An answer is found when a chunk of the question's article covers the characters of the answer."""
    documents, questions = [], []
    for article in rows:
        text, offset = "", 0
        for paragraph in article["paragraphs"]:
            if text:
                text += "\n\n"
            offset = len(text)
            text += paragraph["context"]
            for qa in paragraph["qas"]:
                spans = sorted(
                    {
                        (offset + a["answer_start"], offset + a["answer_start"] + len(a["text"]))
                        for a in qa["answers"]
                        if a["text"] and paragraph["context"][a["answer_start"]:a["answer_start"] + len(a["text"])] == a["text"]
                    }
                )
                if spans:
                    questions.append(
                        {"id": f"drcd-{qa['id']}", "question": qa["question"], "document": article["id"], "answer_spans": spans}
                    )
        documents.append({"id": article["id"], "title": article["title"], "text": text})

    questions.sort(key=lambda q: q["id"])
    if len(questions) > max_questions:
        questions = random.Random(seed).sample(questions, max_questions)
    return {"documents": documents, "questions": questions}
