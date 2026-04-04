"""CONSENSUS topology — multi-agent majority vote for high-stakes decisions.

In the CONSENSUS topology, multiple independent agents evaluate the same
question and cast votes. The swarm reaches a decision when a configurable
fraction of agents agree on the same answer.

Use this topology when:
  - A single-model answer carries unacceptable risk (legal, medical, compliance).
  - You want built-in redundancy against model hallucination or bias.
  - Decisions need an auditable evidence trail (each vote is recorded).

Key concepts:
  - ConsensusConfig(min_agreement=0.67, strategy=ConsensusStrategy.MAJORITY)
  - SwarmConfig(topology=SwarmTopology.CONSENSUS)
  - SwarmResult.consensus_result — agreement_fraction, consensus_reached, votes

Requires:
    OPENAI_API_KEY — set in your environment before running.

Run:
    OPENAI_API_KEY=sk-... uv run python examples/07_multi_agent/swarm_consensus.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from syrin import Agent, Budget, Model
from syrin.enums import ConsensusStrategy, SwarmTopology
from syrin.swarm import ConsensusConfig, Swarm, SwarmConfig

if not os.environ.get("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY is not set. This example requires a real API key.")
    sys.exit(1)

_MODEL = Model.OpenAI("gpt-4o-mini")


# ── Example 1: Legal clause interpretation — three independent analysts ────────
#
# High-stakes contract review: three agents with distinct jurisdictional
# expertise independently interpret the same clause. Majority agreement
# (≥2/3) is required before the swarm returns a verdict.

CLAUSE = (
    "Clause 14.3 — Limitation of Liability: "
    "In no event shall either party be liable for consequential, incidental, "
    "or indirect damages arising from the use of the software, regardless of "
    "whether the party had been advised of the possibility of such damages."
)


class USContractsCounsel(Agent):
    """Senior US software contracts attorney with SaaS specialisation."""

    model = _MODEL
    system_prompt = (
        "You are a senior US software contracts attorney specialising in SaaS agreements. "
        "When given a contract clause, provide a one-sentence enforceability assessment "
        "under US law and state your verdict as exactly one of: "
        "'ENFORCEABLE', 'UNENFORCEABLE', or 'JURISDICTION-DEPENDENT'. "
        "End your response with your verdict on its own line."
    )


class EUTechnologyCounsel(Agent):
    """EU technology law specialist with GDPR and B2B SaaS experience."""

    model = _MODEL
    system_prompt = (
        "You are an EU technology law specialist with deep GDPR and SaaS contract expertise. "
        "When given a contract clause, provide a one-sentence enforceability assessment "
        "under EU law and state your verdict as exactly one of: "
        "'ENFORCEABLE', 'UNENFORCEABLE', or 'JURISDICTION-DEPENDENT'. "
        "End your response with your verdict on its own line."
    )


class CommonwealthLegalAdvisor(Agent):
    """Commonwealth jurisdiction counsel (UK, Australia, Canada)."""

    model = _MODEL
    system_prompt = (
        "You are a senior commercial solicitor practising across Commonwealth jurisdictions "
        "(UK, Australia, and Canada). When given a contract clause, provide a one-sentence "
        "enforceability assessment and state your verdict as exactly one of: "
        "'ENFORCEABLE', 'UNENFORCEABLE', or 'JURISDICTION-DEPENDENT'. "
        "End your response with your verdict on its own line."
    )


async def example_legal_consensus() -> None:
    print("\n── Example 1: Legal clause interpretation — three jurisdictions ──")
    print(f"\nClause under review:\n  {CLAUSE}\n")

    swarm = Swarm(
        agents=[USContractsCounsel(), EUTechnologyCounsel(), CommonwealthLegalAdvisor()],
        goal=CLAUSE,
        config=SwarmConfig(topology=SwarmTopology.CONSENSUS),
        consensus_config=ConsensusConfig(
            min_agreement=0.67,
            strategy=ConsensusStrategy.MAJORITY,
        ),
        budget=Budget(
            max_cost=0.10,
        ),
    )
    result = await swarm.run()

    print(result.content)
    if result.budget_report:
        print(f"\nTotal spent: ${result.budget_report.total_spent:.4f}")


# ── Example 2: Security assessment — unanimous agreement required ──────────────
#
# For security decisions that carry operational risk, require all agents to
# agree before the swarm returns a verdict. min_agreement=1.0 enforces
# unanimous consensus.

SECURITY_PROMPT = (
    "Assess the following infrastructure change for production deployment risk:\n"
    "Proposed change: disable TLS certificate pinning on the mobile SDK to reduce "
    "app-store rejection friction. The SDK communicates with a financial data API "
    "that handles personal account information."
)


class ApplicationSecurityEngineer(Agent):
    """Assesses application-layer and API security risks."""

    model = _MODEL
    system_prompt = (
        "You are a senior application security engineer with expertise in mobile "
        "and API security. Assess the given infrastructure change for security risk. "
        "Provide a 2-3 sentence technical assessment and end with your verdict on "
        "its own line: exactly 'APPROVE', 'REJECT', or 'CONDITIONAL'."
    )


class CloudSecurityArchitect(Agent):
    """Evaluates cloud and infrastructure security posture."""

    model = _MODEL
    system_prompt = (
        "You are a cloud security architect responsible for infrastructure risk. "
        "Assess the given infrastructure change from a threat modelling perspective. "
        "Provide a 2-3 sentence assessment of the attack surface impact and end with "
        "your verdict on its own line: exactly 'APPROVE', 'REJECT', or 'CONDITIONAL'."
    )


class ComplianceOfficer(Agent):
    """Reviews changes for regulatory compliance (SOC 2, PCI-DSS, GDPR)."""

    model = _MODEL
    system_prompt = (
        "You are a compliance officer responsible for SOC 2, PCI-DSS, and GDPR adherence. "
        "Assess the given infrastructure change for regulatory compliance risk. "
        "Identify the specific control category at risk and end with your verdict on "
        "its own line: exactly 'APPROVE', 'REJECT', or 'CONDITIONAL'."
    )


async def example_security_consensus() -> None:
    print("\n── Example 2: Security change approval — unanimous required ─────")
    print(f"\nProposed change:\n  {SECURITY_PROMPT[:120]}...\n")

    swarm = Swarm(
        agents=[
            ApplicationSecurityEngineer(),
            CloudSecurityArchitect(),
            ComplianceOfficer(),
        ],
        goal=SECURITY_PROMPT,
        config=SwarmConfig(topology=SwarmTopology.CONSENSUS),
        consensus_config=ConsensusConfig(
            min_agreement=1.0,  # All three must agree for approval
            strategy=ConsensusStrategy.MAJORITY,
        ),
        budget=Budget(
            max_cost=0.10,
        ),
    )
    result = await swarm.run()

    print(result.content)
    if result.budget_report:
        print(f"\nTotal spent: ${result.budget_report.total_spent:.4f}")


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    await example_legal_consensus()
    await example_security_consensus()
    print("\nAll consensus swarm examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
