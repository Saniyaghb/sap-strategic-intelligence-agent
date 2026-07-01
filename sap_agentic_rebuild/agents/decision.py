from __future__ import annotations

from typing import Any


def _evidence_refs(signal_label: str, signal_analysis: dict[str, Any], max_refs: int = 3) -> list[int]:
    refs = signal_analysis.get("evidence_map", {}).get(signal_label, [])
    return [int(item["evidence_id"]) for item in refs[:max_refs] if "evidence_id" in item]


def _recommendation(title: str, rationale: str, priority: str, evidence_refs: list[int], risk_level: str) -> dict:
    return {
        "title": title,
        "rationale": rationale,
        "priority": priority,
        "evidence_refs": evidence_refs,
        "risk_level": risk_level,
    }


def decide_recommendations(intent: str, signal_analysis: dict[str, Any], profile: dict[str, Any]) -> list[dict]:
    opportunities = [label for label, _count in signal_analysis.get("opportunities", [])]
    risks = [label for label, _count in signal_analysis.get("risks", [])]
    trends = [label for label, _count in signal_analysis.get("trends", [])]

    recs: list[dict] = []

    
    ai_signal = next((x for x in opportunities + trends if "AI" in x or "agent" in x.lower()), None)
    if ai_signal:
        recs.append(
            _recommendation(
                "Prioritize evidence-backed Business AI and agentic workflow use cases",
                "SAP should focus on AI use cases that are directly connected to ERP, analytics, automation, and measurable customer productivity, instead of vague AI branding.",
                "High",
                _evidence_refs(ai_signal, signal_analysis),
                "Medium",
            )
        )

    
    cloud_signal = next((x for x in opportunities + trends if "cloud" in x.lower() or "s/4hana" in x.lower() or "data platform" in x.lower()), None)
    if cloud_signal:
        recs.append(
            _recommendation(
                "Accelerate cloud ERP modernization while protecting customer migration trust",
                "SAP should use cloud ERP migration as the commercial backbone, but reduce friction through clear migration support, integration reliability, and transparent value cases.",
                "High",
                _evidence_refs(cloud_signal, signal_analysis),
                "Medium",
            )
        )

    
    competitor_signal = next((x for x in risks if "compet" in x.lower() or any(v in x.lower() for v in ["oracle", "microsoft", "salesforce", "workday"])), None)
    if competitor_signal:
        recs.append(
            _recommendation(
                "Defend SAP's enterprise suite against hyperscaler and SaaS competitors",
                "SAP should differentiate through process depth, embedded data, industry-specific workflows, and integration with the existing enterprise core.",
                "High",
                _evidence_refs(competitor_signal, signal_analysis),
                "High",
            )
        )


    risk_signal = next((x for x in risks if any(v in x.lower() for v in ["regulatory", "security", "privacy", "legal"])), None)
    if risk_signal:
        recs.append(
            _recommendation(
                "Strengthen AI governance, compliance, and security controls",
                "SAP should treat trust as a product feature because enterprise customers will not adopt AI in core processes without governance, auditability, and security.",
                "Medium",
                _evidence_refs(risk_signal, signal_analysis),
                "Medium",
            )
        )

    
    if len(recs) < 3:
        recs.append(
            _recommendation(
                "Build a source-diverse strategic monitoring loop",
                f"The current knowledge base contains {profile.get('document_count', 0)} documents across {profile.get('source_count', 0)} sources. SAP should continuously monitor company, market, competitor, trend, and research signals before making strategic moves.",
                "Medium",
                [1] if profile.get("document_count", 0) else [],
                "Low",
            )
        )

    if len(recs) < 3:
        recs.append(
            _recommendation(
                "Convert retrieved evidence into quarterly executive decisions",
                "The system should not stop at summarization. Each intelligence run should produce decisions, owners, validation checks, and follow-up questions for management.",
                "Medium",
                [1],
                "Low",
            )
        )

    
    if intent == "risk_assessment":
        recs.sort(key=lambda rec: 0 if rec["risk_level"] == "High" else 1)
    elif intent == "opportunity_discovery":
        recs.sort(key=lambda rec: 0 if "Prioritize" in rec["title"] or "Accelerate" in rec["title"] else 1)

    return recs[:3]
