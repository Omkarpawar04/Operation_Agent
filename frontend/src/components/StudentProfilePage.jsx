import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft, Pencil, Loader2, Mail, Phone, MapPin, GraduationCap, Building2, Video, FileText, Award, X, Send,
  AlertTriangle, CheckCircle2, Clock, BookOpen, Briefcase, Layers,
} from 'lucide-react';
import { api } from '../api.js';
import { BarRow, Card, Empty, Initials, Kpi, KpiGrid, Page, Pill } from './ui.jsx';
import { STAGES, STAGE_CHIP, STAGE_LABEL, fmtDate, fmtDateTime } from './studentMeta.js';
import MyDetailsModal from './MyDetailsModal.jsx';

const KIND = { mock: 'Mock interview', doubt: 'Doubt clearing', final_mock: 'Final mock', ai_mock: 'AI mock' };
const SESSION_CHIP = {
  scheduled: 'bg-sky-50 text-sky-700 border-sky-100', done: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  missed: 'bg-rose-50 text-rose-700 border-rose-100', rescheduled: 'bg-amber-50 text-amber-700 border-amber-100', cancelled: 'bg-slate-50 text-slate-500 border-slate-200',
};
const DRIVE_CHIP = { ranked: 'bg-slate-50 text-slate-600 border-slate-200', pack_review: 'bg-indigo-50 text-indigo-700 border-indigo-100', mocking: 'bg-orange-50 text-orange-700 border-orange-100', report_ready: 'bg-sky-50 text-sky-700 border-sky-100', put_forward: 'bg-emerald-50 text-emerald-700 border-emerald-100' };
const DRIVE_LABEL = { ranked: 'Ranked', pack_review: 'Pack in review', mocking: 'Mocks running', report_ready: 'Report ready', put_forward: 'Put forward' };
const VERDICT = { job_ready: 'Job ready', one_more_mock: 'One more mock', not_ready: 'Not ready' };
const field = 'w-full bg-slate-50/80 border border-slate-200/80 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-400';

// One student's whole record. `studentId` is a student id, or "me" for a student looking at themselves.
export default function StudentProfilePage({ token, role, studentId, onBack, openDetailsOnLoad, onDetailsOpened, onSessionExpired }) {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('overview');
  const [editing, setEditing] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const expiredRef = useRef(onSessionExpired);
  expiredRef.current = onSessionExpired;
  const isOps = role === 'Operations' || role === 'Admin';
  const isStudent = role === 'Student';

  const call = useCallback((path, options = {}) => api(path, { token, onExpired: () => expiredRef.current?.(), ...options }), [token]);
  const base = isStudent ? '/students/me' : `/students/${studentId}`;

  const load = useCallback(async () => {
    setProfile(null);
    setError('');
    try {
      setProfile((await call(base)).profile);
    } catch (e) {
      setError(e.message);
    }
  }, [call, base]);
  useEffect(() => { load(); setTab('overview'); }, [load]);
  // Re-read the record without blanking the page (used after something is logged, like viewing ID numbers)
  const refresh = useCallback(async () => {
    try { setProfile((await call(base)).profile); } catch { /* the page keeps what it has */ }
  }, [call, base]);
  // The dashboard's "Fill my details" button lands here and opens the form straight away
  useEffect(() => {
    if (openDetailsOnLoad && profile) { setDetailsOpen(true); onDetailsOpened?.(); }
  }, [openDetailsOnLoad, profile, onDetailsOpened]);

  const back = !isStudent && onBack && (
    <button onClick={onBack} className="flex items-center gap-1 text-xs font-semibold text-blue-600 hover:underline"><ArrowLeft className="w-4 h-4" /> All students</button>
  );
  if (error) return <Page>{back}<p className="text-xs font-medium text-rose-600 bg-rose-50 border border-rose-100 rounded-2xl px-4 py-3">{error} <button onClick={load} className="underline font-bold ml-1">Try again</button></p></Page>;
  if (!profile) return <Page>{back}<p className="text-xs text-slate-500 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Loading the student record…</p></Page>;

  const p = profile;
  const x = p.extra || {};
  const done = p.sessions.filter((s) => s.status === 'done').length;
  const tabs = [
    ['overview', 'Overview'], ['mocks', `Mocks (${p.sessions.length})`], ['jobs', `Drives and jobs (${p.drives.length + p.placements.length})`],
    ['activity', isOps ? `Notes and activity` : 'Activity'],
  ];

  return (
    <Page>
      {back}

      <section className="bg-white p-5 sm:p-6 rounded-3xl border border-slate-200/80 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-start gap-4 md:gap-6">
          <Initials name={p.name} className="w-16 h-16 text-lg" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight break-words">{p.name}</h1>
              <Pill className={STAGE_CHIP[p.stage]}>{STAGE_LABEL[p.stage]}</Pill>
              {!isStudent && <Pill className={p.completeness.percent >= 100 ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-amber-50 text-amber-700 border-amber-100'}>Profile {p.completeness.percent}%</Pill>}
              {!p.is_active && <Pill className="bg-slate-100 text-slate-500 border-slate-200">Login disabled</Pill>}
            </div>
            <p className="text-xs text-slate-500">
              <span className="font-mono font-semibold text-slate-700">{p.student_code}</span>
              {p.batch && <> · {p.batch}</>}{p.course && <> · {p.course}</>}
            </p>
            <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-slate-600">
              <a href={`mailto:${p.email}`} className="flex items-center gap-1.5 hover:text-blue-600 min-w-0"><Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" /><span className="truncate">{p.email}</span></a>
              {p.phone && <a href={`tel:${p.phone}`} className="flex items-center gap-1.5 hover:text-blue-600"><Phone className="w-3.5 h-3.5 text-slate-400" />{p.phone}</a>}
              {p.city && <span className="flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5 text-slate-400" />{p.city}</span>}
            </div>
          </div>
          {isOps && (
            <button onClick={() => setEditing(true)} className="flex items-center justify-center gap-2 text-xs font-bold text-slate-700 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 border border-slate-200 rounded-xl px-4 py-2.5 transition shrink-0">
              <Pencil className="w-3.5 h-3.5" /> Edit profile
            </button>
          )}
          {isStudent && (
            <button onClick={() => setDetailsOpen(true)} className="flex items-center justify-center gap-2 text-xs font-bold text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-sky-500 hover:brightness-105 shadow-md shadow-blue-500/20 rounded-xl px-4 py-2.5 transition shrink-0">
              <Pencil className="w-3.5 h-3.5" /> {p.completeness.percent < 100 ? 'Fill my details' : 'Update my details'}
            </button>
          )}
        </div>
      </section>

      {isStudent && p.completeness.percent < 100 && (
        <section className="bg-white p-5 sm:p-6 rounded-3xl border border-blue-100 shadow-sm space-y-3" aria-label="Complete your profile">
          <div className="flex items-center justify-between gap-3"><h2 className="text-sm font-bold text-slate-900">Your profile is {p.completeness.percent}% complete</h2><span className="text-xs font-bold text-blue-600 tabular-nums">{8 - p.completeness.missing.length} / 8</span></div>
          <BarRow label="Completeness" value={p.completeness.percent} shown={`${p.completeness.percent}%`} pct={p.completeness.percent} tone={p.completeness.percent >= 50 ? 'blue' : 'amber'} />
          <p className="text-xs text-slate-600">Companies are matched to you using your skills and the roles you want, so the more you fill in, the more drives you can be put forward for. Still to add:</p>
          <div className="flex flex-wrap gap-1.5">{p.completeness.missing.map((m) => <Pill key={m.key} className="bg-amber-50 text-amber-700 border-amber-100">{m.label.replace(/ \(.*\)/, '')}</Pill>)}</div>
        </section>
      )}

      {p.flags.length > 0 && (
        <div className="bg-amber-50/70 border border-amber-100 rounded-2xl px-4 py-3 space-y-1.5" role="note" aria-label="Things to look at">
          <p className="flex items-center gap-1.5 text-[11px] font-bold text-amber-800 uppercase tracking-wider"><AlertTriangle className="w-3.5 h-3.5" />Worth a look</p>
          <ul className="text-xs text-amber-900 space-y-1 list-disc pl-5">{p.flags.map((f) => <li key={f}>{f}</li>)}</ul>
        </div>
      )}

      <KpiGrid>
        <Kpi label="Stage" value={STAGE_LABEL[p.stage]} icon={GraduationCap} tone="blue" />
        <Kpi label="Level" value={`${p.level} / 5`} icon={Award} tone="violet" />
        <Kpi label="Mocks done" value={done} icon={Video} tone="sky" hint={`${p.sessions.length} booked`} />
        <Kpi label="Drives" value={p.drives.length} icon={Building2} tone="indigo" />
        <Kpi label="Videos passed" value={p.learning.videos_passed} icon={BookOpen} tone="emerald" />
        <Kpi label="Resumes" value={p.resumes.length} icon={FileText} tone="amber" />
      </KpiGrid>

      <div className="flex gap-1 overflow-x-auto border-b border-slate-200 -mx-1 px-1" role="tablist">
        {tabs.map(([id, label]) => (
          <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
            className={`px-4 py-2.5 text-xs font-bold whitespace-nowrap border-b-2 -mb-px transition ${tab === id ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>{label}</button>
        ))}
      </div>

      {tab === 'overview' && <Overview p={p} x={x} isOps={isOps} role={role} call={call} refresh={refresh} />}
      {tab === 'mocks' && <Mocks p={p} />}
      {tab === 'jobs' && <Jobs p={p} />}
      {tab === 'activity' && <Activity p={p} isOps={isOps} call={call} studentId={p.id} onChange={setProfile} />}

      {detailsOpen && <MyDetailsModal token={token} profile={p} onClose={() => setDetailsOpen(false)} onSaved={(np) => { setProfile(np); setDetailsOpen(false); }} onSessionExpired={() => expiredRef.current?.()} />}
      {editing && <EditModal p={p} call={call} onClose={() => setEditing(false)} onSaved={(np) => { setProfile(np); setEditing(false); }} />}
    </Page>
  );
}

const Row = ({ label, children }) => (children ? (
  <div className="flex items-start justify-between gap-4 py-2.5 text-xs border-b border-slate-100 last:border-0">
    <dt className="text-slate-400 font-semibold shrink-0">{label}</dt><dd className="text-slate-800 font-medium text-right break-words min-w-0">{children}</dd>
  </div>
) : null);

function Overview({ p, x, isOps, role, call, refresh }) {
  const at = Math.max(0, STAGES.indexOf(p.stage));
  const other = Object.entries(x.other || {});
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 items-start gap-5 sm:gap-6">
      <Card title="About" icon={GraduationCap}>
        <dl>
          <Row label="College">{p.college}</Row>
          <Row label="Degree">{p.degree}{x.postgraduation ? ` · ${x.postgraduation}` : ''}</Row>
          <Row label="Experience">{x.experience_years !== undefined && x.experience_years !== null ? `${x.experience_years} year${x.experience_years === 1 ? '' : 's'}` : null}</Row>
          <Row label="Target roles">{p.target_roles.join(', ')}</Row>
          <Row label="Course mode">{x.course_mode}</Row>
          <Row label="Experience note">{x.experience_note}</Row>
          <Row label="State">{x.state}</Row>
          <Row label="Gender">{x.gender}</Row>
          <Row label="Admitted">{x.admission_date ? fmtDate(x.admission_date) : null}</Row>
          <Row label="WhatsApp">{x.whatsapp}</Row>
          <Row label="LinkedIn">{x.linkedin ? <a href={/^https?:/.test(x.linkedin) ? x.linkedin : `https://${x.linkedin}`} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">{x.linkedin}</a> : null}</Row>
          {isOps && <>
            <Row label="Date of birth">{x.dob ? fmtDate(x.dob) : null}</Row>
            <Row label="Address">{x.address}</Row>
            <Row label="Parent / guardian">{[x.parent_name, x.parent_phone].filter(Boolean).join(' · ')}</Row>
            <Row label="Counsellor">{x.counsellor}</Row>
            <Row label="Referred by">{x.reference_of}</Row>
            <Row label="Telegram">{x.telegram}</Row>
            <Row label="Status in the old system">{x.source_status}</Row>
            <DocumentsRow p={p} call={call} onViewed={refresh} />
          </>}
        </dl>
        <div className="space-y-2 pt-1">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Skills</p>
          {(x.skills || []).length ? <div className="flex flex-wrap gap-1.5">{x.skills.map((s) => <Pill key={s} className="bg-blue-50 text-blue-700 border-blue-100">{s}</Pill>)}</div>
            : <p className="text-xs text-slate-400">No skills added yet. Drive rankings use these, so add them{isOps ? ' with Edit profile' : ''}.</p>}
        </div>
        {isOps && other.length > 0 && (
          <details className="pt-1"><summary className="text-xs font-bold text-blue-600 cursor-pointer">More columns from the Excel ({other.length})</summary>
            <dl className="mt-2">{other.map(([k, v]) => <Row key={k} label={k}>{v}</Row>)}</dl></details>
        )}
      </Card>

      <div className="space-y-5 sm:space-y-6 min-w-0">
        {!['Student'].includes(role) && <TeamUpdates p={p} x={x} role={role} call={call} refresh={refresh} />}
        <Card title="Journey" icon={Layers}>
          <ol className="space-y-2">
            {STAGES.map((s, i) => (
              <li key={s} className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 text-xs font-semibold ${i < at ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : i === at ? 'bg-blue-600 border-blue-600 text-white shadow-md shadow-blue-500/20' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                {i < at ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <span className="w-4 h-4 rounded-full border-2 border-current shrink-0 opacity-60" />}{STAGE_LABEL[s]}
                {i === at && <span className="ml-auto text-[10px] uppercase tracking-wider opacity-80">Now</span>}
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Learning progress" icon={BookOpen}>
          <BarRow label="Videos passed" value={p.learning.videos_passed} pct={0} />
          <p className="text-xs text-slate-500">Quiz attempts: <b className="text-slate-700">{p.learning.quiz_attempts}</b> · Speaking practice sessions: <b className="text-slate-700">{p.learning.comms_sessions}</b></p>
          <p className="text-[11px] text-slate-400">Course videos and quizzes are not switched on yet. Progress will fill in here automatically.</p>
        </Card>
      </div>
    </div>
  );
}

const TEAM_SECTIONS = [
  {
    id: 'operations', title: 'Operations update', roles: ['Operations', 'Admin'],
    fields: [
      ['student_status', 'Student status', 'select', ['Active', 'Inactive', 'Left Between']],
      ['attendance', 'Attendance', 'select', ['Good', 'Average', 'Bad']],
      ['course_completion', 'Course completion', 'select', ['Less Than 25%', '25%', '50%', '75%', '100%']],
      ['operations_remark', 'Remark for placement team', 'text'],
      ['current_ctc', 'Current / previous CTC', 'text'], ['expected_ctc', 'Expected CTC', 'text'],
      ['education_detail', 'Education details', 'text'], ['current_location', 'Current location', 'text'],
      ['preferred_location', 'Preferred job location', 'text'],
    ],
  },
  {
    id: 'trainer', title: 'Trainer / Mock Team update', roles: ['Trainer', 'Admin'],
    fields: [
      ['mock_count', 'Mocks given', 'number'], ['mock_remark', 'Mock preparation remark', 'text'],
      ['mock_final_status', 'Final readiness', 'select', ['Placement Ready', 'Partially Prepared', 'Not Ready for Placement']],
      ['technical_feedback', 'Technical feedback', 'text'], ['mock_final_remark', 'Final communication remark', 'text'],
    ],
  },
  {
    id: 'placement', title: 'Placement update', roles: ['Placement', 'Admin'],
    fields: [
      ['opportunities_given', 'Opportunities given', 'number'], ['interview_feedback', 'Interview feedback', 'text'],
      ['placement_status', 'Placement status', 'select', ['Placed', 'Not Placed', 'Not Eligible For Placement']],
      ['placement_remark', 'Placement remark', 'text'],
    ],
  },
  { id: 'admin', title: 'Management update', roles: ['Admin'], fields: [['management_remark', 'Management / Priyanka remark', 'text']] },
];

function TeamUpdates({ p, x, role, call, refresh }) {
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const open = (section) => { setEditing(section.id); setDraft(Object.fromEntries(section.fields.map(([key]) => [key, x[key] ?? '']))); setError(''); };
  const save = async () => {
    setSaving(true); setError('');
    try {
      await call(`/students/${p.id}/team-update`, { method: 'PATCH', body: { updates: draft } });
      setEditing(null); await refresh();
    } catch (e) { setError(e.message); } finally { setSaving(false); }
  };
  return (
    <div className="space-y-5 sm:space-y-6">
      {TEAM_SECTIONS.map((section) => {
        const canEdit = section.roles.includes(role);
        const hasValue = section.fields.some(([key]) => x[key] !== undefined && x[key] !== '');
        if (!canEdit && !hasValue) return null;
        return (
          <Card key={section.id} title={section.title} icon={FileText}>
            {editing === section.id ? (
              <div className="space-y-3">
                {section.fields.map(([key, label, type, options]) => (
                  <label key={key} className="block text-[11px] font-bold text-slate-500 uppercase space-y-1">
                    {label}
                    {type === 'select' ? <select className={field} value={draft[key] ?? ''} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}><option value="">Not set</option>{options.map((v) => <option key={v} value={v}>{v}</option>)}</select>
                      : type === 'number' ? <input className={field} type="number" min="0" step="1" value={draft[key] ?? ''} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} />
                        : <textarea className={`${field} min-h-20 resize-y normal-case font-medium text-slate-800`} value={draft[key] ?? ''} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} />}
                  </label>
                ))}
                {error && <p className="text-xs text-rose-600">{error}</p>}
                <div className="flex justify-end gap-2"><button onClick={() => setEditing(null)} className="px-3 py-2 text-xs font-bold text-slate-600">Cancel</button><button disabled={saving} onClick={save} className="px-3 py-2 rounded-xl text-xs font-bold text-white bg-blue-600 disabled:opacity-60">{saving ? 'Saving…' : 'Save update'}</button></div>
              </div>
            ) : (
              <>
                <dl>{section.fields.map(([key, label]) => <Row key={key} label={label}>{x[key]}</Row>)}</dl>
                {canEdit && <button onClick={() => open(section)} className="mt-3 text-xs font-bold text-blue-600 hover:underline">Update {section.id === 'trainer' ? 'mock assessment' : section.title.toLowerCase()}</button>}
              </>
            )}
          </Card>
        );
      })}
    </div>
  );
}

function DocumentsRow({ p, call, onViewed }) {
  const [full, setFull] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (!p.documents || (!p.documents.aadhaar && !p.documents.pan)) return null;

  const toggle = async () => {
    if (full) return setFull(null);
    setBusy(true);
    setError('');
    try {
      setFull(await call(`/students/${p.id}/documents`));
      onViewed?.(); // the view is now on the timeline
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const aadhaar = full?.aadhaar ? full.aadhaar.replace(/(\d{4})(\d{4})(\d{4})/, '$1 $2 $3') : p.documents.aadhaar;
  return (
    <div className="py-2.5 text-xs border-b border-slate-100 space-y-1.5">
      <div className="flex items-start justify-between gap-4">
        <dt className="text-slate-400 font-semibold shrink-0">ID numbers</dt>
        <dd className="text-right min-w-0 space-y-0.5">
          {p.documents.aadhaar && <p className="font-mono font-semibold text-slate-800 break-all">Aadhaar {aadhaar}</p>}
          {p.documents.pan && <p className="font-mono font-semibold text-slate-800 break-all">PAN {full?.pan || p.documents.pan}</p>}
        </dd>
      </div>
      <div className="flex items-center justify-end gap-3">
        {error && <span className="text-rose-600 font-medium">{error}</span>}
        <button onClick={toggle} disabled={busy} className="text-blue-600 font-bold hover:underline disabled:opacity-50">{busy ? 'Loading…' : full ? 'Hide' : 'Show full numbers'}</button>
      </div>
      {!full && <p className="text-[11px] text-slate-400 text-right">Saved encrypted. Showing them is recorded on the timeline.</p>}
    </div>
  );
}

function Mocks({ p }) {
  if (!p.sessions.length) return <Card><Empty>No mocks booked yet. They appear here once the placement team schedules them.</Empty></Card>;
  return (
    <Card title="Mocks and doubt sessions" icon={Video}>
      <ul className="divide-y divide-slate-100">
        {p.sessions.map((s) => (
          <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-xs">
            <div className="min-w-0"><p className="font-bold text-slate-900">{KIND[s.kind] || s.kind}{s.mock_number ? ` ${s.mock_number}` : ''}</p>
              <p className="text-slate-400 flex items-center gap-1"><Clock className="w-3 h-3" />{fmtDateTime(s.starts_at)}{s.trainer ? ` · ${s.trainer}` : ''}</p></div>
            <div className="flex items-center gap-2">
              {s.score !== null && s.score !== undefined && <span className="font-black text-slate-800 tabular-nums">{Number(s.score).toFixed(1)}<span className="text-slate-400 font-medium"> / 10</span></span>}
              <Pill className={SESSION_CHIP[s.status]}>{s.status}</Pill>
              {s.meeting_url && s.status === 'scheduled' && <a href={s.meeting_url} target="_blank" rel="noreferrer" className="text-blue-600 font-bold hover:underline">Join</a>}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Jobs({ p }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 items-start gap-5 sm:gap-6">
      <Card title="Company drives" icon={Building2}>
        {p.drives.length === 0 ? <Empty>Not part of any drive yet.</Empty> : (
          <ul className="divide-y divide-slate-100">
            {p.drives.map((d) => (
              <li key={d.id} className="py-3 space-y-2 text-xs">
                <div className="flex items-center justify-between gap-3"><div className="min-w-0"><p className="font-bold text-slate-900 truncate">{d.company}</p><p className="text-slate-400 truncate">{d.role}</p></div>
                  <Pill className={DRIVE_CHIP[d.status]}>{d.selected ? DRIVE_LABEL[d.status] || d.status : 'Not picked'}</Pill></div>
                <BarRow label="Match" value={d.match_score ?? 0} pct={d.match_score ?? 0} />
                {d.final_verdict && <p className="text-slate-600">Verdict: <b>{VERDICT[d.final_verdict]}</b></p>}
              </li>
            ))}
          </ul>
        )}
      </Card>
      <div className="space-y-5 sm:space-y-6 min-w-0">
        <Card title="Offers" icon={Briefcase}>
          {p.placements.length === 0 ? <Empty>No offers recorded yet.</Empty> : (
            <ul className="divide-y divide-slate-100">{p.placements.map((o) => <li key={o.id} className="py-3 text-xs flex justify-between gap-3"><span><b className="text-slate-900">{o.company}</b><br /><span className="text-slate-400">{o.role}</span></span><span className="text-right text-slate-600">{o.ctc_lpa ? `${o.ctc_lpa} LPA` : ''}<br />{fmtDate(o.offer_date)}</span></li>)}</ul>
          )}
        </Card>
        <Card title="Resumes" icon={FileText}>
          {p.resumes.length === 0 ? <Empty>No resume versions saved yet.</Empty> : (
            <ul className="divide-y divide-slate-100">{p.resumes.map((r) => <li key={r.id} className="py-3 text-xs flex justify-between gap-3"><span><b className="text-slate-900">{r.company ? `Tailored for ${r.company}` : 'Base resume'}</b><br /><span className="text-slate-400">Version {r.version} · {fmtDate(r.created_at)}</span></span>{r.ats_match_pct !== null && <span className="font-black text-slate-800">{r.ats_match_pct}% ATS</span>}</li>)}</ul>
          )}
        </Card>
      </div>
    </div>
  );
}

function Activity({ p, isOps, call, studentId, onChange }) {
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const addNote = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      onChange((await call(`/students/${studentId}/notes`, { method: 'POST', body: { body: text } })).profile);
      setText('');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={`grid grid-cols-1 ${isOps ? 'lg:grid-cols-2' : ''} items-start gap-5 sm:gap-6`}>
      {isOps && (
        <Card title="Call notes" icon={Phone}>
          <form onSubmit={addNote} className="space-y-2">
            <textarea className={`${field} min-h-[88px] resize-y`} value={text} onChange={(e) => setText(e.target.value)} placeholder="What was discussed, what was agreed…" aria-label="New note" maxLength={4000} />
            {error && <p className="text-xs text-rose-600 font-medium">{error}</p>}
            <button disabled={saving || !text.trim()} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold px-4 py-2 rounded-xl transition">
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}Save note
            </button>
          </form>
          {p.notes?.length === 0 ? <Empty>No notes yet.</Empty> : (
            <ul className="space-y-3">{p.notes?.map((n) => <li key={n.id} className="bg-slate-50 border border-slate-100 rounded-2xl p-3 text-xs"><p className="text-slate-800 whitespace-pre-wrap break-words">{n.body}</p><p className="text-slate-400 mt-1.5">{n.author} · {fmtDateTime(n.created_at)}</p></li>)}</ul>
          )}
        </Card>
      )}
      <Card title="Timeline" icon={Clock}>
        {p.activity.length === 0 ? <Empty>Nothing has happened on this record yet.</Empty> : (
          <ol className="relative border-l border-slate-200 ml-2 space-y-4">
            {p.activity.map((a) => (
              <li key={a.id} className="pl-5 relative text-xs">
                <span className="absolute -left-[5px] top-1 w-2.5 h-2.5 rounded-full bg-blue-500 ring-4 ring-white" />
                <p className="text-slate-800 font-medium">{a.summary}</p>
                <p className="text-slate-400">{a.actor ? `${a.actor} · ` : ''}{fmtDateTime(a.at)}</p>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}

// Defined at module level on purpose: a component created inside another one is rebuilt on every keystroke and drops focus
const L = ({ label, children }) => <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1 block min-w-0">{label}{children}</label>;

function EditModal({ p, call, onClose, onSaved }) {
  const [batches, setBatches] = useState([]);
  const [form, setForm] = useState({
    name: p.name, phone: p.phone || '', college: p.college || '', degree: p.degree || '', city: p.city || '',
    target_roles: p.target_roles.join(', '), skills: (p.extra.skills || []).join(', '),
    experience_years: p.extra.experience_years ?? '', batch_id: p.batch_id || '', stage: p.stage,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { call('/students/meta/batches').then((d) => setBatches(d.batches)).catch(() => {}); }, [call]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      onSaved((await call(`/students/${p.id}`, { method: 'PATCH', body: { ...form, batch_id: form.batch_id || undefined } })).profile);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-900/40 backdrop-blur-sm sm:p-4" role="dialog" aria-modal="true" aria-label="Edit profile">
      <form onSubmit={submit} className="bg-white border border-slate-200 sm:rounded-3xl rounded-t-3xl shadow-2xl w-full max-w-2xl max-h-[94dvh] overflow-y-auto">
        <div className="sticky top-0 bg-white/95 backdrop-blur flex items-center justify-between px-5 sm:px-6 py-4 border-b border-slate-100">
          <h2 className="text-sm font-bold text-slate-900">Edit {p.name}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-700"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 sm:p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <L label="Full name"><input required className={field} value={form.name} onChange={set('name')} /></L>
            <L label="Phone"><input className={field} value={form.phone} onChange={set('phone')} /></L>
            <L label="College"><input className={field} value={form.college} onChange={set('college')} /></L>
            <L label="Degree"><input className={field} value={form.degree} onChange={set('degree')} /></L>
            <L label="City"><input className={field} value={form.city} onChange={set('city')} /></L>
            <L label="Experience (years)"><input type="number" min="0" max="60" step="0.5" className={field} value={form.experience_years} onChange={set('experience_years')} /></L>
            <L label="Batch"><select className={field} value={form.batch_id} onChange={set('batch_id')}><option value="">No batch</option>{batches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></L>
            <L label="Stage"><select className={field} value={form.stage} onChange={set('stage')}>{STAGES.map((s) => <option key={s} value={s}>{STAGE_LABEL[s]}</option>)}</select></L>
          </div>
          <L label="Target roles (comma separated)"><input className={field} value={form.target_roles} onChange={set('target_roles')} placeholder="Financial Analyst, Equity Research" /></L>
          <L label="Skills (comma separated)"><input className={field} value={form.skills} onChange={set('skills')} placeholder="Excel, Financial Modeling, Valuation" /></L>
          <p className="text-[11px] text-slate-400">Skills and target roles decide how this student ranks in company drives.</p>
          {error && <p className="text-xs font-medium text-rose-600">{error}</p>}
          <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
            <button type="button" onClick={onClose} className="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 transition">Cancel</button>
            <button disabled={saving} className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 transition">{saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}Save changes</button>
          </div>
        </div>
      </form>
    </div>
  );
}
