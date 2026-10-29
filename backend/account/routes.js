import { Router } from 'express';
import pool from '../db.js';
import { displayRole, requireRole } from '../auth.js';
import { hashPassword, verifyPassword } from '../passwords.js';

// Any logged-in user: who am I, and change my own password.
const router = Router();
router.use(requireRole());

const asyncRoute = (fn) => (req, res) => fn(req, res).catch((err) => {
  console.error('Account route error:', err.message);
  res.status(500).json({ success: false, message: 'Server error' });
});

router.get('/', asyncRoute(async (req, res) => {
  const { rows } = await pool.query('SELECT id, name, email, phone, role FROM users WHERE id = $1 AND is_active', [req.user.id]);
  if (!rows.length) return res.status(401).json({ success: false, message: 'Please log in' });
  res.json({ success: true, user: { ...rows[0], role: displayRole(rows[0].role) } });
}));

router.post('/password', asyncRoute(async (req, res) => {
  const { current_password, new_password } = req.body;
  if (typeof new_password !== 'string' || new_password.length < 6) {
    return res.status(400).json({ success: false, message: 'New password must be at least 6 characters' });
  }
  const { rows } = await pool.query('SELECT password_hash FROM users WHERE id = $1 AND is_active', [req.user.id]);
  if (!rows.length || !(await verifyPassword(current_password || '', rows[0].password_hash))) {
    return res.status(400).json({ success: false, message: 'Current password is wrong' });
  }
  await pool.query('UPDATE users SET password_hash = $2, password_enc = NULL WHERE id = $1', [req.user.id, await hashPassword(new_password)]);
  res.json({ success: true, message: 'Password changed' });
}));

export default router;
