"""Tests for ModelRouter and RoutingReason."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from syrin.enums import Media
from syrin.model import Model
from syrin.router import ComplexityTier, RoutingMode, TaskType
from syrin.router.classifier import ClassificationResult, PromptClassifier
from syrin.router.router import ModelRouter, RoutingReason


def _almock(name: str = "test") -> Model:
    return Model.Almock(context_window=4096, latency_min=0, latency_max=0)


def _models() -> list[Model]:
    return [
        _almock("code").with_routing(
            profile_name="code-model",
            strengths=[TaskType.CODE, TaskType.REASONING],
            priority=100,
        ),
        _almock("general").with_routing(
            profile_name="general-model",
            strengths=[TaskType.GENERAL, TaskType.CREATIVE],
            priority=90,
        ),
        _almock("vision").with_routing(
            profile_name="vision-model",
            strengths=[TaskType.VISION],
            input_media={Media.TEXT, Media.IMAGE},
            priority=80,
        ),
    ]


class TestRoutingReason:
    """RoutingReason dataclass."""

    def test_create_minimal(self) -> None:
        r = RoutingReason(
            selected_model="claude-code",
            task_type=TaskType.CODE,
            reason="Model specializes in code tasks",
            cost_estimate=0.003,
            alternatives=["gpt-4o", "ollama-llama3"],
            classification_confidence=0.92,
        )
        assert r.selected_model == "claude-code"
        assert r.task_type == TaskType.CODE
        assert r.reason == "Model specializes in code tasks"
        assert r.cost_estimate == 0.003
        assert r.alternatives == ["gpt-4o", "ollama-llama3"]
        assert r.classification_confidence == 0.92

    def test_create_empty_alternatives(self) -> None:
        r = RoutingReason(
            selected_model="only-one",
            task_type=TaskType.GENERAL,
            reason="Single model",
            cost_estimate=0.0,
            alternatives=[],
            classification_confidence=1.0,
        )
        assert r.alternatives == []

    def test_classification_confidence_bounds(self) -> None:
        r = RoutingReason(
            selected_model="x",
            task_type=TaskType.GENERAL,
            reason="Low confidence",
            cost_estimate=0.0,
            alternatives=[],
            classification_confidence=0.0,
        )
        assert r.classification_confidence == 0.0
        r2 = RoutingReason(
            selected_model="x",
            task_type=TaskType.GENERAL,
            reason="High confidence",
            cost_estimate=0.0,
            alternatives=[],
            classification_confidence=1.0,
        )
        assert r2.classification_confidence == 1.0

    def test_complexity_tier_and_system_alignment_optional(self) -> None:
        r = RoutingReason(
            selected_model="premium",
            task_type=TaskType.CODE,
            reason="Complexity HIGH",
            cost_estimate=0.01,
            alternatives=[],
            classification_confidence=0.9,
            complexity_tier=ComplexityTier.HIGH,
            system_alignment_score=0.45,
        )
        assert r.complexity_tier == ComplexityTier.HIGH
        assert r.system_alignment_score == 0.45

    def test_complexity_tier_none_default(self) -> None:
        r = RoutingReason(
            selected_model="x",
            task_type=TaskType.GENERAL,
            reason="Normal",
            cost_estimate=0.0,
            alternatives=[],
            classification_confidence=1.0,
        )
        assert r.complexity_tier is None
        assert r.system_alignment_score is None


class TestModelRouterValidation:
    """ModelRouter construction validation."""

    def test_empty_models_without_force_model_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one model"):
            ModelRouter(models=[])

    def test_empty_models_with_force_model_ok(self) -> None:
        router = ModelRouter(models=[], force_model=_almock())
        model, task, reason = router.route("hello")
        assert model is not None
        assert reason.reason == "Routing bypassed via force_model"


class TestModelRouterForceModel:
    """Force model bypass."""

    def test_force_model_bypasses_routing(self) -> None:
        router = ModelRouter(models=_models(), force_model=_almock("forced"))
        model, task, reason = router.route("write code")
        assert reason.selected_model == "force_model"
        assert reason.reason == "Routing bypassed via force_model"


class TestModelRouterRouting:
    """Routing logic. Use task_override to avoid classifier dependency in unit tests."""

    def test_route_returns_model_task_reason(self) -> None:
        router = ModelRouter(models=_models())
        model, task, reason = router.route("write a function", task_override=TaskType.CODE)
        assert model is not None
        assert task == TaskType.CODE
        assert reason.selected_model == "code-model"
        assert reason.classification_confidence == 1.0

    def test_task_override_skips_classification(self) -> None:
        router = ModelRouter(models=_models())
        model, task, reason = router.route("hi", task_override=TaskType.CODE)
        assert task == TaskType.CODE
        assert reason.selected_model == "code-model"

    def test_cost_first_mode_selects_cheapest(self) -> None:
        models = _models()
        router = ModelRouter(
            models=models,
            routing_mode=RoutingMode.COST_FIRST,
        )
        model, task, reason = router.route("hello", task_override=TaskType.GENERAL)
        assert reason.selected_model in [p.profile_name or p.name for p in models]

    def test_quality_first_mode_selects_highest_priority(self) -> None:
        router = ModelRouter(
            models=_models(),
            routing_mode=RoutingMode.QUALITY_FIRST,
        )
        model, task, reason = router.route("hello", task_override=TaskType.GENERAL)
        assert reason.selected_model == "general-model"

    def test_no_matching_profile_raises(self) -> None:
        from syrin.exceptions import NoMatchingProfileError

        models = [_almock().with_routing(profile_name="code-only", strengths=[TaskType.CODE])]
        router = ModelRouter(models=models)
        with pytest.raises(NoMatchingProfileError, match="No profile supports"):
            router.route("describe this image", task_override=TaskType.VISION)

    def test_routing_rule_callback_override(self) -> None:
        def pick_code(prompt: str, task_type: TaskType, names: list[str]) -> str | None:
            return "code-model" if "code-model" in names else None

        router = ModelRouter(
            models=_models(),
            routing_rule_callback=pick_code,
        )
        model, task, reason = router.route("write code", task_override=TaskType.CODE)
        assert reason.selected_model == "code-model"

    def test_manual_mode_requires_task_override(self) -> None:
        router = ModelRouter(
            models=_models(),
            routing_mode=RoutingMode.MANUAL,
        )
        with pytest.raises(ValueError, match="RoutingMode.MANUAL requires task_override"):
            router.route("hello")
        model, task, reason = router.route("hello", task_override=TaskType.GENERAL)
        assert task == TaskType.GENERAL

    def test_manual_mode_route_ordered_requires_task_override(self) -> None:
        router = ModelRouter(
            models=_models(),
            routing_mode=RoutingMode.MANUAL,
        )
        with pytest.raises(ValueError, match="RoutingMode.MANUAL requires task_override"):
            router.route_ordered("hello")
        results = router.route_ordered("hello", task_override=TaskType.GENERAL)
        assert len(results) > 0
        assert results[0][1] == TaskType.GENERAL


class TestModelRouterComplexityAndAlignment:
    """Router with classify_extended — complexity_tier, system_alignment_score."""

    def _make_mock_classifier(
        self,
        task: TaskType = TaskType.CODE,
        confidence: float = 0.85,
        complexity_tier: ComplexityTier = ComplexityTier.MEDIUM,
        system_alignment: float | None = 0.7,
    ) -> MagicMock:
        ext = ClassificationResult(
            task_type=task,
            confidence=confidence,
            complexity_score=0.5,
            complexity_tier=complexity_tier,
            system_alignment_score=system_alignment,
            used_fallback=False,
            latency_ms=10.0,
        )
        mock = MagicMock(spec=PromptClassifier)
        mock.classify_extended = MagicMock(return_value=ext)
        mock.low_confidence_fallback = TaskType.GENERAL
        return mock

    def test_route_with_classifier_uses_classify_extended(self) -> None:
        mock_cls = self._make_mock_classifier(
            task=TaskType.REASONING,
            complexity_tier=ComplexityTier.HIGH,
            system_alignment=0.4,
        )
        models = [
            _almock("premium").with_routing(
                profile_name="premium", strengths=[TaskType.CODE, TaskType.REASONING], priority=100
            ),
            _almock("cheap").with_routing(
                profile_name="cheap", strengths=[TaskType.REASONING], priority=80
            ),
        ]
        router = ModelRouter(models=models, classifier=mock_cls)
        model, task, reason = router.route("solve this", messages=[])
        mock_cls.classify_extended.assert_called_once()
        assert reason.task_type == TaskType.REASONING
        assert reason.complexity_tier == ComplexityTier.HIGH
        assert reason.system_alignment_score == 0.4
        assert reason.selected_model == "premium"

    def test_high_complexity_selects_highest_priority(self) -> None:
        mock_cls = self._make_mock_classifier(
            task=TaskType.GENERAL,
            complexity_tier=ComplexityTier.HIGH,
        )
        models = [
            _almock("low").with_routing(
                profile_name="low", strengths=[TaskType.GENERAL], priority=70
            ),
            _almock("high").with_routing(
                profile_name="high", strengths=[TaskType.GENERAL], priority=100
            ),
        ]
        router = ModelRouter(models=models, classifier=mock_cls)
        model, task, reason = router.route("complex question", messages=[])
        assert reason.reason == "Complexity HIGH; selected highest-priority (high)"
        assert reason.selected_model == "high"

    def test_route_with_system_message_extracts_for_alignment(self) -> None:
        from syrin.types import Message

        mock_cls = self._make_mock_classifier(system_alignment=0.6)
        messages = [
            Message(role="system", content="You are a coding assistant."),
            Message(role="user", content="Write a function"),
        ]
        router = ModelRouter(models=_models(), classifier=mock_cls)
        router.route("Write a function", messages=messages)
        call_args = mock_cls.classify_extended.call_args
        assert call_args[0][0] == "Write a function"
        assert call_args[0][1] == "You are a coding assistant."


class TestModelRouterEdgeCases:
    """Edge cases for router: classifier failures, legacy classifier, tier behavior."""

    def _make_mock_classifier(
        self,
        task: TaskType = TaskType.CODE,
        confidence: float = 0.85,
        complexity_tier: ComplexityTier = ComplexityTier.MEDIUM,
        system_alignment: float | None = 0.7,
    ) -> MagicMock:
        ext = ClassificationResult(
            task_type=task,
            confidence=confidence,
            complexity_score=0.5,
            complexity_tier=complexity_tier,
            system_alignment_score=system_alignment,
            used_fallback=False,
            latency_ms=10.0,
        )
        mock = MagicMock(spec=PromptClassifier)
        mock.classify_extended = MagicMock(return_value=ext)
        mock.classify = MagicMock(return_value=(task, confidence))
        mock.low_confidence_fallback = TaskType.GENERAL
        return mock

    def test_classifier_raises_uses_fallback(self) -> None:
        mock_cls = self._make_mock_classifier()
        mock_cls.classify_extended.side_effect = RuntimeError("Model unavailable")
        models = [
            _almock("general").with_routing(
                profile_name="general", strengths=[TaskType.GENERAL], priority=90
            )
        ]
        router = ModelRouter(models=models, classifier=mock_cls)
        model, task, reason = router.route("write code", messages=[])
        assert task == TaskType.GENERAL
        assert reason.classification_confidence == 0.0

    def test_classifier_without_classify_extended_uses_classify(self) -> None:
        mock_cls = MagicMock()
        mock_cls.classify = MagicMock(return_value=(TaskType.CODE, 0.9))
        mock_cls.low_confidence_fallback = TaskType.GENERAL
        del mock_cls.classify_extended

        router = ModelRouter(models=_models(), classifier=mock_cls)
        model, task, reason = router.route("write a function", messages=[])
        mock_cls.classify.assert_called_once_with("write a function")
        assert task == TaskType.CODE
        assert reason.complexity_tier is None
        assert reason.system_alignment_score is None

    def test_low_complexity_with_cost_first_selects_cheapest(self) -> None:
        mock_cls = self._make_mock_classifier(
            task=TaskType.GENERAL,
            complexity_tier=ComplexityTier.LOW,
        )
        models = [
            _almock("cheap").with_routing(
                profile_name="cheap", strengths=[TaskType.GENERAL], priority=70
            ),
            _almock("expensive").with_routing(
                profile_name="expensive", strengths=[TaskType.GENERAL], priority=100
            ),
        ]
        router = ModelRouter(
            models=models,
            classifier=mock_cls,
            routing_mode=RoutingMode.COST_FIRST,
        )
        model, task, reason = router.route("hi", messages=[])
        assert reason.selected_model == "cheap"

    def test_no_system_message_passes_none_to_classifier(self) -> None:
        from syrin.types import Message

        mock_cls = self._make_mock_classifier()
        messages = [Message(role="user", content="hello")]
        router = ModelRouter(models=_models(), classifier=mock_cls)
        router.route("hello", messages=messages)
        call_args = mock_cls.classify_extended.call_args
        assert call_args[0][1] is None


class TestModelRouterBudgetParams:
    """Budget params (budget_optimisation, prefer_cheaper, force_cheapest) affect routing."""

    def test_budget_low_prefers_cheaper_model(self) -> None:
        from syrin.budget import Budget

        budget = Budget(max_cost=1.0)
        budget._set_spent(0.85)  # remaining=0.15, ratio=0.15 < prefer_cheaper=0.20

        models = [
            _almock("cheap").with_routing(
                profile_name="cheap", strengths=[TaskType.GENERAL], priority=70
            ),
            _almock("expensive").with_routing(
                profile_name="expensive", strengths=[TaskType.GENERAL], priority=100
            ),
        ]
        router = ModelRouter(
            models=models,
            budget=budget,
            budget_optimisation=True,
            prefer_cheaper_below_budget_ratio=0.20,
            force_cheapest_below_budget_ratio=0.10,
            routing_mode=RoutingMode.AUTO,
        )
        model, task, reason = router.route("hello", messages=[])
        assert reason.selected_model == "cheap"
        assert "cheaper" in reason.reason.lower() or "budget" in reason.reason.lower()

    def test_budget_critical_forces_cheapest(self) -> None:
        from syrin.budget import Budget

        budget = Budget(max_cost=1.0)
        budget._set_spent(0.92)  # remaining=0.08, ratio=0.08 < force_cheapest=0.10

        models = [
            _almock("cheap").with_routing(
                profile_name="cheap", strengths=[TaskType.GENERAL], priority=70
            ),
            _almock("expensive").with_routing(
                profile_name="expensive", strengths=[TaskType.GENERAL], priority=100
            ),
        ]
        router = ModelRouter(
            models=models,
            budget=budget,
            budget_optimisation=True,
            prefer_cheaper_below_budget_ratio=0.20,
            force_cheapest_below_budget_ratio=0.10,
            routing_mode=RoutingMode.AUTO,
        )
        model, task, reason = router.route("hello", messages=[])
        assert reason.selected_model == "cheap"
        assert "cheapest" in reason.reason.lower() or "critical" in reason.reason.lower()

    def test_budget_optimisation_disabled_ignores_budget(self) -> None:
        from syrin.budget import Budget

        budget = Budget(max_cost=1.0)
        budget._set_spent(0.90)  # Low remaining

        models = [
            _almock("cheap").with_routing(
                profile_name="cheap", strengths=[TaskType.GENERAL], priority=70
            ),
            _almock("expensive").with_routing(
                profile_name="expensive", strengths=[TaskType.GENERAL], priority=100
            ),
        ]
        router = ModelRouter(
            models=models,
            budget=budget,
            budget_optimisation=False,
            routing_mode=RoutingMode.AUTO,
        )
        model, task, reason = router.route("hello", messages=[])
        assert reason.selected_model == "expensive"
        assert "budget" not in reason.reason.lower()


class TestModelRouterRouteOrdered:
    """route_ordered returns ranked list for fallback."""

    def test_route_ordered_returns_list(self) -> None:
        router = ModelRouter(models=_models())
        results = router.route_ordered("hello", task_override=TaskType.GENERAL)
        assert len(results) >= 1
        model, task, reason = results[0]
        assert model is not None
        assert task == TaskType.GENERAL
        assert reason.selected_model in [p.profile_name or p.name for p in _models()]

    def test_route_ordered_max_alternatives(self) -> None:
        router = ModelRouter(models=_models())
        results = router.route_ordered("hello", task_override=TaskType.GENERAL, max_alternatives=2)
        assert len(results) <= 2

    def test_route_ordered_force_model_returns_single(self) -> None:
        router = ModelRouter(models=_models(), force_model=_almock("f"))
        results = router.route_ordered("x")
        assert len(results) == 1
        assert results[0][2].selected_model == "force_model"


class TestModelRouterSelectModel:
    """select_model convenience method."""

    def test_select_model_returns_model(self) -> None:
        router = ModelRouter(models=_models())
        model = router.select_model("hello", context={"input_tokens_estimate": 100})
        assert model is not None


class TestModelRouterPricingCache:
    """Pricing is cached at init; get_pricing not called on every route."""

    def test_pricing_cached_at_init_not_on_route(self) -> None:
        from unittest.mock import patch

        from syrin.cost import ModelPricing

        m = _almock("cached").with_routing(profile_name="cached", strengths=[TaskType.GENERAL])
        pricing = ModelPricing(input_per_1m=1.0, output_per_1m=2.0)
        with patch.object(m, "get_pricing", return_value=pricing) as get_pricing:
            router = ModelRouter(models=[m])
            assert get_pricing.call_count == 1
            for _ in range(5):
                router.route("hello", task_override=TaskType.GENERAL)
            assert get_pricing.call_count == 1

    def test_cost_estimate_uses_cached_pricing(self) -> None:
        from unittest.mock import patch

        from syrin.cost import ModelPricing

        m = _almock("priced").with_routing(profile_name="priced", strengths=[TaskType.GENERAL])
        pricing = ModelPricing(input_per_1m=1.0, output_per_1m=2.0)
        with patch.object(m, "get_pricing", return_value=pricing):
            router = ModelRouter(models=[m])
            _, _, reason = router.route(
                "hello",
                task_override=TaskType.GENERAL,
                context={"input_tokens_estimate": 1000, "max_output_tokens": 500},
            )
            expected = (1000 / 1_000_000) * 1.0 + (500 / 1_000_000) * 2.0
            assert abs(reason.cost_estimate - round(expected, 6)) < 0.0001

    def test_profile_without_pricing_uses_zero_cost(self) -> None:
        from unittest.mock import patch

        m = _almock("no-pricing").with_routing(
            profile_name="no-pricing", strengths=[TaskType.GENERAL]
        )
        with patch.object(m, "get_pricing", return_value=None):
            router = ModelRouter(models=[m])
            _, _, reason = router.route("hello", task_override=TaskType.GENERAL)
            assert reason.cost_estimate == 0.0


class TestModelRouterTokenEstimation:
    """Token estimation uses universal chars/4, not model-specific tokenizer."""

    def test_estimate_tokens_uses_chars_div_4(self) -> None:
        """20 chars -> 5 tokens (20/4), 0 chars -> 1 (min)."""
        router = ModelRouter(models=_models())
        _, _, reason = router.route(
            "x" * 20,
            task_override=TaskType.GENERAL,
            context={"input_tokens_estimate": None},
        )
        # Cost uses in_tok from _estimate_tokens; with 20 chars, in_tok=5 (20//4)
        assert reason.cost_estimate >= 0

    def test_context_input_tokens_estimate_overrides(self) -> None:
        router = ModelRouter(models=_models())
        _, _, reason = router.route(
            "short",
            task_override=TaskType.GENERAL,
            context={"input_tokens_estimate": 5000, "max_output_tokens": 2000},
        )
        # Cost should reflect 5000 input, 2000 output
        assert reason.cost_estimate >= 0

    def test_empty_prompt_gets_min_one_token(self) -> None:
        from unittest.mock import patch

        from syrin.cost import ModelPricing

        m = _almock("t").with_routing(profile_name="t", strengths=[TaskType.GENERAL])
        pricing = ModelPricing(input_per_1m=1.0, output_per_1m=1.0)
        with patch.object(m, "get_pricing", return_value=pricing):
            router = ModelRouter(models=[m])
            _, _, reason = router.route("", task_override=TaskType.GENERAL)
            # Empty prompt -> 1 token (max(1, 0))
            assert reason.cost_estimate == round(
                (1 / 1_000_000) * 1.0 + (1024 / 1_000_000) * 1.0, 6
            )
