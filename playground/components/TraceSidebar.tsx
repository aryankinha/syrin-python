"use client";

import { useCallback, useState } from "react";

const TRUNCATE_AT = 120;
const MAX_DATA_PREVIEW = 80;

function formatHookLabel(hook: string, ctx: Record<string, unknown>): string {
  const tool = ctx?.tool ?? ctx?.tool_name;
  const agent = ctx?.agent_type ?? ctx?.agent ?? ctx?.agent_name;
  const model = ctx?.model ?? ctx?.model_name;

  switch (hook) {
    case "agent.run.start":
      return "Agent run started";
    case "agent.run.end":
      return "Agent run complete";
    case "agent.init":
      return "Agent init";
    case "llm.request.start":
      return model ? `LLM: ${model}` : "LLM started";
    case "llm.request.end":
      return "LLM complete";
    case "tool.call.start":
      return tool ? `Tool "${tool}"` : "Tool called";
    case "tool.call.end":
      return tool ? `Tool "${tool}" done` : "Tool complete";
    case "tool.error":
      return "Tool error";
    case "budget.check":
      return "Budget check";
    case "budget.threshold":
      return "Cost threshold";
    case "budget.exceeded":
      return "Budget exceeded";
    case "guardrail.input":
    case "guardrail.output":
    case "guardrail.blocked":
      return hook.replace(/\./g, " ");
    case "memory.store":
    case "memory.recall":
    case "memory.forget":
      return hook.replace(/\./g, " ");
    case "checkpoint.save":
    case "checkpoint.load":
      return hook.replace(/\./g, " ");
    case "dynamic.pipeline.start":
      return "Dynamic pipeline start";
    case "dynamic.pipeline.plan":
      return "Dynamic pipeline plan";
    case "dynamic.pipeline.execute":
      return "Dynamic pipeline execute";
    case "dynamic.pipeline.agent.spawn":
      return agent ? `Spawned "${agent}"` : "Agent spawned";
    case "dynamic.pipeline.agent.complete":
      return agent ? `"${agent}" complete` : "Agent complete";
    case "dynamic.pipeline.end":
      return "Dynamic pipeline end";
    case "dynamic.pipeline.error":
      return "Dynamic pipeline error";
    case "pipeline.start":
    case "pipeline.end":
      return hook.replace(/\./g, " ");
    case "pipeline.agent.start":
      return agent ? `Pipeline: ${agent}` : "Pipeline started";
    case "pipeline.agent.complete":
      return agent ? `${agent} done` : "Pipeline complete";
    case "generation.image.start":
      return "Generation image start";
    case "generation.image.end": {
      const cost = extractImageCost(ctx);
      return cost != null ? `Generation image end ($${cost.toFixed(4)})` : "Generation image end";
    }
    case "generation.image.error":
      return "Generation image error";
    case "generation.video.start":
      return "Generation video start";
    case "generation.video.end": {
      const cost = extractVideoCost(ctx);
      return cost != null ? `Generation video end ($${cost.toFixed(4)})` : "Generation video end";
    }
    case "generation.video.error":
      return "Generation video error";
    case "handoff.start":
    case "handoff.end":
    case "spawn.start":
    case "spawn.end":
    case "hitl.pending":
    case "hitl.approved":
    case "hitl.rejected":
    case "output.validation.start":
    case "output.validation.success":
    case "output.validation.failed":
      return hook.replace(/\./g, " ");
    default:
      return hook.replace(/\./g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

function extractImageCost(ctx: Record<string, unknown>): number | null {
  const results = ctx.results;
  if (!Array.isArray(results)) return null;
  let total = 0;
  for (const r of results) {
    if (r && typeof r === "object" && "metadata" in r) {
      const meta = (r as { metadata?: { cost_usd?: number } }).metadata;
      const c = meta?.cost_usd;
      if (typeof c === "number" && c > 0) total += c;
    }
  }
  return total > 0 ? total : null;
}

function extractVideoCost(ctx: Record<string, unknown>): number | null {
  const result = ctx.result;
  if (!result || typeof result !== "object" || !("metadata" in result)) return null;
  const meta = (result as { metadata?: { cost_usd?: number } }).metadata;
  const c = meta?.cost_usd;
  return typeof c === "number" && c > 0 ? c : null;
}

function isDataUrl(val: unknown): boolean {
  if (typeof val !== "string") return false;
  return val.startsWith("data:image") || val.startsWith("data:video");
}

function isLongDataUrl(val: unknown): boolean {
  return isDataUrl(val) && String(val).length > MAX_DATA_PREVIEW;
}

function ExpandableText({
  text,
  maxLen,
  className,
}: {
  text: string;
  maxLen: number;
  className?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const truncated = text.length > maxLen;
  const display = truncated && !expanded ? text.slice(0, maxLen) + "…" : text;
  return (
    <span className={className}>
      <code>{display}</code>
      {truncated && (
        <button
          type="button"
          className="trace-expand-btn"
          onClick={() => setExpanded(!expanded)}
          aria-label={expanded ? "Show less" : "Show more"}
        >
          {expanded ? "− less" : "+ more"}
        </button>
      )}
    </span>
  );
}

function formatCtxValue(
  key: string,
  val: unknown,
  hook: string
): React.ReactNode {
  if (val == null) return <span className="trace-event-val">{String(val)}</span>;

  // Generation results: show cost summary, avoid huge base64
  if (key === "results" && Array.isArray(val) && hook === "generation.image.end") {
    const cost = extractImageCost({ results: val });
    const count = val.length;
    const parts = [`${count} image${count !== 1 ? "s" : ""}`];
    if (cost != null) parts.push(`$${cost.toFixed(4)}`);
    return (
      <span className="trace-event-val">
        <code>{parts.join(", ")}</code>
      </span>
    );
  }
  if (key === "result" && val && typeof val === "object" && hook === "generation.video.end") {
    const cost = extractVideoCost({ result: val });
    const parts = ["1 video"];
    if (cost != null) parts.push(`$${cost.toFixed(4)}`);
    return (
      <span className="trace-event-val">
        <code>{parts.join(", ")}</code>
      </span>
    );
  }

  const raw = typeof val === "object" ? JSON.stringify(val) : String(val);

  // Long data URLs: show placeholder only
  if (isLongDataUrl(val)) {
    const kind = String(val).startsWith("data:video") ? "video" : "image";
    return (
      <span className="trace-event-val">
        <code className="trace-event-data-placeholder">[{kind} data, {String(val).length} chars]</code>
      </span>
    );
  }

  // Short data:image - show preview
  if (typeof val === "string" && val.startsWith("data:image") && val.length <= 2000) {
    return (
      <span className="trace-event-val">
        <img
          src={val}
          alt=""
          className="trace-event-img-preview"
          width={80}
          height={80}
        />
        <code>{val.length > MAX_DATA_PREVIEW ? val.slice(0, MAX_DATA_PREVIEW) + "…" : val}</code>
      </span>
    );
  }

  // Text/JSON: expandable when long
  if (raw.length > TRUNCATE_AT) {
    return (
      <span className="trace-event-val">
        <ExpandableText text={raw} maxLen={TRUNCATE_AT} />
      </span>
    );
  }

  return (
    <span className="trace-event-val">
      <code>{raw}</code>
    </span>
  );
}

function CopyButton({
  text,
  className,
  title,
}: {
  text: string;
  className?: string;
  title?: string;
}) {
  const [copied, setCopied] = useState(false);
  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* ignore */
    }
  }, [text]);
  return (
    <button
      type="button"
      className={className}
      onClick={copy}
      title={title ?? "Copy"}
      aria-label={title ?? "Copy"}
    >
      {copied ? "✓" : "⎘"}
    </button>
  );
}

function EventCard({
  hook,
  ctx,
}: {
  hook: string;
  ctx: Record<string, unknown>;
}) {
  const label = formatHookLabel(hook, ctx);
  const keys = Object.keys(ctx).filter(
    (k) => !["tokens", "token_usage"].includes(k) && ctx[k] != null
  );
  const sectionText = JSON.stringify({ hook, ctx }, null, 2);

  return (
    <div className="trace-event-card">
      <div className="trace-event-header">
        <span className="trace-event-label">{label}</span>
        <CopyButton
          text={sectionText}
          className="trace-copy-btn trace-copy-section"
          title="Copy section"
        />
      </div>
      {keys.length > 0 && (
        <div className="trace-event-ctx">
          {keys.map((k) => (
            <div key={k} className="trace-event-row">
              <span className="trace-event-key">{k}:</span>
              {formatCtxValue(k, ctx[k], hook)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface TraceSidebarProps {
  events: Array<{ hook: string; ctx: Record<string, unknown> }>;
  cost?: number;
  tokens?: {
    total?: number;
    total_tokens?: number;
    input_tokens?: number;
    output_tokens?: number;
  };
  onClose: () => void;
  isOpen: boolean;
}

export function TraceSidebar({ events, cost, tokens, onClose, isOpen }: TraceSidebarProps) {
  const totalTokens =
    tokens?.total_tokens ??
    tokens?.total ??
    (tokens?.input_tokens ?? 0) + (tokens?.output_tokens ?? 0);

  const allLogsText = [
    cost != null && `Cost: $${Number(cost).toFixed(6)}`,
    totalTokens > 0 && `Tokens: ${totalTokens}`,
    ...events.map((e) => JSON.stringify({ hook: e.hook, ctx: e.ctx }, null, 2)),
  ]
    .filter(Boolean)
    .join("\n\n");

  if (!isOpen) return null;

  return (
    <>
      <div className="trace-sidebar-overlay" onClick={onClose} aria-hidden="true" />
      <aside className="trace-sidebar" role="dialog" aria-label="Reply trace">
        <div className="trace-sidebar-header">
          <h3>Reply trace</h3>
          <div className="trace-sidebar-actions">
            <CopyButton
              text={allLogsText}
              className="trace-copy-btn trace-copy-all"
              title="Copy all logs"
            />
            <button
              type="button"
              className="trace-sidebar-close"
              onClick={onClose}
              aria-label="Close"
            >
              ×
            </button>
          </div>
        </div>
        <div className="trace-sidebar-body">
          {(cost != null || totalTokens > 0) && (
            <div className="trace-meta-cards">
              {cost != null && (
                <div className="trace-meta-card">
                  <span className="trace-meta-label">Cost</span>
                  <span className="trace-meta-val">${Number(cost).toFixed(6)}</span>
                </div>
              )}
              {totalTokens > 0 && (
                <div className="trace-meta-card">
                  <span className="trace-meta-label">Tokens</span>
                  <span className="trace-meta-val">{totalTokens}</span>
                </div>
              )}
            </div>
          )}
          <div className="trace-events-list">
            {events.map((e, i) => (
              <EventCard key={i} hook={e.hook} ctx={e.ctx} />
            ))}
          </div>
        </div>
      </aside>
    </>
  );
}
