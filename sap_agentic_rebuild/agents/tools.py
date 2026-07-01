from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import pandas as pd

from config import PROCESSED_DIR
from rag.retriever import retrieve_multi_query

OPPORTUNITY_TERMS = {
    "ai": "Business AI and automation",
    "agent": "AI agents and autonomous workflows",
    "cloud": "Cloud migration and cloud ERP",
    "s/4hana": "S/4HANA modernization",
    "rise": "RISE with SAP growth",
    "partnership": "Partnership ecosystem expansion",
    "data": "Data platform and analytics",
    "growth": "Revenue or market growth",
    "innovation": "Product innovation",
    "customer": "Customer adoption",
}

RISK_TERMS = {
    "risk": "General strategic risk",
    "competition": "Competitive pressure",
    "competitor": "Competitive pressure",
    "oracle": "Oracle competitive pressure",
    "microsoft": "Microsoft Dynamics / cloud competition",
    "salesforce": "Salesforce AI / CRM competition",
    "workday": "Workday HCM / ERP competition",
    "regulation": "Regulatory or compliance pressure",
    "security": "Security and privacy risk",
    "privacy": "Security and privacy risk",
    "lawsuit": "Legal risk",
    "cost": "Cost pressure",
    "decline": "Market slowdown risk",
    "outage": "Operational reliability risk",
}

TREND_TERMS = {
    "generative ai": "Generative AI in enterprise software",
    "business ai": "Business AI embedded into ERP workflows",
    "ai agent": "Agentic AI workflows",
    "automation": "Workflow automation",
    "cloud erp": "Cloud ERP modernization",
    "data platform": "Unified data platforms",
    "sovereign cloud": "Sovereign cloud and compliance",
    "sustainability": "Sustainability and ESG technology",
}


def _parse_date(value: str) -> datetime | None:
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except Exception:
        try:
            return pd.to_datetime(value, utc=True).to_pydatetime()
        except Exception:
            return None


def dataset_profile_tool() -> dict[str, Any]:
    """Tool: read the local knowledge base snapshot and summarize coverage."""
    master_file = PROCESSED_DIR / "master_data.csv"
    chunks_file = PROCESSED_DIR / "chunks.csv"

    if not master_file.exists():
        return {"tool": "dataset_profile", "status": "missing", "message": "master_data.csv not found"}

    df = pd.read_csv(master_file).fillna("")
    chunk_count = 0
    if chunks_file.exists():
        chunk_count = len(pd.read_csv(chunks_file))

    parsed_dates = [_parse_date(v) for v in df.get("published", [])]
    parsed_dates = [d for d in parsed_dates if d is not None]
    latest_date = max(parsed_dates).isoformat() if parsed_dates else "unknown"

    return {
        "tool": "dataset_profile",
        "status": "ok",
        "document_count": int(len(df)),
        "chunk_count": int(chunk_count),
        "source_count": int(df["source"].nunique()) if "source" in df else 0,
        "category_counts": df["source_category"].value_counts().to_dict() if "source_category" in df else {},
        "top_sources": df["source"].value_counts().head(8).to_dict() if "source" in df else {},
        "latest_published": latest_date,
    }


def evidence_retrieval_tool(queries: list[str], n_per_query: int = 5) -> dict[str, Any]:
    """Tool: retrieve evidence from ChromaDB using multiple agent-created queries."""
    items = retrieve_multi_query(queries, n_per_query=n_per_query)
    return {
        "tool": "evidence_retrieval",
        "status": "ok",
        "queries": queries,
        "result_count": len(items),
        "items": items,
    }


def _find_terms(text: str, term_map: dict[str, str]) -> list[str]:
    text_l = text.lower()
    found = []
    for term, label in term_map.items():
        if term in text_l:
            found.append(label)
    return found


def _short_snippet(text: str, max_len: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[:max_len].rstrip() + ("..." if len(text) > max_len else "")


def signal_analysis_tool(evidence_items: list[dict]) -> dict[str, Any]:
    """Tool: extract opportunities, risks, trends, and source diversity from evidence."""
    opportunities: Counter[str] = Counter()
    risks: Counter[str] = Counter()
    trends: Counter[str] = Counter()
    evidence_map: dict[str, list[dict]] = {}
    categories: Counter[str] = Counter()
    sources: Counter[str] = Counter()

    for idx, item in enumerate(evidence_items, start=1):
        text = f"{item.get('metadata', {}).get('title', '')} {item.get('text', '')}"
        meta = item.get("metadata", {})
        categories[str(meta.get("source_category", "unknown"))] += 1
        sources[str(meta.get("source", "unknown"))] += 1

        for label in _find_terms(text, OPPORTUNITY_TERMS):
            opportunities[label] += 1
            evidence_map.setdefault(label, []).append({"evidence_id": idx, "title": meta.get("title", ""), "snippet": _short_snippet(item.get("text", ""))})
        for label in _find_terms(text, RISK_TERMS):
            risks[label] += 1
            evidence_map.setdefault(label, []).append({"evidence_id": idx, "title": meta.get("title", ""), "snippet": _short_snippet(item.get("text", ""))})
        for label in _find_terms(text, TREND_TERMS):
            trends[label] += 1
            evidence_map.setdefault(label, []).append({"evidence_id": idx, "title": meta.get("title", ""), "snippet": _short_snippet(item.get("text", ""))})

    return {
        "tool": "signal_analysis",
        "status": "ok",
        "opportunities": opportunities.most_common(8),
        "risks": risks.most_common(8),
        "trends": trends.most_common(8),
        "source_diversity": sources.most_common(),
        "category_diversity": categories.most_common(),
        "evidence_map": evidence_map,
    }
