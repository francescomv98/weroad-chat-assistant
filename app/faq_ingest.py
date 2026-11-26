"""Ingestion: `python -m app.faq_ingest` embeds the FAQs once and writes samples/faq_vectors.json,
so the server doesn't embed them at every start. Run it after changing samples/faqs.json."""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from .config import settings
from .data import Faq, get_catalog
from .faq_embeddings import (
    VECTORS_PATH,
    EmbedFn,
    _normalise,
    documents_hash,
    faq_document,
    openai_embed,
)

# Unit vectors have components well below 1: 6 decimals change a cosine similarity by ~1e-5, far below the
# gaps between FAQs, and halve the file.
_DECIMALS = 6


def write_vectors(faqs: Sequence[Faq], embed: EmbedFn, path: Path, model: str) -> int:
    """Embed the FAQs, write them to `path` and return the tokens used."""
    docs = [faq_document(f) for f in faqs]
    vectors, tokens = embed(docs)
    rows = [[round(x, _DECIMALS) for x in _normalise(v)] for v in vectors]
    # One vector per line: a FAQ edit shows up in the diff as the lines that changed, not one huge line.
    lines = ",\n".join(f"    {json.dumps(r, separators=(',', ':'))}" for r in rows)
    path.write_text(
        "{\n"
        f'  "model": {json.dumps(model)},\n'
        f'  "documents_sha256": {json.dumps(documents_hash(docs, model))},\n'
        f'  "faq_titles": {json.dumps([f.title for f in faqs], ensure_ascii=False)},\n'
        f'  "vectors": [\n{lines}\n  ]\n'
        "}\n",
        encoding="utf-8"
    )
    return tokens


def main() -> None:
    faqs = get_catalog().faqs
    tokens = write_vectors(faqs, openai_embed, VECTORS_PATH, settings.embedding_model)
    print(f"{len(faqs)} FAQs embedded with {settings.embedding_model} ({tokens} tokens) -> {VECTORS_PATH}")


if __name__ == "__main__":
    main()
