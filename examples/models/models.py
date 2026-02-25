"""
Centralized model definitions for Syrin examples.

Import and use anywhere in examples:

    from examples.models.models import gpt4, claude, deepseek_chat, kimi, grok
    agent = Agent(model=gpt4, system_prompt="You are helpful.")

Models require API keys to be passed explicitly (library design).
This file reads from env for example convenience - in your app, pass keys
from your config/secrets manager.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from syrin import Model

# Load .env from examples root so examples can import without calling load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# -----------------------------------------------------------------------------
# Almock (An LLM Mock) — no API key required; use for local testing and CI
# -----------------------------------------------------------------------------
# Use this to run examples without any API key. Uncomment the Almock line in
# each example and comment the real model to try the library with zero cost.
almock = Model.Almock(latency_min=0, latency_max=0, lorem_length=80)


# -----------------------------------------------------------------------------
# Provider models - pass api_key explicitly (examples use env for convenience)
# -----------------------------------------------------------------------------

gpt4 = Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
gpt4_mini = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

claude = Model.Anthropic("claude-sonnet-4-5", api_key=os.getenv("ANTHROPIC_API_KEY"))
claude_opus = Model.Anthropic("claude-opus-4-5", api_key=os.getenv("ANTHROPIC_API_KEY"))

ollama_llama = Model.Ollama("llama3")  # Local - no api_key
ollama_mistral = Model.Ollama("mistral")

gemini = Model.Google("gemini-2.0-flash", api_key=os.getenv("GOOGLE_API_KEY"))
gemini_pro = Model.Google("gemini-1.5-pro", api_key=os.getenv("GOOGLE_API_KEY"))

# LiteLLM - single api_key for many providers
litellm_gpt4 = Model.LiteLLM("openai/gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
litellm_claude = Model.LiteLLM(
    "anthropic/claude-3-5-sonnet", api_key=os.getenv("ANTHROPIC_API_KEY")
)


# -----------------------------------------------------------------------------
# OpenAI-compatible third-party models (Model.Custom)
# -----------------------------------------------------------------------------

# DeepSeek - https://platform.deepseek.com
deepseek_chat = Model.Custom(
    "deepseek-chat",
    api_base="https://api.deepseek.com/v1",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    context_window=128_000,
)
deepseek_reasoner = Model.Custom(
    "deepseek-reasoner",
    api_base="https://api.deepseek.com/v1",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    context_window=128_000,
)

# KIMI (Moonshot) - https://platform.moonshot.ai
# Use api.moonshot.ai (international) or api.moonshot.cn (China)
kimi = Model.Custom(
    "moonshot-v1-8k",
    api_base="https://api.moonshot.ai/v1",
    api_key=os.getenv("MOONSHOT_API_KEY"),
    context_window=8_192,
)
kimi_large = Model.Custom(
    "kimi-k2-turbo-preview",
    api_base="https://api.moonshot.ai/v1",
    api_key=os.getenv("MOONSHOT_API_KEY"),
    context_window=128_000,
)

# Grok (xAI) - https://docs.x.ai
grok = Model.Custom(
    "grok-3-mini",
    api_base="https://api.x.ai/v1",
    api_key=os.getenv("XAI_API_KEY"),
    context_window=131_072,
)
grok_pro = Model.Custom(
    "grok-3",
    api_base="https://api.x.ai/v1",
    api_key=os.getenv("XAI_API_KEY"),
    context_window=131_072,
)
