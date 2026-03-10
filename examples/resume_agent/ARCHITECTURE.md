# Voice Agent: Personal Recruiter — Architecture

Real-world voice agent that answers recruiter calls, represents your professional profile, and can schedule meetings.

## System Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  TELEPHONY (Twilio)                                                 │
│  Phone number → WebSocket media stream (raw audio in/out)            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│  VOICE PIPELINE (Pipecat)                                           │
│  VAD → STT (Deepgram) → Syrin Agent → TTS (ElevenLabs) → Audio Out  │
│  Barge-in, echo cancel, turn-taking                                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ text in / text out
┌───────────────────────────────▼─────────────────────────────────────┐
│  SYRIN AGENT LAYER                                                  │
│  ResumeAgent: Knowledge (RAG), tools, budget, memory, guardrails     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│  KNOWLEDGE & STORAGE                                                │
│  data/ (resume, about, projects) → Syrin Knowledge (Postgres/Memory) │
└─────────────────────────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | This document |
| `README.md` | Setup, run, Twilio config |
| `agent.py` | Syrin ResumeAgent + Knowledge + tools |
| `syrin_processor.py` | Pipecat FrameProcessor adapter (Syrin → LLM frames) |
| `voice_server.py` | Pipecat pipeline: Twilio + Deepgram + Syrin + ElevenLabs |
| `data/` | Sample resume content for Knowledge ingestion |

## Flow (per user turn)

1. **Twilio** forwards inbound call audio via WebSocket to Pipecat
2. **VAD** (Voice Activity Detection) detects when user stops speaking
3. **Deepgram STT** transcribes speech → text
4. **LLM User Aggregator** collects transcript into context
5. **Syrin Processor** receives context, calls `agent.astream(user_text)`, streams response
6. **ElevenLabs TTS** converts response text → audio
7. **Twilio** sends audio back to caller

## Env Vars (examples/.env)

- `OPENAI_API_KEY` — LLM + embeddings
- `DEEPGRAM_AUTH_TOKEN` — STT (Pipecat may expect `DEEPGRAM_API_KEY`; we map in code)
- `ELEVENLABS_API_KEY` — TTS
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- `DATABASE_URL` — optional, for Postgres Knowledge backend

## Twilio Setup

1. Provision a Twilio phone number
2. Configure TwiML webhook → your server (ngrok for local)
3. Webhook URL must point to Pipecat’s Twilio transport handler
4. See `README.md` for step-by-step
