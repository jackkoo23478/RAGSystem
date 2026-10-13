import numpy as np
import json
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.features.documents.models import Document, DocumentChunk
from app.features.rag.keyword import BM25, reciprocal_rank_fusion, tokenize


def cosine_scores(query, vectors):
    """The cosine similarity of the query with every vector."""
    m = np.array(vectors, dtype=float)
    q = np.array(query, dtype=float)

    norms = np.linalg.norm(m, axis=1) * np.linalg.norm(q)
    norms[norms == 0] = 1

    return (m @ q) / norms


def rank_by_cosine(query, vectors, top_k=4, min_score=0.0):
    if not vectors:
        return []

    scores = cosine_scores(query, vectors)

    order = np.argsort(scores)[::-1][:top_k]
    return [(int(i), float(scores[i])) for i in order if scores[i] >= min_score]


@dataclass
class RetrievedChunk :
    chunk_id : int
    document_id : int
    document_name : str
    page_number : int | None
    chunk_index : int
    content : str
    score : float

class EmbeddingMismatchError(Exception):
    """The stored vectors were made by a different embedding model than the one that embedded the question."""


_keyword_index_cache: tuple[int, BM25] | None = None


def keyword_index(texts: list[str]) -> BM25:
    """The BM25 index of these chunk texts. Building it takes a moment, so the last one is kept and used again for as long as
    the texts are the same (it changes when a document is uploaded, deleted or cut again)."""
    global _keyword_index_cache
    key = hash(tuple(texts))
    if _keyword_index_cache is None or _keyword_index_cache[0] != key:
        _keyword_index_cache = (key, BM25([tokenize(t) for t in texts]))
    return _keyword_index_cache[1]


def rank_hybrid(query, vectors, texts, query_text, top_k=4, min_score=0.3):
    """Meaning and keywords together. Returns (index, cosine similarity) of the best chunks.

    The threshold works on the whole question, as before: when not even the best chunk is similar enough in meaning, nothing
    is relevant and nothing is returned. Past that, the chunks are ranked by the meaning ranking and the keyword ranking merged
    (reciprocal rank fusion), so a chunk that uses the words of the question moves up even if its meaning score is modest."""
    if not vectors:
        return []
    meaning = cosine_scores(query, vectors)
    if meaning.max() < min_score:
        return []
    keywords = keyword_index(texts).scores(tokenize(query_text))
    fused = reciprocal_rank_fusion([meaning[None, :], keywords[None, :]])[0]
    order = np.argsort(-fused, kind="stable")[:top_k]
    return [(int(i), float(meaning[i])) for i in order]


def search_chunks(db : Session , query_embedding , top_k = 4 , min_score = 0.3, query_text = None, rerank = None, candidates = None) :
    """The best chunks of the processed documents for a question. With query_text (the question as written) the search is
    hybrid: meaning and keywords. Without it, by meaning only.

    rerank (question, passages) -> scores puts the search results in a better order: the search takes `candidates` chunks, the
    reranker scores them, and the best top_k are kept. It needs query_text, and a chunk's score stays its cosine similarity."""
    rows = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.status == "processed", DocumentChunk.embedding.isnot(None))
        .all()
    )

    vectors = [json.loads(chunk.embedding) for chunk, _ in rows]
    if any(len(vector) != len(query_embedding) for vector in vectors):
        raise EmbeddingMismatchError(
            f"The question has {len(query_embedding)} dimensions but some stored chunks have a different number. "
            "The embedding model was changed: run  python -m scripts.rebuild_index"
        )
    if query_text is None:
        ranked = rank_by_cosine(query_embedding,vectors,top_k,min_score)
    else:
        pool = max(candidates or top_k, top_k) if rerank else top_k
        ranked = rank_hybrid(query_embedding, vectors, [chunk.content for chunk, _ in rows], query_text, pool, min_score)
        if rerank and len(ranked) > 1:
            scores = rerank(query_text, [rows[index][0].content for index, _ in ranked])
            best_first = sorted(range(len(ranked)), key=lambda k: -scores[k])  # a stable sort: equal scores keep the search order
            ranked = [ranked[k] for k in best_first[:top_k]]

    results = []

    for index, score in ranked:
        chunk, document = rows[index]
        results.append(RetrievedChunk(
            chunk_id=chunk.id,
            document_id=document.id,
            document_name=document.original_name,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            score=score,
        ))
    return results
