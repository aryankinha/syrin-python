(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([
  [931],
  {
    1187: function (e, n, t) {
      Promise.resolve().then(t.bind(t, 9158));
    },
    9158: function (e, n, t) {
      "use strict";
      (t.r(n),
        t.d(n, {
          default: function () {
            return w;
          },
        }));
      var a = t(7437),
        l = t(2265);
      async function s() {
        let e =
            arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : "",
          n = await fetch("".concat(e || "", "./config"));
        if (!n.ok) throw Error("Failed to fetch config");
        let t = await n.json(),
          a = (t.apiBase || "").replace(/\/+$/, "");
        return { ...t, apiBase: a ? "".concat(a, "/") : "/" };
      }
      async function r(e, n) {
        let t = ""
            .concat(e.replace(/\/$/, ""), "/")
            .concat(n ? "".concat(n, "/describe") : "describe"),
          a = await fetch(t);
        return a.ok ? a.json() : null;
      }
      function i(e) {
        let { className: n = "", size: t = 24 } = e;
        return (0, a.jsxs)("svg", {
          width: t,
          height: t,
          viewBox: "0 0 24 24",
          fill: "none",
          className: "agent-icon ".concat(n),
          "aria-hidden": !0,
          children: [
            (0, a.jsx)("circle", {
              cx: "12",
              cy: "8",
              r: "4",
              stroke: "currentColor",
              strokeWidth: "2",
            }),
            (0, a.jsx)("path", {
              d: "M4 20c0-4 4-6 8-6s8 2 8 6",
              stroke: "currentColor",
              strokeWidth: "2",
              strokeLinecap: "round",
            }),
          ],
        });
      }
      function o(e) {
        let { agents: n, value: t, onChange: l } = e;
        return !n || n.length <= 1
          ? null
          : (0, a.jsxs)("div", {
              className: "agent-selector",
              children: [
                (0, a.jsx)("label", {
                  htmlFor: "agent-select",
                  children: "Agent",
                }),
                (0, a.jsx)("select", {
                  id: "agent-select",
                  value: t,
                  onChange: (e) => l(e.target.value),
                  children: n.map((e) => {
                    var n;
                    return (0, a.jsxs)(
                      "option",
                      {
                        value: e.name,
                        children: [
                          e.name,
                          " — ",
                          null !== (n = e.description) && void 0 !== n ? n : "",
                        ],
                      },
                      e.name,
                    );
                  }),
                }),
              ],
            });
      }
      function c(e) {
        let { text: n, className: t } = e;
        return n
          ? (0, a.jsx)("div", {
              className: "budget-gauge ".concat(null != t ? t : "").trim(),
              children: n,
            })
          : null;
      }
      function d(e) {
        let { onClick: n, title: t = "Info" } = e;
        return (0, a.jsx)("button", {
          type: "button",
          className: "info-btn",
          onClick: (e) => {
            (e.stopPropagation(), n());
          },
          title: t,
          "aria-label": t,
          children: (0, a.jsxs)("svg", {
            width: "14",
            height: "14",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2",
            strokeLinecap: "round",
            strokeLinejoin: "round",
            children: [
              (0, a.jsx)("circle", { cx: "12", cy: "12", r: "10" }),
              (0, a.jsx)("path", { d: "M12 16v-4M12 8h.01" }),
            ],
          }),
        });
      }
      function u(e) {
        let { message: n, onShowTrace: t, debug: l } = e,
          s = l && n.events && n.events.length > 0;
        return (0, a.jsxs)("div", {
          className: "message "
            .concat(n.role, " ")
            .concat(n.isError ? "error" : ""),
          children: [
            (0, a.jsxs)("div", {
              className: "message-header",
              children: [
                (0, a.jsx)("span", {
                  className: "content",
                  children: n.content,
                }),
                s &&
                  t &&
                  (0, a.jsx)(d, {
                    onClick: () => t(n.events),
                    title: "View trace",
                  }),
              ],
            }),
            n.meta &&
              (0, a.jsx)("div", { className: "meta", children: n.meta }),
          ],
        });
      }
      function h() {
        return (0, a.jsx)("div", {
          className: "message assistant placeholder",
          children: (0, a.jsx)("span", {
            className: "content placeholder-content",
            children: "Waiting for response…",
          }),
        });
      }
      function p(e) {
        let { label: n, kind: t = "status" } = e;
        return (0, a.jsxs)("div", {
          className: "activity-item ".concat(t),
          children: [
            "hook" === t &&
              (0, a.jsx)("span", {
                className: "activity-badge",
                children: "[Hook]",
              }),
            (0, a.jsx)("span", { className: "activity-label", children: n }),
          ],
        });
      }
      function m(e) {
        let {
            messages: n,
            activities: t,
            showPlaceholder: s,
            onShowTrace: r,
            debug: i,
          } = e,
          o = (0, l.useRef)(null);
        return (
          (0, l.useEffect)(() => {
            var e;
            null === (e = o.current) ||
              void 0 === e ||
              e.scrollTo({ top: o.current.scrollHeight, behavior: "smooth" });
          }, [n, t, s]),
          (0, a.jsxs)("div", {
            className: "chat-messages",
            ref: o,
            children: [
              n.map((e, n) =>
                (0, a.jsx)(
                  u,
                  {
                    message: e,
                    onShowTrace: r ? (n) => r(n, e) : void 0,
                    debug: i,
                  },
                  n,
                ),
              ),
              t.map((e) =>
                (0, a.jsx)(p, { label: e.label, kind: e.kind }, e.id),
              ),
              s && (0, a.jsx)(h, {}),
            ],
          })
        );
      }
      function g(e) {
        let {
          value: n,
          onChange: t,
          onSend: l,
          disabled: s = !1,
          placeholder: r = "Type a message…",
        } = e;
        return (0, a.jsxs)("div", {
          className: "input-row",
          children: [
            (0, a.jsx)("input", {
              type: "text",
              value: n,
              onChange: (e) => t(e.target.value),
              onKeyDown: (e) => {
                "Enter" !== e.key || e.shiftKey || (e.preventDefault(), l());
              },
              placeholder: r,
              disabled: s,
            }),
            (0, a.jsx)("button", { onClick: l, disabled: s, children: "Send" }),
          ],
        });
      }
      function v(e) {
        let { hook: n, ctx: t } = e,
          l = (function (e, n) {
            var t, a, l, s;
            let r =
                null !== (t = null == n ? void 0 : n.tool) && void 0 !== t
                  ? t
                  : null == n
                    ? void 0
                    : n.tool_name,
              i =
                null !==
                  (l =
                    null !== (a = null == n ? void 0 : n.agent_type) &&
                    void 0 !== a
                      ? a
                      : null == n
                        ? void 0
                        : n.agent) && void 0 !== l
                  ? l
                  : null == n
                    ? void 0
                    : n.agent_name,
              o =
                null !== (s = null == n ? void 0 : n.model) && void 0 !== s
                  ? s
                  : null == n
                    ? void 0
                    : n.model_name;
            switch (e) {
              case "agent.run.start":
                return "Agent run started";
              case "agent.run.end":
                return "Agent run complete";
              case "agent.init":
                return "Agent init";
              case "llm.request.start":
                return o ? "LLM: ".concat(o) : "LLM started";
              case "llm.request.end":
                return "LLM complete";
              case "tool.call.start":
                return r ? 'Tool "'.concat(r, '"') : "Tool called";
              case "tool.call.end":
                return r ? 'Tool "'.concat(r, '" done') : "Tool complete";
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
              case "memory.store":
              case "memory.recall":
              case "memory.forget":
              case "checkpoint.save":
              case "checkpoint.load":
              case "pipeline.start":
              case "pipeline.end":
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
                return e.replace(/\./g, " ");
              case "dynamic.pipeline.start":
                return "Dynamic pipeline start";
              case "dynamic.pipeline.plan":
                return "Dynamic pipeline plan";
              case "dynamic.pipeline.execute":
                return "Dynamic pipeline execute";
              case "dynamic.pipeline.agent.spawn":
                return i ? 'Spawned "'.concat(i, '"') : "Agent spawned";
              case "dynamic.pipeline.agent.complete":
                return i ? '"'.concat(i, '" complete') : "Agent complete";
              case "dynamic.pipeline.end":
                return "Dynamic pipeline end";
              case "dynamic.pipeline.error":
                return "Dynamic pipeline error";
              case "pipeline.agent.start":
                return i ? "Pipeline: ".concat(i) : "Pipeline started";
              case "pipeline.agent.complete":
                return i ? "".concat(i, " done") : "Pipeline complete";
              default:
                return e
                  .replace(/\./g, " ")
                  .replace(/\b\w/g, (e) => e.toUpperCase());
            }
          })(n, t),
          s = Object.keys(t).filter(
            (e) => !["tokens", "token_usage"].includes(e) && null != t[e],
          );
        return (0, a.jsxs)("div", {
          className: "trace-event-card",
          children: [
            (0, a.jsx)("div", { className: "trace-event-label", children: l }),
            s.length > 0 &&
              (0, a.jsx)("div", {
                className: "trace-event-ctx",
                children: s.map((e) =>
                  (0, a.jsxs)(
                    "div",
                    {
                      className: "trace-event-row",
                      children: [
                        (0, a.jsxs)("span", {
                          className: "trace-event-key",
                          children: [e, ":"],
                        }),
                        (0, a.jsx)("span", {
                          className: "trace-event-val",
                          children:
                            "object" == typeof t[e]
                              ? JSON.stringify(t[e])
                              : String(t[e]),
                        }),
                      ],
                    },
                    e,
                  ),
                ),
              }),
          ],
        });
      }
      function x(e) {
        var n, t, l, s;
        let { events: r, cost: i, tokens: o, onClose: c, isOpen: d } = e;
        if (!d) return null;
        let u =
          null !==
            (s =
              null !== (n = null == o ? void 0 : o.total_tokens) && void 0 !== n
                ? n
                : null == o
                  ? void 0
                  : o.total) && void 0 !== s
            ? s
            : (null !== (t = null == o ? void 0 : o.input_tokens) &&
              void 0 !== t
                ? t
                : 0) +
              (null !== (l = null == o ? void 0 : o.output_tokens) &&
              void 0 !== l
                ? l
                : 0);
        return (0, a.jsxs)(a.Fragment, {
          children: [
            (0, a.jsx)("div", {
              className: "trace-sidebar-overlay",
              onClick: c,
              "aria-hidden": "true",
            }),
            (0, a.jsxs)("aside", {
              className: "trace-sidebar",
              role: "dialog",
              "aria-label": "Reply trace",
              children: [
                (0, a.jsxs)("div", {
                  className: "trace-sidebar-header",
                  children: [
                    (0, a.jsx)("h3", { children: "Reply trace" }),
                    (0, a.jsx)("button", {
                      type: "button",
                      className: "trace-sidebar-close",
                      onClick: c,
                      "aria-label": "Close",
                      children: "\xd7",
                    }),
                  ],
                }),
                (0, a.jsxs)("div", {
                  className: "trace-sidebar-body",
                  children: [
                    (null != i || u > 0) &&
                      (0, a.jsxs)("div", {
                        className: "trace-meta-cards",
                        children: [
                          null != i &&
                            (0, a.jsxs)("div", {
                              className: "trace-meta-card",
                              children: [
                                (0, a.jsx)("span", {
                                  className: "trace-meta-label",
                                  children: "Cost",
                                }),
                                (0, a.jsxs)("span", {
                                  className: "trace-meta-val",
                                  children: ["$", Number(i).toFixed(6)],
                                }),
                              ],
                            }),
                          u > 0 &&
                            (0, a.jsxs)("div", {
                              className: "trace-meta-card",
                              children: [
                                (0, a.jsx)("span", {
                                  className: "trace-meta-label",
                                  children: "Tokens",
                                }),
                                (0, a.jsx)("span", {
                                  className: "trace-meta-val",
                                  children: u,
                                }),
                              ],
                            }),
                        ],
                      }),
                    (0, a.jsx)("div", {
                      className: "trace-events-list",
                      children: r.map((e, n) =>
                        (0, a.jsx)(v, { hook: e.hook, ctx: e.ctx }, n),
                      ),
                    }),
                  ],
                }),
              ],
            }),
          ],
        });
      }
      let j = () =>
          (0, a.jsxs)("svg", {
            width: "16",
            height: "16",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2",
            strokeLinecap: "round",
            strokeLinejoin: "round",
            "aria-hidden": !0,
            children: [
              (0, a.jsx)("circle", { cx: "12", cy: "12", r: "10" }),
              (0, a.jsx)("path", { d: "M12 16v-4M12 8h.01" }),
            ],
          }),
        f = () =>
          (0, a.jsx)("svg", {
            width: "16",
            height: "16",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2",
            strokeLinecap: "round",
            strokeLinejoin: "round",
            "aria-hidden": !0,
            children: (0, a.jsx)("path", {
              d: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z",
            }),
          }),
        y = () =>
          (0, a.jsxs)("svg", {
            width: "16",
            height: "16",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2",
            strokeLinecap: "round",
            strokeLinejoin: "round",
            "aria-hidden": !0,
            children: [
              (0, a.jsx)("rect", {
                x: "1",
                y: "4",
                width: "22",
                height: "16",
                rx: "2",
                ry: "2",
              }),
              (0, a.jsx)("path", { d: "M1 10h22" }),
            ],
          }),
        k = () =>
          (0, a.jsxs)("svg", {
            width: "16",
            height: "16",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2",
            strokeLinecap: "round",
            strokeLinejoin: "round",
            "aria-hidden": !0,
            children: [
              (0, a.jsx)("path", {
                d: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2",
              }),
              (0, a.jsx)("circle", { cx: "9", cy: "7", r: "4" }),
              (0, a.jsx)("path", {
                d: "M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
              }),
            ],
          }),
        b = () =>
          (0, a.jsx)("svg", {
            width: "16",
            height: "16",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2",
            strokeLinecap: "round",
            strokeLinejoin: "round",
            "aria-hidden": !0,
            children: (0, a.jsx)("path", {
              d: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 17h6M17 14v6M14 14h.01",
            }),
          });
      function N(e) {
        var n, t, l, s, r, o, c;
        let {
          isOpen: d,
          onClose: u,
          agents: h,
          selectedAgent: p,
          onSelectAgent: m,
          describe: g,
          setupType: v,
        } = e;
        if (!d) return null;
        let x = null == g ? void 0 : g.tools,
          N = Array.isArray(x)
            ? x.map((e) =>
                "string" == typeof e ? { name: e, description: "" } : e,
              )
            : [],
          w = h && h.length > 1,
          C =
            null !== (n = null == g ? void 0 : g.internal_agents) &&
            void 0 !== n
              ? n
              : [],
          S = "dynamic_pipeline" === v || C.length > 0,
          L = h.find((e) => e.name === p),
          M =
            null !==
              (s =
                null !==
                  (l =
                    null !== (t = null == g ? void 0 : g.name) && void 0 !== t
                      ? t
                      : null == L
                        ? void 0
                        : L.name) && void 0 !== l
                  ? l
                  : p) && void 0 !== s
              ? s
              : "Agent";
        return (0, a.jsxs)(a.Fragment, {
          children: [
            (0, a.jsx)("div", {
              className: "modal-overlay",
              onClick: u,
              "aria-hidden": "true",
            }),
            (0, a.jsxs)("aside", {
              className: "agent-details-modal",
              role: "dialog",
              "aria-label": "Agent details",
              children: [
                (0, a.jsxs)("div", {
                  className: "modal-header",
                  children: [
                    (0, a.jsxs)("div", {
                      className: "modal-title-row",
                      children: [
                        (0, a.jsx)(i, { size: 22 }),
                        (0, a.jsxs)("div", {
                          className: "modal-title-wrap",
                          children: [
                            (0, a.jsx)("h2", {
                              className: "modal-agent-name",
                              children: M,
                            }),
                            (0, a.jsx)("span", {
                              className: "modal-subtitle",
                              children: "Agent details",
                            }),
                          ],
                        }),
                      ],
                    }),
                    (0, a.jsx)("button", {
                      type: "button",
                      className: "modal-close",
                      onClick: u,
                      "aria-label": "Close",
                      children: "\xd7",
                    }),
                  ],
                }),
                (0, a.jsxs)("div", {
                  className: "modal-body",
                  children: [
                    w &&
                      (0, a.jsxs)("div", {
                        className: "modal-section modal-section-icon",
                        children: [
                          (0, a.jsxs)("label", {
                            children: [
                              (0, a.jsx)(k, {}),
                              (0, a.jsx)("span", { children: "Select agent" }),
                            ],
                          }),
                          (0, a.jsx)("p", {
                            className: "modal-hint",
                            children:
                              "You can switch between agents and talk to each one directly.",
                          }),
                          (0, a.jsx)("select", {
                            value: p,
                            onChange: (e) => m(e.target.value),
                            className: "agent-select-in-modal",
                            children: h.map((e) => {
                              var n;
                              return (0, a.jsxs)(
                                "option",
                                {
                                  value: e.name,
                                  children: [
                                    e.name,
                                    " — ",
                                    null !== (n = e.description) && void 0 !== n
                                      ? n
                                      : "",
                                  ],
                                },
                                e.name,
                              );
                            }),
                          }),
                        ],
                      }),
                    S &&
                      C.length > 0 &&
                      (0, a.jsxs)("div", {
                        className: "modal-section modal-section-icon",
                        children: [
                          (0, a.jsxs)("label", {
                            children: [
                              (0, a.jsx)(b, {}),
                              (0, a.jsx)("span", {
                                children:
                                  "Internal agents (used automatically)",
                              }),
                            ],
                          }),
                          (0, a.jsxs)("p", {
                            className: "modal-hint",
                            children: [
                              "These ",
                              C.length,
                              " agents are invoked internally by the orchestrator based on your request. You chat with the orchestrator; it decides which agents to use.",
                            ],
                          }),
                          (0, a.jsx)("ul", {
                            className: "internal-agents-list",
                            children: C.map((e) =>
                              (0, a.jsxs)(
                                "li",
                                {
                                  children: [
                                    (0, a.jsx)(i, { size: 14 }),
                                    (0, a.jsx)("span", { children: e }),
                                  ],
                                },
                                e,
                              ),
                            ),
                          }),
                        ],
                      }),
                    g &&
                      (0, a.jsxs)(a.Fragment, {
                        children: [
                          (0, a.jsxs)("div", {
                            className: "modal-section modal-section-icon",
                            children: [
                              (0, a.jsxs)("label", {
                                children: [
                                  (0, a.jsx)(j, {}),
                                  (0, a.jsx)("span", {
                                    children: "Description",
                                  }),
                                ],
                              }),
                              (0, a.jsx)("p", {
                                className: "modal-desc",
                                children: g.description || "No description.",
                              }),
                            ],
                          }),
                          N.length > 0 &&
                            (0, a.jsxs)("div", {
                              className: "modal-section modal-section-icon",
                              children: [
                                (0, a.jsxs)("label", {
                                  children: [
                                    (0, a.jsx)(f, {}),
                                    (0, a.jsx)("span", { children: "Tools" }),
                                  ],
                                }),
                                (0, a.jsx)("ul", {
                                  className: "tool-list",
                                  children: N.map((e, n) =>
                                    (0, a.jsxs)(
                                      "li",
                                      {
                                        children: [
                                          (0, a.jsx)("code", {
                                            children: e.name,
                                          }),
                                          e.description &&
                                            (0, a.jsxs)("span", {
                                              children: [" — ", e.description],
                                            }),
                                        ],
                                      },
                                      n,
                                    ),
                                  ),
                                }),
                              ],
                            }),
                          g.budget &&
                            (0, a.jsxs)("div", {
                              className: "modal-section modal-section-icon",
                              children: [
                                (0, a.jsxs)("label", {
                                  children: [
                                    (0, a.jsx)(y, {}),
                                    (0, a.jsx)("span", { children: "Budget" }),
                                  ],
                                }),
                                (0, a.jsxs)("div", {
                                  className: "budget-stats",
                                  children: [
                                    (0, a.jsxs)("span", {
                                      children: [
                                        "Spent: $",
                                        Number(
                                          null !== (r = g.budget.spent) &&
                                            void 0 !== r
                                            ? r
                                            : 0,
                                        ).toFixed(4),
                                      ],
                                    }),
                                    (0, a.jsxs)("span", {
                                      children: [
                                        "Remaining: $",
                                        Number(
                                          null !== (o = g.budget.remaining) &&
                                            void 0 !== o
                                            ? o
                                            : 0,
                                        ).toFixed(4),
                                      ],
                                    }),
                                    (0, a.jsxs)("span", {
                                      children: [
                                        Number(
                                          null !==
                                            (c = g.budget.percent_used) &&
                                            void 0 !== c
                                            ? c
                                            : 0,
                                        ).toFixed(1),
                                        "% used",
                                      ],
                                    }),
                                  ],
                                }),
                              ],
                            }),
                        ],
                      }),
                  ],
                }),
              ],
            }),
          ],
        });
      }
      function w() {
        var e, n;
        let {
            config: t,
            loading: d,
            error: u,
          } = (function () {
            let [e, n] = (0, l.useState)(null),
              [t, a] = (0, l.useState)(!0),
              [r, i] = (0, l.useState)(null),
              o = (0, l.useCallback)(async () => {
                try {
                  let e = await s();
                  (n(e), i(null));
                } catch (e) {
                  i(e instanceof Error ? e.message : "Could not load config");
                } finally {
                  a(!1);
                }
              }, []);
            return (
              (0, l.useEffect)(() => {
                o();
              }, [o]),
              { config: e, loading: t, error: r }
            );
          })(),
          [h, p] = (0, l.useState)(""),
          [v, j] = (0, l.useState)([]),
          [f, y] = (0, l.useState)(""),
          [k, b] = (0, l.useState)(!1),
          [w, C] = (0, l.useState)([]),
          [S, L] = (0, l.useState)(null),
          M = (0, l.useRef)(0),
          T =
            null !== (n = null == t ? void 0 : t.apiBase) && void 0 !== n
              ? n
              : "",
          _ = (null == t ? void 0 : t.agents) && t.agents.length > 1 ? h : "",
          {
            formatBudget: E,
            refresh: A,
            updateFromStream: B,
          } = (function (e, n, t) {
            let [a, s] = (0, l.useState)(null),
              r = (0, l.useRef)(null),
              i = (0, l.useCallback)(async () => {
                if (!e || !t || !1 === r.current) return;
                let a = n ? "".concat(n, "/budget") : "budget",
                  l = "".concat(e.replace(/\/$/, ""), "/").concat(a);
                try {
                  let e = await fetch(l);
                  if (404 === e.status) {
                    ((r.current = !1), s(null));
                    return;
                  }
                  if (!e.ok) return;
                  let n = await e.json();
                  ((r.current = !0), s(n));
                } catch (e) {
                  s(null);
                }
              }, [e, n, t]),
              o = (0, l.useCallback)((e) => {
                ((r.current = null != e), s(e));
              }, []);
            return (
              (0, l.useEffect)(() => {
                ((r.current = null), s(null), t && i());
              }, [t, n, i]),
              {
                budget: a,
                formatBudget: () => {
                  var e;
                  if (!a) return null;
                  let n = null !== (e = a.percent_used) && void 0 !== e ? e : 0,
                    t =
                      null != a.spent
                        ? "$".concat(Number(a.spent).toFixed(4))
                        : "",
                    l =
                      null != a.remaining
                        ? "$".concat(Number(a.remaining).toFixed(4))
                        : "";
                  return ""
                    .concat(t, " spent \xb7 ")
                    .concat(l, " remaining (")
                    .concat(n.toFixed(1), "% used)");
                },
                refresh: i,
                updateFromStream: o,
              }
            );
          })(T, _, !!t),
          { describe: D } = (function (e, n, t) {
            let [a, s] = (0, l.useState)(null),
              i = (0, l.useCallback)(async () => {
                e && t && s(await r(e, n || void 0));
              }, [e, n, t]);
            return (
              (0, l.useEffect)(() => {
                i();
              }, [i]),
              { describe: a, refresh: i }
            );
          })(T, _, !!t);
        (0, l.useEffect)(() => {
          var e;
          (null == t
            ? void 0
            : null === (e = t.agents) || void 0 === e
              ? void 0
              : e.length) &&
            !h &&
            p(t.agents[0].name);
        }, [null == t ? void 0 : t.agents, h]);
        let F = t
            ? t.agents && t.agents.length > 1
              ? "".concat(T).concat(h, "/stream")
              : "".concat(T, "stream")
            : "",
          P = (0, l.useCallback)((e, n, t) => {
            L({ events: e, cost: n, tokens: t });
          }, []),
          H = (0, l.useCallback)(async () => {
            var e, n;
            let a, l;
            let s = f.trim();
            if (!s || !t || k) return;
            (y(""),
              b(!0),
              j((e) => [...e, { role: "user", content: s }]),
              j((e) => [
                ...e,
                { role: "assistant", content: "", events: void 0 },
              ]),
              C([]));
            let r = "",
              i = null,
              o =
                ((e = {
                  onStatus: (e) => {
                    C((n) => [
                      ...n,
                      {
                        id: "a-".concat(++M.current),
                        kind: "status",
                        label: e,
                      },
                    ]);
                  },
                  onHook: (e, n) => {
                    let t = (function (e, n) {
                      var t, a, l, s, r;
                      let i =
                          null !== (t = null == n ? void 0 : n.tool) &&
                          void 0 !== t
                            ? t
                            : null == n
                              ? void 0
                              : n.tool_name,
                        o =
                          null !==
                            (l =
                              null !==
                                (a = null == n ? void 0 : n.agent_type) &&
                              void 0 !== a
                                ? a
                                : null == n
                                  ? void 0
                                  : n.agent) && void 0 !== l
                            ? l
                            : null == n
                              ? void 0
                              : n.agent_name,
                        c =
                          null !== (s = null == n ? void 0 : n.model) &&
                          void 0 !== s
                            ? s
                            : null == n
                              ? void 0
                              : n.model_name,
                        d =
                          null !== (r = null == n ? void 0 : n.remaining) &&
                          void 0 !== r
                            ? r
                            : null == n
                              ? void 0
                              : n.budget_remaining,
                        u = null == n ? void 0 : n.task;
                      switch (e) {
                        case "agent.run.start":
                          return "Agent run started";
                        case "agent.run.end":
                          return "Agent run complete";
                        case "agent.init":
                          return "Agent initialized";
                        case "agent.reset":
                          return "Agent reset";
                        case "llm.request.start":
                          return c ? "LLM: ".concat(c) : "LLM call started";
                        case "llm.request.end":
                          return "LLM call complete";
                        case "llm.retry":
                          return "LLM retry";
                        case "llm.fallback":
                          return "LLM fallback";
                        case "tool.call.start":
                          return i
                            ? 'Tool "'.concat(i, '" called')
                            : "Tool called";
                        case "tool.call.end":
                          return i
                            ? 'Tool "'.concat(i, '" complete')
                            : "Tool complete";
                        case "tool.error":
                          return i
                            ? 'Tool "'.concat(i, '" error')
                            : "Tool error";
                        case "budget.check":
                          return "Budget check";
                        case "budget.threshold":
                          return null != d
                            ? "Cost threshold ($".concat(
                                Number(d).toFixed(2),
                                " remaining)",
                              )
                            : "Cost threshold hit";
                        case "budget.exceeded":
                          return "Budget exceeded";
                        case "guardrail.input":
                          return "Guardrail input";
                        case "guardrail.output":
                          return "Guardrail output";
                        case "guardrail.blocked":
                          return "Guardrail blocked";
                        case "memory.store":
                          return "Memory store";
                        case "memory.recall":
                          return "Memory recall";
                        case "memory.forget":
                          return "Memory forget";
                        case "checkpoint.save":
                          return "Checkpoint save";
                        case "checkpoint.load":
                          return "Checkpoint load";
                        case "dynamic.pipeline.start":
                          return u
                            ? "Dynamic pipeline: ".concat(
                                String(u).slice(0, 40),
                                "...",
                              )
                            : "Dynamic pipeline start";
                        case "dynamic.pipeline.plan":
                          return "Dynamic pipeline plan";
                        case "dynamic.pipeline.execute":
                          return "Dynamic pipeline execute";
                        case "dynamic.pipeline.agent.spawn":
                          return o
                            ? 'Spawned "'.concat(o, '"')
                            : "Agent spawned";
                        case "dynamic.pipeline.agent.complete":
                          return o
                            ? '"'.concat(o, '" complete')
                            : "Agent complete";
                        case "dynamic.pipeline.end":
                          return "Dynamic pipeline end";
                        case "dynamic.pipeline.error":
                          return "Dynamic pipeline error";
                        case "pipeline.start":
                          return "Pipeline start";
                        case "pipeline.end":
                          return "Pipeline end";
                        case "pipeline.agent.start":
                          return o
                            ? "Pipeline: ".concat(o)
                            : "Pipeline agent started";
                        case "pipeline.agent.complete":
                          return o
                            ? "Pipeline: ".concat(o, " done")
                            : "Pipeline agent complete";
                        case "handoff.start":
                          return "Handoff start";
                        case "handoff.end":
                          return "Handoff end";
                        case "spawn.start":
                          return "Spawn start";
                        case "spawn.end":
                          return "Spawn end";
                        case "hitl.pending":
                          return "Human-in-the-loop pending";
                        case "hitl.approved":
                          return "Human-in-the-loop approved";
                        case "hitl.rejected":
                          return "Human-in-the-loop rejected";
                        case "output.validation.start":
                          return "Output validation start";
                        case "output.validation.success":
                          return "Output validation success";
                        case "output.validation.failed":
                          return "Output validation failed";
                        default:
                          return e
                            .replace(/\./g, " ")
                            .replace(/\b\w/g, (e) => e.toUpperCase());
                      }
                    })(e, n);
                    C((e) => [
                      ...e,
                      { id: "a-".concat(++M.current), kind: "hook", label: t },
                    ]);
                  },
                  onBudget: (e) => B(e),
                  onText: (e) => {
                    (C([]),
                      j((n) => {
                        let t = [...n],
                          a = t[t.length - 1];
                        return (
                          (null == a ? void 0 : a.role) === "assistant" &&
                            (t[t.length - 1] = { ...a, content: e }),
                          t
                        );
                      }));
                  },
                  onDone: (e) => {
                    var n, s;
                    (C([]),
                      (i = null !== (n = e.events) && void 0 !== n ? n : null),
                      (a = e.cost),
                      (l = e.tokens));
                    let o = [];
                    if (
                      (null != e.cost &&
                        o.push("$".concat(Number(e.cost).toFixed(6))),
                      e.tokens)
                    ) {
                      let n =
                        null !== (s = e.tokens.total_tokens) && void 0 !== s
                          ? s
                          : e.tokens.total;
                      n && o.push("".concat(n, " tokens"));
                    }
                    ((r = o.join(" \xb7 ")),
                      j((n) => {
                        let t = [...n],
                          a = t[t.length - 1];
                        return (
                          (null == a ? void 0 : a.role) === "assistant" &&
                            (t[t.length - 1] = {
                              ...a,
                              meta: r || void 0,
                              events: null != i ? i : void 0,
                              cost: e.cost,
                              tokens: e.tokens,
                            }),
                          t
                        );
                      }),
                      i && (null == t ? void 0 : t.debug) && P(i, a, l),
                      e.budget ? B(e.budget) : A());
                  },
                  onError: (e) => {
                    (C([]),
                      j((n) => {
                        let t = [...n],
                          a = t[t.length - 1];
                        return (
                          (null == a ? void 0 : a.role) === "assistant" &&
                            (t[t.length - 1] = {
                              role: "assistant",
                              content: "Error: ".concat(e.message),
                              isError: !0,
                            }),
                          t
                        );
                      }));
                  },
                }),
                async (n) => {
                  let t = new TextDecoder(),
                    a = "";
                  try {
                    for (;;) {
                      let { value: r, done: i } = await n.read();
                      if (i) break;
                      let o = (a += t.decode(r, { stream: !0 })).split("\n");
                      for (let n of ((a = o.pop() || ""), o)) {
                        var l, s;
                        let t = (function (e) {
                          if (!e.startsWith("data: ")) return null;
                          try {
                            return JSON.parse(e.slice(6));
                          } catch (e) {
                            return null;
                          }
                        })(n);
                        if (!t) continue;
                        let a = t.type;
                        if ("status" === a) {
                          let n = t.message;
                          n && e.onStatus(n);
                          continue;
                        }
                        if ("hook" === a) {
                          let { hook: n, ctx: a } = t;
                          e.onHook(n, a || {});
                          continue;
                        }
                        if ("budget" === a) {
                          e.onBudget && e.onBudget(t);
                          continue;
                        }
                        if ("done" === a) {
                          e.onDone({
                            cost: t.cost,
                            tokens: t.tokens,
                            events: t.events,
                            budget: t.budget,
                          });
                          continue;
                        }
                        if ("text" === a) {
                          let n =
                            null !== (l = t.accumulated) && void 0 !== l
                              ? l
                              : "";
                          e.onText(n);
                          continue;
                        }
                        if (t.done)
                          e.onDone({
                            cost: t.cost,
                            tokens: t.tokens,
                            events: t.events,
                            budget: t.budget,
                          });
                        else if (null != t.text) {
                          let n =
                            null !== (s = t.accumulated) && void 0 !== s
                              ? s
                              : "";
                          e.onText(n);
                        }
                      }
                    }
                  } catch (n) {
                    e.onError(n instanceof Error ? n : Error(String(n)));
                  }
                });
            try {
              let e = await fetch(F, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: s }),
              });
              if (!e.ok) {
                let n = await e.json().catch(() => ({}));
                throw Error(n.error || e.statusText || "Request failed");
              }
              let t =
                null === (n = e.body) || void 0 === n ? void 0 : n.getReader();
              if (!t) throw Error("No response body");
              await o(t);
            } catch (e) {
              (C([]),
                j((n) => {
                  let t = [...n],
                    a = t[t.length - 1];
                  return (
                    (null == a ? void 0 : a.role) === "assistant" &&
                      (t[t.length - 1] = {
                        role: "assistant",
                        content: "Error: ".concat(
                          e instanceof Error ? e.message : "Unknown error",
                        ),
                        isError: !0,
                      }),
                    t
                  );
                }));
            } finally {
              b(!1);
            }
          }, [f, t, k, F, A, B, P]),
          O = (0, l.useCallback)(() => L(null), []),
          [W, $] = (0, l.useState)(!1);
        return d
          ? (0, a.jsxs)("div", {
              className: "playground-loading",
              children: [
                (0, a.jsx)("div", { className: "loading-skeleton" }),
                (0, a.jsx)("p", {
                  className: "loading",
                  children: "Loading playground…",
                }),
              ],
            })
          : u
            ? (0, a.jsxs)("div", {
                className: "playground-error",
                children: [
                  (0, a.jsx)("p", { className: "error", children: u }),
                  (0, a.jsx)("p", {
                    className: "text-muted",
                    children:
                      "Ensure the Syrin server is running and exposes /playground/config.",
                  }),
                ],
              })
            : t
              ? (0, a.jsxs)("div", {
                  className: "playground",
                  children: [
                    (0, a.jsxs)("header", {
                      className: "playground-header",
                      children: [
                        (0, a.jsxs)("div", {
                          className: "playground-logo",
                          children: [
                            (0, a.jsx)(i, { size: 28 }),
                            (0, a.jsx)("span", {
                              className: "playground-title",
                              children: "Syrin Playground",
                            }),
                          ],
                        }),
                        (0, a.jsx)(o, {
                          agents: t.agents,
                          value: h,
                          onChange: p,
                        }),
                        (0, a.jsxs)("button", {
                          type: "button",
                          className: "agent-details-btn",
                          onClick: () => $(!0),
                          title: "Agent details",
                          "aria-label": "Agent details",
                          children: [
                            (0, a.jsxs)("svg", {
                              width: "16",
                              height: "16",
                              viewBox: "0 0 24 24",
                              fill: "none",
                              stroke: "currentColor",
                              strokeWidth: "2",
                              "aria-hidden": !0,
                              children: [
                                (0, a.jsx)("circle", {
                                  cx: "12",
                                  cy: "12",
                                  r: "10",
                                }),
                                (0, a.jsx)("path", { d: "M12 16v-4M12 8h.01" }),
                              ],
                            }),
                            "Agent details",
                          ],
                        }),
                        (0, a.jsx)(c, { text: E() }),
                      ],
                    }),
                    (0, a.jsxs)("main", {
                      className: "playground-main",
                      children: [
                        (0, a.jsx)(m, {
                          messages: v,
                          activities: w,
                          showPlaceholder:
                            k &&
                            v.length > 0 &&
                            (null === (e = v[v.length - 1]) || void 0 === e
                              ? void 0
                              : e.content) === "",
                          onShowTrace: t.debug
                            ? (e, n) =>
                                P(
                                  e,
                                  null == n ? void 0 : n.cost,
                                  null == n ? void 0 : n.tokens,
                                )
                            : void 0,
                          debug: t.debug,
                        }),
                        (0, a.jsx)("div", {
                          className: "playground-input-wrap",
                          children: (0, a.jsx)(g, {
                            value: f,
                            onChange: y,
                            onSend: H,
                            disabled: k,
                            placeholder: "Type a message…",
                          }),
                        }),
                      ],
                    }),
                    (0, a.jsx)(N, {
                      isOpen: W,
                      onClose: () => $(!1),
                      agents: t.agents,
                      selectedAgent: h,
                      onSelectAgent: p,
                      describe: D,
                      setupType: t.setup_type,
                    }),
                    S &&
                      (0, a.jsx)(x, {
                        events: S.events,
                        cost: S.cost,
                        tokens: S.tokens,
                        onClose: O,
                        isOpen: !!S,
                      }),
                  ],
                })
              : null;
      }
    },
  },
  function (e) {
    (e.O(0, [971, 117, 744], function () {
      return e((e.s = 1187));
    }),
      (_N_E = e.O()));
  },
]);
