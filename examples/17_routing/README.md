# Routing Examples

Model routing — task classification, model selection, and Agent integration.

## Examples by Feature

| Example | Features |
|---------|----------|
| **`prompt_classifier.py`** | PromptClassifier, embedding-based task detection |
| **`model_router.py`** | ModelRouter, Model routing fields, task_override, RoutingMode |
| **`agent_routing.py`** | Agent + model list, RoutingConfig, task_type override, ROUTING_DECISION hook |
| **`classifier_with_agent.py`** | PromptClassifier + Agent (auto task detection, no task_override) |
| **`cost_first_budget_agent.py`** | COST_FIRST, prefer_cheaper/force_cheapest budget ratios, budget_optimisation |
| **`quality_first.py`** | QUALITY_FIRST — always pick highest-priority capable model |
| **`simple_model_list.py`** | Minimal: model list + RoutingConfig |
| **`force_model_debug.py`** | force_model — bypass routing, always use specific model |
| **`custom_routing_callback.py`** | routing_rule_callback — VIP prompts, A/B logic |
| **`openrouter_single_key.py`** | OpenRouterBuilder — one API key, multiple providers |
| **`default_profiles_agent.py`** | get_default_profiles() (claude-code, gpt-general, gemini-vision) |
| **`tools_aware_routing.py`** | supports_tools — exclude text-only models when Agent has tools |
| **`vision_modality_routing.py`** | Media (TEXT, IMAGE), input_media for vision models |
| **`routing_observability.py`** | ROUTING_DECISION hook — log routing to file/metrics |
| **`max_cost_cap.py`** | COST_FIRST, cost_estimate in RoutingReason |
| **`production_classifier.py`** | classify_extended, complexity, system alignment |
| **`manual_routing_test.py`** | 5 real models, model.with_fallback for API resilience |

## Run (Almock — no API key)

Add `--trace` to any example that uses Agent to see routing decisions, model selection, and full trace output (which model, why, cost, alternatives).

```bash
# Core
python -m examples.17_routing.model_router
python -m examples.17_routing.agent_routing
python -m examples.17_routing.agent_routing --trace   # with routing traces

# Routing modes
python -m examples.17_routing.cost_first_budget_agent
python -m examples.17_routing.quality_first
python -m examples.17_routing.force_model_debug

# Custom logic
python -m examples.17_routing.custom_routing_callback
python -m examples.17_routing.simple_model_list

# Profiles
python -m examples.17_routing.default_profiles_agent
python -m examples.17_routing.tools_aware_routing
python -m examples.17_routing.vision_modality_routing

# Observability
python -m examples.17_routing.routing_observability

# Requires classifier-embeddings
uv pip install 'syrin[classifier-embeddings]'
python -m examples.17_routing.prompt_classifier
python -m examples.17_routing.classifier_with_agent

# Requires API keys
python -m examples.17_routing.openrouter_single_key   # OPENROUTER_API_KEY
python -m examples.17_routing.manual_routing_test     # OPENAI, GOOGLE, ANTHROPIC, DEEPSEEK
```

## See Also

- [Routing docs](../../docs/routing.md) — Full API, Agent integration, OpenRouter, hooks.
