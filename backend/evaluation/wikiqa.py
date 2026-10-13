"""Cantonese retrieval test from multi-wiki-qa (the `yue` part): articles of the Cantonese Wikipedia, each with
questions written in Cantonese by an LLM (Gemini 1.5 Pro) and the answer text.

Source: https://huggingface.co/datasets/alexandrainst/multi-wiki-qa  (CC BY-NC-SA 4.0: non-commercial, share alike).
Because of that licence the data is downloaded from Hugging Face when needed and kept in evaluation/data/ (not committed).

Every article is cut into chunks with the app's own chunker. A chunk counts as relevant when it comes from the
question's article AND contains the answer text.
"""
import json
import random
from pathlib import Path

from app.features.ingestion.pipeline.chunker import chunk_pages
from evaluation.hub import fetch_page

DATA_DIR = Path(__file__).parent / "data"
DATASET = "alexandrainst/multi-wiki-qa"
MAX_RELEVANT_CHUNKS = 2  # an answer that appears in many chunks of its article makes the question too vague


def download_rows(config: str = "yue", split: str = "train", cache_dir: Path = DATA_DIR) -> list[dict]:
    path = cache_dir / f"multiwikiqa_{config}_{split}_v2.json"  # v2 also keeps where each answer starts
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    rows, offset = [], 0
    while True:
        page = fetch_page(DATASET, config, split, offset)
        for item in page["rows"]:
            row = item["row"]
            rows.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "context": row["context"],
                    "question": row["question"],
                    "answers": row["answers"]["text"],
                    "answer_starts": row["answers"]["answer_start"],
                }
            )
        offset += len(page["rows"])
        if not page["rows"] or offset >= page["num_rows_total"]:
            break

    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def build_dataset(rows: list[dict], max_questions: int = 500, seed: int = 0) -> dict:
    articles: dict[str, dict] = {}
    for row in rows:
        if row["id"] not in articles:
            articles[row["id"]] = {
                "file": f"{row['title']} #{len(articles)}",  # titles are not unique, the number makes the name unique
                "language": "yue",
                "text": row["context"],
            }

    chunks_of = {
        article_id: [text for _, text in chunk_pages([(None, article["text"])])]
        for article_id, article in articles.items()
    }

    candidates = []
    for index, row in enumerate(rows):
        answers = [a for a in dict.fromkeys(row["answers"]) if a.strip()]
        if not answers:
            continue
        holding = [c for c in chunks_of[row["id"]] if any(a in c for a in answers)]
        if not 1 <= len(holding) <= MAX_RELEVANT_CHUNKS:  # cut in two by the chunker, or too vague
            continue
        candidates.append(
            {
                "id": f"wikiqa-{index}",
                "group": "wiki-yue",
                "kind": "answerable",
                "question": row["question"],
                "document": articles[row["id"]]["file"],
                "same_document": True,
                "evidence": answers,
                "must_contain": [answers[:1]],
            }
        )

    if len(candidates) > max_questions:
        candidates = random.Random(seed).sample(sorted(candidates, key=lambda q: q["id"]), max_questions)
    return {"documents": list(articles.values()), "questions": candidates}


def build_span_dataset(rows: list[dict], max_questions: int = 500, seed: int = 0) -> dict:
    """The same articles and questions for every chunker: an answer is found when a chunk of the question's article
    covers the characters where the answer sits (answer_start .. answer_start + len), however the article was cut."""
    documents: dict[str, dict] = {}
    for row in rows:
        documents.setdefault(row["id"], {"id": row["id"], "title": row["title"], "text": row["context"]})

    questions = []
    for index, row in enumerate(rows):
        spans = sorted(
            {
                (start, start + len(text))
                for text, start in zip(row["answers"], row["answer_starts"])
                if text.strip() and row["context"][start:start + len(text)] == text  # the offset really points at the text
            }
        )
        if spans:
            questions.append(
                {"id": f"wikiqa-{index}", "question": row["question"], "document": row["id"], "answer_spans": spans}
            )

    if len(questions) > max_questions:
        questions = random.Random(seed).sample(questions, max_questions)
    return {"documents": list(documents.values()), "questions": questions}
