import net from 'net';
import express from 'express';
import cors from 'cors';
import pool from './db.js'; // db.js loads .env
import { displayRole, issueToken } from './auth.js';
import { hashPassword, verifyPassword } from './passwords.js';
import drivesRouter from './drives/routes.js';
import usersRouter from './users/routes.js';
import studentsRouter from './students/routes.js';
import learningRouter from './learning/routes.js';
import batchesRouter from './batches/routes.js';
import accountRouter from './account/routes.js';
import dashboardRouter from './dashboard/routes.js';

const app = express();

// Excel imports arrive as a JSON body with the file inside, so that one route accepts a larger body
app.use('/api/students/import', express.json({ limit: '20mb' }));
app.use(express.json());

// Enable CORS for frontend running on port 5173
app.use(cors({
  origin: process.env.FRONTEND_ORIGIN || 'http://localhost:5173',
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true
}));

// Slow down password guessing: 8 wrong attempts per email + address, then wait 15 minutes
const MAX_FAILS = 8;
const LOCK_MS = 15 * 60 * 1000;
const fails = new Map(); // key -> { count, since }
const failKey = (req) => `${req.ip}|${String(req.body?.email || '').toLowerCase()}`;
const isLocked = (key) => {
  const f = fails.get(key);
  if (!f) return false;
  if (Date.now() - f.since > LOCK_MS) { fails.delete(key); return false; }
  return f.count >= MAX_FAILS;
};
const recordFail = (key) => {
  const f = fails.get(key);
  fails.set(key, f && Date.now() - f.since <= LOCK_MS ? { ...f, count: f.count + 1 } : { count: 1, since: Date.now() });
};

// Used when the email is unknown, so a wrong email takes as long as a wrong password
const DUMMY_HASH = await hashPassword('not-a-real-password');

app.post('/api/login', async (req, res) => {
  const { email, password } = req.body;
  if (typeof email !== 'string' || typeof password !== 'string') {
    return res.status(400).json({ success: false, message: 'Email and password are required' });
  }
  const key = failKey(req);
  if (isLocked(key)) {
    return res.status(429).json({ success: false, message: 'Too many attempts. Try again in 15 minutes.' });
  }

  try {
    const result = await pool.query('SELECT * FROM users WHERE email = $1 AND is_active', [email]);
    const user = result.rows[0];
    const ok = await verifyPassword(password, user?.password_hash ?? DUMMY_HASH);

    if (!user || !ok) {
      recordFail(key);
      return res.status(401).json({ success: false, message: 'Invalid email or password' });
    }

    fails.delete(key);
    await pool.query('UPDATE users SET last_login_at = NOW() WHERE id = $1', [user.id]);

    res.json({
      success: true,
      message: 'Login successful',
      token: issueToken(user),
      user: { id: user.id, name: user.name, email: user.email, role: displayRole(user.role) }
    });
  } catch (err) {
    console.error('Database query error:', err.message);
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

app.use('/api/me', accountRouter);
app.use('/api/dashboard', dashboardRouter);
app.use('/api/drives', drivesRouter);
app.use('/api/users', usersRouter);
app.use('/api/students', studentsRouter);
app.use('/api/learning', learningRouter);
app.use('/api/batches', batchesRouter);

const PORT = Number(process.env.API_PORT) || 3001;

// On Windows two servers can quietly share one port (the old one keeps answering with old code).
// Look for a listener first and refuse to start instead.
const portTaken = (port) => new Promise((resolve) => {
  const probe = net.connect({ port, host: 'localhost' });
  probe.once('connect', () => { probe.destroy(); resolve(true); });
  probe.once('error', () => resolve(false));
});

if (await portTaken(PORT)) {
  console.error(`Port ${PORT} is already in use: an older server is still running. Stop it (Ctrl+C in its terminal, or end the node.exe process) and start again.`);
  process.exit(1);
}

const server = app.listen(PORT, () => {
  console.log(`Backend server running on port ${PORT}`);
});
server.on('error', (err) => {
  console.error('Server error:', err.message);
  process.exit(1);
});

// If the server ever stops, say why
process.on('uncaughtException', (err) => { console.error('Uncaught exception:', err); process.exit(1); });
process.on('unhandledRejection', (err) => { console.error('Unhandled promise rejection:', err); });
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => { console.log(`Received ${sig}, shutting down`); process.exit(0); });
process.on('exit', (code) => console.log(`Server stopped (exit code ${code})`));
