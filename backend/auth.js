import crypto from 'crypto';

// Signed token (HMAC-SHA256), no extra dependency. Replace with Google/OTP sessions later.
const SECRET = process.env.AUTH_SECRET || crypto.randomBytes(32).toString('hex'); // random per start if unset
const TTL_MS = 12 * 60 * 60 * 1000;

const sign = (body) => crypto.createHmac('sha256', SECRET).update(body).digest('base64url');

export function issueToken(user) {
  const body = Buffer.from(JSON.stringify({ id: user.id, role: user.role, exp: Date.now() + TTL_MS })).toString('base64url');
  return `${body}.${sign(body)}`;
}

function verify(token = '') {
  const [body, sig] = token.split('.');
  if (!body || !sig) return null;
  const expected = Buffer.from(sign(body));
  const given = Buffer.from(sig);
  if (expected.length !== given.length || !crypto.timingSafeEqual(expected, given)) return null;
  const payload = JSON.parse(Buffer.from(body, 'base64url').toString());
  return payload.exp > Date.now() ? payload : null;
}

// A 2-hour link that only works for one video. It lets a <video> tag stream through the backend without the login token in the address.
export function issueStreamToken(userId, videoId) {
  const body = Buffer.from(JSON.stringify({ k: 'stream', u: userId, v: videoId, exp: Date.now() + 2 * 60 * 60 * 1000 })).toString('base64url');
  return `${body}.${sign(body)}`;
}
export function verifyStreamToken(token) {
  const p = verify(token);
  return p && p.k === 'stream' ? p : null;
}

// Usage: app.use('/api/x', requireRole('placement', 'operations')). Admin passes every check, except routes that name only 'admin' for others.
export const requireRole = (...roles) => (req, res, next) => {
  const user = verify((req.headers.authorization || '').replace(/^Bearer /, ''));
  if (!user || user.k === 'stream') return res.status(401).json({ success: false, message: 'Please log in' });
  if (roles.length && user.role !== 'admin' && !roles.includes(user.role)) return res.status(403).json({ success: false, message: 'Not allowed for your role' });
  req.user = user;
  next();
};

// Database roles are lowercase; the frontend uses 'Operations', 'Trainer', ...
export const displayRole = (role) => role.charAt(0).toUpperCase() + role.slice(1);
