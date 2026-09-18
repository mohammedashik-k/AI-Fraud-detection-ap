import { useNavigate } from "react-router-dom";
import { api, setToken } from "../api";
import { overrideDeviceId } from "../fingerprint";

const LONDON = {
  simulate_ip: "81.2.69.142",
  simulate_lat: 51.5074,
  simulate_lng: -0.1278,
  simulate_city: "London",
  simulate_country: "United Kingdom",
};

export default function SimulatePanel({ emailHint, onAfterAction }) {
  const nav = useNavigate();

  async function relogin(extra) {
    const password = "Demo@123";
    const email = emailHint || "priya@sentinelpay.demo";
    const res = await api.login({ email, password, ...extra });
    setToken(res.access_token);
    await onAfterAction?.();
  }

  return (
    <aside className="card simulate">
      <h3>Simulate</h3>
      <p className="muted">Live demo controls — they pre-fill or replay the attack path.</p>
      <button
        type="button"
        onClick={async () => {
          overrideDeviceId(`fp_demo_new_${Date.now()}`);
          await relogin({ device_id: sessionStorage.getItem("sentinel_device_id") });
        }}
      >
        Simulate login from new device
      </button>
      <button
        type="button"
        onClick={async () => {
          await relogin({
            device_id: sessionStorage.getItem("sentinel_device_id") || "fp_demo_travel",
            ...LONDON,
          });
        }}
      >
        Simulate login from different country
      </button>
      <button
        type="button"
        onClick={() => {
          const amount = document.getElementById("txn-amount");
          const cat = document.getElementById("txn-category");
          if (amount) amount.value = 50000;
          if (cat) cat.value = "Jewelry";
          amount?.scrollIntoView({ behavior: "smooth", block: "center" });
        }}
      >
        Simulate high-value transaction
      </button>
      <button type="button" className="ghost" onClick={() => nav("/admin")}>
        Open mule-network graph
      </button>
    </aside>
  );
}
