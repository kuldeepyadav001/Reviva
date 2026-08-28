import { useEffect, useMemo, useState } from "react";

const SERVICES = [
  ["ingest", "/api/ingest/health"],
  ["simulator", "/api/simulator/health"],
  ["diagnosis", "/api/diagnosis/health"],
  ["policy", "/api/policy/health"],
  ["executor", "/api/executor/health"],
];

const GATES = {
  quiet_hours_ist_2100_0900: "Night in India (9pm–9am). We do not message customers then.",
  max_3_attempts_per_customer_day: "Already 3 recovery tries today for this customer. Stopped.",
  duplicate_payment_link_guard: "A link for this amount already exists. We will not send another.",
  amount_gt_10000_needs_approval: "Over ₹10,000 — a person must approve before any retry or link.",
  env_kill_switch: "Kill switch is on. The agent is frozen.",
  redis_kill_switch: "Kill switch is on. The agent is frozen.",
  merchant_kill_switch: "This merchant paused recovery.",
  unmapped_cause: "No playbook for this cause.",
};

function titleFor(a) {
  if (a.status === "pending_approval" && a.block_reason === "amount_gt_10000_needs_approval") {
    return "Waiting for a person (large amount)";
  }
  if (a.status === "pending_approval" || a.action_type === "hold_manual_review") {
    return "Held — we refused to guess";
  }
  if (a.status === "blocked" || a.action_type === "none") {
    return "Stopped by a safety rule";
  }
  const map = {
    schedule_retry_backoff: "Wait, then retry (bank looks down)",
    schedule_retry_balance_window: "Wait for money to land",
    send_payment_link: "New checkout session",
    send_single_reminder_link: "One reminder only",
  };
  return map[a.action_type] || a.action_type;
}

function sourceHuman(src) {
  if (!src) return "";
  if (src.startsWith("rule:")) {
    return `Rules recognised a known Razorpay error (${src.slice(5)}). The AI model was not asked.`;
  }
  if (src === "llm_error") {
    return "The error text was unfamiliar, so we asked the local model. Ollama in this project did not answer — usually the model is not pulled in Reviva’s container (it does not share the other project’s Ollama). We did not invent a cause and we did not contact the customer.";
  }
  if (src === "llm_low_confidence") return "The local model was under 60% sure. Held.";
  if (src.startsWith("llm")) return "Unfamiliar error — local model classified it.";
  if (src === "simulator") return "Practice score for this batch. Not money in a bank account.";
  if (src === "gate") return "A safety rule ran before any customer message.";
  return src;
}

function fmtMoney(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function badgeClass(status) {
  if (status === "executed") return "ok";
  if (status === "blocked") return "bad";
  return "warn";
}

function badgeLabel(status) {
  if (status === "pending_approval") return "needs a person";
  if (status === "scheduled") return "waiting";
  if (status === "blocked") return "stopped";
  if (status === "executed") return "done";
  return status;
}

export default function App() {
  const [page, setPage] = useState("ledger");
  const [status, setStatus] = useState({});
  const [metrics, setMetrics] = useState(null);
  const [actions, setActions] = useState([]);
  const [audit, setAudit] = useState([]);
  const [sel, setSel] = useState(null);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [n, setN] = useState(20);
  const [frozen, setFrozen] = useState(false);
  const [lastBatch, setLastBatch] = useState(null);

  const refresh = () => {
    SERVICES.forEach(([name, path]) => {
      fetch(path)
        .then((r) => r.json())
        .then((j) => setStatus((s) => ({ ...s, [name]: j })))
        .catch(() => setStatus((s) => ({ ...s, [name]: { ok: false } })));
    });
    fetch("/api/executor/metrics")
      .then((r) => r.json())
      .then(setMetrics)
      .catch(() => {});
    fetch("/api/executor/actions")
      .then((r) => r.json())
      .then((rows) => setActions(Array.isArray(rows) ? rows : []))
      .catch(() => {});
    fetch("/api/policy/ops/kill-switch")
      .then((r) => r.json())
      .then((j) => setFrozen(Boolean(j.kill_switch)))
      .catch(() => {});
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 6000);
    return () => clearInterval(t);
  }, []);

  const open = async (a) => {
    setSel(a);
    setPage("ledger");
    setAudit([]);
    try {
      const r = await fetch(`/api/executor/audit/${a.event_id}`);
      const j = await r.json();
      setAudit(Array.isArray(j) ? j : []);
    } catch {
      setAudit([]);
    }
  };

  const runBatch = async () => {
    setBusy(true);
    setErr("");
    try {
      const r = await fetch(`/api/simulator/run-batch?n=${n}`, { method: "POST" });
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`Could not run batch (${r.status}). ${t.slice(0, 160)}`);
      }
      const body = await r.json();
      setLastBatch(body);
      await refresh();
      setPage("ledger");
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const kill = async (on) => {
    await fetch(`/api/policy/ops/kill-switch?on=${on}`, { method: "POST" });
    refresh();
  };

  const rows = useMemo(() => {
    const list = [...actions].reverse();
    if (filter === "all") return list;
    return list.filter((a) => a.status === filter);
  }, [actions, filter]);

  const latest = audit.find((x) => x.action !== "measure_recovery") || audit[0] || {};
  const extra = latest.extra || {};
  const link = extra.link || {};
  const rupee = (sel?.amount_paise || 0) / 100;
  const whyGate = sel?.block_reason ? GATES[sel.block_reason] || extra.playbook : extra.playbook;

  return (
    <>
      <nav className="nav">
        <button type="button" className="chip" onClick={() => setPage("story")}>
          Why
        </button>
        <button type="button" className="chip on" onClick={() => setPage("ledger")}>
          Ledger
        </button>
        <button type="button" className="chip" onClick={() => setPage("mesh")}>
          Services
        </button>
        <span>
          {SERVICES.filter(([n]) => status[n]?.ok).length}/{SERVICES.length} live · test mode
        </span>
      </nav>

      {page === "story" && (
        <header className="hero">
          <h1>
            REVIVA
            <span>REVENUE AT REST</span>
          </h1>
          <p>
            About 70% of Indian cart abandon is a failed payment. About 70% of those people never try
            again. Roughly 40% of fails are a down bank — retrying instantly just fails again.
            Well-separated retries can bring back 15–20% of failed transactions. Reviva is the
            separator: name the cause, obey the brakes, then talk to Razorpay.
          </p>
          <div className="cube" aria-hidden="true" />
          <div className="wrap">
            <div className="impact">
              <div className="glass">
                <div className="k">Abandon from payment fail</div>
                <div className="v">70%</div>
              </div>
              <div className="glass">
                <div className="k">Never retry after one fail</div>
                <div className="v">70%</div>
              </div>
              <div className="glass">
                <div className="k">Bank downtime share</div>
                <div className="v">~40%</div>
              </div>
              <div className="glass">
                <div className="k">Designed recovery of fails</div>
                <div className="v">15–20%</div>
              </div>
            </div>
            <p className="k" style={{ textAlign: "center" }}>
              Industry research used to size the problem — not Reviva live GMV. ₹50L attempts, 10%
              margin, a 20-point success gap ≈ ₹1L/month lost.
            </p>
            <div className="toolbar" style={{ justifyContent: "center" }}>
              <button className="primary" type="button" onClick={() => setPage("ledger")}>
                Open the ledger
              </button>
            </div>
          </div>
        </header>
      )}

      {page === "mesh" && (
        <div className="wrap">
          <h2 className="hero" style={{ fontFamily: "Cormorant Garamond, serif", fontSize: 42 }}>
            Six services
          </h2>
          <div className="impact">
            {SERVICES.map(([name]) => (
              <div className="glass" key={name}>
                <div className="k">{name}</div>
                <div className={status[name]?.ok ? "ok" : "bad"}>
                  {status[name]?.ok ? "Healthy" : "Down"}
                </div>
              </div>
            ))}
          </div>
          <div className="glass">
            <p>
              Ingest trusts the event. Diagnosis uses rules first; Qwen only if the error is junk.
              Policy is the law. Executor talks to Razorpay. Simulator is a practice batch — not a
              shop.
            </p>
            <p>
              If a row says the local model did not answer: in this folder run
              <code> docker compose exec ollama ollama pull qwen2.5:1.5b</code>
              . Your other project’s Ollama is a different disk.
            </p>
          </div>
        </div>
      )}

      {page === "ledger" && (
        <div className="wrap">
          <div className="impact">
            <div className="glass">
              <div className="k">₹ recovered (practice score)</div>
              <div className="v ok">
                {fmtMoney(metrics?.rupees_recovered_sim)}
                <small> not live GMV</small>
              </div>
            </div>
            <div className="glass">
              <div className="k">Stopped by rules</div>
              <div className="v warn">{metrics?.actions_blocked ?? "—"}</div>
            </div>
            <div className="glass">
              <div className="k">Sent or scheduled</div>
              <div className="v">{metrics?.actions_taken ?? "—"}</div>
            </div>
            <div className="glass">
              <div className="k">Practice recovery rate</div>
              <div className="v">{((metrics?.recovery_rate || 0) * 100).toFixed(0)}%</div>
            </div>
          </div>

          {frozen && (
            <div className="glass" style={{ borderColor: "#ff8b8b", marginBottom: 12 }}>
              <h2 className="warn">Agent is frozen</h2>
              <p>
                You pressed freeze (kill switch). Every new failure is <b>stopped</b> — no Payment
                Link, no retry. That is why recent rows all say stopped. Unfreeze to recover again.
              </p>
              <button className="primary" type="button" onClick={() => kill(false)}>
                Unfreeze — allow recovery
              </button>
            </div>
          )}

          <div className="glass">
            <p className="k">
              Freeze = emergency stop for the whole merchant (like pulling the plug). Leave it off
              unless you are demoing a stop. Ledger count is every action ever; a batch that reuses
              the same fake payment ids is ignored (dedup). New batches now get unique ids.
            </p>
            <div className="toolbar">
              <button className="primary" type="button" onClick={runBatch} disabled={busy}>
                {busy ? "Running…" : `Practice batch (${n})`}
              </button>
              <button type="button" onClick={() => setN(20)}>
                20
              </button>
              <button type="button" onClick={() => setN(100)}>
                100
              </button>
              {!frozen && (
                <button type="button" onClick={() => kill(true)}>
                  Emergency freeze
                </button>
              )}
            </div>
            {lastBatch && (
              <p className="k">
                Last batch: {lastBatch.batch} events ingested. Scroll the ledger — newest at the
                top (#{actions.length || "…"}).
              </p>
            )}
            {err && <p className="bad">{err}</p>}
          </div>

          <div className="layout" style={{ marginTop: 16 }}>
            <div className="glass">
              <div className="k">What the agent did</div>
              <div className="toolbar">
                {["all", "executed", "scheduled", "blocked", "pending_approval"].map((f) => (
                  <button
                    key={f}
                    type="button"
                    className={filter === f ? "chip on" : "chip"}
                    onClick={() => setFilter(f)}
                  >
                    {f === "pending_approval" ? "needs a person" : f === "blocked" ? "stopped" : f}
                  </button>
                ))}
              </div>
              {rows.map((a) => (
                <div
                  key={a.id}
                  className={sel?.id === a.id ? "row sel" : "row"}
                  onClick={() => open(a)}
                >
                  <span className="k">#{a.id}</span>
                  <div>
                    <div>{titleFor(a)}</div>
                    <div className="k">
                      ₹{(a.amount_paise / 100).toLocaleString("en-IN")}
                      {a.block_reason ? ` · ${GATES[a.block_reason] || a.block_reason}` : ""}
                    </div>
                  </div>
                  <span className={`badge ${badgeClass(a.status)}`}>{badgeLabel(a.status)}</span>
                </div>
              ))}
              {!rows.length && <p className="k">Nothing yet. Run a practice batch.</p>}
            </div>

            <aside className="glass detail">
              {!sel && (
                <>
                  <h2>Pick a row</h2>
                  <p>
                    You will see the plain-language reason, whether Razorpay was called, and every
                    step we logged. Old rows from before today may still show short machine phrases.
                    Run a new batch after updating to see full sentences from the policy engine.
                  </p>
                </>
              )}
              {sel && (
                <>
                  <div className="k">Event {sel.event_id}</div>
                  <h2>{titleFor(sel)}</h2>
                  <p>{whyGate || "The playbook for this diagnosis was applied."}</p>
                  <div className="meta">
                    <div>
                      <span className="k">Amount</span>
                      <span>₹{rupee.toLocaleString("en-IN")}</span>
                    </div>
                    <div>
                      <span className="k">What happened</span>
                      <span>{badgeLabel(sel.status)}</span>
                    </div>
                    <div>
                      <span className="k">Razorpay</span>
                      <span>
                        {link.stub === false
                          ? "Real test Payment Link"
                          : sel.razorpay_ref
                            ? sel.razorpay_ref
                            : "Not called"}
                      </span>
                    </div>
                  </div>
                  {link.short_url && (
                    <a className="linkout" href={link.short_url} target="_blank" rel="noreferrer">
                      Open test checkout →
                    </a>
                  )}
                  <div className="k" style={{ marginTop: 22 }}>
                    Story of this payment
                  </div>
                  <ul className="timeline">
                    {audit.map((row) => (
                      <li key={row.id}>
                        <strong>
                          {row.action === "measure_recovery"
                            ? "Practice score"
                            : titleFor({
                                action_type: row.action,
                                status: row.outcome,
                                block_reason: null,
                              })}
                        </strong>
                        <div>{sourceHuman(row.decision_source)}</div>
                        <div>{GATES[row.reason] || row.reason}</div>
                        <div className="k">
                          {row.outcome === "recovered"
                            ? "Practice: counted as recovered"
                            : row.outcome === "not_recovered"
                              ? "Practice: counted as not recovered"
                              : row.outcome}{" "}
                          · {row.created_at}
                        </div>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </aside>
          </div>
        </div>
      )}
    </>
  );
}
