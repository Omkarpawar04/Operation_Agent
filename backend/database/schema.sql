-- FinXL placement platform: database schema (PostgreSQL 15+)
-- Generated 2026-10-19. One file for the whole platform; the phase comment on each table says when it is built.
-- Five people roles log in: admin, operations, placement, trainer, student. AI agents write the rest.

create extension if not exists pgcrypto;  -- gen_random_uuid()
create extension if not exists citext;    -- case-insensitive email
create extension if not exists btree_gist; -- no-overlap rules on sessions

create sequence student_code_seq;  -- numbers for generated student codes

create type user_role as enum ('admin', 'operations', 'placement', 'trainer', 'student');
create type student_stage as enum ('learning', 'communication', 'technical_mocks', 'final_mock', 'job_ready', 'placed');
create type session_kind as enum ('mock', 'doubt', 'final_mock', 'ai_mock');

-- People and access · phase 1
-- Everyone who logs in. Only four roles: operations, placement, trainer, student.
create table users (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email citext not null unique,  -- login id
  phone text,  -- for OTP and WhatsApp
  role user_role not null,  -- admin | operations | placement | trainer | student
  password_hash text,  -- scrypt hash (never the password). Until Google/OTP login is built
  is_active boolean not null default true,
  last_login_at timestamptz,
  created_at timestamptz not null default now()
);

-- Learning · phase 3
-- A course, with its pass rules.
create table courses (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  is_published boolean not null default false,  -- students only see published courses
  pass_mark_pct smallint not null default 60,  -- quiz pass mark
  watch_to_unlock_pct smallint not null default 90,  -- watch % before the quiz opens
  trainer_release boolean not null default true  -- a topic's videos stay hidden until a trainer marks the topic complete for the batch
);

-- People and access · phase 1
-- A group of students who start together.
create table batches (
  id uuid primary key default gen_random_uuid(),
  name text not null,  -- e.g. Batch Oct-26
  course_id uuid references courses(id),
  starts_on date,
  ends_on date,
  created_at timestamptz not null default now()
);

-- People and access · phase 1
-- One row per Excel upload by the operations team, with what was skipped and why.
create table student_imports (
  id uuid primary key default gen_random_uuid(),
  file_name text not null,
  uploaded_by uuid not null references users(id),  -- operations user
  rows_total int not null,
  rows_imported int not null,
  rows_skipped int not null,
  problems jsonb,  -- [{row, reason}]
  created_at timestamptz not null default now()
);

-- People and access · phase 1
-- The student 360 profile. Hub table: almost everything else points here.
create table students (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references users(id),
  student_code text unique,  -- e.g. FXL-0001; from the Excel when it has one, else generated
  aadhaar_enc text,  -- AES-encrypted ID numbers (never plain text); operations can reveal them, each view is logged
  pan_enc text,
  batch_id uuid references batches(id),
  import_id uuid references student_imports(id),  -- which upload created them
  college text,
  degree text,
  city text,
  target_roles text[],
  extra jsonb,  -- any other Excel columns, kept as-is
  stage student_stage not null default 'learning',  -- learning | communication | technical_mocks | final_mock | job_ready | placed
  level smallint not null default 0,  -- level engine 0 to 5
  job_ready_at timestamptz,
  fast_track_by uuid references users(id),  -- staff who opened every topic for this student
  fast_track_at timestamptz,  -- null = videos unlock one by one
  created_at timestamptz not null default now()
);

-- People and access · phase 1
-- Call notes and follow-ups the operations team adds on the 360 record.
create table student_notes (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id),
  author_id uuid not null references users(id),
  body text not null,
  created_at timestamptz not null default now()
);

-- People and access · phase 1
-- Trainer profile used by auto-scheduling.
create table trainers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references users(id),
  skills text[] not null,  -- topics they can take
  weekly_capacity smallint not null,  -- max sessions per week
  created_at timestamptz not null default now()
);

-- People and access · phase 1
-- Which trainers teach which batch. A trainer only sees and opens topics for these batches.
create table batch_trainers (
  batch_id uuid not null references batches(id),
  trainer_id uuid not null references trainers(id),
  created_at timestamptz not null default now(),
  primary key (batch_id, trainer_id)
);

-- People and access · phase 1
-- Weekly time windows. Replaces the weekly Excel sheet.
create table trainer_availability (
  id uuid primary key default gen_random_uuid(),
  trainer_id uuid not null references trainers(id),
  weekday smallint not null,  -- 0 = Monday
  starts time not null,
  ends time not null,
  valid_from date not null,
  valid_to date  -- null = until changed
);

-- Learning · phase 3
-- Modules inside a course, in order.
create table course_modules (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references courses(id),
  title text not null,
  position smallint not null
);

-- Learning · phase 3
-- One lesson video. Videos unlock in order.
create table videos (
  id uuid primary key default gen_random_uuid(),
  module_id uuid not null references course_modules(id),
  title text not null,
  position smallint not null,
  duration_sec int,  -- optional
  video_url text,  -- video host or storage
  key_points text[]
);

-- Learning · phase 3
-- Trainer marks a topic (course module) complete for a batch; only then do its videos appear to that batch.
create table topic_releases (
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references batches(id),
  module_id uuid not null references course_modules(id),
  released_by uuid not null references trainers(id),  -- trainer who taught it
  released_at timestamptz not null default now(),
  unique (batch_id, module_id)
);

-- Learning · phase 3
-- Opens one topic early for one student (faster learners), ahead of their batch.
create table student_topic_access (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id),
  module_id uuid not null references course_modules(id),
  opened_by uuid not null references users(id),
  created_at timestamptz not null default now(),
  unique (student_id, module_id)
);

-- Learning · phase 3
-- Multiple-choice questions shown after a video.
create table quiz_questions (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id),
  question text not null,
  options text[] not null,
  answer_index smallint not null,
  position smallint not null
);

-- Learning · phase 3
-- Real watch time per student per video. Skipping ahead does not count. Inside an open topic, each video opens after the previous quiz is passed.
create table video_progress (
  student_id uuid not null references students(id),  -- primary key with video_id
  video_id uuid not null references videos(id),
  watched_seconds bit varying,  -- one bit per second actually watched
  watched_pct smallint not null default 0,
  last_position_sec int not null default 0,  -- resume point
  duration_sec int,  -- video length as the player reported it
  last_beat_at timestamptz,  -- last progress message; limits how fast watched seconds can be claimed
  started_at timestamptz,
  quiz_unlocked_at timestamptz,
  passed_at timestamptz,
  primary key (student_id, video_id)
);

-- Learning · phase 3
-- Every quiz attempt and its score.
create table quiz_attempts (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id),
  video_id uuid not null references videos(id),
  answers smallint[] not null,  -- chosen option per question
  score_pct smallint not null,
  passed boolean not null,
  created_at timestamptz not null default now()
);

-- Communication coach · phase 2
-- Speaking questions: introduce yourself, HR, explain it simply.
create table comms_drills (
  id uuid primary key default gen_random_uuid(),
  group_name text not null,
  question text not null,
  target_seconds smallint not null,
  guidance text,  -- what a good answer does
  is_active boolean not null default true
);

-- Communication coach · phase 2
-- One practice answer with its AI scores and feedback.
create table comms_sessions (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id),
  drill_id uuid not null references comms_drills(id),
  mode text not null,  -- voice | typed
  duration_sec int,
  words_per_minute smallint,
  filler_words smallint,
  transcript text not null,
  audio_url text,
  scores jsonb not null,  -- {fluency, grammar, structure, clarity, confidence, relevance, pronunciation}
  overall numeric(3,1) not null,  -- out of 10
  went_well text[],
  fixes text[],
  better_answer text,
  created_at timestamptz not null default now()
);

-- Communication coach · phase 2
-- Unlocks between stages, e.g. 3 sessions in a row at 7/10 unlock technical mocks.
create table student_gates (
  student_id uuid not null references students(id),  -- primary key with gate
  gate text not null,  -- technical_mocks | final_mock | job_ready
  unlocked_at timestamptz not null,
  reason text,  -- rule that passed
  primary key (student_id, gate)
);

-- Communication coach · phase 3
-- Skill list for the skill matrix.
create table skills (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  category text  -- technical | communication | behavioural
);

-- Communication coach · phase 3
-- Every score that feeds a student's skill matrix and level.
create table skill_scores (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id),
  skill_id uuid not null references skills(id),
  score numeric(3,1) not null,  -- out of 10
  source text not null,  -- quiz | comms | mock | assessment
  source_id uuid,  -- row that produced it
  created_at timestamptz not null default now()
);

-- Companies, JDs and Q&A · phase 1
-- Each company once. Questions, drives, jobs and placements link here.
create table companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  name_key text not null unique,  -- lower-case, trimmed, for matching
  sector text,
  website text,
  created_at timestamptz not null default now()
);

-- Companies, JDs and Q&A · phase 1
-- A placement drive: one company, one role, one JD.
create table drives (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id),
  role text not null,
  location text,
  jd_text text not null,
  jd_file_url text,
  requirements jsonb,  -- skills, experience, location read from the JD by AI
  mocks_per_student smallint not null default 3,  -- 3 to 5
  status text not null,  -- draft | selecting | prepping | mocking | done
  created_by uuid not null references users(id),  -- placement user
  created_at timestamptz not null default now()
);

-- Companies, JDs and Q&A · phase 1
-- Students ranked and picked for a drive, and where each one is.
create table drive_students (
  id uuid primary key default gen_random_uuid(),
  drive_id uuid not null references drives(id),
  student_id uuid not null references students(id),
  match_score smallint,  -- 0 to 100
  match_reasons jsonb,  -- why they ranked there
  selected boolean not null default false,
  status text not null,  -- ranked | pack_review | mocking | report_ready | put_forward
  final_verdict text,  -- job_ready | one_more_mock | not_ready
  created_at timestamptz not null default now(),
  unique (drive_id, student_id)
);

-- Companies, JDs and Q&A · phase 1
-- The interview Q&A bank. Every row is in the consolidated pool; rows with a company also show under that company.
create table interview_questions (
  id uuid primary key default gen_random_uuid(),
  company_id uuid references companies(id),  -- null = general question
  question text not null,
  question_key text not null,  -- normalised text, stops duplicates
  ideal_answer text,
  round text not null,  -- technical | hr | behavioural | case_study | other
  source text not null,  -- manual | excel | ai | reported_after_interview
  added_by uuid references users(id),
  created_at timestamptz not null default now(),
  unique nulls not distinct (company_id, question_key)
);

-- Companies, JDs and Q&A · phase 1
-- Every resume version: base resume and one per company JD.
create table resumes (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id),
  drive_id uuid references drives(id),  -- null = base resume
  version smallint not null,
  content jsonb not null,  -- structured sections
  file_url text,  -- PDF
  ats_match_pct smallint,
  missing_keywords text[],
  created_at timestamptz not null default now()
);

-- Companies, JDs and Q&A · phase 1
-- What a student gets for one company: resume, script and Q&A. Placement approves it.
create table prep_packs (
  id uuid primary key default gen_random_uuid(),
  drive_student_id uuid not null unique references drive_students(id),
  resume_id uuid references resumes(id),
  script text,  -- tell me about yourself, why this company
  status text not null,  -- draft | approved
  approved_by uuid references users(id),
  approved_at timestamptz,
  created_at timestamptz not null default now()
);

-- Companies, JDs and Q&A · phase 1
-- Questions in a pack. Company questions from the bank first, then AI ones.
create table pack_questions (
  id uuid primary key default gen_random_uuid(),
  pack_id uuid not null references prep_packs(id),
  question_id uuid references interview_questions(id),  -- set when taken from the bank
  question text not null,
  ideal_answer text,
  key_points text[],
  follow_ups text[],
  position smallint not null
);

-- Mocks and doubt sessions · phase 1
-- Every booked session: trainer mock, doubt clearing, final face-to-face mock or AI mock.
create table sessions (
  id uuid primary key default gen_random_uuid(),
  kind session_kind not null,  -- mock | doubt | final_mock | ai_mock
  student_id uuid not null references students(id),
  trainer_id uuid references trainers(id),  -- null for AI mocks
  drive_student_id uuid references drive_students(id),  -- set for JD-based mocks
  mock_number smallint,  -- 1 to 5
  reason text,  -- e.g. score below 6 on DCF
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  meeting_url text,
  calendar_event_id text,
  status text not null,  -- scheduled | done | missed | rescheduled | cancelled
  created_at timestamptz not null default now()
);

-- Mocks and doubt sessions · phase 1
-- Which questions were asked in a session, and how each was answered.
create table session_questions (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions(id),
  question_id uuid references interview_questions(id),
  asked_order smallint not null,
  answer_transcript text,
  score numeric(3,1)
);

-- Mocks and doubt sessions · phase 1
-- Trainer scores plus AI feedback for one session.
create table scorecards (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null unique references sessions(id),
  scores jsonb not null,  -- {technical, financial_concepts, excel, modelling, communication, confidence, behavioural, resume_knowledge}, each /10
  overall numeric(3,1) not null,
  trainer_notes text,
  ai_feedback jsonb,  -- strengths, gaps, next steps
  created_at timestamptz not null default now()
);

-- Mocks and doubt sessions · phase 1
-- Video, audio and transcript of every mock and doubt session.
create table recordings (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions(id),
  video_url text not null,
  transcript text,
  duration_sec int,
  created_at timestamptz not null default now()
);

-- Jobs and placement · phase 4
-- Openings the job agent finds for job-ready students.
create table job_postings (
  id uuid primary key default gen_random_uuid(),
  company_id uuid references companies(id),
  title text not null,
  location text,
  portal text not null,  -- naukri | foundit | linkedin | other
  url text,
  posted_on date,
  created_at timestamptz not null default now()
);

-- Jobs and placement · phase 4
-- One student applying to one job or drive, with its latest status.
create table applications (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id),
  job_posting_id uuid references job_postings(id),
  drive_id uuid references drives(id),
  resume_id uuid references resumes(id),  -- which version was sent
  portal text,
  status text not null,  -- applied | viewed | shortlisted | interview | rejected | offer
  tracked_by text,  -- extension | email | manual
  applied_at timestamptz not null,
  status_at timestamptz not null
);

-- Jobs and placement · phase 4
-- Status history of each application, with the evidence.
create table application_events (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null references applications(id),
  status text not null,
  evidence text,  -- e.g. email subject
  created_at timestamptz not null default now()
);

-- Jobs and placement · phase 1
-- An offer recorded against a student and company.
create table placements (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id),
  company_id uuid not null references companies(id),
  application_id uuid references applications(id),
  drive_id uuid references drives(id),
  role text not null,
  ctc_lpa numeric(5,2),  -- salary, lakhs per year
  offer_date date not null,
  joining_date date,
  created_at timestamptz not null default now()
);

-- Jobs and placement · phase 4
-- After a real interview: questions asked and outcome. Each question is also added to the Q&A bank.
create table interview_feedback (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id),
  company_id uuid not null references companies(id),
  application_id uuid references applications(id),
  round text,
  questions_asked text[] not null,
  outcome text,  -- selected | rejected | waiting
  notes text,
  created_at timestamptz not null default now()
);

-- Messages, AI and 360 timeline · phase 1
-- Every email, WhatsApp message and calendar block, with delivery status.
create table notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),  -- recipient
  channel text not null,  -- email | whatsapp | calendar
  template text not null,
  payload jsonb,
  status text not null,  -- queued | sent | delivered | failed
  provider_ref text,
  scheduled_for timestamptz,  -- when to send (24 h / 1 h / 10 min reminders); null = send now
  sent_at timestamptz,
  error text,
  created_at timestamptz not null default now()
);

-- Messages, AI and 360 timeline · phase 1
-- Every AI call: what it made, which model, cost. For audit and cost tracking.
create table ai_jobs (
  id uuid primary key default gen_random_uuid(),
  kind text not null,  -- match | resume | qa | script | scorecard | comms_score
  ref_table text,
  ref_id uuid,
  model text not null,
  status text not null,
  input_tokens int,
  output_tokens int,
  cost_inr numeric(8,2),
  created_at timestamptz not null default now()
);

-- Messages, AI and 360 timeline · phase 1
-- One row per thing that happens to a student. The 360 timeline reads from here.
create table activity_log (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id),
  actor_id uuid references users(id),  -- null = AI agent or system
  kind text not null,  -- imported | login | quiz | comms | mock | application | placed | note
  ref_table text,
  ref_id uuid,
  summary text not null,  -- one line shown on the timeline
  at timestamptz not null default now()
);

-- Messages, AI and 360 timeline · phase 4
-- Rules the teams set up, e.g. "if a score is below 6, book doubt clearing".
create table workflows (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  trigger text not null,
  steps jsonb not null,
  is_active boolean not null default true,
  created_by uuid references users(id),
  created_at timestamptz not null default now()
);

-- Indexes on foreign keys
create index on batches (course_id);
create index on student_imports (uploaded_by);
create index on students (batch_id);
create index on students (import_id);
create index on students (fast_track_by);
create index on student_notes (student_id);
create index on student_notes (author_id);
create index on trainer_availability (trainer_id);
create index on course_modules (course_id);
create index on videos (module_id);
create index on topic_releases (batch_id);
create index on topic_releases (module_id);
create index on topic_releases (released_by);
create index on student_topic_access (student_id);
create index on student_topic_access (module_id);
create index on student_topic_access (opened_by);
create index on quiz_questions (video_id);
create index on video_progress (student_id);
create index on video_progress (video_id);
create index on quiz_attempts (student_id);
create index on quiz_attempts (video_id);
create index on comms_sessions (student_id);
create index on comms_sessions (drill_id);
create index on student_gates (student_id);
create index on skill_scores (student_id);
create index on skill_scores (skill_id);
create index on drives (company_id);
create index on drives (created_by);
create index on drive_students (drive_id);
create index on drive_students (student_id);
create index on interview_questions (company_id);
create index on interview_questions (added_by);
create index on resumes (student_id);
create index on resumes (drive_id);
create index on prep_packs (resume_id);
create index on prep_packs (approved_by);
create index on pack_questions (pack_id);
create index on pack_questions (question_id);
create index on sessions (student_id);
create index on sessions (trainer_id);
create index on sessions (drive_student_id);
create index on session_questions (session_id);
create index on session_questions (question_id);
create index on recordings (session_id);
create index on job_postings (company_id);
create index on applications (student_id);
create index on applications (job_posting_id);
create index on applications (drive_id);
create index on applications (resume_id);
create index on application_events (application_id);
create index on placements (student_id);
create index on placements (company_id);
create index on placements (application_id);
create index on placements (drive_id);
create index on interview_feedback (student_id);
create index on interview_feedback (company_id);
create index on interview_feedback (application_id);
create index on notifications (user_id);
create index on activity_log (student_id);
create index on activity_log (actor_id);
create index on workflows (created_by);

-- Double-booking is impossible: no two scheduled sessions may overlap for the same trainer or the same student
alter table sessions add constraint sessions_no_trainer_overlap
  exclude using gist (trainer_id with =, tstzrange(starts_at, ends_at) with &&)
  where (status = 'scheduled' and trainer_id is not null);
alter table sessions add constraint sessions_no_student_overlap
  exclude using gist (student_id with =, tstzrange(starts_at, ends_at) with &&)
  where (status = 'scheduled');
create index on notifications (scheduled_for) where status = 'queued';

create index on students (stage);
create index on activity_log (student_id, at desc);
