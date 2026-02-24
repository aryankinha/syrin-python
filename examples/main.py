#!/usr/bin/env python
"""Syrin Examples - Run individual or all examples.

Usage:
    python examples/main.py                    # Run all examples
    python examples/main.py core               # Run core examples
    python examples/main.py core.basic_agent   # Run specific example
    python examples/main.py memory              # Run memory examples
    python examples/main.py multi_agent         # Run multi-agent examples
    python examples/main.py advanced            # Run advanced examples
"""

from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) < 2:
        print("Running all examples...")
        print("=" * 60)

        # Core examples
        print("\n### CORE EXAMPLES ###")
        from examples.core.agent_with_budget import example_agent_with_budget, example_shared_budget
        from examples.core.basic_agent import example_basic_agent
        from examples.core.prompt_decorator import example_prompt_decorator

        try:
            example_basic_agent()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_agent_with_budget()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_shared_budget()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_prompt_decorator()
        except Exception as e:
            print(f"Error: {e}")

        # Memory examples
        print("\n### MEMORY EXAMPLES ###")
        from examples.memory.basic_memory import example_basic_memory, example_memory_types

        try:
            example_basic_memory()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_memory_types()
        except Exception as e:
            print(f"Error: {e}")

        # Multi-agent examples
        print("\n### MULTI-AGENT EXAMPLES ###")
        from examples.multi_agent.handoff import example_handoff, example_handoff_with_context
        from examples.multi_agent.pipeline import (
            example_parallel_pipeline,
            example_pipeline_with_budget,
            example_sequential_pipeline,
        )
        from examples.multi_agent.team import example_team, example_team_selection

        try:
            example_handoff()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_handoff_with_context()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_sequential_pipeline()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_parallel_pipeline()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_pipeline_with_budget()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_team()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_team_selection()
        except Exception as e:
            print(f"Error: {e}")

        # Advanced examples
        print("\n### ADVANCED EXAMPLES ###")
        from examples.advanced.async_agent import (
            example_sync_response,
            example_sync_wrapper,
        )
        from examples.advanced.inheritance import example_inheritance

        try:
            example_inheritance()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_sync_response()
        except Exception as e:
            print(f"Error: {e}")

        try:
            example_sync_wrapper()
        except Exception as e:
            print(f"Error: {e}")

        print("\n" + "=" * 60)
        print("All examples completed!")

    else:
        module = sys.argv[1]

        if module == "core":
            from examples.core.agent_with_budget import (
                example_agent_with_budget,
                example_shared_budget,
            )
            from examples.core.basic_agent import example_basic_agent
            from examples.core.prompt_decorator import example_prompt_decorator

            example_basic_agent()
            example_agent_with_budget()
            example_shared_budget()
            example_prompt_decorator()

        elif module == "memory":
            from examples.memory.basic_memory import example_basic_memory, example_memory_types

            example_basic_memory()
            example_memory_types()

        elif module == "multi_agent":
            from examples.multi_agent.handoff import example_handoff, example_handoff_with_context
            from examples.multi_agent.pipeline import (
                example_parallel_pipeline,
                example_pipeline_with_budget,
                example_sequential_pipeline,
            )
            from examples.multi_agent.team import example_team, example_team_selection

            example_handoff()
            example_handoff_with_context()
            example_sequential_pipeline()
            example_parallel_pipeline()
            example_pipeline_with_budget()
            example_team()
            example_team_selection()

        elif module == "advanced":
            from examples.advanced.inheritance import example_inheritance

            example_inheritance()

        else:
            # Try to import and run specific module
            try:
                mod = __import__(f"examples.{module}", fromlist=[""])
                if hasattr(mod, "main"):
                    mod.main()
                else:
                    print(f"No main() function in examples.{module}")
            except ImportError as e:
                print(f"Unknown module: {module}")
                print(f"Error: {e}")


if __name__ == "__main__":
    main()
