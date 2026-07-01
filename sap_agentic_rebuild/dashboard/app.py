from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st


# Project imports

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.strategic_agent import run_strategic_agent
from config import (
    AGENT_MEMORY_FILE,
    AGENT_TRACE_FILE,
    AUTO_REFRESH_HOURS,
    COMPANY_NAME,
    INDUSTRY,
    OLLAMA_MODEL,
    PROCESSED_DIR,
    SCHEDULER_STATUS_FILE,
    SOURCES,
)


# Page setup

st.set_page_config(
    page_title="SAP Executive Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BERLIN_TZ = ZoneInfo("Europe/Berlin")
DEFAULT_GOAL = "If you were the CEO of SAP today, what should management do next and why?"


# Styling

st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 1.3rem;
        padding-bottom: 2rem;
        max-width: 1450px;
    }
    .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 24px;
        background: linear-gradient(135deg, #07172f 0%, #123a63 52%, #0d6efd 100%);
        color: white;
        box-shadow: 0 16px 40px rgba(0,0,0,0.18);
        margin-bottom: 1rem;
    }
    .hero h1 {
        margin: 0;
        font-size: 2.25rem;
        letter-spacing: -0.04em;
    }
    .hero p {
        margin-top: 0.45rem;
        margin-bottom: 0;
        opacity: 0.94;
        font-size: 1rem;
    }
    .workflow {
        display: flex;
        flex-wrap: wrap;
        gap: .45rem;
        margin-top: .9rem;
    }
    .pill {
        padding: .35rem .65rem;
        border-radius: 999px;
        background: rgba(255,255,255,.14);
        border: 1px solid rgba(255,255,255,.25);
        color: white;
        font-size: .82rem;
    }
    .section-title {
        font-size: 1.25rem;
        font-weight: 750;
        margin: .4rem 0 .8rem 0;
    }
    .small-muted {
        color: #6b7280;
        font-size: .86rem;
    }
    .kpi-card {
        background: white;
        padding: 1rem 1.1rem;
        border-radius: 20px;
        border: 1px solid #e6eaf0;
        box-shadow: 0 6px 22px rgba(15,23,42,.06);
        min-height: 115px;
    }
    .kpi-label {
        color: #64748b;
        font-size: .82rem;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: .04em;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: .2rem;
    }
    .kpi-note {
        color: #64748b;
        font-size: .82rem;
        margin-top: .25rem;
    }
    .info-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: .95rem 1rem;
        box-shadow: 0 6px 18px rgba(15, 23, 42, .04);
        margin-bottom: .75rem;
    }
    .signal-card {
        border-left: 5px solid #0d6efd;
        background: #ffffff;
        border-radius: 16px;
        padding: .9rem 1rem;
        border-top: 1px solid #e5e7eb;
        border-right: 1px solid #e5e7eb;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: .75rem;
    }
    .risk-card {
        border-left: 5px solid #b42318;
        background: #ffffff;
        border-radius: 16px;
        padding: .9rem 1rem;
        border-top: 1px solid #e5e7eb;
        border-right: 1px solid #e5e7eb;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: .75rem;
    }
    .recommendation-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dbe3ef;
        border-radius: 20px;
        padding: 1rem 1.1rem;
        box-shadow: 0 8px 24px rgba(15,23,42,.06);
        margin-bottom: .85rem;
    }
    .tag {
        display: inline-block;
        padding: .22rem .52rem;
        border-radius: 999px;
        background: #eef2ff;
        color: #27346a;
        font-size: .78rem;
        font-weight: 650;
        margin-right: .25rem;
        margin-bottom: .25rem;
    }
    .tag-risk {
        background: #fff1f2;
        color: #9f1239;
    }
    .tag-ok {
        background: #ecfdf5;
        color: #065f46;
    }

.risk-assessment-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .55rem;
    margin-top: .75rem;
}
.risk-assessment-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: .65rem .7rem;
}
.risk-assessment-box .risk-label {
    color: #64748b;
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .06em;
    text-transform: uppercase;
    margin-bottom: .18rem;
}
.risk-assessment-box .risk-value {
    color: #0f172a;
    font-size: .95rem;
    font-weight: 800;
}
.risk-assessment-box .risk-note {
    color: #475569;
    font-size: .78rem;
    margin-top: .2rem;
    line-height: 1.35;
}
    .briefing-box {
        background: #0f172a;
        color: white;
        border-radius: 22px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 14px 34px rgba(15,23,42,.20);
    }
    .briefing-box h3, .briefing-box p, .briefing-box li {
        color: white;
    }

    .executive-callout {
        background: linear-gradient(135deg, #f8fbff 0%, #eef6ff 100%);
        border: 1px solid #d8e8ff;
        border-radius: 22px;
        padding: 1rem 1.1rem;
        box-shadow: 0 8px 24px rgba(37,99,235,.08);
        margin: .65rem 0 1rem 0;
    }
    .executive-callout h3 {
        margin: 0 0 .35rem 0;
        color: #0f172a;
    }
    .executive-callout p {
        margin: 0;
        color: #475569;
        line-height: 1.55;
    }
    .sentiment-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dbe3ef;
        border-radius: 24px;
        padding: 1rem 1.1rem;
        box-shadow: 0 10px 28px rgba(15,23,42,.07);
        min-height: 150px;
    }
    .sentiment-title {
        font-size: .8rem;
        font-weight: 800;
        letter-spacing: .08em;
        text-transform: uppercase;
        color: #64748b;
    }
    .sentiment-value {
        font-size: 2rem;
        font-weight: 850;
        color: #0f172a;
        margin-top: .25rem;
    }
    .sentiment-subtitle {
        color: #64748b;
        font-size: .86rem;
        margin-top: .35rem;
        line-height: 1.4;
    }
    .sentiment-gauge {
        width: 100%;
        height: 12px;
        background: #e5e7eb;
        border-radius: 999px;
        overflow: hidden;
        margin-top: .65rem;
    }
    .sentiment-gauge-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #dc2626 0%, #f59e0b 48%, #16a34a 100%);
    }
    .explain-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .75rem;
        margin-top: .75rem;
    }
    .explain-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: .85rem .95rem;
        box-shadow: 0 6px 18px rgba(15,23,42,.05);
    }
    .explain-card b {
        color: #0f172a;
    }
    .explain-card p {
        margin: .35rem 0 0 0;
        color: #64748b;
        font-size: .86rem;
        line-height: 1.45;
    }
    .section-badge {
        display: inline-block;
        padding: .24rem .6rem;
        border-radius: 999px;
        background: #dbeafe;
        color: #1e3a8a;
        font-size: .78rem;
        font-weight: 800;
        margin-bottom: .55rem;
    }


    .info-card b, .signal-card h4, .risk-card h4, .recommendation-card h3 {
        color: #0f172a !important;
    }
    .info-card p, .signal-card p, .risk-card p, .recommendation-card p {
        color: #475569 !important;
    }
    .signal-card, .risk-card, .recommendation-card, .info-card, .kpi-card {
        color: #0f172a !important;
    }
    .update-card {
        background: linear-gradient(135deg, #0b2545 0%, #143e70 100%);
        color: #ffffff;
        border-radius: 18px;
        padding: 1rem 1.1rem;
        border: 1px solid rgba(255,255,255,.14);
        box-shadow: 0 8px 22px rgba(15,23,42,.16);
        margin: .5rem 0 1.2rem 0;
    }
    .update-card .label {
        font-size: .8rem;
        text-transform: uppercase;
        letter-spacing: .08em;
        opacity: .75;
        font-weight: 800;
    }
    .update-card .value {
        font-size: 1.35rem;
        font-weight: 850;
        margin-top: .2rem;
    }
    .briefing-panel {
        background: #ffffff;
        border: 1px solid #dbe3ef;
        border-radius: 22px;
        padding: 1rem 1.1rem;
        min-height: 190px;
        box-shadow: 0 8px 24px rgba(15,23,42,.06);
        color: #0f172a;
    }
    .briefing-panel h3 {
        color: #0f172a !important;
        margin: 0 0 .5rem 0;
    }
    .briefing-panel p, .briefing-panel li {
        color: #475569 !important;
        line-height: 1.55;
    }
    .action-box {
        background: linear-gradient(135deg, #f8fbff 0%, #eef6ff 100%);
        border: 1px solid #d8e8ff;
        border-radius: 20px;
        padding: 1rem 1.1rem;
        margin: .4rem 0 1rem 0;
    }
    .action-box h4 { color: #0f172a !important; margin: 0 0 .35rem 0; }
    .action-box p { color: #475569 !important; margin: 0; }


    .executive-summary-box {
        background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
        border: 1px solid #dbe3ef;
        border-radius: 24px;
        padding: 1.15rem 1.25rem;
        box-shadow: 0 10px 28px rgba(15,23,42,.07);
        color: #0f172a;
        margin: .8rem 0 1rem 0;
    }
    .executive-summary-box p {
        color: #334155 !important;
        font-size: 1rem;
        line-height: 1.62;
        margin: 0 0 .75rem 0;
    }
    .priority-card {
        background: #ffffff;
        border: 1px solid #dbe3ef;
        border-left: 5px solid #0d6efd;
        border-radius: 18px;
        padding: .95rem 1rem;
        box-shadow: 0 8px 22px rgba(15,23,42,.05);
        margin-bottom: .75rem;
        color: #0f172a;
    }
    .priority-card h4 {
        color: #0f172a !important;
        margin: 0 0 .5rem 0;
    }
    .priority-card p {
        color: #475569 !important;
        margin: .4rem 0 0 0;
        line-height: 1.45;
    }
    .evidence-note {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: .75rem .85rem;
        color: #475569;
        margin-bottom: .8rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# Utility functions

def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_master_data() -> pd.DataFrame:
    file = PROCESSED_DIR / "master_data.csv"
    if not file.exists():
        return pd.DataFrame()
    df = pd.read_csv(file).fillna("")
    return add_sentiment_columns(df, use_finbert=True)


def parse_datetime(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None or str(value).strip() == "":
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", utc=True)


def clean_text(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def safe_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns]

def dedupe_sentences(text: str) -> str:
    """Remove repeated sentences/phrases from collected news text for cleaner dashboard display."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return ""

    
    parts = re.split(r"(?<=[.!?])\s+", text)
    seen: set[str] = set()
    cleaned: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        key = re.sub(r"[^a-zA-Z0-9]+", " ", part.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(part)
    return " ".join(cleaned)


def clean_display_body(title: Any, body: Any, limit: int = 280) -> str:
    """Clean card body text so titles are not repeated inside the description."""
    title_clean = re.sub(r"\s+", " ", str(title or "")).strip()
    body_clean = re.sub(r"\s+", " ", str(body or "")).strip()

    if not body_clean:
        return ""

   
    if title_clean and body_clean.lower().startswith(title_clean.lower()):
        body_clean = body_clean[len(title_clean):].strip(" -:|.")

    
    body_clean = dedupe_sentences(body_clean)
    return clean_text(body_clean, limit)


def clean_evidence_snippet(item: dict[str, Any], limit: int = 900) -> str:
    """Show only the useful evidence text, without repeated Title/Source/Category metadata."""
    title = str(item.get("title", "") or "")
    raw = str(item.get("snippet", "") or item.get("text", "") or "")
    raw = re.sub(r"\s+", " ", raw).strip()

    
    content_match = re.search(r"\bContent:\s*(.*)", raw, flags=re.IGNORECASE)
    if content_match:
        raw = content_match.group(1).strip()

   
    raw = re.sub(r"^Title:\s*", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"\bSource:\s*[^:]{1,120}?\bPublished:\s*", "Published: ", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\bPublished:\s*[^:]{1,120}?\bCategory:\s*", "Category: ", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\bCategory:\s*\w+\s*", "", raw, flags=re.IGNORECASE)

    if title and raw.lower().startswith(title.lower()):
        raw = raw[len(title):].strip(" -:|.")

    raw = dedupe_sentences(raw)
    return clean_text(raw, limit)


def signal_search_terms(label: str, kind: str) -> set[str]:
    """Create focused evidence-matching terms so risk/opportunity cards do not reuse random evidence."""
    label_l = str(label or "").lower()
    terms = {t for t in re.findall(r"[a-zA-Z0-9]+", label_l) if len(t) > 2}

    if any(term in label_l for term in ["business ai", "automation", "agent", "ai"]):
        terms.update({"ai", "agent", "agentic", "automation", "autonomous", "workflow", "business"})
    if any(term in label_l for term in ["cloud", "migration", "erp", "s/4hana", "rise"]):
        terms.update({"cloud", "migration", "erp", "s4hana", "hana", "rise"})
    if any(term in label_l for term in ["security", "privacy", "governance", "compliance", "regulation"]):
        terms.update({"security", "privacy", "governance", "compliance", "regulation", "regulatory", "breach", "trust"})
    if any(term in label_l for term in ["competitive", "competition", "competitor", "rival", "hyperscaler"]):
        terms.update({"competition", "competitive", "competitor", "rival", "oracle", "microsoft", "salesforce", "workday", "hyperscaler"})

    
    if kind == "risk":
        terms.update({"risk", "pressure", "concern", "threat", "challenge"})

    return terms


POSITIVE_WORDS = {
    "growth", "increase", "increased", "rising", "rise", "record", "strong", "profit",
    "profits", "revenue", "expansion", "expand", "expanded", "partnership", "partner",
    "innovation", "innovative", "launch", "launched", "success", "successful", "accelerate",
    "improve", "improved", "upgrade", "leader", "leading", "adoption", "win", "wins",
    "boost", "positive", "opportunity", "cloud", "ai", "automation",
}

NEGATIVE_WORDS = {
    "risk", "risks", "decline", "declined", "fall", "fell", "loss", "losses", "weak",
    "weakness", "lawsuit", "investigation", "outage", "security", "privacy", "breach",
    "warning", "pressure", "threat", "threats", "competition", "competitor", "delay",
    "delayed", "cut", "cuts", "concern", "concerns", "regulation", "regulatory", "fine",
    "cost", "costs", "uncertainty", "negative", "slowdown", "challenge", "challenging",
}


def keyword_sentiment_score(text: str) -> float:
    """
    Lightweight fallback sentiment method.

    This is kept intentionally because FinBERT may not be installed or may be slow
    during a live demo. The fallback keeps the dashboard working reliably.
    """
    tokens = re.findall(r"[a-zA-Z][a-zA-Z\-]+", str(text).lower())
    if not tokens:
        return 0.0

    positive = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negative = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    total = positive + negative

    if total == 0:
        return 0.0

    return round((positive - negative) / total, 3)


def label_from_score(score: float) -> str:
    if score > 0.12:
        return "Positive"
    if score < -0.12:
        return "Negative"
    return "Neutral"


def keyword_sentiment_record(text: str) -> dict[str, Any]:
    score = keyword_sentiment_score(text)
    return {
        "sentiment_label": label_from_score(score),
        "sentiment_score": score,
        "sentiment_confidence": abs(score),
        "sentiment_method": "keyword_fallback",
    }


@st.cache_resource(show_spinner=False)
def load_finbert_pipeline():
    """
    Load FinBERT once for the whole Streamlit app.

    Model used:
    ProsusAI/finbert

    It is better for financial/business sentiment than a raw BERT model.
    """
    from transformers import pipeline

    return pipeline(
        "sentiment-analysis",
        model="ProsusAI/finbert",
        tokenizer="ProsusAI/finbert",
    )


def normalize_finbert_result(result: dict[str, Any]) -> dict[str, Any]:
    raw_label = str(result.get("label", "neutral")).lower()
    confidence = float(result.get("score", 0.0))

    if "positive" in raw_label:
        label = "Positive"
        score = confidence
    elif "negative" in raw_label:
        label = "Negative"
        score = -confidence
    else:
        label = "Neutral"
        score = 0.0

    return {
        "sentiment_label": label,
        "sentiment_score": round(score, 3),
        "sentiment_confidence": round(confidence, 3),
        "sentiment_method": "finbert",
    }


def finbert_sentiment_records(texts: list[str]) -> list[dict[str, Any]]:
    """
    Try FinBERT first. If loading or inference fails, use keyword fallback.

    This gives a stronger dashboard while still keeping the project safe for
    offline/demo conditions.
    """
    if not texts:
        return []

    try:
        classifier = load_finbert_pipeline()
        cleaned_texts = [clean_text(text, limit=512) for text in texts]
        results = classifier(
            cleaned_texts,
            truncation=True,
            max_length=512,
            batch_size=8,
        )
        return [normalize_finbert_result(item) for item in results]

    except Exception:
        return [keyword_sentiment_record(text) for text in texts]


def add_sentiment_columns(df: pd.DataFrame, use_finbert: bool = True) -> pd.DataFrame:
    """
    Adds sentiment columns used by Section 5 of the dashboard.

    Columns created:
    - sentiment_label: Positive / Neutral / Negative
    - sentiment_score: -1 to +1 style score
    - sentiment_confidence: model/fallback confidence
    - sentiment_method: finbert or keyword_fallback
    - published_dt: parsed timestamp for trend charts
    """
    if df.empty:
        return df

    df = df.copy()

    title = df["title"] if "title" in df.columns else pd.Series([""] * len(df), index=df.index)
    text = df["text"] if "text" in df.columns else df.get("content", pd.Series([""] * len(df), index=df.index))
    combined = (title.astype(str) + " " + text.astype(str)).tolist()

    if use_finbert:
        sentiment_records = finbert_sentiment_records(combined)
    else:
        sentiment_records = [keyword_sentiment_record(item) for item in combined]

    sentiment_df = pd.DataFrame(sentiment_records, index=df.index)
    for col in ["sentiment_label", "sentiment_score", "sentiment_confidence", "sentiment_method"]:
        df[col] = sentiment_df[col] if col in sentiment_df.columns else ""

    df["published_dt"] = df["published"].apply(parse_datetime) if "published" in df.columns else pd.NaT
    return df

def format_timestamp(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(ts):
        return str(value) if value else "Unknown"
    return ts.tz_convert(BERLIN_TZ).strftime("%d %b %Y, %H:%M %Z")


def latest_update(master_df: pd.DataFrame, status: dict[str, Any]) -> str:
    if status.get("updated_at"):
        return format_timestamp(status.get("updated_at"))
    if not master_df.empty and "collected_at" in master_df.columns:
        collected = pd.to_datetime(master_df["collected_at"], errors="coerce", utc=True).dropna()
        if not collected.empty:
            return format_timestamp(collected.max())
    if not master_df.empty and "published_dt" in master_df.columns:
        published = master_df["published_dt"].dropna()
        if not published.empty:
            return format_timestamp(published.max())
    return "Unknown"


def run_pipeline_from_dashboard() -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "run_pipeline.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60 * 60,
    )
    return result.returncode, (result.stdout or "") + "\n" + (result.stderr or "")


def kpi_card(label: str, value: str | int, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def data_card(title: str, body: str, tags: list[str] | None = None, url: str | None = None) -> None:
    tag_html = ""
    if tags:
        tag_html = "".join([f'<span class="tag">{tag}</span>' for tag in tags if tag])
    link_html = f'<div style="margin-top:.4rem;"><a href="{url}" target="_blank">Open source</a></div>' if url else ""
    st.markdown(
        f"""
        <div class="info-card">
            <b>{clean_text(title, 130)}</b>
            <p class="small-muted">{clean_display_body(title, body, 280)}</p>
            {tag_html}
            {link_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def trend_confidence(count: int) -> int:
    return max(45, min(95, 50 + int(count) * 8))


def impact_from_count(count: int) -> str:
    if count >= 5:
        return "High"
    if count >= 2:
        return "Medium"
    return "Low"


def severity_from_count(count: int) -> str:
    if count >= 5:
        return "High"
    if count >= 2:
        return "Medium"
    return "Low"


def evidence_for_signal(label: str, evidence: list[dict[str, Any]], kind: str = "opportunity", max_items: int = 3) -> list[dict[str, Any]]:
    """Match evidence to the specific signal instead of reusing the first retrieved chunks."""
    terms = signal_search_terms(label, kind)
    if not terms:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    for item in evidence:
        blob = f"{item.get('title', '')} {item.get('snippet', '')} {item.get('category', '')} {item.get('source', '')}".lower()
        score = sum(blob.count(term) for term in terms)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:max_items]]


def expected_impact_for_recommendation(title: str) -> str:
    title_l = title.lower()
    if any(term in title_l for term in ["ai", "agent", "automation"]):
        return "Higher product differentiation, faster enterprise workflows, and stronger AI positioning."
    if any(term in title_l for term in ["cloud", "s/4hana", "migration", "modernization"]):
        return "Improved cloud revenue quality, customer retention, and migration momentum."
    if any(term in title_l for term in ["compet", "defend", "suite"]):
        return "Stronger competitive moat against Oracle, Microsoft, Salesforce, and Workday."
    if any(term in title_l for term in ["governance", "security", "compliance"]):
        return "Reduced regulatory, security, and trust risk in enterprise AI adoption."
    return "Better executive prioritization through evidence-backed decision-making."




def recommendation_risk_assessment(title: str, risk_level: str) -> dict[str, tuple[str, str]]:
    """
    Creates the required risk assessment fields for each recommendation.
    These are rule-based dashboard labels derived from the recommendation theme.
    """
    title_l = title.lower()
    base_level = risk_level if risk_level in {"High", "Medium", "Low"} else "Medium"

    if any(term in title_l for term in ["ai", "agent", "automation", "r&d"]):
        return {
            "Financial risk": (base_level, "Investment cost and uncertain AI monetization timeline."),
            "Operational risk": ("Medium", "Requires integration with ERP workflows and internal capability building."),
            "Strategic risk": ("Medium", "Competitors may move faster in enterprise AI positioning."),
        }
    if any(term in title_l for term in ["cloud", "s/4hana", "migration", "modernization"]):
        return {
            "Financial risk": ("Medium", "Migration support and cloud incentives may affect short-term margins."),
            "Operational risk": (base_level, "Customer migration complexity can slow execution."),
            "Strategic risk": ("Medium", "Slow transition may weaken cloud growth momentum."),
        }
    if any(term in title_l for term in ["compet", "defend", "suite", "oracle", "microsoft", "salesforce", "workday"]):
        return {
            "Financial risk": ("Medium", "Competitive pricing and product investment may pressure margins."),
            "Operational risk": ("Low", "Main execution need is stronger go-to-market coordination."),
            "Strategic risk": (base_level, "Loss of enterprise positioning could reduce long-term market share."),
        }
    if any(term in title_l for term in ["governance", "security", "compliance", "regulation"]):
        return {
            "Financial risk": ("Low", "Compliance investment is controlled compared with potential penalties."),
            "Operational risk": ("Medium", "Requires process controls, monitoring, and internal governance."),
            "Strategic risk": (base_level, "Weak trust controls could damage enterprise adoption."),
        }
    return {
        "Financial risk": (base_level, "Budget allocation should be monitored against business value."),
        "Operational risk": ("Medium", "Execution depends on coordination across product, sales, and customer teams."),
        "Strategic risk": ("Medium", "Delays may reduce competitive advantage."),
    }


def render_risk_assessment_boxes(risks: dict[str, tuple[str, str]]) -> str:
    boxes = []
    for label, value in risks.items():
        level, note = value
        boxes.append(
            f"""
            <div class="risk-assessment-box">
                <div class="risk-label">{label}</div>
                <div class="risk-value">{level}</div>
                <div class="risk-note">{note}</div>
            </div>
            """
        )
    return '<div class="risk-assessment-grid">' + ''.join(boxes) + '</div>'


def show_signal_cards(signals: list[Any], evidence: list[dict[str, Any]], kind: str = "opportunity") -> None:
    if not signals:
        st.info("No signals available yet. Run the Strategic Agent first.")
        return

    for raw in signals:
        if isinstance(raw, (list, tuple)) and len(raw) >= 2:
            label, count = raw[0], int(raw[1])
        elif isinstance(raw, dict):
            label, count = raw.get("title", "Signal"), int(raw.get("count", 1))
        else:
            label, count = str(raw), 1

        matched = evidence_for_signal(str(label), evidence, kind=kind)
        evidence_refs = ", ".join([f"E{item.get('evidence_id', '?')}" for item in matched]) or "Evidence not available"
        card_class = "risk-card" if kind == "risk" else "signal-card"
        second_label = "Severity" if kind == "risk" else "Impact"
        second_value = severity_from_count(count) if kind == "risk" else impact_from_count(count)
        confidence = trend_confidence(count)
        category = "Strategic / Competitive / Operational" if kind == "risk" else "Growth / Product / Market"

        st.markdown(
            f"""
            <div class="{card_class}">
                <h4 style="margin:.1rem 0 .35rem 0;">{label}</h4>
                <span class="tag">{second_label}: {second_value}</span>
                <span class="tag">Confidence: {confidence}%</span>
                <span class="tag {'tag-risk' if kind == 'risk' else 'tag-ok'}">Category: {category}</span>
                <p class="small-muted" style="margin-top:.65rem;">Evidence: {evidence_refs}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"Show supporting evidence for {label}"):
            for item in matched:
                st.markdown(f"**E{item.get('evidence_id', '?')}: {item.get('title', '')}**")
                st.caption(f"{item.get('source', '')} | {item.get('category', '')} | {item.get('published', '')}")
                st.write(clean_evidence_snippet(item))
                if item.get("url"):
                    st.markdown(f"[Open source]({item.get('url')})")


def get_agent_result() -> dict[str, Any] | None:
    if "last_agent_result" in st.session_state:
        return st.session_state["last_agent_result"]
    trace = read_json(AGENT_TRACE_FILE)
    return trace if trace else None


def source_filtered(df: pd.DataFrame, categories: list[str], limit: int = 6) -> pd.DataFrame:
    if df.empty or "source_category" not in df.columns:
        return pd.DataFrame()
    view = df[df["source_category"].astype(str).str.lower().isin(categories)].copy()
    if "published_dt" in view.columns:
        view = view.sort_values("published_dt", ascending=False, na_position="last")
    return view.head(limit)


def show_market_cards(df: pd.DataFrame, categories: list[str], empty_text: str) -> None:
    view = source_filtered(df, categories, limit=6)
    if view.empty:
        st.info(empty_text)
        return
    for _, row in view.iterrows():
        data_card(
            title=row.get("title", "Untitled"),
            body=row.get("text", row.get("content", "")),
            tags=[str(row.get("source", "")), str(row.get("source_category", "")), str(row.get("sentiment_label", ""))],
            url=row.get("url", ""),
        )


def sentiment_counts(df: pd.DataFrame) -> pd.Series:
    if df.empty or "sentiment_label" not in df.columns:
        return pd.Series({"Positive": 0, "Neutral": 0, "Negative": 0})
    return df["sentiment_label"].value_counts().reindex(["Positive", "Neutral", "Negative"]).fillna(0).astype(int)


def sentiment_status(avg: float) -> tuple[str, str]:
    if avg >= 0.20:
        return "Favorable", "Coverage is leaning positive. This usually points to supportive market narratives, growth signals, or product momentum."
    if avg <= -0.20:
        return "Pressure", "Coverage is leaning negative. This may indicate risk pressure from competition, regulation, security, financial weakness, or customer concerns."
    return "Balanced", "Coverage is mostly neutral or mixed. This usually means the market is watching, but the signal is not strongly positive or negative yet."


def sentiment_method_label(df: pd.DataFrame) -> str:
    if df.empty or "sentiment_method" not in df.columns:
        return "No method available"
    counts = df["sentiment_method"].value_counts()
    finbert = int(counts.get("finbert", 0))
    fallback = int(counts.get("keyword_fallback", 0))
    return f"FinBERT: {finbert} | Keyword fallback: {fallback}"


def sentiment_summary(df: pd.DataFrame, title: str) -> None:
    if df.empty:
        st.info(f"No data available for {title}.")
        return

    counts = sentiment_counts(df)
    avg = round(float(df["sentiment_score"].mean()), 3) if "sentiment_score" in df else 0.0
    status_label, status_text = sentiment_status(avg)
    total = int(len(df))
    positive_share = round((int(counts.get("Positive", 0)) / total) * 100, 1) if total else 0.0
    negative_share = round((int(counts.get("Negative", 0)) / total) * 100, 1) if total else 0.0
    gauge_width = max(0, min(100, int((avg + 1) * 50)))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card(f"{title} Positive", int(counts.get("Positive", 0)), f"{positive_share}% of analyzed records")
    with c2:
        kpi_card(f"{title} Neutral", int(counts.get("Neutral", 0)), "factual or mixed coverage")
    with c3:
        kpi_card(f"{title} Negative", int(counts.get("Negative", 0)), f"{negative_share}% of analyzed records")
    with c4:
        kpi_card(f"{title} Index", avg, "-1 negative to +1 positive")

    st.markdown(
        f"""
        <div class="sentiment-card">
            <div class="sentiment-title">Executive reading: {title}</div>
            <div class="sentiment-value">{status_label}</div>
            <div class="sentiment-subtitle">{status_text}</div>
            <div class="sentiment-gauge"><div class="sentiment-gauge-fill" style="width:{gauge_width}%"></div></div>
            
        </div>
        """,
        unsafe_allow_html=True,
    )


def sentiment_distribution_frame(df: pd.DataFrame) -> pd.DataFrame:
    counts = sentiment_counts(df)
    return pd.DataFrame({"Sentiment": counts.index, "Records": counts.values})


def method_distribution_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "sentiment_method" not in df.columns:
        return pd.DataFrame({"Method": [], "Records": []})
    counts = df["sentiment_method"].value_counts().reset_index()
    counts.columns = ["Method", "Records"]
    return counts


def sentiment_explanation_box() -> None:
    st.markdown(
        """
        <div class="executive-callout">
            <h3>Sentiment turns public information into a management signal.</h3>
            <p>
                The dashboard classifies each collected record as Positive, Neutral, or Negative using FinBERT as the primary sentiment model. FinBERT is used because it is better suited to business and financial language than a simple keyword counter. If FinBERT is unavailable, the system automatically falls back to the keyword-based method, so sentiment analysis still works.
            </p>
        </div>
        <div class="explain-grid">
            <div class="explain-card"><b>News sentiment</b><p>Measures how company, market, and business news are framing SAP right now.</p></div>
            <div class="explain-card"><b>Public sentiment</b><p>Uses public-facing market sources such as news, competitor coverage, and trend articles to estimate external perception.</p></div>
            <div class="explain-card"><b>Sentiment trend</b><p>Tracks whether sentiment is improving, stable, or weakening over time.</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def top_signal_names(signals: list[Any], limit: int = 3) -> list[str]:
    names: list[str] = []
    for raw in signals[:limit]:
        if isinstance(raw, (list, tuple)) and raw:
            names.append(str(raw[0]))
        elif isinstance(raw, dict):
            names.append(str(raw.get("title", "Signal")))
        else:
            names.append(str(raw))
    return [name for name in names if name]


def bullet_html(items: list[str]) -> str:
    if not items:
        return "<p>No items available yet.</p>"
    return "<ul>" + "".join(f"<li>{clean_text(item, 180)}</li>" for item in items) + "</ul>"


def render_update_card(update_text: str) -> None:
    st.markdown(
        f'''
        <div class="update-card">
            <div class="label">Last refresh</div>
            <div class="value">{update_text}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def escape_html(value: Any) -> str:
    text = str(value or "")
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def human_join(items: list[str], fallback: str = "available strategic signals") -> str:
    clean_items = [clean_text(item, 90) for item in items if str(item).strip()]
    if not clean_items:
        return fallback
    if len(clean_items) == 1:
        return clean_items[0]
    if len(clean_items) == 2:
        return f"{clean_items[0]} and {clean_items[1]}"
    return ", ".join(clean_items[:-1]) + f", and {clean_items[-1]}"


def generated_briefing_is_structured_qna(text: str) -> bool:
    """
    Detects whether the LLM returned the older three-heading Q&A format.
    If yes, the dashboard displays the cleaner direct executive summary instead.
    """
    lowered = str(text or "").lower()
    markers = ["what happened", "why does it matter", "what should management do next"]
    return sum(1 for marker in markers if marker in lowered) >= 2


def _goal_from_result(result: dict[str, Any]) -> str:
    """Return the exact user goal/question from the latest agent run."""
    goal = str(result.get("goal", "") or "").strip()
    if goal:
        return goal
    for item in result.get("execution_trace", []) or []:
        if item.get("stage") == "goal_received":
            return str(item.get("detail", "") or "").strip()
    return DEFAULT_GOAL


def _priority_sentence(recommendations: list[dict[str, Any]], max_items: int = 3) -> str:
    titles = [str(rec.get("title", "")).strip() for rec in recommendations[:max_items] if str(rec.get("title", "")).strip()]
    if not titles:
        return "management should focus on the validated strategic recommendations from the agent."
    clean_titles = [title[0].lower() + title[1:] if title else title for title in titles]
    return "management should " + human_join(clean_titles, "act on the validated recommendations") + "."


def build_direct_ceo_summary(result: dict[str, Any]) -> list[str]:
    """
    Builds a direct executive answer from validated agent outputs.

    It is intent-aware:
    - risk questions answer risks directly
    - opportunity questions answer opportunities directly
    - competitor questions answer competitive response directly
    - trend questions answer trend priorities directly
    - CEO strategy questions answer what management should do next

    This keeps the dashboard grounded and avoids generic LLM-style wording.
    """
    goal = _goal_from_result(result)
    goal_l = goal.lower()
    intent = str(result.get("intent", "") or "").lower()

    signals = result.get("signals", {}) or {}
    recommendations = result.get("recommendations", []) or []
    validation = result.get("validation", {}) or {}
    evidence = result.get("evidence", []) or []

    opportunity_names = top_signal_names(signals.get("opportunities", []), 3)
    risk_names = top_signal_names(signals.get("risks", []), 3)
    trend_names = top_signal_names(signals.get("trends", []), 3)

    evidence_text = f"{len(evidence)} retrieved evidence items" if evidence else "the available retrieved evidence"
    validation_status = str(validation.get("status", "unknown"))
    validation_confidence = str(validation.get("confidence", "unknown"))
    validation_text = f"The recommendation check is {validation_status} with {validation_confidence} confidence."
    action_sentence = _priority_sentence(recommendations)

    is_risk = intent == "risk_assessment" or any(word in goal_l for word in ["risk", "risks", "threat", "threats", "concern", "problem"])
    is_opportunity = intent == "opportunity_discovery" or any(word in goal_l for word in ["opportunity", "growth", "invest", "expand"])
    is_competitive = intent == "competitive_strategy" or any(word in goal_l for word in ["competitor", "oracle", "microsoft", "salesforce", "workday", "competition"])
    is_trend = intent == "trend_strategy" or any(word in goal_l for word in ["trend", "future", "automation", "agent", "ai"])

    if is_risk:
        risk_text = human_join(risk_names, "the risk signals found in the retrieved evidence")
        supporting_context = []
        if trend_names:
            supporting_context.append("related trend signals such as " + human_join(trend_names))
        if opportunity_names:
            supporting_context.append("growth areas such as " + human_join(opportunity_names))
        context_text = human_join(supporting_context, "the wider SAP strategy context")
        return [
            f"The biggest risks for {COMPANY_NAME} right now are {risk_text}. These risks should be treated as management priorities because they can affect cloud ERP execution, Business AI adoption, customer trust, and competitive positioning.",
            f"The retrieved evidence also points to {context_text}, so the risk picture is not isolated. It is connected to how fast {COMPANY_NAME} can modernize its cloud and AI offerings while keeping enterprise customers confident.",
            f"Management should respond by using the validated recommendations as execution priorities: {_priority_sentence(recommendations).replace('management should ', '')} {validation_text} This briefing is based on {evidence_text}.",
        ]

    if is_opportunity:
        opportunity_text = human_join(opportunity_names, "the opportunity signals found in the retrieved evidence")
        return [
            f"The strongest opportunities for {COMPANY_NAME} are {opportunity_text}. These areas matter because they connect directly to SAP's enterprise software position, cloud ERP modernization, and Business AI strategy.",
            f"The evidence suggests that management should focus on opportunities that create practical business value for existing enterprise customers, not only broad AI branding. The most useful opportunities are the ones that can improve workflows, migration outcomes, and customer productivity.",
            f"Next, {_priority_sentence(recommendations)} {validation_text} This briefing is based on {evidence_text}.",
        ]

    if is_competitive:
        risk_text = human_join(risk_names, "competitive pressure")
        return [
            f"SAP's competitive challenge is centered on {risk_text}. The retrieved evidence indicates that management should treat competition as a strategic execution issue, especially around cloud ERP, Business AI, and enterprise platform differentiation.",
            f"This matters because competitors can pressure SAP through faster product launches, platform integration, pricing, or customer migration support. SAP's advantage should come from deep enterprise process knowledge and integrated business data across its suite.",
            f"Management should defend SAP's position by turning the validated recommendations into focused execution priorities: {_priority_sentence(recommendations).replace('management should ', '')} {validation_text}",
        ]

    if is_trend:
        trend_text = human_join(trend_names, "the trend signals found in the retrieved evidence")
        return [
            f"The main trends management should monitor are {trend_text}. These trends are important because they influence how enterprise customers evaluate future ERP, automation, analytics, and AI-enabled business systems.",
            f"For SAP, the strategic issue is whether these trends can be converted into reliable customer value inside existing enterprise workflows. Trend monitoring should therefore be linked to product execution, migration support, and risk control.",
            f"Next, {_priority_sentence(recommendations)} {validation_text} This briefing is based on {evidence_text}.",
        ]

    opportunity_text = human_join(opportunity_names, "the strongest opportunity signals")
    risk_text = human_join(risk_names, "the main risk signals")
    trend_text = human_join(trend_names, "the relevant trend signals")
    return [
        f"If I were advising {COMPANY_NAME}'s management today, I would prioritize the validated actions from the agent rather than a broad generic AI strategy. The evidence points to {opportunity_text}, while also showing {risk_text} and {trend_text}.",
        f"This matters because SAP's next strategic move must protect its position in enterprise software while turning cloud ERP and Business AI momentum into measurable customer value. The briefing is based on {evidence_text}. {validation_text}",
        f"Management should now convert the validated recommendations into execution priorities: {_priority_sentence(recommendations).replace('management should ', '')}",
    ]

def render_executive_summary(result: dict[str, Any]) -> None:
    """
    Shows a direct executive answer built from the agent's validated signals,
    recommendations, validation status, and evidence count.

    The visible CEO summary intentionally does not use free-form LLM wording.
    This avoids hallucinated sectors, numbers, or claims appearing in the main
    executive dashboard. The LLM output remains available only in an optional
    technical expander below.
    """
    paragraphs = build_direct_ceo_summary(result)

    paragraph_html = "".join(f"<p>{escape_html(paragraph)}</p>" for paragraph in paragraphs)
    st.markdown(
        f"""
        <div class="executive-summary-box">
            {paragraph_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_management_priorities(recommendations: list[dict[str, Any]]) -> None:
    if not recommendations:
        st.info("No validated recommendations available yet.")
        return

    for idx, rec in enumerate(recommendations[:3], start=1):
        title = clean_text(rec.get("title", f"Recommendation {idx}"), 150)
        priority = clean_text(rec.get("priority", "Medium"), 40)
        risk_level = clean_text(rec.get("risk_level", "Medium"), 40)
        evidence_refs = rec.get("evidence_refs", [])
        evidence_text = ", ".join(["E" + str(ref) for ref in evidence_refs]) if evidence_refs else "Evidence review needed"
        rationale = clean_text(rec.get("rationale", ""), 260)
        impact = expected_impact_for_recommendation(title)

        st.markdown(
            f"""
            <div class="priority-card">
                <h4>{idx}. {escape_html(title)}</h4>
                <span class="tag tag-ok">Priority: {escape_html(priority)}</span>
                <span class="tag tag-risk">Risk Level: {escape_html(risk_level)}</span>
                <span class="tag">Evidence: {escape_html(evidence_text)}</span>
                <p><b>Why this action:</b> {escape_html(rationale)}</p>
                <p><b>Expected impact:</b> {escape_html(impact)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# Load data

master_df = load_master_data()
status = read_json(SCHEDULER_STATUS_FILE)
memory = read_json(AGENT_MEMORY_FILE)
result = get_agent_result()


# Header

st.markdown(
    f"""
    <div class="hero">
        <h1>{COMPANY_NAME} Executive Intelligence Dashboard</h1>
        <p>Agentic strategic intelligence.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# Sidebar controls

with st.sidebar:
    st.header("Executive Controls")
    model = st.text_input("Ollama model", value=OLLAMA_MODEL)
    n_per_query = st.slider("Evidence chunks per query", 2, 10, 4)

    st.divider()
    if st.button("Rebuild Data Pipeline", use_container_width=True):
        with st.spinner("Running live collection, cleaning, chunking, embedding, and indexing..."):
            code, output = run_pipeline_from_dashboard()
        if code == 0:
            st.success("Pipeline completed successfully.")
        else:
            st.error("Pipeline failed. Check terminal output.")
        st.code(output[-7000:])

    st.divider()
    st.caption(f"Auto-refresh interval: every {AUTO_REFRESH_HOURS} hours")
    st.caption(f"Configured sources: {len(SOURCES)}")
    st.caption(f"Memory runs: {len(memory.get('runs', []))}")


result = get_agent_result()


# Required dashboard sections

tabs = st.tabs(
    [
        "1. Company Overview",
        "2. Market Intelligence",
        "3. Opportunity Monitor",
        "4. Risk Monitor",
        "5. Sentiment Analysis",
        "6. Strategic Recommendations",
        "7. CEO Briefing",
    ]
)


# Section 1: Company Overview

with tabs[0]:
    st.markdown('<div class="section-title">Section 1: Company Overview</div>', unsafe_allow_html=True)
    source_count = int(master_df["source"].nunique()) if not master_df.empty and "source" in master_df else 0
    category_count = int(master_df["source_category"].nunique()) if not master_df.empty and "source_category" in master_df else 0
    chunk_file = PROCESSED_DIR / "chunks.csv"
    chunk_count = len(pd.read_csv(chunk_file)) if chunk_file.exists() else 0
    update_text = latest_update(master_df, status)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Company", COMPANY_NAME, "")
    with c2:
        kpi_card("Industry", "Enterprise Software", "ERP • Cloud • Business AI")
    with c3:
        kpi_card("Documents", len(master_df), "collected records")
    with c4:
        kpi_card("Data Sources", source_count, f"{category_count} categories")
    with c5:
        kpi_card("Indexed Chunks", chunk_count, "retrieval units")

    st.markdown("#### Last Update Timestamp")
    render_update_card(update_text)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Documents by Source Category")
        if not master_df.empty and "source_category" in master_df:
            st.bar_chart(master_df["source_category"].value_counts())
        else:
            st.warning("No source category data found.")
    with col_b:
        st.markdown("#### Top Data Sources")
        if not master_df.empty and "source" in master_df:
            st.bar_chart(master_df["source"].value_counts().head(10))
        else:
            st.warning("No source data found.")

    with st.expander("Show raw knowledge base records"):
        if master_df.empty:
            st.warning("No processed data found.")
        else:
            st.dataframe(
                safe_columns(master_df.copy(), ["title", "source", "source_category", "published", "sentiment_label", "sentiment_method", "url"]).head(300),
                use_container_width=True,
            )


# Section 2: Market Intelligence

with tabs[1]:
    st.markdown('<div class="section-title">Section 2: Market Intelligence</div>', unsafe_allow_html=True)
    

    m1, m2 = st.columns(2)
    with m1:
        st.markdown("### Recent News")
        show_market_cards(master_df, ["news", "market"], "No recent news or market records found.")
    with m2:
        st.markdown("### Competitor Activities")
        show_market_cards(master_df, ["competitor"], "No competitor records found.")

    m3, m4 = st.columns(2)
    with m3:
        st.markdown("### Emerging Technologies")
        show_market_cards(master_df, ["trend", "research"], "No trend or research records found.")
    with m4:
        st.markdown("### Important Company Announcements")
        show_market_cards(master_df, ["company"], "No company announcement records found.")


# Section 3: Opportunity Monitor

with tabs[2]:
    st.markdown('<div class="section-title">Section 3: Opportunity Monitor</div>', unsafe_allow_html=True)
    if result:
        opportunities = result.get("signals", {}).get("opportunities", [])
        show_signal_cards(opportunities, result.get("evidence", []), kind="opportunity")
    else:
        st.info("Generate a CEO Briefing in Section 7 to produce opportunity signals.")


# Section 4: Risk Monitor

with tabs[3]:
    st.markdown('<div class="section-title">Section 4: Risk Monitor</div>', unsafe_allow_html=True)
    if result:
        risks = result.get("signals", {}).get("risks", [])
        show_signal_cards(risks, result.get("evidence", []), kind="risk")
    else:
        st.info("Generate a CEO Briefing in Section 7 to produce risk signals.")


# Section 5: Sentiment Analysis

with tabs[4]:
    st.markdown('<div class="section-title">Section 5: Sentiment Analysis</div>', unsafe_allow_html=True)
    sentiment_explanation_box()

    if master_df.empty:
        st.warning("No data available for sentiment analysis.")
    else:
        news_df = master_df[master_df["source_category"].astype(str).str.lower().isin(["news", "market", "company"])]
        public_df = master_df[master_df["source_category"].astype(str).str.lower().isin(["news", "market", "competitor", "trend", "research"])]

        st.markdown("### Executive Sentiment Overview")
        overall_avg = round(float(master_df["sentiment_score"].mean()), 3) if "sentiment_score" in master_df else 0.0
        overall_status, _ = sentiment_status(overall_avg)
        method_mix = sentiment_method_label(master_df)
        total_records = len(master_df)
        latest_sentiment_date = "Unknown"
        if "published_dt" in master_df.columns:
            valid_dates = master_df["published_dt"].dropna()
            if not valid_dates.empty:
                latest_sentiment_date = valid_dates.max().tz_convert(BERLIN_TZ).strftime("%d %b %Y")

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            kpi_card("Overall Sentiment", overall_status, f"index: {overall_avg}")
        with s2:
            kpi_card("Records Analyzed", total_records, "documents scored")
        with s3:
            kpi_card("Sentiment Engine", "FinBERT", "keyword fallback ready")
        with s4:
            kpi_card("Latest Signal Date", latest_sentiment_date, "based on published date")

        

        st.markdown("### News Sentiment")
        
        sentiment_summary(news_df, "News")
        n_col1, n_col2 = st.columns([1.1, 1])
        with n_col1:
            st.markdown("#### News sentiment distribution")
            st.bar_chart(sentiment_distribution_frame(news_df), x="Sentiment", y="Records")
        with n_col2:
            st.markdown("#### News executive interpretation")
            news_avg = round(float(news_df["sentiment_score"].mean()), 3) if not news_df.empty and "sentiment_score" in news_df else 0.0
            news_status, news_text = sentiment_status(news_avg)
            news_counts = sentiment_counts(news_df)
            news_total = int(len(news_df))
            news_negative_share = round((int(news_counts.get("Negative", 0)) / news_total) * 100, 1) if news_total else 0.0
            news_positive_share = round((int(news_counts.get("Positive", 0)) / news_total) * 100, 1) if news_total else 0.0
            st.markdown(
                f"""
                <div class="info-card">
                    <h4 style="margin:.1rem 0 .4rem 0;">{news_status}</h4>
                    <p class="small-muted">{news_text}</p>
                    <span class="tag tag-ok">Positive share: {news_positive_share}%</span>
                    <span class="tag tag-risk">Negative share: {news_negative_share}%</span>
                    <span class="tag">Average index: {news_avg}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### Public Sentiment")
        st.caption("External perception estimated from public-facing market sources, including news, competitor coverage, trend articles, and research records.")
        sentiment_summary(public_df, "Public")
        p_col1, p_col2 = st.columns([1.1, 1])
        with p_col1:
            st.markdown("#### Public sentiment distribution")
            st.bar_chart(sentiment_distribution_frame(public_df), x="Sentiment", y="Records")
        with p_col2:
            st.markdown("#### Public sentiment source mix")
            if public_df.empty or "source_category" not in public_df.columns:
                st.info("No source mix available.")
            else:
                source_mix = public_df["source_category"].value_counts().reset_index()
                source_mix.columns = ["Source Category", "Records"]
                st.bar_chart(source_mix, x="Source Category", y="Records")

        st.markdown("### Sentiment Trends")
        trend_df = master_df.dropna(subset=["published_dt"]).copy()
        if trend_df.empty:
            st.warning("Published dates are not clean enough to build a sentiment trend chart.")
        else:
            trend_df["week"] = trend_df["published_dt"].dt.to_period("W").astype(str)
            weekly = trend_df.groupby("week", as_index=False)["sentiment_score"].mean().tail(16)
            weekly["sentiment_score"] = weekly["sentiment_score"].round(3)
            st.line_chart(weekly, x="week", y="sentiment_score")
            latest_avg = float(weekly["sentiment_score"].iloc[-1]) if not weekly.empty else 0.0
            previous_avg = float(weekly["sentiment_score"].iloc[-2]) if len(weekly) > 1 else latest_avg
            direction = "improving" if latest_avg > previous_avg else "weakening" if latest_avg < previous_avg else "stable"
            st.info(f"Latest weekly sentiment is {round(latest_avg, 3)} and appears {direction} compared with the previous available week.")

        with st.expander("Show sentiment-scored records"):
            st.dataframe(
                safe_columns(master_df.copy(), ["title", "source", "source_category", "published", "sentiment_label", "sentiment_score", "sentiment_confidence", "sentiment_method", "url"]).head(300),
                use_container_width=True,
            )


# Section 6: Strategic Recommendations

with tabs[5]:
    st.markdown('<div class="section-title">Section 6: Strategic Recommendations</div>', unsafe_allow_html=True)
    st.caption("Each recommendation includes priority, supporting evidence, expected impact, risk level, and a three-part risk assessment: financial, operational, and strategic risk.")
    if not result:
        st.info("Run the Strategic Agent to generate validated strategic recommendations.")
    else:
        validation = result.get("validation", {})
        st.success(
            f"Validation status: {validation.get('status', 'unknown')} | Confidence: {validation.get('confidence', 'unknown')} | Evidence-backed recommendations only"
        )
        recommendations = result.get("recommendations", [])
        evidence = result.get("evidence", [])

        for idx, rec in enumerate(recommendations, start=1):
            title = rec.get("title", f"Recommendation {idx}")
            priority = rec.get("priority", "Medium")
            risk_level = rec.get("risk_level", "Medium")
            evidence_refs = rec.get("evidence_refs", [])
            impact = expected_impact_for_recommendation(title)
            risk_assessment = recommendation_risk_assessment(title, risk_level)
            risk_assessment_html = render_risk_assessment_boxes(risk_assessment)

            st.markdown(
                f"""
                <div class="recommendation-card">
                    <h3 style="margin-top:0;">{idx}. {title}</h3>
                    <span class="tag tag-ok">Priority: {priority}</span>
                    <span class="tag tag-risk">Risk Level: {risk_level}</span>
                    <span class="tag">Evidence: {', '.join(['E' + str(ref) for ref in evidence_refs]) if evidence_refs else 'Needs stronger evidence'}</span>
                    <p style="margin-top:.75rem;"><b>Recommendation:</b> {rec.get('rationale', '')}</p>
                    <p><b>Expected Impact:</b> {impact}</p>
                    <p><b>Risk Assessment:</b></p>
                    {risk_assessment_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander(f"Supporting evidence for recommendation {idx}"):
                if not evidence_refs:
                    st.warning("No direct evidence references attached to this recommendation.")
                for ref in evidence_refs:
                    item = next((e for e in evidence if int(e.get("evidence_id", -1)) == int(ref)), None)
                    if item:
                        st.markdown(f"**E{item.get('evidence_id')}: {item.get('title', '')}**")
                        st.caption(f"{item.get('source', '')} | {item.get('category', '')} | {item.get('published', '')}")
                        st.write(clean_evidence_snippet(item))
                        if item.get("url"):
                            st.markdown(f"[Open source]({item.get('url')})")


# Section 7: CEO Briefing

with tabs[6]:
    st.markdown('<div class="section-title">Section 7: CEO Briefing</div>', unsafe_allow_html=True)

    st.markdown(
        "Use this section to ask a CEO-level strategic question. The dashboard will run the agent and return a direct executive summary that naturally covers what happened, why it matters, and what management should do next."
    )

    ceo_goal = st.text_area(
        "CEO briefing question",
        value=DEFAULT_GOAL,
        height=105,
        key="ceo_goal_input",
    )

    run_ceo_clicked = st.button("Generate CEO Briefing", type="primary", use_container_width=True)
    if run_ceo_clicked:
        if master_df.empty:
            st.error("No processed data found. Run the data pipeline first.")
        else:
            with st.spinner("Running strategic agent: planning, retrieval, signal analysis, recommendation scoring, validation, and final executive wording..."):
                st.session_state["last_agent_result"] = run_strategic_agent(
                    goal=ceo_goal,
                    model=model,
                    n_per_query=n_per_query,
                )
            st.success("CEO briefing generated.")
            st.rerun()

    result = get_agent_result()

    if not result:
        st.info("Enter a CEO-level question above and click Generate CEO Briefing.")
    else:
        evidence = result.get("evidence", [])
        recommendations = result.get("recommendations", [])
        validation = result.get("validation", {})

        st.markdown("### Executive Summary")
        st.caption(
            "This is a direct CEO answer. It is not displayed as three separate Q&A boxes, but it still covers the required logic: what happened, why it matters, and what management should do next."
        )
        render_executive_summary(result)

        v1, v2, v3 = st.columns(3)
        with v1:
            kpi_card("Validation", validation.get("status", "unknown"), "recommendation check")
        with v2:
            kpi_card("Confidence", validation.get("confidence", "unknown"), "evidence strength")
        with v3:
            kpi_card("Evidence Used", len(evidence), "retrieved items")

        st.markdown("### Management Priorities")
        render_management_priorities(recommendations)

        with st.expander("Optional: local LLM wording for technical review"):
            st.caption("This is hidden by default and is not used as the visible executive summary. The main CEO summary above is built from validated agent outputs to avoid unsupported claims.")
            st.markdown(result.get("final_answer", "No generated wording available."))

        st.markdown("### Evidence Pack")
        st.markdown(
            """
            <div class="evidence-note">
                The evidence pack shows the retrieved source chunks used by the agent. These references support the recommendations shown above.
            </div>
            """,
            unsafe_allow_html=True,
        )
        for item in evidence[:10]:
            with st.expander(f"E{item.get('evidence_id')}: {item.get('title', '')[:95]}"):
                st.caption(f"{item.get('source', '')} | {item.get('category', '')} | {item.get('published', '')} | similarity: {item.get('similarity', '')}")
                st.write(clean_evidence_snippet(item))
                if item.get("url"):
                    st.markdown(f"[Open source]({item.get('url')})")
