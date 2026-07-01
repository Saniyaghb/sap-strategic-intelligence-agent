from __future__ import annotations

from config import COMPANY_NAME


def classify_goal(goal: str) -> str:
    text = goal.lower()
    if any(word in text for word in ["risk", "threat", "problem", "concern"]):
        return "risk_assessment"
    if any(word in text for word in ["opportunity", "growth", "invest", "expand"]):
        return "opportunity_discovery"
    if any(word in text for word in ["competitor", "oracle", "microsoft", "salesforce", "workday"]):
        return "competitive_strategy"
    if any(word in text for word in ["trend", "future", "ai", "agent", "automation"]):
        return "trend_strategy"
    return "ceo_strategy"


def build_retrieval_queries(goal: str, intent: str) -> list[str]:
    base = [goal]

    if intent == "risk_assessment":
        base.extend([
            f"{COMPANY_NAME} risks competition regulation security cloud AI",
            f"{COMPANY_NAME} investor risk earnings cloud transition",
            "enterprise software AI regulation security risk",
        ])
    elif intent == "opportunity_discovery":
        base.extend([
            f"{COMPANY_NAME} opportunity business AI cloud ERP growth",
            f"{COMPANY_NAME} partnerships customers innovation S/4HANA",
            "enterprise AI automation data platform opportunity",
        ])
    elif intent == "competitive_strategy":
        base.extend([
            f"{COMPANY_NAME} competitors Oracle Microsoft Salesforce Workday",
            "Oracle ERP Microsoft Dynamics Salesforce AI Workday cloud ERP",
            f"{COMPANY_NAME} competitive advantage business AI cloud ERP",
        ])
    elif intent == "trend_strategy":
        base.extend([
            "enterprise AI agents RAG business intelligence trends",
            f"{COMPANY_NAME} business AI cloud ERP automation trend",
            "AI agents enterprise software ERP cloud data platform",
        ])
    else:
        base.extend([
            f"{COMPANY_NAME} CEO strategy business AI cloud ERP risks opportunities",
            f"{COMPANY_NAME} earnings investor relations AI cloud growth",
            f"{COMPANY_NAME} competitors Oracle Microsoft Salesforce Workday ERP",
            "enterprise AI agents cloud ERP automation regulation trends",
        ])

    # Removing duplicates while preserving order.
    return list(dict.fromkeys(base))


def create_execution_plan(goal: str, intent: str) -> list[dict]:
    return [
        {"step": 1, "name": "Understand goal", "action": f"Classify the user goal as {intent}."},
        {"step": 2, "name": "Plan retrieval", "action": "Create multiple evidence queries instead of using only the raw user question."},
        {"step": 3, "name": "Use tools", "action": "Run dataset profiling, vector retrieval, and signal analysis tools."},
        {"step": 4, "name": "Analyze", "action": "Identify risks, opportunities, trends, evidence strength, and source diversity."}, 
        {"step": 5, "name": "Decide", "action": "Score and rank strategic recommendations using retrieved evidence."},
        {"step": 6, "name": "Validate", "action": "Check that every recommendation is supported by evidence before presenting it."},
        {"step": 7, "name": "Recommend", "action": "Send only validated structured context to the LLM backend for final wording."},
        {"step": 8, "name": "Remember", "action": "Store the run summary and recommendation titles in local memory."},
    ]
