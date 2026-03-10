"""Agent integration helpers — build router and profiles from model lists."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from syrin.model import Model

if TYPE_CHECKING:
    from syrin.budget import Budget
from syrin.enums import Media
from syrin.router.config import RoutingConfig
from syrin.router.enums import TaskType
from syrin.router.router import ModelRouter, _RoutingProfile

logger = logging.getLogger(__name__)

# Built-in model ID -> (strengths, input_media). More specific patterns first.
_BUILTIN_CAPABILITIES: dict[str, tuple[list[TaskType], set[Media]]] = {
    "claude": (
        [TaskType.CODE, TaskType.REASONING, TaskType.PLANNING, TaskType.GENERAL],
        {Media.TEXT},
    ),
    "gpt-4o-mini": ([TaskType.GENERAL, TaskType.CREATIVE, TaskType.TRANSLATION], {Media.TEXT}),
    "gpt-3.5": ([TaskType.GENERAL, TaskType.CREATIVE, TaskType.TRANSLATION], {Media.TEXT}),
    "gpt-4o": (
        [TaskType.GENERAL, TaskType.VISION, TaskType.CREATIVE, TaskType.TRANSLATION],
        {Media.TEXT, Media.IMAGE},
    ),
    "gpt-4": (
        [TaskType.GENERAL, TaskType.VISION, TaskType.CREATIVE, TaskType.TRANSLATION],
        {Media.TEXT, Media.IMAGE},
    ),
    "gemini": (
        [TaskType.VISION, TaskType.VIDEO, TaskType.GENERAL],
        {Media.TEXT, Media.IMAGE, Media.VIDEO},
    ),
}

# User-registered capabilities. Checked before built-in. Order: (pattern, strengths, input_media).
_USER_CAPABILITIES: list[tuple[str, list[TaskType], set[Media]]] = []


def register_model_capabilities(
    pattern: str,
    strengths: list[TaskType],
    *,
    input_media: set[Media] | None = None,
) -> None:
    """Register task strengths and input media for models whose ID contains pattern.

    Checked before built-in mappings. Use for DeepSeek, Mistral, Qwen, etc.

    Args:
        pattern: Substring to match in model_id (case-insensitive).
        strengths: Task types this model supports.
        input_media: Supported input media. Default {Media.TEXT}.

    Example:
        register_model_capabilities(
            "deepseek",
            [TaskType.CODE, TaskType.REASONING, TaskType.GENERAL],
        )
    """
    media = input_media if input_media is not None else {Media.TEXT}
    _USER_CAPABILITIES.append((pattern.lower(), list(strengths), set(media)))


def _model_id_from_model(m: Model) -> str:
    raw = getattr(m, "model_id", None) or getattr(m, "_model_id", "") or ""
    return (raw.split("/")[-1] if "/" in str(raw) else str(raw)).lower()


def _infer_strengths_and_media(model_id: str) -> tuple[list[TaskType], set[Media]]:
    """Infer task strengths and input media from model ID. Uses registry then built-in. Unknown -> GENERAL, TEXT."""
    mid = model_id.lower()
    for pattern, strengths, input_media in _USER_CAPABILITIES:
        if pattern in mid:
            return (list(strengths), set(input_media))
    for pattern, (strengths, input_media) in _BUILTIN_CAPABILITIES.items():
        if pattern in mid:
            return (list(strengths), set(input_media))
    return ([TaskType.GENERAL], {Media.TEXT})


def _profiles_from_models(
    models: list[Model],
    *,
    strengths: list[TaskType] | None = None,
) -> list[_RoutingProfile]:
    """Build routing profiles from a list of models. Internal use by ModelRouter.

    Each model gets a profile with name, strengths, input_media, etc. from Model
    routing fields when set, else auto-inferred.

    Args:
        models: List of Model instances.
        strengths: Task types each model supports. Overrides all when provided.

    Returns:
        List of internal routing profiles (one per model).

    """
    if not models:
        return []
    out: list[_RoutingProfile] = []
    seen: set[str] = set()
    for i, m in enumerate(models):
        name = (
            getattr(m, "profile_name", None)
            or getattr(m, "name", None)
            or getattr(m, "model_id", "")
        )
        if not name and hasattr(m, "_name"):
            name = getattr(m, "_name", "")
        if not name and hasattr(m, "_model_id"):
            raw = getattr(m, "_model_id", "")
            name = raw.split("/")[-1] if "/" in str(raw) else str(raw)
        if not name:
            name = f"model-{i}"
        base = name
        idx = 0
        while name in seen:
            idx += 1
            name = f"{base}-{idx}"
        seen.add(name)
        model_id = _model_id_from_model(m)
        inferred_strengths, inferred_input_media = _infer_strengths_and_media(model_id)
        # Use Model routing fields when set, else global strengths, else inferred
        m_strengths = getattr(m, "strengths", None)
        m_input = getattr(m, "input_media", None)
        m_output = getattr(m, "output_media", None)
        task_strengths = (
            list(m_strengths)
            if m_strengths is not None
            else list(strengths)
            if strengths is not None
            else inferred_strengths
        )
        task_input_media = (
            set(m_input)
            if m_input is not None
            else inferred_input_media
            if strengths is None
            else {Media.TEXT}
        )
        task_output_media = set(m_output) if m_output is not None else {Media.TEXT}
        task_priority = getattr(m, "priority", 100)
        task_supports_tools = getattr(m, "supports_tools", True)
        out.append(
            _RoutingProfile(
                model=m,
                name=name,
                strengths=task_strengths,
                input_media=task_input_media,
                output_media=task_output_media,
                supports_tools=task_supports_tools,
                priority=task_priority,
            )
        )
        if strengths is None:
            for p in out:
                logger.debug(
                    "Inferred profile for %s: strengths=%s, input_media=%s",
                    p.name,
                    [s.value for s in p.strengths],
                    [m.value for m in (p.input_media or set())],
                )
        if strengths is None and len(out) > 1:
            all_strengths = [frozenset(p.strengths) for p in out]
            if len(set(all_strengths)) == 1 and all_strengths[0] == {TaskType.GENERAL}:
                logger.warning(
                    "_profiles_from_models: All models have identical strengths (GENERAL). "
                    "Routing will not differentiate. Use Model routing fields (strengths=...) or pass strengths=[...]."
                )
    return out


def build_router_from_models(
    models: list[Model],
    *,
    routing_config: RoutingConfig | None = None,
    budget: Budget | None = None,
) -> ModelRouter:
    """Build a ModelRouter from a list of models and optional RoutingConfig.

    When routing_config is provided, its routing_mode, force_model, budget
    thresholds, etc. are applied. Otherwise defaults are used.

    Args:
        models: List of Model instances.
        routing_config: Optional RoutingConfig for routing behavior.
        budget: Optional Budget for cost-aware routing.

    Returns:
        ModelRouter ready for Agent use.
    """
    if routing_config is not None:
        if routing_config.router is not None:
            return routing_config.router
        return ModelRouter(
            models=models,
            routing_mode=routing_config.routing_mode,
            classifier=routing_config.classifier,
            budget=budget,
            budget_optimisation=routing_config.budget_optimisation,
            prefer_cheaper_below_budget_ratio=routing_config.prefer_cheaper_below_budget_ratio,
            force_cheapest_below_budget_ratio=routing_config.force_cheapest_below_budget_ratio,
            force_model=routing_config.force_model,
            routing_rule_callback=routing_config.routing_rule_callback,
        )
    return ModelRouter(models=models, budget=budget)
