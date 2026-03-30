"""Guardrails system for input/output/action validation."""

from __future__ import annotations

# Import auth module
from syrin.guardrails.auth.capability import CapabilityIssuer, CapabilityToken
from syrin.guardrails.base import Guardrail

# Import built-in guardrails
from syrin.guardrails.built_in import (
    AuthorityCheck,
    BudgetEnforcer,
    CapabilityGuardrail,
    CitationGuardrail,
    ContentFilter,
    FactVerificationGuardrail,
    HumanApproval,
    LengthGuardrail,
    PIIScanner,
    ThresholdApproval,
)
from syrin.guardrails.chain import GuardrailChain
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision
from syrin.guardrails.engine import EvaluationResult, ParallelEvaluationEngine
from syrin.guardrails.enums import DecisionAction, GuardrailMode, GuardrailStage

# Import intelligence layer
from syrin.guardrails.intelligence import (
    AdaptiveThresholdGuardrail,
    AttackSimulator,
    ContextAwareGuardrail,
    EscalationDetector,
    FuzzingEngine,
    RedTeamEvaluator,
)
from syrin.guardrails.result import GuardrailCheckResult

# Public API: GuardrailResult = GuardrailCheckResult
GuardrailResult = GuardrailCheckResult

__all__ = [
    # Core classes
    "Guardrail",
    "GuardrailContext",
    "GuardrailDecision",
    "GuardrailChain",
    "ParallelEvaluationEngine",
    "EvaluationResult",
    # Enums
    "GuardrailMode",
    "GuardrailStage",
    "DecisionAction",
    # Built-in guardrails
    "CitationGuardrail",
    "ContentFilter",
    "FactVerificationGuardrail",
    "PIIScanner",
    # Authority layer
    "AuthorityCheck",
    "BudgetEnforcer",
    "ThresholdApproval",
    "HumanApproval",
    "CapabilityGuardrail",
    # Auth
    "CapabilityToken",
    "CapabilityIssuer",
    # Intelligence layer
    "ContextAwareGuardrail",
    "EscalationDetector",
    "AdaptiveThresholdGuardrail",
    "AttackSimulator",
    "RedTeamEvaluator",
    "FuzzingEngine",
    "LengthGuardrail",
    "GuardrailResult",
    "GuardrailCheckResult",
]
