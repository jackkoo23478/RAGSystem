"""Load an embedding model by its Hugging Face name, for trying models other than the one the app uses."""
from app.features.ingestion.pipeline.embedder import MODEL_NAME, embed_texts


def prefixes_for(model_name: str) -> tuple[str, str]:
    """(document prefix, question prefix). The E5 models were trained with these and score worse without them."""
    if "e5" in model_name.lower():
        return "passage: ", "query: "
    return "", ""


def load_embedder(model_name: str):
    """Return (embed for documents, embed for questions). The app's own model is used as it is in production."""
    if model_name == MODEL_NAME:
        return embed_texts, embed_texts

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    doc_prefix, query_prefix = prefixes_for(model_name)

    def encoder(prefix: str):
        def embed(texts: list[str]) -> list[list[float]]:
            if not texts:
                return []
            return [v.tolist() for v in model.encode([prefix + t for t in texts])]

        return embed

    return encoder(doc_prefix), encoder(query_prefix)
