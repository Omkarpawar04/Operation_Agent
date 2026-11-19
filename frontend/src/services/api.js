async function request(path, options = {}) {
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status}).`);
  return payload;
}

export const getHealth = () => request("/health");
export const getVoices = () => request("/api/tts/voices");
export const getInterviews = () => request("/api/interviews");
export const getInterview = (id) => request(`/api/interviews/${encodeURIComponent(id)}`);
export const getReport = (id) => request(`/api/interviews/${encodeURIComponent(id)}/report`);
export const retryReport = (id) => request(`/api/interviews/${encodeURIComponent(id)}/evaluate`, { method: "POST" });

export async function extractDocument(file) {
  const body = new FormData();
  body.append("file", file);
  const result = await request("/api/extract", { method: "POST", body });
  return result.text;
}

export async function previewVoice(voiceId) {
  const response = await fetch("/api/tts/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ voice_id: voiceId }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Could not generate this voice preview.");
  }
  return response.blob();
}
