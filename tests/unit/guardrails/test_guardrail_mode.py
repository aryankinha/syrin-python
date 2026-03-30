"""Tests for GuardrailMode.SYSTEM_PROMPT: enum values, mode field, system prompt instruction
generation, and the is_system_prompt_mode helper."""

from __future__ import annotations


class TestGuardrailModeEnum:
    def test_guardrail_mode_importable(self) -> None:
        from syrin.guardrails import GuardrailMode

        assert GuardrailMode is not None

    def test_evaluate_mode_exists(self) -> None:
        from syrin.guardrails import GuardrailMode

        assert hasattr(GuardrailMode, "EVALUATE")

    def test_system_prompt_mode_exists(self) -> None:
        from syrin.guardrails import GuardrailMode

        assert hasattr(GuardrailMode, "SYSTEM_PROMPT")

    def test_values_are_strings(self) -> None:
        from syrin.guardrails import GuardrailMode

        assert isinstance(GuardrailMode.EVALUATE.value, str)
        assert isinstance(GuardrailMode.SYSTEM_PROMPT.value, str)

    def test_evaluate_is_default(self) -> None:
        """EVALUATE is the mode used when none is specified."""
        from syrin.guardrails import Guardrail, GuardrailContext, GuardrailDecision, GuardrailMode

        class SimpleGuardrail(Guardrail):
            async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
                return GuardrailDecision(passed=True)

        g = SimpleGuardrail()
        assert g.mode == GuardrailMode.EVALUATE


class TestGuardrailModeField:
    def test_guardrail_accepts_mode_in_init(self) -> None:
        from syrin.guardrails import Guardrail, GuardrailContext, GuardrailDecision, GuardrailMode

        class ToneGuardrail(Guardrail):
            async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
                return GuardrailDecision(passed=True)

        g = ToneGuardrail(mode=GuardrailMode.SYSTEM_PROMPT)
        assert g.mode == GuardrailMode.SYSTEM_PROMPT

    def test_guardrail_mode_keyword_name(self) -> None:
        from syrin.guardrails import Guardrail, GuardrailContext, GuardrailDecision, GuardrailMode

        class ToneGuardrail(Guardrail):
            async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
                return GuardrailDecision(passed=True)

        g = ToneGuardrail(mode=GuardrailMode.SYSTEM_PROMPT)
        assert g.mode.value == "system_prompt"


class TestSystemPromptInstruction:
    def test_system_prompt_instruction_returns_string(self) -> None:
        from syrin.guardrails import Guardrail, GuardrailContext, GuardrailDecision, GuardrailMode

        class ToneGuardrail(Guardrail):
            async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
                return GuardrailDecision(passed=True)

            def system_prompt_instruction(self) -> str:
                return "Always respond in a professional tone."

        g = ToneGuardrail(mode=GuardrailMode.SYSTEM_PROMPT)
        assert g.system_prompt_instruction() == "Always respond in a professional tone."

    def test_default_system_prompt_instruction_is_empty(self) -> None:
        """Default implementation returns empty string (no instruction)."""
        from syrin.guardrails import Guardrail, GuardrailContext, GuardrailDecision

        class SimpleGuardrail(Guardrail):
            async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
                return GuardrailDecision(passed=True)

        g = SimpleGuardrail()
        assert g.system_prompt_instruction() == ""

    def test_is_system_prompt_mode_helper(self) -> None:
        from syrin.guardrails import Guardrail, GuardrailContext, GuardrailDecision, GuardrailMode

        class ToneGuardrail(Guardrail):
            async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
                return GuardrailDecision(passed=True)

        evaluate_g = ToneGuardrail()
        system_g = ToneGuardrail(mode=GuardrailMode.SYSTEM_PROMPT)
        assert evaluate_g.is_system_prompt_mode is False
        assert system_g.is_system_prompt_mode is True
