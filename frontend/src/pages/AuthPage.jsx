import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../api";
import { getDeviceId } from "../fingerprint";

export default function AuthPage() {
  const nav = useNavigate();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("priya@sentinelpay.demo");
  const [password, setPassword] = useState("Demo@123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") {
        await api.register(email, password);
      }
      const device_id = await getDeviceId();
      const res = await api.login({ email, password, device_id });
      setToken(res.access_token);
      nav("/dashboard");
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-hero">
        <p className="eyebrow">SentinelPay</p>
        <h1>AI fraud detection that sees the whole account, not just a swipe.</h1>
        <p className="muted">
          Device fingerprinting, impossible-travel checks, mule-network graphs, and behavioral scoring — loaded the
          moment you sign in.
        </p>
      </div>
      <form className="card auth-card" onSubmit={onSubmit}>
        <div className="tabs">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
            Login
          </button>
          <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>
            Register
          </button>
        </div>
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </label>
        <label>
          Password
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" minLength={8} required />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>
          {busy ? "Working…" : mode === "login" ? "Sign in" : "Create account & sign in"}
        </button>
        <p className="hint">Device ID is captured automatically with FingerprintJS. No extra fields.</p>
      </form>
    </div>
  );
}
