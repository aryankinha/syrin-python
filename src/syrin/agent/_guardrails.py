"""Guardrails use case: run guardrails on input/output text.

Agent delegates to run_guardrails. Public API stays on Agent.
"""

from __future__ import annotations

from typing import Any

from syrin.enums import GuardrailStage, Hook
from syrin.events import EventContext
from syrin.guardrails import GuardrailChain, GuardrailResult
from syrin.observability import SemanticAttributes, SpanKind, SpanStatus


def run_guardrails(agent: Any, text: str, stage: GuardrailStage) -> GuardrailResult:
    """Run guardrails on text. Excludes remotely disabled guardrails."""
    disabled = getattr(agent, "_guardrails_disabled", set()) or set()
    guardrail_list = getattr(agent._guardrails, "_guardrails", [])
    effective = [g for g in guardrail_list if g.name not in disabled]
    if len(effective) == 0:
        return GuardrailResult(passed=True)
    effective_chain = GuardrailChain(effective)

    agent._emit_event(
        Hook.GUARDRAIL_INPUT if stage == GuardrailStage.INPUT else Hook.GUARDRAIL_OUTPUT,
        EventContext(
            text=text[:200],
            stage=stage.value,
            guardrail_count=len(effective_chain),
        ),
    )

    metadata: dict[str, object] = {}
    runtime = getattr(agent, "_runtime", None)
    if runtime is not None and getattr(runtime, "grounded_facts", None):
        metadata["grounded_facts"] = list(runtime.grounded_facts)

    tracer = agent._tracer
    with tracer.span(
        f"guardrails.{stage.value}",
        kind=SpanKind.GUARDRAIL,
        attributes={SemanticAttributes.GUARDRAIL_STAGE: stage.value},
    ) as guardrail_span:
        result = effective_chain.check(
            text, stage, budget=agent._budget, agent=agent, metadata=metadata or None
        )

        guardrail_span.set_attribute(SemanticAttributes.GUARDRAIL_PASSED, result.passed)

        if not result.passed:
            guardrail_span.set_attribute(
                SemanticAttributes.GUARDRAIL_VIOLATION, result.reason or "Unknown"
            )
            guardrail_span.set_status(SpanStatus.ERROR, result.reason)

            agent._emit_event(
                Hook.GUARDRAIL_BLOCKED,
                EventContext(
                    stage=stage.value,
                    reason=result.reason,
                    guardrail_names=[g.name for g in effective],
                ),
            )

            guardrail_names = [g.name for g in effective]
            if stage == GuardrailStage.INPUT:
                agent._run_report.guardrail.input_passed = False
                agent._run_report.guardrail.input_reason = result.reason
                agent._run_report.guardrail.input_guardrails = guardrail_names
                agent._run_report.guardrail.blocked = True
                agent._run_report.guardrail.blocked_stage = stage.value
            else:
                agent._run_report.guardrail.output_passed = False
                agent._run_report.guardrail.output_reason = result.reason
                agent._run_report.guardrail.output_guardrails = guardrail_names
                agent._run_report.guardrail.blocked = True
                agent._run_report.guardrail.blocked_stage = stage.value
        else:
            guardrail_names = [g.name for g in effective]
            if stage == GuardrailStage.INPUT:
                agent._run_report.guardrail.input_passed = True
                agent._run_report.guardrail.input_guardrails = guardrail_names
            else:
                agent._run_report.guardrail.output_passed = True
                agent._run_report.guardrail.output_guardrails = guardrail_names

        return result
