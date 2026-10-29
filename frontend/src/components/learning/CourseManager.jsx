import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowUp, ArrowDown, BookOpen, Check, Layers, ListChecks, Loader2, Pencil, Plus, PlayCircle, Trash2, X } from 'lucide-react';
import { Card, Empty, Page, PageHeader, Pill, PrimaryButton } from '../ui.jsx';
import { ErrorLine, ghostBtn, input, minutes, PROVIDER_LABEL, useCall } from './shared.jsx';

// Admin builds the courses; Operations can look but not change (canEdit = false).
export default function CourseManager({ token, canEdit, onSessionExpired }) {
  const call = useCall(token, onSessionExpired);
  const [courses, setCourses] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: '', description: '' });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setError(''); setCourses((await call('/courses')).courses); } catch (e) { setError(e.message); setCourses([]); }
  }, [call]);
  useEffect(() => { load(); }, [load]);

  if (openId) return <CourseEditor key={openId} id={openId} call={call} canEdit={canEdit} onBack={() => { setOpenId(null); load(); }} />;

  const create = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      const { course } = await call('/courses', { method: 'POST', body: form });
      setCreating(false); setForm({ title: '', description: '' }); setOpenId(course.id);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };

  return (
    <Page>
      <PageHeader
        title="Learning Modules" icon={BookOpen}
        subtitle={canEdit ? 'Build courses once. Every batch gets all published courses; trainers open the topics.' : 'The courses students learn from. Only the admin edits them.'}
        action={canEdit && <PrimaryButton icon={Plus} onClick={() => setCreating(true)}>New course</PrimaryButton>}
      />
      <ErrorLine>{error}</ErrorLine>
      {creating && (
        <form onSubmit={create} className="bg-white p-5 sm:p-6 rounded-3xl border border-blue-100 shadow-sm space-y-3">
          <h2 className="text-sm font-bold text-slate-900">New course</h2>
          <input className={input} placeholder="Course title, e.g. Financial Modelling" aria-label="Course title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} autoFocus />
          <textarea className={`${input} min-h-[70px]`} placeholder="What students will learn (optional)" aria-label="Course description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <div className="flex gap-2 justify-end">
            <button type="button" className={ghostBtn} onClick={() => setCreating(false)}>Cancel</button>
            <PrimaryButton type="submit" disabled={busy || !form.title.trim()}>{busy ? 'Creating…' : 'Create course'}</PrimaryButton>
          </div>
        </form>
      )}
      {courses === null ? <div className="flex justify-center py-16"><Loader2 className="w-5 h-5 animate-spin text-slate-400" /></div> : courses.length === 0 ? (
        <Card title="No courses yet" icon={BookOpen}><Empty>{canEdit ? 'Create the first course, then add modules and video links to it.' : 'No courses have been created yet.'}</Empty></Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {courses.map((c) => (
            <button key={c.id} onClick={() => setOpenId(c.id)} className="text-left bg-white p-5 rounded-3xl border border-slate-200/80 shadow-sm hover:shadow-md hover:border-blue-200 transition space-y-3">
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-sm font-bold text-slate-900 min-w-0 break-words">{c.title}</h3>
                <Pill className={c.is_published ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-amber-50 text-amber-700 border-amber-100'}>{c.is_published ? 'Published' : 'Draft'}</Pill>
              </div>
              {c.description && <p className="text-xs text-slate-500 line-clamp-2">{c.description}</p>}
              <p className="text-[11px] font-semibold text-slate-400 flex items-center gap-3"><span className="flex items-center gap-1"><Layers className="w-3.5 h-3.5" />{c.modules} modules</span><span className="flex items-center gap-1"><PlayCircle className="w-3.5 h-3.5" />{c.videos} videos</span></p>
            </button>
          ))}
        </div>
      )}
    </Page>
  );
}

function CourseEditor({ id, call, canEdit, onBack }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [settings, setSettings] = useState(null);
  const [newModule, setNewModule] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const d = await call(`/courses/${id}`);
      setData(d);
      setSettings((s) => s || { title: d.course.title, description: d.course.description || '', pass_mark_pct: d.course.pass_mark_pct, watch_to_unlock_pct: d.course.watch_to_unlock_pct });
    } catch (e) { setError(e.message); }
  }, [call, id]);
  useEffect(() => { load(); }, [load]);

  // One wrapper for every change: run it, show a plain error if it fails, reload the course
  const act = async (fn) => {
    setBusy(true); setError('');
    try { await fn(); await load(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  if (!data) return <Page>{error ? <ErrorLine>{error}</ErrorLine> : <div className="flex justify-center py-16"><Loader2 className="w-5 h-5 animate-spin text-slate-400" /></div>}<button className={ghostBtn} onClick={onBack}><ArrowLeft className="w-4 h-4" />Back</button></Page>;
  const { course, modules } = data;
  const move = (list, i, d, url) => { const ids = list.map((x) => x.id); [ids[i], ids[i + d]] = [ids[i + d], ids[i]]; return act(() => call(url, { method: 'POST', body: { ids } })); };

  return (
    <Page>
      <PageHeader
        title={course.title} icon={BookOpen}
        subtitle={`${modules.length} modules · ${modules.reduce((a, m) => a + m.videos.length, 0)} videos`}
        action={<button className={ghostBtn} onClick={onBack}><ArrowLeft className="w-4 h-4" />All courses</button>}
      />
      <ErrorLine>{error}</ErrorLine>

      <Card title="Course settings" icon={Pencil} action={canEdit && (
        <button disabled={busy} onClick={() => act(() => call(`/courses/${id}`, { method: 'PATCH', body: { is_published: !course.is_published } }))}
          className={`text-xs font-bold px-3 py-1.5 rounded-xl border transition ${course.is_published ? 'text-amber-700 bg-amber-50 border-amber-100' : 'text-white bg-emerald-600 border-emerald-600'}`}>
          {course.is_published ? 'Unpublish' : 'Publish to students'}
        </button>)}>
        <div className="space-y-3">
          {!course.is_published && <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2">Draft. Students cannot see this course until you publish it.</p>}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Title<input className={input} disabled={!canEdit} value={settings.title} onChange={(e) => setSettings({ ...settings, title: e.target.value })} /></label>
            <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Description<input className={input} disabled={!canEdit} value={settings.description} onChange={(e) => setSettings({ ...settings, description: e.target.value })} /></label>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Watch this much before the quiz opens (%)<input className={input} type="number" min="1" max="100" disabled={!canEdit} value={settings.watch_to_unlock_pct} onChange={(e) => setSettings({ ...settings, watch_to_unlock_pct: e.target.value })} /></label>
            <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Quiz pass mark (%)<input className={input} type="number" min="1" max="100" disabled={!canEdit} value={settings.pass_mark_pct} onChange={(e) => setSettings({ ...settings, pass_mark_pct: e.target.value })} /></label>
          </div>
          {canEdit && (
            <div className="flex justify-end">
              <button disabled={busy || !settings.title.trim()} className={ghostBtn} onClick={() => act(() => call(`/courses/${id}`, { method: 'PATCH', body: { title: settings.title, description: settings.description, watch_to_unlock_pct: Number(settings.watch_to_unlock_pct), pass_mark_pct: Number(settings.pass_mark_pct) } }))}><Check className="w-4 h-4" />Save details</button>
            </div>
          )}
        </div>
      </Card>

      {modules.length === 0 && <Card title="Modules" icon={Layers}><Empty>{canEdit ? 'Add the first module below, e.g. "Module 1: Financial Statements".' : 'No modules yet.'}</Empty></Card>}
      {modules.map((m, i) => (
        <ModuleCard key={m.id} m={m} index={i} total={modules.length} canEdit={canEdit} busy={busy} act={act} call={call}
          onUp={() => move(modules, i, -1, `/courses/${id}/modules/reorder`)} onDown={() => move(modules, i, 1, `/courses/${id}/modules/reorder`)} />
      ))}

      {canEdit && (
        <form className="flex flex-col sm:flex-row gap-2" onSubmit={(e) => { e.preventDefault(); if (newModule.trim()) act(async () => { await call(`/courses/${id}/modules`, { method: 'POST', body: { title: newModule } }); setNewModule(''); }); }}>
          <input className={input} placeholder="New module title, e.g. Module 2: Forecasting" aria-label="New module title" value={newModule} onChange={(e) => setNewModule(e.target.value)} />
          <PrimaryButton type="submit" icon={Plus} disabled={busy || !newModule.trim()}>Add module</PrimaryButton>
        </form>
      )}

      {canEdit && (
        <div className="pt-4 border-t border-slate-200/70 flex justify-end">
          <button disabled={busy} className="flex items-center gap-1.5 text-xs font-bold text-rose-600 hover:bg-rose-50 border border-rose-100 rounded-xl px-3 py-2 transition"
            onClick={() => { if (window.confirm(`Delete "${course.title}" with all its modules and videos? This cannot be undone.`)) act(async () => { await call(`/courses/${id}`, { method: 'DELETE' }); onBack(); }); }}>
            <Trash2 className="w-4 h-4" />Delete course
          </button>
        </div>
      )}
    </Page>
  );
}

function ModuleCard({ m, index, total, canEdit, busy, act, call, onUp, onDown }) {
  const [title, setTitle] = useState(null); // non-null while renaming
  const [adding, setAdding] = useState(false);
  const [editVideo, setEditVideo] = useState(null);
  const [quizFor, setQuizFor] = useState(null);

  const moveVideo = (i, d) => { const ids = m.videos.map((v) => v.id); [ids[i], ids[i + d]] = [ids[i + d], ids[i]]; return act(() => call(`/modules/${m.id}/videos/reorder`, { method: 'POST', body: { ids } })); };

  return (
    <section className="bg-white rounded-3xl border border-slate-200/80 shadow-sm overflow-hidden" aria-label={m.title}>
      <div className="flex items-center justify-between gap-3 px-5 py-4 bg-slate-50/70 border-b border-slate-100">
        {title === null ? (
          <h3 className="text-sm font-bold text-slate-900 min-w-0 break-words">{m.title}</h3>
        ) : (
          <form className="flex gap-2 flex-1" onSubmit={(e) => { e.preventDefault(); act(async () => { await call(`/modules/${m.id}`, { method: 'PATCH', body: { title } }); setTitle(null); }); }}>
            <input className={input} value={title} onChange={(e) => setTitle(e.target.value)} aria-label="Module title" autoFocus />
            <button type="submit" className={ghostBtn} aria-label="Save title"><Check className="w-4 h-4" /></button>
            <button type="button" className={ghostBtn} onClick={() => setTitle(null)} aria-label="Cancel"><X className="w-4 h-4" /></button>
          </form>
        )}
        {canEdit && title === null && (
          <div className="flex items-center gap-1 shrink-0">
            <button disabled={busy || index === 0} onClick={onUp} className={ghostBtn} aria-label="Move module up"><ArrowUp className="w-4 h-4" /></button>
            <button disabled={busy || index === total - 1} onClick={onDown} className={ghostBtn} aria-label="Move module down"><ArrowDown className="w-4 h-4" /></button>
            <button onClick={() => setTitle(m.title)} className={ghostBtn} aria-label="Rename module"><Pencil className="w-4 h-4" /></button>
            <button disabled={busy} className="flex items-center justify-center text-rose-600 hover:bg-rose-50 border border-rose-100 rounded-xl px-3 py-2 transition" aria-label="Delete module"
              onClick={() => { if (window.confirm(`Delete "${m.title}" and its ${m.videos.length} videos?`)) act(() => call(`/modules/${m.id}`, { method: 'DELETE' })); }}><Trash2 className="w-4 h-4" /></button>
          </div>
        )}
      </div>

      <ul className="divide-y divide-slate-100">
        {m.videos.length === 0 && <li><Empty>No videos in this module yet.</Empty></li>}
        {m.videos.map((v, i) => (
          <li key={v.id} className="px-5 py-3">
            {editVideo === v.id ? (
              <VideoForm initial={v} busy={busy} onCancel={() => setEditVideo(null)}
                onSave={(body) => act(async () => { await call(`/videos/${v.id}`, { method: 'PATCH', body }); setEditVideo(null); })} />
            ) : (
              <div className="flex items-center justify-between gap-3 text-xs">
                <div className="min-w-0">
                  <p className="font-bold text-slate-900 break-words flex items-center gap-2"><PlayCircle className="w-4 h-4 text-blue-600 shrink-0" />{i + 1}. {v.title} {v.duration_sec ? <span className="text-slate-400 font-medium">· {minutes(v.duration_sec)}</span> : null}</p>
                  <a href={v.video_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline break-all block mt-0.5 pl-6">{v.video_url}</a>
                  {v.key_points?.length > 0 && <p className="text-slate-400 mt-0.5 pl-6">{v.key_points.length} key point{v.key_points.length === 1 ? '' : 's'}</p>}
                  <p className="mt-1.5 pl-6 flex flex-wrap items-center gap-1.5">
                    <Pill className={v.provider === 'other' ? 'bg-amber-50 text-amber-700 border-amber-100' : 'bg-emerald-50 text-emerald-700 border-emerald-100'}>{PROVIDER_LABEL[v.provider]} · {v.provider === 'other' ? 'student confirms by hand' : 'watch time tracked'}</Pill>
                    <Pill className={v.questions ? 'bg-indigo-50 text-indigo-700 border-indigo-100' : 'bg-slate-50 text-slate-500 border-slate-200'}>{v.questions ? `${v.questions} quiz question${v.questions === 1 ? '' : 's'}` : 'No quiz'}</Pill>
                  </p>
                </div>
                <div className="flex items-center gap-1 shrink-0 flex-wrap justify-end">
                  <button onClick={() => setQuizFor(quizFor === v.id ? null : v.id)} className={ghostBtn} aria-expanded={quizFor === v.id}><ListChecks className="w-4 h-4" />Quiz</button>
                  {canEdit && (<>
                    <button disabled={busy || i === 0} onClick={() => moveVideo(i, -1)} className={ghostBtn} aria-label="Move video up"><ArrowUp className="w-4 h-4" /></button>
                    <button disabled={busy || i === m.videos.length - 1} onClick={() => moveVideo(i, 1)} className={ghostBtn} aria-label="Move video down"><ArrowDown className="w-4 h-4" /></button>
                    <button onClick={() => setEditVideo(v.id)} className={ghostBtn} aria-label="Edit video"><Pencil className="w-4 h-4" /></button>
                    <button disabled={busy} className="flex items-center justify-center text-rose-600 hover:bg-rose-50 border border-rose-100 rounded-xl px-3 py-2 transition" aria-label="Delete video"
                      onClick={() => { if (window.confirm(`Delete "${v.title}"?`)) act(() => call(`/videos/${v.id}`, { method: 'DELETE' })); }}><Trash2 className="w-4 h-4" /></button>
                  </>)}
                </div>
              </div>
            )}
            {quizFor === v.id && editVideo !== v.id && <QuizEditor video={v} call={call} canEdit={canEdit} onChange={() => act(async () => {})} />}
          </li>
        ))}
      </ul>

      {canEdit && (
        <div className="px-5 py-4 border-t border-slate-100">
          {adding ? (
            <VideoForm busy={busy} onCancel={() => setAdding(false)} onSave={(body) => act(async () => { await call(`/modules/${m.id}/videos`, { method: 'POST', body }); setAdding(false); })} />
          ) : <button className={ghostBtn} onClick={() => setAdding(true)}><Plus className="w-4 h-4" />Add video</button>}
        </div>
      )}
    </section>
  );
}

function VideoForm({ initial, busy, onSave, onCancel }) {
  const [f, setF] = useState({
    title: initial?.title || '', video_url: initial?.video_url || '',
    duration_min: initial?.duration_sec ? String(Math.round(initial.duration_sec / 60)) : '', points: (initial?.key_points || []).join('\n'),
  });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = (e) => {
    e.preventDefault();
    onSave({ title: f.title, video_url: f.video_url, duration_min: f.duration_min === '' ? null : Number(f.duration_min), key_points: f.points.split('\n') });
  };
  return (
    <form onSubmit={submit} className="space-y-3 bg-blue-50/40 border border-blue-100 rounded-2xl p-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Video title<input className={input} value={f.title} onChange={set('title')} autoFocus /></label>
        <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Video link<input className={input} placeholder="https://youtu.be/…" value={f.video_url} onChange={set('video_url')} /></label>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[160px_1fr] gap-3">
        <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Length (minutes)<input className={input} inputMode="numeric" placeholder="optional" value={f.duration_min} onChange={set('duration_min')} /></label>
        <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Key points (one per line, optional)<textarea className={`${input} min-h-[60px]`} value={f.points} onChange={set('points')} /></label>
      </div>
      <p className="text-[11px] text-slate-400">Use an unlisted YouTube or Vimeo link so only your students can find it.</p>
      <div className="flex gap-2 justify-end">
        <button type="button" className={ghostBtn} onClick={onCancel}>Cancel</button>
        <PrimaryButton type="submit" disabled={busy || !f.title.trim() || !f.video_url.trim()}>{initial ? 'Save video' : 'Add video'}</PrimaryButton>
      </div>
    </form>
  );
}

// The quiz of one video: multiple choice, 2 to 6 choices, one correct. Operations can read it, only the admin changes it.
function QuizEditor({ video, call, canEdit, onChange }) {
  const [list, setList] = useState(null);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(null); // a question id, or 'new'

  const load = useCallback(async () => {
    try { setList((await call(`/videos/${video.id}/questions`)).questions); } catch (e) { setError(e.message); setList([]); }
  }, [call, video.id]);
  useEffect(() => { load(); }, [load]);

  const save = async (body, qid) => {
    await call(qid ? `/questions/${qid}` : `/videos/${video.id}/questions`, { method: qid ? 'PATCH' : 'POST', body });
    setEditing(null); await load(); onChange();
  };
  const remove = async (qid) => {
    setError('');
    try { await call(`/questions/${qid}`, { method: 'DELETE' }); await load(); onChange(); } catch (e) { setError(e.message); }
  };

  return (
    <div className="mt-3 ml-6 bg-indigo-50/30 border border-indigo-100 rounded-2xl p-4 space-y-3" aria-label={`Quiz for ${video.title}`}>
      <p className="text-[11px] text-slate-500">Students open this quiz after watching the course's watch percentage, and must score the pass mark to move on. A lesson with no questions completes by watching alone.</p>
      <ErrorLine>{error}</ErrorLine>
      {list === null ? <Loader2 className="w-4 h-4 animate-spin text-slate-400" /> : list.length === 0 && editing !== 'new' ? <p className="text-xs text-slate-400">No questions yet.</p> : (
        <ol className="space-y-3">
          {list.map((qu, i) => (
            <li key={qu.id}>
              {editing === qu.id ? <QuestionForm initial={qu} onSave={(b) => save(b, qu.id)} onCancel={() => setEditing(null)} /> : (
                <div className="bg-white border border-slate-200/80 rounded-xl p-3 text-xs space-y-1.5">
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-bold text-slate-900 break-words min-w-0">{i + 1}. {qu.question}</p>
                    {canEdit && (
                      <span className="flex gap-1 shrink-0">
                        <button className={ghostBtn} aria-label="Edit question" onClick={() => setEditing(qu.id)}><Pencil className="w-3.5 h-3.5" /></button>
                        <button className="flex items-center justify-center text-rose-600 hover:bg-rose-50 border border-rose-100 rounded-xl px-2.5 py-2 transition" aria-label="Delete question" onClick={() => { if (window.confirm('Delete this question?')) remove(qu.id); }}><Trash2 className="w-3.5 h-3.5" /></button>
                      </span>
                    )}
                  </div>
                  <ul className="space-y-0.5">
                    {qu.options.map((o, oi) => (
                      <li key={o + oi} className={`flex items-center gap-2 break-words ${oi === qu.answer_index ? 'text-emerald-700 font-semibold' : 'text-slate-600'}`}>
                        {oi === qu.answer_index ? <Check className="w-3.5 h-3.5 shrink-0" /> : <span className="w-3.5 shrink-0" />}{o}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
      {canEdit && editing === 'new' && <QuestionForm onSave={(b) => save(b)} onCancel={() => setEditing(null)} />}
      {canEdit && editing !== 'new' && <button className={ghostBtn} onClick={() => setEditing('new')}><Plus className="w-4 h-4" />Add question</button>}
    </div>
  );
}

function QuestionForm({ initial, onSave, onCancel }) {
  const [question, setQuestion] = useState(initial?.question || '');
  const [options, setOptions] = useState(initial?.options || ['', '']);
  const [answer, setAnswer] = useState(initial?.answer_index ?? 0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const name = useRef(`ans-${Math.random().toString(36).slice(2)}`).current;

  const setOpt = (i, v) => setOptions((o) => o.map((x, j) => (j === i ? v : x)));
  const removeOpt = (i) => { setOptions((o) => o.filter((_, j) => j !== i)); setAnswer((a) => (a === i ? 0 : a > i ? a - 1 : a)); };
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('');
    try { await onSave({ question, options, answer_index: answer }); } catch (err) { setError(err.message); setBusy(false); }
  };

  return (
    <form onSubmit={submit} className="bg-white border border-blue-100 rounded-xl p-3 space-y-3">
      <label className="text-[11px] font-bold text-slate-500 space-y-1 block">Question<textarea className={`${input} min-h-[56px]`} value={question} onChange={(e) => setQuestion(e.target.value)} autoFocus /></label>
      <fieldset className="space-y-2">
        <legend className="text-[11px] font-bold text-slate-500 mb-1">Answer choices. Tick the correct one.</legend>
        {options.map((o, i) => (
          <div key={i} className="flex items-center gap-2">
            <input type="radio" name={name} checked={answer === i} onChange={() => setAnswer(i)} className="w-4 h-4 accent-emerald-600 shrink-0" aria-label={`Choice ${i + 1} is correct`} />
            <input className={input} value={o} placeholder={`Choice ${i + 1}`} aria-label={`Choice ${i + 1}`} onChange={(e) => setOpt(i, e.target.value)} />
            {options.length > 2 && <button type="button" className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 shrink-0" aria-label={`Remove choice ${i + 1}`} onClick={() => removeOpt(i)}><X className="w-4 h-4" /></button>}
          </div>
        ))}
        {options.length < 6 && <button type="button" className="text-[11px] font-bold text-blue-600 hover:underline" onClick={() => setOptions((o) => [...o, ''])}>+ Add a choice</button>}
      </fieldset>
      <ErrorLine>{error}</ErrorLine>
      <div className="flex gap-2 justify-end">
        <button type="button" className={ghostBtn} onClick={onCancel}>Cancel</button>
        <PrimaryButton type="submit" disabled={busy || !question.trim() || options.some((o) => !o.trim())}>{initial ? 'Save question' : 'Add question'}</PrimaryButton>
      </div>
    </form>
  );
}
