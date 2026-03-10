# Model Routing

Intelligent model routing selects the best model based on task type, modality, cost, and developer preferences — **before** any LLM call.

Key components: Model (routing fields), ModalityDetector, RoutingConfig, ModelRouter, RoutingReason, get_default_profiles, Agent integration, OpenRouter, response metadata, ROUTING_DECISION hook.

## What Developers Can Build

With the routing system, you can:

| Capability | How |
|------------|-----|
| **Task-based routing** | Route code → Claude, general → GPT-4o-mini, vision → Gemini, etc. |
| **Cost optimization** | COST_FIRST mode; budget thresholds (`prefer_cheaper_below_budget_ratio`, `force_cheapest_below_budget_ratio`) |
| **Quality-first** | QUALITY_FIRST mode; HIGH complexity → highest-priority model |
| **Single API key** | OpenRouterBuilder — one key for Anthropic, OpenAI, Google, etc. |
| **Custom routing logic** | `routing_rule_callback` — VIP prompts, A/B tests, manual overrides |
| **Force specific model** | `force_model` — bypass routing for debugging or pinned model |
| **Tools-aware** | Exclude text-only models when Agent has tools (`supports_tools`) |
| **Vision/Video routing** | `input_media` — route to vision models when messages have images |
| **Budget-aware** | `prefer_cheaper_below_budget_ratio`, `force_cheapest_below_budget_ratio`, `budget_optimisation` — prefer cheap when low |
| **Custom classifier** | Pass `classifier` to RoutingConfig for custom task detection |
| **Production classification** | `classify_extended` — complexity, system alignment, LRU cache |
| **Observability** | `Hook.ROUTING_DECISION`; `r.routing_reason`, `r.model_used`, `r.actual_cost` |

Use Agent with `model=[...]` + `model_router=RoutingConfig(...)` for automatic per-request routing. Or use `ModelRouter` standalone with custom profiles.

## Enums

### TaskType

Detected task type for routing:

| Value | Use |
|-------|-----|
| `CODE` | Code generation, debugging, review |
| `GENERAL` | General conversation, Q&A |
| `VISION` | Image understanding, OCR (input) |
| `IMAGE_GENERATION` | Create, draw, or generate an image (output) |
| `VIDEO` | Video analysis, transcription (input) |
| `VIDEO_GENERATION` | Create or generate a video (output) |
| `PLANNING` | Task decomposition, strategy |
| `REASONING` | Math, logic, analysis |
| `CREATIVE` | Writing, brainstorming |
| `TRANSLATION` | Language translation |

### Media

Single canonical enum for content and model capabilities: **Media** (TEXT, IMAGE, VIDEO, AUDIO, FILE). Use for message content detection, agent **input_media** / **output_media**, and model profile **input_media** / **output_media**. Import from `syrin.enums` or `syrin.router`.

### RoutingMode

| Value | Behavior |
|-------|----------|
| `AUTO` | Balance cost and capability (default) |
| `COST_FIRST` | Cheapest capable model |
| `QUALITY_FIRST` | Highest-priority capable model |
| `MANUAL` | Developer provides task type |

## PromptClassifier

Embedding-based task classification — no LLM needed. Uses sentence-transformers for cosine similarity between prompt and task examples.

**Keyword fallback (no install):** Prompts like "generate an image of X" or "create a video of Y" are detected via keywords and classified as `IMAGE_GENERATION` / `VIDEO_GENERATION` — **no sentence-transformers required**. Use `use_keyword_fallback=True` (default).

**Full classification (optional install):**

```bash
uv sync --extra classifier-embeddings
# or: uv pip install 'syrin[classifier-embeddings]'
```

**Usage:**

```python
from syrin.router import PromptClassifier, TaskType

classifier = PromptClassifier(
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    min_confidence=0.35,  # Raw cosine similarity threshold; unrelated -> 0
    low_confidence_fallback=TaskType.GENERAL,
)

task_type, confidence = classifier.classify("write a function to sort a list")
# → (TaskType.CODE, 0.92)

# Low-confidence prompts use fallback
task_type, confidence = classifier.classify("hi")
# → (TaskType.GENERAL, 0.35)  # Below min, returns fallback
```

**Custom embedding provider** — Use OpenAI, Cohere, or any `encode(texts) -> list[list[float]]`:

```python
class MyEmbeddingProvider:
    def encode(self, texts: list[str]) -> list[list[float]]:
        # Call OpenAI / Cohere / etc.
        return [[0.1] * 384 for _ in texts]

classifier = PromptClassifier(embedding_provider=MyEmbeddingProvider())
```

**Custom examples:**

```python
classifier = PromptClassifier(
    examples={
        TaskType.CODE: ["implement binary search", "fix the bug"],
        TaskType.REASONING: ["solve this math problem", "prove the following"],
    },
)
task_type, confidence = classifier.classify("solve this math problem")
```

**Warmup (optional):** Load the model before first use to avoid latency on first classify:

```python
classifier.warmup()
```

### Production: Extended Classification

For higher vs lower model selection and system-prompt alignment:

```python
from syrin.router import PromptClassifier, ClassificationResult, ComplexityTier

classifier = PromptClassifier(enable_cache=True, max_cache_size=1000)

# Returns task_type, confidence, complexity_score, system_alignment_score
result = classifier.classify_extended(
    "Implement a distributed consensus algorithm",
    system_prompt="You are a coding assistant.",
)
# result.task_type, result.confidence
# result.complexity_score  # 0=cheap model, 1=premium
# result.complexity_tier   # LOW, MEDIUM, HIGH
# result.system_alignment_score  # High = prompt in scope
```

When `complexity_tier == HIGH`, the router prefers highest-priority capable models.

### ComplexityTier

| Value | Use |
|-------|-----|
| `LOW` | Simple prompts — use cheaper models |
| `MEDIUM` | Moderate — balance cost/capability |
| `HIGH` | Complex — prefer premium models |

### Production Settings

- **enable_cache** (default True): LRU cache for repeated prompts.
- **max_cache_size** (default 1000): Max cached results. `0` to disable.
- **clear_cache()**: Call when examples or config change.
- **complexity_use_embedding** (default True): Use embedding for complexity; else heuristic only.

## Cache

Models use Hugging Face cache (`~/.cache/huggingface/`). Override with `cache_dir`:

```python
classifier = PromptClassifier(cache_dir="/path/to/cache")
```

If `cache_dir` is provided and does not exist, the parent directory must exist and be writable.

## Model routing fields

Configure routing per model via Model constructor or `model.with_routing()`:

```python
from syrin.model import Model
from syrin.enums import Media
from syrin.router import TaskType

model = Model.Anthropic(
    "claude-sonnet-4-5",
    api_key="...",
    profile_name="claude-code",
    strengths=[TaskType.CODE, TaskType.REASONING, TaskType.PLANNING],
    input_media={Media.TEXT},
    output_media={Media.TEXT},
    supports_tools=True,
    priority=100,
)

# Or add routing to existing model
model = gpt4_mini.with_routing(strengths=[TaskType.CODE], profile_name="code")
```

When `strengths`, `input_media`, `output_media`, `priority`, or `supports_tools` are set on Model, `ModelRouter` uses them. `supports_tools=False` excludes the model when tools are present.

## ModalityDetector

Detect required modalities from messages before routing:

```python
from syrin.router import ModalityDetector
from syrin.types import Message

detector = ModalityDetector()
media = detector.detect(messages)  # set[Media]: {Media.TEXT}, or + IMAGE, VIDEO, AUDIO
```

Detects base64 data URLs (`data:image/...;base64,...`) in message content.

## Multimodal and generation

**Multimodal input** (text + images/files) and **image/video generation** have their own guide: **[Multimodal](multimodal.md)**.

There you’ll find: content parts, `file_to_message`, PDF extraction, playground paste/attach; standalone `generate_image` / `generate_video`; declarative Agent API (`output_media={Media.IMAGE, Media.VIDEO}` for generation tools); hooks and StrEnums. The router’s **ModalityDetector** (above) routes messages that contain images to vision-capable profiles — see [Multimodal — Routing and vision](multimodal.md#routing-and-vision).

## Agent Integration

Pass a list of models and optional `model_router` to enable automatic routing:

```python
from syrin import Agent, Budget
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode, TaskType

# Simple: model list + model_router
agent = Agent(
    model=[
        Model.Anthropic("claude-sonnet-4-5", api_key="..."),
        Model.OpenAI("gpt-4o-mini", api_key="..."),
        Model.Google("gemini-2.0-flash", api_key="..."),
    ],
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
    system_prompt="You are helpful.",
    budget=Budget(run=10.0),
)

# Agent routes per request
r = agent.response("write a sorting function")
# Uses Claude (CODE task)
print(r.routing_reason.selected_model, r.routing_reason.reason)

r = agent.response("what is the weather?")
# Uses GPT-4o-mini (GENERAL task)

# Task override for ambiguous prompts
r = agent.response("Fix this", task_type=TaskType.CODE)

# Force specific model (bypass routing)
agent = Agent(
    model=[...],
    model_router=RoutingConfig(force_model=Model.Anthropic("claude-opus", api_key="...")),
)
```

**Response metadata (when routing):** `r.routing_reason`, `r.model_used`, `r.task_type`, `r.actual_cost`.

**Hook:** Subscribe to `Hook.ROUTING_DECISION` for observability. EventContext includes `routing_reason`, `model`, `task_type`, `prompt`.

## OpenRouter

Single API key for multiple providers. Use `Model.OpenRouter` or `OpenRouterBuilder`:

```python
import os
from syrin.model import Model, OpenRouterBuilder

# Single model
model = Model.OpenRouter(
    "anthropic/claude-sonnet-4-5",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Builder: one key, multiple models (for routing)
builder = OpenRouterBuilder(api_key=os.getenv("OPENROUTER_API_KEY"))
claude = builder.model("anthropic/claude-sonnet-4-5")
gpt = builder.model("openai/gpt-4o-mini")

agent = Agent(
    model=[claude, gpt],
    model_router=RoutingConfig(routing_mode=RoutingMode.COST_FIRST),
    system_prompt="You are helpful.",
)
```

OpenRouter response headers (`x-openrouter-total-cost`, `x-openrouter-model-used`) populate `response.actual_cost` and `response.model_used` when available.

## RoutingConfig

Configuration for routing — use with Agent or pass to ModelRouter:

```python
from syrin.router import RoutingConfig, RoutingMode

config = RoutingConfig(
    routing_mode=RoutingMode.AUTO,
    budget_optimisation=True,
    prefer_cheaper_below_budget_ratio=0.20,
    force_cheapest_below_budget_ratio=0.10,
)
```

| Field | Default | Description |
|-------|---------|-------------|
| `routing_mode` | AUTO | AUTO, COST_FIRST, QUALITY_FIRST, or MANUAL |
| `force_model` | None | Bypass routing; always use this model |
| `classifier` | None | Custom PromptClassifier; None = default embeddings-based |
| `router` | None | Explicit ModelRouter; overrides auto-created from model list |
| `budget_optimisation` | True | Prefer cheaper models when budget runs low |
| `prefer_cheaper_below_budget_ratio` | 0.20 | When remaining/limit < 20%, prefer cheaper capable models |
| `force_cheapest_below_budget_ratio` | 0.10 | When remaining/limit < 10%, force cheapest capable model |
| `routing_rule_callback` | None | `(prompt, task_type, profile_names) -> profile_name | None` |

**Custom routing callback** — VIP prompts, A/B logic, or manual overrides:

```python
def vip_routing(prompt: str, task_type: TaskType, profile_names: list[str]) -> str | None:
    if "VIP" in prompt:
        return "premium"  # Force premium model for VIP
    if task_type == TaskType.CODE and "preview" in profile_names:
        return "preview"  # A/B: use preview model for code
    return None  # Let router decide

agent = Agent(
    model=[claude, gpt],
    model_router=RoutingConfig(routing_rule_callback=vip_routing),
)
```

**MANUAL mode** — You provide task type; no classification:

```python
router = ModelRouter(models=models, routing_mode=RoutingMode.MANUAL)
model, task, reason = router.route("Fix this", task_override=TaskType.CODE)
```

## Model capabilities

ModelRouter derives routing metadata from each Model. **Auto-detects strengths** from model IDs when not set:

- Claude → CODE, REASONING, PLANNING
- GPT-4o/GPT-4 → GENERAL, VISION, CREATIVE
- GPT-4o-mini/GPT-3.5 → GENERAL
- Gemini → VISION, VIDEO, GENERAL

Configure routing per-model via **Model routing fields** (recommended): `strengths`, `input_media`, `output_media`, `priority`, `supports_tools`. When set on Model, those values are used. Otherwise, auto-inference applies.

**Model capabilities registry** — Register custom models (DeepSeek, Mistral, Qwen, etc.):

```python
from syrin.router import register_model_capabilities

register_model_capabilities(
    "deepseek",
    [TaskType.CODE, TaskType.REASONING, TaskType.GENERAL],
)
# Now ModelRouter(models=[Model(provider="custom", model_id="deepseek-v3")]) infers CODE, REASONING
```

## ModelRouter

Main routing class. Selects the best model based on task, modality, cost, and budget:

```python
from syrin.model import Model
from syrin.router import ModelRouter, RoutingMode, TaskType

router = ModelRouter(
    models=[
        Model.Anthropic("claude-sonnet-4-5", api_key="...", profile_name="code", strengths=[TaskType.CODE, TaskType.REASONING]),
        Model.OpenAI("gpt-4o-mini", api_key="...", profile_name="general", strengths=[TaskType.GENERAL]),
    ],
    routing_mode=RoutingMode.AUTO,
)

model, task_type, reason = router.route("write a sorting function")
print(reason.selected_model, reason.reason, reason.cost_estimate)
```

**Task override:** For ambiguous prompts, pass `task_override`:

```python
model, task, reason = router.route("Fix this", task_override=TaskType.CODE)
```

**Force model:** Bypass routing:

```python
router = ModelRouter(
    models=[...],
    force_model=Model.Anthropic("claude-opus", api_key="..."),
)
```

**Fallback routing:** `route_ordered()` returns ranked list of (model, task_type, reason) for try-until-success:

```python
for model, task, reason in router.route_ordered("hello", max_alternatives=3):
    try:
        resp = await model.acomplete(messages)
        break
    except ProviderError:
        continue
```

## RoutingReason

Returned by `router.route()`. Explains the selection:

- `selected_model` — Profile name chosen
- `task_type` — Detected or overridden task type
- `reason` — Human-readable explanation
- `cost_estimate` — Estimated cost in USD
- `alternatives` — Other profile names that could have been used
- `classification_confidence` — 0.0–1.0 from PromptClassifier
- `complexity_tier` — LOW/MEDIUM/HIGH when classify_extended used (production)
- `system_alignment_score` — Prompt vs system alignment [0,1] when available

## Default Profiles

Use or override built-in profiles (lazy — no import-side model creation):

```python
from syrin.router import get_default_profiles

models = list(get_default_profiles().values())
router = ModelRouter(models=models)
```

Default profiles: `claude-code`, `gpt-general`, `gemini-vision`. Pass API keys when using with Agent.

## Budget Thresholds

When `budget_optimisation=True` (default) and Agent has a run budget:

- `prefer_cheaper_below_budget_ratio` (default 0.20): When remaining/limit < 20%, router prefers cheaper capable models
- `force_cheapest_below_budget_ratio` (default 0.10): When remaining/limit < 10%, router forces cheapest capable model

Use with `Budget(run=1.0)` for cost-sensitive agents.

## Custom Classifier

Pass a custom `PromptClassifier` to use your own task detection logic:

```python
from syrin.router import PromptClassifier, RoutingConfig, TaskType

classifier = PromptClassifier(
    examples={TaskType.CODE: ["write", "debug", "implement"], ...},
    min_confidence=0.35,
)

agent = Agent(
    model=[...],
    model_router=RoutingConfig(classifier=classifier),
)
```

Or pass a classifier to `ModelRouter` directly when using standalone routing.

## Response Metadata (when routing)

When using Agent with routing, the response includes:

- `r.routing_reason` — `RoutingReason` (selected_model, task_type, reason, cost_estimate, alternatives, classification_confidence, complexity_tier, system_alignment_score). `Hook.ROUTING_DECISION` includes `routing_latency_ms`.
- `r.model_used` — Model ID that answered (from provider/OpenRouter headers when available)
- `r.task_type` — Detected or overridden task type
- `r.actual_cost` — Actual cost when provider reports it (e.g. OpenRouter `x-openrouter-total-cost`)

See [Response Object](agent/response.md) for the full response reference.

## See Also

- [Models Guide](models.md) — `Model.OpenRouter`, `OpenRouterBuilder`, built-in providers
- [Agent: Model](agent/model.md) — `model` as list, `model_router` with Agent
- [Response](agent/response.md) — Response fields including routing metadata
- [Events & Hooks](agent/events-hooks.md) — `Hook.ROUTING_DECISION`
