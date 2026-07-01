from __future__ import annotations

from functools import lru_cache
import re

try:
    import chromadb
except Exception:
    chromadb = None

import pandas as pd

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

from config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL, PROCESSED_DIR


@lru_cache(maxsize=1)
def get_model():
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers is not installed")
    return SentenceTransformer(EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def get_collection():
    if chromadb is None:
        raise RuntimeError("chromadb is not installed")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


def _query_terms(query: str) -> set[str]:
    stopwords = {"the", "and", "or", "of", "to", "in", "for", "with", "what", "should", "would", "today", "why", "how", "if", "were", "you", "as"}
    terms = re.findall(r"[a-zA-Z0-9]+", query.lower())
    return {term for term in terms if len(term) > 2 and term not in stopwords}


def fallback_keyword_retrieve(query: str, n_results: int = 8) -> list[dict]:
    """Fallback retrieval if ChromaDB has not been built yet.

    This keeps the demo usable. ChromaDB semantic retrieval is still the intended
    RAG method, but keyword fallback prevents a dramatic classroom tragedy.
    """
    chunks_file = PROCESSED_DIR / "chunks.csv"
    if not chunks_file.exists():
        return []

    df = pd.read_csv(chunks_file).fillna("")
    terms = _query_terms(query)
    if not terms:
        return []

    scored = []
    for _, row in df.iterrows():
        text = str(row.get("chunk", ""))
        text_l = text.lower()
        score = sum(text_l.count(term) for term in terms)
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    items: list[dict] = []
    for score, row in scored[:n_results]:
        items.append(
            {
                "text": str(row.get("chunk", "")),
                "metadata": {
                    "doc_id": str(row.get("doc_id", "")),
                    "chunk_id": str(row.get("chunk_id", "")),
                    "title": str(row.get("title", "")),
                    "source": str(row.get("source", "")),
                    "source_category": str(row.get("source_category", "")),
                    "url": str(row.get("url", "")),
                    "published": str(row.get("published", "")),
                    "chunk_no": int(row.get("chunk_no", 0)),
                },
                "distance": 1 / (score + 1),
                "similarity": round(score / (score + 5), 4),
                "query": query,
                "retrieval_method": "keyword_fallback",
            }
        )
    return items


def retrieve_documents(query: str, n_results: int = 8, where: dict | None = None) -> list[dict]:
    if chromadb is None or SentenceTransformer is None:
        return fallback_keyword_retrieve(query, n_results=n_results)
    if not CHROMA_DIR.exists() or not any(CHROMA_DIR.iterdir()):
        return fallback_keyword_retrieve(query, n_results=n_results)

    try:
        model = get_model()
        collection = get_collection()
        query_embedding = model.encode([query], normalize_embeddings=True).tolist()[0]

        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        results = collection.query(**query_kwargs)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        items: list[dict] = []
        for doc, meta, distance in zip(documents, metadatas, distances):
            items.append(
                {
                    "text": doc,
                    "metadata": meta,
                    "distance": float(distance),
                    "similarity": round(1 / (1 + float(distance)), 4),
                    "query": query,
                    "retrieval_method": "chroma_semantic",
                }
            )
        return items
    except Exception:
        return fallback_keyword_retrieve(query, n_results=n_results)


def retrieve_multi_query(queries: list[str], n_per_query: int = 5) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []

    for query in queries:
        for item in retrieve_documents(query, n_results=n_per_query):
            key = str(item["metadata"].get("chunk_id") or item["metadata"].get("doc_id") or item["text"][:80])
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

    merged.sort(key=lambda item: item.get("similarity", 0), reverse=True)
    return merged


def format_evidence(items: list[dict], max_chars: int = 8000) -> str:
    blocks: list[str] = []
    used = 0

    for idx, item in enumerate(items, start=1):
        meta = item["metadata"]
        block = (
            f"Evidence {idx}\n"
            f"Title: {meta.get('title', '')}\n"
            f"Source: {meta.get('source', '')}\n"
            f"Category: {meta.get('source_category', '')}\n"
            f"Date: {meta.get('published', '')}\n"
            f"URL: {meta.get('url', '')}\n"
            f"Similarity: {item.get('similarity', '')}\n"
            f"Text: {item['text']}"
        )
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)

    return "\n\n".join(blocks)
