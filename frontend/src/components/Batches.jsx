import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, BookOpen, Calendar, Check, GraduationCap, Layers, Loader2, Pencil, Plus, Search, Trash2, UserCheck, UserPlus, Users, X } from 'lucide-react';
import { api } from '../api.js';
import { BarRow, Card, Empty, Initials, Page, PageHeader, Pill, PrimaryButton } from './ui.jsx';
import { STAGE_CHIP, STAGE_LABEL } from './studentMeta.js';

const input = 'w-full bg-slate-50/80 border border-slate-200/80 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-400';
const ghostBtn = 'flex items-center justify-center gap-1.5 text-xs font-bold text-slate-600 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 transition disabled:opacity-50';
const STATUS = {
  running: { label: 'Running', chip: 'bg-emerald-50 text-emerald-700 border-emerald-100' },
  upcoming: { label: 'Upcoming', chip: 'bg-sky-50 text-sky-700 border-sky-100' },
  completed: { label: 'Completed', chip: 'bg-slate-50 text-slate-600 border-slate-200' },
};
const day = (d) => (d ? new Date(`${String(d).slice(0, 10)}T00:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : null);
const dates = (b) => (b.starts_on || b.ends_on ? `${day(b.starts_on) || '—'} to ${day(b.ends_on) || 'open'}` : 'No dates set');
const iso = (d) => (d ? String(d).slice(0, 10) : '');

function ErrorLine({ children }) {
  if (!children) return null;
  return <p role="alert" className="text-xs font-medium text-rose-600 bg-rose-50 border border-rose-100 rounded-xl px-3 py-2">{children}</p>;
}

// Batches: Admin and Operations run them; a trainer sees only the batches they are assigned to.
export default function Batches({ token, role, openStudent, onSessionExpired }) {
  const canEdit = role === 'Admin' || role === 'Operations';
  const expired = useRef(onSessionExpired);
  expired.current = onSessionExpired;
  const call = useCallback((path, opts = {}) => api(`/batches${path}`, { token, onExpired: () => expired.current?.(), ...opts }), [token]);

  const [batches, setBatches] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try { setError(''); setBatches((await call('')).batches); } catch (e) { setError(e.message); setBatches([]); }
  }, [call]);
  useEffect(() => { load(); }, [load]);

  if (openId) return <BatchDetail key={openId} id={openId} call={call} canEdit={canEdit} openStudent={openStudent} onBack={() => { setOpenId(null); load(); }} />;

  const shown = (batches || []).filter((b) => (filter === 'all' || b.status === filter) && (!search || b.name.toLowerCase().includes(search.toLowerCase())));
  const count = (s) => (batches || []).filter((b) => b.status === s).length;

  return (
    <Page>
      <PageHeader
        title="Batches" icon={Users}
        subtitle={canEdit ? 'Groups of students who start together. Every batch gets all published courses; its trainer opens the topics.' : 'The batches you teach.'}
        action={canEdit && <PrimaryButton icon={Plus} onClick={() => setCreating(true)}>New batch</PrimaryButton>}
      />
      <ErrorLine>{error}</ErrorLine>
      {creating && <BatchForm title="New batch" submitLabel="Create batch" onCancel={() => setCreating(false)} onSubmit={async (body) => { const { batch } = await call('', { method: 'POST', body }); setCreating(false); setOpenId(batch.id); }} />}

      <div className="flex flex-col md:flex-row md:items-center gap-3 bg-white p-3 sm:p-4 rounded-3xl border border-slate-200/80 shadow-sm">
        <div className="relative flex-1 min-w-0">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input className={`${input} pl-9`} placeholder="Search batches" aria-label="Search batches" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Filter by status">
          {[['all', 'All', (batches || []).length], ['running', 'Running', count('running')], ['upcoming', 'Upcoming', count('upcoming')], ['completed', 'Completed', count('completed')]].map(([k, label, n]) => (
            <button key={k} role="tab" aria-selected={filter === k} onClick={() => setFilter(k)} className={`text-xs font-bold px-3 py-2 rounded-xl border transition ${filter === k ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'}`}>{label} <span className="opacity-70">{n}</span></button>
          ))}
        </div>
      </div>

      {batches === null ? <div className="flex justify-center py-16"><Loader2 className="w-5 h-5 animate-spin text-slate-400" /></div> : shown.length === 0 ? (
        <Card title={batches.length === 0 ? 'No batches yet' : 'No batches match'} icon={Users}>
          <Empty>{batches.length === 0 ? (canEdit ? 'Create the first batch, or import students with a Batch column and they are created for you.' : 'You are not assigned to any batch yet. The admin or operations team assigns them.') : 'Try another filter or search.'}</Empty>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-5">
          {shown.map((b) => (
            <button key={b.id} onClick={() => setOpenId(b.id)} className="text-left bg-white p-5 rounded-3xl border border-slate-200/80 shadow-sm hover:shadow-md hover:border-blue-200 transition space-y-3.5">
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-sm font-bold text-slate-900 min-w-0 break-words">{b.name}</h3>
                <Pill className={STATUS[b.status].chip}>{STATUS[b.status].label}</Pill>
              </div>
              <p className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5 shrink-0" />{dates(b)}</p>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div><p className="text-slate-400 font-semibold">Students</p><p className="text-lg font-extrabold text-slate-900 tabular-nums">{b.students}</p></div>
                <div><p className="text-slate-400 font-semibold">Job ready</p><p className="text-lg font-extrabold text-emerald-600 tabular-nums">{b.job_ready}</p></div>
              </div>
              <BarRow label="Topics opened" value={b.topics_open} shown={`${b.topics_open} / ${b.topics_total}`} pct={b.topics_total ? (b.topics_open / b.topics_total) * 100 : 0} tone="blue" />
              <p className="text-[11px] text-slate-500 flex items-center gap-1.5 min-w-0"><UserCheck className="w-3.5 h-3.5 shrink-0 text-slate-400" /><span className="truncate">{b.trainers.length ? b.trainers.map((t) => t.name).join(', ') : 'No trainer assigned'}</span></p>
            </button>
          ))}
        </div>
      )}
    </Page>
  );
}

// Name + dates, used to create a batch and to edit one
function BatchForm({ title, initial, submitLabel, onSubmit, onCancel }) {
  const [f, setF] = useState({ name: initial?.name || '', starts_on: iso(initial?.starts_on), ends_on: iso(initial?.ends_on) });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('');
    try { await onSubmit({ name: f.name, starts_on: f.starts_on || null, ends_on: f.ends_on || null }); } catch (err) { setError(err.message); setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="bg-white p-5 sm:p-6 rounded-3xl border border-blue-100 shadow-sm space-y-3">
      <h2 className="text-sm font-bold text-slate-900">{title}</h2>
      <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr] gap-3">
        <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Batch name<input className={input} placeholder="e.g. Batch Nov-26" value={f.name} onChange={set('name')} autoFocus /></label>
        <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Starts on (optional)<input type="date" className={input} value={f.starts_on} onChange={set('starts_on')} /></label>
        <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Ends on (optional)<input type="date" className={input} value={f.ends_on} onChange={set('ends_on')} /></label>
      </div>
      <ErrorLine>{error}</ErrorLine>
      <div className="flex gap-2 justify-end">
        <button type="button" className={ghostBtn} onClick={onCancel}>Cancel</button>
        <PrimaryButton type="submit" disabled={busy || !f.name.trim()}>{busy ? 'Saving…' : submitLabel}</PrimaryButton>
      </div>
    </form>
  );
}

function BatchDetail({ id, call, canEdit, openStudent, onBack }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [trainerPick, setTrainerPick] = useState('');
  const [picked, setPicked] = useState(() => new Set()); // students ticked for a bulk move
  const [others, setOthers] = useState([]);              // the other batches they can move to
  const [target, setTarget] = useState('');

  const load = useCallback(async () => {
    try { setData(await call(`/${id}`)); } catch (e) { setError(e.message); }
  }, [call, id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!canEdit) return;
    call('').then((r) => setOthers(r.batches.filter((b) => b.id !== id))).catch(() => {});
  }, [call, canEdit, id]);

  const act = async (fn) => {
    setBusy(true); setError('');
    try { await fn(); await load(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  if (!data) return <Page>{error ? <ErrorLine>{error}</ErrorLine> : <div className="flex justify-center py-16"><Loader2 className="w-5 h-5 animate-spin text-slate-400" /></div>}<button className={ghostBtn} onClick={onBack}><ArrowLeft className="w-4 h-4" />Back</button></Page>;
  const { batch, students, trainers, available_trainers: available, courses } = data;
  const everyone = students.length > 0 && picked.size === students.length;
  const toggleAll = () => setPicked(everyone ? new Set() : new Set(students.map((s) => s.id)));
  const toggleOne = (sid) => setPicked((p) => { const n = new Set(p); if (n.has(sid)) n.delete(sid); else n.add(sid); return n; });
  const targetName = others.find((b) => b.id === target)?.name;
  const move = () => {
    const all = everyone;
    if (!window.confirm(`Move ${all ? `all ${students.length} students` : `${picked.size} student${picked.size === 1 ? '' : 's'}`} from ${batch.name} to ${targetName}?`)) return;
    act(async () => { await call(`/${id}/move`, { method: 'POST', body: { target_id: target, ...(all ? {} : { student_ids: [...picked] }) } }); setPicked(new Set()); setTarget(''); });
  };
  const jobReady = students.filter((s) => s.stage === 'job_ready' || s.stage === 'placed').length;

  return (
    <Page>
      <PageHeader
        title={batch.name} icon={Users}
        subtitle={`${dates(batch)} · ${students.length} student${students.length === 1 ? '' : 's'} · ${jobReady} job ready`}
        action={<div className="flex gap-2 flex-wrap">
          {canEdit && <button className={ghostBtn} onClick={() => setEditing(true)}><Pencil className="w-4 h-4" />Edit</button>}
          <button className={ghostBtn} onClick={onBack}><ArrowLeft className="w-4 h-4" />All batches</button>
        </div>}
      >
        <div className="mt-2"><Pill className={STATUS[batch.status].chip}>{STATUS[batch.status].label}</Pill></div>
      </PageHeader>
      <ErrorLine>{error}</ErrorLine>
      {editing && <BatchForm title="Edit batch" initial={batch} submitLabel="Save changes" onCancel={() => setEditing(false)} onSubmit={async (body) => { await call(`/${id}`, { method: 'PATCH', body }); setEditing(false); await load(); }} />}

      <div className="grid grid-cols-1 xl:grid-cols-3 items-start gap-5 sm:gap-6">
        <div className="xl:col-span-2 space-y-5 sm:space-y-6">
          <Card title={`Students (${students.length})`} icon={GraduationCap} action={canEdit && <button className="flex items-center gap-1 text-[11px] font-bold text-blue-600 hover:underline" onClick={() => setAdding((v) => !v)}><UserPlus className="w-3.5 h-3.5" />{adding ? 'Close' : 'Add students'}</button>}>
            {adding && <AddStudents batchId={id} call={call} onDone={async () => { setAdding(false); await load(); }} />}
            {canEdit && students.length > 0 && (
              <div className="flex flex-col md:flex-row md:items-center gap-3 mb-2 pb-3 border-b border-slate-100">
                <label className="flex items-center gap-2 text-xs font-bold text-slate-600 cursor-pointer"><input type="checkbox" checked={everyone} onChange={toggleAll} className="w-4 h-4 accent-blue-600" />{everyone ? 'Everyone selected' : 'Select all'}</label>
                {picked.size > 0 && (
                  <div className="flex flex-col sm:flex-row gap-2 md:ml-auto md:min-w-[22rem]">
                    <select className={input} aria-label="Move to batch" value={target} onChange={(e) => setTarget(e.target.value)}>
                      <option value="">{others.length ? `Move ${picked.size} to…` : 'No other batch to move to'}</option>
                      {others.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                    </select>
                    <button disabled={busy || !target} className={ghostBtn} onClick={move}>Move</button>
                  </div>
                )}
              </div>
            )}
            {students.length === 0 ? <Empty>No students in this batch yet.</Empty> : (
              <ul className="divide-y divide-slate-100">
                {students.map((s) => (
                  <li key={s.id} className="flex items-center justify-between gap-3 py-2.5">
                    {canEdit && <input type="checkbox" aria-label={`Select ${s.name}`} checked={picked.has(s.id)} onChange={() => toggleOne(s.id)} className="w-4 h-4 accent-blue-600 shrink-0" />}
                    <button onClick={() => openStudent?.(s.id)} className="flex items-center gap-2.5 min-w-0 text-left hover:opacity-80 flex-1">
                      <Initials name={s.name} />
                      <span className="min-w-0 text-xs"><span className="font-bold text-slate-900 block truncate">{s.name}</span><span className="text-slate-400 block truncate">{s.student_code || 'No ID yet'}{s.city ? ` · ${s.city}` : ''}</span></span>
                    </button>
                    <span className="flex items-center gap-2 shrink-0">
                      <Pill className={STAGE_CHIP[s.stage]}>{STAGE_LABEL[s.stage]}</Pill>
                      {canEdit && <button disabled={busy} aria-label={`Remove ${s.name}`} className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition" onClick={() => { if (window.confirm(`Remove ${s.name} from ${batch.name}?`)) act(() => call(`/${id}/students/${s.id}`, { method: 'DELETE' })); }}><X className="w-4 h-4" /></button>}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="space-y-5 sm:space-y-6">
          <Card title="Trainers" icon={UserCheck}>
            {trainers.length === 0 ? <Empty>No trainer yet. A trainer must be assigned before topics can be opened for this batch.</Empty> : (
              <ul className="divide-y divide-slate-100">
                {trainers.map((t) => (
                  <li key={t.id} className="flex items-center justify-between gap-3 py-2.5 text-xs">
                    <span className="flex items-center gap-2.5 min-w-0"><Initials name={t.name} /><span className="min-w-0"><span className="font-bold text-slate-900 block truncate">{t.name}</span><span className="text-slate-400 block truncate">{t.email}</span></span></span>
                    {canEdit && <button disabled={busy} aria-label={`Remove ${t.name}`} className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition" onClick={() => act(() => call(`/${id}/trainers/${t.id}`, { method: 'DELETE' }))}><X className="w-4 h-4" /></button>}
                  </li>
                ))}
              </ul>
            )}
            {canEdit && (
              <div className="flex gap-2 pt-3">
                <select className={input} aria-label="Trainer to add" value={trainerPick} onChange={(e) => setTrainerPick(e.target.value)} disabled={available.length === 0}>
                  <option value="">{available.length ? 'Add a trainer…' : 'No more trainers to add'}</option>
                  {available.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
                <button disabled={busy || !trainerPick} className={ghostBtn} onClick={() => act(async () => { await call(`/${id}/trainers`, { method: 'POST', body: { trainer_id: trainerPick } }); setTrainerPick(''); })}><Plus className="w-4 h-4" />Add</button>
              </div>
            )}
          </Card>

          <Card title="Learning progress" icon={BookOpen}>
            {courses.length === 0 ? <Empty>No published courses yet.</Empty> : (
              <div className="space-y-3.5">
                {courses.map((c) => <BarRow key={c.id} label={c.title} value={c.released} shown={`${c.released} / ${c.modules} topics open`} pct={c.modules ? (c.released / c.modules) * 100 : 0} tone="blue" />)}
              </div>
            )}
          </Card>
        </div>
      </div>

      {canEdit && (
        <div className="pt-4 border-t border-slate-200/70 flex justify-end">
          <button disabled={busy} className="flex items-center gap-1.5 text-xs font-bold text-rose-600 hover:bg-rose-50 border border-rose-100 rounded-xl px-3 py-2 transition"
            onClick={() => { if (window.confirm(`Delete ${batch.name}?`)) act(async () => { await call(`/${id}`, { method: 'DELETE' }); onBack(); }); }}>
            <Trash2 className="w-4 h-4" />Delete batch
          </button>
        </div>
      )}
    </Page>
  );
}

// Search students (those with no batch first), tick some, add them
function AddStudents({ batchId, call, onDone }) {
  const [text, setText] = useState('');
  const [list, setList] = useState(null);
  const [picked, setPicked] = useState(() => new Set());
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    const t = setTimeout(async () => {
      try { const r = await call(`/${batchId}/candidates?q=${encodeURIComponent(text)}`); if (live) setList(r.students); } catch (e) { if (live) setError(e.message); }
    }, 250);
    return () => { live = false; clearTimeout(t); };
  }, [call, batchId, text]);

  const toggle = (id) => setPicked((p) => { const n = new Set(p); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const add = async () => {
    setBusy(true); setError('');
    try { await call(`/${batchId}/students`, { method: 'POST', body: { student_ids: [...picked] } }); await onDone(); } catch (e) { setError(e.message); setBusy(false); }
  };

  return (
    <div className="mb-4 bg-blue-50/40 border border-blue-100 rounded-2xl p-4 space-y-3">
      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <input className={`${input} pl-9`} placeholder="Search by name, email or student ID" aria-label="Search students to add" value={text} onChange={(e) => setText(e.target.value)} autoFocus />
      </div>
      <ErrorLine>{error}</ErrorLine>
      {list === null ? <Loader2 className="w-4 h-4 animate-spin text-slate-400 mx-auto" /> : list.length === 0 ? <Empty>No students found.</Empty> : (
        <ul className="max-h-64 overflow-y-auto divide-y divide-blue-100/60 bg-white rounded-xl border border-blue-100">
          {list.map((s) => (
            <li key={s.id}>
              <label className="flex items-center gap-3 px-3 py-2.5 text-xs cursor-pointer hover:bg-slate-50">
                <input type="checkbox" checked={picked.has(s.id)} onChange={() => toggle(s.id)} className="w-4 h-4 accent-blue-600" />
                <span className="min-w-0 flex-1"><span className="font-bold text-slate-900 block truncate">{s.name}</span><span className="text-slate-400 block truncate">{s.student_code || s.email}</span></span>
                {s.current_batch && <span className="text-[11px] text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-2 py-0.5 shrink-0">now in {s.current_batch}</span>}
              </label>
            </li>
          ))}
        </ul>
      )}
      <div className="flex justify-end">
        <PrimaryButton icon={Check} disabled={busy || picked.size === 0} onClick={add}>{busy ? 'Adding…' : `Add ${picked.size || ''} student${picked.size === 1 ? '' : 's'}`}</PrimaryButton>
      </div>
    </div>
  );
}
