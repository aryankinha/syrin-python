"""Sandbox Execution Example.

Demonstrates:
- Executing code in a sandboxed environment
- Different sandbox runtimes (local, subprocess)
- Handling execution results
- Using sandbox for safe code execution

Run: python -m examples.advanced.sandbox
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from syrin.sandbox import (
    LocalSandbox,
    SubprocessSandbox,
    get_sandbox,
)

from syrin import Agent, Model
from syrin.enums import SandboxRuntime

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


def example_local_sandbox() -> None:
    """Using local sandbox for code execution."""
    print("\n" + "=" * 50)
    print("Local Sandbox Example")
    print("=" * 50)

    sandbox = LocalSandbox()

    # Execute simple Python code
    code = """
result = 2 + 2
print(f'Result: {result}')
"""

    result = sandbox.execute(code)
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    print(f"Duration: {result.duration:.4f}s")


def example_subprocess_sandbox() -> None:
    """Using subprocess sandbox for code execution."""
    print("\n" + "=" * 50)
    print("Subprocess Sandbox Example")
    print("=" * 50)

    sandbox = SubprocessSandbox()

    # Execute Python code
    code = """
import json
data = {'name': 'test', 'values': [1, 2, 3]}
print(json.dumps(data))
"""

    result = sandbox.execute(code, timeout=5.0)
    print(f"Success: {result.success}")
    print(f"Output: {result.output.strip()}")
    print(f"Duration: {result.duration:.4f}s")


def example_sandbox_error_handling() -> None:
    """Handling sandbox errors."""
    print("\n" + "=" * 50)
    print("Sandbox Error Handling")
    print("=" * 50)

    sandbox = LocalSandbox()

    # Code with error
    bad_code = """
x = 1 / 0  # Division by zero
"""

    result = sandbox.execute(bad_code)
    print(f"Success: {result.success}")
    print(f"Error: {result.error}")
    print(f"Output: '{result.output}'")


def example_sandbox_with_timeout() -> None:
    """Testing timeout behavior."""
    print("\n" + "=" * 50)
    print("Sandbox Timeout Example")
    print("=" * 50)

    sandbox = SubprocessSandbox()

    # Code that takes too long
    slow_code = """
import time
time.sleep(5)
print('Done')
"""

    result = sandbox.execute(slow_code, timeout=1.0)
    print(f"Success: {result.success}")
    print(f"Error: {result.error}")
    print(f"Duration: {result.duration:.4f}s")


def example_sandbox_execute_file() -> None:
    """Executing a file in sandbox."""
    print("\n" + "=" * 50)
    print("Sandbox Execute File")
    print("=" * 50)

    sandbox = SubprocessSandbox()

    # Create a temp file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("""
import sys
print(f"Python version: {sys.version}")
print("File executed successfully")
""")
        temp_path = f.name

    result = sandbox.execute_file(temp_path, timeout=5.0)
    print(f"Success: {result.success}")
    print(f"Output: {result.output.strip()}")

    # Clean up
    import os

    os.unlink(temp_path)


def example_get_sandbox() -> None:
    """Using get_sandbox factory function."""
    print("\n" + "=" * 50)
    print("Get Sandbox Factory")
    print("=" * 50)

    # Get local sandbox
    local = get_sandbox(SandboxRuntime.LOCAL)
    print(f"Local sandbox: {type(local).__name__}")

    # Get subprocess sandbox
    subprocess = get_sandbox(SandboxRuntime.SUBPROCESS)
    print(f"Subprocess sandbox: {type(subprocess).__name__}")

    # Execute with each
    code = "print('Hello from sandbox')"

    result1 = local.execute(code)
    print(f"Local result: {result1.output.strip()}")

    result2 = subprocess.execute(code)
    print(f"Subprocess result: {result2.output.strip()}")


def example_sandbox_result() -> None:
    """Working with SandboxResult."""
    print("\n" + "=" * 50)
    print("Sandbox Result Properties")
    print("=" * 50)

    sandbox = LocalSandbox()

    code = """
output = "computed value"
"""

    result = sandbox.execute(code)

    print(f"success: {result.success}")
    print(f"output: '{result.output}'")
    print(f"error: {result.error}")
    print(f"duration: {result.duration}")


def example_sandbox_with_agent() -> None:
    """Using sandbox with an agent."""
    print("\n" + "=" * 50)
    print("Sandbox with Agent")
    print("=" * 50)

    from syrin import tool

    sandbox = LocalSandbox()

    @tool
    def execute_code(code: str) -> str:
        """Execute Python code in sandbox and return output."""
        result = sandbox.execute(code)
        if result.success:
            return result.output
        return f"Error: {result.error}"

    class CodingAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a coding assistant. Use the execute_code tool to run Python code."
        tools = [execute_code]

    agent = CodingAgent()

    result = agent.response("What is 10 + 5? Use the tool to calculate.")
    print(f"Response: {result.content}")
    print(f"Tool calls: {len(result.tool_calls)}")


if __name__ == "__main__":
    example_local_sandbox()
    example_subprocess_sandbox()
    example_sandbox_error_handling()
    example_sandbox_with_timeout()
    example_sandbox_execute_file()
    example_get_sandbox()
    example_sandbox_result()
    example_sandbox_with_agent()
