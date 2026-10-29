import React, { useState } from 'react';
import { Lock, Loader2, X } from 'lucide-react';
import { api } from '../api.js';

const input = 'w-full bg-slate-50/80 border border-slate-200/80 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-400';

export default function ChangePasswordModal({ token, onClose, onSessionExpired }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [again, setAgain] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (next !== again) return setError('The two new passwords do not match');
    setSaving(true);
    try {
      await api('/me/password', { token, method: 'POST', body: { current_password: current, new_password: next }, onExpired: onSessionExpired });
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4" role="dialog" aria-modal="true" aria-label="Change password">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl p-6 max-w-sm w-full space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2"><Lock className="w-4 h-4 text-amber-500" /><h3 className="text-sm font-bold text-slate-900">Change password</h3></div>
          <button onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-700"><X className="w-4 h-4" /></button>
        </div>
        {done ? (
          <>
            <p className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">Password changed. Use the new one next time you log in.</p>
            <button onClick={onClose} className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold py-2.5 rounded-xl transition">Close</button>
          </>
        ) : (
          <form onSubmit={submit} className="space-y-3">
            <label className="block text-[11px] font-bold text-slate-500 uppercase space-y-1">Current password
              <input type="password" required autoComplete="current-password" className={input} value={current} onChange={(e) => setCurrent(e.target.value)} />
            </label>
            <label className="block text-[11px] font-bold text-slate-500 uppercase space-y-1">New password (6+ characters)
              <input type="password" required minLength={6} autoComplete="new-password" className={input} value={next} onChange={(e) => setNext(e.target.value)} />
            </label>
            <label className="block text-[11px] font-bold text-slate-500 uppercase space-y-1">Repeat new password
              <input type="password" required minLength={6} autoComplete="new-password" className={input} value={again} onChange={(e) => setAgain(e.target.value)} />
            </label>
            {error && <p className="text-xs font-medium text-rose-600">{error}</p>}
            <button disabled={saving} className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-bold py-2.5 rounded-xl transition">
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}Change password
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
