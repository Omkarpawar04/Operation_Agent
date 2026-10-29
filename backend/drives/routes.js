import { Router } from 'express';
import pool from '../db.js';
import { requireRole } from '../auth.js';
import { parseJd } from './jdParser.js';
import { scoreStudent } from './matcher.js';

const router = Router();
router.use(requireRole('placement', 'operations'));

const asyncRoute = (fn) => (req, res) => fn(req, res).catch((err) => {
  console.error('Drive route error:', err.message);
  res.status(500).json({ success: false, message: 'Server error' });
});

// Create a drive: save company + JD, read the JD, rank every student
router.post('/', asyncRoute(async (req, res) => {
  const { company, role, location, jd_text, mocks_per_student = 3 } = req.body;
  if (!company?.trim() || !role?.trim() || !jd_text?.trim()) {
    return res.status(400).json({ success: false, message: 'company, role and jd_text are required' });
  }
  if (!Number.isInteger(mocks_per_student) || mocks_per_student < 3 || mocks_per_student > 5) {
    return res.status(400).json({ success: false, message: 'mocks_per_student must be 3 to 5' });
  }

  let requirements;
  try {
    requirements = await parseJd({ company, role, location: location?.trim(), jdText: jd_text });
  } catch (err) {
    console.error('JD parsing failed:', err.message);
    return res.status(502).json({ success: false, message: 'Could not read the JD. Check that Python is installed (PYTHON_BIN).' });
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const c = await client.query(
      `INSERT INTO companies (name, name_key) VALUES ($1, $2)
       ON CONFLICT (name_key) DO UPDATE SET name = companies.name RETURNING id`,
      [company.trim(), company.trim().toLowerCase()]);
    const d = await client.query(
      `INSERT INTO drives (company_id, role, location, jd_text, requirements, mocks_per_student, status, created_by)
       VALUES ($1,$2,$3,$4,$5,$6,'selecting',$7) RETURNING id`,
      [c.rows[0].id, role.trim(), location?.trim() || null, jd_text, requirements, mocks_per_student, req.user.id]);
    const driveId = d.rows[0].id;

    const students = (await client.query('SELECT id, target_roles, city, extra FROM students')).rows;
    for (const s of students) {
      const { score, reasons } = scoreStudent(s, requirements, role);
      await client.query(
        `INSERT INTO drive_students (drive_id, student_id, match_score, match_reasons, status) VALUES ($1,$2,$3,$4,'ranked')`,
        [driveId, s.id, score, JSON.stringify(reasons)]);
    }
    await client.query('COMMIT');
    res.status(201).json({ success: true, drive_id: driveId, requirements, ranked: students.length });
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}));

router.get('/', asyncRoute(async (_req, res) => {
  const { rows } = await pool.query(
    `SELECT d.id, c.name AS company, d.role, d.location, d.status, d.mocks_per_student, d.created_at,
            count(ds.*) FILTER (WHERE ds.selected)::int AS selected_count
     FROM drives d JOIN companies c ON c.id = d.company_id
     LEFT JOIN drive_students ds ON ds.drive_id = d.id
     GROUP BY d.id, c.name ORDER BY d.created_at DESC`);
  res.json({ success: true, drives: rows });
}));

// One drive with its ranked students, best match first
router.get('/:id', asyncRoute(async (req, res) => {
  const d = await pool.query(
    `SELECT d.*, c.name AS company FROM drives d JOIN companies c ON c.id = d.company_id WHERE d.id = $1`, [req.params.id]);
  if (!d.rows.length) return res.status(404).json({ success: false, message: 'Drive not found' });
  const s = await pool.query(
    `SELECT ds.student_id, u.name, u.email, st.city, st.target_roles, ds.match_score, ds.match_reasons, ds.selected, ds.status
     FROM drive_students ds JOIN students st ON st.id = ds.student_id JOIN users u ON u.id = st.user_id
     WHERE ds.drive_id = $1 ORDER BY ds.match_score DESC NULLS LAST, u.name`, [req.params.id]);
  res.json({ success: true, drive: d.rows[0], students: s.rows });
}));

// Placement ticks the students to put forward (replaces the previous selection)
router.post('/:id/select', asyncRoute(async (req, res) => {
  const ids = req.body.student_ids;
  if (!Array.isArray(ids)) return res.status(400).json({ success: false, message: 'student_ids must be a list' });
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query('UPDATE drive_students SET selected = false WHERE drive_id = $1', [req.params.id]);
    const r = await client.query(
      'UPDATE drive_students SET selected = true WHERE drive_id = $1 AND student_id = ANY($2::uuid[])', [req.params.id, ids]);
    if (r.rowCount !== new Set(ids).size) throw Object.assign(new Error('unknown student'), { status: 400 });
    await client.query('UPDATE drives SET status = $2 WHERE id = $1', [req.params.id, ids.length ? 'prepping' : 'selecting']);
    await client.query('COMMIT');
    res.json({ success: true, selected: r.rowCount });
  } catch (err) {
    await client.query('ROLLBACK');
    if (err.status === 400 || err.code === '22P02') {
      return res.status(400).json({ success: false, message: 'Some students are not part of this drive' });
    }
    throw err;
  } finally {
    client.release();
  }
}));

export default router;
