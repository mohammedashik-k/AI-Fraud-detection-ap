export default function TrustGauge({ score = 0, label = "Trust score" }) {
  const clamped = Math.max(0, Math.min(100, Number(score) || 0));
  const r = 54;
  const c = 2 * Math.PI * r;
  const offset = c - (clamped / 100) * c;
  const tone = clamped >= 70 ? "safe" : clamped >= 40 ? "medium" : "high";
  return (
    <div className={`gauge ${tone}`}>
      <svg viewBox="0 0 140 140" width="140" height="140">
        <circle cx="70" cy="70" r={r} className="gauge-track" />
        <circle
          cx="70"
          cy="70"
          r={r}
          className="gauge-value"
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="gauge-label">
        <strong>{clamped}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}
