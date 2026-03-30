---
title: Multimodal Generation
description: Generate images, videos, and voice with AI agents
weight: 370
---

## Multimodal Generation

Syrin agents can generate images, videos, and voice output. Declare capabilities and the agent automatically gets generation tools.

## Agent with Image Generation

Agents get `generate_image` tool when configured for image output.

```python
from syrin import Agent, Model
from syrin.enums import Media

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    output_media={Media.TEXT, Media.IMAGE},
    system_prompt=(
        "You are helpful. When asked for an image, use generate_image."
    ),
)

# Agent decides to generate an image
result = agent.run(
    "Create a simple image of a red circle on white background."
)

# Result contains both text and image
print(f"Text: {result.content}")
if result.media:
    print(f"Image URL: {result.media[0].url}")
    print(f"Image bytes: {len(result.media[0].bytes)} bytes")
```

**What just happened:**
1. Declared `output_media={Media.IMAGE}`
2. Agent received `generate_image` tool
3. LLM decided to call the tool
4. Response includes image URL and bytes

## Agent with Video Generation

Generate short videos from text prompts.

```python
from syrin import Agent, Model
from syrin.enums import Media

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    output_media={Media.TEXT, Media.VIDEO},
    system_prompt=(
        "You are helpful. When asked for a video, use generate_video."
    ),
)

result = agent.run(
    "Create a video of waves crashing on a beach at sunset."
)

if result.media:
    for item in result.media:
        if item.type == "video":
            print(f"Video: {item.url}")
            print(f"Duration: {item.duration}s")
```

**What just happened:**
1. Declared `output_media={Media.VIDEO}`
2. Agent received `generate_video` tool
3. Generated video included in response
4. Video metadata (duration, format) available

## Multimodal Input and Output

Handle images in requests too.

```python
from syrin import Agent, Model, Media

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    input_media={Media.TEXT, Media.IMAGE},
    output_media={Media.TEXT, Media.IMAGE},
    system_prompt="Describe images and generate similar ones.",
)

# Upload image with request
result = agent.run(
    content="Describe this image and create a variation.",
    media=[
        {"type": "image", "url": "https://example.com/photo.jpg"}
    ],
)
```

**What just happened:**
1. Accepted image input
2. Analyzed the image
3. Generated a variation
4. Returned description and new image

## Explicit Generators

Use generators directly without agents.

```python
from syrin.generation import ImageGenerator, VideoGenerator

# Gemini Imagen for images
image_gen = ImageGenerator.Gemini(api_key="your-google-api")

image_result = await image_gen.generate(
    prompt="A serene mountain lake at dawn",
    aspect_ratio="16:9",
    safety_setting="block_some",
)

# Gemini Veo for videos
video_gen = VideoGenerator.Gemini(api_key="your-google-api")

video_result = await video_gen.generate(
    prompt="Time-lapse of clouds moving across sky",
    duration_seconds=8,
    resolution="720p",
)

print(f"Image: {image_result.url}")
print(f"Video: {video_result.url}")
```

**What just happened:**
1. Created generator instances directly
2. Generated image with custom parameters
3. Generated video with specified duration
4. Got URLs for the generated media

## Generation Options

Fine-tune output quality and style.

```python
from syrin.generation import ImageGenerator, GenerationOptions
from syrin.enums import ImageStyle, OutputFormat

gen = ImageGenerator.Gemini(api_key="your-google-api")

result = await gen.generate(
    prompt="A cozy coffee shop interior",
    options=GenerationOptions(
        style=ImageStyle.PHOTOREALISTIC,
        aspect_ratio="4:3",
        format=OutputFormat.PNG,
        quality=90,
        person_generation="allow_some",
        moderation=True,
    ),
)
```

**What just happened:**
1. Specified photorealistic style
2. Set aspect ratio and format
3. Enabled moderation filter
4. Got high-quality PNG output

## Voice Generation

Convert text to speech.

```python
from syrin.generation import VoiceGenerator
from syrin.enums import VoiceStyle

voice_gen = VoiceGenerator(
    provider=VoiceGenerator.ELEVENLABS,
    api_key="your-elevenlabs-api",
)

result = await voice_gen.generate(
    text="Hello! Welcome to our service. How can I help you today?",
    voice=VoiceStyle.FRIENDLY,
    language="en-US",
    speed=1.0,
)

# Save to file
with open("welcome.mp3", "wb") as f:
    f.write(result.audio_bytes)

print(f"Audio duration: {result.duration}s")
print(f"Format: {result.format}")
```

**What just happened:**
1. Created ElevenLabs voice generator
2. Generated friendly-sounding speech
3. Got audio bytes and metadata
4. Saved as MP3 file

## PDF Text Extraction

Extract text from uploaded documents.

```python
from syrin.generation import PDFExtractor

extractor = PDFExtractor()

result = await extractor.extract(
    source="https://example.com/document.pdf",
    pages=[1, 2, 3],  # Specific pages, or None for all
)

for page in result.pages:
    print(f"Page {page.number}:")
    print(f"Text: {page.text[:200]}...")
    print(f"Tables: {len(page.tables)}")
    print(f"Images: {len(page.images)}")
```

**What just happened:**
1. Extracted text from PDF pages
2. Captured tables and embedded images
3. Preserved page structure
4. Ready for knowledge ingestion

## Vision Routing

Route based on input media type.

```python
from syrin import Agent, Model, RoutingConfig
from syrin.router import RoutingMode, TaskType
from syrin.enums import Media

# Different models for different tasks
gpt4o_mini = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
gpt4o = Model.OpenAI("gpt-4o", api_key="your-api-key")

models = [
    gpt4o_mini.with_routing(
        profile_name="text",
        strengths=[TaskType.GENERAL, TaskType.CODE],
        input_media={Media.TEXT},
        output_media={Media.TEXT},
        priority=80,
    ),
    gpt4o.with_routing(
        profile_name="vision",
        strengths=[TaskType.VISION, TaskType.IMAGE_GENERATION],
        input_media={Media.TEXT, Media.IMAGE},
        output_media={Media.TEXT, Media.IMAGE},
        priority=95,
    ),
]

agent = Agent(
    model=models,
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
)
```

**What just happened:**
1. Configured routing profiles
2. Text tasks route to GPT-4o-mini
3. Vision tasks route to GPT-4o
4. Automatic selection based on input

## Running the Examples

```bash
# Agent with generation tools
PYTHONPATH=. python -m examples.18_multimodal.agent_with_generation_tools

# Standalone image generation
PYTHONPATH=. python -m examples.18_multimodal.standalone_generate_image

# Standalone video generation
PYTHONPATH=. python -m examples.18_multimodal.standalone_generate_video

# Voice generation
PYTHONPATH=. python -m examples.18_multimodal.agent_voice_generation

# Vision routing
PYTHONPATH=. python -m examples.18_multimodal.vision_routing_multimodal
```

## What's Next?

- Learn about [MCP integration](/agent-kit/integrations/mcp) for tool servers
- Explore [production serving](/agent-kit/production/serving)
- Understand [context management](/agent-kit/core/context)

## See Also

- [Multimodal documentation](/agent-kit/advanced/multimodality)
- [Image generation reference](/agent-kit/advanced/multimodality#image-generation)
- [Video generation reference](/agent-kit/advanced/multimodality#video-generation)
