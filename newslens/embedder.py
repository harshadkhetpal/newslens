"""Local embedding service — sentence-transformers, loaded once per process."""

from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from . import config


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(config.EMBEDDING_MODEL)


def embed(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts; vectors are L2-normalised so cosine == dot."""
    vectors = _model().encode(
        texts, normalize_embeddings=True, show_progress_bar=False
    )
    return [v.tolist() for v in vectors]


def embed_one(text: str) -> List[float]:
    return embed([text])[0]
