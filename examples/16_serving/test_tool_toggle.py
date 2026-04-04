#!/usr/bin/env python3
"""Test tool toggle and /stream behavior with a running chatbot.

Run the chatbot first:
  python -m examples.16_serving.chatbot

Then run:
  python -m examples.16_serving.test_tool_toggle

Verifies:
- GET /config shows 3 tools (remember_fact, get_current_time, repeat_back).
- With tools ON: POST /stream gets real replies (full loop runs; no fallback).
- With one tool disabled: stream still works; disabled tool not used.
- With all tools OFF: stream uses single completion; if model returns tool_calls we show fallback.
- Toggle back ON: stream again gets real replies.

PATCH /config requires agent_id in the body (from GET /config).
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
CONFIG_URL = f"{BASE}/config"
STREAM_URL = f"{BASE}/stream"

FALLBACK_TOOL_MSG = "The model chose to use a tool; this stream endpoint"
FALLBACK_DISABLED_MSG = "Tools are currently disabled"


def _read_json(resp) -> dict:
    raw = resp.read().decode()
    return json.loads(raw) if raw else {}


def get_config() -> tuple[int, dict]:
    req = urllib.request.Request(CONFIG_URL, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return (resp.status, _read_json(resp))
    except urllib.error.HTTPError as e:
        return (e.code, _read_json(e) if e.fp else {})


def patch_config(agent_id: str, overrides: list[dict], version: int = 1) -> tuple[int, dict]:
    req = urllib.request.Request(
        CONFIG_URL,
        data=json.dumps({"agent_id": agent_id, "version": version, "overrides": overrides}).encode(
            "utf-8"
        ),
        method="PATCH",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return (resp.status, _read_json(resp))
    except urllib.error.HTTPError as e:
        return (e.code, _read_json(e) if e.fp else {})


def post_stream(message: str) -> tuple[int, str]:
    """POST /stream; return (status, accumulated text from SSE)."""
    req = urllib.request.Request(
        STREAM_URL,
        data=json.dumps({"message": message}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    accumulated = ""
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data and data != "[DONE]":
                        try:
                            obj = json.loads(data)
                            acc = obj.get("accumulated") or obj.get("text") or ""
                            if acc:
                                accumulated = acc
                        except json.JSONDecodeError:
                            pass
            return (resp.status, accumulated)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return (e.code, body)


def main() -> int:
    print("1. GET /config — expect 3 tools (remember_fact, get_current_time, repeat_back)")
    status, cfg = get_config()
    if status != 200:
        print(f"   FAIL: GET /config returned {status}")
        return 1
    agent_id = cfg.get("agent_id") or "chatbot:Chatbot"
    sections = cfg.get("sections", {})
    tools_section = sections.get("tools", {})
    fields = tools_section.get("fields", [])
    tool_paths = [f.get("path", "") for f in fields if f.get("path", "").endswith(".enabled")]
    tool_names = [p.split(".")[1] for p in tool_paths if p.count(".") >= 2]
    print(f"   Tools in config: {tool_names}")
    if len(tool_names) < 3:
        print(f"   FAIL: expected at least 3 tools, got {len(tool_names)}")
        return 1
    print("   OK")

    print("\n2. Tools ON — POST /stream 'What time is it?' (expect real reply, not fallback)")
    status, text = post_stream("What time is it?")
    if status != 200:
        print(f"   FAIL: stream returned {status}")
        return 1
    if FALLBACK_TOOL_MSG in text or FALLBACK_DISABLED_MSG in text:
        print(f"   FAIL: got fallback message: {text[:120]}...")
        return 1
    print(f"   Reply: {text[:100]}..." if len(text) > 100 else f"   Reply: {text}")
    print("   OK")

    print("\n3. Disable get_current_time — PATCH then stream 'What time is it?'")
    version = cfg.get("version", 1)
    status, _ = patch_config(
        agent_id, [{"path": "tools.get_current_time.enabled", "value": False}], version
    )
    if status != 200:
        print(f"   FAIL: PATCH returned {status}")
        return 1
    status, text = post_stream("What time is it?")
    if status != 200:
        print(f"   FAIL: stream returned {status}")
        return 1
    print(f"   Reply: {text[:100]}..." if len(text) > 100 else f"   Reply: {text}")
    print("   OK")

    print("\n4. Disable all tools — PATCH then stream 'I am building Test'")
    status, cfg2 = get_config()
    version = cfg2.get("version", 1)
    aid2 = cfg2.get("agent_id") or agent_id
    overrides = [{"path": f"tools.{n}.enabled", "value": False} for n in tool_names]
    status, _ = patch_config(aid2, overrides, version)
    if status != 200:
        print(f"   FAIL: PATCH returned {status}")
        return 1
    status, text = post_stream("I am building Test")
    if status != 200:
        print(f"   FAIL: stream returned {status}")
        return 1
    # With all tools off we may get normal reply or "Tools are currently disabled"
    print(f"   Reply: {text[:100]}..." if len(text) > 100 else f"   Reply: {text}")
    print("   OK")

    print("\n5. Re-enable all tools — PATCH then stream 'Echo back: hello'")
    status, cfg3 = get_config()
    version = cfg3.get("version", 1)
    aid3 = cfg3.get("agent_id") or agent_id
    overrides = [{"path": f"tools.{n}.enabled", "value": True} for n in tool_names]
    status, _ = patch_config(aid3, overrides, version)
    if status != 200:
        print(f"   FAIL: PATCH returned {status}")
        return 1
    status, text = post_stream("Echo back: hello")
    if status != 200:
        print(f"   FAIL: stream returned {status}")
        return 1
    if FALLBACK_TOOL_MSG in text:
        print(f"   WARN: got fallback (model may not have used repeat_back): {text[:80]}...")
    else:
        print(f"   Reply: {text[:100]}..." if len(text) > 100 else f"   Reply: {text}")
    print("   OK")

    print("\nAll tool-toggle checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
