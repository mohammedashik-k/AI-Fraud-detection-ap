const TOKEN_KEY = "sentinelpay_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = typeof detail === "string" ? detail : detail?.[0]?.msg || res.statusText;
    throw new Error(msg);
  }
  return data;
}

export const api = {
  register: (email, password) => request("/register", { method: "POST", auth: false, body: { email, password } }),
  login: (payload) => request("/login", { method: "POST", auth: false, body: payload }),
  profile: () => request("/account/profile"),
  dashboard: () => request("/dashboard"),
  transaction: (payload) => request("/transaction", { method: "POST", body: payload }),
  muleNetwork: () => request("/admin/mule-network"),
};
