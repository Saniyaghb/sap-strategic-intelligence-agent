from __future__ import annotations

from typing import Any

try:
    import ollama
except Exception:  # Ollama package may not be installed in every environment.
    ollama = None

from config import OLLAMA_MODEL
from rag.retriever import format_evidence


def _format_recommendations(recommendations: list[dict]) -> str:
    lines = []
    for idx, rec in enumerate(recommendations, start=1):
        lines.append(
            f"{idx}. {rec.get('title')}\n"
            f"   Priority: {rec.get('priority')}\n"
            f"   Risk level: {rec.get('risk_level')}\n"
            f"   Evidence refs: {rec.get('evidence_refs')}\n"
            f"   Rationale: {rec.get('rationale')}"
        )
    return "\n".join(lines)


def fallback_briefing(goal: str, recommendations: list[dict], validation: dict, signal_analysis: dict) -> str:
    rec_lines = []
    for rec in recommendations:
        refs = ", ".join([f"Evidence {ref}" for ref in rec.get("evidence_refs", [])]) or "No direct evidence reference"
        rec_lines.append(
            f"- {rec['title']} | Priority: {rec['priority']} | Risk: {rec['risk_level']} | {refs}\n"
            f"  {rec['rationale']}"
        )

    return f"""# Direct Answer
For the goal: {goal}, SAP should focus on the validated recommendations below. The answer is generated from the agent's retrieved evidence and deterministic analysis layer. The LLM backend was not available, so this fallback briefing is produced without hallucinating extra claims.

# Key Signals
Opportunities: {signal_analysis.get('opportunities', [])[:5]}
Risks: {signal_analysis.get('risks', [])[:5]}
Trends: {signal_analysis.get('trends', [])[:5]}

# Strategic Recommendations
{chr(10).join(rec_lines)}

# Validation
Status: {validation.get('status')}
Confidence: {validation.get('confidence')}
Warnings: {validation.get('warnings')}
Issues: {validation.get('issues')}
"""


def generate_validated_briefing(
    goal: str,
    plan: list[dict],
    recommendations: list[dict],
    validation: dict,
    evidence_items: list[dict],
    signal_analysis: dict[str, Any],
    model: str | None = None,
) -> str:
    selected_model = model or OLLAMA_MODEL
    evidence_text = format_evidence(evidence_items, max_chars=4500)
    rec_text = _format_recommendations(recommendations)

    prompt = f"""
You are writing a short CEO-level briefing for SAP.

The Python agent already planned, retrieved evidence, analyzed signals, selected recommendations, and validated them.
You are only the final writing layer.

Answer the user's question directly in 4 short paragraphs, then add exactly 3 numbered management priorities.
Do not use headings except:
# CEO Briefing
# Management Priorities

Rules:
- Use only the provided evidence, signal analysis, validation result, and validated recommendations.
- Do not invent numbers, percentages, dates, market sizes, sectors, customer segments, company names, or confidence scores.
- If a detail is not explicitly present in the provided evidence or recommendations, do not include it.
- Do not create new recommendations.
- Do not create tables.
- Keep the full answer under 600 words.
- Prefer cautious wording such as "the retrieved evidence suggests" instead of unsupported certainty.

USER GOAL:
{goal}

VALIDATED RECOMMENDATIONS:
{rec_text}

VALIDATION RESULT:
{validation}

SIGNAL ANALYSIS:
Opportunities: {signal_analysis.get('opportunities')}
Risks: {signal_analysis.get('risks')}
Trends: {signal_analysis.get('trends')}

EVIDENCE:
{evidence_text}
"""

    if ollama is None:
        return fallback_briefing(goal, recommendations, validation, signal_analysis) + "\n\nLLM backend note: Python package `ollama` is not installed."

    try:
        response = ollama.chat(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3, "num_predict": 600},
        )
        return response["message"]["content"]
    except Exception as exc:
        return fallback_briefing(goal, recommendations, validation, signal_analysis) + f"\n\nLLM backend note: {exc}"
