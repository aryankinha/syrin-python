"""Tests for Workflow checkpoint/resume across processes.

Exit criteria:
- Workflow with persistent CheckpointBackend: pause in process A,
  resume in process B — correct step and HandoffContext restored
"""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.checkpoint._core import MemoryCheckpointBackend
from syrin.workflow._core import Workflow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model() -> Model:
    return Model.Almock(latency_seconds=0.01, lorem_length=3)


class _AgentA(Agent):
    model = _model()
    system_prompt = "a"


class _AgentB(Agent):
    model = _model()
    system_prompt = "b"


class _AgentC(Agent):
    model = _model()
    system_prompt = "c"


# ---------------------------------------------------------------------------
# Checkpoint save: backend receives entries after each step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkpoint_saved_after_each_step() -> None:
    """After each workflow step, a checkpoint is saved to the backend."""
    backend = MemoryCheckpointBackend()
    wf = Workflow("cp-wf", checkpoint_backend=backend).step(_AgentA).step(_AgentB)
    await wf.run("input")

    # Backend should have the 'latest' checkpoint
    ckpts = backend.list("cp-wf")
    # run_id:latest should be in the list
    assert len(ckpts) == 1
    ckpt = backend.load(ckpts[0])
    assert ckpt is not None
    # After 2 steps the last saved checkpoint step_index is 1 (second step)
    assert ckpt.metadata["step_index"] == 1


@pytest.mark.asyncio
async def test_checkpoint_stores_handoff_context() -> None:
    """Checkpoint metadata contains the HandoffContext fields."""
    backend = MemoryCheckpointBackend()
    wf = Workflow("ctx-wf", checkpoint_backend=backend).step(_AgentA).step(_AgentB)
    await wf.run("hello world")

    ckpts = backend.list("ctx-wf")
    ckpt = backend.load(ckpts[0])
    assert ckpt is not None
    meta = ckpt.metadata
    assert "content" in meta
    assert "history" in meta
    assert "budget_remaining" in meta
    assert "run_id" in meta


@pytest.mark.asyncio
async def test_checkpoint_stores_total_cost() -> None:
    """Checkpoint metadata contains accumulated total_cost."""
    backend = MemoryCheckpointBackend()
    wf = Workflow("cost-wf", checkpoint_backend=backend).step(_AgentA)
    await wf.run("task")

    ckpts = backend.list("cost-wf")
    ckpt = backend.load(ckpts[0])
    assert ckpt is not None
    assert "total_cost" in ckpt.metadata
    assert isinstance(ckpt.metadata["total_cost"], float)


# ---------------------------------------------------------------------------
# Checkpoint resume: start from saved step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_skips_completed_steps() -> None:
    """When resuming, steps before the checkpoint step_index are skipped."""
    backend = MemoryCheckpointBackend()

    # Track which agents actually ran
    ran: list[str] = []

    class _TrackA(Agent):
        model = _model()
        system_prompt = "track-a"

        async def arun(self, *args: object, **kwargs: object) -> object:
            ran.append("A")
            return await super().arun(*args, **kwargs)

    class _TrackB(Agent):
        model = _model()
        system_prompt = "track-b"

        async def arun(self, *args: object, **kwargs: object) -> object:
            ran.append("B")
            return await super().arun(*args, **kwargs)

    # First run: complete both steps, save checkpoint
    wf1 = Workflow("resume-wf", checkpoint_backend=backend).step(_TrackA).step(_TrackB)
    await wf1.run("start")
    run_id = wf1._executor.run_id if wf1._executor else None
    assert run_id is not None
    assert "A" in ran
    assert "B" in ran

    # Now pretend we only completed step 0 (patch the checkpoint)
    ckpt_key = f"{run_id}:latest"
    from syrin.checkpoint._core import CheckpointState

    partial_ckpt = CheckpointState(
        agent_name="resume-wf",
        checkpoint_id=ckpt_key,
        metadata={
            "step_index": 0,  # step 0 done, resume from step 1
            "total_cost": 0.001,
            "budget_remaining": 9.999,
            "content": "output after A",
            "history": ["start"],
            "run_id": run_id,
        },
    )
    backend.save(partial_ckpt)

    ran.clear()

    # Resume from checkpoint
    wf2 = (
        Workflow(
            "resume-wf",
            checkpoint_backend=backend,
            resume_run_id=run_id,
        )
        .step(_TrackA)
        .step(_TrackB)
    )
    await wf2.run("start")

    # Only B should have run (A was already done at step_index=0)
    assert "A" not in ran, "Step A should have been skipped on resume"
    assert "B" in ran, "Step B should have run on resume"


@pytest.mark.asyncio
async def test_resume_restores_handoff_context_content() -> None:
    """After resume, the agent receives the content from the saved HandoffContext."""
    backend = MemoryCheckpointBackend()

    received_inputs: list[str] = []

    class _CapAgent(Agent):
        model = _model()
        system_prompt = "capture"

        async def arun(self, prompt: str, **kwargs: object) -> object:
            received_inputs.append(prompt)
            return await super().arun(prompt, **kwargs)

    # Save a partial checkpoint with step_index=0 (so step 1 = _CapAgent will run)
    class _DummyA(Agent):
        model = _model()
        system_prompt = "dummy"

    # First create a run to get a valid run_id
    wf_init = Workflow("ctx-restore-wf", checkpoint_backend=backend).step(_DummyA)
    await wf_init.run("original")
    run_id = wf_init._executor.run_id if wf_init._executor else "run-test"

    # Manually set up a checkpoint with specific content
    from syrin.checkpoint._core import CheckpointState

    ckpt = CheckpointState(
        agent_name="ctx-restore-wf",
        checkpoint_id=f"{run_id}:latest",
        metadata={
            "step_index": 0,
            "total_cost": 0.0,
            "budget_remaining": 10.0,
            "content": "restored content from checkpoint",
            "history": [],
            "run_id": run_id,
        },
    )
    backend.save(ckpt)

    wf2 = (
        Workflow(
            "ctx-restore-wf",
            checkpoint_backend=backend,
            resume_run_id=run_id,
        )
        .step(_DummyA)
        .step(_CapAgent)
    )
    await wf2.run("ignored on resume")

    # The CapAgent (step 1) should have received the restored content as input
    assert len(received_inputs) > 0
    assert "restored content from checkpoint" in received_inputs[0]
