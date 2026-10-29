import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowLeft, Award, BookOpen, CheckCircle2, ChevronRight, Clock, Loader2, Lock, PlayCircle, Sparkles, SkipForward,
} from 'lucide-react';
import { ErrorLine, minutes, useCall } from './shared.jsx';
import Player from './Player.jsx';

// Student view of Learning Modules, in the original look: a course grid, then a player with a lessons sidebar.
// Every course is here for every batch; a topic opens once the trainer marks it completed for the student's batch.

const GRADIENTS = [
  'from-indigo-600 via-indigo-500 to-sky-500', 'from-violet-600 via-purple-500 to-fuchsia-500', 'from-emerald-600 via-teal-500 to-cyan-500',
  'from-blue-700 via-blue-600 to-indigo-500', 'from-rose-600 via-pink-500 to-orange-400', 'from-slate-800 via-slate-700 to-indigo-600',
];
const gradientFor = (text = '') => GRADIENTS[[...text].reduce((a, c) => a + c.charCodeAt(0), 0) % GRADIENTS.length];
const hours = (sec) => {
  if (!sec) return null;
  const h = Math.floor(sec / 3600); const m = Math.round((sec % 3600) / 60);
  return h ? `${h}h ${m ? `${m}m` : ''}`.trim() : `${Math.max(1, m)} min`;
};
const pctOf = (done, total) => (total ? Math.round((done / total) * 100) : 0);

function ProgressBar({ value, className = 'h-2' }) {
  return (
    <div className={`w-full bg-slate-100 rounded-full overflow-hidden p-0.5 ${className}`} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className="bg-gradient-to-r from-indigo-500 to-indigo-600 h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${value}%` }} />
    </div>
  );
}

// Course cover: a coloured banner with the course's initials (courses have no image of their own)
function Cover({ title, className = 'h-44', children }) {
  const initials = title.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');
  return (
    <div className={`relative overflow-hidden bg-gradient-to-br ${gradientFor(title)} ${className}`}>
      <div className="absolute -right-6 -bottom-8 text-white/15 text-[9rem] font-black leading-none select-none" aria-hidden="true">{initials}</div>
      <BookOpen className="absolute left-5 bottom-5 w-9 h-9 text-white/80" />
      {children}
    </div>
  );
}

export default function StudentLearning({ token, onSessionExpired }) {
  const call = useCall(token, onSessionExpired);
  const [state, setState] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try { setError(''); setState(await call('/courses')); } catch (e) { setError(e.message); setState({ courses: [] }); }
  }, [call]);
  useEffect(() => { load(); }, [load]);

  if (openId) return <CourseView id={openId} call={call} onBack={() => { setOpenId(null); load(); }} />;

  const courses = state?.courses || [];
  const totalVideos = courses.reduce((a, c) => a + c.videos, 0);
  const totalDone = courses.reduce((a, c) => a + c.done_videos, 0);

  return (
    <div className="space-y-6 animate-fadeIn max-w-[1600px] mx-auto pb-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Learning Modules</h1>
          <p className="text-slate-500 text-sm mt-1">Structured curriculum, technical frameworks, and assessment modules. Your trainer opens each topic after teaching it.</p>
        </div>
        {courses.length > 0 && (
          <span className="px-4 py-2 bg-indigo-50 text-indigo-700 text-sm font-semibold rounded-2xl flex items-center gap-2 shadow-sm self-start md:self-auto">
            <Sparkles size={16} /> {pctOf(totalDone, totalVideos)}% of all lessons watched
          </span>
        )}
      </div>
      <ErrorLine>{error}</ErrorLine>

      {state === null ? <div className="flex justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div> : (
        <>
          {state.has_batch === false && <p className="text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-2xl px-4 py-3">You are not in a batch yet, so no topics are open. Ask the operations team to add you to your batch.</p>}
          {courses.length === 0 ? (
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-12 text-center text-slate-400 text-sm">Courses will show here as soon as they are published.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {courses.map((c, idx) => {
                const progress = pctOf(c.done_videos, c.videos);
                return (
                  <div key={c.id} className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-xl hover:-translate-y-1.5 transition-all duration-300 flex flex-col group" style={{ animationDelay: `${idx * 100}ms` }}>
                    <Cover title={c.title}>
                      <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-md px-3 py-1 rounded-full text-xs font-semibold text-slate-800 shadow-sm">{c.modules} topic{c.modules === 1 ? '' : 's'}</div>
                      <div className="absolute top-4 right-4 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full text-xs font-bold text-white shadow-sm">{progress}% Completed</div>
                    </Cover>
                    <div className="p-6 space-y-4 flex-1 flex flex-col justify-between">
                      <div className="space-y-2">
                        <h3 className="text-lg font-bold text-slate-900 group-hover:text-indigo-600 transition-colors break-words">{c.title}</h3>
                        <p className="text-slate-500 text-sm line-clamp-2 leading-relaxed">{c.description || 'Open the course to see its topics and lessons.'}</p>
                      </div>
                      <div className="space-y-4">
                        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-xs font-medium text-slate-400">
                          <span className="flex items-center gap-1.5"><BookOpen size={14} /> {c.videos} Lessons</span>
                          {hours(c.total_sec) && <span className="flex items-center gap-1.5"><Clock size={14} /> {hours(c.total_sec)}</span>}
                          <span><strong className="text-slate-600">{c.open_videos}</strong> open to you</span>
                        </div>
                        <ProgressBar value={progress} />
                        <button onClick={() => setOpenId(c.id)} className="w-full py-3 bg-slate-900 hover:bg-indigo-600 text-white font-semibold rounded-2xl transition-all duration-300 flex items-center justify-center gap-2 text-sm shadow-sm hover:shadow-indigo-200 hover:shadow-lg active:scale-[0.98] group/btn">
                          <span>{c.done_videos > 0 ? 'Continue Module' : 'Start Module'}</span>
                          <ChevronRight size={16} className="transition-transform duration-300 group-hover/btn:translate-x-1.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function CourseView({ id, call, onBack }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [activeId, setActiveId] = useState(null);
  const [info, setInfo] = useState(null);          // how to play the open lesson (link, resume point, quiz rules)
  const [live, setLive] = useState({ pct: 0, unlocked: false, passed: false });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setData(await call(`/courses/${id}`)); } catch (e) { setError(e.message); }
  }, [call, id]);
  useEffect(() => { load(); }, [load]);

  // Every lesson in course order. A lesson can be played only when its topic is open and the earlier lessons are passed.
  const lessons = useMemo(() => (data ? data.modules.flatMap((m) => m.videos.map((v) => ({ ...v, module: m }))) : []), [data]);
  const playable = lessons.filter((l) => l.playable);

  useEffect(() => {
    if (!data || activeId) return;
    const first = playable.find((l) => !l.done) || playable[0];
    if (first) setActiveId(first.id);
  }, [data, activeId, playable]);

  const active = lessons.find((l) => l.id === activeId && l.playable) || null;
  const idRef = useRef(null);
  idRef.current = active?.id || null;
  const liveRef = useRef(live);
  liveRef.current = live;

  // Fetch the play info whenever another lesson is opened
  useEffect(() => {
    if (!active) { setInfo(null); return undefined; }
    let dead = false;
    setInfo(null);
    call(`/videos/${active.id}/play`)
      .then((r) => { if (!dead) { setInfo(r); setLive({ pct: r.watched_pct, unlocked: r.quiz_unlocked, passed: r.passed }); } })
      .catch((e) => { if (!dead) setError(e.message); });
    return () => { dead = true; };
  }, [call, active?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // The player calls this every few seconds with the seconds really watched
  const beatFor = (videoId) => async (ranges, position, duration) => {
    const r = await call(`/videos/${videoId}/progress`, { method: 'POST', body: { ranges, position, duration } });
    if (idRef.current === videoId) {
      const was = liveRef.current;
      setLive({ pct: r.watched_pct, unlocked: r.quiz_unlocked, passed: r.passed });
      if (r.quiz_unlocked !== was.unlocked || r.passed !== was.passed) load();
    }
    return r;
  };

  const confirmWatched = async () => {
    setBusy(true); setError('');
    try {
      const r = await call(`/videos/${active.id}/watched`, { method: 'POST' });
      setLive({ pct: 100, unlocked: true, passed: r.passed });
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  if (!data) {
    return (
      <div className="space-y-6">
        {error ? <ErrorLine>{error}</ErrorLine> : <div className="flex justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>}
        <button onClick={onBack} className="flex items-center gap-2 text-slate-600 font-medium bg-slate-50 hover:bg-slate-100 px-4 py-2 rounded-xl text-sm"><ArrowLeft size={18} /> Back to Courses</button>
      </div>
    );
  }

  const { course, modules } = data;
  const doneCount = lessons.filter((l) => l.done).length;
  const progress = pctOf(doneCount, lessons.length);
  const totalSec = lessons.reduce((a, l) => a + (l.duration_sec || 0), 0);
  const idx = active ? playable.findIndex((l) => l.id === active.id) : -1;
  const next = idx >= 0 ? playable[idx + 1] : null;
  const prev = idx > 0 ? playable[idx - 1] : null;
  const isDone = Boolean(active && (active.done || live.passed));

  return (
    <div className="space-y-6 animate-fadeIn max-w-[1600px] mx-auto pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-2xl shadow-sm border border-slate-100">
        <button onClick={onBack} className="flex items-center gap-2 text-slate-600 hover:text-slate-900 font-medium transition-all bg-slate-50 hover:bg-slate-100 px-4 py-2 rounded-xl text-sm group self-start">
          <ArrowLeft size={18} className="transition-transform group-hover:-translate-x-1" /> Back to Courses
        </button>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="px-3 py-1 bg-indigo-50 text-indigo-700 text-xs font-semibold rounded-full">{modules.length} topic{modules.length === 1 ? '' : 's'}</span>
          <span className="text-sm font-medium text-slate-500">{doneCount} of {lessons.length} lessons passed</span>
        </div>
      </div>
      <ErrorLine>{error}</ErrorLine>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <div className="lg:col-span-2 space-y-6 min-w-0">
          <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
            {active && info ? (
              <Player key={active.id} videoId={active.id} info={info} onBeat={beatFor(active.id)} />
            ) : (
              <div className={`relative aspect-video text-white text-center p-6 bg-gradient-to-br ${gradientFor(course.title)} flex flex-col items-center justify-center gap-3`} aria-label="Video player">
                <span className="w-16 h-16 bg-white/20 backdrop-blur rounded-full flex items-center justify-center">
                  {active ? <Loader2 size={30} className="animate-spin" /> : playable.length === 0 ? <Lock size={30} /> : <PlayCircle size={34} />}
                </span>
                <h3 className="text-xl font-bold">{active ? 'Loading the lesson…' : playable.length === 0 ? 'Nothing is open yet' : 'Pick a lesson to start'}</h3>
                {!active && <p className="text-white/80 text-sm max-w-md">{playable.length === 0 ? 'Your trainer opens each topic after teaching it. Check back soon.' : 'Choose a lesson from the list.'}</p>}
              </div>
            )}

            <div className="p-6 space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-xl font-bold text-slate-900 break-words">{active ? active.title : course.title}</h2>
                  <p className="text-xs text-slate-400 mt-1">{active ? `${active.module.title}${active.duration_sec ? ` · ${minutes(active.duration_sec)}` : ''}` : (course.description || 'Course overview')}</p>
                </div>
                {active && (isDone
                  ? <span className="text-xs font-semibold px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full flex items-center gap-1 self-start sm:self-auto shrink-0"><CheckCircle2 size={14} /> Completed</span>
                  : <span className="text-xs font-semibold px-3 py-1 bg-amber-50 text-amber-700 rounded-full self-start sm:self-auto shrink-0">In Progress</span>)}
              </div>

              {active && info && (
                <div className="space-y-2" aria-label="Watch progress">
                  <div className="flex justify-between text-xs font-semibold text-slate-600">
                    <span>Watched</span><span>{live.pct}%</span>
                  </div>
                  <div className="relative w-full bg-slate-100 h-2.5 rounded-full overflow-hidden" role="progressbar" aria-valuenow={live.pct} aria-valuemin={0} aria-valuemax={100} aria-label="Watched so far">
                    <div className={`h-full rounded-full transition-all duration-700 ${live.pct >= info.unlock_pct ? 'bg-gradient-to-r from-emerald-500 to-emerald-600' : 'bg-gradient-to-r from-indigo-500 to-indigo-600'}`} style={{ width: `${live.pct}%` }} />
                    <div className="absolute top-0 bottom-0 w-0.5 bg-slate-400/70" style={{ left: `${info.unlock_pct}%` }} title={`${info.unlock_pct}% opens the quiz`} />
                  </div>
                  <p className="text-[11px] text-slate-400">
                    {info.provider === 'other'
                      ? 'This link cannot be followed automatically. Watch it, then confirm below.'
                      : `Only the parts you actually play count. Skipping ahead does not. ${info.questions ? `The quiz opens at ${info.unlock_pct}%.` : `The lesson completes at ${info.unlock_pct}%.`}`}
                  </p>
                </div>
              )}

              {active && info && info.provider === 'other' && !isDone && !live.unlocked && (
                <button disabled={busy} onClick={confirmWatched} className="flex items-center gap-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 px-5 py-2.5 rounded-xl shadow-sm transition active:scale-95">
                  <CheckCircle2 size={16} /> {busy ? 'Saving…' : 'I have watched this video'}
                </button>
              )}

              {active && info && (
                <QuizPanel key={active.id} call={call} videoId={active.id} info={info} live={live} onPassed={async () => { setLive((l) => ({ ...l, passed: true })); await load(); }} />
              )}

              {active && (
                <div className="flex flex-wrap items-center gap-2">
                  <button disabled={!prev} onClick={() => setActiveId(prev.id)} className="flex items-center gap-1.5 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-slate-50 px-4 py-2 rounded-xl transition"><ArrowLeft size={16} /> Previous</button>
                  <button disabled={!next} onClick={() => setActiveId(next.id)} className={`flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-xl transition disabled:opacity-40 ${isDone && next ? 'text-white bg-indigo-600 hover:bg-indigo-500' : 'text-slate-600 bg-slate-50 hover:bg-slate-100'}`}>Next lesson <SkipForward size={16} /></button>
                </div>
              )}

              <hr className="border-slate-100" />
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Lesson Notes &amp; Summary</h4>
                <div className="text-slate-600 leading-relaxed text-sm bg-slate-50 p-4 rounded-2xl border border-slate-100">
                  {info?.key_points?.length > 0 ? (
                    <ul className="list-disc pl-5 space-y-1">{info.key_points.map((k) => <li key={k}>{k}</li>)}</ul>
                  ) : active ? 'No notes were added for this lesson.' : (course.description || 'Open a lesson to see its notes here.')}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="bg-white rounded-3xl shadow-sm border border-slate-100 p-6 space-y-6 lg:sticky lg:top-0 min-w-0">
          <div>
            <h3 className="font-bold text-slate-900 text-lg break-words">{course.title}</h3>
            <p className="text-slate-500 text-xs mt-1">{lessons.length} Lessons{hours(totalSec) ? ` • ${hours(totalSec)}` : ''}</p>
            <div className="mt-4 space-y-1.5">
              <div className="flex justify-between text-xs font-semibold text-slate-600"><span>Overall Progress</span><span>{progress}%</span></div>
              <ProgressBar value={progress} className="h-2.5" />
            </div>
          </div>
          <hr className="border-slate-100" />

          <div className="space-y-5 max-h-[34rem] overflow-y-auto pr-1">
            {modules.length === 0 && <p className="text-xs text-slate-400">This course has no topics yet.</p>}
            {modules.map((m, i) => {
              const done = m.videos.filter((v) => v.done).length;
              return (
                <div key={m.id} className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider min-w-0 break-words">{i + 1}. {m.title}</h4>
                    {m.released
                      ? <span className="text-[11px] font-semibold text-slate-400 shrink-0">{done}/{m.videos.length}</span>
                      : <span className="flex items-center gap-1 text-[11px] font-semibold text-slate-400 shrink-0"><Lock size={12} /> Locked</span>}
                  </div>
                  {!m.released && <p className="text-[11px] text-slate-400 -mt-1">Opens when your trainer completes this topic.</p>}
                  <div className="space-y-1.5">
                    {m.videos.map((l) => {
                      const selected = activeId === l.id && l.playable;
                      if (!l.playable) {
                        return (
                          <div key={l.id} className="w-full p-3 rounded-2xl text-sm flex items-center justify-between text-slate-300 cursor-not-allowed" aria-disabled="true" title={m.released ? 'Pass the lesson before this one first' : 'Your trainer has not opened this topic yet'}>
                            <span className="flex items-center gap-3 min-w-0"><Lock size={16} className="shrink-0" /><span className="line-clamp-1">{l.title}</span></span>
                            <span className="text-xs shrink-0 ml-2">{minutes(l.duration_sec)}</span>
                          </div>
                        );
                      }
                      return (
                        <button key={l.id} onClick={() => setActiveId(l.id)}
                          className={`w-full text-left p-3 rounded-2xl text-sm flex items-center justify-between transition-all duration-200 active:scale-[0.98] ${selected ? 'bg-indigo-50 text-indigo-900 font-semibold border border-indigo-100 shadow-sm translate-x-1' : 'hover:bg-slate-50 hover:translate-x-1 text-slate-600'}`}>
                          <span className="flex items-center gap-3 min-w-0">
                            {l.done ? <CheckCircle2 size={16} className="text-emerald-500 shrink-0" /> : <PlayCircle size={16} className={`shrink-0 ${selected ? 'text-indigo-600' : 'text-slate-400'}`} />}
                            <span className="line-clamp-1">{l.title}</span>
                          </span>
                          <span className="text-xs text-slate-400 shrink-0 ml-2">{!l.done && l.watched_pct > 0 ? `${l.watched_pct}%` : minutes(l.duration_sec)}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// The quiz under the player: closed until enough is watched, then multiple choice. The answers appear only after passing.
function QuizPanel({ call, videoId, info, live, onPassed }) {
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);
  const [retake, setRetake] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!live.unlocked || !info.questions) return undefined;
    let dead = false;
    call(`/videos/${videoId}/quiz`)
      .then((r) => { if (!dead) { setQuiz(r); setAnswers(Array(r.questions.length).fill(null)); } })
      .catch((e) => { if (!dead) setError(e.message); });
    return () => { dead = true; };
  }, [call, videoId, live.unlocked, info.questions]);

  if (!info.questions) {
    return (
      <div className="flex items-start gap-3 text-sm bg-slate-50 border border-slate-100 rounded-2xl p-4 text-slate-600">
        <Award size={18} className="shrink-0 mt-0.5 text-slate-400" />
        <p>{live.passed ? 'No quiz for this lesson, and you have completed it.' : `No quiz for this lesson. It completes when you have watched ${info.unlock_pct}% of it.`}</p>
      </div>
    );
  }
  if (!live.unlocked) {
    return (
      <div className="flex items-start gap-3 text-sm bg-slate-50 border border-slate-100 rounded-2xl p-4 text-slate-600" aria-label="Quiz">
        <Lock size={18} className="shrink-0 mt-0.5 text-slate-400" />
        <div><p className="font-semibold text-slate-700">Quiz locked</p><p className="text-xs mt-0.5">Watch {info.unlock_pct}% of the video to open it. You are at {live.pct}%.</p></div>
      </div>
    );
  }
  if (!quiz) return <div className="flex justify-center py-6">{error ? <ErrorLine>{error}</ErrorLine> : <Loader2 className="w-5 h-5 animate-spin text-slate-400" />}</div>;

  const alreadyPassed = (quiz.passed || result?.passed) && !retake;
  const submit = async () => {
    setBusy(true); setError('');
    try {
      const r = await call(`/videos/${videoId}/quiz`, { method: 'POST', body: { answers } });
      setResult(r);
      setRetake(false);
      if (r.passed) await onPassed();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const again = () => { setResult(null); setRetake(true); setAnswers(Array(quiz.questions.length).fill(null)); };

  return (
    <section className="border border-indigo-100 rounded-2xl overflow-hidden" aria-label="Quiz">
      <div className="flex items-center justify-between gap-3 bg-indigo-50/60 px-5 py-3">
        <h4 className="text-sm font-bold text-indigo-900 flex items-center gap-2"><Award size={16} /> Quiz</h4>
        <span className="text-[11px] font-semibold text-indigo-700">Pass mark {quiz.pass_mark_pct}%{quiz.best_score !== null ? ` · best ${quiz.best_score}%` : ''}</span>
      </div>
      <div className="p-5 space-y-5">
        <ErrorLine>{error}</ErrorLine>
        {result ? (
          <div className={`text-sm rounded-2xl p-4 border ${result.passed ? 'bg-emerald-50 border-emerald-100 text-emerald-800' : 'bg-rose-50 border-rose-100 text-rose-800'}`} role="status">
            <p className="font-bold">{result.passed ? `Passed with ${result.score_pct}%. The next lesson is open.` : `You scored ${result.score_pct}%. You need ${result.pass_mark_pct}%.`}</p>
            {!result.passed && <p className="text-xs mt-1">Marked wrong: {result.results.map((r, i) => (r.correct ? null : `Question ${i + 1}`)).filter(Boolean).join(', ')}. Have another go.</p>}
            <div className="flex gap-2 mt-3">
              {!result.passed && <button onClick={again} className="text-xs font-bold bg-white border border-rose-200 rounded-xl px-4 py-2 hover:bg-rose-50">Try again</button>}
              {result.passed && <button onClick={again} className="text-xs font-bold bg-white border border-emerald-200 rounded-xl px-4 py-2 hover:bg-emerald-50">Retake</button>}
            </div>
          </div>
        ) : alreadyPassed ? (
          <div className="text-sm rounded-2xl p-4 border bg-emerald-50 border-emerald-100 text-emerald-800 flex items-center justify-between gap-3" role="status">
            <p className="font-bold flex items-center gap-2"><CheckCircle2 size={16} /> You passed this quiz.</p>
            <button onClick={again} className="text-xs font-bold bg-white border border-emerald-200 rounded-xl px-4 py-2 hover:bg-emerald-50 shrink-0">Retake</button>
          </div>
        ) : (
          <>
            {quiz.questions.map((qu, qi) => (
              <fieldset key={qu.id} className="space-y-2">
                <legend className="text-sm font-semibold text-slate-900"><span className="text-slate-400 mr-1">{qi + 1}.</span>{qu.question}</legend>
                <div className="space-y-1.5">
                  {qu.options.map((o, oi) => (
                    <label key={o + oi} className={`flex items-center gap-3 text-sm rounded-xl border px-3 py-2.5 cursor-pointer transition ${answers[qi] === oi ? 'border-indigo-300 bg-indigo-50 text-indigo-900' : 'border-slate-200 hover:bg-slate-50 text-slate-700'}`}>
                      <input type="radio" name={`q-${qu.id}`} checked={answers[qi] === oi} onChange={() => setAnswers((a) => a.map((x, i) => (i === qi ? oi : x)))} className="w-4 h-4 accent-indigo-600" />
                      <span className="break-words min-w-0">{o}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            <button disabled={busy || answers.some((a) => a === null)} onClick={submit} className="flex items-center gap-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-5 py-2.5 rounded-xl shadow-sm transition active:scale-95">
              <CheckCircle2 size={16} /> {busy ? 'Checking…' : 'Submit answers'}
            </button>
          </>
        )}
      </div>
    </section>
  );
}
