import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Users, GraduationCap, Briefcase, CalendarClock, UserCheck, Award, KeyRound, Video, Building2, ChevronRight,
  Sparkles, CheckCircle2, AlertCircle, UserPlus, FileText, HelpCircle, Clock, ShieldCheck, Gauge, Pencil,
} from 'lucide-react';
import { api } from '../api.js';
import { BarRow, Card, DashboardSkeleton, Empty, Initials, Kpi, KpiGrid, Page, PageHeader, Pill, PrimaryButton } from './ui.jsx';

const STAGES = ['learning', 'communication', 'technical_mocks', 'final_mock', 'job_ready', 'placed'];
const STAGE_LABEL = { learning: 'Learning', communication: 'Communication', technical_mocks: 'Technical mocks', final_mock: 'Final mock', job_ready: 'Job ready', placed: 'Placed' };
const STAGE_TIP = {
  learning: 'Finish your course videos and quizzes to unlock communication practice.',
  communication: 'Practise speaking answers. Three sessions in a row at 7/10 unlock technical mocks.',
  technical_mocks: 'Attend your technical mocks and work on the feedback after each one.',
  final_mock: 'Your final mock decides if you are job ready. Revise your weakest topics.',
  job_ready: 'You are job ready. Keep your resume tailored and apply to matching roles.',
  placed: 'Congratulations on your placement.',
};
const DRIVE_STATUS = { draft: 'Draft', selecting: 'Selecting students', prepping: 'Preparing packs', mocking: 'Mocks running', done: 'Done' };
const KIND = { mock: 'Mock interview', doubt: 'Doubt clearing', final_mock: 'Final mock', ai_mock: 'AI mock' };
const STATUS_TONE = { draft: 'slate', selecting: 'sky', prepping: 'indigo', mocking: 'orange', done: 'emerald' };
const STATUS_CHIP = {
  draft: 'bg-slate-50 text-slate-600 border-slate-200', selecting: 'bg-sky-50 text-sky-700 border-sky-100', prepping: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  mocking: 'bg-orange-50 text-orange-700 border-orange-100', done: 'bg-emerald-50 text-emerald-700 border-emerald-100',
};

const when = (iso) => new Date(iso).toLocaleString('en-IN', { weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
const sum = (list = [], pick = () => true) => list.filter(pick).reduce((a, r) => a + r.total, 0);
const byKey = (list = [], key) => Object.fromEntries(list.map((r) => [r[key], r.total]));
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function ViewAll({ onClick, children }) {
  return <button onClick={onClick} className="flex items-center gap-0.5 text-[11px] font-bold text-blue-600 hover:underline shrink-0">{children}<ChevronRight className="w-3 h-3" /></button>;
}

// Things that need a human today, worked out from the numbers. Shows "all clear" when there are none.
function Attention({ items, go }) {
  return (
    <Card title="Needs attention" icon={AlertCircle}>
      {items.length === 0 ? (
        <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-xl px-3 py-3"><CheckCircle2 className="w-4 h-4 shrink-0" />All clear. Nothing is waiting on you.</div>
      ) : (
        <ul className="space-y-2">
          {items.map((it) => (
            <li key={it.text}>
              <button onClick={() => go(it.tab)} className="w-full flex items-center justify-between gap-3 text-left text-xs bg-amber-50/70 hover:bg-amber-50 border border-amber-100 rounded-xl px-3 py-2.5 transition">
                <span className="text-slate-700 font-medium">{it.text}</span><ChevronRight className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function QuickActions({ actions, go, allowed }) {
  const list = actions.filter((a) => allowed.includes(a.tab));
  return (
    <Card title="Quick actions" icon={Sparkles}>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-2">
        {list.map(({ label, tab, icon: Icon }) => (
          <button key={label} onClick={() => go(tab)} className="flex items-center gap-2.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 border border-slate-200/80 rounded-xl px-3 py-2.5 transition text-left">
            <Icon className="w-4 h-4 text-blue-600 shrink-0" /><span className="truncate">{label}</span>
          </button>
        ))}
      </div>
    </Card>
  );
}

function SessionList({ sessions, who, empty }) {
  if (!sessions.length) return <Empty>{empty}</Empty>;
  return (
    <ul className="divide-y divide-slate-100">
      {sessions.map((s) => (
        <li key={s.id} className="flex items-center justify-between gap-3 py-3 text-xs">
          <div className="flex items-center gap-3 min-w-0">
            <Initials name={s[who] || KIND[s.kind]} />
            <div className="min-w-0">
              <p className="font-bold text-slate-900 truncate">{KIND[s.kind] || s.kind}{s.mock_number ? ` ${s.mock_number}` : ''}{s[who] ? ` · ${s[who]}` : ''}</p>
              <p className="text-slate-400 flex items-center gap-1"><Clock className="w-3 h-3" />{when(s.starts_at)}</p>
            </div>
          </div>
          {s.meeting_url && <a href={s.meeting_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-blue-600 font-bold hover:underline shrink-0"><Video className="w-3.5 h-3.5" /> Join</a>}
        </li>
      ))}
    </ul>
  );
}

// ------------------------------------------------------------------ Admin
function Admin({ d, go, allowed }) {
  const role = (r) => d.users_by_role.find((x) => x.role === r) || { total: 0, active: 0 };
  const stages = byKey(d.students_by_stage, 'stage');
  const students = sum(d.students_by_stage);
  const drives = byKey(d.drives_by_status, 'status');
  const openDrives = sum(d.drives_by_status, (r) => r.status !== 'done');
  const allUsers = d.users_by_role.reduce((a, r) => a + r.total, 0);
  const activeUsers = d.users_by_role.reduce((a, r) => a + r.active, 0);
  const attention = [
    d.never_logged_in > 0 && { text: `${d.never_logged_in} login${d.never_logged_in === 1 ? ' has' : 's have'} never signed in`, tab: 'Master' },
    (drives.selecting || 0) > 0 && { text: `${drives.selecting} drive${drives.selecting === 1 ? ' is' : 's are'} waiting for students to be picked`, tab: 'Drives' },
  ].filter(Boolean);

  return (
    <>
      <KpiGrid>
        <Kpi label="Students" value={role('student').total} icon={GraduationCap} tone="blue" hint={`${role('student').active} active`} onClick={() => go('Student List')} />
        <Kpi label="Trainers" value={role('trainer').total} icon={UserCheck} tone="violet" />
        <Kpi label="Active logins" value={activeUsers} icon={ShieldCheck} tone="emerald" hint={`of ${allUsers}`} onClick={() => go('Master')} />
        <Kpi label="Upcoming sessions" value={d.upcoming_sessions} icon={CalendarClock} tone="sky" />
        <Kpi label="Open drives" value={openDrives} icon={Building2} tone="indigo" onClick={() => go('Drives')} />
        <Kpi label="Never logged in" value={d.never_logged_in} icon={KeyRound} tone="amber" hint="Share a password" onClick={() => go('Master')} />
      </KpiGrid>

      <div className="grid grid-cols-1 lg:grid-cols-2 items-start gap-5 sm:gap-6">
        <Card title="Student pipeline" icon={GraduationCap}>
          {students === 0 ? <Empty>No students yet.</Empty> : (
            <div className="space-y-3.5">
              {STAGES.map((s, i) => <BarRow key={s} label={STAGE_LABEL[s]} value={stages[s] || 0} pct={((stages[s] || 0) / students) * 100} tone={['blue', 'sky', 'indigo', 'violet', 'emerald', 'emerald'][i]} />)}
            </div>
          )}
        </Card>
        <Card title="Logins by role" icon={Users} action={<ViewAll onClick={() => go('Master')}>Manage users</ViewAll>}>
          <div className="space-y-3.5">
            {d.users_by_role.map((r) => <BarRow key={r.role} label={cap(r.role)} value={r.active} shown={`${r.active} / ${r.total} active`} pct={r.total ? (r.active / r.total) * 100 : 0} tone="blue" />)}
          </div>
        </Card>
        <Card title="Placement drives" icon={Building2} action={<ViewAll onClick={() => go('Drives')}>Open drives</ViewAll>} className="lg:col-span-2">
          {d.drives_by_status.length === 0 ? <Empty>No drives yet.</Empty> : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3.5">
              {d.drives_by_status.map((r) => <BarRow key={r.status} label={DRIVE_STATUS[r.status] || r.status} value={r.total} pct={(r.total / sum(d.drives_by_status)) * 100} tone={STATUS_TONE[r.status] === 'slate' ? 'blue' : STATUS_TONE[r.status]} />)}
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 sm:gap-6">
        <Card title="Recent logins" icon={Clock}>
          {d.recent_logins.length === 0 ? <Empty>Nobody has logged in yet.</Empty> : (
            <ul className="divide-y divide-slate-100">
              {d.recent_logins.map((r) => (
                <li key={`${r.name}${r.last_login_at}`} className="flex items-center justify-between gap-3 py-2.5 text-xs">
                  <span className="flex items-center gap-2.5 min-w-0"><Initials name={r.name} /><span className="min-w-0"><span className="font-bold text-slate-900 block truncate">{r.name}</span><span className="text-slate-400 capitalize">{r.role}</span></span></span>
                  <span className="text-slate-500 text-right shrink-0">{when(r.last_login_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Attention items={attention} go={go} />
        <QuickActions go={go} allowed={allowed} actions={[
          { label: 'Add a user', tab: 'Master', icon: UserPlus }, { label: 'New placement drive', tab: 'Drives', icon: Building2 },
          { label: 'Resume Optimizer', tab: 'Resume Optimizer', icon: FileText }, { label: 'Q&A Generator', tab: 'QnA Generator', icon: HelpCircle },
        ]} />
      </div>
    </>
  );
}

// ------------------------------------------------------------------ Operations
function Operations({ d, go, allowed }) {
  const stages = byKey(d.students_by_stage, 'stage');
  const drives = byKey(d.drives_by_status, 'status');
  const openDrives = sum(d.drives_by_status, (r) => r.status !== 'done');
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const attention = [
    d.no_batch > 0 && { text: `${plural(d.no_batch, 'student has', 'students have')} no batch yet`, tab: 'Student List' },
    d.no_skills > 0 && { text: `${plural(d.no_skills, 'student has', 'students have')} no skills added, so drives cannot rank them`, tab: 'Student List' },
    d.never_logged_in > 0 && { text: `${plural(d.never_logged_in, 'student has', 'students have')} never signed in`, tab: 'Student List' },
    d.unassigned_sessions > 0 && { text: `${plural(d.unassigned_sessions, 'upcoming mock has', 'upcoming mocks have')} no trainer`, tab: 'Live Mocks' },
    (drives.selecting || 0) > 0 && { text: `${plural(drives.selecting, 'drive is', 'drives are')} waiting for students to be picked`, tab: 'Drives' },
  ].filter(Boolean);

  return (
    <>
      <KpiGrid>
        <Kpi label="Students" value={d.students_total} icon={GraduationCap} tone="blue" hint={`${d.students_active} active`} onClick={() => go('Student List')} />
        <Kpi label="Job ready" value={(stages.job_ready || 0) + (stages.placed || 0)} icon={Award} tone="emerald" hint="incl. placed" />
        <Kpi label="No batch" value={d.no_batch} icon={Users} tone="amber" onClick={() => go('Student List')} />
        <Kpi label="No skills yet" value={d.no_skills} icon={Pencil} tone="violet" onClick={() => go('Student List')} />
        <Kpi label="Upcoming mocks" value={d.upcoming_sessions} icon={CalendarClock} tone="sky" onClick={() => go('Live Mocks')} />
        <Kpi label="Open drives" value={openDrives} icon={Building2} tone="indigo" onClick={() => go('Drives')} />
      </KpiGrid>

      <div className="grid grid-cols-1 lg:grid-cols-2 items-start gap-5 sm:gap-6">
        <Card title="Student pipeline" icon={GraduationCap} action={<ViewAll onClick={() => go('Student List')}>All students</ViewAll>}>
          {d.students_total === 0 ? <Empty>No students yet. Import your Excel sheet from the Student List.</Empty> : (
            <div className="space-y-3.5">
              {STAGES.map((s, i) => <BarRow key={s} label={STAGE_LABEL[s]} value={stages[s] || 0} pct={((stages[s] || 0) / d.students_total) * 100} tone={['blue', 'sky', 'indigo', 'violet', 'emerald', 'emerald'][i]} />)}
            </div>
          )}
        </Card>
        <Card title="Batches" icon={Users}>
          {d.batches.length === 0 ? <Empty>No batches yet.</Empty> : (
            <div className="space-y-3.5">
              {d.batches.map((b) => <BarRow key={b.id} label={b.name} value={b.job_ready} shown={`${b.job_ready} / ${b.students} job ready`} pct={b.students ? (b.job_ready / b.students) * 100 : 0} tone="emerald" />)}
            </div>
          )}
        </Card>
        <Card title="Placement drives" icon={Building2} action={<ViewAll onClick={() => go('Drives')}>Open drives</ViewAll>} className="lg:col-span-2">
          {d.drives_by_status.length === 0 ? <Empty>No drives yet.</Empty> : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3.5">
              {d.drives_by_status.map((r) => <BarRow key={r.status} label={DRIVE_STATUS[r.status] || r.status} value={r.total} pct={(r.total / sum(d.drives_by_status)) * 100} tone={STATUS_TONE[r.status] === 'slate' ? 'blue' : STATUS_TONE[r.status]} />)}
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 sm:gap-6">
        <Card title="Recently added students" icon={UserPlus}>
          {d.recent_students.length === 0 ? <Empty>No students yet.</Empty> : (
            <ul className="divide-y divide-slate-100">
              {d.recent_students.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-3 py-2.5 text-xs">
                  <span className="flex items-center gap-2.5 min-w-0"><Initials name={r.name} /><span className="min-w-0"><span className="font-bold text-slate-900 block truncate">{r.name}</span><span className="text-slate-400">{r.student_code || 'No ID yet'}</span></span></span>
                  <Pill className="bg-slate-50 text-slate-600 border-slate-200">{STAGE_LABEL[r.stage]}</Pill>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Latest Excel imports" icon={FileText}>
          {d.recent_imports.length === 0 ? <Empty>No imports yet.</Empty> : (
            <ul className="divide-y divide-slate-100">
              {d.recent_imports.map((r) => (
                <li key={r.id} className="py-2.5 text-xs">
                  <p className="font-bold text-slate-900 truncate">{r.file_name}</p>
                  <p className="text-slate-400">{r.rows_imported} imported · {r.rows_skipped} skipped · {when(r.created_at)}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Attention items={attention} go={go} />
        <QuickActions go={go} allowed={allowed} actions={[
          { label: 'Import students', tab: 'Student List', icon: UserPlus }, { label: 'New placement drive', tab: 'Drives', icon: Building2 },
          { label: 'Live mocks', tab: 'Live Mocks', icon: Video }, { label: 'Resume Optimizer', tab: 'Resume Optimizer', icon: FileText },
        ]} />
      </div>
    </>
  );
}

// ------------------------------------------------------------------ Placement
function Placement({ d, go, allowed }) {
  const stages = byKey(d.students_by_stage, 'stage');
  const drives = byKey(d.drives_by_status, 'status');
  const open = sum(d.drives_by_status, (r) => r.status !== 'done');
  const selected = d.recent_drives.reduce((a, r) => a + r.selected_count, 0);
  const attention = [(drives.selecting || 0) > 0 && { text: `${drives.selecting} drive${drives.selecting === 1 ? ' is' : 's are'} waiting for students to be picked`, tab: 'Drives' }].filter(Boolean);

  return (
    <>
      <KpiGrid>
        <Kpi label="Open drives" value={open} icon={Building2} tone="indigo" onClick={() => go('Drives')} />
        <Kpi label="All drives" value={sum(d.drives_by_status)} icon={Briefcase} tone="blue" />
        <Kpi label="Students" value={d.students_total} icon={GraduationCap} tone="sky" onClick={() => go('Student List')} />
        <Kpi label="Job ready" value={d.students_job_ready} icon={Award} tone="emerald" />
        <Kpi label="Put forward" value={selected} icon={UserCheck} tone="violet" hint="in recent drives" />
        <Kpi label="Placements" value={d.placements_total} icon={Sparkles} tone="amber" />
      </KpiGrid>

      <div className="grid grid-cols-1 lg:grid-cols-2 items-start gap-5 sm:gap-6">
        <Card title="Recent drives" icon={Building2} action={<ViewAll onClick={() => go('Drives')}>All drives</ViewAll>}>
          {d.recent_drives.length === 0 ? <Empty>No drives yet. Create the first one from the Drives tab.</Empty> : (
            <ul className="divide-y divide-slate-100">
              {d.recent_drives.map((r) => (
                <li key={r.id}>
                  <button onClick={() => go('Drives')} className="w-full flex items-center justify-between gap-3 py-3 text-xs text-left hover:bg-slate-50/70 rounded-xl px-1 transition">
                    <span className="min-w-0"><span className="font-bold text-slate-900 block truncate">{r.company}</span><span className="text-slate-400 block truncate">{r.role}</span></span>
                    <span className="flex items-center gap-2 shrink-0"><Pill className={STATUS_CHIP[r.status]}>{DRIVE_STATUS[r.status] || r.status}</Pill><span className="text-slate-500 tabular-nums w-14 text-right">{r.selected_count} picked</span></span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Student readiness" icon={GraduationCap}>
          {d.students_total === 0 ? <Empty>No students yet.</Empty> : (
            <div className="space-y-3.5">
              {STAGES.map((s, i) => <BarRow key={s} label={STAGE_LABEL[s]} value={stages[s] || 0} pct={((stages[s] || 0) / d.students_total) * 100} tone={['blue', 'sky', 'indigo', 'violet', 'emerald', 'emerald'][i]} />)}
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
        <Attention items={attention} go={go} />
        <QuickActions go={go} allowed={allowed} actions={[
          { label: 'New placement drive', tab: 'Drives', icon: Building2 }, { label: 'Resume Optimizer', tab: 'Resume Optimizer', icon: FileText },
          { label: 'Student list', tab: 'Student List', icon: Users }, { label: 'Job portal', tab: 'Job Portal', icon: Briefcase },
        ]} />
      </div>
    </>
  );
}

// ------------------------------------------------------------------ Trainer
function Trainer({ d, go, allowed }) {
  const p = d.profile;
  const week = d.sessions_this_week || 0;
  const capacity = p?.weekly_capacity || 0;
  const attention = [!p || p.skills.length === 0 ? { text: 'Your skills are not set, so mocks cannot be matched to you', tab: 'Overview' } : null].filter(Boolean);

  return (
    <>
      <KpiGrid count={4}>
        <Kpi label="Sessions this week" value={week} icon={CalendarClock} tone="blue" />
        <Kpi label="Upcoming" value={d.upcoming_total ?? d.upcoming_sessions.length} icon={Clock} tone="sky" />
        <Kpi label="Completed" value={d.done_sessions} icon={Award} tone="emerald" />
        <Kpi label="Weekly capacity" value={capacity || '—'} icon={Gauge} tone="violet" hint="sessions per week" />
      </KpiGrid>

      <div className="grid grid-cols-1 lg:grid-cols-2 items-start gap-5 sm:gap-6">
        <Card title="Upcoming sessions" icon={CalendarClock}>
          <SessionList sessions={d.upcoming_sessions} who="student" empty="Nothing scheduled yet. Sessions appear here, with the join link, once mocks are booked for you." />
        </Card>
        <div className="space-y-5 sm:space-y-6 min-w-0">
          <Card title="This week's load" icon={Gauge}>
            {capacity ? <BarRow label="Booked vs weekly capacity" value={week} shown={`${week} / ${capacity}`} pct={(week / capacity) * 100} tone={week >= capacity ? 'rose' : 'blue'} /> : <Empty>No weekly capacity set yet.</Empty>}
          </Card>
          <Card title="Your skills" icon={Award}>
            {p && p.skills.length ? (
              <div className="flex flex-wrap gap-1.5">{p.skills.map((s) => <Pill key={s} className="bg-violet-50 text-violet-700 border-violet-100">{s}</Pill>)}</div>
            ) : <Empty>No skills on your profile yet. Ask the operations team to add them.</Empty>}
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
        <Attention items={attention} go={go} />
        <QuickActions go={go} allowed={allowed} actions={[
          { label: 'Live mocks', tab: 'Live Mocks', icon: Video }, { label: 'Student list', tab: 'Student List', icon: Users },
          { label: 'Batches', tab: 'Batches', icon: GraduationCap }, { label: 'Progress reports', tab: 'Progress Reports', icon: Award },
        ]} />
      </div>
    </>
  );
}

// ------------------------------------------------------------------ Student
function Student({ d, go, allowed, onFillDetails }) {
  const p = d.profile;
  const fill = d.completeness;
  const at = p ? Math.max(0, STAGES.indexOf(p.stage)) : 0;
  return (
    <>
      <KpiGrid count={4}>
        <Kpi label="Current stage" value={p ? STAGE_LABEL[p.stage] : '—'} icon={GraduationCap} tone="blue" />
        <Kpi label="Level" value={p ? `${p.level} / 5` : '—'} icon={Award} tone="violet" />
        <Kpi label="Upcoming sessions" value={d.upcoming_sessions.length} icon={CalendarClock} tone="sky" />
        <Kpi label="Companies" value={d.drives.length} icon={Building2} tone="emerald" hint="put forward for" />
      </KpiGrid>

      {fill && fill.percent < 100 && (
        <Card title="Complete your profile" icon={UserCheck}
          action={<button onClick={onFillDetails} className="flex items-center gap-1 text-[11px] font-bold text-blue-600 hover:underline shrink-0">Fill my details<ChevronRight className="w-3 h-3" /></button>}>
          <BarRow label="Profile completeness" value={fill.percent} shown={`${fill.percent}%`} pct={fill.percent} tone={fill.percent >= 50 ? 'blue' : 'amber'} />
          <p className="text-xs text-slate-600">Companies are matched to you using your <b>skills</b> and the <b>roles you want</b>. A complete profile gets you into more drives.</p>
          <div className="flex flex-wrap gap-1.5">{fill.missing.map((m) => <Pill key={m.key} className="bg-amber-50 text-amber-700 border-amber-100">{m.label.replace(/ \(.*\)/, '')}</Pill>)}</div>
          <PrimaryButton icon={Pencil} onClick={onFillDetails} className="w-full sm:w-auto">Fill my details</PrimaryButton>
        </Card>
      )}

      <Card title="Your journey" icon={GraduationCap}>
        {!p ? <Empty>Your student profile is not set up yet. Contact the operations team.</Empty> : (
          <div className="space-y-4">
            <p className="text-xs text-slate-500">{[p.degree, p.college, p.city, p.batch && `Batch ${p.batch}`].filter(Boolean).join(' · ') || 'Profile details not added yet'}</p>
            <ol className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-2">
              {STAGES.map((s, i) => (
                <li key={s} className={`rounded-xl border px-3 py-2.5 text-[11px] font-semibold text-center ${i < at ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : i === at ? 'bg-blue-600 border-blue-600 text-white shadow-md shadow-blue-500/20' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                  {i < at && <CheckCircle2 className="w-3 h-3 inline -mt-0.5 mr-1" />}{STAGE_LABEL[s]}
                </li>
              ))}
            </ol>
            <p className="text-xs text-slate-600 bg-blue-50/60 border border-blue-100 rounded-xl px-3 py-2.5"><b>Next step:</b> {STAGE_TIP[p.stage]}</p>
            {p.target_roles?.length > 0 && <p className="text-xs text-slate-500">Target roles: <span className="font-semibold text-slate-700">{p.target_roles.join(', ')}</span></p>}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 items-start gap-5 sm:gap-6">
        <Card title="Upcoming sessions" icon={CalendarClock}>
          <SessionList sessions={d.upcoming_sessions} who="trainer" empty="No mocks booked yet. They will show here, with the join link, as soon as they are scheduled." />
        </Card>
        <Card title="Companies you are put forward for" icon={Building2}>
          {d.drives.length === 0 ? <Empty>Not shortlisted for any company yet.</Empty> : (
            <ul className="divide-y divide-slate-100">
              {d.drives.map((r) => <li key={r.id} className="py-3 text-xs"><p className="font-bold text-slate-900">{r.company}</p><p className="text-slate-400">{r.role}</p></li>)}
            </ul>
          )}
        </Card>
      </div>

      <QuickActions go={go} allowed={allowed} actions={[
        { label: 'Resume Optimizer', tab: 'Resume Optimizer', icon: FileText }, { label: 'Q&A Generator', tab: 'QnA Generator', icon: HelpCircle },
        { label: 'Live mocks', tab: 'Live Mocks', icon: Video }, { label: 'Learning modules', tab: 'Learning Modules', icon: GraduationCap },
      ]} />
    </>
  );
}

const VIEWS = { Admin, Operations, Placement, Trainer, Student };
const COPY = {
  Admin: { subtitle: 'Logins, roles and how the platform is being used.', cta: { label: 'Manage Users', tab: 'Master', icon: UserPlus } },
  Operations: { subtitle: 'Your students, batches and drives day to day.', cta: { label: 'Student List', tab: 'Student List', icon: GraduationCap } },
  Placement: { subtitle: 'Company drives and how ready your students are.', cta: { label: 'New Drive', tab: 'Drives', icon: Building2 } },
  Trainer: { subtitle: 'Your sessions, capacity and skills.', cta: { label: 'Live Mocks', tab: 'Live Mocks', icon: Video } },
  Student: { subtitle: 'Your progress, upcoming mocks and companies.', cta: { label: 'Resume Optimizer', tab: 'Resume Optimizer', icon: FileText } },
};

export default function RoleDashboard({ token, user, role, allowedTabs = [], setActiveTab, onFillDetails, onSessionExpired }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const expiredRef = useRef(onSessionExpired);
  expiredRef.current = onSessionExpired;

  const load = useCallback(async () => {
    try {
      setError('');
      setData(await api('/dashboard', { token, onExpired: () => expiredRef.current?.() }));
    } catch (e) {
      setError(e.message);
    }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const View = VIEWS[role];
  const copy = COPY[role];
  const cta = copy && allowedTabs.includes(copy.cta.tab) ? copy.cta : null;

  if (!data && !error) return <DashboardSkeleton />;

  return (
    <Page>
      <PageHeader
        title={<>Overview <Sparkles className="w-5 h-5 text-amber-500 inline -mt-1" /></>}
        subtitle={`Welcome back, ${user.name}. ${copy?.subtitle || ''}`}
        action={cta && <PrimaryButton icon={cta.icon} onClick={() => setActiveTab(cta.tab)}>{cta.label}</PrimaryButton>}
      />
      {error && (
        <p className="text-xs font-medium text-rose-600 bg-rose-50 border border-rose-100 rounded-2xl px-4 py-3">
          {error} <button onClick={load} className="underline font-bold ml-1">Try again</button>
        </p>
      )}
      {data && View && <View d={data} go={setActiveTab} allowed={allowedTabs} onFillDetails={onFillDetails} />}
    </Page>
  );
}
