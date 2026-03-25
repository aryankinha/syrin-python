# Remote config and tool-toggle tests

## Tool toggle test (recommended first)

With the chatbot running (`python -m examples.16_serving.chatbot`), run:

```bash
python -m examples.16_serving.test_tool_toggle
```

This checks that:
- The agent has 3 tools: `remember_fact`, `get_current_time`, `repeat_back`.
- With tools ON, POST /stream runs the full REACT loop and returns real replies (no fallback).
- Disabling one or all tools via PATCH /config works; stream still returns a reply.
- Re-enabling tools restores normal behavior.

---

# Remote config stress test (chatbot)

This document describes how to run the remote config stress test against the chatbot example and how to get enums (e.g. loop_strategy) as a dropdown in the playground UI.

## 1. Start the chatbot

In one terminal:

```bash
cd /path/to/syrin-python
python -m examples.16_serving.chatbot
```

Server runs at http://localhost:8000 (POST /chat, GET /playground, GET/PATCH /config).

## 2. Run the stress test

In another terminal:

```bash
cd /path/to/syrin-python
python -m examples.16_serving.stress_test_remote_config
```

The script:

- **GET /config** — Asserts `sections.agent` has field `agent.loop_strategy` with `enum_values` (e.g. `["react", "plan_execute", "code_action", "single_shot"]`). The UI uses this for the dropdown.
- **PATCH loop_strategy** — Sets to `single_shot`, then reverts (value: null).
- **PATCH tools.remember_fact.enabled** — Toggles the remember tool off then on.
- **PATCH budget.max_cost** — Changes run limit (e.g. 0.25).
- **Stress** — Runs 20 PATCHes in sequence (loop_strategy, budget.max_cost, tool toggle) to ensure no false rejects or flakes.

If all steps pass, the config API and schema (including enum_values for dropdowns) are working.

## 3. Dropdown in the playground (loop_strategy, etc.)

The API returns `enum_values` for fields like `agent.loop_strategy`. The playground’s Agent config modal shows a **select** (dropdown) for any field that has `enum_values`.

If you don’t see the dropdown and instead see a text input:

1. **Rebuild the playground** so the served static files include the latest UI (select for enums):

   ```bash
   cd playground
   npm run build
   ```

2. Restart the chatbot and open http://localhost:8000/playground → **Agent config**. The loop strategy field should appear as a dropdown with options like "react", "plan execute", "code action", "single shot".

## 4. What is not in remote config

- **budget.on_exceeded** (raise/warn/stop) is a callable in code and is not exposed as an enum in the config schema; only run, reserve, per, etc. are configurable via PATCH.
