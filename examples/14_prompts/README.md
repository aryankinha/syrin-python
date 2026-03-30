# 14_prompts — Prompt composition and runtime variables

- **prompt_decorator.py** — Define reusable prompt templates with `@prompt`.
- **dynamic_prompt.py** — Pass `template_variables` at class, instance, and per-call scope.
- **persona_prompt.py** — Keep prompt generation inside the agent with `@system_prompt`.

Use these examples when you want prompts to stay explicit, versionable, and parameterized in normal Python code.
