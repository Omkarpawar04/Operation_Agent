import React, { useCallback, useRef } from 'react';
import { api } from '../../api.js';

export const input = 'w-full bg-slate-50/80 border border-slate-200/80 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-400';
export const ghostBtn = 'flex items-center justify-center gap-1.5 text-xs font-bold text-slate-600 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 transition disabled:opacity-50';

// Calls the backend with the login token; a rejected login signs the user out
export function useCall(token, onSessionExpired) {
  const expired = useRef(onSessionExpired);
  expired.current = onSessionExpired;
  return useCallback((path, opts = {}) => api(`/learning${path}`, { token, onExpired: () => expired.current?.(), ...opts }), [token]);
}

export const minutes = (sec) => (sec ? `${Math.max(1, Math.round(sec / 60))} min` : '');
export const fmtDate = (iso) => new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

// What kind of link is this? Mirrors the backend. Only youtube, vimeo and file links can be followed second by second.
export function parseVideo(url = '') {
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/^www\./, '');
    let yid = null;
    if (host === 'youtu.be') yid = u.pathname.slice(1).split('/')[0];
    else if (host.endsWith('youtube.com') || host.endsWith('youtube-nocookie.com')) {
      if (u.pathname === '/watch') yid = u.searchParams.get('v');
      else { const m = u.pathname.match(/^\/(?:embed|shorts|live)\/([\w-]+)/); if (m) yid = m[1]; }
    }
    if (yid) return { provider: 'youtube', id: yid, url };
    if (host === 'vimeo.com' || host.endsWith('.vimeo.com')) {
      const m = u.pathname.match(/\/(\d{5,})/);
      if (m) return { provider: 'vimeo', id: m[1], url };
    }
    if (/\.(mp4|webm|ogv|ogg|mov|m4v)$/i.test(u.pathname)) return { provider: 'file', url };
  } catch { /* not a link */ }
  return { provider: 'other', url };
}

export const PROVIDER_LABEL = { youtube: 'YouTube', vimeo: 'Vimeo', file: 'Video file', other: 'Other link' };

// Google Drive links can be shown inside the page (but not followed), other links open in a new tab
export function otherEmbed(url = '') {
  try {
    const u = new URL(url);
    if (u.hostname === 'drive.google.com') {
      const m = u.pathname.match(/\/file\/d\/([\w-]+)/);
      if (m) return `https://drive.google.com/file/d/${m[1]}/preview`;
    }
  } catch { /* not a link */ }
  return null;
}

export function ErrorLine({ children }) {
  if (!children) return null;
  return <p role="alert" className="text-xs font-medium text-rose-600 bg-rose-50 border border-rose-100 rounded-xl px-3 py-2">{children}</p>;
}
