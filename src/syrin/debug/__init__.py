"""syrin.debug — Pry: an interactive debugger for AI agents.

Pry is syrin's answer to Ruby's byebug — a rich live TUI that lets you step
through agent execution, inspect state at any point, and set breakpoints
anywhere in your code.

**Quickstart**::

    from syrin import Agent, Model
    from syrin.debug import Pry

    agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="..."))

    pry = Pry()
    pry.attach(agent)
    agent.run("What is the weather?")

**Breakpoints anywhere**::

    pry = Pry()
    pry.attach(agent)

    agent.run("Research topic A")
    pry.debugpoint("before handoff")   # blocks here — inspect full state, then [p]
    agent.handoff(OtherAgent, "task")

**Context manager** (keeps TUI open until you press q)::

    with Pry() as pry:
        pry.attach(agent)
        pry.run(agent.run, "Hello")   # runs agent in background thread
        pry.wait()                    # hold open — [q] to exit

**Filter modes**: ``"all"`` | ``"errors"`` | ``"tools"`` | ``"memory"``

**Tabs** (letter hotkeys):
  [e] event   [a] agents   [t] tools   [m] memory
  [g] guard   [d] debug    [r] errors

**Navigation**:
  [↑↓] scroll   [←→] switch panels   [↵] detail
  [p]  pause/resume   [n] step   [q] quit
"""

from syrin._replay import replay_trace
from syrin.debug._ui import Pry

__all__ = ["Pry", "replay_trace"]
