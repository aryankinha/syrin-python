---
title: Voice AI Agent
description: Build phone-callable AI agents with Syrin and Pipecat
weight: 380
---

## Voice AI Agent

Build AI agents that answer phone calls. This example combines **Syrin** (agent brain) with **Pipecat** (voice pipeline) and **Twilio** (telephony).

## Architecture

```
Phone Call (Twilio)
    ↓
Voice Pipeline (Pipecat: STT → Agent → TTS)
    ↓
Syrin Agent (Knowledge + Tools)
    ↓
Response
```

**Components:**
- **Twilio**: Receives phone calls, connects to WebSocket
- **Pipecat**: Handles speech-to-text (STT), voice activity detection (VAD), and text-to-speech (TTS)
- **Syrin**: Agent brain with knowledge base and scheduling tools

## The Resume Agent

A phone-callable AI that represents your professional profile to recruiters.

```python
from syrin import Agent, tool
from syrin.embedding import Embedding
from syrin.knowledge import Knowledge
from syrin.model import Model

@tool
def get_available_slots(date_range: str) -> str:
    """Check calendar availability for scheduling a meeting."""
    return "I have availability. How about March 18 at 2pm, March 19 at 10am?"

@tool
def book_appointment(date_time: str, recruiter_name: str, recruiter_email: str) -> str:
    """Book a meeting after recruiter confirms a time."""
    return f"Done! I've booked {date_time} for {recruiter_name}."

def create_resume_agent() -> Agent:
    knowledge = Knowledge(
        sources=[
            Knowledge.Markdown("data/about.md"),
            Knowledge.YAML("data/skills.yaml"),
            Knowledge.Directory("data/projects", glob="*.md"),
        ],
        embedding=Embedding.OpenAI("text-embedding-3-small"),
        backend=KnowledgeBackend.MEMORY,
        chunk_size=400,
        top_k=5,
    )
    
    return Agent(
        model=Model.OpenAI("gpt-4o-mini"),
        system_prompt=(
            "You are an AI voice assistant representing a professional. "
            "Answer questions about background, skills, and projects. "
            "Keep responses SHORT and CONVERSATIONAL (1-3 sentences). "
            "No bullet points or lists. Speak naturally."
        ),
        knowledge=knowledge,
        tools=[get_available_slots, book_appointment],
    )
```

**What just happened:**
1. Created knowledge base from resume files (markdown, YAML, projects)
2. Added scheduling tools for calendar integration
3. Configured system prompt for natural phone conversation

## Voice Server Setup

Connect to Twilio via Pipecat:

```python
# voice_server.py
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebSocketTransport,
)
from pipecat.transports.services.twilio import TwilioTransport

async def run_agent():
    transport = TwilioTransport(
        account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        audio_sample_rate=16000,
    )
    
    # Connect Pipecat to Syrin agent
    await transport.connect()
    
    # Agent handles conversation via WebSocket
    runner = PipelineRunner()
    await runner.run(pipeline)
```

## Running Text Mode

Test the agent without voice:

```bash
cd examples/resume_agent
source .venv/bin/activate
python agent.py
```

```
You: Tell me about Python experience
Agent: Based on the resume, Divyanshu has 5+ years of Python experience, 
       primarily using FastAPI and PyTorch for machine learning projects.
```

## Environment Setup

Required environment variables:

```bash
# LLM + Embeddings
OPENAI_API_KEY=sk-...

# Voice (STT/TTS)
DEEPGRAM_AUTH_TOKEN=...
ELEVENLABS_API_KEY=...

# Telephony
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
```

## Customizing Your Data

Edit files in `data/`:

```markdown
# data/about.md
## Divyanshu Shekhar
**Experience**: 5+ years software engineering
**Current**: Founder at Syrin AI
**Skills**: Python, ML, Distributed Systems
```

```yaml
# data/skills.yaml
skills:
  - name: Python
    level: Expert
    years: 5
  - name: Machine Learning
    level: Advanced
    years: 3
```

## Production: PostgreSQL Backend

For production knowledge storage:

```python
# Set DATABASE_URL in .env
# docker run -d --name syrin-pg -p 5434:5432 \
#   -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16

knowledge = Knowledge(
    sources=[...],
    backend=KnowledgeBackend.POSTGRES,
    connection_url="postgresql://postgres:postgres@localhost:5434/postgres",
)
```

## Deployment with ngrok

```bash
# Terminal 1: Expose local server
ngrok http 7860

# Terminal 2: Start voice server
python voice_server.py -t twilio -x YOUR_SUBDOMAIN.ngrok.io
```

## Twilio Configuration

1. Go to Twilio Console → Phone Numbers
2. Select your number
3. Set "A call comes in" to TwiML Bin:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://YOUR_HOST/ws" />
  </Connect>
</Response>
```

## Key Features

| Feature | Implementation |
| --- | --- |
| **Knowledge** | Resume files chunked and embedded |
| **Scheduling** | Stub tools (ready for Calendly) |
| **Short responses** | 1-3 sentences for phone |
| **No markdown** | Natural speech only |
| **Postgres** | Optional for production scale |

## Running the Example

```bash
# Setup
cd examples/resume_agent
uv sync
source .venv/bin/activate

# Test text mode
python agent.py

# Voice mode (requires Twilio + Pipecat)
python voice_server.py -t twilio -x YOUR.ngrok.io
```

## What's Next?

- Learn about [multimodal generation](/examples/multimodal)
- Explore [knowledge management](/examples/knowledge-agent)
- Understand [production serving](/production/serving)

## See Also

- [Multimodal documentation](/advanced/multimodality)
- [Knowledge pool documentation](/integrations/knowledge-pool)
- [Serving documentation](/production/serving)
