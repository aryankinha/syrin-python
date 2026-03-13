"""Tests for agent runtime grounded_facts and report.grounding (Step 2)."""

from __future__ import annotations

from syrin.agent._helpers import _AgentRuntime
from syrin.enums import VerificationStatus
from syrin.knowledge._grounding import GroundedFact
from syrin.response import AgentReport, GroundingReport


class TestAgentRuntimeGroundedFacts:
    """_AgentRuntime.grounded_facts (2A)."""

    def test_runtime_has_grounded_facts_list(self) -> None:
        rt = _AgentRuntime()
        assert hasattr(rt, "grounded_facts")
        assert isinstance(rt.grounded_facts, list)
        assert len(rt.grounded_facts) == 0

    def test_grounded_facts_extend_and_clear(self) -> None:
        rt = _AgentRuntime()
        f = GroundedFact(content="Fact", source="doc.pdf", verification=VerificationStatus.VERIFIED)
        rt.grounded_facts.append(f)
        assert len(rt.grounded_facts) == 1
        assert rt.grounded_facts[0].content == "Fact"
        rt.grounded_facts.clear()
        assert len(rt.grounded_facts) == 0


class TestGroundingReport:
    """GroundingReport and AgentReport.grounding (2C)."""

    def test_agent_report_has_grounding_field(self) -> None:
        report = AgentReport()
        assert hasattr(report, "grounding")
        assert report.grounding is None

    def test_grounding_report_dataclass(self) -> None:
        gr = GroundingReport(verified_count=3, total_facts=5, sources=["a.pdf", "b.pdf"])
        assert gr.verified_count == 3
        assert gr.total_facts == 5
        assert gr.sources == ["a.pdf", "b.pdf"]
