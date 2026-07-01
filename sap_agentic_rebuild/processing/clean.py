from __future__ import annotations

import hashlib
import re
from html import unescape

import pandas as pd
from bs4 import BeautifulSoup

from config import PROCESSED_DIR, RAW_DIR

REQUIRED_COLUMNS = [
    "id",
    "title",
    "content",
    "text",
    "url",
    "published",
    "source",
    "source_category",
    "publisher",
    "collected_at",
]


def clean_text(value: str) -> str:
    value = "" if value is None else str(value)
    value = unescape(value)
    value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def stable_doc_id(*parts: str) -> str:
    raw = "|".join(str(part or "").strip().lower() for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "link": "url",
        "date": "published",
        "summary": "content",
        "description": "content",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    for col in ["title", "content", "text", "url", "published", "source", "source_category", "publisher"]:
        df[col] = df[col].fillna("").map(clean_text)

    empty_text = df["text"].str.len() == 0
    df.loc[empty_text, "text"] = (df.loc[empty_text, "title"] + ". " + df.loc[empty_text, "content"]).map(clean_text)

    df["id"] = df.apply(
        lambda row: row["id"] if str(row["id"]).strip() else stable_doc_id(row["title"], row["url"], row["source"]),
        axis=1,
    )
    return df[REQUIRED_COLUMNS]


def prepare_master_data(min_text_length: int = 60) -> pd.DataFrame:
    input_file = RAW_DIR / "all_sources.csv"
    if not input_file.exists():
        raise FileNotFoundError("data/raw/all_sources.csv not found. Run: python collectors/live_collect.py")

    df = pd.read_csv(input_file).fillna("")
    df = normalize_columns(df)
    df = df[df["text"].str.len() >= min_text_length].copy()
    df = df.drop_duplicates(subset=["id"]).reset_index(drop=True)
    df["doc_id"] = [f"doc_{idx:05d}" for idx in range(len(df))]

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_file = PROCESSED_DIR / "master_data.csv"
    df.to_csv(out_file, index=False)

    print(f"Prepared master dataset with {len(df)} documents")
    print(f"Saved: {out_file}")
    return df


if __name__ == "__main__":
    prepare_master_data()
