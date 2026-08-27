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

  useEffect(() => {
    SERVICES.forEach(([name, path]) => {
      fetch(path)
        .then((r) => r.json())
        .then((j) => setStatus((s) => ({ ...s, [name]: j })))
        .catch(() => setStatus((s) => ({ ...s, [name]: { ok: false } })));
    });
  }, []);

  return (
    <div className="wrap">
      <h1>Reviva</h1>
      <p className="sub">Payment-failure recovery — operator console (React)</p>
      <div className="grid">
        {SERVICES.map(([name]) => (
          <div className="card" key={name}>
            <div>{name}</div>
            <div className={status[name]?.ok ? "ok" : "bad"}>
              {status[name]?.ok ? "healthy" : status[name] ? "down" : "checking…"}
            </div>
          </div>
        ))}
      </div>
      <p className="sub">
        Metrics and audit explorer land after executor + diagnosis stages.
      </p>
    </div>
  );
}
