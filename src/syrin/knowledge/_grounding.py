"""Grounding layer: fact extraction, verification, and grounded context.

When grounding=True on Knowledge, search returns pre-extracted, pre-verified
facts instead of raw chunks — reducing hallucination by design.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from syrin.enums import Hook, VerificationStatus
from syrin.knowledge._store import SearchResult, chunk_id
from syrin.knowledge._verification import _call_model, verify_claim

if TYPE_CHECKING:
    from syrin.budget import BudgetTracker
    from syrin.events import EventContext
    from syrin.model import Model

_log = logging.getLogger(__name__)

_EXTRACT_PROMPT = """Extract distinct factual statements from the following search results.
For each fact, provide: the factual statement, source document (use the document identifier from the context), page number if available, and confidence (0.0-1.0).
Output a JSON array. Each object must have: "fact", "source", "page" (int or null), "confidence".
Extract 1-15 facts. Be precise; do not invent information.
If the results contain no extractable facts, return [].

Query: {query}

Search results:
{results}

JSON array:"""


def _status_from_verdict(verdict: str) -> VerificationStatus:
    """Map verify_claim verdict string to VerificationStatus."""
    v = verdict.upper()
    if v == "SUPPORTED":
        return VerificationStatus.VERIFIED
    if v == "CONTRADICTED":
        return VerificationStatus.CONTRADICTED
    return VerificationStatus.NOT_FOUND


@dataclass
class GroundedFact:
    """A single verified fact extracted from a knowledge source.

    Attributes:
        content: The factual statement.
        source: Source document identifier (file path, URL, etc.).
        page: Page number in source document (if applicable).
        confidence: Confidence score in [0, 1].
        verification: Verification status — VERIFIED, UNVERIFIED, CONTRADICTED, NOT_FOUND.
        chunk_id: ID of the source chunk (document_id::chunk_index).
        metadata: Additional metadata (table_index, section, etc.).
    """

    content: str
    source: str
    page: int | None = None
    confidence: float = 0.0
    verification: VerificationStatus = VerificationStatus.UNVERIFIED
    chunk_id: str | None = None
    metadata: dict[str, str | int | float | bool | None | list[str]] = field(default_factory=dict)


@dataclass
class GroundingConfig:
    """Configuration for the grounding layer on Knowledge.

    Attributes:
        enabled: Whether grounding is active.
        extract_facts: Extract structured facts from retrieved chunks.
        cite_sources: Attach source doc + page to each fact.
        flag_missing: Explicitly flag when expected data is missing.
        verify_before_use: Verify each fact using verify_claim before including.
        confidence_threshold: Minimum confidence to include a fact (0.0-1.0).
        max_facts: Maximum facts to extract per search. None = no limit.
    """

    enabled: bool = True
    extract_facts: bool = True
    cite_sources: bool = True
    flag_missing: bool = True
    verify_before_use: bool = True
    confidence_threshold: float = 0.7
    max_facts: int | None = 15

    def __post_init__(self) -> None:
        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be in [0, 1]")
        if self.max_facts is not None and self.max_facts < 1:
            raise ValueError("max_facts must be >= 1 or None")


async def _extract_facts(
    query: str,
    results: list[SearchResult],
    model: Model,
    *,
    emit: Callable[[str, EventContext], None] | None = None,
    budget_tracker: BudgetTracker | None = None,
    max_facts: int | None = 15,
) -> list[GroundedFact]:
    """Extract structured facts from search results via LLM."""
    if not results:
        return []

    if emit:
        from syrin.events import EventContext

        emit(
            Hook.GROUNDING_EXTRACT_START,
            EventContext({"query": query[:200], "chunk_count": len(results)}),
        )

    results_text = "\n\n".join(
        f"[{r.rank}] Source: {r.chunk.document_id} | {r.chunk.content[:400]}"
        + ("..." if len(r.chunk.content) > 400 else "")
        for r in results[:10]
    )
    prompt = _EXTRACT_PROMPT.format(query=query, results=results_text)
    try:
        out = await _call_model(model, prompt, budget_tracker=budget_tracker)
    except Exception as e:
        _log.warning("Fact extraction failed: %s. Falling back to chunk-as-fact.", e)
        return _chunks_to_facts(results)

    facts: list[GroundedFact] = []
    try:
        parsed = json.loads(out.strip())
        if not isinstance(parsed, list):
            parsed = []
    except json.JSONDecodeError:
        _log.debug(
            "Could not parse extraction JSON for query %r. Falling back to chunk-as-fact.",
            query[:50],
        )
        return _chunks_to_facts(results)

    for i, item in enumerate(parsed[: max_facts or 999]):
        if not isinstance(item, dict):
            continue
        fact_str = item.get("fact") or item.get("content") or ""
        if not fact_str or not isinstance(fact_str, str):
            continue
        source_val = item.get("source")
        source_str = str(source_val) if source_val is not None else ""
        page_val = item.get("page")
        page_int: int | None = None
        if isinstance(page_val, int):
            page_int = page_val
        elif isinstance(page_val, float) and page_val == int(page_val):
            page_int = int(page_val)
        conf_val = item.get("confidence", 0.5)
        try:
            conf = max(0.0, min(1.0, float(conf_val)))
        except (TypeError, ValueError):
            conf = 0.5
        r = results[i] if i < len(results) else results[-1] if results else None
        cid = chunk_id(r.chunk) if r else None
        if not source_str and r:
            source_str = r.chunk.document_id
        if page_int is None and r:
            pval = r.chunk.metadata.get("page")
            if isinstance(pval, (int, float)):
                page_int = int(pval)
        facts.append(
            GroundedFact(
                content=fact_str.strip(),
                source=source_str or "unknown",
                page=page_int,
                confidence=conf,
                verification=VerificationStatus.UNVERIFIED,
                chunk_id=cid,
                metadata={},
            )
        )

    if emit:
        from syrin.events import EventContext

        emit(
            Hook.GROUNDING_EXTRACT_END,
            EventContext({"fact_count": len(facts), "query": query[:200]}),
        )

    return facts


def _format_raw_results(results: list[SearchResult], max_per: int = 300) -> str:
    """Format raw search results for tool response (fallback when grounding yields no facts)."""
    if not results:
        return "No relevant results found."
    lines: list[str] = []
    seen: set[str] = set()
    for r in results:
        content = r.chunk.content[:max_per] + ("..." if len(r.chunk.content) > max_per else "")
        if content in seen:
            continue
        seen.add(content)
        lines.append(f"[{r.rank}] (score={r.score:.2f}) {content}")
    return "\n\n".join(lines)


def _chunks_to_facts(results: list[SearchResult]) -> list[GroundedFact]:
    """Fallback: treat each chunk as a single fact when extraction fails."""
    facts: list[GroundedFact] = []
    for r in results[:10]:
        source = r.chunk.document_id
        page = None
        pval = r.chunk.metadata.get("page")
        if isinstance(pval, (int, float)):
            page = int(pval)
        facts.append(
            GroundedFact(
                content=r.chunk.content[:500] + ("..." if len(r.chunk.content) > 500 else ""),
                source=source,
                page=page,
                confidence=r.score,
                verification=VerificationStatus.UNVERIFIED,
                chunk_id=chunk_id(r.chunk),
                metadata={},
            )
        )
    return facts


async def _verify_facts(
    facts: list[GroundedFact],
    results: list[SearchResult],
    model: Model,
    *,
    emit: Callable[[str, EventContext], None] | None = None,
    budget_tracker: BudgetTracker | None = None,
) -> list[GroundedFact]:
    """Verify each fact against source chunks using verify_claim."""
    if not results:
        return [
            GroundedFact(
                content=f.content,
                source=f.source,
                page=f.page,
                confidence=f.confidence,
                verification=VerificationStatus.NOT_FOUND,
                chunk_id=f.chunk_id,
                metadata=f.metadata,
            )
            for f in facts
        ]

    verified: list[GroundedFact] = []
    for f in facts:
        verdict = await verify_claim(
            f.content,
            results,
            model,
            emit=emit,
            budget_tracker=budget_tracker,
        )
        status = _status_from_verdict(verdict)
        if emit:
            from syrin.events import EventContext

            emit(
                Hook.GROUNDING_VERIFY,
                EventContext(
                    {"fact": f.content[:100], "verdict": verdict, "confidence": f.confidence}
                ),
            )
        verified.append(
            GroundedFact(
                content=f.content,
                source=f.source,
                page=f.page,
                confidence=f.confidence,
                verification=status,
                chunk_id=f.chunk_id,
                metadata=f.metadata,
            )
        )
    return verified


def _format_grounded_facts(
    facts: list[GroundedFact],
    config: GroundingConfig,
) -> str:
    """Format grounded facts as human-readable string for tool response."""
    if not facts:
        return "No grounded facts available."
    lines: list[str] = []
    lines.append("GROUNDED FACTS (verified against source documents):")
    for i, f in enumerate(facts, 1):
        if f.confidence < config.confidence_threshold:
            continue
        status = f"[{f.verification.value}]"
        cite = ""
        if config.cite_sources and f.source:
            cite = f" [Source: {f.source}"
            if f.page is not None:
                cite += f", Page {f.page}"
            cite += "]"
        lines.append(f"{i}. {status} {f.content}{cite}")
    if config.flag_missing:
        missing = [
            f
            for f in facts
            if f.verification == VerificationStatus.NOT_FOUND
            and f.confidence >= config.confidence_threshold
        ]
        if missing:
            lines.append("")
            lines.append("[NOT FOUND] The following could not be verified in source documents:")
            for m in missing[:5]:
                lines.append(f"- {m.content[:80]}...")
    return "\n".join(lines) if lines else "No facts passed confidence threshold."


async def apply_grounding(
    query: str,
    results: list[SearchResult],
    config: GroundingConfig,
    get_model: Callable[[], object | None],
    *,
    emit: Callable[[str, EventContext], None] | None = None,
    get_budget_tracker: Callable[[], object | None] | None = None,
) -> tuple[str, list[GroundedFact]]:
    """Apply grounding to search results: extract facts, verify, format.

    Call after obtaining results from knowledge.search() or agentic flow.
    Returns formatted grounded context string and list of GroundedFact.

    Returns:
        (formatted_string, list_of_grounded_facts)
    """
    results_list = results
    if not results_list:
        return "No relevant results found. No grounded facts available.", []

    # Fast path: skip LLM extraction when extract_facts=False (raw chunks, no latency).
    if not config.extract_facts:
        return _format_raw_results(results_list), []

    model = cast("Model | None", get_model() if get_model is not None else None)
    if model is None:
        return (
            "Grounding requires a model. Set agent model or grounding_config.search_model.",
            [],
        )

    bt = cast(
        "BudgetTracker | None",
        get_budget_tracker() if get_budget_tracker else None,
    )

    facts = await _extract_facts(
        query,
        results_list,
        model,
        emit=emit,
        budget_tracker=bt,
        max_facts=config.max_facts,
    )
    if not facts:
        return _format_raw_results(results_list), []

    if config.verify_before_use:
        facts = await _verify_facts(
            facts,
            results_list,
            model,
            emit=emit,
            budget_tracker=bt,
        )

    if emit:
        from syrin.events import EventContext

        verified_count = sum(1 for f in facts if f.verification == VerificationStatus.VERIFIED)
        unverified_count = sum(1 for f in facts if f.verification == VerificationStatus.UNVERIFIED)
        missing_count = sum(1 for f in facts if f.verification == VerificationStatus.NOT_FOUND)
        emit(
            Hook.GROUNDING_COMPLETE,
            EventContext(
                {
                    "verified_count": verified_count,
                    "unverified_count": unverified_count,
                    "missing_count": missing_count,
                    "total": len(facts),
                }
            ),
        )

    formatted = _format_grounded_facts(facts, config)
    return formatted, facts
