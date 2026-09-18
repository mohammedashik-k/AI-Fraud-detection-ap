import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, clearToken } from "../api";
import { getDeviceId } from "../fingerprint";
import HistoryTable from "../components/HistoryTable";
import SimulatePanel from "../components/SimulatePanel";
import TransactionForm from "../components/TransactionForm";
import TrustGauge from "../components/TrustGauge";

export default function DashboardPage() {
  const nav = useNavigate();
  const [profile, setProfile] = useState(null);
  const [deviceId, setDeviceId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  async function load() {
    const [p, id] = await Promise.all([api.profile(), getDeviceId()]);
    setProfile(p);
    setDeviceId(id);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function submitTxn(payload) {
    setBusy(true);
    setError("");
    try {
      const result = await api.transaction(payload);
      setLastResult(result);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    clearToken();
    nav("/");
  }

  if (!profile && !error) return <div className="page">Loading account profile…</div>;
  if (!profile) return <div className="page error">{error}</div>;

  const session = profile.location_profile?.current_session;
  const building = profile.building_trust_profile;

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <p className="eyebrow">SentinelPay</p>
          <h1>{profile.email}</h1>
          <p className="muted">
            {profile.account_id} · opened {new Date(profile.account_created_date).toLocaleDateString()}
          </p>
        </div>
        <nav>
          <Link to="/admin">Admin</Link>
          <button type="button" className="ghost" onClick={logout}>
            Log out
          </button>
        </nav>
      </header>

      {building && (
        <div className="banner">
          Building your trust profile… {profile.transaction_profile.total_transactions}/{profile.min_txns_for_trust}{" "}
          transactions scored. New accounts use a slightly stricter baseline until history exists.
        </div>
      )}

      <section className="grid-3">
        <div className="card session-card">
          <h3>Current session</h3>
          {session ? (
            <dl>
              <div>
                <dt>Device</dt>
                <dd>{session.device_id}</dd>
              </div>
              <div>
                <dt>IP</dt>
                <dd>{session.ip_address}</dd>
              </div>
              <div>
                <dt>Location</dt>
                <dd>
                  {session.city}, {session.country}
                </dd>
              </div>
              <div>
                <dt>Signed in</dt>
                <dd>{session.login_time ? new Date(session.login_time).toLocaleString() : "—"}</dd>
              </div>
            </dl>
          ) : (
            <p className="muted">No session geo yet.</p>
          )}
        </div>
        <div className="card gauge-wrap">
          <TrustGauge score={profile.trust_score} />
          <ul className="breakdown">
            <li>Device consistency {profile.trust_breakdown.device_consistency}</li>
            <li>Location consistency {profile.trust_breakdown.location_consistency}</li>
            <li>Clean history {profile.trust_breakdown.history_cleanliness}</li>
          </ul>
        </div>
        <SimulatePanel emailHint={profile.email} onAfterAction={load} />
      </section>

      <section className="grid-2">
        <TransactionForm deviceId={deviceId} onSubmit={submitTxn} lastResult={lastResult} busy={busy} />
        <div className="card">
          <h3>Account snapshot</h3>
          <p>
            {profile.transaction_profile.total_transactions} transactions · avg ₹
            {Number(profile.transaction_profile.average_transaction_amount).toLocaleString("en-IN")} · avg risk{" "}
            {profile.transaction_profile.historical_avg_risk_score}
          </p>
          <h4>Known devices</h4>
          <ul className="device-list">
            {profile.device_profile.known_devices.map((d) => (
              <li key={d.device_id} className={d.is_current ? "current" : ""}>
                {d.device_id} {d.is_current ? "(active)" : ""} · last {new Date(d.last_seen).toLocaleDateString()}
              </li>
            ))}
          </ul>
          <h4>Recent locations</h4>
          <ul>
            {profile.location_profile.past_locations.slice(0, 6).map((l) => (
              <li key={l.timestamp}>
                {l.city}, {l.country} · {new Date(l.timestamp).toLocaleString()}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {error && <p className="error">{error}</p>}

      <section className="card">
        <h3>Transaction history</h3>
        <p className="muted">Click a row to expand the scoring rationale.</p>
        <HistoryTable rows={profile.transaction_profile.history} />
      </section>
    </div>
  );
}
