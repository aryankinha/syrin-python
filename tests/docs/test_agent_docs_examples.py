"""Validate code examples from docs/agent/*.md.

Each test runs a logical code example extracted from the documentation.
Examples that call response(), arun(), stream(), or astream() mock the provider
to avoid real LLM calls. Examples that only construct agents or call read-only
methods run without mocking.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from syrin import Agent, Budget, Hook, Pipeline
from syrin.agent.multi_agent import parallel, sequential
from syrin.budget import RateLimit
from syrin.checkpoint import CheckpointConfig, CheckpointTrigger
from syrin.enums import LoopStrategy, MemoryType, OnExceeded
from syrin.memory import BufferMemory
from syrin.model import Model
from syrin.tool import tool
from syrin.types import ProviderResponse, TokenUsage


def _mock_provider_response(
    content: str = "test response",
    tool_calls: list | None = None,
) -> ProviderResponse:
    return ProviderResponse(
        content=content,
        tool_calls=tool_calls or [],
        token_usage=TokenUsage(input_tokens=10, output_tokens=20),
    )


def _create_mock_provider():
    mock = MagicMock()
    mock.complete = AsyncMock(return_value=_mock_provider_response())
    mock.stream_sync = MagicMock(
        return_value=iter([_mock_provider_response(content="chunk1"), _mock_provider_response(content="chunk2")])
    )

    async def _stream_gen(*_args, **_kwargs):
        yield _mock_provider_response(content="async chunk")

    mock.stream = _stream_gen
    return mock


# -----------------------------------------------------------------------------
# docs/agent/README.md
# -----------------------------------------------------------------------------


class TestReadmeExamples:
    """Examples from docs/agent/README.md."""

    @patch("syrin.agent._get_provider")
    def test_quick_start(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            system_prompt="You are a helpful assistant.",
        )
        response = agent.response("Hello!")
        assert response.content


# -----------------------------------------------------------------------------
# docs/agent/running.md
# -----------------------------------------------------------------------------


class TestRunningExamples:
    """Examples from docs/agent/running.md."""

    @patch("syrin.agent._get_provider")
    def test_response_sync(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        response = agent.response("What is the capital of France?")
        assert response.content
        assert hasattr(response, "cost")

    @pytest.mark.asyncio
    @patch("syrin.agent._get_provider")
    async def test_arun_async(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        response = await agent.arun("What is the capital of France?")
        assert response.content

    @patch("syrin.agent._get_provider")
    def test_stream_sync(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        chunks = list(agent.stream("Write a short poem"))
        assert len(chunks) >= 1
        assert all(hasattr(c, "text") and hasattr(c, "accumulated_text") for c in chunks)

    @pytest.mark.asyncio
    @patch("syrin.agent._get_provider")
    async def test_astream_async(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        chunks = [c async for c in agent.astream("Write a short poem")]
        assert len(chunks) >= 1

    @patch("syrin.agent._get_provider")
    def test_stream_chunk_fields(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        for chunk in agent.stream("Hello"):
            assert hasattr(chunk, "text")
            assert hasattr(chunk, "accumulated_text")
            assert hasattr(chunk, "cost_so_far")
            break

    def test_error_handling_imports(self):
        from syrin.exceptions import BudgetExceededError, ToolExecutionError

        assert BudgetExceededError is not None
        assert ToolExecutionError is not None


# -----------------------------------------------------------------------------
# docs/agent/memory.md
# -----------------------------------------------------------------------------


class TestMemoryExamples:
    """Examples from docs/agent/memory.md."""

    def test_remember_returns_memory_id(self):
        from syrin.memory import Memory

        agent = Agent(model=Model("openai/gpt-4o-mini"), memory=Memory())
        mem_id = agent.remember(
            "User prefers dark mode",
            memory_type=MemoryType.EPISODIC,
            importance=0.8,
            user_id="user_123",
        )
        assert isinstance(mem_id, str)

    def test_recall_returns_list(self):
        from syrin.memory import Memory

        agent = Agent(model=Model("openai/gpt-4o-mini"), memory=Memory())
        memories = agent.recall(query="user preferences", memory_type=MemoryType.EPISODIC, limit=10)
        assert isinstance(memories, list)

    def test_forget_returns_int(self):
        from syrin.memory import Memory

        agent = Agent(model=Model("openai/gpt-4o-mini"), memory=Memory())
        agent.remember("temp fact")
        deleted = agent.forget(memory_type=MemoryType.EPISODIC)
        assert isinstance(deleted, int)

    def test_memory_config_agent_construction(self):
        from syrin.enums import MemoryBackend
        from syrin.memory.config import Memory as MemoryConfig

        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            memory=MemoryConfig(
                backend=MemoryBackend.MEMORY,
                types=[MemoryType.CORE, MemoryType.EPISODIC],
                top_k=10,
                relevance_threshold=0.7,
                auto_store=False,
            ),
        )
        assert agent.memory is not None

    def test_conversation_memory_buffer(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"), memory=BufferMemory())
        assert agent.conversation_memory is not None


# -----------------------------------------------------------------------------
# docs/agent/budget.md
# -----------------------------------------------------------------------------


class TestBudgetExamples:
    """Examples from docs/agent/budget.md."""

    @patch("syrin.agent._get_provider")
    def test_budget_basic_usage(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"), budget=Budget(run=1.0))
        response = agent.response("Hello")
        assert response.content
        summary = agent.budget_summary
        assert "current_run_cost" in summary or "run_cost" in summary or "run_remaining" in summary

    def test_budget_params_construction(self):
        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            budget=Budget(
                run=1.0,
                per=RateLimit(hour=10),
                on_exceeded=OnExceeded.ERROR,
                shared=False,
            ),
        )
        assert agent._budget is not None

    def test_budget_store_construction(self):
        from syrin.budget_store import FileBudgetStore

        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            budget=Budget(run=1.0),
            budget_store=FileBudgetStore("/tmp/budget.json"),
            budget_store_key="user_123",
        )
        assert agent._budget_store is not None


# -----------------------------------------------------------------------------
# docs/agent/tools.md
# -----------------------------------------------------------------------------


class TestToolsExamples:
    """Examples from docs/agent/tools.md."""

    def test_tool_definition(self):
        @tool
        def search(query: str) -> str:
            """Search the web for information."""
            return f"Results for: {query}"

        assert search.name == "search"

    def test_agent_with_tools_construction(self):
        @tool
        def search(query: str) -> str:
            """Search the web for information."""
            return f"Results for: {query}"

        @tool
        def calculate(expression: str) -> str:
            """Evaluate a mathematical expression. Use only +, -, *, /, **."""
            return str(eval(expression))

        agent = Agent(model=Model("openai/gpt-4o-mini"), tools=[search, calculate])
        assert len(agent._tools) == 2

    def test_tool_with_optional_params(self):
        @tool
        def create_task(title: str, priority: int = 1, tags: list[str] | None = None) -> str:
            """Create a task with title, optional priority and tags."""
            return f"Created: {title} (priority={priority})"

        result = create_task.func(title="test", priority=2)
        assert "Created:" in result

    @patch("syrin.agent._get_provider")
    def test_execute_tool_custom_loop(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        @tool
        def search(query: str) -> str:
            return f"Results: {query}"

        agent = Agent(model=Model("openai/gpt-4o-mini"), tools=[search])
        result = agent._execute_tool("search", {"query": "hello"})
        assert "hello" in result


# -----------------------------------------------------------------------------
# docs/agent/constructor.md
# -----------------------------------------------------------------------------


class TestConstructorExamples:
    """Examples from docs/agent/constructor.md."""

    def test_model_openai_anthropic_ollama(self):
        agent1 = Agent(model=Model("openai/gpt-4o-mini"))
        agent2 = Agent(model=Model("anthropic/claude-3-5-sonnet"))
        agent3 = Agent(model=Model("ollama/llama3"))
        assert agent1._model_config.provider == "openai"
        assert agent2._model_config.provider == "anthropic"
        assert agent3._model_config.provider in ("ollama", "litellm")

    def test_system_prompt(self):
        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            system_prompt="You are a helpful assistant. Be concise.",
        )
        assert "helpful" in agent._system_prompt

    def test_tools_constructor(self):
        @tool
        def search(query: str) -> str:
            """Search for information."""
            return f"Results: {query}"

        agent = Agent(model=Model("openai/gpt-4o-mini"), tools=[search])
        assert len(agent._tools) == 1

    def test_budget_constructor(self):
        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            budget=Budget(run=1.0, on_exceeded=OnExceeded.STOP),
        )
        assert agent._budget is not None

    def test_output_constructor(self):
        from pydantic import BaseModel

        from syrin.output import Output

        class Answer(BaseModel):
            text: str
            confidence: float

        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            output=Output(Answer, validation_retries=3, context={"allowed_domains": ["example.com"]}),
        )
        assert agent._output is not None

    def test_max_tool_iterations(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"), max_tool_iterations=5)
        assert agent._max_tool_iterations == 5

    def test_budget_store_constructor(self):
        from syrin.budget_store import FileBudgetStore

        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            budget=Budget(run=1.0),
            budget_store=FileBudgetStore("/tmp/budget.json"),
            budget_store_key="user_123",
        )
        assert agent._budget_store_key == "user_123"

    def test_memory_config_constructor(self):
        from syrin.memory.config import Memory as MemoryConfig

        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            memory=MemoryConfig(types=[MemoryType.CORE, MemoryType.EPISODIC], top_k=10, auto_store=True),
        )
        assert agent.memory is not None

    @patch("syrin.agent._get_provider")
    def test_loop_strategy_constructor(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"), loop_strategy=LoopStrategy.SINGLE_SHOT)
        response = agent.response("Hi")
        assert response.content

    def test_loop_constructor(self):
        from syrin.loop import ReactLoop

        agent = Agent(model=Model("openai/gpt-4o-mini"), loop=ReactLoop(max_iterations=5))
        assert agent._loop is not None

    def test_guardrails_constructor(self):
        from syrin.guardrails import BlockedWordsGuardrail

        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            guardrails=[BlockedWordsGuardrail(["spam", "offensive"])],
        )
        assert agent._guardrails is not None

    def test_context_constructor(self):
        from syrin.context import Context

        agent = Agent(model=Model("openai/gpt-4o-mini"), context=Context())
        assert agent.context is not None

    def test_rate_limit_constructor(self):
        from syrin.ratelimit import APIRateLimit

        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            rate_limit=APIRateLimit(rpm=60, tpm=90000),
        )
        assert agent.rate_limit is not None

    def test_checkpoint_constructor(self):
        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            checkpoint=CheckpointConfig(
                enabled=True,
                storage="sqlite",
                path="/tmp/checkpoints.db",
                trigger=CheckpointTrigger.STEP,
                max_checkpoints=10,
            ),
        )
        assert agent._checkpoint_config is not None

    def test_debug_constructor(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"), debug=True)
        assert agent._debug is True

    @patch("syrin.agent._get_provider")
    def test_complete_example(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        @tool
        def search(query: str) -> str:
            """Search for information."""
            return f"Results: {query}"

        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            system_prompt="You are a research assistant.",
            tools=[search],
            budget=Budget(run=0.50),
            max_tool_iterations=10,
            memory=None,
            loop_strategy=LoopStrategy.REACT,
            guardrails=[],
            checkpoint=CheckpointConfig(enabled=True, trigger=CheckpointTrigger.STEP, max_checkpoints=5),
            debug=False,
        )
        response = agent.response("What is quantum computing?")
        assert response.content


# -----------------------------------------------------------------------------
# docs/agent/creating-agents.md
# -----------------------------------------------------------------------------


class TestCreatingAgentsExamples:
    """Examples from docs/agent/creating-agents.md."""

    @patch("syrin.agent._get_provider")
    def test_instance_based(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            system_prompt="You are helpful.",
        )
        response = agent.response("Hello")
        assert response.content

    @patch("syrin.agent._get_provider")
    def test_class_based(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        class Assistant(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "You are a helpful assistant."

        agent = Assistant()
        response = agent.response("Hello")
        assert response.content

    def test_inheritance_mro(self):
        @tool
        def search(query: str) -> str:
            """Search for information."""
            return f"Results: {query}"

        @tool
        def calculate(expression: str) -> str:
            """Evaluate a math expression."""
            return str(eval(expression))

        class BaseResearcher(Agent):
            model = Model("openai/gpt-4o")
            system_prompt = "You are a researcher."
            tools = [search]

        class MathResearcher(BaseResearcher):
            model = Model("openai/gpt-4o-mini")
            tools = [calculate]

        agent = MathResearcher()
        assert agent._model_config.model_id == "gpt-4o-mini" or "gpt-4o-mini" in str(agent._model_config.model_id)
        assert len(agent._tools) == 2

    def test_override_at_instantiation(self):
        @tool
        def search(query: str) -> str:
            return f"Results: {query}"

        @tool
        def calculate(expression: str) -> str:
            return str(eval(expression))

        class BaseResearcher(Agent):
            model = Model("openai/gpt-4o")
            system_prompt = "You are a researcher."
            tools = [search]

        class MathResearcher(BaseResearcher):
            model = Model("openai/gpt-4o-mini")
            tools = [calculate]

        agent = MathResearcher(
            system_prompt="You are a math specialist.",
            tools=[calculate],
        )
        assert "math specialist" in agent._system_prompt

    def test_model_required_raises(self):
        with pytest.raises(TypeError, match="model"):
            Agent()

    def test_custom_agent_name(self):
        class ResearcherAgent(Agent):
            _syrin_name = "research"
            model = Model("openai/gpt-4o")
            system_prompt = "You are a researcher."

        assert getattr(ResearcherAgent, "_syrin_name", None) == "research"


# -----------------------------------------------------------------------------
# docs/agent/overview.md
# -----------------------------------------------------------------------------


class TestOverviewExamples:
    """Examples from docs/agent/overview.md."""

    def test_model_usage(self):
        model = Model("openai/gpt-4o-mini")
        assert model is not None

    @patch("syrin.agent._get_provider")
    def test_minimum_agent(self, mock_get_provider):
        mock_get_provider.return_value = _mock_provider_response(content="4")
        mock = MagicMock()
        mock.complete = AsyncMock(return_value=_mock_provider_response(content="4"))
        mock.stream_sync = MagicMock(return_value=iter([_mock_provider_response(content="4")]))

        async def _stream(*_args, **_kwargs):
            yield _mock_provider_response(content="4")

        mock.stream = AsyncMock(return_value=_stream())
        mock_get_provider.return_value = mock

        agent = Agent(model=Model("openai/gpt-4o-mini"))
        response = agent.response("What is 2+2?")
        assert response.content

    @patch("syrin.agent._get_provider")
    def test_full_featured_agent(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        @tool
        def search(query: str) -> str:
            """Search the web for information."""
            return f"Results for: {query}"

        class ResearchAgent(Agent):
            model = Model("openai/gpt-4o")
            system_prompt = "You are a research specialist. Use tools when needed."
            tools = [search]
            budget = Budget(run=1.0)

        agent = ResearchAgent(debug=True)
        events_fired = []

        def on_end(ctx):
            events_fired.append(ctx)

        agent.events.on(Hook.AGENT_RUN_END, on_end)
        response = agent.response("Research quantum computing")
        assert response.content
        assert hasattr(response, "cost")


# -----------------------------------------------------------------------------
# docs/agent/response.md
# -----------------------------------------------------------------------------


class TestResponseExamples:
    """Examples from docs/agent/response.md."""

    @patch("syrin.agent._get_provider")
    def test_response_fields(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        response = agent.response("Hello")
        assert hasattr(response, "content")
        assert hasattr(response, "cost")
        assert hasattr(response, "tokens")
        assert hasattr(response, "model")

    @patch("syrin.agent._get_provider")
    def test_str_response(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        response = agent.response("Hello")
        assert str(response) == response.content

    @patch("syrin.agent._get_provider")
    def test_bool_response(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        response = agent.response("Hello")
        assert bool(response) is True


# -----------------------------------------------------------------------------
# docs/agent/properties.md
# -----------------------------------------------------------------------------


class TestPropertiesExamples:
    """Examples from docs/agent/properties.md."""

    def test_budget_summary(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"), budget=Budget(run=1.0))
        summary = agent.budget_summary
        assert isinstance(summary, dict)

    def test_memory_property(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"), memory=BufferMemory())
        mem = agent.memory
        assert mem is not None

    def test_conversation_memory_property(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"), memory=BufferMemory())
        conv = agent.conversation_memory
        assert conv is not None

    def test_context_property(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        ctx = agent.context
        assert ctx is not None

    def test_switch_model(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        agent.switch_model(Model("openai/gpt-4o"))
        assert "gpt-4o" in str(agent._model_config.model_id)


# -----------------------------------------------------------------------------
# docs/agent/rate-limiting.md
# -----------------------------------------------------------------------------


class TestRateLimitingExamples:
    """Examples from docs/agent/rate-limiting.md."""

    def test_rate_limit_basic(self):
        from syrin.ratelimit import APIRateLimit

        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            rate_limit=APIRateLimit(rpm=60, tpm=90000),
        )
        assert agent.rate_limit is not None


# -----------------------------------------------------------------------------
# docs/agent/guardrails.md
# -----------------------------------------------------------------------------


class TestGuardrailsExamples:
    """Examples from docs/agent/guardrails.md."""

    def test_blocked_words_guardrail(self):
        from syrin.guardrails import BlockedWordsGuardrail

        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            guardrails=[BlockedWordsGuardrail(["spam", "offensive"])],
        )
        assert agent._guardrails is not None


# -----------------------------------------------------------------------------
# docs/agent/checkpointing.md
# -----------------------------------------------------------------------------


class TestCheckpointingExamples:
    """Examples from docs/agent/checkpointing.md."""

    def test_checkpoint_config(self):
        agent = Agent(
            model=Model("openai/gpt-4o-mini"),
            checkpoint=CheckpointConfig(
                enabled=True,
                storage="sqlite",
                path="/tmp/agent_checkpoints.db",
                trigger=CheckpointTrigger.STEP,
                max_checkpoints=10,
            ),
        )
        assert agent._checkpoint_config is not None

    def test_save_checkpoint_returns_optional_str(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"), checkpoint=CheckpointConfig(enabled=False))
        result = agent.save_checkpoint(name="test", reason="test")
        assert result is None or isinstance(result, str)

    def test_load_checkpoint_returns_bool(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        success = agent.load_checkpoint("nonexistent-id")
        assert isinstance(success, bool)

    def test_list_checkpoints_returns_list(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        ids = agent.list_checkpoints(name="test")
        assert isinstance(ids, list)


# -----------------------------------------------------------------------------
# docs/agent/events-hooks.md
# -----------------------------------------------------------------------------


class TestEventsHooksExamples:
    """Examples from docs/agent/events-hooks.md."""

    @patch("syrin.agent._get_provider")
    def test_register_handlers(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        events_seen = []

        def on_start(ctx):
            events_seen.append(("start", ctx))

        def on_end(ctx):
            events_seen.append(("end", ctx))

        agent.events.on(Hook.AGENT_RUN_START, on_start)
        agent.events.on(Hook.AGENT_RUN_END, on_end)
        agent.response("Hi")
        assert len(events_seen) >= 2

    def test_on_all_handler(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        seen = []

        def log_all(hook, ctx):
            seen.append(hook)

        agent.events.on_all(log_all)
        assert callable(agent.events.on_all)


# -----------------------------------------------------------------------------
# docs/agent/handoff-spawn.md
# -----------------------------------------------------------------------------


class TestHandoffSpawnExamples:
    """Examples from docs/agent/handoff-spawn.md."""

    @patch("syrin.agent._get_provider")
    def test_handoff(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        class Researcher(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "You research topics."

        class Writer(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "You write articles."

        researcher = Researcher()
        response = researcher.handoff(Writer, "Write an article based on your research")
        assert response.content

    @patch("syrin.agent._get_provider")
    def test_spawn_with_task(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        class Parent(Agent):
            model = Model("openai/gpt-4o-mini")

        class Child(Agent):
            model = Model("openai/gpt-4o-mini")

        parent = Parent()
        result = parent.spawn(Child, task="Research topic X", budget=Budget(run=0.10))
        assert result.content

    @patch("syrin.agent._get_provider")
    def test_spawn_parallel(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        class Parent(Agent):
            model = Model("openai/gpt-4o-mini")

        class Researcher(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "Research."

        class Analyst(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "Analyze."

        class Writer(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "Write."

        parent = Parent()
        results = parent.spawn_parallel(
            [
                (Researcher, "Research A"),
                (Analyst, "Analyze B"),
                (Writer, "Write C"),
            ]
        )
        assert len(results) == 3
        assert all(hasattr(r, "content") for r in results)


# -----------------------------------------------------------------------------
# docs/agent/multi-agent-patterns.md
# -----------------------------------------------------------------------------


class TestMultiAgentPatternsExamples:
    """Examples from docs/agent/multi-agent-patterns.md."""

    @patch("syrin.agent._get_provider")
    def test_pipeline_sequential(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        class ResearcherAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "Research."

        class WriterAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "Write summaries."

        pipeline = Pipeline(budget=Budget(run=1.0))
        result = pipeline.run(
            [
                (ResearcherAgent, "Research quantum computing"),
                (WriterAgent, "Write a summary"),
            ]
        ).sequential()
        assert result.content

    @patch("syrin.agent._get_provider")
    def test_pipeline_parallel(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        class ResearcherAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "Research."

        pipeline = Pipeline()
        results = pipeline.run(
            [
                (ResearcherAgent, "Research topic A"),
                (ResearcherAgent, "Research topic B"),
            ]
        ).parallel()
        assert len(results) == 2

    @pytest.mark.asyncio
    @patch("syrin.agent._get_provider")
    async def test_parallel_helper(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent1 = Agent(model=Model("openai/gpt-4o-mini"))
        agent2 = Agent(model=Model("openai/gpt-4o-mini"))
        results = await parallel(
            [
                (agent1, "Task 1"),
                (agent2, "Task 2"),
            ]
        )
        assert len(results) == 2

    @patch("syrin.agent._get_provider")
    def test_sequential_helper(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent1 = Agent(model=Model("openai/gpt-4o-mini"))
        agent2 = Agent(model=Model("openai/gpt-4o-mini"))
        result = sequential(
            [(agent1, "Task 1"), (agent2, "Task 2")],
            pass_previous=True,
        )
        assert result.content


# -----------------------------------------------------------------------------
# docs/agent/model.md
# -----------------------------------------------------------------------------


class TestModelExamples:
    """Examples from docs/agent/model.md."""

    def test_switch_model_runtime(self):
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        agent.switch_model(Model("openai/gpt-4o"))
        assert agent._model_config is not None

    @patch("syrin.agent._get_provider")
    def test_response_model_field(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()
        agent = Agent(model=Model("openai/gpt-4o-mini"))
        response = agent.response("Hello")
        assert response.model


# -----------------------------------------------------------------------------
# docs/agent/structured-output.md (partial - Output construction only)
# -----------------------------------------------------------------------------


class TestStructuredOutputExamples:
    """Examples from docs/agent/structured-output.md."""

    def test_output_config_construction(self):
        from pydantic import BaseModel

        from syrin.output import Output

        class UserInfo(BaseModel):
            name: str
            age: int
            email: str

        agent = Agent(model=Model("openai/gpt-4o-mini"), output=Output(UserInfo))
        assert agent._output is not None
