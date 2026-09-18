import FingerprintJS from "@fingerprintjs/fingerprintjs";

let cachedId = null;

export async function getDeviceId() {
  if (cachedId) return cachedId;
  const stored = sessionStorage.getItem("sentinel_device_id");
  if (stored) {
    cachedId = stored;
    return stored;
  }
  const fp = await FingerprintJS.load();
  const result = await fp.get();
  cachedId = result.visitorId;
  sessionStorage.setItem("sentinel_device_id", cachedId);
  return cachedId;
}

export function overrideDeviceId(id) {
  cachedId = id;
  sessionStorage.setItem("sentinel_device_id", id);
}
