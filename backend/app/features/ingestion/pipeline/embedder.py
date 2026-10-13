import torch
from sentence_transformers import SentenceTransformer

from app.core.config import settings

# Set by EMBEDDING_MODEL. Changing it changes the vectors, so run `python -m scripts.rebuild_index` afterwards.
MODEL_NAME = settings.embedding_model
_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        # half precision on the GPU: 1.1 GB instead of 2.2. Measured on 500 + 500 questions: the same hit rate, and the vectors
        # are 0.9999 similar to the full precision ones, so vectors stored earlier stay valid
        half = {"model_kwargs": {"torch_dtype": torch.float16}} if torch.cuda.is_available() else {}
        _model = SentenceTransformer(MODEL_NAME, **half)
    return _model

def embed_texts(texts : list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_model()
    embeddings = model.encode(texts)
    return [v.tolist() for v in embeddings]
