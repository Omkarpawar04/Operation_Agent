import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Users, Search, UploadCloud, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../api.js';
import { Card, Empty, Initials, Page, PageHeader, Pill, PrimaryButton } from './ui.jsx';
import ImportStudentsModal from './ImportStudentsModal.jsx';
import { STAGES, STAGE_CHIP, STAGE_LABEL, ago } from './studentMeta.js';

const PAGE_SIZE = 25;
const select = 'bg-slate-50/80 border border-slate-200/80 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-400 min-w-0';

const percentTone = (p) => (p >= 100 ? 'from-emerald-500 to-teal-600' : p >= 50 ? 'from-blue-500 to-indigo-600' : 'from-amber-400 to-orange-500');
function Percent({ value }) {
  return (
    <div className="flex items-center gap-2 min-w-0" title={`Profile ${value}% complete`}>
      <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden shrink-0"><div className={`h-full bg-gradient-to-r ${percentTone(value)}`} style={{ width: `${value}%` }} /></div>
      <span className="text-[11px] font-bold text-slate-600 tabular-nums">{value}%</span>
    </div>
  );
}

function Flags({ s }) {
  if (!s.never_logged_in && !s.inactive && !s.no_skills) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {s.never_logged_in && <Pill className="bg-amber-50 text-amber-700 border-amber-100">Never logged in</Pill>}
      {s.inactive && <Pill className="bg-rose-50 text-rose-700 border-rose-100">Inactive 7+ days</Pill>}
      {s.no_skills && <Pill className="bg-slate-50 text-slate-500 border-slate-200">No skills</Pill>}
    </div>
  );
}

export default function StudentListPage({ token, role, openStudent, onSessionExpired }) {
  const [data, setData] = useState(null);
  const [batches, setBatches] = useState([]);
  const [q, setQ] = useState('');
  const [search, setSearch] = useState(''); // q after a short pause, so typing does not fire a request per key
  const [batchId, setBatchId] = useState('');
  const [stage, setStage] = useState('');
  const [flag, setFlag] = useState('');
  const [sort, setSort] = useState('name');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showImport, setShowImport] = useState(false);
  const latest = useRef(0);
  const expiredRef = useRef(onSessionExpired);
  expiredRef.current = onSessionExpired;
  const canImport = role === 'Operations' || role === 'Admin';

  useEffect(() => {
    const t = setTimeout(() => { setSearch(q); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const load = useCallback(async () => {
    const ticket = ++latest.current; // ignore answers that arrive after a newer request
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, page_size: PAGE_SIZE, sort });
      if (search) params.set('q', search);
      if (batchId) params.set('batch_id', batchId);
      if (stage) params.set('stage', stage);
      if (flag) params.set('flag', flag);
      const d = await api(`/students?${params}`, { token, onExpired: () => expiredRef.current?.() });
      if (ticket !== latest.current) return;
      setData(d);
      setError('');
    } catch (e) {
      if (ticket === latest.current) setError(e.message);
    } finally {
      if (ticket === latest.current) setLoading(false);
    }
  }, [token, page, sort, search, batchId, stage, flag]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    api('/students/meta/batches', { token }).then((d) => setBatches(d.batches)).catch(() => {});
  }, [token]);

  const students = data?.students || [];
  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const stageCounts = Object.fromEntries((data?.stage_counts || []).map((s) => [s.stage, s.total]));
  const everyone = Object.values(stageCounts).reduce((a, b) => a + b, 0);
  const filtering = Boolean(search || batchId || stage || flag);
  const reset = (setter) => (e) => { setter(e.target.value); setPage(1); };

  return (
    <Page>
      <PageHeader
        icon={Users}
        title="Students"
        subtitle={data ? `${everyone} student${everyone === 1 ? '' : 's'} on the platform. Open any one to see their full record.` : 'Loading…'}
        action={canImport && <PrimaryButton icon={UploadCloud} onClick={() => setShowImport(true)}>Import from Excel</PrimaryButton>}
      />

      {everyone > 0 && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by stage">
          {[['', 'All', everyone], ...STAGES.map((s) => [s, STAGE_LABEL[s], stageCounts[s] || 0])].map(([value, label, count]) => (
            <button key={value} onClick={() => { setStage(value); setPage(1); }} aria-pressed={stage === value}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition ${stage === value ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'}`}>
              {label} <span className="opacity-60">{count}</span>
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-col lg:flex-row lg:items-center gap-3 bg-white p-4 rounded-3xl border border-slate-200/80 shadow-sm">
        <div className="relative flex-1 min-w-0">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, email, phone or student ID" aria-label="Search students"
            className="w-full bg-slate-50/80 border border-slate-200/80 text-xs pl-9 pr-4 py-2 rounded-xl outline-none focus:border-blue-400" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 lg:flex lg:gap-3">
          <select className={select} value={batchId} onChange={reset(setBatchId)} aria-label="Filter by batch">
            <option value="">All batches</option>
            {batches.map((b) => <option key={b.id} value={b.id}>{b.name} ({b.students})</option>)}
          </select>
          <select className={select} value={flag} onChange={reset(setFlag)} aria-label="Filter by needs">
            <option value="">Everyone</option>
            <option value="never">Never logged in</option>
            <option value="inactive">Inactive 7+ days</option>
            <option value="no_skills">No skills added</option>
          </select>
          <select className={select} value={sort} onChange={reset(setSort)} aria-label="Sort by">
            <option value="name">Sort: Name</option>
            <option value="newest">Sort: Newest first</option>
            <option value="last_login">Sort: Last login</option>
            <option value="code">Sort: Student ID</option>
          </select>
        </div>
      </div>

      {error && <p className="text-xs font-medium text-rose-600 bg-rose-50 border border-rose-100 rounded-2xl px-4 py-3">{error} <button onClick={load} className="underline font-bold ml-1">Try again</button></p>}

      {!data && loading ? (
        <p className="text-xs text-slate-500 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Loading students…</p>
      ) : students.length === 0 ? (
        <Card>
          <Empty>
            {filtering ? 'No students match these filters.' : canImport ? 'No students yet. Import your first batch from an Excel file.' : 'No students yet.'}
          </Empty>
          {!filtering && canImport && <div className="flex justify-center pb-2"><PrimaryButton icon={UploadCloud} onClick={() => setShowImport(true)}>Import from Excel</PrimaryButton></div>}
        </Card>
      ) : (
        <div className={loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
          {/* Phone, tablet, laptop: one card per student */}
          <div className="xl:hidden grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4">
            {students.map((s) => (
              <button key={s.id} onClick={() => openStudent(s.id)} className="text-left bg-white rounded-3xl border border-slate-200/80 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition p-4 sm:p-5 space-y-3 min-w-0">
                <div className="flex items-start gap-3 min-w-0">
                  <Initials name={s.name} className="w-10 h-10" />
                  <div className="min-w-0 flex-1">
                    <p className="font-bold text-sm text-slate-900 truncate">{s.name}</p>
                    <p className="text-xs text-slate-400 truncate">{s.student_code} · {s.email}</p>
                  </div>
                  <Pill className={STAGE_CHIP[s.stage]}>{STAGE_LABEL[s.stage]}</Pill>
                </div>
                <dl className="grid grid-cols-3 gap-2 text-xs bg-slate-50 rounded-2xl p-3">
                  <div className="min-w-0"><dt className="text-[10px] font-bold uppercase text-slate-400">Batch</dt><dd className="mt-0.5 text-slate-700 truncate">{s.batch || '—'}</dd></div>
                  <div className="min-w-0"><dt className="text-[10px] font-bold uppercase text-slate-400">City</dt><dd className="mt-0.5 text-slate-700 truncate">{s.city || '—'}</dd></div>
                  <div className="min-w-0"><dt className="text-[10px] font-bold uppercase text-slate-400">Last login</dt><dd className="mt-0.5 text-slate-700 truncate">{ago(s.last_login_at)}</dd></div>
                </dl>
                <div className="flex items-center justify-between gap-3 text-[11px] text-slate-500"><span>Profile</span><Percent value={s.profile_percent} /></div>
                <Flags s={s} />
              </button>
            ))}
          </div>

          {/* Wide screens: a table */}
          <div className="hidden xl:block bg-white rounded-3xl border border-slate-200/80 shadow-sm overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 text-slate-400 text-[11px] font-bold border-b border-slate-100 tracking-wider uppercase">
                <tr><th className="px-5 py-3">ID</th><th className="px-5 py-3">Student</th><th className="px-5 py-3">Batch</th><th className="px-5 py-3">City</th><th className="px-5 py-3">Stage</th><th className="px-5 py-3">Last login</th><th className="px-5 py-3">Profile</th><th className="px-5 py-3">Needs</th><th /></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {students.map((s) => (
                  <tr key={s.id} onClick={() => openStudent(s.id)} className="hover:bg-blue-50/40 cursor-pointer transition-colors">
                    <td className="px-5 py-3.5 font-mono text-slate-500 whitespace-nowrap">{s.student_code}</td>
                    <td className="px-5 py-3.5 max-w-[280px]"><div className="flex items-center gap-3 min-w-0"><Initials name={s.name} /><div className="min-w-0"><p className="font-semibold text-slate-800 truncate">{s.name}</p><p className="text-slate-400 truncate">{s.email}</p></div></div></td>
                    <td className="px-5 py-3.5 text-slate-600">{s.batch || '—'}</td>
                    <td className="px-5 py-3.5 text-slate-600">{s.city || '—'}</td>
                    <td className="px-5 py-3.5"><Pill className={STAGE_CHIP[s.stage]}>{STAGE_LABEL[s.stage]}</Pill></td>
                    <td className="px-5 py-3.5 text-slate-500 whitespace-nowrap">{ago(s.last_login_at)}</td>
                    <td className="px-5 py-3.5"><Percent value={s.profile_percent} /></td>
                    <td className="px-5 py-3.5"><Flags s={s} /></td>
                    <td className="px-5 py-3.5 text-slate-300"><ChevronRight className="w-4 h-4" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 text-xs text-slate-500">
            <span>Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}</span>
            <div className="flex items-center gap-2">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="flex items-center gap-1 px-3 py-2 rounded-xl border border-slate-200 bg-white font-semibold hover:bg-slate-50 disabled:opacity-40"><ChevronLeft className="w-3.5 h-3.5" />Previous</button>
              <span className="font-semibold text-slate-700 tabular-nums">{page} / {pages}</span>
              <button disabled={page >= pages} onClick={() => setPage(page + 1)} className="flex items-center gap-1 px-3 py-2 rounded-xl border border-slate-200 bg-white font-semibold hover:bg-slate-50 disabled:opacity-40">Next<ChevronRight className="w-3.5 h-3.5" /></button>
            </div>
          </div>
        </div>
      )}

      {showImport && <ImportStudentsModal token={token} onClose={() => setShowImport(false)} onImported={load} onSessionExpired={onSessionExpired} />}
    </Page>
  );
}
