import { Fragment, useState } from "react";

const TONE = { Safe: "safe", Medium: "medium", High: "high" };

export default function HistoryTable({ rows = [] }) {
  const [open, setOpen] = useState(null);
  if (!rows.length) return <p className="muted">No transactions yet.</p>;
  return (
    <table className="history">
      <thead>
        <tr>
          <th>Time</th>
          <th>Amount</th>
          <th>Category</th>
          <th>Risk</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <Fragment key={row.id}>
            <tr
              className={TONE[row.risk_level] || ""}
              onClick={() => setOpen(open === row.id ? null : row.id)}
            >
              <td>{new Date(row.timestamp).toLocaleString()}</td>
              <td>₹{Number(row.amount).toLocaleString("en-IN")}</td>
              <td>{row.merchant_category}</td>
              <td>
                <span className={`pill ${TONE[row.risk_level]}`}>
                  {row.risk_level} ({row.risk_score})
                </span>
              </td>
              <td>{row.action_taken}</td>
            </tr>
            {open === row.id && (
              <tr className="reason-row">
                <td colSpan={5}>{row.reasoning}</td>
              </tr>
            )}
          </Fragment>
        ))}
      </tbody>
    </table>
  );
}
