# Multimodal: Images, Files, and Generation

Syrin supports **multimodal input** (text + images or files) and **image/video generation** (output). Use vision-capable models for understanding, and optional Gemini (Imagen/Veo) for creating images and videos.

**In this guide:**
- **Media** — single enum (TEXT, IMAGE, VIDEO, AUDIO, FILE) for capabilities and content
- **input_media** / **output_media** — what the agent accepts and can produce; **input_file_rules** when FILE is in input_media
- Sending images and files with messages (content parts, `file_to_message`)
- Image and video generation: standalone API and Agent `output_media`
- Hooks and options (StrEnums, no free strings)

## Multimodal Input

Agents accept **MultimodalInput**: a plain string or a **list of content parts**. Use content parts when the user sends images or files.

### Content parts format

Same shape as OpenAI/Anthropic multimodal messages:

- `{"type": "text", "text": "Your question here"}`
- `{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}`

### Building messages with files

Use `file_to_message` to turn file bytes into a data URL for content parts:

```python
from pathlib import Path
from syrin import Agent
from syrin.model import Model
from syrin.multimodal import file_to_message

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="..."),
    system_prompt="You are helpful. Describe or answer questions about images.",
)

# Text only (unchanged)
r = agent.response("Hello")

# Image + text — list of content parts
data_url = file_to_message(Path("photo.png").read_bytes(), "image/png")
content_parts = [
    {"type": "text", "text": "What's in this image?"},
    {"type": "image_url", "image_url": {"url": data_url}},
]
r = agent.response(content_parts)
```

**`file_to_message(data, mimetype, role="user")`** returns a `data:` URL string. Use it inside content parts as above.

### PDF text extraction

For PDFs, extract text first (optional dependency `syrin[pdf]`), then send as text:

```python
from pathlib import Path
from syrin.multimodal import pdf_extract_text

text = pdf_extract_text(Path("doc.pdf").read_bytes())
r = agent.response(f"Summarize this document:\n\n{text}")
```

### Playground

When serving with `enable_playground=True`, the web UI supports:

- **Paste** images into the input (e.g. Ctrl+V / Cmd+V)
- **Attach** images or PDFs via the attachment button

The playground sends `message` as either a string or a list of content parts. The backend and router handle both; vision-capable models are selected when images are present (see [Routing](routing.md#modalitydetector)).

### Routing and vision

When you use a **model list and RoutingConfig**, the router’s **ModalityDetector** inspects messages and can route to a vision-capable profile when content includes images. Ensure at least one Model has `input_media={Media.TEXT, Media.IMAGE}` (and optionally `TaskType.VISION` in strengths). See [Routing — ModalityDetector](routing.md#modalitydetector).

---

## Image and Video Generation

Create images or short videos from text. **Built-in providers:** Google (Imagen, Veo), OpenAI (DALL·E 3). Optional dependency: `syrin[generation]`. Set `GOOGLE_API_KEY` for Google, `OPENAI_API_KEY` for DALL·E.

### Standalone API

Use the top-level functions when you don’t need an agent:

```bash
uv pip install syrin[generation]
```

```python
from syrin import generate_image, generate_video, GenerationResult

# Image (Imagen) — returns one result or list
result = generate_image("a futuristic cityscape at sunset", aspect_ratio="16:9")
if isinstance(result, list):
    result = result[0] if result else None
if result and result.success:
    print(result.url)  # data:image/png;base64,...

# Video (Veo) — async on API side; function polls until done
result = generate_video("a dog running through a field at sunset")
if result.success:
    print(result.url)  # data:video/mp4;base64,...
```

**`GenerationResult`**: `success`, `url`, `content_type`, `content_bytes`, `error`, `metadata`.  
Built-in providers populate `metadata` with `cost_usd` and `model_name` for budget tracking.  
Default models: image `imagen-4.0-generate-001`, video `veo-2.0-generate-001`. Pass `model=` to override.

### Declarative generation with Agent

Enable image and video **tools** by setting **output_media** to include `Media.IMAGE` and/or `Media.VIDEO`. The agent infers the Gemini API key from a Google model in its model list or from `GOOGLE_API_KEY`:

```python
from syrin import Agent
from syrin.enums import Media
from syrin.model import Model

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini"),
    output_media={Media.TEXT, Media.IMAGE, Media.VIDEO},
    system_prompt="You are helpful. Use generate_image when the user asks for an image.",
)
# When GOOGLE_API_KEY (or a Google model key) is available:
# - agent._image_generator and agent._video_generator are set
# - Tools generate_image and generate_video are added automatically
```

So you get **multi-modal in and out**: user can send images (content parts) and ask for generated images/videos (tools). Use **input_media** to declare what the agent accepts (e.g. `{Media.TEXT, Media.IMAGE}`); use **input_file_rules** when `Media.FILE` is in input_media (allowed MIME types and max size).

### Explicit image_generation and video_generation

Use **static constructors** (like `Model.OpenAI`) or pass custom generators to Agent:

```python
from syrin import Agent, ImageGenerator, VideoGenerator
from syrin.model import Model

# Image: Google (Gemini), OpenAI DALL·E
img_gen = ImageGenerator.Gemini(api_key="...")
# img_gen = ImageGenerator.DALLE(api_key="...")  # OpenAI DALL·E 3

# Video: Google (Gemini)
vid_gen = VideoGenerator.Gemini(api_key="...")

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini"),
    image_generation=img_gen,
    video_generation=vid_gen,
    system_prompt="You are helpful. Use generate_image when asked for images.",
)
```

### Custom providers (Leonardo, Flex, etc.)

**Option 1: Register and use static namespace** — After registering, use `ImageGenerator.Leonardo()`:

```python
from syrin.generation import ImageGenerator, GenerationResult, register_image_provider

# Implement ImageGenerationProvider protocol
class LeonardoImageProvider:
    def __init__(self, api_key=None, **kwargs): ...
    def generate(self, prompt, *, aspect_ratio="1:1", number_of_images=1, output_mime_type="image/png", model=None, **kwargs):
        # Call Leonardo API...
        return [GenerationResult(success=True, url="...")]

register_image_provider("leonardo", LeonardoImageProvider)

# Now ImageGenerator.Leonardo() works
gen = ImageGenerator.Leonardo(api_key=os.getenv("LEONARDO_API_KEY"))
agent = Agent(model=..., image_generation=gen)
```

**Option 2: Subclass** — For a named type:

```python
class LeonardoImageGenerator(ImageGenerator):
    pass

gen = LeonardoImageGenerator(provider=LeonardoImageProvider(api_key="..."))
agent = Agent(model=..., image_generation=gen)
```

When **output_media** includes IMAGE/VIDEO, the framework auto-creates default Gemini generators (if an API key is available). When **image_generation** or **video_generation** is provided, those are used instead.

### Standalone use

For standalone use without an agent, use **ImageGenerator** and **VideoGenerator** directly or the top-level `generate_image` / `generate_video` functions.

### Options (StrEnums)

No free strings for options:

- **AspectRatio**: `ONE_TO_ONE`, `THREE_FOUR`, `FOUR_THREE`, `NINE_SIXTEEN`, `SIXTEEN_NINE` (values like `"1:1"`, `"16:9"`).
- **OutputMimeType** (images): `IMAGE_PNG`, `IMAGE_JPEG`.

Use these in `ImageGenerator` / `VideoGenerator` or in the standalone API (which accepts string aspect ratios for backward compatibility).

### Hooks

Generation lifecycle is observable:

- **Image**: `Hook.GENERATION_IMAGE_START`, `GENERATION_IMAGE_END`, `Hook.GENERATION_IMAGE_ERROR`
- **Video**: `Hook.GENERATION_VIDEO_START`, `GENERATION_VIDEO_END`, `Hook.GENERATION_VIDEO_ERROR`

When the agent adds the generation tools, it passes its `_emit_event` into the generators so these hooks fire. Subscribe via `agent.events` or your event bus.

### Budget and cost tracking

When the agent has a **budget**, image and video generation cost is **automatically recorded** into the budget. Built-in providers (DALL·E, Imagen, Veo) populate `GenerationResult.metadata` with `cost_usd` and `model_name`. On `GENERATION_IMAGE_END` and `GENERATION_VIDEO_END`, the agent records this cost via `_record_cost_info`, so your run total includes LLM tokens plus any image/video generation.

```python
from syrin import Agent, Budget
from syrin.enums import Media
from syrin.model import Model

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini"),
    output_media={Media.TEXT, Media.IMAGE},
    budget=Budget(run=5.0),
)
r = agent.response("Draw a sunset")
# r.cost includes both LLM usage and image generation cost
```

Custom providers can add `metadata["cost_usd"]` and `metadata["model_name"]` to their `GenerationResult` to participate in budget tracking. Use `syrin.cost.calculate_image_cost` / `calculate_video_cost` for helper pricing, or compute cost yourself.

### Extending: custom providers

Image and video generation use **protocols** and a **provider registry**:

- `ImageGenerationProvider`: implement `generate(prompt, *, aspect_ratio, number_of_images, output_mime_type, model, **kwargs) -> list[GenerationResult]`
- `VideoGenerationProvider`: implement `generate(prompt, *, aspect_ratio, model, **kwargs) -> GenerationResult`
- `register_image_provider(name, cls)` / `register_video_provider(name, cls)` — after registration, use `ImageGenerator.Leonardo()` etc.

**Built-in static constructors:**

| Image | Video |
|-------|-------|
| `ImageGenerator.Gemini()` (Google Imagen) | `VideoGenerator.Gemini()` (Google Veo) |
| `ImageGenerator.DALLE()` (OpenAI DALL·E 3) | — |

Implement the protocol, then `register_image_provider(name, cls)` / `register_video_provider(name, cls)` to add e.g. `ImageGenerator.Leonardo()`.

---

## Summary

| Need | Use |
|------|-----|
| Send image + text to agent | Content parts + `file_to_message`; vision-capable model or router |
| Paste/attach in UI | Playground with `enable_playground=True` |
| Generate image/video in code | `generate_image` / `generate_video` |
| Agent has image/video tools | `output_media={Media.IMAGE, Media.VIDEO}` or `image_generation=` / `video_generation=` |
| Google image/video | `ImageGenerator.Gemini()`, `VideoGenerator.Gemini()` |
| OpenAI image | `ImageGenerator.DALLE(api_key=...)` (DALL·E 3; requires `openai`) |
| Custom provider | `register_image_provider("leonardo", Cls)` then `ImageGenerator.Leonardo()` |
| Observe generation | `Hook.GENERATION_IMAGE_*`, `Hook.GENERATION_VIDEO_*` |

**See also:** [Routing](routing.md) (ModalityDetector, vision profiles), [Models](models.md) (vision-capable models), [Serving](serving.md) (playground and API).
