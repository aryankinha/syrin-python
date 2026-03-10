"""Tests for RoutingConfig — routing configuration."""

from __future__ import annotations

import pytest

from syrin.router import RoutingMode, TaskType
from syrin.router.config import RoutingConfig


def _dummy_callback(prompt: str, task_type: TaskType, profiles: list[str]) -> str | None:
    return None


class TestRoutingConfigValid:
    """Valid RoutingConfig construction."""

    def test_minimal_config(self) -> None:
        cfg = RoutingConfig()
        assert cfg.router is None
        assert cfg.classifier is None
        assert cfg.routing_mode == RoutingMode.AUTO
        assert cfg.force_model is None
        assert cfg.budget_optimisation is True
        assert cfg.prefer_cheaper_below_budget_ratio == 0.20
        assert cfg.force_cheapest_below_budget_ratio == 0.10
        assert cfg.routing_rule_callback is None

    def test_with_routing_mode(self) -> None:
        cfg = RoutingConfig(routing_mode=RoutingMode.COST_FIRST)
        assert cfg.routing_mode == RoutingMode.COST_FIRST

    def test_with_budget_thresholds(self) -> None:
        cfg = RoutingConfig(
            prefer_cheaper_below_budget_ratio=0.25,
            force_cheapest_below_budget_ratio=0.05,
        )
        assert cfg.prefer_cheaper_below_budget_ratio == 0.25
        assert cfg.force_cheapest_below_budget_ratio == 0.05

    def test_thresholds_at_boundary(self) -> None:
        cfg = RoutingConfig(
            prefer_cheaper_below_budget_ratio=0.5,
            force_cheapest_below_budget_ratio=0.5,
        )
        assert cfg.prefer_cheaper_below_budget_ratio == 0.5
        assert cfg.force_cheapest_below_budget_ratio == 0.5

    def test_budget_optimisation_disabled(self) -> None:
        cfg = RoutingConfig(budget_optimisation=False)
        assert cfg.budget_optimisation is False

    def test_routing_rule_callback(self) -> None:
        cfg = RoutingConfig(routing_rule_callback=_dummy_callback)
        assert cfg.routing_rule_callback is _dummy_callback

    def test_with_explicit_router(self) -> None:
        from syrin.router import ModelRouter
        from syrin.router.defaults import get_default_profiles

        models = list(get_default_profiles().values())
        router = ModelRouter(models=models)
        cfg = RoutingConfig(router=router)
        assert cfg.router is router

    def test_with_force_model(self) -> None:
        from syrin.model import Model

        m = Model.Almock()
        cfg = RoutingConfig(force_model=m)
        assert cfg.force_model is m


class TestRoutingConfigValidation:
    """RoutingConfig validation."""

    def test_prefer_cheaper_below_budget_ratio_out_of_range_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RoutingConfig(prefer_cheaper_below_budget_ratio=1.5)
        with pytest.raises(ValidationError):
            RoutingConfig(prefer_cheaper_below_budget_ratio=-0.1)

    def test_force_cheapest_below_budget_ratio_out_of_range_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RoutingConfig(force_cheapest_below_budget_ratio=2.0)
        with pytest.raises(ValidationError):
            RoutingConfig(force_cheapest_below_budget_ratio=-0.01)

    def test_force_cheapest_gt_prefer_raises(self) -> None:
        with pytest.raises(
            ValueError, match="force_cheapest_below_budget_ratio.*<=.*prefer_cheaper"
        ):
            RoutingConfig(
                prefer_cheaper_below_budget_ratio=0.10,
                force_cheapest_below_budget_ratio=0.20,
            )
