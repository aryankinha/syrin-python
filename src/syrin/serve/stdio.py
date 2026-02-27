"""STDIO JSON lines protocol — background / subprocess serving."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from syrin.agent import Agent
    from syrin.serve.config import ServeConfig


def run_stdio_protocol(
    agent: Agent,
    config: ServeConfig,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> None:
    """Run STDIO JSON lines protocol. Blocks until EOF on stdin.

    Reads one JSON per line from stdin. Each line: {"input": "..."} or {"message": "..."}
    with optional "thread_id". Writes one JSON per line to stdout with content, cost,
    tokens, thread_id.

    Args:
        agent: Agent to run.
        config: Serve config.
        stdin: Input stream. Defaults to sys.stdin.
        stdout: Output stream. Defaults to sys.stdout. Use for testing without patching.
    """
    inp = stdin if stdin is not None else sys.stdin
    out = stdout if stdout is not None else sys.stdout

    def _write_out(obj: dict[str, object]) -> None:
        out.write(json.dumps(obj) + "\n")
        out.flush()

    for line in inp:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            _write_out({"error": f"Invalid JSON: {e}"})
            continue
        msg = obj.get("input") or obj.get("message") or obj.get("content")
        thread_id = obj.get("thread_id")
        if not isinstance(msg, str) or not msg.strip():
            _write_out({"error": "Missing 'input', 'message', or 'content'"})
            continue
        try:
            r = agent.response(msg.strip())
            payload = {
                "content": str(r.content),
                "cost": r.cost,
                "tokens": r.tokens.total_tokens if r.tokens else 0,
            }
            if thread_id is not None:
                payload["thread_id"] = thread_id
            _write_out(payload)
        except Exception as e:
            _write_out({"error": str(e), "thread_id": thread_id})
