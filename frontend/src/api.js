const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "aiops_access_token";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(extra = {}) {
  const token = getStoredToken();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "The analyzer service returned an error.");
  }
  return payload;
}

export async function analyzeLogs({ text, file }) {
  if (file) {
    const data = new FormData();
    data.append("file", file);
    if (text?.trim()) {
      data.append("text", text);
    }

    const response = await fetch(`${API_BASE_URL}/upload-logs`, {
      method: "POST",
      headers: authHeaders(),
      body: data,
    });
    return parseResponse(response);
  }

  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ logs: text, source: "manual paste" }),
  });
  return parseResponse(response);
}

export async function loginUser({ email, password }) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parseResponse(response);
}

export async function fetchCurrentUser() {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: authHeaders(),
  });
  return parseResponse(response);
}

export async function logoutUser() {
  const response = await fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    headers: authHeaders(),
  });
  return parseResponse(response);
}

export async function fetchAuditEvents() {
  const response = await fetch(`${API_BASE_URL}/auth/audit`, {
    headers: authHeaders(),
  });
  return parseResponse(response);
}

export async function fetchHistory() {
  const response = await fetch(`${API_BASE_URL}/history`, {
    headers: authHeaders(),
  });
  return parseResponse(response);
}

export async function fetchOperationalOverview() {
  const response = await fetch(`${API_BASE_URL}/ops/overview`, {
    headers: authHeaders(),
  });
  return parseResponse(response);
}

export async function fetchPlatformOverview() {
  const response = await fetch(`${API_BASE_URL}/platform/overview`, {
    headers: authHeaders(),
  });
  return parseResponse(response);
}

export async function resolveIncident(incidentId) {
  const response = await fetch(`${API_BASE_URL}/platform/incidents/${incidentId}/resolve`, {
    method: "POST",
    headers: authHeaders(),
  });
  return parseResponse(response);
}

export async function fetchSampleLogs() {
  const response = await fetch(`${API_BASE_URL}/sample-logs`);
  return parseResponse(response);
}
