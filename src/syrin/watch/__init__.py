"""Watch / event-driven triggers for Agent, Pipeline, and DynamicPipeline.

Register ``WatchProtocol`` implementations to have your agent respond to
webhooks, cron schedules, message queues, or any other trigger source.

Example::

    from syrin import Agent, Model
    from syrin.watch import WebhookProtocol, CronProtocol

    agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="..."))

    # Single protocol
    agent.watch(protocol=CronProtocol(schedule="0 9 * * 1-5", input="Good morning!"))

    # Multiple protocols
    agent.watch(protocols=[
        CronProtocol(schedule="0 9 * * 1-5", input="Weekday report"),
        WebhookProtocol(path="/trigger", port=8080, secret="hmac-secret"),
    ])
"""

from syrin.watch._cron import CronProtocol
from syrin.watch._queue import QueueBackend, QueueProtocol
from syrin.watch._trigger import TriggerEvent, WatchProtocol
from syrin.watch._watchable import Watchable
from syrin.watch._webhook import WebhookProtocol

__all__ = [
    "TriggerEvent",
    "WatchProtocol",
    "Watchable",
    "WebhookProtocol",
    "CronProtocol",
    "QueueProtocol",
    "QueueBackend",
]
