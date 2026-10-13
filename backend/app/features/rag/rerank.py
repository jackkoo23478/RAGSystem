import torch
from sentence_transformers import CrossEncoder

from app.core.config import settings

_model = None


def get_model() -> CrossEncoder:
    global _model
    if _model is None:
        on_gpu = torch.cuda.is_available()
        # half precision on the GPU: 1.1 GB instead of 2.2, and the same order of passages
        _model = CrossEncoder(
            settings.rerank_model,
            device="cuda" if on_gpu else "cpu",
            max_length=512,
            model_kwargs={"torch_dtype": torch.float16} if on_gpu else {},
        )
    return _model


def rerank_scores(question: str, passages: list[str]) -> list[float]:
    """How well each passage answers the question (higher is better). Unlike the search, which compares two separate vectors,
    this model reads the question and the passage together, so it is slower (about 0.15 s for 10 passages) and more exact."""
    if not passages:
        return []
    scores = get_model().predict([(question, p) for p in passages], batch_size=len(passages), show_progress_bar=False)
    return [float(s) for s in scores]
