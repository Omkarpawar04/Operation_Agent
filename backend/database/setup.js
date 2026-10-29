import 'dotenv/config';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import pkg from 'pg';
import { encryptPassword, hashPassword, isHashed, verifyPassword } from '../passwords.js';

const { Client } = pkg;
const dir = path.dirname(fileURLToPath(import.meta.url));

const config = {
  user: process.env.PGUSER || 'postgres',
  host: process.env.PGHOST || 'localhost',
  password: process.env.PGPASSWORD,
  port: Number(process.env.PGPORT) || 5432,
};
const dbName = process.env.PGDATABASE || 'finxl_platform';

// 1. Create the database if it does not exist
const admin = new Client({ ...config, database: 'postgres' });
await admin.connect();
const exists = await admin.query('SELECT 1 FROM pg_database WHERE datname = $1', [dbName]);
if (exists.rowCount === 0) {
  await admin.query(`CREATE DATABASE "${dbName}"`);
  console.log(`Created database ${dbName}`);
}
await admin.end();

// 2. Apply schema (once) and seed data (re-runnable).
//    --reset drops everything in the public schema first. Development only.
const db = new Client({ ...config, database: dbName });
await db.connect();
const run = async (file) => {
  await db.query(fs.readFileSync(path.join(dir, file), 'utf8'));
  console.log(`Applied ${file}`);
};
if (process.argv.includes('--reset')) {
  await db.query('DROP SCHEMA public CASCADE; CREATE SCHEMA public;');
  console.log('Reset: dropped all existing tables');
}
const applied = await db.query("SELECT to_regclass('public.sessions') AS t");
if (applied.rows[0].t) console.log('Schema already applied, skipping (use --reset to rebuild)');
else await run('schema.sql');
// Databases created before the Admin role existed: add it, and make admin@finxl.com an Admin
await db.query("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin' BEFORE 'operations'");
await db.query("UPDATE users SET role = 'admin', name = 'Admin' WHERE email = 'admin@finxl.com' AND role = 'operations'");
await run('seed.sql');

// Databases created before the Master page could show passwords need the extra column
await db.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS password_enc text');

// Student codes (FXL-0001...). Older databases get the column, the sequence, and codes for existing students
await db.query('ALTER TABLE students ADD COLUMN IF NOT EXISTS student_code text');
await db.query('CREATE UNIQUE INDEX IF NOT EXISTS students_student_code_key ON students (student_code)');
await db.query('CREATE SEQUENCE IF NOT EXISTS student_code_seq');
await db.query('ALTER TABLE students ADD COLUMN IF NOT EXISTS aadhaar_enc text, ADD COLUMN IF NOT EXISTS pan_enc text');
await db.query(`UPDATE students s SET student_code = 'FXL-' || lpad(nextval('student_code_seq')::text, 4, '0')
                FROM (SELECT id FROM students WHERE student_code IS NULL ORDER BY created_at, id) x WHERE s.id = x.id`);

// Learning: courses need a description and a published flag; a video's length is optional
await db.query('ALTER TABLE courses ADD COLUMN IF NOT EXISTS description text, ADD COLUMN IF NOT EXISTS is_published boolean NOT NULL DEFAULT false');
await db.query('ALTER TABLE videos ALTER COLUMN duration_sec DROP NOT NULL');

// Watch tracking: the length the player saw and when progress was last reported
await db.query('ALTER TABLE video_progress ADD COLUMN IF NOT EXISTS duration_sec int, ADD COLUMN IF NOT EXISTS last_beat_at timestamptz');

// Which trainers teach which batch
await db.query(`CREATE TABLE IF NOT EXISTS batch_trainers (
  batch_id uuid NOT NULL REFERENCES batches(id), trainer_id uuid NOT NULL REFERENCES trainers(id),
  created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (batch_id, trainer_id))`);

// The seed holds plain demo passwords: store each as a hash (for login) plus an encrypted copy (for Master)
for (const u of (await db.query('SELECT id, password_hash FROM users WHERE password_hash IS NOT NULL')).rows) {
  if (!isHashed(u.password_hash)) {
    await db.query('UPDATE users SET password_hash = $2, password_enc = $3 WHERE id = $1',
      [u.id, await hashPassword(u.password_hash), encryptPassword(u.password_hash)]);
  }
}

// Demo logins created before viewing existed: if they still have the documented password, make it viewable
const DEMO = { 'admin@finxl.com': 'admin123', 'operations@finxl.com': 'operations123', 'placement@finxl.com': 'placement123', 'trainer@finxl.com': 'trainer123', 'student@finxl.com': 'student123' };
for (const u of (await db.query('SELECT id, email, password_hash FROM users WHERE password_enc IS NULL AND password_hash IS NOT NULL')).rows) {
  if (DEMO[u.email] && (await verifyPassword(DEMO[u.email], u.password_hash))) {
    await db.query('UPDATE users SET password_enc = $2 WHERE id = $1', [u.id, encryptPassword(DEMO[u.email])]);
  }
}
console.log('Demo passwords stored');
const { rows } = await db.query('SELECT email, role FROM users ORDER BY email');
console.table(rows);
await db.end();
