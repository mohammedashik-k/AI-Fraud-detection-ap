const CATEGORIES = ["Grocery", "Fuel", "Restaurants", "Utilities", "Online", "Electronics", "Travel", "Jewelry", "Transfer"];

export default function TransactionForm({ deviceId, onSubmit, lastResult, busy }) {
  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        const fd = new FormData(e.currentTarget);
        onSubmit({
          amount: Number(fd.get("amount")),
          merchant_category: fd.get("merchant_category"),
          device_id: deviceId,
        });
      }}
    >
      <h3>Make a transaction</h3>
      <label>
        Amount (₹)
        <input name="amount" id="txn-amount" type="number" min="1" step="1" defaultValue="1200" required />
      </label>
      <label>
        Merchant category
        <select name="merchant_category" id="txn-category" defaultValue="Grocery">
          {CATEGORIES.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </label>
      <button className="primary" disabled={busy}>
        {busy ? "Scoring…" : "Submit & score"}
      </button>
      {lastResult && (
        <div className={`result-banner ${lastResult.risk_level.toLowerCase()}`}>
          <strong>
            {lastResult.risk_level} · {lastResult.risk_score}/100 · {lastResult.recommended_action}
          </strong>
          <p>{lastResult.reasoning}</p>
        </div>
      )}
    </form>
  );
}
