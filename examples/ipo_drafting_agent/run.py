#!/usr/bin/env python
"""IPO DRHP Drafting Agent - Run Script

This script demonstrates how to use the IPO DRHP Agent to draft the
Capital Structure section of a Draft Red Herring Prospectus.

Requirements:
    pip install syrin[openai]

Usage:
    python examples/ipo_drafting_agent/run.py

Environment Variables:
    OPENAI_API_KEY: Your OpenAI API key (or set in .env file)
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file before checking for API key
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


def main() -> None:
    """Main entry point."""

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        print("Please set your OpenAI API key:")
        print("  - Edit examples/ipo_drafting_agent/.env")
        print("  - Or export OPENAI_API_KEY=your_api_key")
        sys.exit(1)

    # Import after path setup
    from examples.ipo_drafting_agent.ipo_agent.agent import create_agent

    # Create agent
    print("Creating DRHP agent with Knowledge, Grounding, Budget, and Guardrails...")
    agent = create_agent()
    print(f"  - Agent: {agent.name}")
    if agent._budget:
        print(f"  - Budget: ${agent._budget.max_cost}")
    print(f"  - Guardrails: {len(agent._guardrails)}")
    print()

    # Run the agent
    print("Running agent to draft Capital Structure section...")
    print("-" * 50)

    prompt = "Draft the Capital Structure and Shareholding Pattern section for the DRHP."

    result = agent.run(prompt)

    print("-" * 50)
    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)

    if result.structured:
        print("\n### DRAFT SECTION ###")
        print(result.structured.parsed.draft_section)

        print("\n### SOURCES USED ###")
        for src in result.structured.parsed.sources_used:
            print(f"  - {src}")

        print("\n### AUTO-EXTRACTED PARTS ###")
        for part in result.structured.parsed.auto_extracted_parts:
            print(f"  - {part}")

        print("\n### REQUIRES REVIEW ###")
        for item in result.structured.parsed.requires_review:
            print(f"  - {item}")

    print("\n" + "=" * 70)
    print("METRICS")
    print("=" * 70)
    print(f"Cost: ${result.cost:.4f}")

    grounded_facts = getattr(agent._runtime, "grounded_facts", None)
    if grounded_facts:
        print(f"Grounded Facts: {len(grounded_facts)}")
        verified = sum(1 for f in grounded_facts if f.verification.value == "VERIFIED")
        contradicted = sum(1 for f in grounded_facts if f.verification.value == "CONTRADICTED")
        not_found = sum(1 for f in grounded_facts if f.verification.value == "NOT_FOUND")
        unverified = sum(1 for f in grounded_facts if f.verification.value == "UNVERIFIED")
        print(f"  - Verified:   {verified}")
        print(f"  - Contradicted: {contradicted}")
        print(f"  - Not Found:  {not_found}")
        print(f"  - Unverified: {unverified}")

        # Save intermediate JSON
        import json

        def shorten_path(p: str) -> str:
            """Shorten path to be more readable."""
            if "examples/ipo_drafting_agent/data/" in p:
                return p.split("examples/ipo_drafting_agent/data/")[-1]
            return p

        intermediate = {
            "prompt": prompt,
            "draft_section": result.structured.parsed.draft_section if result.structured else "",
            "sources_used": [
                shorten_path(s)
                for s in (result.structured.parsed.sources_used if result.structured else [])
            ],
            "auto_extracted_parts": result.structured.parsed.auto_extracted_parts
            if result.structured
            else [],
            "requires_review": result.structured.parsed.requires_review
            if result.structured
            else [],
            "grounded_facts": [
                {
                    "content": f.content[:500] + "..." if len(f.content) > 500 else f.content,
                    "source": shorten_path(f.source) if f.source else "",
                    "confidence": round(f.confidence, 3),
                    "verification": f.verification.value,
                }
                for f in grounded_facts
            ],
            "metrics": {
                "cost": round(result.cost, 4),
                "total_facts": len(grounded_facts),
                "verified": verified,
                "contradicted": contradicted,
                "not_found": not_found,
                "unverified": unverified,
            },
        }

        output_path = Path(__file__).parent / "output_intermediate.json"
        output_path.write_text(json.dumps(intermediate, indent=2))
        print(f"\nIntermediate output saved to: {output_path}")

    if agent._budget:
        print(f"\nBudget Spent: ${agent._budget._spent:.4f}")
        print(f"Budget Remaining: ${agent._budget.remaining:.4f}")


if __name__ == "__main__":
    main()
