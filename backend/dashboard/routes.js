import { Router } from 'express';
import pool from '../db.js';
import { requireRole } from '../auth.js';
import { completeness } from '../students/profileRules.js';

// One endpoint, a different answer per role. Every number comes from the database.
const router = Router();
router.use(requireRole());

const q = async (sql, params = []) => (await pool.query(sql, params)).rows;
const one = async (sql, params = []) => (await q(sql, params))[0];

const BUILDERS = {
  // Admin: who has a login and how the platform is used
  async admin() {
    return {
      users_by_role: await q(`SELECT role, count(*)::int AS total, count(*) FILTER (WHERE is_active)::int AS active FROM users GROUP BY role ORDER BY role`),
      students_by_stage: await q(`SELECT stage, count(*)::int AS total FROM students GROUP BY stage ORDER BY stage`),
      drives_by_status: await q(`SELECT status, count(*)::int AS total FROM drives GROUP BY status ORDER BY status`),
      upcoming_sessions: (await one(`SELECT count(*)::int AS n FROM sessions WHERE status = 'scheduled' AND starts_at > now()`)).n,
      never_logged_in: (await one(`SELECT count(*)::int AS n FROM users WHERE is_active AND last_login_at IS NULL AND password_hash IS NOT NULL`)).n,
      recent_logins: await q(`SELECT name, role, last_login_at FROM users WHERE last_login_at IS NOT NULL ORDER BY last_login_at DESC LIMIT 5`),
    };
  },

  // Operations: running the student pipeline day to day
  async operations() {
    return {
      students_by_stage: await q(`SELECT stage, count(*)::int AS total FROM students GROUP BY stage ORDER BY stage`),
      students_total: (await one(`SELECT count(*)::int AS n FROM students`)).n,
      students_active: (await one(`SELECT count(*)::int AS n FROM students s JOIN users u ON u.id = s.user_id WHERE u.is_active`)).n,
      no_batch: (await one(`SELECT count(*)::int AS n FROM students WHERE batch_id IS NULL`)).n,
      no_skills: (await one(`SELECT count(*)::int AS n FROM students WHERE coalesce(jsonb_array_length(CASE WHEN jsonb_typeof(extra->'skills') = 'array' THEN extra->'skills' ELSE '[]'::jsonb END), 0) = 0`)).n,
      no_login: (await one(`SELECT count(*)::int AS n FROM students s JOIN users u ON u.id = s.user_id WHERE u.password_hash IS NULL`)).n,
      never_logged_in: (await one(`SELECT count(*)::int AS n FROM students s JOIN users u ON u.id = s.user_id WHERE u.is_active AND u.password_hash IS NOT NULL AND u.last_login_at IS NULL`)).n,
      upcoming_sessions: (await one(`SELECT count(*)::int AS n FROM sessions WHERE status = 'scheduled' AND starts_at > now()`)).n,
      unassigned_sessions: (await one(`SELECT count(*)::int AS n FROM sessions WHERE status = 'scheduled' AND starts_at > now() AND trainer_id IS NULL`)).n,
      drives_by_status: await q(`SELECT status, count(*)::int AS total FROM drives GROUP BY status ORDER BY status`),
      batches: await q(
        `SELECT b.id, b.name, count(s.*)::int AS students, count(s.*) FILTER (WHERE s.stage IN ('job_ready','placed'))::int AS job_ready
         FROM batches b LEFT JOIN students s ON s.batch_id = b.id GROUP BY b.id, b.name ORDER BY b.name LIMIT 8`),
      recent_students: await q(
        `SELECT s.id, s.student_code, u.name, s.stage, s.created_at FROM students s JOIN users u ON u.id = s.user_id ORDER BY s.created_at DESC LIMIT 6`),
      recent_imports: await q(
        `SELECT i.id, i.file_name, i.rows_imported, i.rows_skipped, i.created_at, u.name AS by
         FROM student_imports i JOIN users u ON u.id = i.uploaded_by ORDER BY i.created_at DESC LIMIT 3`),
    };
  },

  async placement() {
    return {
      drives_by_status: await q(`SELECT status, count(*)::int AS total FROM drives GROUP BY status ORDER BY status`),
      students_by_stage: await q(`SELECT stage, count(*)::int AS total FROM students GROUP BY stage ORDER BY stage`),
      students_total: (await one(`SELECT count(*)::int AS n FROM students`)).n,
      students_job_ready: (await one(`SELECT count(*)::int AS n FROM students WHERE stage IN ('job_ready','placed')`)).n,
      placements_total: (await one(`SELECT count(*)::int AS n FROM placements`)).n,
      recent_drives: await q(
        `SELECT d.id, c.name AS company, d.role, d.status, count(ds.*) FILTER (WHERE ds.selected)::int AS selected_count, d.created_at
         FROM drives d JOIN companies c ON c.id = d.company_id LEFT JOIN drive_students ds ON ds.drive_id = d.id
         GROUP BY d.id, c.name ORDER BY d.created_at DESC LIMIT 5`),
    };
  },

  async trainer(user) {
    const t = await one(`SELECT id, skills, weekly_capacity FROM trainers WHERE user_id = $1`, [user.id]);
    if (!t) return { profile: null, upcoming_sessions: [], upcoming_total: 0, done_sessions: 0, sessions_this_week: 0 };
    return {
      profile: { skills: t.skills, weekly_capacity: t.weekly_capacity },
      upcoming_sessions: await q(
        `SELECT s.id, s.kind, s.mock_number, s.starts_at, s.ends_at, s.meeting_url, u.name AS student
         FROM sessions s JOIN students st ON st.id = s.student_id JOIN users u ON u.id = st.user_id
         WHERE s.trainer_id = $1 AND s.status = 'scheduled' AND s.starts_at > now() ORDER BY s.starts_at LIMIT 10`, [t.id]),
      upcoming_total: (await one(`SELECT count(*)::int AS n FROM sessions WHERE trainer_id = $1 AND status = 'scheduled' AND starts_at > now()`, [t.id])).n,
      done_sessions: (await one(`SELECT count(*)::int AS n FROM sessions WHERE trainer_id = $1 AND status = 'done'`, [t.id])).n,
      sessions_this_week: (await one(
        `SELECT count(*)::int AS n FROM sessions WHERE trainer_id = $1 AND status = 'scheduled' AND starts_at >= now() AND starts_at < now() + interval '7 days'`, [t.id])).n,
    };
  },

  async student(user) {
    const s = await one(
      `SELECT st.id, st.city, st.degree, st.college, st.target_roles, st.stage, st.level, st.extra, u.phone, b.name AS batch
       FROM students st JOIN users u ON u.id = st.user_id LEFT JOIN batches b ON b.id = st.batch_id WHERE st.user_id = $1`, [user.id]);
    if (!s) return { profile: null, drives: [], upcoming_sessions: [] };
    const { extra, phone, ...shown } = s;
    return {
      profile: shown,
      completeness: completeness({ phone, city: s.city, college: s.college, degree: s.degree, target_roles: s.target_roles || [], extra: extra || {} }),
      drives: await q(
        `SELECT d.id, c.name AS company, d.role, ds.status FROM drive_students ds
         JOIN drives d ON d.id = ds.drive_id JOIN companies c ON c.id = d.company_id
         WHERE ds.student_id = $1 AND ds.selected ORDER BY d.created_at DESC`, [s.id]),
      upcoming_sessions: await q(
        `SELECT s.id, s.kind, s.mock_number, s.starts_at, s.meeting_url, u.name AS trainer
         FROM sessions s LEFT JOIN trainers t ON t.id = s.trainer_id LEFT JOIN users u ON u.id = t.user_id
         WHERE s.student_id = $1 AND s.status = 'scheduled' AND s.starts_at > now() ORDER BY s.starts_at LIMIT 10`, [s.id]),
    };
  },
};

router.get('/', async (req, res) => {
  try {
    const data = await BUILDERS[req.user.role](req.user);
    res.json({ success: true, role: req.user.role, ...data });
  } catch (err) {
    console.error('Dashboard error:', err.message);
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

export default router;
