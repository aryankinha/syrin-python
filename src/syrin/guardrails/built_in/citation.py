"""Citation guardrail — ensures factual statements have source citations."""

from __future__ import annotations

import re

from syrin.enums import DecisionAction
from syrin.guardrails.base import Guardrail
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision


class CitationGuardrail(Guardrail):
    """Guardrail that ensures factual statements in output have citations.

    Checks for citation markers (e.g. [Source: ..., [1], (page X)).
    Use with grounding-enabled knowledge for regulated/financial domains.

    Example:
        >>> guardrail = CitationGuardrail(
        ...     require_source=True,
        ...     require_page=False,
        ...     missing_marker="[UNVERIFIED]",
        ... )
        >>> result = await guardrail.evaluate(context)
    """

    _CITATION_PATTERNS = [
        r"\[Source:",
        r"\[source:",
        r"\(Source:",
        r"\(source:",
        r"\[1\]",
        r"\[\d+\]",
        r"\(p\.\s*\d+\)",
        r"\(page\s+\d+\)",
        r"\[.*?,\s*[Pp]age\s+\d+\]",
    ]

    def __init__(
        self,
        require_source: bool = True,
        require_page: bool = False,
        missing_marker: str = "[UNVERIFIED]",
        action: DecisionAction = DecisionAction.FLAG,
        name: str | None = None,
    ) -> None:
        """Initialize citation guardrail.

        Args:
            require_source: If True, factual-looking sentences need a citation.
            require_page: If True, require page number in citation (stricter).
            missing_marker: Marker to suggest for uncited facts.
            action: FLAG to annotate without blocking, BLOCK to reject.
            name: Optional custom name.
        """
        super().__init__(name)
        self.require_source = require_source
        self.require_page = require_page
        self.missing_marker = missing_marker
        self.action = action

    def _has_citation(self, text: str) -> bool:
        """Check if text contains a citation marker."""
        return any(re.search(pat, text, re.IGNORECASE) for pat in self._CITATION_PATTERNS)

    def _has_page_in_citation(self, text: str) -> bool:
        """Check if text contains page number in citation."""
        return bool(re.search(r"page\s+\d+|p\.\s*\d+|\[\d+\]", text, re.IGNORECASE))

    async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        """Check that factual statements have citations.

        Splits output into paragraphs; for paragraphs that look factual
        (contain numbers, percentages), requires citation markers.

        Args:
            context: Guardrail context with text (output).

        Returns:
            GuardrailDecision indicating if citations are present.
        """
        if not self.require_source:
            return GuardrailDecision(
                passed=True,
                rule="citation_check",
                metadata={"require_source": False},
            )

        text = context.text
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        uncited: list[str] = []
        for para in paragraphs:
            if len(para) < 30:
                continue
            if not re.search(r"\d|%|₹|\$|€|£|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", para):
                continue
            if self._has_citation(para):
                if self.require_page and not self._has_page_in_citation(para):
                    uncited.append(para[:60] + "...")
                continue
            uncited.append(para[:60] + ("..." if len(para) > 60 else ""))

        if uncited:
            return GuardrailDecision(
                passed=False,
                rule="missing_citation",
                reason=f"Factual statements without citations: {len(uncited)} paragraph(s). "
                f"Use {self.missing_marker} for uncited facts or add [Source: doc, Page N].",
                confidence=0.9,
                action=self.action,
                metadata={"uncited_count": len(uncited), "missing_marker": self.missing_marker},
                alternatives=[
                    "Add citations: [Source: document.pdf, Page N]",
                    f"Mark uncited: {self.missing_marker}",
                ],
            )
        return GuardrailDecision(
            passed=True,
            rule="citation_check",
            metadata={"require_source": True, "require_page": self.require_page},
        )
