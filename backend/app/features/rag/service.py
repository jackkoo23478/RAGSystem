import re
import time
from dataclasses import dataclass

from app.features.ingestion.pipeline.embedder import embed_texts
from app.features.rag.llm import LLMError
from app.features.rag.prompt import NO_ANSWER_TEXT, build_prompt
from app.features.rag.repository import create_query
from app.features.rag.retrieval import search_chunks


@dataclass
class CitationOut:
    number: int  # the [n] used in the answer
    document_id: int
    document_name: str
    page_number: int | None
    snippet: str
    score: float


@dataclass
class RagResult:
    query_id: int
    status: str  # answered / no_evidence / invalid_answer
    answer: str | None  # only set when status == "answered"
    citations: list[CitationOut]


def extract_cited_numbers(answer: str, max_n: int) -> list[int]:
    numbers = []
    for match in re.findall(r"\[(\d+)\]", answer):
        n = int(match)
        if 1 <= n <= max_n and n not in numbers:
            numbers.append(n)
    return numbers


def is_refusal(answer: str) -> bool:
    return NO_ANSWER_TEXT in answer


def answer_question(db, user_id, question, llm, embed=embed_texts, top_k=4, min_score=0.3) -> RagResult:
    question = question.strip()
    if not question:
        raise ValueError("question must not be empty")

    started = time.perf_counter()

    def elapsed_ms() -> int:  # measured when the query is saved, so it covers search and model
        return int((time.perf_counter() - started) * 1000)

    chunks = search_chunks(db, embed([question])[0], top_k=top_k, min_score=min_score)

    if not chunks:  # nothing relevant: refuse without calling the LLM
        query = create_query(db, user_id, question, status="no_evidence", latency_ms=elapsed_ms())
        return RagResult(query_id=query.id, status="no_evidence", answer=None, citations=[])

    try:
        answer = llm.generate(build_prompt(question, chunks))
    except LLMError:
        create_query(db, user_id, question, status="failed", latency_ms=elapsed_ms())
        raise

    if is_refusal(answer):
        query = create_query(db, user_id, question, status="no_evidence", answer=answer, latency_ms=elapsed_ms())
        return RagResult(query_id=query.id, status="no_evidence", answer=None, citations=[])

    cited = extract_cited_numbers(answer, max_n=len(chunks))
    if not cited:  # no valid [n]: do not trust it, do not show it
        query = create_query(db, user_id, question, status="invalid_answer", answer=answer, latency_ms=elapsed_ms())
        return RagResult(query_id=query.id, status="invalid_answer", answer=None, citations=[])

    used = [(n, chunks[n - 1]) for n in cited]  # [n] in the answer is chunks[n - 1] in the prompt
    rows = [
        dict(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            document_name=chunk.document_name,
            page_number=chunk.page_number,
            snippet=chunk.content[:300],
            score=chunk.score,
        )
        for _, chunk in used
    ]
    query = create_query(
        db, user_id, question, status="answered", answer=answer, citations=rows, latency_ms=elapsed_ms()
    )
    citations = [
        CitationOut(
            number=n,
            document_id=chunk.document_id,
            document_name=chunk.document_name,
            page_number=chunk.page_number,
            snippet=chunk.content[:300],
            score=chunk.score,
        )
        for n, chunk in used
    ]
    return RagResult(query_id=query.id, status="answered", answer=answer, citations=citations)