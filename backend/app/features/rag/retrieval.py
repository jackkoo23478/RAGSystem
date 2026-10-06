import numpy as np
import json
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.features.documents.models import Document, DocumentChunk


def rank_by_cosine(query, vectors, top_k=4, min_score=0.0):
    if not vectors:
        return []

    m = np.array(vectors, dtype=float)
    q = np.array(query, dtype=float)

    norms = np.linalg.norm(m, axis=1) * np.linalg.norm(q)
    norms[norms == 0] = 1

    scores = (m @ q) / norms

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
    
def search_chunks(db : Session , query_embedding , top_k = 4 , min_score = 0.3) :
    rows = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.status == "processed", DocumentChunk.embedding.isnot(None))
        .all()
    )
    
    vectors = [json.loads(chunk.embedding) for chunk, _ in rows]
    ranked = rank_by_cosine(query_embedding,vectors,top_k,min_score)
    
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