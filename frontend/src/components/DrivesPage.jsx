import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Building2, Plus, ArrowLeft, Loader2, ChevronDown, ChevronRight, Check } from 'lucide-react';
import { API_BASE } from '../api.js';
import { BarRow, Card, Empty, Page, PageHeader, Pill, PrimaryButton } from './ui.jsx';

const API = `${API_BASE}/drives`;
const STATUS_LABEL = { draft: 'Draft', selecting: 'Selecting students', prepping: 'Preparing packs', mocking: 'Mocks running', done: 'Done' };
const STATUS_CHIP = {
  draft: 'bg-slate-50 text-slate-600 border-slate-200', selecting: 'bg-sky-50 text-sky-700 border-sky-100', prepping: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  mocking: 'bg-orange-50 text-orange-700 border-orange-100', done: 'bg-emerald-50 text-emerald-700 border-emerald-100',
};
const EMPTY_FORM = { company: '', role: '', location: '', mocks_per_student: 3, jd_text: '' };
const field = 'w-full bg-slate-50/80 border border-slate-200/80 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-400';

export default function DrivesPage({ token, onSessionExpired }) {
  const [drives, setDrives] = useState([]);
  const [openId, setOpenId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const expiredRef = useRef(onSessionExpired); // keeps `call` stable even if the parent passes a new function each render
  expiredRef.current = onSessionExpired;

  // One place for every call: adds the token, unwraps JSON, handles an expired login
  const call = useCallback(async (path = '', options = {}) => {
    const res = await fetch(API + path, {
      ...options,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) expiredRef.current?.();
    if (!res.ok) throw new Error(data.message || 'Something went wrong');
    return data;
  }, [token]);

  const loadDrives = useCallback(async () => {
    try {
      setError('');
      setDrives((await call()).drives);
    } catch (e) {
      setError(e.message === 'Failed to fetch' ? 'Cannot reach the backend. Is it running on port 3001?' : e.message);
    } finally {
      setLoading(false);
    }
  }, [call]);

  useEffect(() => { loadDrives(); }, [loadDrives]);

  if (openId) {
    return <DriveDetail id={openId} call={call} onBack={() => { setOpenId(null); loadDrives(); }} />;
  }

  return (
    <Page>
      <PageHeader
        icon={Building2}
        title="Placement Drives"
        subtitle="Add a company JD, see how every student matches, and pick who to put forward."
        action={<PrimaryButton icon={Plus} onClick={() => setShowForm((v) => !v)}>{showForm ? 'Close' : 'New Drive'}</PrimaryButton>}
      />

      {showForm && <NewDriveForm call={call} onCreated={(id) => { setShowForm(false); setOpenId(id); }} />}

      {error && <p className="text-xs font-medium text-rose-600 bg-rose-50 border border-rose-100 rounded-2xl px-4 py-3">{error}</p>}

      {loading ? (
        <p className="text-xs text-slate-500 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Loading drives…</p>
      ) : drives.length === 0 ? (
        <Card><Empty>No drives yet. Click "New Drive" to add the first company JD.</Empty></Card>
      ) : (
        <>
          {/* Phone, tablet, laptop: cards */}
          <div className="xl:hidden grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4">
            {drives.map((d) => (
              <button key={d.id} onClick={() => setOpenId(d.id)} className="text-left bg-white rounded-3xl border border-slate-200/80 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition p-4 sm:p-5 space-y-3 min-w-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0"><p className="font-bold text-sm text-slate-900 truncate">{d.company}</p><p className="text-xs text-slate-500 truncate">{d.role}</p></div>
                  <Pill className={STATUS_CHIP[d.status]}>{STATUS_LABEL[d.status] || d.status}</Pill>
                </div>
                <dl className="grid grid-cols-3 gap-2 text-xs bg-slate-50 rounded-2xl p-3">
                  <div className="min-w-0"><dt className="text-[10px] font-bold uppercase text-slate-400">Location</dt><dd className="mt-0.5 text-slate-700 truncate">{d.location || '—'}</dd></div>
                  <div><dt className="text-[10px] font-bold uppercase text-slate-400">Picked</dt><dd className="mt-0.5 text-slate-700 font-bold">{d.selected_count}</dd></div>
                  <div><dt className="text-[10px] font-bold uppercase text-slate-400">Mocks</dt><dd className="mt-0.5 text-slate-700 font-bold">{d.mocks_per_student}</dd></div>
                </dl>
              </button>
            ))}
          </div>

          {/* Wide screens: table */}
          <div className="hidden xl:block bg-white rounded-3xl border border-slate-200/80 shadow-sm overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 text-slate-400 text-[11px] font-bold border-b border-slate-100 tracking-wider uppercase">
                <tr><th className="px-5 py-3">Company</th><th className="px-5 py-3">Role</th><th className="px-5 py-3">Location</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Picked</th><th className="px-5 py-3">Mocks</th><th /></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {drives.map((d) => (
                  <tr key={d.id} onClick={() => setOpenId(d.id)} className="hover:bg-blue-50/40 cursor-pointer transition-colors">
                    <td className="px-5 py-3.5 font-semibold text-slate-800">{d.company}</td>
                    <td className="px-5 py-3.5">{d.role}</td>
                    <td className="px-5 py-3.5">{d.location || '—'}</td>
                    <td className="px-5 py-3.5"><Pill className={STATUS_CHIP[d.status]}>{STATUS_LABEL[d.status] || d.status}</Pill></td>
                    <td className="px-5 py-3.5">{d.selected_count}</td>
                    <td className="px-5 py-3.5">{d.mocks_per_student}</td>
                    <td className="px-5 py-3.5 text-slate-300"><ChevronRight className="w-4 h-4" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Page>
  );
}

function NewDriveForm({ call, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const data = await call('', { method: 'POST', body: JSON.stringify({ ...form, mocks_per_student: Number(form.mocks_per_student) }) });
      onCreated(data.drive_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-5 sm:p-6 space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1 block">Company
          <input required className={field} value={form.company} onChange={set('company')} placeholder="Acme Capital" />
        </label>
        <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1 block">Role
          <input required className={field} value={form.role} onChange={set('role')} placeholder="Financial Analyst" />
        </label>
        <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1 block">Location
          <input className={field} value={form.location} onChange={set('location')} placeholder="Mumbai" />
        </label>
        <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1 block">Mocks per student
          <select className={field} value={form.mocks_per_student} onChange={set('mocks_per_student')}>
            {[3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      </div>
      <label className="block text-[11px] font-bold text-slate-500 uppercase space-y-1">Job description
        <textarea required rows={8} className={`${field} resize-y min-h-[140px]`} value={form.jd_text} onChange={set('jd_text')} placeholder="Paste the full job description here" />
      </label>
      {error && <p className="text-xs font-medium text-rose-600">{error}</p>}
      <PrimaryButton disabled={saving} className="w-full sm:w-auto">
        {saving ? 'Reading JD and ranking students…' : 'Create drive and rank students'}
      </PrimaryButton>
    </form>
  );
}

function DriveDetail({ id, call, onBack }) {
  const [data, setData] = useState(null);
  const [picked, setPicked] = useState(new Set());
  const [expanded, setExpanded] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    call(`/${id}`).then((d) => {
      setData(d);
      setPicked(new Set(d.students.filter((s) => s.selected).map((s) => s.student_id)));
    }).catch((e) => setError(e.message));
  }, [id, call]);

  const toggle = (sid) => {
    const next = new Set(picked);
    next.has(sid) ? next.delete(sid) : next.add(sid);
    setPicked(next);
    setMessage('');
  };

  const save = async () => {
    setSaving(true);
    setError('');
    try {
      await call(`/${id}/select`, { method: 'POST', body: JSON.stringify({ student_ids: [...picked] }) });
      setMessage(`Saved ${picked.size} student${picked.size === 1 ? '' : 's'}.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const back = (
    <button onClick={onBack} className="flex items-center gap-1 text-xs font-semibold text-blue-600 hover:underline"><ArrowLeft className="w-4 h-4" /> All drives</button>
  );
  if (error && !data) return <Page>{back}<p className="text-xs text-rose-600">{error}</p></Page>;
  if (!data) return <Page>{back}<p className="text-xs text-slate-500 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Loading drive…</p></Page>;

  const { drive, students } = data;
  const req = drive.requirements || {};
  const chips = (list, cls) => (list || []).map((s) => <Pill key={s} className={cls}>{s}</Pill>);

  const reasons = (s) => (
    <div className="space-y-1.5">
      {(s.match_reasons || []).map((r) => (
        <p key={r.factor} className="text-xs text-slate-600">
          <span className="font-bold capitalize">{r.factor}</span> · {r.points}/{r.max} · {r.detail}
          {r.missing?.length > 0 && <span className="text-rose-600"> · missing: {r.missing.join(', ')}</span>}
        </p>
      ))}
    </div>
  );

  return (
    <Page>
      {back}
      <PageHeader icon={Building2} title={`${drive.company} · ${drive.role}`} subtitle={`${drive.location || 'Location not set'} · ${drive.mocks_per_student} mocks per student`} action={<Pill className={STATUS_CHIP[drive.status]}>{STATUS_LABEL[drive.status] || drive.status}</Pill>} />

      <Card title="What the JD asks for">
        <div className="flex flex-wrap gap-1.5">
          {chips(req.required_skills, 'bg-rose-50 text-rose-700 border-rose-100')}
          {chips(req.preferred_skills, 'bg-blue-50 text-blue-700 border-blue-100')}
          {req.min_experience_years > 0 && <Pill className="bg-slate-50 text-slate-600 border-slate-200">{req.min_experience_years}+ years experience</Pill>}
          {!req.required_skills?.length && !req.preferred_skills?.length && <Empty>No skills were found in this JD.</Empty>}
        </div>
      </Card>

      {/* Phone, tablet, laptop: one card per student */}
      <div className="xl:hidden grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4">
        {students.map((s) => (
          <article key={s.student_id} className={`bg-white rounded-3xl border shadow-sm p-4 sm:p-5 space-y-3 min-w-0 ${picked.has(s.student_id) ? 'border-blue-300 ring-2 ring-blue-100' : 'border-slate-200/80'}`}>
            <div className="flex items-start gap-3">
              <input type="checkbox" aria-label={`Select ${s.name}`} checked={picked.has(s.student_id)} onChange={() => toggle(s.student_id)} className="w-5 h-5 mt-0.5 accent-blue-600 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="font-bold text-sm text-slate-900 truncate">{s.name}</p>
                <p className="text-xs text-slate-400 truncate">{s.email}</p>
                <p className="text-xs text-slate-500 mt-0.5 truncate">{[s.city, (s.target_roles || []).join(', ')].filter(Boolean).join(' · ') || '—'}</p>
              </div>
              <span className="text-lg font-black text-slate-900 tabular-nums">{s.match_score}</span>
            </div>
            <BarRow label="Match" value={s.match_score} pct={s.match_score} />
            <button onClick={() => setExpanded(expanded === s.student_id ? null : s.student_id)} className="flex items-center gap-1 text-[11px] font-bold text-blue-600">
              {expanded === s.student_id ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}Why this score
            </button>
            {expanded === s.student_id && <div className="bg-slate-50 rounded-2xl p-3">{reasons(s)}</div>}
          </article>
        ))}
      </div>

      {/* Wide screens: table */}
      <div className="hidden xl:block bg-white rounded-3xl border border-slate-200/80 shadow-sm overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50/80 text-slate-400 text-[11px] font-bold border-b border-slate-100 tracking-wider uppercase">
            <tr><th className="px-5 py-3 w-10" /><th className="px-5 py-3">Student</th><th className="px-5 py-3">City</th><th className="px-5 py-3">Target role</th><th className="px-5 py-3">Match</th><th className="px-5 py-3 w-10" /></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {students.map((s) => (
              <React.Fragment key={s.student_id}>
                <tr className="hover:bg-blue-50/40 transition-colors">
                  <td className="px-5 py-3.5"><input type="checkbox" aria-label={`Select ${s.name}`} checked={picked.has(s.student_id)} onChange={() => toggle(s.student_id)} className="w-4 h-4 accent-blue-600" /></td>
                  <td className="px-5 py-3.5"><p className="font-semibold text-slate-800">{s.name}</p><p className="text-slate-400">{s.email}</p></td>
                  <td className="px-5 py-3.5">{s.city || '—'}</td>
                  <td className="px-5 py-3.5">{(s.target_roles || []).join(', ') || '—'}</td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <div className="w-28 h-2 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-blue-500 to-indigo-600" style={{ width: `${s.match_score}%` }} /></div>
                      <span className="font-bold text-slate-700 tabular-nums">{s.match_score}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <button onClick={() => setExpanded(expanded === s.student_id ? null : s.student_id)} aria-label="Show why" className="text-slate-400 hover:text-blue-600">
                      {expanded === s.student_id ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </button>
                  </td>
                </tr>
                {expanded === s.student_id && (
                  <tr className="bg-slate-50/60"><td /><td colSpan={5} className="px-5 py-3">{reasons(s)}</td></tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Stays in view on a phone so saving never needs a long scroll back */}
      <div className="sticky bottom-0 -mx-4 sm:mx-0 px-4 sm:px-0 py-3 bg-gradient-to-t from-slate-50 via-slate-50/95 to-transparent flex flex-wrap items-center gap-3">
        <PrimaryButton icon={saving ? Loader2 : Check} onClick={save} disabled={saving}>Save selection ({picked.size})</PrimaryButton>
        {message && <span className="text-xs font-medium text-emerald-600">{message}</span>}
        {error && <span className="text-xs font-medium text-rose-600">{error}</span>}
      </div>
    </Page>
  );
}
