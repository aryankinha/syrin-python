"""Agentic RAG: query decomposition, result grading, refinement, and verification.

Implements multi-step retrieval when agentic=True on Knowledge. Provides:
- Query decomposition (split complex queries into sub-queries)
- Result grading (LLM or embedding-based relevance)
- Query refinement (rewrite and re-search when results are poor)
- Claim verification (SUPPORTED | CONTRADICTED | NOT_FOUND)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from syrin.enums import Hook
from syrin.knowledge._verification import _call_model, grade_results, verify_claim

if TYPE_CHECKING:
    from syrin.budget import BudgetTracker
    from syrin.events import EventContext
    from syrin.knowledge import Knowledge
    from syrin.knowledge._store import SearchResult
    from syrin.model import Model

# Used in search_knowledge_deep signature for append_grounded_facts callback
from syrin.knowledge._grounding import GroundedFact

_BUDGET_RATIO_THRESHOLD = 0.85  # Stop refinement when run_usage >= 0.85 * effective_run

_DECOMPOSE_PROMPT = """Given this user question, output 1-5 focused sub-questions that would help answer it.
One sub-question per line. No numbering, bullets, or prefixes. Just the questions.
Output nothing else.

Question:
{query}
"""

_REFINE_PROMPT = """The search results for this question were not sufficiently relevant.
Rewrite the question to improve retrieval. Output only the rewritten question, nothing else.

Original question: {query}

Results (low relevance):
{results}

Rewritten question:"""


@dataclass
class AgenticRAGConfig:
    """Configuration for agentic retrieval.

    Attributes:
        max_search_iterations: Max refinement loops before returning best-effort results.
        decompose_complex: Auto-decompose complex queries into sub-queries.
        grade_results: Use LLM to grade result relevance (otherwise use embedding score).
        relevance_threshold: Min score (0-1) to accept results without refinement.
        web_fallback: When True, tool may suggest web search if KB fails (agent must have web tool).
        verify_before_respond: Not implemented; reserved for future use.
        search_model: Model for decomposition/grading. None = use agent's model when attached.
    """

    max_search_iterations: int = 3
    decompose_complex: bool = True
    grade_results: bool = True
    relevance_threshold: float = 0.5
    web_fallback: bool = False
    verify_before_respond: bool = False  # Reserved; not implemented
    search_model: Model | None = None

    def __post_init__(self) -> None:
        if self.max_search_iterations < 1:
            raise ValueError("max_search_iterations must be >= 1")
        if not 0 <= self.relevance_threshold <= 1:
            raise ValueError("relevance_threshold must be in [0, 1]")


def _parse_sub_queries(text: str) -> list[str]:
    """Extract sub-questions from LLM output. One per line, stripped."""
    if not text or not text.strip():
        return []
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    # Remove common prefixes: "1.", "a)", "-", "*", "•", "(1)", "Q1:", etc.
    out: list[str] = []
    for line in lines:
        m = re.match(
            r"^(?:\(?[a-zA-Z\d]+[\.\)\:\-]\s*|[\u2022\u25e6\u25aa\u25cf\u2023*\-]+\s*)", line
        )
        if m:
            line = line[m.end() :].strip()
        if line:
            out.append(line)
    return out[:5]  # Cap at 5


async def decompose_query(
    query: str,
    model: Model,
    *,
    emit: Callable[[str, EventContext], None] | None = None,
    budget_tracker: BudgetTracker | None = None,
) -> list[str]:
    """Decompose a complex query into sub-queries via LLM.

    Returns a list of sub-queries (or [query] if decomposition yields nothing).
    """
    prompt = _DECOMPOSE_PROMPT.format(query=query)
    out = await _call_model(model, prompt, budget_tracker=budget_tracker)
    sub = _parse_sub_queries(out)
    if emit:
        from syrin.events import EventContext

        emit(
            Hook.KNOWLEDGE_AGENTIC_DECOMPOSE,
            EventContext({"query": query, "sub_queries": sub}),
        )
    return sub if sub else [query]


async def refine_query(
    query: str,
    results: list[SearchResult],
    model: Model,
    *,
    emit: Callable[[str, EventContext], None] | None = None,
    budget_tracker: BudgetTracker | None = None,
) -> str:
    """Rewrite the query to improve retrieval. Returns new query string."""
    previews = [
        f"[{r.rank}] {r.chunk.content[:150]}..."
        if len(r.chunk.content) > 150
        else f"[{r.rank}] {r.chunk.content}"
        for r in results[:5]
    ]
    results_text = "\n\n".join(previews)
    prompt = _REFINE_PROMPT.format(query=query, results=results_text)
    out = await _call_model(model, prompt, budget_tracker=budget_tracker)
    refined = out.strip() or query
    if emit:
        from syrin.events import EventContext

        emit(
            Hook.KNOWLEDGE_AGENTIC_REFINE,
            EventContext({"original": query, "refined": refined}),
        )
    return refined


def _format_results(results: list[SearchResult], max_per: int = 300) -> str:
    """Format search results for tool response."""
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


def _is_complex_query(query: str) -> bool:
    """Heuristic: query is complex if it has multiple clauses or 'and'."""
    q = query.strip().lower()
    if len(q) < 50:
        return False
    and_count = q.count(" and ") + q.count(" & ")
    or_count = q.count(" or ")
    question_marks = q.count("?")
    return and_count >= 1 or or_count >= 1 or question_marks >= 2


async def search_knowledge_deep(
    knowledge: Knowledge,
    query: str,
    *,
    source: str | None = None,
    config: AgenticRAGConfig,
    get_model: Callable[[], object | None],
    emit: Callable[[str, EventContext], None] | None = None,
    get_budget_tracker: Callable[[], object | None] | None = None,
    append_grounded_facts: Callable[[list[GroundedFact]], None] | None = None,
) -> str:
    """Deep search: decompose, search sub-queries, grade, refine if needed, consolidate."""
    model = cast(
        "Model | None",
        config.search_model or (get_model() if get_model is not None else None),
    )
    if model is None:
        return "search_knowledge_deep requires a model. Set agentic_config.search_model or use an Agent with a model."

    bt = cast("BudgetTracker | None", get_budget_tracker() if get_budget_tracker else None)

    from syrin.knowledge._store import MetadataFilter

    filt: MetadataFilter | None = {"source": source} if source else None

    all_results: list[SearchResult] = []
    queries_to_run: list[str] = [query]

    if config.decompose_complex and _is_complex_query(query):
        try:
            sub = await decompose_query(query, model, emit=emit, budget_tracker=bt)
            queries_to_run = sub if len(sub) > 1 else [query]
        except Exception:
            queries_to_run = [query]

    for q in queries_to_run:
        results = await knowledge.search(query=q, filter=filt)
        if not results:
            continue

        grade_score: float
        if config.grade_results:
            try:
                grade_score = await grade_results(q, results, model, emit=emit, budget_tracker=bt)
            except Exception:
                grade_score = results[0].score if results else 0.0
        else:
            grade_score = results[0].score if results else 0.0

        if grade_score >= config.relevance_threshold:
            all_results.extend(results)
            continue

        # Refinement loop
        refined = q
        for _ in range(config.max_search_iterations - 1):
            if (
                bt is not None
                and hasattr(bt, "run_usage_with_reserved")
                and hasattr(bt, "check_budget")
                and getattr(bt, "run_usage_with_reserved", 0) > 1.0
            ):
                break
            try:
                refined = await refine_query(refined, results, model, emit=emit, budget_tracker=bt)
            except Exception:
                break
            results = await knowledge.search(query=refined, filter=filt)
            if not results:
                break
            if config.grade_results:
                try:
                    grade_score = await grade_results(
                        refined, results, model, emit=emit, budget_tracker=bt
                    )
                except Exception:
                    grade_score = results[0].score if results else 0.0
            else:
                grade_score = results[0].score if results else 0.0
            if grade_score >= config.relevance_threshold:
                all_results.extend(results)
                break

        if not all_results and results:
            all_results.extend(results)

    if not all_results and config.web_fallback:
        return (
            "No sufficiently relevant results found in the knowledge base. "
            "Consider using web search if available."
        )

    # Deduplicate by content, preserve order
    seen_ids: set[str] = set()
    unique: list[SearchResult] = []
    for r in all_results:
        cid = f"{r.chunk.document_id}::{r.chunk.chunk_index}"
        if cid not in seen_ids:
            seen_ids.add(cid)
            unique.append(r)

    results_final = unique[:10]
    gconfig = getattr(knowledge, "_grounding_config", None)
    if gconfig is not None and gconfig.enabled:
        from syrin.knowledge._grounding import apply_grounding

        formatted, facts = await apply_grounding(
            query=query,
            results=results_final,
            config=gconfig,
            get_model=get_model,
            emit=emit,
            get_budget_tracker=get_budget_tracker,
        )
        if append_grounded_facts is not None and facts:
            append_grounded_facts(facts)
        return formatted
    return _format_results(results_final)


async def verify_knowledge(
    knowledge: Knowledge,
    claim: str,
    *,
    config: AgenticRAGConfig,
    get_model: Callable[[], object | None],
    emit: Callable[[str, EventContext], None] | None = None,
    get_budget_tracker: Callable[[], object | None] | None = None,
) -> str:
    """Verify if a claim is supported, contradicted, or not found in the knowledge base."""
    model = cast(
        "Model | None",
        config.search_model or (get_model() if get_model is not None else None),
    )
    if model is None:
        return "verify_knowledge requires a model. Set agentic_config.search_model or use an Agent with a model."

    results = await knowledge.search(claim)
    bt = cast("BudgetTracker | None", get_budget_tracker() if get_budget_tracker else None)
    verdict = await verify_claim(claim, results, model, emit=emit, budget_tracker=bt)

    best = results[0] if results else None
    score_str = f"{best.score:.2f}" if best else "N/A"
    preview = (
        (best.chunk.content[:100] + "...")
        if best and len(best.chunk.content) > 100
        else (best.chunk.content if best else "")
    )

    return f"VERDICT: {verdict}\nScore: {score_str}\nRelevant: {preview}"
