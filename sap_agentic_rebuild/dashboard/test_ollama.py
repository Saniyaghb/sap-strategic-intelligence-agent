from __future__ import annotations

import ollama
from config import OLLAMA_MODEL


def main() -> None:
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": "Reply with one sentence: Ollama is working."}],
    )
    print(response["message"]["content"])


if __name__ == "__main__":
    main()
