from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from config import AUTO_REFRESH_HOURS, CHROMA_DIR, PROCESSED_DIR, SCHEDULER_STATUS_FILE

ROOT = Path(__file__).resolve().parent
MASTER_FILE = PROCESSED_DIR / "master_data.csv"
CHUNKS_FILE = PROCESSED_DIR / "chunks.csv"
LOCK_FILE = ROOT / ".pipeline.lock"
REFRESH_SECONDS = AUTO_REFRESH_HOURS * 60 * 60


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_status(**updates) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    status = {}
    if SCHEDULER_STATUS_FILE.exists():
        try:
            status = json.loads(SCHEDULER_STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            status = {}
    status.update(updates)
    status["updated_at"] = iso_now()
    SCHEDULER_STATUS_FILE.write_text(json.dumps(status, indent=2), encoding="utf-8")


def file_age_seconds(path: Path) -> float | None:
    if not path.exists():
        return None
    return time.time() - path.stat().st_mtime


def chroma_has_files() -> bool:
    return CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir())


def pipeline_is_needed() -> tuple[bool, str]:
    if not MASTER_FILE.exists():
        return True, "master_data.csv is missing"
    if not CHUNKS_FILE.exists():
        return True, "chunks.csv is missing"
    if not chroma_has_files():
        return True, "ChromaDB index is missing"
    age = file_age_seconds(MASTER_FILE)
    if age is not None and age >= REFRESH_SECONDS:
        return True, f"processed data is {round(age / 3600, 2)} hours old"
    return False, "processed data and vector store are ready"


def lock_is_stale() -> bool:
    age = file_age_seconds(LOCK_FILE)
    return age is not None and age > 2 * 60 * 60


def run_pipeline(reason: str) -> bool:
    if LOCK_FILE.exists() and not lock_is_stale():
        write_status(status="skipped", reason="Pipeline already running")
        return False
    if LOCK_FILE.exists() and lock_is_stale():
        LOCK_FILE.unlink(missing_ok=True)

    LOCK_FILE.write_text(iso_now(), encoding="utf-8")
    write_status(status="running", reason=reason, started_at=iso_now())

    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "run_pipeline.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60 * 60,
        )
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode == 0:
            write_status(status="success", reason=reason, last_success_at=iso_now(), last_output=output[-4000:])
            return True
        write_status(status="failed", reason=reason, last_failure_at=iso_now(), last_output=output[-4000:])
        return False
    except Exception as exc:
        write_status(status="failed", reason=reason, last_failure_at=iso_now(), last_output=str(exc))
        return False
    finally:
        LOCK_FILE.unlink(missing_ok=True)


def scheduler_loop(stop_event: threading.Event) -> None:
    while not stop_event.wait(REFRESH_SECONDS):
        run_pipeline(f"scheduled {AUTO_REFRESH_HOURS}-hour refresh")


def start_streamlit() -> int:
    app_file = ROOT / "dashboard" / "app.py"
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app_file)], cwd=str(ROOT))


def main() -> None:
    print("SAP Agentic Strategic Intelligence Dashboard")
    print(f"Automatic refresh interval: every {AUTO_REFRESH_HOURS} hours")

    needed, reason = pipeline_is_needed()
    if needed:
        print(f"Running startup pipeline because {reason}")
        run_pipeline(f"startup refresh because {reason}")
    else:
        print(f"Skipping startup pipeline: {reason}")
        write_status(status="ready", reason=reason)

    stop_event = threading.Event()
    thread = threading.Thread(target=scheduler_loop, args=(stop_event,), daemon=True)
    thread.start()

    try:
        start_streamlit()
    finally:
        stop_event.set()


if __name__ == "__main__":
    main()
