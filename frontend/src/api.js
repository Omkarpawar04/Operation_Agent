// Backend address comes from frontend/.env (VITE_API_URL); falls back to the local default
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3001/api';

// One place for backend calls: adds the login token, unwraps JSON, turns failures into readable errors.
// onExpired runs when the server says the login is no longer valid (only for calls that sent a token).
export async function api(path, { token, method = 'GET', body, onExpired } = {}) {
  let res;
  try {
    res = await fetch(API_BASE + path, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error('Cannot reach the backend. Is it running on port 3001?');
  }
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && token) onExpired?.();
  if (!res.ok) throw new Error(data.message || 'Something went wrong');
  return data;
}
