(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([
  [931],
  {
    1187: function (e, t, n) {
      Promise.resolve().then(n.bind(n, 7340));
    },
    7340: function (e, t, n) {
      "use strict";
      (n.r(t),
        n.d(t, {
          default: function () {
            return s;
          },
        }));
      var a = n(7437),
        l = n(2265);
      function s() {
        let [e, t] = (0, l.useState)(null),
          [n, s] = (0, l.useState)(!0),
          [r, o] = (0, l.useState)(null),
          [i, c] = (0, l.useState)(""),
          [u, d] = (0, l.useState)([]),
          [h, g] = (0, l.useState)(""),
          [f, p] = (0, l.useState)(!1),
          [m, v] = (0, l.useState)(null),
          [x, b] = (0, l.useState)(""),
          [k, j] = (0, l.useState)(!1),
          y = (0, l.useCallback)(async () => {
            try {
              var e;
              let n = await fetch("/playground/config");
              if (!n.ok) throw Error("Failed to fetch config");
              let a = await n.json(),
                l = (a.apiBase || "").replace(/\/+$/, "");
              (t({ ...a, apiBase: l ? "".concat(l, "/") : "/" }),
                (null === (e = a.agents) || void 0 === e ? void 0 : e.length) &&
                  c(a.agents[0].name),
                o(null));
            } catch (e) {
              o(e instanceof Error ? e.message : "Could not load config");
            } finally {
              s(!1);
            }
          }, []);
        (0, l.useEffect)(() => {
          y();
        }, [y]);
        let N = (0, l.useCallback)(() => {
            if (!e) return "";
            let t = e.apiBase;
            return e.agents && e.agents.length > 1
              ? "".concat(t).concat(i, "/stream")
              : "".concat(t, "stream");
          }, [e, i]),
          w = (0, l.useCallback)(() => {
            if (!e) return "";
            let t = e.apiBase;
            return e.agents && e.agents.length > 1
              ? "".concat(t).concat(i, "/budget")
              : "".concat(t, "budget");
          }, [e, i]),
          E = (0, l.useCallback)(async () => {
            let e = w();
            if (e)
              try {
                var t;
                let n = await fetch(e);
                if (!n.ok) return;
                let a = await n.json(),
                  l = null !== (t = a.percent_used) && void 0 !== t ? t : 0,
                  s =
                    null != a.spent
                      ? "$".concat(Number(a.spent).toFixed(4))
                      : "",
                  r =
                    null != a.remaining
                      ? "$".concat(Number(a.remaining).toFixed(4))
                      : "";
                v(
                  ""
                    .concat(s, " spent, ")
                    .concat(r, " remaining (")
                    .concat(l.toFixed(1), "% used)"),
                );
              } catch (e) {
                v(null);
              }
          }, [w]);
        (0, l.useEffect)(() => {
          e && E();
        }, [e, i, E]);
        let S = (0, l.useCallback)(
            (t) => {
              (null == e ? void 0 : e.debug) &&
                (null == t ? void 0 : t.length) &&
                (b(JSON.stringify(t, null, 2)), j(!0));
            },
            [null == e ? void 0 : e.debug],
          ),
          C = (0, l.useCallback)(async () => {
            let t = h.trim();
            if (!t || !e || f) return;
            (g(""), p(!0), d((e) => [...e, { role: "user", content: t }]));
            let n = { role: "assistant", content: "" };
            d((e) => [...e, n]);
            let a = "",
              l = null;
            try {
              var s, r, o, i, c, u, m;
              let e = await fetch(N(), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: t }),
              });
              if (!e.ok) {
                let t = await e.json().catch(() => ({}));
                throw Error(t.error || e.statusText || "Request failed");
              }
              let n =
                null === (s = e.body) || void 0 === s ? void 0 : s.getReader();
              if (!n) throw Error("No response body");
              let h = new TextDecoder(),
                g = "";
              for (;;) {
                let { value: e, done: t } = await n.read();
                if (t) break;
                let s = (g += h.decode(e, { stream: !0 })).split("\n");
                for (let e of ((g = s.pop() || ""), s))
                  if (e.startsWith("data: "))
                    try {
                      let t = JSON.parse(e.slice(6));
                      if (t.done) {
                        if (null != t.cost || t.tokens) {
                          let e = [];
                          if (
                            (null != t.cost &&
                              e.push("$".concat(Number(t.cost).toFixed(6))),
                            t.tokens)
                          ) {
                            let n = t.tokens,
                              a =
                                null !==
                                  (i =
                                    null !== (o = n.total_tokens) &&
                                    void 0 !== o
                                      ? o
                                      : n.total) && void 0 !== i
                                  ? i
                                  : (n.input_tokens || 0) +
                                    (n.output_tokens || 0);
                            a && e.push("".concat(a, " tokens"));
                          }
                          a = e.join(" \xb7 ");
                        }
                        (null === (r = t.events) || void 0 === r
                          ? void 0
                          : r.length) && (l = t.events);
                      } else if (null != t.text) {
                        let e =
                          null !== (c = t.accumulated) && void 0 !== c ? c : "";
                        if (
                          (d((t) => {
                            let n = [...t],
                              a = n[n.length - 1];
                            return (
                              (null == a ? void 0 : a.role) === "assistant" &&
                                (n[n.length - 1] = { ...a, content: e }),
                              n
                            );
                          }),
                          null != t.cost || t.tokens)
                        ) {
                          let e = [];
                          if (
                            (null != t.cost &&
                              e.push("$".concat(Number(t.cost).toFixed(6))),
                            t.tokens)
                          ) {
                            let n = t.tokens,
                              a =
                                null !==
                                  (m =
                                    null !== (u = n.total_tokens) &&
                                    void 0 !== u
                                      ? u
                                      : n.total) && void 0 !== m
                                  ? m
                                  : (n.input_tokens || 0) +
                                    (n.output_tokens || 0);
                            a && e.push("".concat(a, " tokens"));
                          }
                          a = e.join(" \xb7 ");
                        }
                      }
                    } catch (e) {}
              }
              (d((e) => {
                let t = [...e],
                  n = t[t.length - 1];
                return (
                  (null == n ? void 0 : n.role) === "assistant" &&
                    (t[t.length - 1] = { ...n, meta: a || void 0 }),
                  t
                );
              }),
                l && S(l),
                E());
            } catch (e) {
              d((t) => {
                let n = [...t],
                  a = n[n.length - 1];
                return (
                  (null == a ? void 0 : a.role) === "assistant" &&
                    (n[n.length - 1] = {
                      role: "assistant",
                      content: "Error: ".concat(
                        e instanceof Error ? e.message : "Unknown error",
                      ),
                      isError: !0,
                    }),
                  n
                );
              });
            } finally {
              p(!1);
            }
          }, [h, e, f, N, E, S]);
        if (n)
          return (0, a.jsx)("div", {
            className: "container",
            children: (0, a.jsx)("p", {
              className: "loading",
              children: "Loading playground…",
            }),
          });
        if (r)
          return (0, a.jsxs)("div", {
            className: "container",
            children: [
              (0, a.jsx)("p", { className: "error", children: r }),
              (0, a.jsx)("p", {
                className: "text-muted",
                children:
                  "Ensure the Syrin server is running and exposes /playground/config.",
              }),
            ],
          });
        if (!e) return null;
        let _ = e.agents && e.agents.length > 1;
        return (0, a.jsxs)("div", {
          className: "container",
          children: [
            (0, a.jsx)("div", {
              className: "header",
              children:
                _ &&
                (0, a.jsxs)("div", {
                  className: "agent-selector",
                  children: [
                    (0, a.jsx)("label", {
                      htmlFor: "agent-select",
                      children: "Agent",
                    }),
                    (0, a.jsx)("select", {
                      id: "agent-select",
                      value: i,
                      onChange: (e) => c(e.target.value),
                      children: e.agents.map((e) => {
                        var t;
                        return (0, a.jsx)(
                          "option",
                          {
                            value: e.name,
                            children:
                              null !== (t = e.description) && void 0 !== t
                                ? t
                                : e.name,
                          },
                          e.name,
                        );
                      }),
                    }),
                  ],
                }),
            }),
            null != m &&
              (0, a.jsx)("div", { className: "budget-gauge", children: m }),
            (0, a.jsxs)("div", {
              className: "chat-area",
              children: [
                (0, a.jsx)("div", {
                  className: "messages",
                  children: u.map((e, t) =>
                    (0, a.jsxs)(
                      "div",
                      {
                        className: "message "
                          .concat(e.role, " ")
                          .concat(e.isError ? "error" : ""),
                        children: [
                          (0, a.jsx)("span", {
                            className: "content",
                            children: e.content,
                          }),
                          e.meta &&
                            (0, a.jsx)("div", {
                              className: "meta",
                              children: e.meta,
                            }),
                        ],
                      },
                      t,
                    ),
                  ),
                }),
                (0, a.jsxs)("div", {
                  className: "input-row",
                  children: [
                    (0, a.jsx)("input", {
                      type: "text",
                      value: h,
                      onChange: (e) => g(e.target.value),
                      onKeyDown: (e) => {
                        "Enter" !== e.key ||
                          e.shiftKey ||
                          (e.preventDefault(), C());
                      },
                      placeholder: "Type a message…",
                      disabled: f,
                    }),
                    (0, a.jsx)("button", {
                      onClick: C,
                      disabled: f,
                      children: "Send",
                    }),
                  ],
                }),
              ],
            }),
            e.debug &&
              (0, a.jsxs)("details", {
                className: "observability-panel",
                open: k,
                onToggle: (e) => j(e.target.open),
                children: [
                  (0, a.jsx)("summary", { children: "Observability (debug)" }),
                  (0, a.jsx)("pre", {
                    children:
                      x || "Events from last response will appear here.",
                  }),
                ],
              }),
          ],
        });
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
