from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import AGENT_MEMORY_FILE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_memory(path: Path = AGENT_MEMORY_FILE) -> dict[str, Any]:
    if not path.exists():
        return {"runs": [], "known_goals": [], "last_recommendations": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"runs": [], "known_goals": [], "last_recommendations": []}


def save_memory(memory: dict[str, Any], path: Path = AGENT_MEMORY_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")


def update_memory(goal: str, intent: str, recommendations: list[dict], validation: dict) -> dict[str, Any]:
    memory = load_memory()
    run_summary = {
        "timestamp": _now(),
        "goal": goal,
        "intent": intent,
        "recommendation_titles": [rec.get("title", "") for rec in recommendations],
        "validation_status": validation.get("status", "unknown"),
    }
    memory.setdefault("runs", []).append(run_summary)
    memory["runs"] = memory["runs"][-20:]

    if goal not in memory.setdefault("known_goals", []):
        memory["known_goals"].append(goal)
        memory["known_goals"] = memory["known_goals"][-20:]

    memory["last_recommendations"] = recommendations[:5]
    save_memory(memory)
    return memory
