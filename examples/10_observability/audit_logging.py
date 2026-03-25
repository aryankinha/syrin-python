"""Audit logging for compliance and observability.

AuditLog persists lifecycle events (LLM calls, tool calls, handoffs, spawns)
to JSONL files or custom backends. Use for compliance, debugging, and
cost attribution.

Run: python examples/10_observability/audit_logging.py
Visit: http://localhost:8000/playground
Requires: uv pip install syrin[serve]
"""

import syrin
from syrin import Agent, AgentConfig, AuditLog, Model, Pipeline
from syrin.agent.multi_agent import DynamicPipeline


def main() -> None:
    # Agent with audit - writes to ./audit_agent.jsonl
    audit = AuditLog(path="./audit_agent.jsonl")
    agent = Agent(
        model=Model.Almock(),
        system_prompt="You are helpful.",
        config=AgentConfig(audit=audit),
    )
    agent.run("What is 2+2?")
    print("Agent audit written to ./audit_agent.jsonl")

    # Pipeline with audit
    pipeline_audit = AuditLog(path="./audit_pipeline.jsonl")

    class Writer(Agent):
        model = Model.Almock()
        system_prompt = "Write concisely."

    pipeline = Pipeline(audit=pipeline_audit)
    pipeline.run([(Writer, "Say hello in one word")])
    print("Pipeline audit written to ./audit_pipeline.jsonl")

    # DynamicPipeline with audit
    dyn_audit = AuditLog(path="./audit_dynamic.jsonl")
    dyn = DynamicPipeline(
        agents=[Writer],
        model=Model.Almock(),
        audit=dyn_audit,
    )
    dyn.run("Greet the user")
    print("DynamicPipeline audit written to ./audit_dynamic.jsonl")

    # Query entries (built-in JSONL backend)
    backend = audit.get_backend()
    entries = backend.query(syrin.AuditFilters(limit=5))
    print(f"\nLast 5 agent audit entries: {len(entries)}")
    for e in entries[:3]:
        print(f"  {e.timestamp} | {e.event} | {e.source}")


class AuditDemoAgent(syrin.Agent):
    _agent_name = "audit-agent"
    _agent_description = "Agent with audit logging"
    model = syrin.Model.Almock()
    system_prompt = "You are helpful."


if __name__ == "__main__":
    main()
    audit = syrin.AuditLog(path="./audit_serve.jsonl")
    agent = AuditDemoAgent(config=AgentConfig(audit=audit))
    print("Serving at http://localhost:8000/playground")
    agent.serve(port=8000, enable_playground=True, debug=True)
