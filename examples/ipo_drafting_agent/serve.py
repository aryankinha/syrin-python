#!/usr/bin/env python3
"""Serve the DRHP Drafting Agent over HTTP.

Usage:
    cd examples/ipo_drafting_agent
    uv run python serve.py

Then:
    curl -X POST http://localhost:8000/chat \\
      -H "Content-Type: application/json" \\
      -d '{"message": "Draft the Capital Structure and Shareholding Pattern section."}'

Or visit http://localhost:8000/playground (if syrin[serve] with playground).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(_SCRIPT_DIR / ".env")
load_dotenv(_SCRIPT_DIR.parent / ".env")


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY required. Set in .env or environment.")
        return

    from ipo_agent.agent import create_agent

    from syrin.serve.config import ServeConfig

    agent = create_agent(data_dir=_SCRIPT_DIR / "data", api_key=api_key)
    print("Serving at http://localhost:8000")
    print("  POST /chat  — send message, get response")
    agent.serve(port=8000, config=ServeConfig(enable_playground=True, debug=True))


if __name__ == "__main__":
    main()
