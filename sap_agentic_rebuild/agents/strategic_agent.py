from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from config import AGENT_TRACE_FILE
from agents.decision import decide_recommendations
from agents.llm_client import generate_validated_briefing
from agents.memory import load_memory, update_memory
from agents.planner import build_retrieval_queries, classify_goal, create_execution_plan
from agents.tools import dataset_profile_tool, evidence_retrieval_tool, signal_analysis_tool
from agents.validator import validate_recommendations


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _compact_evidence(items: list[dict]) -> list[dict]:
    compact = []
    for idx, item in enumerate(items, start=1):
        meta = item.get("metadata", {})
        compact.append(
            {
                "evidence_id": idx,
                "title": meta.get("title", ""),
                "source": meta.get("source", ""),
                "category": meta.get("source_category", ""),
                "published": meta.get("published", ""),
                "url": meta.get("url", ""),
                "similarity": item.get("similarity"),
                "query": item.get("query", ""),
                "snippet": str(item.get("text", ""))[:500],
            }
        )
    return compact


def run_strategic_agent(goal: str, model: str | None = None, n_per_query: int = 4) -> dict[str, Any]:
    """
    Main agent controller.

    This is the part to explain in the exam:
    Goal -> Plan -> Retrieve -> Analyze -> Decide -> Recommend -> Validate -> Memory

    The LLM is only called near the end for final wording.
    """
    started_at = _now()
    memory_before = load_memory()

    # 1. Autonomous goal understanding.
    intent = classify_goal(goal)

    # 2. Planning before execution.
    plan = create_execution_plan(goal, intent)
    queries = build_retrieval_queries(goal, intent)

    execution_trace: list[dict] = [
        {"stage": "goal_received", "detail": goal, "timestamp": started_at},
        {"stage": "intent_classification", "detail": intent, "timestamp": _now()},
        {"stage": "planning", "detail": plan, "timestamp": _now()},
        {"stage": "query_generation", "detail": queries, "timestamp": _now()},
    ]

    # 3. Tool usage beyond the LLM.
    profile = dataset_profile_tool()
    execution_trace.append({"stage": "tool_used", "tool": "dataset_profile", "detail": profile, "timestamp": _now()})

    retrieved = evidence_retrieval_tool(queries, n_per_query=n_per_query)
    evidence_items = retrieved.get("items", [])
    execution_trace.append(
        {
            "stage": "tool_used",
            "tool": "evidence_retrieval",
            "detail": {"queries": queries, "result_count": len(evidence_items)},
            "timestamp": _now(),
        }
    )

    # 4. Analysis of risks, opportunities, and trends.
    signal_analysis = signal_analysis_tool(evidence_items)
    execution_trace.append(
        {
            "stage": "tool_used",
            "tool": "signal_analysis",
            "detail": {
                "opportunities": signal_analysis.get("opportunities", [])[:5],
                "risks": signal_analysis.get("risks", [])[:5],
                "trends": signal_analysis.get("trends", [])[:5],
            },
            "timestamp": _now(),
        }
    )

    # 5. Decision-making.
    recommendations = decide_recommendations(intent, signal_analysis, profile)
    execution_trace.append({"stage": "decision", "detail": recommendations, "timestamp": _now()})

    # 6. Validation before presenting.
    validation = validate_recommendations(recommendations, evidence_items, profile)
    execution_trace.append({"stage": "validation", "detail": validation, "timestamp": _now()})

    # 7. LLM final synthesis. The LLM is not the agent; it is the writer/backend.
    final_answer = generate_validated_briefing(
        goal=goal,
        plan=plan,
        recommendations=recommendations,
        validation=validation,
        evidence_items=evidence_items,
        signal_analysis=signal_analysis,
        model=model,
    )
    execution_trace.append({"stage": "llm_synthesis", "detail": "Final answer generated from validated context.", "timestamp": _now()})

    # 8. Memory update.
    memory_after = update_memory(goal, intent, recommendations, validation)
    execution_trace.append({"stage": "memory_update", "detail": "Run summary saved to agent_memory.json", "timestamp": _now()})

    result = {
        "goal": goal,
        "intent": intent,
        "model": model,
        "started_at": started_at,
        "finished_at": _now(),
        "plan": plan,
        "queries": queries,
        "tools_used": ["dataset_profile", "evidence_retrieval", "signal_analysis", "recommendation_validator", "agent_memory"],
        "profile": profile,
        "signals": {
            "opportunities": signal_analysis.get("opportunities", []),
            "risks": signal_analysis.get("risks", []),
            "trends": signal_analysis.get("trends", []),
            "source_diversity": signal_analysis.get("source_diversity", []),
            "category_diversity": signal_analysis.get("category_diversity", []),
        },
        "recommendations": recommendations,
        "validation": validation,
        "final_answer": final_answer,
        "evidence": _compact_evidence(evidence_items),
        "memory_before_run_count": len(memory_before.get("runs", [])),
        "memory_after_run_count": len(memory_after.get("runs", [])),
        "execution_trace": execution_trace,
    }

    AGENT_TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    AGENT_TRACE_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    return result


if __name__ == "__main__":
    demo_goal = "If you were the CEO of SAP today, what should management do next and why?"
    output = run_strategic_agent(demo_goal)
    print(output["final_answer"])
