from __future__ import annotations

from typing import Any


def validate_recommendations(recommendations: list[dict], evidence_items: list[dict], profile: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []

    if not evidence_items:
        issues.append("No retrieved evidence was available.")

    if profile.get("document_count", 0) < 100:
        warnings.append("Dataset has fewer than 100 documents, so strategic confidence is limited.")

    if profile.get("source_count", 0) < 3:
        warnings.append("Fewer than 3 sources are represented in the knowledge base.")

    evidence_count = len(evidence_items)
    for rec in recommendations:
        refs = rec.get("evidence_refs", [])
        if not refs:
            issues.append(f"Recommendation has no evidence reference: {rec.get('title', '')}")
        for ref in refs:
            if not isinstance(ref, int) or ref < 1 or ref > evidence_count:
                issues.append(f"Invalid evidence reference {ref} in recommendation: {rec.get('title', '')}")

    unique_categories = {
        item.get("metadata", {}).get("source_category", "unknown") for item in evidence_items
    }
    if len(unique_categories) < 2:
        warnings.append("Retrieved evidence has low category diversity.")

    status = "pass" if not issues else "needs_review"
    confidence = "High" if status == "pass" and not warnings else "Medium" if status == "pass" else "Low"

    return {
        "tool": "recommendation_validator",
        "status": status,
        "confidence": confidence,
        "issues": issues,
        "warnings": warnings,
        "evidence_count": evidence_count,
        "source_category_count": len(unique_categories),
    }
