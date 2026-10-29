import { Router } from 'express';
import pool from '../db.js';
import { requireRole } from '../auth.js';
import { canStoreViewable, decryptPassword, encryptPassword, hashPassword } from '../passwords.js';

// Master section: only the admin manages logins.
const router = Router();
router.use(requireRole('admin'));

const ROLES = ['admin', 'operations', 'placement', 'trainer', 'student'];
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD = 6;

const asyncRoute = (fn) => (req, res) => fn(req, res).catch((err) => {
  console.error('Users route error:', err.message);
  res.status(500).json({ success: false, message: 'Server error' });
});

// What gets saved for a password: the login hash, plus an encrypted copy the Master page can show
const passwordFields = async (plain) => [await hashPassword(plain), encryptPassword(plain)];
const passwordProblem = (p) => (typeof p !== 'string' || p.length < MIN_PASSWORD ? `Password must be at least ${MIN_PASSWORD} characters` : null);

const COLUMNS = `u.id, u.name, u.email, u.phone, u.role, u.is_active, u.last_login_at, u.created_at,
                 (u.password_hash IS NOT NULL) AS has_password, (u.password_enc IS NOT NULL) AS can_view_password`;

// The list never carries passwords; each one is fetched on demand below
router.get('/', asyncRoute(async (req, res) => {
  const { role } = req.query;
  if (role && !ROLES.includes(role)) return res.status(400).json({ success: false, message: 'Unknown role' });
  const { rows } = await pool.query(
    `SELECT ${COLUMNS} FROM users u WHERE ($1::user_role IS NULL OR u.role = $1::user_role) ORDER BY u.role, u.name`,
    [role || null]);
  res.json({ success: true, users: rows });
}));

// Create a login with the password the admin typed
router.post('/', asyncRoute(async (req, res) => {
  const { name, email, phone, role, password } = req.body;
  if (!name?.trim()) return res.status(400).json({ success: false, message: 'Name is required' });
  if (!EMAIL.test(email || '')) return res.status(400).json({ success: false, message: 'A valid email is required' });
  if (!ROLES.includes(role)) return res.status(400).json({ success: false, message: 'Role must be one of: ' + ROLES.join(', ') });
  const problem = passwordProblem(password);
  if (problem) return res.status(400).json({ success: false, message: problem });

  const [hash, enc] = await passwordFields(password);
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const u = await client.query(
      `INSERT INTO users (name, email, phone, role, password_hash, password_enc) VALUES ($1,$2,$3,$4,$5,$6)
       RETURNING id, name, email, phone, role, is_active, created_at`,
      [name.trim(), email.trim(), phone?.trim() || null, role, hash, enc]);
    const id = u.rows[0].id;
    if (role === 'student') {
      await client.query("INSERT INTO students (user_id, student_code) VALUES ($1, 'FXL-' || lpad(nextval('student_code_seq')::text, 4, '0'))", [id]);
    }
    if (role === 'trainer') await client.query('INSERT INTO trainers (user_id, skills, weekly_capacity) VALUES ($1, $2, 10)', [id, []]);
    await client.query('COMMIT');
    res.status(201).json({ success: true, user: u.rows[0] });
  } catch (err) {
    await client.query('ROLLBACK');
    if (err.code === '23505') return res.status(409).json({ success: false, message: 'That email already has a login' });
    throw err;
  } finally {
    client.release();
  }
}));

// Edit name, phone, or switch a login on/off. The role is fixed once created.
router.patch('/:id', asyncRoute(async (req, res) => {
  const { name, phone, is_active } = req.body;
  if (is_active === false && req.params.id === req.user.id) {
    return res.status(400).json({ success: false, message: 'You cannot deactivate your own login' });
  }
  if (name !== undefined && !String(name).trim()) return res.status(400).json({ success: false, message: 'Name cannot be empty' });
  const { rows } = await pool.query(
    `UPDATE users u SET name = COALESCE($2, u.name), phone = COALESCE($3, u.phone), is_active = COALESCE($4, u.is_active)
     WHERE u.id = $1 RETURNING ${COLUMNS}`,
    [req.params.id, name?.trim() ?? null, phone?.trim() ?? null, typeof is_active === 'boolean' ? is_active : null]);
  if (!rows.length) return res.status(404).json({ success: false, message: 'User not found' });
  res.json({ success: true, user: rows[0] });
}));

// Set a user's password to the one the admin typed
router.post('/:id/password', asyncRoute(async (req, res) => {
  const problem = passwordProblem(req.body.password);
  if (problem) return res.status(400).json({ success: false, message: problem });
  const [hash, enc] = await passwordFields(req.body.password);
  const { rows } = await pool.query(
    `UPDATE users u SET password_hash = $2, password_enc = $3 WHERE u.id = $1 RETURNING ${COLUMNS}`, [req.params.id, hash, enc]);
  if (!rows.length) return res.status(404).json({ success: false, message: 'User not found' });
  res.json({ success: true, user: rows[0] });
}));

// Show the saved password. Each view is written to the server log.
router.get('/:id/password', asyncRoute(async (req, res) => {
  const { rows } = await pool.query('SELECT email, password_enc FROM users WHERE id = $1', [req.params.id]);
  if (!rows.length) return res.status(404).json({ success: false, message: 'User not found' });
  const password = decryptPassword(rows[0].password_enc);
  if (password === null) {
    return res.status(404).json({
      success: false,
      message: canStoreViewable()
        ? 'No viewable password saved. The user changed it themselves, or it was set before viewing existed. Use Set password.'
        : 'Password viewing is not set up (PASSWORD_VIEW_KEY is missing in backend/.env).',
    });
  }
  console.log(`[audit] ${new Date().toISOString()} user ${req.user.id} viewed the password of ${rows[0].email}`);
  res.json({ success: true, password });
}));

export default router;
