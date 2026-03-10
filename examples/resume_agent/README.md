# Voice Agent: Personal Recruiter

A phone-callable AI agent that represents your professional profile to recruiters. Built with **Syrin** (agent brain) + **Pipecat** (voice pipeline).

## Setup

```bash
cd examples/resume_agent
uv venv .venv
uv sync
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system diagram.

**Flow:** Twilio (phone) → Pipecat (STT/TTS/VAD) → Syrin Agent (Knowledge, tools) → response

## Quick Start (Text Mode)

From this directory with the venv activated:

```bash
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python agent.py
```

Type questions; the agent uses the knowledge base (data/about.md, data/skills.yaml, data/projects/).

## Voice Mode (Phone Call)

### 1. Install Pipecat

```bash
pip install "pipecat-ai[deepgram,elevenlabs]"
# Or: uv sync (from this directory)
```

### 2. Environment

Ensure `examples/.env` (parent of resume_agent) has:

- `OPENAI_API_KEY` — LLM + embeddings
- `DEEPGRAM_AUTH_TOKEN` or `DEEPGRAM_API_KEY` — STT
- `ELEVENLABS_API_KEY` — TTS
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` — telephony

### 3. Customize Your Data

Edit `data/about.md`, `data/skills.yaml`, and `data/projects/` with your resume and projects. The agent answers from this knowledge.

### 4. Run Locally with ngrok

```bash
# Terminal 1: Expose local server
ngrok http 7860

# Terminal 2: Start voice server (from examples/resume_agent/)
source .venv/bin/activate
python voice_server.py -t twilio -x YOUR_NGROK_SUBDOMAIN.ngrok.io
```

Use `-x` with your ngrok host (e.g. `abc123.ngrok-free.app`) so Twilio can reach the WebSocket.

### 5. Configure Twilio

1. Go to [Twilio Console](https://console.twilio.com/) → Phone Numbers → your number.
2. Under "Voice Configuration", set "A call comes in" to **TwiML Bin**.
3. Create a TwiML Bin with:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://https://6487-2405-201-d061-7-109e-2475-3a67-5aeb.ngrok-free.app/ws" />
  </Connect>
</Response>
```

Replace `YOUR_NGROK_HOST` with your ngrok URL (e.g. `abc123.ngrok-free.app`).

### 6. Call

Call your Twilio number. The agent will greet you and answer questions about the resume content in `data/`.

## Optional: Postgres Knowledge Backend

For production, use Postgres + pgvector for Knowledge:

1. Start Postgres with pgvector:  
   `docker run -d --name syrin-pg -p 5434:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16`
2. Set in `examples/.env`:

   ```
   DATABASE_URL=postgresql://postgres:postgres@localhost:5434/postgres
   ```

3. Install: `uv sync --extra knowledge-postgres`

The agent will use Postgres for the knowledge store.

## Configuration You May Need

| Need | Action |
|------|--------|
| Different ElevenLabs voice | Set `ELEVENLABS_VOICE_ID` in `.env` |
| Deepgram key | Use `DEEPGRAM_AUTH_TOKEN` (mapped to `DEEPGRAM_API_KEY` in code) |
| Twilio number | Ensure it supports Voice; configure the TwiML Bin as above |
