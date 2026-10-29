import { Router } from 'express';
import pool from '../db.js';
import { requireRole } from '../auth.js';

// Batches: a group of students who start together. Admin and Operations run them; a trainer sees only
// the batches they are assigned to. Courses are global, so a batch needs no course.
const router = Router();
router.use(requireRole('admin', 'operations', 'trainer'));

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const q = async (sql, params = []) => (await pool.query(sql, params)).rows;
const one = async (sql, params = []) => (await q(sql, params))[0];
const bad = (res, message, status = 400) => res.status(status).json({ success: false, message });
const asyncRoute = (fn) => (req, res) => fn(req, res).catch((err) => {
  console.error('Batches route error:', err.message);
  res.status(500).json({ success: false, message: 'Server error' });
});
const manage = requireRole('admin', 'operations');
const validId = (req, res, next) => (UUID.test(req.params.id) ? next() : bad(res, 'Batch not found', 404));
const like = (s) => `%${s.replace(/[\\%_]/g, (c) => `\\${c}`)}%`;
const isDate = (d) => typeof d === 'string' && DATE.test(d) && !Number.isNaN(Date.parse(d));

const STATUS = `CASE WHEN b.starts_on > current_date THEN 'upcoming' WHEN b.ends_on < current_date THEN 'completed' ELSE 'running' END`;

// A trainer may only open batches they teach
async function canSee(req, batchId) {
  if (req.user.role !== 'trainer') return true;
  return Boolean(await one(
    'SELECT 1 AS x FROM batch_trainers bt JOIN trainers t ON t.id = bt.trainer_id WHERE bt.batch_id = $1 AND t.user_id = $2', [batchId, req.user.id]));
}

// ----------------------------------------------------------------------------- list
router.get('/', asyncRoute(async (req, res) => {
  const mine = req.user.role === 'trainer';
  const rows = await q(
    `SELECT b.id, b.name, b.starts_on, b.ends_on, ${STATUS} AS status,
            (SELECT count(*)::int FROM students s WHERE s.batch_id = b.id) AS students,
            (SELECT count(*)::int FROM students s WHERE s.batch_id = b.id AND s.stage IN ('job_ready','placed')) AS job_ready,
            (SELECT count(*)::int FROM topic_releases tr WHERE tr.batch_id = b.id) AS topics_open,
            (SELECT count(*)::int FROM course_modules m JOIN courses c ON c.id = m.course_id WHERE c.is_published) AS topics_total,
            coalesce((SELECT json_agg(json_build_object('id', t.id, 'name', u.name) ORDER BY u.name)
                      FROM batch_trainers bt JOIN trainers t ON t.id = bt.trainer_id JOIN users u ON u.id = t.user_id WHERE bt.batch_id = b.id), '[]'::json) AS trainers
     FROM batches b
     WHERE (NOT $1 OR EXISTS (SELECT 1 FROM batch_trainers bt JOIN trainers t ON t.id = bt.trainer_id WHERE bt.batch_id = b.id AND t.user_id = $2))
     ORDER BY b.starts_on DESC NULLS LAST, b.name`, [mine, req.user.id]);
  res.json({ success: true, batches: rows });
}));

// ----------------------------------------------------------------------------- one batch
router.get('/:id', validId, asyncRoute(async (req, res) => {
  if (!(await canSee(req, req.params.id))) return bad(res, 'Batch not found', 404);
  const batch = await one(`SELECT b.id, b.name, b.starts_on, b.ends_on, ${STATUS} AS status FROM batches b WHERE b.id = $1`, [req.params.id]);
  if (!batch) return bad(res, 'Batch not found', 404);
  const [students, trainers, available, courses] = await Promise.all([
    q(`SELECT s.id, s.student_code, u.name, u.email, s.stage, s.city FROM students s JOIN users u ON u.id = s.user_id WHERE s.batch_id = $1 ORDER BY u.name`, [batch.id]),
    q(`SELECT t.id, u.name, u.email FROM batch_trainers bt JOIN trainers t ON t.id = bt.trainer_id JOIN users u ON u.id = t.user_id WHERE bt.batch_id = $1 ORDER BY u.name`, [batch.id]),
    req.user.role === 'trainer' ? [] : q(
      `SELECT t.id, u.name FROM trainers t JOIN users u ON u.id = t.user_id
       WHERE u.is_active AND NOT EXISTS (SELECT 1 FROM batch_trainers bt WHERE bt.batch_id = $1 AND bt.trainer_id = t.id) ORDER BY u.name`, [batch.id]),
    q(`SELECT c.id, c.title, count(m.id)::int AS modules, count(tr.id)::int AS released
       FROM courses c LEFT JOIN course_modules m ON m.course_id = c.id LEFT JOIN topic_releases tr ON tr.module_id = m.id AND tr.batch_id = $1
       WHERE c.is_published GROUP BY c.id ORDER BY c.title`, [batch.id]),
  ]);
  res.json({ success: true, batch, students, trainers, available_trainers: available, courses });
}));

// Students who could be added: anyone not already in this batch (those in another batch are marked)
router.get('/:id/candidates', manage, validId, asyncRoute(async (req, res) => {
  const search = String(req.query.q || '').trim();
  const rows = await q(
    `SELECT s.id, s.student_code, u.name, u.email, b.name AS current_batch
     FROM students s JOIN users u ON u.id = s.user_id LEFT JOIN batches b ON b.id = s.batch_id
     WHERE u.is_active AND s.batch_id IS DISTINCT FROM $1
       AND ($2 = '' OR u.name ILIKE $3 OR u.email ILIKE $3 OR s.student_code ILIKE $3)
     ORDER BY (s.batch_id IS NULL) DESC, u.name LIMIT 30`, [req.params.id, search, like(search)]);
  res.json({ success: true, students: rows });
}));

// ----------------------------------------------------------------------------- create / edit / delete
function fields(b, partial) {
  const out = {};
  if (!partial || b.name !== undefined) { out.name = typeof b.name === 'string' ? b.name.trim() : ''; if (!out.name) return { error: 'Give the batch a name' }; if (out.name.length > 80) return { error: 'The name is too long' }; }
  for (const k of ['starts_on', 'ends_on']) {
    if (b[k] === undefined) continue;
    if (b[k] === null || b[k] === '') out[k] = null;
    else if (!isDate(b[k])) return { error: 'Dates must look like 2026-11-03' };
    else out[k] = b[k];
  }
  return { out };
}

router.post('/', manage, asyncRoute(async (req, res) => {
  const { out, error } = fields(req.body, false);
  if (error) return bad(res, error);
  if (out.starts_on && out.ends_on && out.ends_on < out.starts_on) return bad(res, 'The end date is before the start date');
  if (await one('SELECT 1 AS x FROM batches WHERE lower(name) = lower($1)', [out.name])) return bad(res, 'A batch with that name already exists', 409);
  const row = await one('INSERT INTO batches (name, starts_on, ends_on) VALUES ($1, $2, $3) RETURNING id, name, starts_on, ends_on', [out.name, out.starts_on || null, out.ends_on || null]);
  res.status(201).json({ success: true, batch: row });
}));

router.patch('/:id', manage, validId, asyncRoute(async (req, res) => {
  const { out, error } = fields(req.body, true);
  if (error) return bad(res, error);
  const cur = await one('SELECT name, starts_on::text AS starts_on, ends_on::text AS ends_on FROM batches WHERE id = $1', [req.params.id]);
  if (!cur) return bad(res, 'Batch not found', 404);
  const next = { name: out.name ?? cur.name, starts_on: 'starts_on' in out ? out.starts_on : cur.starts_on, ends_on: 'ends_on' in out ? out.ends_on : cur.ends_on };
  if (next.starts_on && next.ends_on && next.ends_on < next.starts_on) return bad(res, 'The end date is before the start date');
  if (await one('SELECT 1 AS x FROM batches WHERE lower(name) = lower($1) AND id <> $2', [next.name, req.params.id])) return bad(res, 'A batch with that name already exists', 409);
  const row = await one('UPDATE batches SET name = $2, starts_on = $3, ends_on = $4 WHERE id = $1 RETURNING id, name, starts_on, ends_on', [req.params.id, next.name, next.starts_on || null, next.ends_on || null]);
  res.json({ success: true, batch: row });
}));

router.delete('/:id', manage, validId, asyncRoute(async (req, res) => {
  const n = (await one('SELECT count(*)::int AS n FROM students WHERE batch_id = $1', [req.params.id])).n;
  if (n > 0) return bad(res, `${n} student${n === 1 ? ' is' : 's are'} still in this batch. Move them out first.`, 409);
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query('DELETE FROM topic_releases WHERE batch_id = $1', [req.params.id]);
    await client.query('DELETE FROM batch_trainers WHERE batch_id = $1', [req.params.id]);
    const r = await client.query('DELETE FROM batches WHERE id = $1', [req.params.id]);
    await client.query('COMMIT');
    if (!r.rowCount) return bad(res, 'Batch not found', 404);
    res.json({ success: true });
  } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
}));

// ----------------------------------------------------------------------------- students in a batch
router.post('/:id/students', manage, validId, asyncRoute(async (req, res) => {
  const ids = req.body.student_ids;
  if (!Array.isArray(ids) || ids.length === 0 || ids.length > 500 || !ids.every((i) => UUID.test(i))) return bad(res, 'Pick at least one student');
  const batch = await one('SELECT name FROM batches WHERE id = $1', [req.params.id]);
  if (!batch) return bad(res, 'Batch not found', 404);
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const moved = await client.query('UPDATE students SET batch_id = $1 WHERE id = ANY($2::uuid[]) AND batch_id IS DISTINCT FROM $1 RETURNING id', [req.params.id, ids]);
    await client.query(
      "INSERT INTO activity_log (student_id, actor_id, kind, summary) SELECT unnest($1::uuid[]), $2, 'batch', $3",
      [moved.rows.map((r) => r.id), req.user.id, `Added to batch ${batch.name}`]);
    await client.query('COMMIT');
    res.json({ success: true, added: moved.rowCount });
  } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
}));

// Move students to another batch: the ones given, or everyone in this batch when no list is sent
router.post('/:id/move', manage, validId, asyncRoute(async (req, res) => {
  const { target_id: target, student_ids: ids } = req.body;
  if (!UUID.test(target || '')) return bad(res, 'Pick the batch to move them to');
  if (target === req.params.id) return bad(res, 'Pick a different batch');
  if (ids !== undefined && (!Array.isArray(ids) || ids.length === 0 || ids.length > 1000 || !ids.every((i) => UUID.test(i)))) return bad(res, 'Pick at least one student');
  const [from, to] = await Promise.all([one('SELECT name FROM batches WHERE id = $1', [req.params.id]), one('SELECT name FROM batches WHERE id = $1', [target])]);
  if (!from) return bad(res, 'Batch not found', 404);
  if (!to) return bad(res, 'The batch to move to was not found', 404);
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const moved = await client.query(
      'UPDATE students SET batch_id = $2 WHERE batch_id = $1 AND ($3::uuid[] IS NULL OR id = ANY($3::uuid[])) RETURNING id',
      [req.params.id, target, ids || null]);
    await client.query(
      "INSERT INTO activity_log (student_id, actor_id, kind, summary) SELECT unnest($1::uuid[]), $2, 'batch', $3",
      [moved.rows.map((r) => r.id), req.user.id, `Moved from batch ${from.name} to ${to.name}`]);
    await client.query('COMMIT');
    res.json({ success: true, moved: moved.rowCount });
  } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
}));

router.delete('/:id/students/:studentId', manage, validId, asyncRoute(async (req, res) => {
  if (!UUID.test(req.params.studentId)) return bad(res, 'Student not found', 404);
  const batch = await one('SELECT name FROM batches WHERE id = $1', [req.params.id]);
  const r = await pool.query('UPDATE students SET batch_id = NULL WHERE id = $1 AND batch_id = $2', [req.params.studentId, req.params.id]);
  if (!r.rowCount) return bad(res, 'That student is not in this batch', 404);
  await pool.query("INSERT INTO activity_log (student_id, actor_id, kind, summary) VALUES ($1, $2, 'batch', $3)", [req.params.studentId, req.user.id, `Removed from batch ${batch?.name || ''}`.trim()]);
  res.json({ success: true });
}));

// ----------------------------------------------------------------------------- trainers in a batch
router.post('/:id/trainers', manage, validId, asyncRoute(async (req, res) => {
  if (!UUID.test(req.body.trainer_id || '')) return bad(res, 'Pick a trainer');
  if (!(await one('SELECT 1 AS x FROM batches WHERE id = $1', [req.params.id]))) return bad(res, 'Batch not found', 404);
  if (!(await one('SELECT 1 AS x FROM trainers WHERE id = $1', [req.body.trainer_id]))) return bad(res, 'Trainer not found', 404);
  await pool.query('INSERT INTO batch_trainers (batch_id, trainer_id) VALUES ($1, $2) ON CONFLICT DO NOTHING', [req.params.id, req.body.trainer_id]);
  res.json({ success: true });
}));

router.delete('/:id/trainers/:trainerId', manage, validId, asyncRoute(async (req, res) => {
  if (!UUID.test(req.params.trainerId)) return bad(res, 'Trainer not found', 404);
  await pool.query('DELETE FROM batch_trainers WHERE batch_id = $1 AND trainer_id = $2', [req.params.id, req.params.trainerId]);
  res.json({ success: true });
}));

export default router;
