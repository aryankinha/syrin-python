"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useConfig } from "@/hooks/useConfig";
import { useBudget } from "@/hooks/useBudget";
import { useDescribe } from "@/hooks/useDescribe";
import {
  createStreamProcessor,
  formatHookLabelForActivity,
  type MessageData,
  type MessageAttachment,
  type ActivityEntry,
} from "@/hooks/useStream";
import { AgentIcon } from "@/components/AgentIcon";
import { AgentSelector } from "@/components/AgentSelector";
import { BudgetGauge } from "@/components/BudgetGauge";
import { ChatArea } from "@/components/ChatArea";
import { ChatInput } from "@/components/ChatInput";
import { TraceSidebar } from "@/components/TraceSidebar";
import { AgentDetailsModal } from "@/components/AgentDetailsModal";
import { AgentConfigModal } from "@/components/AgentConfigModal";

export default function PlaygroundPage() {
  const { config, loading, error } = useConfig();
  const [selectedAgent, setSelectedAgent] = useState("");
  const [messages, setMessages] = useState<MessageData[]>([]);
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<MessageAttachment[]>([]);
  const [sending, setSending] = useState(false);
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const [traceSidebar, setTraceSidebar] = useState<{
    events: Array<{ hook: string; ctx: Record<string, unknown> }>;
    cost?: number;
    tokens?: Record<string, number>;
  } | null>(null);
  const activityIdRef = useRef(0);

  const apiBase = config?.apiBase ?? "";
  const multiAgent = config?.agents && config.agents.length > 1;
  const agentPath = multiAgent ? selectedAgent : "";
  const {
    formatBudget,
    refresh: refreshBudget,
    updateFromStream,
  } = useBudget(apiBase, agentPath, !!config);
  const { describe } = useDescribe(apiBase, agentPath, !!config);

  useEffect(() => {
    if (config?.agents?.length && !selectedAgent) {
      setSelectedAgent(config.agents[0].name);
    }
  }, [config?.agents, selectedAgent]);

  const streamUrl = config
    ? config.agents && config.agents.length > 1
      ? `${apiBase}${selectedAgent}/stream`
      : `${apiBase}stream`
    : "";

  const showTrace = useCallback(
    (
      events: Array<{ hook: string; ctx: Record<string, unknown> }>,
      cost?: number,
      tokens?: Record<string, number>
    ) => {
      setTraceSidebar({ events, cost, tokens });
    },
    []
  );

  const buildMessageBody = useCallback(
    (text: string, atts: MessageAttachment[]): string | object[] => {
      if (atts.length === 0) return text || "";
      const parts: object[] = [];
      if (text) parts.push({ type: "text", text });
      for (const a of atts) {
        if (a.type === "image") parts.push({ type: "image_url", image_url: { url: a.url } });
        else parts.push({ type: "text", text: `[File: ${a.contentType || "file"}]` });
      }
      return parts;
    },
    []
  );

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if ((!text && attachments.length === 0) || !config || sending) return;

    const userAttachments = [...attachments];
    setInput("");
    setAttachments([]);
    setSending(true);
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: text || "(attachments only)",
        attachments: userAttachments.length ? userAttachments : undefined,
      },
    ]);
    setMessages((prev) => [...prev, { role: "assistant", content: "", events: undefined }]);
    setActivities([]);

    let meta = "";
    let lastEvents: Array<{ hook: string; ctx: Record<string, unknown> }> | null = null;
    let lastCost: number | undefined;
    let lastTokens: Record<string, number> | undefined;

    const processor = createStreamProcessor({
      onStatus: (label) => {
        setActivities((prev) => [
          ...prev,
          { id: `a-${++activityIdRef.current}`, kind: "status", label },
        ]);
      },
      onHook: (hook, ctx) => {
        const label = formatHookLabelForActivity(hook, ctx);
        setActivities((prev) => [
          ...prev,
          { id: `a-${++activityIdRef.current}`, kind: "hook", label },
        ]);
      },
      onBudget: (data) => updateFromStream(data),
      onText: (accumulated) => {
        setActivities([]);
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = { ...last, content: accumulated };
          }
          return next;
        });
      },
      onDone: (opts) => {
        setActivities([]);
        lastEvents = opts.events ?? null;
        lastCost = opts.cost;
        lastTokens = opts.tokens;
        const parts: string[] = [];
        if (opts.cost != null) parts.push(`$${Number(opts.cost).toFixed(6)}`);
        if (opts.tokens) {
          const t = opts.tokens.total_tokens ?? opts.tokens.total;
          if (t) parts.push(`${t} tokens`);
        }
        meta = parts.join(" · ");
        const atts: MessageAttachment[] = (opts.attachments ?? []).map((a) => ({
          url: a.url,
          type: a.type,
          contentType: a.content_type,
        }));
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = {
              ...last,
              meta: meta || undefined,
              events: lastEvents ?? undefined,
              cost: opts.cost,
              tokens: opts.tokens,
              attachments: atts.length ? atts : last.attachments,
            };
          }
          return next;
        });
        if (lastEvents && config?.debug) {
          showTrace(lastEvents, lastCost, lastTokens);
        }
        if (opts.budget) {
          updateFromStream(opts.budget);
        } else {
          refreshBudget();
        }
      },
      onError: (err) => {
        setActivities([]);
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = {
              role: "assistant",
              content: `Error: ${err.message}`,
              isError: true,
            };
          }
          return next;
        });
      },
    });

    const body = buildMessageBody(text, userAttachments);

    try {
      const res = await fetch(streamUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: body }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { error?: string }).error || res.statusText || "Request failed");
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      await processor(reader);
    } catch (err) {
      setActivities([]);
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant") {
          next[next.length - 1] = {
            role: "assistant",
            content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
            isError: true,
          };
        }
        return next;
      });
    } finally {
      setSending(false);
    }
  }, [
    input,
    attachments,
    config,
    sending,
    streamUrl,
    buildMessageBody,
    refreshBudget,
    updateFromStream,
    showTrace,
  ]);

  const closeTraceSidebar = useCallback(() => setTraceSidebar(null), []);
  const [agentModalOpen, setAgentModalOpen] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);

  if (loading) {
    return (
      <div className="playground-loading">
        <div className="loading-skeleton" />
        <p className="loading">Loading playground…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="playground-error">
        <p className="error">{error}</p>
        <p className="text-muted">
          Ensure the Syrin server is running and exposes /playground/config.
        </p>
      </div>
    );
  }

  if (!config) return null;

  return (
    <div className="playground">
      <header className="playground-header">
        <div className="playground-logo">
          <AgentIcon size={28} />
          <span className="playground-title">Syrin Playground</span>
        </div>
        <AgentSelector agents={config.agents} value={selectedAgent} onChange={setSelectedAgent} />
        <button
          type="button"
          className="agent-details-btn"
          onClick={() => setAgentModalOpen(true)}
          title="Agent details"
          aria-label="Agent details"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4M12 8h.01" />
          </svg>
          Agent details
        </button>
        <button
          type="button"
          className="agent-details-btn"
          onClick={() => setConfigModalOpen(true)}
          title="Agent config (remote overrides)"
          aria-label="Agent config"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden
          >
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
          </svg>
          Agent config
        </button>
        <BudgetGauge text={formatBudget()} />
      </header>

      <main className="playground-main">
        <ChatArea
          messages={messages}
          activities={activities}
          showPlaceholder={
            sending && messages.length > 0 && messages[messages.length - 1]?.content === ""
          }
          onShowTrace={
            config.debug ? (evts, msg) => showTrace(evts, msg?.cost, msg?.tokens) : undefined
          }
          debug={config.debug}
        />

        <div className="playground-input-wrap">
          <ChatInput
            value={input}
            onChange={setInput}
            onSend={sendMessage}
            disabled={sending}
            placeholder="Type a message or paste/attach an image…"
            attachments={attachments}
            onAttachmentsChange={setAttachments}
          />
        </div>
      </main>

      <AgentDetailsModal
        isOpen={agentModalOpen}
        onClose={() => setAgentModalOpen(false)}
        agents={config.agents}
        selectedAgent={selectedAgent}
        onSelectAgent={setSelectedAgent}
        describe={describe}
        setupType={config.setup_type}
      />
      <AgentConfigModal
        isOpen={configModalOpen}
        onClose={() => setConfigModalOpen(false)}
        apiBase={apiBase}
        agentName={multiAgent ? selectedAgent : undefined}
        agentDisplayName={selectedAgent || config.agents?.[0]?.name}
      />
      {traceSidebar && (
        <TraceSidebar
          events={traceSidebar.events}
          cost={traceSidebar.cost}
          tokens={traceSidebar.tokens}
          onClose={closeTraceSidebar}
          isOpen={!!traceSidebar}
        />
      )}
    </div>
  );
}
