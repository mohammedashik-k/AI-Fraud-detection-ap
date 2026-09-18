import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { DataSet, Network } from "vis-network/standalone";
import { api } from "../api";

export default function AdminPage() {
  const host = useRef(null);
  const net = useRef(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.muleNetwork().then(setData).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!data || !host.current) return;
    const nodes = new DataSet(
      data.nodes.map((n) => ({
        id: n.id,
        label: `${n.account_id}\n${n.email}`,
        shape: "dot",
        size: 22,
        color: "#3dd6c6",
        font: { color: "#e8eefc", size: 12 },
      }))
    );
    const edges = new DataSet(
      data.links.map((l, i) => ({
        id: i,
        from: l.source,
        to: l.target,
        label: l.type === "device" ? "shared device" : "shared IP",
        color: l.type === "device" ? "#f0b429" : "#7aa2ff",
        font: { color: "#9fb0d0", size: 10, strokeWidth: 0 },
      }))
    );
    net.current?.destroy();
    net.current = new Network(
      host.current,
      { nodes, edges },
      {
        physics: { barnesHut: { gravitationalConstant: -3200, springLength: 140 } },
        interaction: { hover: true },
        edges: { width: 2, smooth: true },
      }
    );
    return () => net.current?.destroy();
  }, [data]);

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Mule network</h1>
          <p className="muted">Accounts connected by a shared device fingerprint or IP address.</p>
        </div>
        <Link to="/dashboard">Back to dashboard</Link>
      </header>
      {error && <p className="error">{error}</p>}
      <div className="card graph-card">
        <div ref={host} className="graph" />
      </div>
    </div>
  );
}
