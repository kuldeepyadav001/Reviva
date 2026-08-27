import { useEffect, useState } from "react";

const SERVICES = [
  ["ingest", "/api/ingest/health"],
  ["simulator", "/api/simulator/health"],
  ["diagnosis", "/api/diagnosis/health"],
  ["policy", "/api/policy/health"],
  ["executor", "/api/executor/health"],
];

export default function App() {
  const [status, setStatus] = useState({});
  const [metrics, setMetrics] = useState(null);
  const [actions, setActions] = useState([]);
  const [audit, setAudit] = useState(null);
  const [busy, setBusy] = useState(false);

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
      .then(setActions)
      .catch(() => {});
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);

  const runBatch = async () => {
    setBusy(true);
    try {
      await fetch("/api/simulator/run-batch?n=20", { method: "POST" });
      refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="wrap">
      <h1>Reviva</h1>
      <p className="sub">Payment-failure recovery — operator console</p>
      <p className="sub">
        ₹ recovered is <b>seeded simulation</b> unless a row is tagged live.
      </p>
      <p>
        <button type="button" onClick={runBatch} disabled={busy}>
          {busy ? "Running…" : "Run labeled batch (20)"}
        </button>
      </p>
      <div className="grid">
        {SERVICES.map(([name]) => (
          <div className="card" key={name}>
            <div>{name}</div>
            <div className={status[name]?.ok ? "ok" : "bad"}>
              {status[name]?.ok ? "healthy" : status[name] ? "down" : "checking…"}
            </div>
          </div>
        ))}
        <div className="card">
          <div>₹ recovered (sim)</div>
          <div className="ok">{metrics?.rupees_recovered_sim ?? "—"}</div>
        </div>
        <div className="card">
          <div>Blocked</div>
          <div>{metrics?.actions_blocked ?? "—"}</div>
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="sub">Actions — click for audit</div>
        <table>
          <thead>
            <tr>
              <th>id</th>
              <th>event</th>
              <th>type</th>
              <th>status</th>
            </tr>
          </thead>
          <tbody>
            {(actions || []).slice(-30).reverse().map((a) => (
              <tr
                key={a.id}
                onClick={() =>
                  fetch(`/api/executor/audit/${a.event_id}`)
                    .then((r) => r.json())
                    .then(setAudit)
                }
              >
                <td>{a.id}</td>
                <td>{a.event_id}</td>
                <td>{a.action_type}</td>
                <td>{a.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {audit && <pre>{JSON.stringify(audit, null, 2)}</pre>}
      </div>
    </div>
  );
}
