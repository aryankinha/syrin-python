"""Voice server — Pipecat pipeline with Twilio, Deepgram, ElevenLabs, Syrin.

Run:
    1. pip install "pipecat-ai[deepgram,elevenlabs,twilio]"
    2. Set env in examples/.env: OPENAI_API_KEY, DEEPGRAM_AUTH_TOKEN, ELEVENLABS_API_KEY,
       TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
    3. ngrok http 7860  # expose local server
    4. Configure Twilio TwiML Bin: <Stream url="wss://YOUR_NGROK.ngrok.io/ws" />
    5. python voice_server.py -t twilio -x your-ngrok-subdomain.ngrok.io

    6. Call your Twilio number — the agent will answer.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root for imports
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root.parent))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

# Map DEEPGRAM_AUTH_TOKEN → DEEPGRAM_API_KEY if needed (Pipecat expects DEEPGRAM_API_KEY)
if not os.getenv("DEEPGRAM_API_KEY") and os.getenv("DEEPGRAM_AUTH_TOKEN"):
    os.environ["DEEPGRAM_API_KEY"] = os.environ["DEEPGRAM_AUTH_TOKEN"]


def _check_env() -> None:
    required = [
        "OPENAI_API_KEY",
        "DEEPGRAM_API_KEY",
        "ELEVENLABS_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise SystemExit(f"Missing env: {', '.join(missing)}. Set in examples/.env")


# Pipecat imports (lazy - only when bot runs)
def _get_pipecat():
    try:
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.frames.frames import LLMRunFrame
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.processors.aggregators.llm_context import LLMContext
        from pipecat.processors.aggregators.llm_response_universal import (
            LLMContextAggregatorPair,
            LLMUserAggregatorParams,
        )
        from pipecat.runner.utils import create_transport
        from pipecat.services.deepgram.stt import DeepgramSTTService
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
        from pipecat.transports.base_transport import BaseTransport
        from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams

        return {
            "SileroVADAnalyzer": SileroVADAnalyzer,
            "LLMRunFrame": LLMRunFrame,
            "Pipeline": Pipeline,
            "PipelineRunner": PipelineRunner,
            "PipelineParams": PipelineParams,
            "PipelineTask": PipelineTask,
            "LLMContext": LLMContext,
            "LLMContextAggregatorPair": LLMContextAggregatorPair,
            "LLMUserAggregatorParams": LLMUserAggregatorParams,
            "create_transport": create_transport,
            "DeepgramSTTService": DeepgramSTTService,
            "ElevenLabsTTSService": ElevenLabsTTSService,
            "BaseTransport": BaseTransport,
            "FastAPIWebsocketParams": FastAPIWebsocketParams,
        }
    except ImportError as e:
        raise SystemExit(
            f"Install Pipecat: pip install 'pipecat-ai[deepgram,elevenlabs,twilio]'\nError: {e}"
        ) from e


async def run_bot(transport, runner_args):
    pc = _get_pipecat()
    from agent import get_resume_agent
    from syrin_processor import SyrinLLMProcessor

    stt = pc["DeepgramSTTService"](api_key=os.getenv("DEEPGRAM_API_KEY"))
    tts = pc["ElevenLabsTTSService"](
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
    )
    agent = get_resume_agent()
    llm = SyrinLLMProcessor(agent)

    context = pc["LLMContext"]()
    user_aggregator, assistant_aggregator = pc["LLMContextAggregatorPair"](
        context,
        user_params=pc["LLMUserAggregatorParams"](vad_analyzer=pc["SileroVADAnalyzer"]()),
    )

    pipeline = pc["Pipeline"](
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    task = pc["PipelineTask"](
        pipeline,
        params=pc["PipelineParams"](
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(tr, client):
        context.add_message(
            {
                "role": "user",
                "content": "Please introduce yourself briefly as Divyanshu Shekhar's assistant for this recruiter call.",
            }
        )
        await task.queue_frames([pc["LLMRunFrame"]()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(tr, client):
        await task.cancel()

    runner = pc["PipelineRunner"](handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


async def bot(runner_args):
    """Pipecat runner entry point. Must be at module level."""
    _check_env()
    pc = _get_pipecat()
    params = {
        "twilio": lambda: pc["FastAPIWebsocketParams"](
            audio_in_enabled=True, audio_out_enabled=True
        ),
        "webrtc": lambda: pc["FastAPIWebsocketParams"](
            audio_in_enabled=True, audio_out_enabled=True
        ),
    }
    transport = await pc["create_transport"](runner_args, params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
