const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

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
      body: data,
    });
    return parseResponse(response);
  }

  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ logs: text, source: "manual paste" }),
  });
  return parseResponse(response);
}

export async function fetchHistory() {
  const response = await fetch(`${API_BASE_URL}/history`);
  return parseResponse(response);
}

export async function fetchSampleLogs() {
  const response = await fetch(`${API_BASE_URL}/sample-logs`);
  return parseResponse(response);
}
