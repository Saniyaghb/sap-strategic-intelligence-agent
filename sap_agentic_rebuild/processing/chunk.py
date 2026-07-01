from __future__ import annotations

import re

import pandas as pd

from config import PROCESSED_DIR


def split_into_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def get_overlap_sentences(sentences: list[str], overlap_chars: int) -> list[str]:
    if not sentences or overlap_chars <= 0:
        return []
    overlap: list[str] = []
    total = 0
    for sentence in reversed(sentences):
        if overlap and total + len(sentence) > overlap_chars:
            break
        overlap.insert(0, sentence)
        total += len(sentence)
    return overlap


def split_long_sentence(sentence: str, chunk_size: int) -> list[str]:
    words = sentence.split()
    pieces: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    text = str(text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_length = 0

    for sentence in split_into_sentences(text):
        if len(sentence) > chunk_size:
            if current_sentences:
                chunks.append(" ".join(current_sentences).strip())
                current_sentences = []
                current_length = 0
            chunks.extend(split_long_sentence(sentence, chunk_size))
            continue

        if current_sentences and current_length + len(sentence) > chunk_size:
            chunks.append(" ".join(current_sentences).strip())
            current_sentences = get_overlap_sentences(current_sentences, overlap)
            current_length = sum(len(s) for s in current_sentences)

        current_sentences.append(sentence)
        current_length += len(sentence)

    if current_sentences:
        chunks.append(" ".join(current_sentences).strip())

    return chunks


def create_chunks(chunk_size: int = 900, overlap: int = 150) -> pd.DataFrame:
    input_file = PROCESSED_DIR / "master_data.csv"
    if not input_file.exists():
        raise FileNotFoundError("master_data.csv not found. Run: python processing/clean.py")

    df = pd.read_csv(input_file).fillna("")
    rows: list[dict] = []

    for _, row in df.iterrows():
        base_text = (
            f"Title: {row['title']}\n"
            f"Source: {row['source']}\n"
            f"Published: {row['published']}\n"
            f"Category: {row['source_category']}\n"
            f"Content: {row['text']}"
        )
        for chunk_no, chunk in enumerate(chunk_text(base_text, chunk_size, overlap)):
            rows.append(
                {
                    "chunk_id": f"{row['doc_id']}_chunk_{chunk_no:03d}",
                    "doc_id": row["doc_id"],
                    "title": row["title"],
                    "source": row["source"],
                    "source_category": row["source_category"],
                    "url": row["url"],
                    "published": row["published"],
                    "chunk_no": chunk_no,
                    "chunk": chunk,
                }
            )

    chunk_df = pd.DataFrame(rows)
    out_file = PROCESSED_DIR / "chunks.csv"
    chunk_df.to_csv(out_file, index=False)
    print(f"Created {len(chunk_df)} chunks from {len(df)} documents")
    print(f"Saved: {out_file}")
    return chunk_df


if __name__ == "__main__":
    create_chunks()
