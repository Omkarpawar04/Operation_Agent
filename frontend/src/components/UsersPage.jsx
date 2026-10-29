import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Settings, Plus, Search, Loader2, KeyRound, Copy, Check, X, ShieldCheck, Info, Eye, EyeOff, Dices } from 'lucide-react';
import { api } from '../api.js';
import { Initials, Page, PageHeader, PrimaryButton } from './ui.jsx';

const ROLES = [
  { value: 'admin', label: 'Admin' },
  { value: 'operations', label: 'Operations' },
  { value: 'placement', label: 'Placement' },
  { value: 'trainer', label: 'Trainer' },
  { value: 'student', label: 'Student' },
];
const ROLE_STYLE = {
  admin: 'bg-rose-50 text-rose-700 border-rose-100',
  operations: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  placement: 'bg-sky-50 text-sky-700 border-sky-100',
  trainer: 'bg-violet-50 text-violet-700 border-violet-100',
  student: 'bg-emerald-50 text-emerald-700 border-emerald-100',
};
const EMPTY = { name: '', email: '', phone: '', role: 'student', password: '' };
const MIN_PASSWORD = 6;
const input = 'w-full bg-slate-50/80 border border-slate-200/80 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-400';

const when = (iso) => (iso ? new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : 'Never');

// Optional helper for when you do not want to think of one: 10 easy-to-read characters
function suggestPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789';
  const bytes = crypto.getRandomValues(new Uint32Array(10));
  return Array.from(bytes, (b) => chars[b % chars.length]).join('');
}

// Master section: the admin creates logins, types the passwords, and can look them up later.
export default function UsersPage({ token, currentUserId, onSessionExpired }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [showFormPassword, setShowFormPassword] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [credentials, setCredentials] = useState(null); // { name, email, password, reason }
  const [passwordFor, setPasswordFor] = useState(null); // user whose password is being set
  const [revealed, setRevealed] = useState({}); // user id -> password currently shown
  const [busyId, setBusyId] = useState(null);
  const expiredRef = useRef(onSessionExpired);
  expiredRef.current = onSessionExpired;

  const call = useCallback((path, options = {}) => api(path, { token, onExpired: () => expiredRef.current?.(), ...options }), [token]);

  const load = useCallback(async () => {
    try {
      setError('');
      setUsers((await call('/users')).users);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [call]);
  useEffect(() => { load(); }, [load]);

  const create = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFormError('');
    try {
      const data = await call('/users', { method: 'POST', body: form });
      setCredentials({ name: data.user.name, email: data.user.email, password: form.password, reason: 'Login created' });
      setForm(EMPTY);
      setShowFormPassword(false);
      setShowForm(false);
      load();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const savePassword = async (user, password) => {
    const data = await call(`/users/${user.id}/password`, { method: 'POST', body: { password } });
    setUsers((list) => list.map((x) => (x.id === user.id ? data.user : x)));
    setRevealed((r) => { const { [user.id]: _drop, ...rest } = r; return rest; });
    setPasswordFor(null);
    setCredentials({ name: user.name, email: user.email, password, reason: 'Password set' });
  };

  const toggleReveal = async (u) => {
    if (revealed[u.id] !== undefined) {
      setRevealed(({ [u.id]: _drop, ...rest }) => rest);
      return;
    }
    setBusyId(u.id);
    try {
      const data = await call(`/users/${u.id}/password`);
      setRevealed((r) => ({ ...r, [u.id]: data.password }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const toggleActive = async (u) => {
    setBusyId(u.id);
    try {
      const data = await call(`/users/${u.id}`, { method: 'PATCH', body: { is_active: !u.is_active } });
      setUsers((list) => list.map((x) => (x.id === u.id ? data.user : x)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const counts = ROLES.map((r) => ({ ...r, total: users.filter((u) => u.role === r.value).length }));
  const q = search.trim().toLowerCase();
  const shown = users.filter((u) => (roleFilter === 'all' || u.role === roleFilter) && (!q || u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)));
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <Page>
      <PageHeader
        icon={Settings}
        title="Master · Users and Logins"
        subtitle="Create logins, type each password yourself, look passwords up, and switch access on or off."
        action={<PrimaryButton icon={Plus} onClick={() => setShowForm((v) => !v)}>{showForm ? 'Close' : 'Add User'}</PrimaryButton>}
      />

      <div className="flex items-start gap-2 bg-amber-50 border border-amber-100 text-amber-800 text-xs rounded-2xl px-4 py-3">
        <Info className="w-4 h-4 shrink-0 mt-0.5" />
        <p>Passwords you set are saved encrypted and only show here when you click <b>Show</b>. If a user changes their own password, it becomes private and shows as "Not viewable"; use <b>Set password</b> to give them a new one.</p>
      </div>

      {showForm && (
        <form onSubmit={create} className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-5 sm:p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
            <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1">Full name
              <input required className={input} value={form.name} onChange={set('name')} placeholder="Priya Sharma" />
            </label>
            <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1">Email (login)
              <input required type="email" className={input} value={form.email} onChange={set('email')} placeholder="priya@example.com" />
            </label>
            <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1">Phone
              <input className={input} value={form.phone} onChange={set('phone')} placeholder="Optional" />
            </label>
            <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1">Role
              <select className={input} value={form.role} onChange={set('role')}>
                {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </label>
            <div className="text-[11px] font-bold text-slate-500 uppercase space-y-1">
              <label htmlFor="new-user-password">Password ({MIN_PASSWORD}+ characters)</label>
              <div className="flex gap-1.5">
                <div className="relative flex-1 min-w-0">
                  <input id="new-user-password" required minLength={MIN_PASSWORD} autoComplete="off" type={showFormPassword ? 'text' : 'password'}
                    className={`${input} pr-8`} value={form.password} onChange={set('password')} placeholder="Type a password" />
                  <button type="button" onClick={() => setShowFormPassword((v) => !v)} aria-label={showFormPassword ? 'Hide password' : 'Show password'}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700">
                    {showFormPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <button type="button" title="Suggest a password (optional)" aria-label="Suggest a password"
                  onClick={() => { setForm({ ...form, password: suggestPassword() }); setShowFormPassword(true); }}
                  className="px-2.5 rounded-xl border border-slate-200 text-slate-500 hover:bg-blue-50 hover:text-blue-700 transition"><Dices className="w-4 h-4" /></button>
              </div>
            </div>
          </div>
          {formError && <p className="text-xs font-medium text-rose-600">{formError}</p>}
          <button disabled={saving} className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition">
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}<span>Create login</span>
          </button>
        </form>
      )}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white p-4 rounded-3xl border border-slate-200/80 shadow-sm">
        <div className="flex flex-wrap gap-2">
          {[{ value: 'all', label: 'All', total: users.length }, ...counts].map((r) => (
            <button key={r.value} onClick={() => setRoleFilter(r.value)} aria-pressed={roleFilter === r.value}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition ${roleFilter === r.value ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'}`}>
              {r.label} <span className="opacity-60">{r.total}</span>
            </button>
          ))}
        </div>
        <div className="relative w-full md:max-w-xs">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name or email" aria-label="Search users"
            className="w-full bg-slate-50/80 border border-slate-200/80 text-xs pl-9 pr-4 py-2 rounded-xl outline-none focus:border-blue-400" />
        </div>
      </div>

      {error && <p className="text-xs font-medium text-rose-600 bg-rose-50 border border-rose-100 rounded-2xl px-4 py-3">{error}</p>}

      {loading ? (
        <p className="p-6 text-xs text-slate-500 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Loading users…</p>
      ) : shown.length === 0 ? (
        <p className="bg-white rounded-3xl border border-slate-200/80 p-6 text-xs text-slate-500">No users match.</p>
      ) : (
        <>
          {/* Phone, tablet and laptop: one card per user */}
          <div className="xl:hidden grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4">
            {shown.map((u) => (
              <article key={u.id} className={`bg-white rounded-3xl border border-slate-200/80 shadow-sm p-4 sm:p-5 space-y-3 min-w-0 ${u.is_active ? '' : 'opacity-60'}`}>
                <div className="flex items-start gap-3 min-w-0">
                  <Initials name={u.name} className="w-10 h-10" />
                  <div className="min-w-0 flex-1">
                    <p className="font-bold text-sm text-slate-900 truncate">{u.name}{u.id === currentUserId && <span className="ml-2 text-[10px] text-blue-600 font-bold">YOU</span>}</p>
                    <p className="text-xs text-slate-400 truncate">{u.email}{u.phone ? ` · ${u.phone}` : ''}</p>
                  </div>
                  <span className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border capitalize shrink-0 ${ROLE_STYLE[u.role]}`}>{u.role}</span>
                </div>
                <dl className="grid grid-cols-3 gap-2 text-xs bg-slate-50 rounded-2xl p-3">
                  <div className="min-w-0"><dt className="text-[10px] font-bold uppercase text-slate-400">Password</dt><dd className="mt-0.5 truncate"><PasswordCell u={u} revealed={revealed} /></dd></div>
                  <div><dt className="text-[10px] font-bold uppercase text-slate-400">Status</dt><dd className="mt-0.5"><StatusText u={u} /></dd></div>
                  <div className="min-w-0"><dt className="text-[10px] font-bold uppercase text-slate-400">Last login</dt><dd className="mt-0.5 text-slate-600 truncate">{when(u.last_login_at)}</dd></div>
                </dl>
                <RowActions u={u} currentUserId={currentUserId} busyId={busyId} revealed={revealed} onReveal={toggleReveal} onSet={setPasswordFor} onToggle={toggleActive} />
              </article>
            ))}
          </div>

          {/* Wide screens: a table */}
          <div className="hidden xl:block bg-white rounded-3xl border border-slate-200/80 shadow-sm overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 text-slate-400 text-[11px] font-bold border-b border-slate-100 tracking-wider uppercase">
                <tr><th className="px-5 py-3">User</th><th className="px-5 py-3">Role</th><th className="px-5 py-3">Password</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Last login</th><th className="px-5 py-3 text-right">Actions</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {shown.map((u) => (
                  <tr key={u.id} className={u.is_active ? '' : 'opacity-60'}>
                    <td className="px-5 py-3.5 max-w-[280px]">
                      <p className="font-semibold text-slate-800 truncate">{u.name}{u.id === currentUserId && <span className="ml-2 text-[10px] text-blue-600 font-bold">YOU</span>}</p>
                      <p className="text-slate-400 truncate">{u.email}{u.phone ? ` · ${u.phone}` : ''}</p>
                    </td>
                    <td className="px-5 py-3.5"><span className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border capitalize ${ROLE_STYLE[u.role]}`}>{u.role}</span></td>
                    <td className="px-5 py-3.5"><PasswordCell u={u} revealed={revealed} /></td>
                    <td className="px-5 py-3.5"><StatusText u={u} /></td>
                    <td className="px-5 py-3.5 text-slate-500 whitespace-nowrap">{when(u.last_login_at)}</td>
                    <td className="px-5 py-3.5"><RowActions u={u} currentUserId={currentUserId} busyId={busyId} revealed={revealed} onReveal={toggleReveal} onSet={setPasswordFor} onToggle={toggleActive} end /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {passwordFor && <SetPasswordModal user={passwordFor} onSave={(pw) => savePassword(passwordFor, pw)} onClose={() => setPasswordFor(null)} />}
      {credentials && <CredentialsModal {...credentials} onClose={() => setCredentials(null)} />}
    </Page>
  );
}

// ---- pieces shared by the card and table layouts
function PasswordCell({ u, revealed }) {
  if (!u.has_password) return <span className="text-amber-600 font-semibold">Not set</span>;
  if (revealed[u.id] !== undefined) return <span className="font-mono font-bold text-slate-900 select-all break-all">{revealed[u.id]}</span>;
  if (u.can_view_password) return <span className="font-mono text-slate-400 tracking-widest">••••••••</span>;
  return <span className="text-slate-400" title="The user changed it themselves, or it was set before viewing existed">Not viewable</span>;
}

const StatusText = ({ u }) => (u.is_active ? <span className="text-emerald-600 font-semibold">Active</span> : <span className="text-slate-500 font-semibold">Disabled</span>);

function RowActions({ u, currentUserId, busyId, revealed, onReveal, onSet, onToggle, end = false }) {
  const shownNow = revealed[u.id] !== undefined;
  const btn = 'flex items-center justify-center gap-1 px-3 py-2 rounded-xl border border-slate-200 text-slate-600 font-semibold transition disabled:opacity-40 text-xs';
  return (
    <div className={`flex flex-wrap gap-2 ${end ? 'justify-end' : ''}`}>
      {u.can_view_password && (
        <button disabled={busyId === u.id} onClick={() => onReveal(u)} className={`${btn} hover:bg-blue-50 hover:text-blue-700`}>
          {shownNow ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}{shownNow ? 'Hide' : 'Show'}
        </button>
      )}
      <button onClick={() => onSet(u)} className={`${btn} hover:bg-blue-50 hover:text-blue-700`}><KeyRound className="w-3.5 h-3.5" /> Set password</button>
      <button disabled={busyId === u.id || u.id === currentUserId} onClick={() => onToggle(u)} title={u.id === currentUserId ? 'You cannot disable your own login' : ''} className={`${btn} hover:bg-slate-50`}>
        {u.is_active ? 'Disable' : 'Enable'}
      </button>
    </div>
  );
}

function SetPasswordModal({ user, onSave, onClose }) {
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await onSave(password);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4" role="dialog" aria-modal="true" aria-label="Set password">
      <form onSubmit={submit} className="bg-white border border-slate-200 rounded-3xl shadow-2xl p-5 sm:p-6 max-w-sm w-full max-h-[90dvh] overflow-y-auto space-y-4">
        <div className="flex items-start justify-between">
          <div><h3 className="text-sm font-bold text-slate-900">Set password</h3><p className="text-xs text-slate-500">{user.name} · {user.email}</p></div>
          <button type="button" onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-700"><X className="w-4 h-4" /></button>
        </div>
        <div className="flex gap-1.5">
          <div className="relative flex-1">
            <input autoFocus required minLength={MIN_PASSWORD} autoComplete="off" type={visible ? 'text' : 'password'} aria-label="New password"
              className={`${input} pr-8`} value={password} onChange={(e) => setPassword(e.target.value)} placeholder={`New password (${MIN_PASSWORD}+ characters)`} />
            <button type="button" onClick={() => setVisible((v) => !v)} aria-label={visible ? 'Hide password' : 'Show password'} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700">
              {visible ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
          <button type="button" title="Suggest a password (optional)" aria-label="Suggest a password" onClick={() => { setPassword(suggestPassword()); setVisible(true); }}
            className="px-2.5 rounded-xl border border-slate-200 text-slate-500 hover:bg-blue-50 hover:text-blue-700 transition"><Dices className="w-4 h-4" /></button>
        </div>
        <p className="text-[11px] text-slate-500">Their current password stops working as soon as you save.</p>
        {error && <p className="text-xs font-medium text-rose-600">{error}</p>}
        <button disabled={saving} className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-bold py-2.5 rounded-xl transition">
          {saving && <Loader2 className="w-4 h-4 animate-spin" />}Save password
        </button>
      </form>
    </div>
  );
}

function CredentialsModal({ name, email, password, reason, onClose }) {
  const [copied, setCopied] = useState(false);
  const text = `FinXL Placement Platform login\nName: ${name}\nEmail: ${email}\nPassword: ${password}\nSign in at: ${window.location.origin}`;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt('Copy these login details:', text);
    }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4" role="dialog" aria-modal="true" aria-label="Login details">
      <div className="bg-white border border-slate-200 rounded-3xl shadow-2xl p-5 sm:p-6 max-w-md w-full max-h-[90dvh] overflow-y-auto space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-emerald-600" /><h3 className="text-sm font-bold text-slate-900">{reason}</h3></div>
          <button onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-700"><X className="w-4 h-4" /></button>
        </div>
        <dl className="text-xs space-y-2 bg-slate-50 border border-slate-200 rounded-xl p-4">
          <div className="flex justify-between gap-3"><dt className="text-slate-400">Name</dt><dd className="font-semibold text-slate-800">{name}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-slate-400">Email</dt><dd className="font-semibold text-slate-800 break-all">{email}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-slate-400">Password</dt><dd className="font-mono font-bold text-slate-900 select-all tracking-wide">{password}</dd></div>
        </dl>
        <div className="flex gap-2.5">
          <button onClick={copy} className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold py-2.5 rounded-xl transition">
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}{copied ? 'Copied' : 'Copy login details'}
          </button>
          <button onClick={onClose} className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold py-2.5 rounded-xl transition">Done</button>
        </div>
      </div>
    </div>
  );
}
