import { Router } from 'express';
import pool from '../db.js';
import { Readable } from 'stream';
import { requireRole, issueStreamToken, verifyStreamToken } from '../auth.js';
import { providerOf, assertPublicHost } from './media.js';

// Learning modules.
//  - Admin builds courses, modules and videos (courses are global: no assigning to batches).
//  - Every batch automatically sees every published course.
//  - A module's videos stay locked for a batch until that batch's trainer marks the topic complete.
const router = Router();

// Streams a video file through the backend. Some file hosts forbid other websites from playing their files
// (Cross-Origin-Resource-Policy: same-origin), and the browser then refuses to play them. The server is not bound by that rule.
// The address carries a 2-hour token for this one video instead of the login token.
router.get('/videos/:id/stream', async (req, res) => {
  const t = verifyStreamToken(String(req.query.token || ''));
  if (!t || t.v !== req.params.id) return res.status(403).end();
  try {
    const { rows } = await pool.query('SELECT video_url FROM videos WHERE id = $1', [req.params.id]);
    if (!rows.length) return res.status(404).end();
    const url = new URL(rows[0].video_url);
    await assertPublicHost(url.hostname);
    const ctl = new AbortController();
    res.on('close', () => ctl.abort());
    const up = await fetch(url, { headers: req.headers.range ? { Range: req.headers.range } : {}, redirect: 'manual', signal: ctl.signal });
    if (up.status >= 300 && up.status < 400) return res.status(502).end();
    res.status(up.status);
    for (const h of ['content-type', 'content-length', 'content-range', 'accept-ranges', 'last-modified', 'etag']) {
      const v = up.headers.get(h);
      if (v) res.setHeader(h, v);
    }
    res.setHeader('Cache-Control', 'private, max-age=0');
    if (!up.body) return res.end();
    Readable.fromWeb(up.body).on('error', () => res.destroy()).pipe(res);
  } catch (err) {
    if (!res.headersSent) res.status(502).end(); else res.destroy();
  }
});

router.use(requireRole()); // any logged-in user; each route narrows further

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const q = async (sql, params = []) => (await pool.query(sql, params)).rows;
const one = async (sql, params = []) => (await q(sql, params))[0];
const bad = (res, message, status = 400) => res.status(status).json({ success: false, message });
const asyncRoute = (fn) => (req, res) => fn(req, res).catch((err) => {
  console.error('Learning route error:', err.message);
  res.status(500).json({ success: false, message: 'Server error' });
});
const adminOnly = requireRole('admin');
const validId = (req, res, next) => (UUID.test(req.params.id || req.params.batchId || '') ? next() : bad(res, 'Not found', 404));

const clean = (s) => (typeof s === 'string' ? s.trim() : '');
const pct = (v, fallback) => (Number.isInteger(v) && v >= 1 && v <= 100 ? v : fallback);
const isHttp = (u) => { try { return ['http:', 'https:'].includes(new URL(u).protocol); } catch { return false; } };

// The student's batch (null if none) and student id
const studentOf = (userId) => one('SELECT id, batch_id FROM students WHERE user_id = $1', [userId]);

// ----------------------------------------------------------------------------- read
router.get('/courses', asyncRoute(async (req, res) => {
  const role = req.user.role;
  const published = role === 'admin' || role === 'operations' ? '' : 'WHERE c.is_published';
  const courses = await q(
    `SELECT c.id, c.title, c.description, c.is_published,
            (SELECT count(*)::int FROM course_modules m WHERE m.course_id = c.id) AS modules,
            (SELECT count(*)::int FROM videos v JOIN course_modules m ON m.id = v.module_id WHERE m.course_id = c.id) AS videos,
            (SELECT coalesce(sum(v.duration_sec), 0)::int FROM videos v JOIN course_modules m ON m.id = v.module_id WHERE m.course_id = c.id) AS total_sec
     FROM courses c ${published} ORDER BY c.title`);
  if (role !== 'student') return res.json({ success: true, courses });

  // For a student, add how much is open to them and how much they have watched
  const st = await studentOf(req.user.id);
  const stats = st ? await q(
    `SELECT m.course_id,
            count(v.*) FILTER (WHERE tr.id IS NOT NULL OR sa.id IS NOT NULL)::int AS open_videos,
            count(v.*) FILTER (WHERE vp.passed_at IS NOT NULL)::int AS done_videos
     FROM course_modules m JOIN videos v ON v.module_id = m.id
     LEFT JOIN topic_releases tr ON tr.module_id = m.id AND tr.batch_id = $2
     LEFT JOIN student_topic_access sa ON sa.module_id = m.id AND sa.student_id = $1
     LEFT JOIN video_progress vp ON vp.video_id = v.id AND vp.student_id = $1
     GROUP BY m.course_id`, [st.id, st.batch_id]) : [];
  const by = Object.fromEntries(stats.map((s) => [s.course_id, s]));
  res.json({ success: true, has_batch: Boolean(st?.batch_id), courses: courses.map((c) => ({ ...c, open_videos: by[c.id]?.open_videos || 0, done_videos: by[c.id]?.done_videos || 0 })) });
}));

// One course with its modules and videos. What is included depends on who asks:
//  admin / operations: everything (operations read-only). trainer: titles + release state for ?batch=.
//  student: video links only for modules released to their batch.
router.get('/courses/:id', validId, asyncRoute(async (req, res) => {
  const role = req.user.role;
  const course = await one('SELECT id, title, description, is_published, pass_mark_pct, watch_to_unlock_pct, trainer_release FROM courses WHERE id = $1', [req.params.id]);
  if (!course || (!course.is_published && role !== 'admin' && role !== 'operations')) return bad(res, 'Course not found', 404);

  const modules = await q('SELECT id, title, position FROM course_modules WHERE course_id = $1 ORDER BY position, title', [course.id]);
  const videos = await q(
    `SELECT v.id, v.module_id, v.title, v.position, v.duration_sec, v.video_url, v.key_points
     FROM videos v JOIN course_modules m ON m.id = v.module_id WHERE m.course_id = $1 ORDER BY v.position, v.title`, [course.id]);

  let released = new Set();   // module ids open to the viewer
  let releasedAt = {};        // module id -> date, for trainers
  const prog = new Map();     // the student's own progress per video
  if (role === 'student') {
    const st = await studentOf(req.user.id);
    if (st) {
      const rows = await q(
        `SELECT module_id FROM topic_releases WHERE batch_id = $2
         UNION SELECT module_id FROM student_topic_access WHERE student_id = $1`, [st.id, st.batch_id]);
      released = new Set(rows.map((r) => r.module_id));
      for (const r of await q('SELECT video_id, watched_pct, quiz_unlocked_at, passed_at FROM video_progress WHERE student_id = $1', [st.id])) prog.set(r.video_id, r);
    }
  } else if (role === 'trainer' || role === 'admin' || role === 'operations') {
    const batchId = UUID.test(req.query.batch || '') ? req.query.batch : null;
    if (batchId) {
      const rows = await q('SELECT module_id, released_at FROM topic_releases WHERE batch_id = $1', [batchId]);
      released = new Set(rows.map((r) => r.module_id));
      releasedAt = Object.fromEntries(rows.map((r) => [r.module_id, r.released_at]));
    }
  }
  const questions = Object.fromEntries((await q('SELECT video_id, count(*)::int AS n FROM quiz_questions WHERE video_id = ANY($1::uuid[]) GROUP BY video_id', [videos.map((v) => v.id)])).map((r) => [r.video_id, r.n]));
  const staff = role === 'admin' || role === 'operations';

  res.json({
    success: true,
    course,
    modules: modules.map((m) => {
      let earlierDone = true; // a lesson opens only after every earlier lesson in its topic is passed
      return {
        ...m,
        released: released.has(m.id),
        released_at: releasedAt[m.id] || null,
        videos: videos.filter((v) => v.module_id === m.id).map((v) => {
          const p = prog.get(v.id);
          const done = Boolean(p?.passed_at);
          const playable = role === 'student' && released.has(m.id) && earlierDone;
          earlierDone = earlierDone && done;
          const out = { id: v.id, title: v.title, position: v.position, duration_sec: v.duration_sec, done, provider: providerOf(v.video_url), questions: questions[v.id] || 0 };
          if (role === 'student') Object.assign(out, { watched_pct: p?.watched_pct || 0, quiz_unlocked: Boolean(p?.quiz_unlocked_at), playable });
          if (staff || playable) Object.assign(out, { video_url: v.video_url, key_points: v.key_points });
          return out;
        }),
      };
    }),
  });
}));

// ----------------------------------------------------------------------------- admin: courses
router.post('/courses', adminOnly, asyncRoute(async (req, res) => {
  const title = clean(req.body.title);
  if (!title) return bad(res, 'Give the course a title');
  const row = await one(
    `INSERT INTO courses (title, description) VALUES ($1, $2) RETURNING id, title, description, is_published`,
    [title, clean(req.body.description) || null]);
  res.status(201).json({ success: true, course: row });
}));

router.patch('/courses/:id', adminOnly, validId, asyncRoute(async (req, res) => {
  const b = req.body;
  if (b.title !== undefined && !clean(b.title)) return bad(res, 'Title cannot be empty');
  const row = await one(
    `UPDATE courses SET title = COALESCE($2, title), description = COALESCE($3, description),
            is_published = COALESCE($4, is_published), pass_mark_pct = COALESCE($5, pass_mark_pct),
            watch_to_unlock_pct = COALESCE($6, watch_to_unlock_pct)
     WHERE id = $1 RETURNING id, title, description, is_published, pass_mark_pct, watch_to_unlock_pct`,
    [req.params.id, b.title === undefined ? null : clean(b.title), b.description === undefined ? null : clean(b.description),
      typeof b.is_published === 'boolean' ? b.is_published : null,
      b.pass_mark_pct === undefined ? null : pct(b.pass_mark_pct, null), b.watch_to_unlock_pct === undefined ? null : pct(b.watch_to_unlock_pct, null)]);
  if (!row) return bad(res, 'Course not found', 404);
  res.json({ success: true, course: row });
}));

// Delete a course and everything under it, unless a student has already watched or attempted something
async function deleteVideos(client, where, params) {
  await client.query(`DELETE FROM quiz_questions WHERE video_id IN (SELECT v.id FROM videos v ${where})`, params);
  await client.query(`DELETE FROM videos WHERE id IN (SELECT v.id FROM videos v ${where})`, params);
}
async function inUse(where, params) {
  return (await one(
    `SELECT (SELECT count(*) FROM video_progress WHERE video_id IN (SELECT v.id FROM videos v ${where}))
          + (SELECT count(*) FROM quiz_attempts WHERE video_id IN (SELECT v.id FROM videos v ${where})) AS n`, params)).n > 0;
}
const IN_COURSE = 'JOIN course_modules m ON m.id = v.module_id WHERE m.course_id = $1';
const IN_MODULE = 'WHERE v.module_id = $1';

router.delete('/courses/:id', adminOnly, validId, asyncRoute(async (req, res) => {
  if (await inUse(IN_COURSE, [req.params.id])) return bad(res, 'Students have already watched videos in this course. Unpublish it instead of deleting.', 409);
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await deleteVideos(client, IN_COURSE, [req.params.id]);
    await client.query('DELETE FROM topic_releases WHERE module_id IN (SELECT id FROM course_modules WHERE course_id = $1)', [req.params.id]);
    await client.query('DELETE FROM student_topic_access WHERE module_id IN (SELECT id FROM course_modules WHERE course_id = $1)', [req.params.id]);
    await client.query('DELETE FROM course_modules WHERE course_id = $1', [req.params.id]);
    await client.query('UPDATE batches SET course_id = NULL WHERE course_id = $1', [req.params.id]);
    const r = await client.query('DELETE FROM courses WHERE id = $1', [req.params.id]);
    await client.query('COMMIT');
    if (!r.rowCount) return bad(res, 'Course not found', 404);
    res.json({ success: true });
  } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
}));

// ----------------------------------------------------------------------------- admin: modules
router.post('/courses/:id/modules', adminOnly, validId, asyncRoute(async (req, res) => {
  const title = clean(req.body.title);
  if (!title) return bad(res, 'Give the module a title');
  if (!(await one('SELECT 1 AS x FROM courses WHERE id = $1', [req.params.id]))) return bad(res, 'Course not found', 404);
  const row = await one(
    `INSERT INTO course_modules (course_id, title, position)
     VALUES ($1, $2, (SELECT coalesce(max(position), 0) + 1 FROM course_modules WHERE course_id = $1)) RETURNING id, title, position`,
    [req.params.id, title]);
  res.status(201).json({ success: true, module: row });
}));

router.patch('/modules/:id', adminOnly, validId, asyncRoute(async (req, res) => {
  const title = clean(req.body.title);
  if (!title) return bad(res, 'Title cannot be empty');
  const row = await one('UPDATE course_modules SET title = $2 WHERE id = $1 RETURNING id, title, position', [req.params.id, title]);
  if (!row) return bad(res, 'Module not found', 404);
  res.json({ success: true, module: row });
}));

router.delete('/modules/:id', adminOnly, validId, asyncRoute(async (req, res) => {
  if (await inUse(IN_MODULE, [req.params.id])) return bad(res, 'Students have already watched videos in this module, so it cannot be deleted.', 409);
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await deleteVideos(client, IN_MODULE, [req.params.id]);
    await client.query('DELETE FROM topic_releases WHERE module_id = $1', [req.params.id]);
    await client.query('DELETE FROM student_topic_access WHERE module_id = $1', [req.params.id]);
    const r = await client.query('DELETE FROM course_modules WHERE id = $1', [req.params.id]);
    await client.query('COMMIT');
    if (!r.rowCount) return bad(res, 'Module not found', 404);
    res.json({ success: true });
  } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
}));

// Put the ids in the order given. Rejects ids that do not belong to the parent.
async function reorder(res, table, parentCol, parentId, ids) {
  if (!Array.isArray(ids) || !ids.every((i) => UUID.test(i))) return bad(res, 'ids must be a list of ids');
  const have = (await q(`SELECT id FROM ${table} WHERE ${parentCol} = $1`, [parentId])).map((r) => r.id);
  if (have.length !== ids.length || !ids.every((i) => have.includes(i))) return bad(res, 'The list must contain every item exactly once');
  await Promise.all(ids.map((id, i) => pool.query(`UPDATE ${table} SET position = $2 WHERE id = $1`, [id, i + 1])));
  res.json({ success: true });
}
router.post('/courses/:id/modules/reorder', adminOnly, validId, asyncRoute((req, res) => reorder(res, 'course_modules', 'course_id', req.params.id, req.body.ids)));
router.post('/modules/:id/videos/reorder', adminOnly, validId, asyncRoute((req, res) => reorder(res, 'videos', 'module_id', req.params.id, req.body.ids)));

// ----------------------------------------------------------------------------- admin: videos
function videoFields(b, partial) {
  const out = {};
  if (!partial || b.title !== undefined) { out.title = clean(b.title); if (!out.title) return { error: 'Give the video a title' }; }
  if (!partial || b.video_url !== undefined) {
    out.video_url = clean(b.video_url);
    if (!isHttp(out.video_url)) return { error: 'Paste a full video link starting with https://' };
  }
  if (b.duration_min !== undefined) {
    if (b.duration_min === null || b.duration_min === '') out.duration_sec = null;
    else if (!(Number(b.duration_min) > 0 && Number(b.duration_min) < 1000)) return { error: 'Length must be a number of minutes' };
    else out.duration_sec = Math.round(Number(b.duration_min) * 60);
  }
  if (b.key_points !== undefined) out.key_points = (Array.isArray(b.key_points) ? b.key_points : []).map(clean).filter(Boolean).slice(0, 20);
  return { out };
}

router.post('/modules/:id/videos', adminOnly, validId, asyncRoute(async (req, res) => {
  const { out, error } = videoFields(req.body, false);
  if (error) return bad(res, error);
  if (!(await one('SELECT 1 AS x FROM course_modules WHERE id = $1', [req.params.id]))) return bad(res, 'Module not found', 404);
  const row = await one(
    `INSERT INTO videos (module_id, title, position, duration_sec, video_url, key_points)
     VALUES ($1, $2, (SELECT coalesce(max(position), 0) + 1 FROM videos WHERE module_id = $1), $3, $4, $5)
     RETURNING id, title, position, duration_sec, video_url, key_points`,
    [req.params.id, out.title, out.duration_sec ?? null, out.video_url, out.key_points || []]);
  res.status(201).json({ success: true, video: row });
}));

router.patch('/videos/:id', adminOnly, validId, asyncRoute(async (req, res) => {
  const { out, error } = videoFields(req.body, true);
  if (error) return bad(res, error);
  const cur = await one('SELECT * FROM videos WHERE id = $1', [req.params.id]);
  if (!cur) return bad(res, 'Video not found', 404);
  const row = await one(
    `UPDATE videos SET title = $2, video_url = $3, duration_sec = $4, key_points = $5 WHERE id = $1
     RETURNING id, title, position, duration_sec, video_url, key_points`,
    [req.params.id, out.title ?? cur.title, out.video_url ?? cur.video_url, 'duration_sec' in out ? out.duration_sec : cur.duration_sec, out.key_points ?? cur.key_points]);
  res.json({ success: true, video: row });
}));

router.delete('/videos/:id', adminOnly, validId, asyncRoute(async (req, res) => {
  if (await inUse('WHERE v.id = $1', [req.params.id])) return bad(res, 'Students have already watched this video, so it cannot be deleted.', 409);
  await pool.query('DELETE FROM quiz_questions WHERE video_id = $1', [req.params.id]);
  const r = await pool.query('DELETE FROM videos WHERE id = $1', [req.params.id]);
  if (!r.rowCount) return bad(res, 'Video not found', 404);
  res.json({ success: true });
}));

// ----------------------------------------------------------------------------- trainer: batches and release
router.get('/batches', requireRole('trainer', 'operations'), asyncRoute(async (req, res) => {
  const mine = req.user.role === 'trainer';
  res.json({
    success: true,
    batches: await q(
      `SELECT b.id, b.name, b.starts_on, count(s.*)::int AS students,
              (SELECT count(*)::int FROM topic_releases t WHERE t.batch_id = b.id) AS released_modules
       FROM batches b LEFT JOIN students s ON s.batch_id = b.id
       WHERE (NOT $1 OR EXISTS (SELECT 1 FROM batch_trainers bt JOIN trainers t ON t.id = bt.trainer_id WHERE bt.batch_id = b.id AND t.user_id = $2))
       GROUP BY b.id ORDER BY b.starts_on DESC NULLS LAST, b.name`, [mine, req.user.id]),
  });
}));

// Mark a topic complete for a batch (released = true) or take it back (false)
router.put('/batches/:batchId/modules/:moduleId', requireRole('trainer'), asyncRoute(async (req, res) => {
  const { batchId, moduleId } = req.params;
  if (!UUID.test(batchId) || !UUID.test(moduleId)) return bad(res, 'Not found', 404);
  if (typeof req.body.released !== 'boolean') return bad(res, 'released must be true or false');
  const trainer = await one('SELECT id FROM trainers WHERE user_id = $1', [req.user.id]);
  if (!trainer) return bad(res, 'Your trainer profile is not set up yet. Ask the admin.', 403);
  if (!(await one('SELECT 1 AS x FROM batches WHERE id = $1', [batchId]))) return bad(res, 'Batch not found', 404);
  if (!(await one('SELECT 1 AS x FROM batch_trainers WHERE batch_id = $1 AND trainer_id = $2', [batchId, trainer.id]))) return bad(res, 'You are not assigned to this batch', 403);
  if (!(await one('SELECT 1 AS x FROM course_modules m JOIN courses c ON c.id = m.course_id WHERE m.id = $1 AND c.is_published', [moduleId]))) return bad(res, 'Module not found', 404);
  if (req.body.released) {
    await pool.query(
      `INSERT INTO topic_releases (batch_id, module_id, released_by) VALUES ($1, $2, $3) ON CONFLICT (batch_id, module_id) DO NOTHING`,
      [batchId, moduleId, trainer.id]);
  } else {
    await pool.query('DELETE FROM topic_releases WHERE batch_id = $1 AND module_id = $2', [batchId, moduleId]);
  }
  console.log(`[audit] ${new Date().toISOString()} trainer ${req.user.id} ${req.body.released ? 'released' : 'locked'} module ${moduleId} for batch ${batchId}`);
  res.json({ success: true, released: req.body.released });
}));

// ----------------------------------------------------------------------------- student: watching and quizzes
// A lesson is open to a student when its topic is released to their batch and every earlier lesson in the topic is passed.
async function videoAccess(userId, videoId) {
  const st = await studentOf(userId);
  if (!st) return { error: 'Your student profile is not set up yet', status: 404 };
  const v = await one(
    `SELECT v.id, v.title, v.position, v.duration_sec, v.video_url, v.key_points, v.module_id, c.watch_to_unlock_pct, c.pass_mark_pct
     FROM videos v JOIN course_modules m ON m.id = v.module_id JOIN courses c ON c.id = m.course_id
     WHERE v.id = $1 AND c.is_published`, [videoId]);
  if (!v) return { error: 'Video not found', status: 404 };
  const open = await one(
    `SELECT 1 AS x WHERE EXISTS (SELECT 1 FROM topic_releases t WHERE t.module_id = $1 AND t.batch_id = $3)
                      OR EXISTS (SELECT 1 FROM student_topic_access a WHERE a.module_id = $1 AND a.student_id = $2)`,
    [v.module_id, st.id, st.batch_id]);
  if (!open) return { error: 'This topic is not open for your batch yet', status: 403 };
  const blocked = await one(
    `SELECT 1 AS x FROM videos p WHERE p.module_id = $1 AND p.position < $2
       AND NOT EXISTS (SELECT 1 FROM video_progress vp WHERE vp.video_id = p.id AND vp.student_id = $3 AND vp.passed_at IS NOT NULL) LIMIT 1`,
    [v.module_id, v.position, st.id]);
  if (blocked) return { error: 'Pass the earlier lessons in this topic first', status: 403 };
  return { st, v };
}

const MAX_SEC = 6 * 60 * 60;      // no lesson is longer than 6 hours
const questionCount = async (videoId) => (await one('SELECT count(*)::int AS n FROM quiz_questions WHERE video_id = $1', [videoId])).n;

// Opening a lesson: where to resume and the link to play
router.get('/videos/:id/play', requireRole('student'), validId, asyncRoute(async (req, res) => {
  const a = await videoAccess(req.user.id, req.params.id);
  if (a.error) return bad(res, a.error, a.status);
  const p = await one('SELECT watched_pct, last_position_sec, duration_sec, quiz_unlocked_at, passed_at FROM video_progress WHERE student_id = $1 AND video_id = $2', [a.st.id, a.v.id]);
  res.json({
    success: true,
    video_url: a.v.video_url, provider: providerOf(a.v.video_url), key_points: a.v.key_points,
    duration_sec: a.v.duration_sec || p?.duration_sec || null,
    position: p?.last_position_sec || 0, watched_pct: p?.watched_pct || 0,
    unlock_pct: a.v.watch_to_unlock_pct, pass_mark_pct: a.v.pass_mark_pct,
    quiz_unlocked: Boolean(p?.quiz_unlocked_at), passed: Boolean(p?.passed_at), questions: await questionCount(a.v.id),
    stream_token: issueStreamToken(req.user.id, a.v.id),
  });
}));

// The player reports which seconds were really played. Skipping ahead does not count, and seconds cannot be
// claimed faster than the clock allows. Reaching the course's "watch %" opens the quiz (or passes a lesson with no quiz).
router.post('/videos/:id/progress', requireRole('student'), validId, asyncRoute(async (req, res) => {
  const a = await videoAccess(req.user.id, req.params.id);
  if (a.error) return bad(res, a.error, a.status);
  const { ranges, position, duration } = req.body;
  if (!Array.isArray(ranges) || ranges.length > 60) return bad(res, 'Bad progress data');
  for (const r of ranges) {
    if (!Array.isArray(r) || r.length !== 2 || !r.every(Number.isInteger) || r[0] < 0 || r[1] < r[0] || r[1] > MAX_SEC || r[1] - r[0] > 600) return bad(res, 'Bad progress data');
  }

  // The length to measure against: the player's own number, unless it disagrees a lot with what the admin entered
  const reported = Number(duration);
  const given = a.v.duration_sec;
  const okReported = Number.isFinite(reported) && reported >= 5 && reported <= MAX_SEC;
  let length;
  if (given && okReported && Math.abs(reported - given) / given <= 0.25) length = reported;
  else if (given) length = given;
  else if (okReported) length = reported;
  else return bad(res, 'The video length is not known yet');
  length = Math.ceil(length);

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query('INSERT INTO video_progress (student_id, video_id, started_at) VALUES ($1, $2, now()) ON CONFLICT DO NOTHING', [a.st.id, a.v.id]);
    const row = (await client.query(
      `SELECT watched_seconds::text AS bits, last_beat_at, extract(epoch FROM (now() - last_beat_at)) AS gap
       FROM video_progress WHERE student_id = $1 AND video_id = $2 FOR UPDATE`, [a.st.id, a.v.id])).rows[0];

    const bits = (row.bits || '').padEnd(length, '0').slice(0, length).split('');
    const claimed = new Set();
    for (const [from, to] of ranges) for (let s = from; s <= to && s < length; s += 1) if (bits[s] === '0') claimed.add(s);
    const allowed = row.last_beat_at ? Math.ceil(Math.min(60, Math.max(0, Number(row.gap))) * 2.2) + 6 : 20;
    for (const s of [...claimed].sort((x, y) => x - y).slice(0, allowed)) bits[s] = '1';
    const watchedPct = Math.min(100, Math.round((bits.filter((b) => b === '1').length / length) * 100));

    const hasQuiz = (await client.query('SELECT count(*)::int AS n FROM quiz_questions WHERE video_id = $1', [a.v.id])).rows[0].n > 0;
    const unlocked = watchedPct >= a.v.watch_to_unlock_pct;
    const upd = (await client.query(
      `UPDATE video_progress SET watched_seconds = $3::bit varying, watched_pct = $4, last_position_sec = $5, duration_sec = $6, last_beat_at = now(),
              quiz_unlocked_at = COALESCE(quiz_unlocked_at, CASE WHEN $7::boolean THEN now() END),
              passed_at = COALESCE(passed_at, CASE WHEN $8::boolean THEN now() END)
       WHERE student_id = $1 AND video_id = $2 RETURNING quiz_unlocked_at, passed_at`,
      [a.st.id, a.v.id, bits.join(''), watchedPct, Number.isInteger(position) ? Math.min(Math.max(position, 0), length) : 0, length, unlocked, unlocked && !hasQuiz])).rows[0];
    await client.query('COMMIT');
    res.json({ success: true, watched_pct: watchedPct, unlock_pct: a.v.watch_to_unlock_pct, quiz_unlocked: Boolean(upd.quiz_unlocked_at), passed: Boolean(upd.passed_at), questions: hasQuiz ? await questionCount(a.v.id) : 0 });
  } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
}));

// A link the page cannot follow (not YouTube, Vimeo or a video file): the student confirms it by hand
router.post('/videos/:id/watched', requireRole('student'), validId, asyncRoute(async (req, res) => {
  const a = await videoAccess(req.user.id, req.params.id);
  if (a.error) return bad(res, a.error, a.status);
  if (providerOf(a.v.video_url) !== 'other') return bad(res, 'This video is tracked automatically. Just watch it.', 409);
  const hasQuiz = (await questionCount(a.v.id)) > 0;
  await pool.query(
    `INSERT INTO video_progress (student_id, video_id, watched_pct, started_at, quiz_unlocked_at, passed_at) VALUES ($1, $2, 100, now(), now(), CASE WHEN $3::boolean THEN NULL ELSE now() END)
     ON CONFLICT (student_id, video_id) DO UPDATE SET watched_pct = 100, quiz_unlocked_at = coalesce(video_progress.quiz_unlocked_at, now()),
       passed_at = coalesce(video_progress.passed_at, CASE WHEN $3::boolean THEN NULL ELSE now() END)`,
    [a.st.id, a.v.id, hasQuiz]);
  res.json({ success: true, quiz_unlocked: true, passed: !hasQuiz, questions: hasQuiz ? await questionCount(a.v.id) : 0 });
}));

// The quiz, without the answers. Only once enough of the video has been watched.
router.get('/videos/:id/quiz', requireRole('student'), validId, asyncRoute(async (req, res) => {
  const a = await videoAccess(req.user.id, req.params.id);
  if (a.error) return bad(res, a.error, a.status);
  const p = await one('SELECT quiz_unlocked_at, passed_at, watched_pct FROM video_progress WHERE student_id = $1 AND video_id = $2', [a.st.id, a.v.id]);
  if (!p?.quiz_unlocked_at) return bad(res, `Watch at least ${a.v.watch_to_unlock_pct}% of the video to open the quiz`, 403);
  const questions = await q('SELECT id, question, options FROM quiz_questions WHERE video_id = $1 ORDER BY position, id', [a.v.id]);
  const best = await one('SELECT max(score_pct)::int AS best, count(*)::int AS attempts FROM quiz_attempts WHERE student_id = $1 AND video_id = $2', [a.st.id, a.v.id]);
  res.json({ success: true, questions, pass_mark_pct: a.v.pass_mark_pct, passed: Boolean(p.passed_at), best_score: best.best, attempts: best.attempts });
}));

// Mark an attempt. The right answers are only shown once the student has passed.
router.post('/videos/:id/quiz', requireRole('student'), validId, asyncRoute(async (req, res) => {
  const a = await videoAccess(req.user.id, req.params.id);
  if (a.error) return bad(res, a.error, a.status);
  const p = await one('SELECT quiz_unlocked_at FROM video_progress WHERE student_id = $1 AND video_id = $2', [a.st.id, a.v.id]);
  if (!p?.quiz_unlocked_at) return bad(res, `Watch at least ${a.v.watch_to_unlock_pct}% of the video to open the quiz`, 403);
  const questions = await q('SELECT id, options, answer_index FROM quiz_questions WHERE video_id = $1 ORDER BY position, id', [a.v.id]);
  const answers = req.body.answers;
  if (!questions.length) return bad(res, 'This lesson has no quiz', 404);
  if (!Array.isArray(answers) || answers.length !== questions.length || !answers.every((x, i) => Number.isInteger(x) && x >= 0 && x < questions[i].options.length)) return bad(res, 'Answer every question');
  const results = questions.map((qu, i) => ({ correct: answers[i] === qu.answer_index }));
  const score = Math.round((results.filter((r) => r.correct).length / questions.length) * 100);
  const passed = score >= a.v.pass_mark_pct;
  await pool.query('INSERT INTO quiz_attempts (student_id, video_id, answers, score_pct, passed) VALUES ($1, $2, $3, $4, $5)', [a.st.id, a.v.id, answers, score, passed]);
  if (passed) await pool.query('UPDATE video_progress SET passed_at = coalesce(passed_at, now()) WHERE student_id = $1 AND video_id = $2', [a.st.id, a.v.id]);
  res.json({ success: true, score_pct: score, passed, pass_mark_pct: a.v.pass_mark_pct, results, ...(passed ? { correct_answers: questions.map((qu) => qu.answer_index) } : {}) });
}));

// ----------------------------------------------------------------------------- admin: quiz questions
function questionFields(b) {
  const question = clean(b.question);
  if (!question || question.length > 500) return { error: 'Write the question (up to 500 characters)' };
  if (!Array.isArray(b.options) || b.options.length < 2 || b.options.length > 6) return { error: 'Give between 2 and 6 answer choices' };
  const options = b.options.map(clean);
  if (options.some((o) => !o || o.length > 200)) return { error: 'Every answer choice needs text (up to 200 characters)' };
  if (!Number.isInteger(b.answer_index) || b.answer_index < 0 || b.answer_index >= options.length) return { error: 'Mark which choice is correct' };
  return { out: { question, options, answer_index: b.answer_index } };
}

router.get('/videos/:id/questions', requireRole('admin', 'operations'), validId, asyncRoute(async (req, res) => {
  res.json({ success: true, questions: await q('SELECT id, question, options, answer_index, position FROM quiz_questions WHERE video_id = $1 ORDER BY position, id', [req.params.id]) });
}));

router.post('/videos/:id/questions', adminOnly, validId, asyncRoute(async (req, res) => {
  const { out, error } = questionFields(req.body);
  if (error) return bad(res, error);
  if (!(await one('SELECT 1 AS x FROM videos WHERE id = $1', [req.params.id]))) return bad(res, 'Video not found', 404);
  const row = await one(
    `INSERT INTO quiz_questions (video_id, question, options, answer_index, position)
     VALUES ($1, $2, $3, $4, (SELECT coalesce(max(position), 0) + 1 FROM quiz_questions WHERE video_id = $1)) RETURNING id, question, options, answer_index, position`,
    [req.params.id, out.question, out.options, out.answer_index]);
  res.status(201).json({ success: true, question: row });
}));

router.patch('/questions/:id', adminOnly, validId, asyncRoute(async (req, res) => {
  const { out, error } = questionFields(req.body);
  if (error) return bad(res, error);
  const row = await one('UPDATE quiz_questions SET question = $2, options = $3, answer_index = $4 WHERE id = $1 RETURNING id, question, options, answer_index, position', [req.params.id, out.question, out.options, out.answer_index]);
  if (!row) return bad(res, 'Question not found', 404);
  res.json({ success: true, question: row });
}));

router.delete('/questions/:id', adminOnly, validId, asyncRoute(async (req, res) => {
  const r = await pool.query('DELETE FROM quiz_questions WHERE id = $1', [req.params.id]);
  if (!r.rowCount) return bad(res, 'Question not found', 404);
  res.json({ success: true });
}));

export default router;
