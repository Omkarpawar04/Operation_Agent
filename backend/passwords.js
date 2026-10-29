import crypto from 'crypto';
import { promisify } from 'util';

const scrypt = promisify(crypto.scrypt);
const KEYLEN = 64;
const PREFIX = 'scrypt$';

// Stored as "scrypt$<salt>$<hash>". Passwords are never stored or shown in plain text.
export async function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = (await scrypt(password, salt, KEYLEN)).toString('hex');
  return `${PREFIX}${salt}$${hash}`;
}

export async function verifyPassword(password, stored) {
  if (typeof stored !== 'string' || !stored.startsWith(PREFIX)) return false;
  const [, salt, hash] = stored.split('$');
  const expected = Buffer.from(hash, 'hex');
  const actual = await scrypt(password, salt, expected.length);
  return crypto.timingSafeEqual(expected, actual);
}

export const isHashed = (stored) => typeof stored === 'string' && stored.startsWith(PREFIX);

// 12 characters, no look-alikes (0/O, 1/l/I), easy to read out over a call
export function generatePassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789';
  return Array.from({ length: 12 }, () => chars[crypto.randomInt(chars.length)]).join('');
}

// ---------------------------------------------------------------------------
// Viewable passwords (Master page). Stored encrypted with PASSWORD_VIEW_KEY, so a copy of the
// database alone does not reveal them. Login still uses the one-way hash above.
// ---------------------------------------------------------------------------
const viewKey = () => {
  const hex = process.env.PASSWORD_VIEW_KEY || '';
  return /^[0-9a-f]{64}$/i.test(hex) ? Buffer.from(hex, 'hex') : null;
};

export const canStoreViewable = () => viewKey() !== null;

export function encryptPassword(plain) {
  const key = viewKey();
  if (!key) return null;
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const data = Buffer.concat([cipher.update(plain, 'utf8'), cipher.final()]);
  return ['v1', iv.toString('base64'), cipher.getAuthTag().toString('base64'), data.toString('base64')].join('.');
}

export function decryptPassword(stored) {
  const key = viewKey();
  if (!key || typeof stored !== 'string') return null;
  const [version, iv, tag, data] = stored.split('.');
  if (version !== 'v1') return null;
  try {
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(iv, 'base64'));
    decipher.setAuthTag(Buffer.from(tag, 'base64'));
    return Buffer.concat([decipher.update(Buffer.from(data, 'base64')), decipher.final()]).toString('utf8');
  } catch {
    return null; // wrong key or tampered value
  }
}
