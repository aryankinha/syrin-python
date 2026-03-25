"""RoutingConfig — configuration for model selection and routing."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, Field, model_validator

from syrin.model import Model
from syrin.router.classifier import PromptClassifier
from syrin.router.enums import RoutingMode, TaskType

# Import last to avoid circular: ModelRouter imports classifier, profile, etc.
from syrin.router.router import ModelRouter


class RoutingConfig(BaseModel):  # type: ignore[explicit-any]
    """Configuration for model selection and routing. Use with Agent(model_router=...).

    Example::

        config = RoutingConfig(
            routing_mode=RoutingMode.COST_FIRST,
            budget_optimisation=True,
            prefer_cheaper_below_budget_ratio=0.20,
        )
        agent = Agent(model=[claude, gpt], model_router=config)

    Attributes:
        router: Explicit ModelRouter. If set, overrides auto-created router from model list.
        classifier: Custom PromptClassifier. None = use default (embeddings).
        routing_mode: AUTO, COST_FIRST, QUALITY_FIRST, or MANUAL.
        force_model: Bypass routing; always use this model.
        budget_optimisation: When True, prefer cheaper models when budget runs low.
        prefer_cheaper_below_budget_ratio: When remaining/limit < this, prefer cheaper capable models.
        force_cheapest_below_budget_ratio: When remaining/limit < this, force cheapest capable model.
        routing_rule_callback: Custom callback(prompt, task_type, profile_names) -> profile_name | None.
    """

    model_config = {"arbitrary_types_allowed": True}

    router: ModelRouter | None = Field(
        default=None,
        description="Explicit ModelRouter. Overrides auto-created router from model list.",
    )
    classifier: PromptClassifier | None = Field(
        default=None,
        description="Custom PromptClassifier. None = default embeddings-based.",
    )
    routing_mode: RoutingMode = Field(
        default=RoutingMode.AUTO,
        description="AUTO, COST_FIRST, QUALITY_FIRST, or MANUAL.",
    )
    force_model: Model | None = Field(
        default=None,
        description="Bypass routing; always use this model.",
    )
    budget_optimisation: bool = Field(
        default=True,
        description="When True, prefer cheaper models when budget runs low.",
    )
    prefer_cheaper_below_budget_ratio: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction (0–1) of remaining budget. When remaining/limit < this, "
            "router prefers cheaper capable models. Default 0.20."
        ),
    )
    force_cheapest_below_budget_ratio: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction (0–1) of remaining budget. When remaining/limit < this, "
            "router forces cheapest capable model. Default 0.10. Must be <= prefer_cheaper_below_budget_ratio."
        ),
    )
    routing_rule_callback: Callable[[str, TaskType, list[str]], str | None] | None = Field(
        default=None,
        description="Callback(prompt, task_type, profile_names) -> preferred profile name or None.",
    )

    @model_validator(mode="after")
    def _warn_ignored_when_router_set(self) -> RoutingConfig:
        import warnings

        if self.router is not None:
            ignored = []
            if self.routing_mode != RoutingMode.AUTO:
                ignored.append("routing_mode")
            if self.classifier is not None:
                ignored.append("classifier")
            if ignored:
                warnings.warn(
                    f"RoutingConfig.router is set — {', '.join(ignored)} will be ignored. "
                    "Configure these on the ModelRouter directly.",
                    stacklevel=2,
                )
        return self

    @model_validator(mode="after")
    def _validate_cheapest_le_prefer(self) -> RoutingConfig:
        if self.force_cheapest_below_budget_ratio > self.prefer_cheaper_below_budget_ratio:
            raise ValueError(
                f"force_cheapest_below_budget_ratio ({self.force_cheapest_below_budget_ratio}) "
                f"must be <= prefer_cheaper_below_budget_ratio ({self.prefer_cheaper_below_budget_ratio})."
            )
        return self


# Resolve forward refs (Model, ModelRouter, etc.) after all types are imported
RoutingConfig.model_rebuild()
