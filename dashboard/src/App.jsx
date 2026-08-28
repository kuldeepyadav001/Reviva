import { useEffect, useMemo, useState } from "react";

const SERVICES = [
  ["ingest", "/api/ingest/health"],
  ["simulator", "/api/simulator/health"],
  ["diagnosis", "/api/diagnosis/health"],
  ["policy", "/api/policy/health"],
  ["executor", "/api/executor/health"],
];

const LABELS = {
  schedule_retry_backoff: "Backoff retry — bank likely down",
  schedule_retry_balance_window: "Wait for funds window",
  send_payment_link: "Fresh Payment Link (new session)",
  send_single_reminder_link: "One reminder, then stop",
  hold_manual_review: "Held for a human",
  none: "No money action",
};

function humanSource(src) {
  if (!src) return "—";
  if (src.startsWith("rule:")) return `Rules engine (${src.slice(5)})`;
  if (src.startsWith("llm")) return `Local model (${src})`;
  if (src === "simulator") return "Evaluation harness (not live GMV)";
  if (src === "gate") return "Stopping rule";
  return src;
}

function fmtMoney(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export default function App() {
  const [status, setStatus] = useState({});
  const [metrics, setMetrics] = useState(null);
  const [actions, setActions] = useState([]);
  const [audit, setAudit] = useState([]);
  const [sel, setSel] = useState(null);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [n, setN] = useState(20);

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
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 6000);
    return () => clearInterval(t);
  }, []);

  const open = async (a) => {
    setSel(a);
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
      if (!r.ok) throw new Error(`batch ${r.status}`);
      await refresh();
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

  const latest = audit[0] || {};
  const extra = latest.extra || {};
  const link = extra.link || {};
  const rupee = (sel?.amount_paise || 0) / 100;

  return (
    <>
      <nav className="nav">
        <span>Recovery ops · IST</span>
        <span>Test mode · Razorpay</span>
        <span>
          {SERVICES.filter(([n]) => status[n]?.ok).length}/{SERVICES.length} services
        </span>
      </nav>

      <header className="hero">
        <h1>
          REVIVA
          <span>REVENUE AT REST</span>
        </h1>
        <p>
          Seventy percent of Indian cart abandon is a failed payment. Seventy percent of those
          customers never try again. Reviva names the cause, refuses illegal retries, and only then
          asks Razorpay for a new session.
        </p>
        <div className="cube" aria-hidden="true" />
        <div className="scroll">Scroll the ledger</div>
      </header>

      <div className="wrap">
        <div className="impact">
          <div className="glass">
            <div className="k">Abandon from payment fail</div>
            <div className="v">70%</div>
          </div>
          <div className="glass">
            <div className="k">Gone after one fail</div>
            <div className="v">70%</div>
          </div>
          <div className="glass">
            <div className="k">Bank downtime share</div>
            <div className="v">~40%</div>
          </div>
          <div className="glass">
            <div className="k">₹ recovered (sim)</div>
            <div className="v ok">
              {fmtMoney(metrics?.rupees_recovered_sim)}
              <small> not live GMV</small>
            </div>
          </div>
        </div>

        <div className="glass">
          <div className="k">Mesh</div>
          <div className="svcs">
            {SERVICES.map(([name]) => (
              <span className="badge" key={name}>
                <span className="dot" style={{ background: status[name]?.ok ? "#7dffc3" : "#ff8b8b" }} />
                {name}
              </span>
            ))}
          </div>
          <div className="toolbar" style={{ marginTop: 16 }}>
            <button className="primary" type="button" onClick={runBatch} disabled={busy}>
              {busy ? "Running batch…" : `Run labeled batch (${n})`}
            </button>
            <button type="button" onClick={() => setN(20)}>
              20
            </button>
            <button type="button" onClick={() => setN(100)}>
              100
            </button>
            <button type="button" onClick={() => kill(true)}>
              Kill switch on
            </button>
            <button type="button" onClick={() => kill(false)}>
              Kill switch off
            </button>
            <span className="k">
              blocked {metrics?.actions_blocked ?? "—"} · taken {metrics?.actions_taken ?? "—"} ·
              rate {((metrics?.recovery_rate || 0) * 100).toFixed(0)}%
            </span>
          </div>
          {err && <p className="bad">{err}</p>}
        </div>

        <div className="layout" style={{ marginTop: 16 }}>
          <div className="glass">
            <div className="k">Ledger</div>
            <div className="toolbar">
              {["all", "executed", "scheduled", "blocked", "pending_approval"].map((f) => (
                <button
                  key={f}
                  type="button"
                  className={filter === f ? "chip on" : "chip"}
                  onClick={() => setFilter(f)}
                >
                  {f.replace("_", " ")}
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
                  <div>{LABELS[a.action_type] || a.action_type}</div>
                  <div className="k">
                    event {a.event_id} · ₹{(a.amount_paise / 100).toLocaleString("en-IN")}
                    {a.block_reason ? ` · ${a.block_reason}` : ""}
                  </div>
                </div>
                <span className={`badge ${a.status === "blocked" ? "bad" : a.status === "executed" ? "ok" : "warn"}`}>
                  {a.status}
                </span>
              </div>
            ))}
            {!rows.length && <p className="k">No rows yet. Run a batch.</p>}
          </div>

          <aside className="glass detail">
            {!sel && (
              <>
                <h2>Select a recovery</h2>
                <p>
                  Each row is a decision. The right panel is why it happened — rule id, model, or a
                  gate that refused to spend the customer’s attention.
                </p>
              </>
            )}
            {sel && (
              <>
                <div className="k">Event {sel.event_id}</div>
                <h2>{LABELS[sel.action_type] || sel.action_type}</h2>
                <p>
                  {sel.block_reason
                    ? `Stopped: ${sel.block_reason.replaceAll("_", " ")}.`
                    : extra.playbook || "Playbook applied as diagnosed."}
                </p>
                <div className="meta">
                  <div>
                    <span className="k">Amount</span>
                    <span>₹{rupee.toLocaleString("en-IN")}</span>
                  </div>
                  <div>
                    <span className="k">Status</span>
                    <span>{sel.status}</span>
                  </div>
                  <div>
                    <span className="k">Razorpay ref</span>
                    <span>{sel.razorpay_ref || extra.razorpay_ref || "—"}</span>
                  </div>
                  <div>
                    <span className="k">Stub?</span>
                    <span>{link.stub === false ? "No — live test link" : link.stub ? "Yes" : "—"}</span>
                  </div>
                </div>
                {link.short_url && (
                  <a className="linkout" href={link.short_url} target="_blank" rel="noreferrer">
                    Open Razorpay test checkout →
                  </a>
                )}
                <div className="k" style={{ marginTop: 22 }}>
                  Why (audit)
                </div>
                <ul className="timeline">
                  {audit.map((row) => (
                    <li key={row.id}>
                      <strong>{row.action.replaceAll("_", " ")}</strong>
                      <div className="k">{humanSource(row.decision_source)}</div>
                      <div>{row.reason}</div>
                      <div className="k">
                        {row.outcome} · {row.created_at}
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </aside>
        </div>
      </div>
    </>
  );
}
