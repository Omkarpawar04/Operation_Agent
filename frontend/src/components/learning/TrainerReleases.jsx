import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Circle, Layers, Loader2, Users } from 'lucide-react';
import { Card, Empty, Page, PageHeader, Pill } from '../ui.jsx';
import { ErrorLine, fmtDate, input, useCall } from './shared.jsx';

// Trainer: pick a batch, then tick the topics taught. Ticking a topic opens its videos for that batch only.
export default function TrainerReleases({ token, onSessionExpired }) {
  const call = useCall(token, onSessionExpired);
  const [batches, setBatches] = useState(null);
  const [courses, setCourses] = useState([]);
  const [batchId, setBatchId] = useState('');
  const [courseId, setCourseId] = useState('');
  const [course, setCourse] = useState(null);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const [b, c] = await Promise.all([call('/batches'), call('/courses')]);
        setBatches(b.batches); setCourses(c.courses);
        if (b.batches[0]) setBatchId(b.batches[0].id);
        if (c.courses[0]) setCourseId(c.courses[0].id);
      } catch (e) { setError(e.message); setBatches([]); }
    })();
  }, [call]);

  const loadCourse = useCallback(async () => {
    if (!batchId || !courseId) return setCourse(null);
    try { setError(''); setCourse(await call(`/courses/${courseId}?batch=${batchId}`)); } catch (e) { setError(e.message); }
  }, [call, batchId, courseId]);
  useEffect(() => { loadCourse(); }, [loadCourse]);

  const toggle = async (m) => {
    setBusyId(m.id); setError('');
    try { await call(`/batches/${batchId}/modules/${m.id}`, { method: 'PUT', body: { released: !m.released } }); await loadCourse(); }
    catch (e) { setError(e.message); } finally { setBusyId(''); }
  };

  const batch = batches?.find((b) => b.id === batchId);
  const modules = course?.modules || [];
  const done = modules.filter((m) => m.released).length;

  return (
    <Page>
      <PageHeader title="Learning Modules" icon={Layers} subtitle="Mark the topics you have finished teaching. Their videos then open for that batch's students." />
      <ErrorLine>{error}</ErrorLine>
      {batches === null ? <div className="flex justify-center py-16"><Loader2 className="w-5 h-5 animate-spin text-slate-400" /></div> : batches.length === 0 ? (
        <Card title="No batches yet" icon={Users}><Empty>You are not assigned to a batch yet. The admin or operations team assigns trainers from the Batches tab.</Empty></Card>
      ) : courses.length === 0 ? (
        <Card title="No courses yet" icon={Layers}><Empty>The admin has not published a course yet.</Empty></Card>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-white p-4 sm:p-5 rounded-3xl border border-slate-200/80 shadow-sm">
            <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Batch
              <select className={input} value={batchId} onChange={(e) => setBatchId(e.target.value)}>
                {batches.map((b) => <option key={b.id} value={b.id}>{b.name} ({b.students} students)</option>)}
              </select>
            </label>
            <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Course
              <select className={input} value={courseId} onChange={(e) => setCourseId(e.target.value)}>
                {courses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
              </select>
            </label>
          </div>

          <Card title={`${course?.course.title || 'Course'} · ${batch?.name || ''}`} icon={Layers} action={modules.length > 0 && <Pill className="bg-blue-50 text-blue-700 border-blue-100">{done} / {modules.length} topics open</Pill>}>
            {modules.length === 0 ? <Empty>This course has no modules yet.</Empty> : (
              <ul className="divide-y divide-slate-100">
                {modules.map((m, i) => (
                  <li key={m.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 py-3.5">
                    <div className="min-w-0 flex items-start gap-3">
                      {m.released ? <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" /> : <Circle className="w-5 h-5 text-slate-300 shrink-0 mt-0.5" />}
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-slate-900 break-words">{i + 1}. {m.title}</p>
                        <p className="text-[11px] text-slate-400">{m.videos.length} video{m.videos.length === 1 ? '' : 's'}{m.released && m.released_at ? ` · completed ${fmtDate(m.released_at)}` : ''}</p>
                      </div>
                    </div>
                    <button disabled={busyId === m.id} onClick={() => toggle(m)}
                      className={`text-xs font-bold px-4 py-2 rounded-xl border transition shrink-0 disabled:opacity-60 ${m.released ? 'text-slate-600 bg-white border-slate-200 hover:bg-slate-50' : 'text-white bg-emerald-600 border-emerald-600 hover:brightness-105'}`}>
                      {busyId === m.id ? 'Saving…' : m.released ? 'Lock again' : 'Mark as completed'}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </Page>
  );
}
