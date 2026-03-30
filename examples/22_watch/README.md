# 22_watch — Event-driven agents and pipelines

- **cron_trigger.py** — Fire an agent on a schedule with `CronProtocol`.
- **webhook_trigger.py** — Trigger an agent from HTTP requests with `WebhookProtocol`.
- **queue_trigger.py** — Consume queue messages with `QueueProtocol`.
- **pipeline_watch.py** — Feed watch events into a pipeline.
- **multi_protocol.py** — Combine multiple trigger sources in one application.

These examples cover the `syrin.watch` surface exposed for long-running workers and background automation.
