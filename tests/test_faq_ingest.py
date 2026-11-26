import json
import logging

import pytest

from app.config import settings
from app.data import load_catalog
from app.faq_embeddings import (
    VECTORS_PATH,
    FaqEmbeddingIndex,
    documents_hash,
    faq_document,
)
from app.faq_ingest import write_vectors
from tests.test_assistant import fake_embed


def counting(embed):
    calls = []

    def wrapped(texts):
        calls.append(len(texts))
        return embed(texts)

    return wrapped, calls


def test_the_committed_vectors_match_the_faqs():
    """CI check, no API key: fails when faqs.json (or the embedding model) changed without a new ingestion.
    The real samples/faqs.json, not the `catalog` fixture, which has its own test FAQs."""
    if not VECTORS_PATH.exists():
        pytest.fail(f"{VECTORS_PATH.name} is missing: run python -m app.faq_ingest and commit it")
    faqs = load_catalog().faqs
    data = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    docs = [faq_document(f) for f in faqs]
    assert data["model"] == settings.embedding_model, "run python -m app.faq_ingest and commit the file"
    assert data["documents_sha256"] == documents_hash(docs, data["model"]), (
        "faqs.json changed since the last ingestion: run python -m app.faq_ingest and commit the file")
    assert len(data["vectors"]) == len(faqs)
    assert len({len(v) for v in data["vectors"]}) == 1  # every vector has the same dimensions


def test_the_index_uses_the_ingested_vectors_without_embedding_the_faqs(catalog, tmp_path):
    path = tmp_path / "faq_vectors.json"
    write_vectors(catalog.faqs, fake_embed, path, settings.embedding_model)
    embed, calls = counting(fake_embed)
    index = FaqEmbeddingIndex(catalog.faqs, embed, min_similarity=0.5, vectors_path=path)

    results, _ = index.search("Visa for Japan?")

    assert calls == [1]  # only the question was embedded, not the 50 FAQs
    assert "visa" in results[0][0].title.lower()


def test_outdated_vectors_are_not_used(catalog, tmp_path, caplog):
    path = tmp_path / "faq_vectors.json"
    write_vectors(catalog.faqs[:-1], fake_embed, path, settings.embedding_model)  # a FAQ added since
    embed, calls = counting(fake_embed)
    caplog.set_level(logging.WARNING, logger="app.faq_embeddings")

    vectors = FaqEmbeddingIndex(catalog.faqs, embed, vectors_path=path).vectors()

    assert calls == [len(catalog.faqs)]  # computed again, as without ingestion
    assert len(vectors) == len(catalog.faqs)
    assert any("out of date" in r.getMessage() for r in caplog.records)


def test_vectors_from_another_model_are_not_used(catalog, tmp_path):
    path = tmp_path / "faq_vectors.json"
    write_vectors(catalog.faqs, fake_embed, path, "another-embedding-model")
    embed, calls = counting(fake_embed)

    FaqEmbeddingIndex(catalog.faqs, embed, vectors_path=path).vectors()

    assert calls == [len(catalog.faqs)]


def test_without_the_file_the_faqs_are_embedded_at_startup(catalog, tmp_path):
    embed, calls = counting(fake_embed)

    FaqEmbeddingIndex(catalog.faqs, embed, vectors_path=tmp_path / "missing.json").vectors()

    assert calls == [len(catalog.faqs)]


def test_an_index_with_its_own_embed_function_ignores_the_ingested_file(catalog):
    # The committed file holds OpenAI vectors: mixing them with another embedder's query vectors is wrong.
    assert FaqEmbeddingIndex(catalog.faqs, fake_embed).vectors_path is None
    assert FaqEmbeddingIndex(catalog.faqs).vectors_path == VECTORS_PATH
