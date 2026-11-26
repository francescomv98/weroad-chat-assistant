from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import threading
from collections.abc import Callable, Sequence
from pathlib import Path

from .config import settings
from .data import SAMPLES_DIR, Faq
from .llm import LLMProviderError

log = logging.getLogger(__name__)

EmbedFn = Callable[[list[str]], tuple[list[list[float]], int]]

_client = None


def openai_embed(texts: list[str]) -> tuple[list[list[float]], int]:
    import openai

    global _client
    try:
        if _client is None:
            _client = openai.OpenAI(timeout=30.0)
        resp = _client.embeddings.create(model=settings.embedding_model, input=texts)
    except openai.AuthenticationError as e:
        raise LLMProviderError(500, "OpenAI API key invalid: check OPENAI_API_KEY in .env") from e
    except openai.OpenAIError as e:
        raise LLMProviderError(502, f"Embedding request failed: {e}") from e
    return [d.embedding for d in resp.data], resp.usage.total_tokens


# "for a WeRoad trip", "on the trip", "WeRoad's": every FAQ is about WeRoad trips, so these words make
# all FAQs look alike and push the right one down. The model adds them in ~2 of 5 queries even when the
# tool description says not to (eval 20261125-114357), so they are removed here. On the 203 queries of
# that run, right FAQ in the top 3: 200 -> 203.
_GENERIC_WORDS = re.compile(
    r"\b(?:on|for|in|during|of|with)\s+(?:a|an|the|my|your|our)?\s*(?:weroad\s+)?trips?\b|\bweroad(?:'s|’s)?\b",
    re.IGNORECASE,
)


def clean_query(query: str) -> str:
    cleaned = _GENERIC_WORDS.sub(" ", query)
    cleaned = re.sub(r"\s+([?.!,])", r"\1", re.sub(r"\s{2,}", " ", cleaned)).strip()
    return cleaned if len(cleaned.split()) >= 2 else query


def faq_document(faq: Faq) -> str:
    where = f"Destination: {faq.destination}\n" if faq.destination else ""
    return f"{faq.title}\n{where}{faq.body}"


def _normalise(v: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


_vector_cache: dict[tuple, list[list[float]]] = {}
_cache_lock = threading.Lock()

# Written by the ingestion step (`python -m app.faq_ingest`), committed, and shipped in the Docker image.
VECTORS_PATH = SAMPLES_DIR / "faq_vectors.json"


def documents_hash(docs: Sequence[str], model: str) -> str:
    """Identifies what the vectors were computed from: any change to a FAQ, to how a FAQ becomes a document
    (`faq_document`) or to the model gives a different hash, so an outdated file is never used."""
    h = hashlib.sha256(model.encode())
    for d in docs:
        h.update(b"\0" + d.encode())
    return h.hexdigest()


def load_vectors(path: Path, docs: Sequence[str], model: str) -> list[list[float]] | None:
    """The vectors in `path` if they were computed from exactly these documents with this model, else None."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log.info("FAQ vectors: %s not found, computing them (run python -m app.faq_ingest)", path.name)
        return None
    except (OSError, ValueError) as e:
        log.warning("FAQ vectors: %s unreadable (%s), computing them", path.name, e)
        return None
    if data.get("model") != model or data.get("documents_sha256") != documents_hash(docs, model):
        # The FAQs changed (or the model) without a new ingestion: the old vectors would rank the wrong FAQs.
        log.warning("FAQ vectors: %s is out of date, computing them (run python -m app.faq_ingest)", path.name)
        return None
    return data["vectors"]


class FaqEmbeddingIndex:
    def __init__(self, faqs: Sequence[Faq], embed: EmbedFn | None = None,
                 top_k: int = 3, min_similarity: float | None = None, vectors_path: Path | None = None) -> None:
        self.faqs = tuple(faqs)
        self.embed = embed or openai_embed
        # The ingested file holds OpenAI vectors: by default it is used only with the OpenAI embeddings, so
        # an index with another `embed` (the tests' fake) never mixes its query vectors with those.
        self.vectors_path = vectors_path if vectors_path is not None else (VECTORS_PATH if embed is None else None)
        self.top_k = top_k
        self.min_similarity = settings.faq_min_similarity if min_similarity is None else min_similarity

    def vectors(self) -> list[list[float]]:
        docs = tuple(faq_document(f) for f in self.faqs)
        model = settings.embedding_model
        key = (self.embed, model, docs, self.vectors_path)
        with _cache_lock:
            if key not in _vector_cache:
                ingested = load_vectors(self.vectors_path, docs, model) if self.vectors_path else None
                if ingested is None:
                    vectors, _tokens = self.embed(list(docs))
                    ingested = [_normalise(v) for v in vectors]
                _vector_cache[key] = ingested

            return _vector_cache[key]

    def search(self, query: str) -> tuple[list[tuple[Faq, float]], int]:
        """FAQs most similar to `query` (best first, at most top_k, above the cut-off) and the tokens used."""
        doc_vectors = self.vectors()
        [q], tokens = self.embed([clean_query(query)])
        q = _normalise(q)
        # strict: a vector per FAQ and the same dimensions everywhere; a mismatch is a bug, not a shorter list
        scored = [
            (faq, sum(a * b for a, b in zip(q, v, strict=True)))
            for faq, v in zip(self.faqs, doc_vectors, strict=True)
        ]
        scored.sort(key=lambda x: -x[1])

        return [(f, s) for f, s in scored[: self.top_k] if s >= self.min_similarity], tokens
