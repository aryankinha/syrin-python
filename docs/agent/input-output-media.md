---
title: Input/Output Media
description: Handle text, images, audio, video, and file attachments in agent conversations.
weight: 68
---

## Beyond Text: Images, Audio, Video, Files

Your users don't think in text only. They upload X-rays, record voice memos, send PDFs, and share videos. A text-only agent ignores most of how humans communicate.

Syrin handles all media types seamlessly—declare what you accept, what you produce, and the framework handles the rest.

Traditional chatbots are text-only. But real-world use cases demand more:

- A medical imaging agent needs to analyze X-rays
- A voice assistant needs speech input and output
- A document processing agent needs PDF attachments
- A video analysis agent needs to watch footage

Building these capabilities from scratch means wrestling with different APIs, formats, and model capabilities.

## The Solution

Syrin uses the `Media` enum to declare what your agent accepts and produces:

```python
from syrin import Agent, Model
from syrin.enums import Media

# Text-only agent (default)
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a helpful assistant.",
)

# Vision agent that accepts images
vision_agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    input_media={Media.TEXT, Media.IMAGE},
    system_prompt="You analyze medical images.",
)

# Multimodal agent that produces images
creative_agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    input_media={Media.TEXT, Media.IMAGE},
    output_media={Media.TEXT, Media.IMAGE},
    system_prompt="You are a creative artist.",
)
```

**What just happened:** We declared media capabilities for each agent. Syrin validates these against model capabilities and automatically configures the right tools.

## Media Types

| Type | Description | Common Use Cases |
|------|-------------|------------------|
| `TEXT` | Plain text | All agents (default) |
| `IMAGE` | Images (JPEG, PNG, GIF, WebP) | Vision analysis, image generation |
| `AUDIO` | Audio files (MP3, WAV, etc.) | Voice assistants, transcription |
| `VIDEO` | Video files or frames | Video analysis |
| `FILE` | Generic attachments (PDF, docs) | Document processing |

## Image Input

Process images that users send:

```python
from syrin import Agent, Model
from syrin.enums import Media

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    input_media={Media.TEXT, Media.IMAGE},
    system_prompt="You are a helpful image analyst.",
)

# Send an image URL
result = agent.run([
    {"type": "text", "text": "What's in this image?"},
    {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}},
])

# Send base64-encoded image
import base64
with open("photo.jpg", "rb") as f:
    img_data = base64.b64encode(f.read()).decode()
    
result = agent.run([
    {"type": "text", "text": "Analyze this image."},
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}},
])
```

**What just happened:** We sent an image along with text. The model sees both and can answer questions about the image.

## Image Generation

Produce images as output:

```python
from syrin import Agent, Model
from syrin.enums import Media

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    output_media={Media.TEXT, Media.IMAGE},
    system_prompt="You are a creative artist. Generate images when helpful.",
)

# Request an image
result = agent.run("Create a sunset over mountains")
print(result.generated_media)  # Contains image data
```

**What just happened:** The agent can now generate images. When it decides an image would help, it creates one automatically.

## File Attachments

Process uploaded files:

```python
from syrin import Agent, Model, InputFileRules
from syrin.enums import Media

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    input_media={Media.TEXT, Media.FILE},
    input_file_rules=InputFileRules(
        allowed_mime_types=["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        max_size_mb=10,
    ),
    system_prompt="You summarize documents.",
)

# Send a file
result = agent.run([
    {"type": "text", "text": "Summarize this document."},
    {"type": "file", "file": {"url": "https://example.com/report.pdf"}},
])
```

**What just happened:** We configured the agent to accept PDF and Word files up to 10MB. The model can now read and analyze document content.

## Audio Input

Process voice and audio:

```python
from syrin import Agent, Model
from syrin.enums import Media

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    input_media={Media.TEXT, Media.AUDIO},
    system_prompt="You transcribe and summarize audio.",
)

# Send audio file
result = agent.run([
    {"type": "text", "text": "Transcribe this audio."},
    {"type": "audio_url", "audio_url": {"url": "https://example.com/recording.mp3"}},
])
```

## Audio Output (Voice)

Generate spoken responses:

```python
from syrin import Agent, Model
from syrin.generation import VoiceGenerator

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    output_media={Media.TEXT, Media.AUDIO},
    voice_generation=VoiceGenerator(
        voice="alloy",  # OpenAI voice options
    ),
    system_prompt="You are a helpful voice assistant.",
)
```

## Hooks for Media

Monitor media processing:

```python
agent.events.on("generation.image.start", lambda e: 
    print(f"Generating image with {e.get('model', 'default')}")
)

agent.events.on("generation.image.end", lambda e: 
    print(f"Image generated: {e.get('size', 'unknown')}")
)

agent.events.on("llm.request.start", lambda e:
    print(f"Media types in request: {e.get('media_types', [])}")
)
```

## Message Format

Send mixed content in a single request:

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    input_media={Media.TEXT, Media.IMAGE, Media.FILE},
)

# Mixed content request
result = agent.run([
    {"type": "text", "text": "Look at this document and image, then answer:"},
    {"type": "file", "file": {"url": "https://example.com/report.pdf"}},
    {"type": "image_url", "image_url": {"url": "https://example.com/diagram.png"}},
    {"type": "text", "text": "Does the diagram match the document?"},
])
```

**What just happened:** We sent text, a PDF, and an image in one request. The agent processes all of them together.

---

## What's Next?

- [Advanced: Multimodality](/advanced/multimodality) — Deep dive into media handling
- [Advanced: Image Generation](/agent/input-output-media) — Generate images
- [Advanced: Voice](/agent/input-output-media) — Voice output

## See Also

- [Core Concepts: Models](/core/models) — Multimodal models
- [Agents: Tools](/agent/tools) — Tools that handle media
- [Integrations: MCP](/integrations/mcp) — External media tools
