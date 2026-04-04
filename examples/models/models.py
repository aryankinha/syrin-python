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
# High token amount and pricing tier so budget visibly decreases in playground.
almock = Model.mock(
    latency_min=1,
    latency_max=3,
    lorem_length=800,
    pricing_tier="high",
)

# Almock for DynamicPipeline orchestrator — returns valid JSON plan so agents spawn
# Latency mimics real API calls for playground UX
almock_orchestrator = Model.mock(
    latency_min=0.3,
    latency_max=0.8,
    response_mode="custom",
    custom_response='[{"type":"researcher","task":"Research the user request"},{"type":"fact_checker","task":"Verify the research findings"}]',
    pricing_tier="high",
)

# Almock custom replies for DynamicPipeline spawned agents (demo-friendly output)
# Latency mimics real API calls for playground UX
almock_researcher = Model.mock(
    latency_min=0.5,
    latency_max=1.2,
    response_mode="custom",
    custom_response="Research findings: Based on the user's request, here are key points and sources. [Simulated research output for demo.]",
    pricing_tier="high",
)
almock_analyst = Model.mock(
    latency_min=0.5,
    latency_max=1.2,
    response_mode="custom",
    custom_response="Analysis: Structured evaluation of the topic. Pros and cons summarized. [Simulated analysis for demo.]",
    pricing_tier="high",
)
almock_writer = Model.mock(
    latency_min=0.5,
    latency_max=1.2,
    response_mode="custom",
    custom_response="Draft: Clear, concise content based on the provided context. [Simulated draft for demo.]",
    pricing_tier="high",
)
almock_fact_checker = Model.mock(
    latency_min=0.5,
    latency_max=1.2,
    response_mode="custom",
    custom_response="Fact check: Verified claims. Sources confirmed. No major inaccuracies found. [Simulated fact check for demo.]",
    pricing_tier="high",
)
almock_summarizer = Model.mock(
    latency_min=0.5,
    latency_max=1.2,
    response_mode="custom",
    custom_response="Summary: Key takeaways and executive summary of the research and analysis. [Simulated summary for demo.]",
    pricing_tier="high",
)


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
