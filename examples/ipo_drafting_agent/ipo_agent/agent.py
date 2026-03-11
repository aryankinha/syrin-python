"""DRHP Drafting Agent - Capital Structure & Shareholding Pattern."""

from __future__ import annotations

import os
from pathlib import Path

from syrin import Agent, Output
from syrin.embedding import Embedding
from syrin.enums import KnowledgeBackend
from syrin.knowledge import (
    AgenticRAGConfig,
    ChunkConfig,
    ChunkStrategy,
    GroundingConfig,
    Knowledge,
)
from syrin.model import Model

from .models import DraftOutput

# Base path for data (relative to this file)
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _data_path(*parts: str) -> Path:
    return _DATA_DIR.joinpath(*parts)


SYSTEM_PROMPT = """You are a DRHP drafting assistant for Capital Structure and Shareholding Pattern.

CRITICAL - Call search_knowledge FIRST. Use these queries: "capital structure", "authorized capital", "issued capital", "shareholding", "PAS-3", "List of Allottees", "allottees", "equity shares", "MOA", "SH-7". Do NOT answer until you have retrieved facts.

RULES:
- Copy numbers and names EXACTLY from search results. Do not invent or approximate.
- For shareholding: List of Allottees has Rohit Sharma 192, Suresh Sharma 192, Sunrise Engineering Works 576. MOA subscribers have different numbers - use List of Allottees for post-allotment allottees.
- Post-allotment: total 19,321 shares, Rs. 1,93,210 (from PAS-3 capital structure table).
- draft_section MUST be paragraph-style legal disclosure using ONLY facts from search results.
- Do NOT use "Example Limited" or any invented company name. Use the company name from the documents.

Output a single valid JSON object (no markdown, no code blocks):
{
  "draft_section": "<paragraph in formal legal language>",
  "sources_used": ["<doc names used>"],
  "auto_extracted_parts": ["<fields extracted from docs>"],
  "requires_review": ["<items needing human verification>"]
}"""


def create_knowledge(data_dir: Path | None = None, api_key: str | None = None) -> Knowledge:
    """Create Knowledge orchestrator with document sources."""
    base = data_dir or _DATA_DIR
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for embeddings")

    embedding = Embedding.OpenAI("text-embedding-3-small", api_key=api_key)

    # Load all supported formats from data dir (PAS-3, SH-7, etc.)
    sources = [Knowledge.Directory(str(base), glob="**/*.md")]

    return Knowledge(
        sources=sources,
        embedding=embedding,
        backend=KnowledgeBackend.MEMORY,
        chunk_config=ChunkConfig(
            strategy=ChunkStrategy.RECURSIVE,
            chunk_size=512,
            min_chunk_size=64,
        ),
        top_k=12,
        score_threshold=0.2,
        agentic=True,
        agentic_config=AgenticRAGConfig(
            max_search_iterations=3,
            decompose_complex=True,
            grade_results=True,
            relevance_threshold=0.35,
            web_fallback=False,
        ),
        # extract_facts=False: fast path, no LLM per search; raw chunks with grounding metadata.
        grounding=GroundingConfig(
            extract_facts=True,
            verify_before_use=True,
            cite_sources=True,
            confidence_threshold=0.7,
        ),
        inject_system_prompt=True,
    )


def create_agent(
    *,
    data_dir: Path | None = None,
    api_key: str | None = None,
    model_id: str = "gpt-4o",
) -> Agent:
    """Create the DRHP drafting agent."""
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    knowledge = create_knowledge(data_dir=data_dir, api_key=api_key)

    return Agent(
        name="ipo_drafting_agent",
        description="A DRHP drafting assistant for Capital Structure and Shareholding Pattern.",
        model=Model.OpenAI(model_id, api_key=api_key),
        system_prompt=SYSTEM_PROMPT,
        knowledge=knowledge,
        output=Output(DraftOutput, validation_retries=3),
        max_tool_iterations=15,
    )
