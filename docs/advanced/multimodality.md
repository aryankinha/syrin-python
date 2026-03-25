---
title: Multimodality
description: Image generation, video generation, audio synthesis, and multimodal input
weight: 260
---

## The Problem: Agents Should See, Speak, and Create

Modern AI isn't just text. Users want agents that can:

- **See** — Analyze images, read charts, understand photos
- **Generate images** — Create visuals on demand
- **Generate video** — Produce short video clips
- **Speak** — Convert text to natural speech
- **Process files** — Handle PDFs, documents, presentations

**The challenge:**
- Each modality has different APIs and quirks
- You need a unified interface
- Integration with agent workflow is complex
- Costs vary wildly between providers

**The solution:** Syrin's unified multimodal system — one interface for all media types.

## Media Types

Syrin supports these media types:

| Media | Input | Output | Providers |
| --- | --- | --- | --- |
| TEXT | ✓ | ✓ | All models |
| IMAGE | ✓ | ✓ | GPT-4V, Claude, Gemini (input); DALL-E, Imagen (output) |
| AUDIO | ✓ | ✓ | Whisper (input); ElevenLabs, OpenAI TTS (output) |
| VIDEO | ✗ | ✓ | Veo, Sora |

## Image Generation

### Standalone: Just Call generate_image()

```python
from syrin import generate_image

# Simple usage
result = generate_image(
    prompt="a sunset over mountains",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

if result[0].success:
    # result[0].url - data URL with base64 image
    # result[0].content_bytes - raw image bytes
    # result[0].content_type - "image/png" or "image/jpeg"
    save_to_file(result[0].content_bytes)
```

### With Options

```python
result = generate_image(
    prompt="a minimalist logo of a blue bird on white",
    model="imagen-3.0-generate-001",      # Model choice
    number_of_images=2,                    # 1-4 images
    aspect_ratio="16:9",                   # 1:1, 3:4, 4:3, 9:16, 16:9
    output_mime_type="image/png",          # image/png or image/jpeg
    negative_prompt="text, watermark",     # What to avoid
)

# Multiple images
for i, r in enumerate(result):
    if r.success:
        print(f"Image {i}: {r.content_type}")
```

### GenerationResult Structure

```python
@dataclass
class GenerationResult:
    success: bool                    # True if generation succeeded
    error: str | None               # Error message if failed
    url: str | None                 # Data URL (data:image/png;base64,...)
    content_bytes: bytes | None      # Raw image/video bytes
    content_type: str | None         # MIME type
    metadata: dict | None            # Provider-specific data
```

## Video Generation

### Standalone: generate_video()

Video generation is asynchronous — the API starts a job and you poll for completion:

```python
from syrin import generate_video

# Sync version (polls until done)
result = generate_video(
    prompt="a golden retriever running through a sunny field, 3 seconds",
    api_key=os.getenv("GOOGLE_API_KEY"),
    aspect_ratio="16:9",
    poll_interval_seconds=10.0,    # Check every 10 seconds
    poll_timeout_seconds=300.0,    # Give up after 5 minutes
)

if result.success:
    # result.url - data URL with base64 video
    # result.content_bytes - raw video bytes
    # result.content_type - "video/mp4"
    save_to_file(result.content_bytes)
```

### Async Version (Non-Blocking)

```python
import asyncio
from syrin import generate_video_async

async def generate_video():
    result = await generate_video_async(
        prompt="a cat jumping",
        poll_timeout_seconds=300.0,
    )
    
    if result.success:
        return result.content_bytes
```

## Voice Generation (Text-to-Speech)

### Standalone TTS

```python
from syrin import VoiceGenerator

# OpenAI TTS
voice = VoiceGenerator.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ElevenLabs TTS
voice = VoiceGenerator.ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Generate speech
result = voice.generate(
    text="Hello, welcome to our service!",
    voice_id="default",              # Provider-specific voice ID
    speed=1.0,                       # 0.5 - 2.0
    language="en",                   # Language code
)

if result.success:
    # result.url - audio data URL
    # result.content_bytes - raw audio bytes
    # result.content_type - audio/mp3, audio/wav, etc.
    play_audio(result.content_bytes)
```

### Voice Output Formats

```python
from syrin.enums import VoiceOutputFormat

# Available formats
voice.generate(
    text="Hello!",
    output_format=VoiceOutputFormat.MP3_44100,     # Default
    output_format=VoiceOutputFormat.WAV_24000,
    output_format=VoiceOutputFormat.OGG_24000,
)
```

## Agent Integration: Declarative Media

Instead of separate generation calls, agents can declare what media they support:

```python
from syrin import Agent, Model
from syrin.enums import Media

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="..."),
    
    # Agent can produce these media types
    output_media={Media.TEXT, Media.IMAGE, Media.VIDEO, Media.AUDIO},
    
    system_prompt="""
    You are a creative assistant. When users ask for:
    - Images: use generate_image tool
    - Videos: use generate_video tool
    - Speech: use generate_voice tool
    """,
)
```

**What just happened:**
1. You declared the agent supports IMAGE, VIDEO, and AUDIO output
2. Syrin automatically added `generate_image`, `generate_video`, and `generate_voice` tools
3. The agent decides when to use each based on user requests

### With Voice Generation

```python
from syrin import VoiceGenerator

# Configure voice
voice_gen = VoiceGenerator.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="..."),
    output_media={Media.TEXT, Media.AUDIO},
    voice_generation=voice_gen,  # Enable voice tool
    
    system_prompt="""
    You are a helpful voice assistant. When asked to speak, 
    use the generate_voice tool to respond with speech.
    """,
)

# Agent can now speak!
result = agent.run("Say hello in a friendly tone")
```

## Multimodal Input: Vision

Agents can see images, PDFs, and documents:

### Sending Images

```python
import base64
from syrin import Agent, Model
from syrin.multimodal import file_to_message

# Read image as base64 data URL
with open("chart.png", "rb") as f:
    image_data = f.read()

data_url = file_to_message(image_data, "image/png")

# Send with text
content_parts = [
    {"type": "text", "text": "Analyze this chart and summarize the trends"},
    {"type": "image_url", "image_url": {"url": data_url}},
]

result = agent.run(content_parts)
```

### Supported Formats

```python
# PNG
data_url = file_to_message(image_bytes, "image/png")

# JPEG
data_url = file_to_message(image_bytes, "image/jpeg")

# PDF (for Claude, Gemini)
data_url = file_to_message(pdf_bytes, "application/pdf")

# URL
data_url = "https://example.com/image.png"
content = [
    {"type": "text", "text": "What's in this image?"},
    {"type": "image_url", "image_url": {"url": data_url}},
]
```

## Automatic Media Routing

Syrin can automatically select the right model based on input content:

```python
from syrin import Agent, Model
from syrin.enums import Media
from syrin.router import ModelRouter, RoutingConfig, RoutingMode, TaskType

# Define models with media capabilities
text_model = Model.OpenAI(
    "gpt-4o-mini",
    profile_name="text",
    input_media={Media.TEXT},
    output_media={Media.TEXT},
    strengths=[TaskType.GENERAL, TaskType.CODE],
)

vision_model = Model.OpenAI(
    "gpt-4o",
    profile_name="vision",
    input_media={Media.TEXT, Media.IMAGE},
    output_media={Media.TEXT},
    strengths=[TaskType.VISION, TaskType.GENERAL],
)

# Router selects based on input
router = ModelRouter(models=[text_model, vision_model], routing_mode=RoutingMode.AUTO)

agent = Agent(
    model=[text_model, vision_model],  # List of models
    model_router=RoutingConfig(router=router),
)
```

**How routing works:**
1. User sends text only → selects `text_model`
2. User sends image → selects `vision_model`
3. Router filters by `input_media` capability

## Custom Generation Providers

Implement your own image/video/voice provider:

### Image Provider Protocol

```python
from syrin.generation import ImageGenerationProvider, GenerationResult

class MyImageProvider(ImageGenerationProvider):
    """Custom image generation provider."""
    
    def generate(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "1:1",
        number_of_images: int = 1,
        output_mime_type: str = "image/png",
        model: str | None = None,
        **kwargs,
    ) -> list[GenerationResult]:
        # Your implementation
        image_bytes = my_api.generate(prompt, ...)
        
        return [
            GenerationResult(
                success=True,
                url=f"data:{output_mime_type};base64,{b64(image_bytes)}",
                content_bytes=image_bytes,
                content_type=output_mime_type,
            )
        ]


# Register and use
from syrin.generation import register_image_provider

register_image_provider("my-provider", MyImageProvider())

# Use in agent
from syrin.generation import ImageGenerator

agent = Agent(
    model=model,
    output_media={Media.IMAGE},
    image_generation=ImageGenerator(provider=MyImageProvider()),
)
```

### Video Provider Protocol

```python
from syrin.generation import VideoGenerationProvider, GenerationResult

class MyVideoProvider(VideoGenerationProvider):
    """Custom video generation provider."""
    
    def generate(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "16:9",
        model: str | None = None,
        **kwargs,
    ) -> GenerationResult:
        # Your implementation
        video_bytes = my_api.generate_video(prompt, ...)
        
        return GenerationResult(
            success=True,
            content_bytes=video_bytes,
            content_type="video/mp4",
        )
```

### Voice Provider Protocol

```python
from syrin.generation import VoiceGenerationProvider, GenerationResult

class MyVoiceProvider(VoiceGenerationProvider):
    """Custom text-to-speech provider."""
    
    def generate(
        self,
        text: str,
        *,
        voice_id: str = "default",
        speed: float = 1.0,
        language: str = "en",
        **kwargs,
    ) -> GenerationResult:
        # Your implementation
        audio_bytes = my_tts_api.synthesize(text, voice=voice_id)
        
        return GenerationResult(
            success=True,
            content_bytes=audio_bytes,
            content_type="audio/mp3",
        )
    
    async def generate_async(self, *args, **kwargs) -> GenerationResult:
        # Async version
        ...
```

## Cost Tracking

Generation costs are tracked in the budget:

```python
from syrin import Agent, Model, Budget

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="..."),
    budget=Budget(max_cost=10.00),  # $10 limit
    output_media={Media.IMAGE, Media.AUDIO},
)

# When agent generates media, costs are tracked
result = agent.run("Create an image of a sunset and say something about it")

print(f"Total cost: ${result.cost}")  # Includes LLM + image + audio costs
```

## Error Handling

All generation methods return `GenerationResult` with error info:

```python
result = generate_image("a beautiful sunset", api_key="invalid-key")

if not result[0].success:
    print(f"Error: {result[0].error}")
    # Handle gracefully - don't crash the agent
```

### Graceful Degradation

```python
from syrin.guardrails import GuardrailChain, ContentBlock

guardrails = GuardrailChain([
    ContentBlock(
        name="generation_fallback",
        check=lambda ctx: True,  # Always pass
        on_fail="warn",         # Warn instead of block
    ),
])

agent = Agent(
    model=model,
    output_media={Media.IMAGE},
    guardrails=guardrails,
)
```

## Use Cases

### 1. Product Visualization Agent

```python
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="..."),
    output_media={Media.TEXT, Media.IMAGE},
    system_prompt="""
    You are a product designer. When users describe products, 
    generate visualizations using generate_image.
    """,
)

result = agent.run(
    "Design a modern ergonomic chair in blue with silver accents"
)
```

### 2. Marketing Content Creator

```python
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="..."),
    output_media={Media.TEXT, Media.IMAGE, Media.AUDIO},
    voice_generation=VoiceGenerator.OpenAI(api_key="..."),
    system_prompt="""
    Create marketing content. For products:
    1. Generate an image
    2. Write copy
    3. Record audio narration
    """,
)
```

### 3. Document Analyzer

```python
agent = Agent(
    model=Model.Anthropic("claude-3-5-sonnet", api_key="..."),
    system_prompt="Analyze uploaded documents and answer questions.",
)

# Send PDF page as image
with open("page1.png", "rb") as f:
    page_image = file_to_message(f.read(), "image/png")

result = agent.run([
    {"type": "text", "text": "What does this document say?"},
    {"type": "image_url", "image_url": {"url": page_image}},
])
```

## Performance Considerations

| Operation | Typical Latency | Notes |
| --- | --- | --- |
| Image generation | 5-30 seconds | Depends on provider and queue |
| Video generation | 1-5 minutes | Very slow, consider caching |
| Voice synthesis | <1 second | Fast, real-time possible |
| Vision processing | Similar to text | Varies by model |

## What's Next?

- [Testing](/advanced/testing) — Test multimodal agents
- [Custom Model](/advanced/custom-model) — Custom providers
- [Event Bus](/advanced/event-bus) — Track generation events

## See Also

- [Input/Output Media](/agent/input-output-media) — Media handling in agents
- [Vision Routing](/core/models-routing) — Model selection by input
- [Guardrails](/agent/guardrails) — Safety for generated content
