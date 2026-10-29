import { Router } from 'express';
import pool from '../db.js';
import { requireRole } from '../auth.js';
import { canStoreViewable, decryptPassword, encryptPassword, hashPassword } from '../passwords.js';
import { completeness, maskAadhaar, maskPan } from './profileRules.js';
import { FIELDS, MIN_PASSWORD, autoMap, ignoredHeaders, limits, pickSheet, readWorkbook, validateRows } from './importer.js';

const router = Router();

const STAGES = ['learning', 'communication', 'technical_mocks', 'final_mock', 'job_ready', 'placed'];
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const STAFF = ['admin', 'operations', 'placement', 'trainer'];
const isOpsTeam = (role) => role === 'operations' || role === 'admin';
const NEXT_CODE = "'FXL-' || lpad(nextval('student_code_seq')::text, 4, '0')";
// Private details only the operations team sees
const TEAM_EXTRA = ['student_status', 'attendance', 'course_completion', 'operations_remark', 'current_ctc', 'expected_ctc', 'education_detail', 'current_location', 'preferred_location', 'management_remark', 'mock_count', 'mock_remark', 'mock_final_status', 'technical_feedback', 'mock_final_remark', 'opportunities_given', 'interview_feedback', 'placement_status', 'placement_remark'];
const OPS_ONLY_EXTRA = ['dob', 'address', 'parent_name', 'parent_phone', 'counsellor', 'reference_of', 'telegram', 'other', 'source_status'];
// A student sees their own details, but not what the team recorded about them
const STUDENT_HIDDEN_EXTRA = ['counsellor', 'reference_of', 'other', 'source_status', ...TEAM_EXTRA];

const asyncRoute = (fn) => (req, res) => fn(req, res).catch((err) => {
  console.error('Students route error:', err.message);
  res.status(500).json({ success: false, message: 'Server error' });
});
const bad = (res, message, status = 400) => res.status(status).json({ success: false, message });
const list = (v) => (Array.isArray(v) ? v : String(v ?? '').split(/[,;\n]/)).map((x) => String(x).trim()).filter(Boolean);
const withPercent = ({ college, degree, extra, ...s }) => ({
  ...s,
  profile_percent: completeness({ phone: s.phone, city: s.city, college, degree, target_roles: s.target_roles, extra }).percent,
});
const like = (q) => `%${q.replace(/[\\%_]/g, (c) => `\\${c}`)}%`;

// ----------------------------------------------------------------------------- batches (for filters and import)
router.get('/meta/batches', requireRole(...STAFF), asyncRoute(async (_req, res) => {
  const { rows } = await pool.query(
    `SELECT b.id, b.name, c.title AS course, count(s.id)::int AS students
     FROM batches b LEFT JOIN courses c ON c.id = b.course_id LEFT JOIN students s ON s.batch_id = b.id
     GROUP BY b.id, c.title ORDER BY b.name`);
  res.json({ success: true, batches: rows });
}));

// ----------------------------------------------------------------------------- list
router.get('/', requireRole(...STAFF), asyncRoute(async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const size = Math.min(100, Math.max(1, parseInt(req.query.page_size, 10) || 25));
  const { q = '', batch_id, stage, flag, sort = 'name' } = req.query;
  if (batch_id && !UUID.test(batch_id)) return bad(res, 'Unknown batch');
  if (stage && !STAGES.includes(stage)) return bad(res, 'Unknown stage');

  const where = ['TRUE'];
  const params = [];
  const p = (v) => { params.push(v); return '$' + params.length; }; // adds a value, returns its $n
  if (q.trim()) {
    const n = p(like(q.trim()));
    where.push(`(u.name ILIKE ${n} OR u.email::text ILIKE ${n} OR s.student_code ILIKE ${n} OR u.phone ILIKE ${n})`);
  }
  if (batch_id) where.push(`s.batch_id = ${p(batch_id)}`);
  if (stage) where.push(`s.stage = ${p(stage)}::student_stage`);
  if (flag === 'never') where.push('(u.last_login_at IS NULL AND u.password_hash IS NOT NULL)');
  if (flag === 'inactive') where.push("u.last_login_at < now() - interval '7 days'");
  if (flag === 'no_skills') where.push("(s.extra->'skills' IS NULL OR jsonb_array_length(s.extra->'skills') = 0)");
  const sqlWhere = where.join(' AND ');
  const order = { name: 'u.name', newest: 's.created_at DESC', last_login: 'u.last_login_at DESC NULLS LAST', code: 's.student_code' }[sort] || 'u.name';

  const base = `FROM students s JOIN users u ON u.id = s.user_id LEFT JOIN batches b ON b.id = s.batch_id WHERE ${sqlWhere}`;
  const total = (await pool.query(`SELECT count(*)::int AS n ${base}`, params)).rows[0].n;
  const { rows } = await pool.query(
    `SELECT s.id, s.student_code, u.name, u.email, u.phone, u.is_active, u.last_login_at, s.city, s.stage, s.level, s.target_roles,
            b.name AS batch, s.created_at, s.college, s.degree, s.extra,
            (u.last_login_at IS NULL AND u.password_hash IS NOT NULL) AS never_logged_in,
            (u.last_login_at < now() - interval '7 days') AS inactive,
            (s.extra->'skills' IS NULL OR jsonb_array_length(s.extra->'skills') = 0) AS no_skills
     ${base} ORDER BY ${order}, u.name LIMIT ${size} OFFSET ${(page - 1) * size}`, params);

  const stages = (await pool.query('SELECT stage, count(*)::int AS total FROM students GROUP BY stage')).rows;
  res.json({ success: true, students: rows.map(withPercent), total, page, page_size: size, stage_counts: stages });
}));

// ----------------------------------------------------------------------------- 360 profile
async function buildProfile(studentId, viewer) {
  const base = await pool.query(
    `SELECT s.id, s.student_code, s.college, s.degree, s.city, s.target_roles, s.extra, s.stage, s.level, s.job_ready_at,
            s.batch_id, s.created_at, s.fast_track_at, s.aadhaar_enc, s.pan_enc,
            u.id AS user_id, u.name, u.email, u.phone, u.is_active, u.last_login_at, (u.password_hash IS NOT NULL) AS has_password,
            b.name AS batch, s.extra->>'course' AS course
     FROM students s JOIN users u ON u.id = s.user_id
     LEFT JOIN batches b ON b.id = s.batch_id WHERE s.id = $1`, [studentId]);
  if (!base.rows.length) return null;
  const s = base.rows[0];
  const q = async (sql) => (await pool.query(sql, [studentId])).rows;

  const [drives, sessions, placements, resumes, activity, learning] = await Promise.all([
    q(`SELECT d.id, c.name AS company, d.role, ds.status, ds.match_score, ds.selected, ds.final_verdict, d.created_at
       FROM drive_students ds JOIN drives d ON d.id = ds.drive_id JOIN companies c ON c.id = d.company_id
       WHERE ds.student_id = $1 ORDER BY d.created_at DESC`),
    q(`SELECT se.id, se.kind, se.mock_number, se.status, se.starts_at, se.meeting_url, tu.name AS trainer, sc.overall AS score
       FROM sessions se LEFT JOIN trainers t ON t.id = se.trainer_id LEFT JOIN users tu ON tu.id = t.user_id
       LEFT JOIN scorecards sc ON sc.session_id = se.id WHERE se.student_id = $1 ORDER BY se.starts_at DESC LIMIT 50`),
    q(`SELECT p.id, co.name AS company, p.role, p.ctc_lpa, p.offer_date FROM placements p JOIN companies co ON co.id = p.company_id
       WHERE p.student_id = $1 ORDER BY p.offer_date DESC`),
    q(`SELECT r.id, r.version, r.ats_match_pct, r.created_at, co.name AS company FROM resumes r
       LEFT JOIN drives d ON d.id = r.drive_id LEFT JOIN companies co ON co.id = d.company_id WHERE r.student_id = $1 ORDER BY r.created_at DESC`),
    q(`SELECT a.id, a.kind, a.summary, a.at, au.name AS actor FROM activity_log a LEFT JOIN users au ON au.id = a.actor_id
       WHERE a.student_id = $1 ORDER BY a.at DESC LIMIT 40`),
    q(`SELECT (SELECT count(*)::int FROM video_progress WHERE student_id = $1 AND passed_at IS NOT NULL) AS videos_passed,
              (SELECT count(*)::int FROM quiz_attempts WHERE student_id = $1) AS quiz_attempts,
              (SELECT count(*)::int FROM comms_sessions WHERE student_id = $1) AS comms_sessions`),
  ]);

  let extra = s.extra || {};
  const hidden = isOpsTeam(viewer.role) ? [] : viewer.role === 'student' ? STUDENT_HIDDEN_EXTRA : OPS_ONLY_EXTRA;
  if (hidden.length) extra = Object.fromEntries(Object.entries(extra).filter(([k]) => !hidden.includes(k)));
  const fill = completeness({ phone: s.phone, city: s.city, college: s.college, degree: s.degree, target_roles: s.target_roles || [], extra: s.extra || {} });

  // Things the team should look at (shown to staff only)
  const flags = [];
  const days = s.last_login_at ? Math.floor((Date.now() - new Date(s.last_login_at)) / 86400000) : null;
  if (s.has_password && !s.last_login_at) flags.push('Has never logged in');
  else if (days !== null && days >= 7) flags.push(`No login for ${days} days`);
  if (!s.has_password) flags.push('No password set yet');
  if (!(extra.skills || []).length) flags.push('No skills added, so drive rankings score this student 0 for skills');
  if (!(s.target_roles || []).length) flags.push('No target role added');
  if (!s.batch) flags.push('Not in a batch');
  if (fill.percent < 100) flags.push(`Profile ${fill.percent}% complete (missing: ${fill.missing.map((m) => m.label.replace(/ \(.*\)/, '').toLowerCase()).join(', ')})`);

  const profile = {
    id: s.id, student_code: s.student_code, name: s.name, email: s.email, phone: s.phone, is_active: s.is_active,
    last_login_at: s.last_login_at, created_at: s.created_at, college: s.college, degree: s.degree, city: s.city,
    target_roles: s.target_roles || [], extra, stage: s.stage, level: s.level, job_ready_at: s.job_ready_at,
    batch_id: s.batch_id, batch: s.batch, course: s.course,
    drives, sessions, placements, resumes, learning: learning[0],
    activity: viewer.role === 'student' ? activity.filter((a) => a.kind !== 'note') : activity,
    flags: viewer.role === 'student' ? [] : flags,
  };
  profile.completeness = fill;
  if (isOpsTeam(viewer.role)) {
    profile.documents = { aadhaar: maskAadhaar(decryptPassword(s.aadhaar_enc)), pan: maskPan(decryptPassword(s.pan_enc)) };
    profile.notes = (await pool.query(
      `SELECT n.id, n.body, n.created_at, u.name AS author FROM student_notes n JOIN users u ON u.id = n.author_id
       WHERE n.student_id = $1 ORDER BY n.created_at DESC`, [studentId])).rows;
  }
  return profile;
}

router.get('/me', requireRole('student'), asyncRoute(async (req, res) => {
  const own = await pool.query('SELECT id FROM students WHERE user_id = $1', [req.user.id]);
  if (!own.rows.length) return bad(res, 'Your student profile is not set up yet. Contact the operations team.', 404);
  res.json({ success: true, profile: await buildProfile(own.rows[0].id, req.user), viewer: req.user.role });
}));

// A student fills in their own details. Only what a student should control; stage, batch, ID and email stay with the team.
const GENDERS = ['Male', 'Female', 'Other', 'Prefer not to say'];
const SELF_TEXT = [
  ['college', 'College', 150, 'col'], ['degree', 'Graduation', 120, 'col'], ['city', 'City', 80, 'col'],
  ['postgraduation', 'Post graduation', 120, 'extra'], ['state', 'State', 80, 'extra'], ['address', 'Address', 300, 'extra'],
  ['parent_name', 'Parent or guardian name', 100, 'extra'], ['linkedin', 'LinkedIn profile', 200, 'extra'], ['telegram', 'Telegram', 80, 'extra'],
];

router.patch('/me', requireRole('student'), asyncRoute(async (req, res) => {
  const own = await pool.query('SELECT id, user_id FROM students WHERE user_id = $1', [req.user.id]);
  if (!own.rows.length) return bad(res, 'Your student profile is not set up yet. Contact the operations team.', 404);
  const b = req.body || {};
  const vals = [own.rows[0].id]; // $1 is the student
  const sets = [];
  const extraPut = {};
  const extraDrop = [];
  const errors = [];
  const bind = (v) => { vals.push(v); return '$' + vals.length; };

  for (const [key, label, max, where] of SELF_TEXT) {
    if (b[key] === undefined) continue;
    const v = String(b[key] ?? '').trim();
    if (v.length > max) { errors.push(`${label} is too long (most ${max} characters)`); continue; }
    if (where === 'col') sets.push(`${key} = ${bind(v || null)}`);
    else if (v) extraPut[key] = v; else extraDrop.push(key);
  }
  for (const [key, label] of [['whatsapp', 'WhatsApp number'], ['parent_phone', 'Parent phone number']]) {
    if (b[key] === undefined) continue;
    const d = String(b[key] ?? '').replace(/\D/g, '');
    if (d && (d.length < 7 || d.length > 15)) { errors.push(`${label} should have 7 to 15 digits`); continue; }
    if (d) extraPut[key] = d; else extraDrop.push(key);
  }
  if (b.gender !== undefined) {
    if (b.gender && !GENDERS.includes(b.gender)) errors.push('Pick one of the gender options');
    else if (b.gender) extraPut.gender = b.gender; else extraDrop.push('gender');
  }
  if (b.dob !== undefined) {
    const d = String(b.dob || '');
    if (d && (!/^\d{4}-\d{2}-\d{2}$/.test(d) || Number.isNaN(Date.parse(d)) || new Date(d) > new Date() || d < '1940-01-01')) errors.push('Date of birth is not a valid date');
    else if (d) extraPut.dob = d; else extraDrop.push('dob');
  }
  if (b.experience_years !== undefined) {
    if (b.experience_years === '' || b.experience_years === null) extraDrop.push('experience_years');
    else {
      const y = Number(b.experience_years);
      if (!Number.isFinite(y) || y < 0 || y > 60) errors.push('Experience should be a number of years, like 0, 1.5 or 3');
      else extraPut.experience_years = y;
    }
  }
  if (b.skills !== undefined) {
    const skills = [...new Set(list(b.skills))];
    if (skills.length > 40 || skills.some((x) => x.length > 60)) errors.push('Add up to 40 skills, each a short phrase');
    else if (skills.length) extraPut.skills = skills; else extraDrop.push('skills');
  }
  if (b.target_roles !== undefined) {
    const roles = [...new Set(list(b.target_roles))];
    if (roles.length > 10 || roles.some((x) => x.length > 80)) errors.push('Add up to 10 roles');
    else sets.push(`target_roles = ${bind(roles)}::text[]`);
  }
  let phone;
  if (b.phone !== undefined) {
    const d = String(b.phone ?? '').replace(/\D/g, '');
    if (d && (d.length < 7 || d.length > 15)) errors.push('Mobile number should have 7 to 15 digits'); else phone = d || null;
  }
  if (errors.length) return bad(res, errors[0]);
  if (!sets.length && !Object.keys(extraPut).length && !extraDrop.length && phone === undefined) return bad(res, 'Nothing to save');

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    sets.push(`extra = (COALESCE(extra, '{}'::jsonb) || ${bind(JSON.stringify(extraPut))}::jsonb) - ${bind(extraDrop)}::text[]`);
    await client.query(`UPDATE students SET ${sets.join(', ')} WHERE id = $1`, vals);
    if (phone !== undefined) await client.query('UPDATE users SET phone = $2 WHERE id = $1', [req.user.id, phone]);
    await client.query("INSERT INTO activity_log (student_id, actor_id, kind, summary) VALUES ($1, $2, 'note', 'Student updated their own details')", [own.rows[0].id, req.user.id]);
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
  res.json({ success: true, profile: await buildProfile(own.rows[0].id, req.user), viewer: req.user.role });
}));

// Full Aadhaar / PAN, for operations only. Every look is recorded on the student's timeline.
router.get('/:id/documents', requireRole('operations'), asyncRoute(async (req, res) => {
  if (!UUID.test(req.params.id)) return bad(res, 'Student not found', 404);
  const { rows } = await pool.query('SELECT aadhaar_enc, pan_enc FROM students WHERE id = $1', [req.params.id]);
  if (!rows.length) return bad(res, 'Student not found', 404);
  const aadhaar = decryptPassword(rows[0].aadhaar_enc);
  const pan = decryptPassword(rows[0].pan_enc);
  if (!aadhaar && !pan) return bad(res, 'No ID numbers are saved for this student', 404);
  console.log(`[audit] ${new Date().toISOString()} user ${req.user.id} viewed the ID numbers of student ${req.params.id}`);
  await pool.query("INSERT INTO activity_log (student_id, actor_id, kind, summary) VALUES ($1, $2, 'note', 'ID numbers viewed')", [req.params.id, req.user.id]);
  res.json({ success: true, aadhaar, pan });
}));

router.get('/:id', requireRole(...STAFF), asyncRoute(async (req, res) => {
  if (!UUID.test(req.params.id)) return bad(res, 'Student not found', 404);
  const profile = await buildProfile(req.params.id, req.user);
  if (!profile) return bad(res, 'Student not found', 404);
  res.json({ success: true, profile, viewer: req.user.role });
}));

// ----------------------------------------------------------------------------- edit + notes (operations)
router.patch('/:id', requireRole('operations'), asyncRoute(async (req, res) => {
  if (!UUID.test(req.params.id)) return bad(res, 'Student not found', 404);
  const b = req.body;
  if (b.name !== undefined && !String(b.name).trim()) return bad(res, 'Name cannot be empty');
  if (b.stage !== undefined && !STAGES.includes(b.stage)) return bad(res, 'Unknown stage');
  if (b.batch_id && !UUID.test(b.batch_id)) return bad(res, 'Unknown batch');
  let years = null;
  if (b.experience_years !== undefined && b.experience_years !== '' && b.experience_years !== null) {
    years = Number(b.experience_years);
    if (!Number.isFinite(years) || years < 0 || years > 60) return bad(res, 'Experience must be a number of years');
  }

  const before = (await pool.query('SELECT stage FROM students WHERE id = $1', [req.params.id])).rows[0];
  if (!before) return bad(res, 'Student not found', 404);

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const extra = {};
    if (b.skills !== undefined) extra.skills = list(b.skills);
    if (b.experience_years !== undefined) extra.experience_years = years;
    const r = await client.query(
      `UPDATE students SET college = COALESCE($2, college), degree = COALESCE($3, degree), city = COALESCE($4, city),
         target_roles = COALESCE($5::text[], target_roles), batch_id = COALESCE($6::uuid, batch_id),
         stage = COALESCE($7::student_stage, stage), extra = COALESCE(extra, '{}'::jsonb) || $8::jsonb
       WHERE id = $1 RETURNING user_id`,
      [req.params.id, b.college?.trim() ?? null, b.degree?.trim() ?? null, b.city?.trim() ?? null,
        b.target_roles !== undefined ? list(b.target_roles) : null, b.batch_id || null, b.stage ?? null, JSON.stringify(extra)]);
    if (b.name !== undefined || b.phone !== undefined) {
      await client.query('UPDATE users SET name = COALESCE($2, name), phone = COALESCE($3, phone) WHERE id = $1',
        [r.rows[0].user_id, b.name?.trim() ?? null, b.phone !== undefined ? String(b.phone).replace(/\D/g, '') || null : null]);
    }
    const what = b.stage && b.stage !== before.stage ? `Stage changed from ${before.stage} to ${b.stage}` : 'Profile details updated';
    await client.query("INSERT INTO activity_log (student_id, actor_id, kind, summary) VALUES ($1, $2, 'note', $3)", [req.params.id, req.user.id, what]);
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
  res.json({ success: true, profile: await buildProfile(req.params.id, req.user) });
}));

// Each team owns only its own operational fields. Admin can correct any team section.
const TEAM_FIELDS = {
  operations: ['student_status', 'attendance', 'course_completion', 'operations_remark', 'current_ctc', 'expected_ctc', 'education_detail', 'current_location', 'preferred_location'],
  trainer: ['mock_count', 'mock_remark', 'mock_final_status', 'technical_feedback', 'mock_final_remark'],
  placement: ['opportunities_given', 'interview_feedback', 'placement_status', 'placement_remark'],
  admin: ['management_remark'],
};
const TEAM_ENUMS = {
  student_status: ['Active', 'Inactive', 'Left Between'],
  attendance: ['Good', 'Average', 'Bad'],
  course_completion: ['Less Than 25%', '25%', '50%', '75%', '100%'],
  mock_final_status: ['Placement Ready', 'Partially Prepared', 'Not Ready for Placement'],
  placement_status: ['Placed', 'Not Placed', 'Not Eligible For Placement'],
};

router.patch('/:id/team-update', requireRole('operations', 'trainer', 'placement', 'admin'), asyncRoute(async (req, res) => {
  if (!UUID.test(req.params.id)) return bad(res, 'Student not found', 404);
  const updates = req.body?.updates;
  if (!updates || typeof updates !== 'object' || Array.isArray(updates)) return bad(res, 'Provide the team updates');
  const role = req.user.role;
  const allowed = role === 'admin' ? Object.values(TEAM_FIELDS).flat() : TEAM_FIELDS[role] || [];
  const keys = Object.keys(updates);
  if (!keys.length || keys.some((key) => !allowed.includes(key))) return bad(res, 'You can only update fields owned by your team', 403);
  const clean = {};
  for (const key of keys) {
    const raw = updates[key];
    if (['mock_count', 'opportunities_given'].includes(key)) {
      const n = Number(raw);
      if (!Number.isInteger(n) || n < 0 || n > 10000) return bad(res, `${key.replaceAll('_', ' ')} must be a non-negative whole number`);
      clean[key] = n;
    } else {
      const value = String(raw ?? '').trim();
      if (TEAM_ENUMS[key] && value && !TEAM_ENUMS[key].includes(value)) return bad(res, `Invalid ${key.replaceAll('_', ' ')}`);
      if (value.length > 4000) return bad(res, `${key.replaceAll('_', ' ')} is too long`);
      clean[key] = value;
    }
  }
  const exists = await pool.query('SELECT 1 FROM students WHERE id = $1', [req.params.id]);
  if (!exists.rowCount) return bad(res, 'Student not found', 404);
  await pool.query("UPDATE students SET extra = COALESCE(extra, '{}'::jsonb) || $2::jsonb WHERE id = $1", [req.params.id, JSON.stringify(clean)]);
  await pool.query("INSERT INTO activity_log (student_id, actor_id, kind, summary) VALUES ($1, $2, 'note', $3)", [req.params.id, req.user.id, `${role === 'admin' ? 'Management' : role[0].toUpperCase() + role.slice(1)} updated ${keys.map((k) => k.replaceAll('_', ' ')).join(', ')}`]);
  res.json({ success: true, profile: await buildProfile(req.params.id, req.user) });
}));

router.post('/:id/notes', requireRole('operations'), asyncRoute(async (req, res) => {
  if (!UUID.test(req.params.id)) return bad(res, 'Student not found', 404);
  const body = String(req.body.body ?? '').trim();
  if (!body) return bad(res, 'Write something first');
  if (body.length > 4000) return bad(res, 'Keep a note under 4000 characters');
  const exists = await pool.query('SELECT 1 FROM students WHERE id = $1', [req.params.id]);
  if (!exists.rowCount) return bad(res, 'Student not found', 404);
  await pool.query('INSERT INTO student_notes (student_id, author_id, body) VALUES ($1, $2, $3)', [req.params.id, req.user.id, body]);
  await pool.query("INSERT INTO activity_log (student_id, actor_id, kind, summary) VALUES ($1, $2, 'note', 'Call note added')", [req.params.id, req.user.id]);
  res.status(201).json({ success: true, profile: await buildProfile(req.params.id, req.user) });
}));

// ----------------------------------------------------------------------------- Excel import (operations)
// Same endpoint for the preview (dry_run) and the real import, so the preview is exactly what will happen.
router.post('/import', requireRole('operations'), asyncRoute(async (req, res) => {
  const { file_name, file_base64, sheet, mapping: sentMapping, options = {}, dry_run = true } = req.body;
  if (typeof file_base64 !== 'string' || !file_base64) return bad(res, 'Choose an Excel file first');
  const buffer = Buffer.from(file_base64, 'base64');

  let sheets;
  try {
    sheets = await readWorkbook(buffer);
  } catch {
    return bad(res, 'Could not read this file. Please upload an Excel .xlsx file (open it and use Save As .xlsx if it is an older format).');
  }
  if (!sheets.length) return bad(res, 'The file has no sheets');
  const chosen = pickSheet(sheets, sheet);
  if (chosen.rows.length > limits.MAX_ROWS) return bad(res, `That sheet has ${chosen.rows.length} rows. Please import at most ${limits.MAX_ROWS} at a time.`);

  const auto = autoMap(chosen.headers);
  const mapping = { ...auto, ...(sentMapping || {}) };
  for (const k of Object.keys(mapping)) {
    const i = mapping[k];
    if (i === '' || i === undefined || i === null) mapping[k] = null;
    else if (!Number.isInteger(Number(i)) || Number(i) < 0 || Number(i) >= chosen.headers.length) mapping[k] = null;
    else mapping[k] = Number(i);
  }
  const defaults = { batch: String(options.batch_name || '').trim(), course: String(options.course_name || '').trim() };
  const missing = FIELDS.filter((f) => f.required && mapping[f.key] === null).map((f) => f.label);

  const summary = {
    file_name: file_name || 'students.xlsx', sheets: sheets.map((s) => ({ name: s.name, rows: s.rows.length })), sheet: chosen.name,
    headers: chosen.headers, ignored_headers: ignoredHeaders(chosen.headers), mapping, auto_mapping: auto, fields: FIELDS.map(({ key, label, required }) => ({ key, label, required: !!required })),
  };
  if (missing.length) {
    return res.json({ success: true, ...summary, blocking: `Tell me which column holds: ${missing.join(' and ')}.`, ready: 0, skipped: 0, problems: [], sample: [] });
  }

  const emails = [...new Set(chosen.rows.map((r) => String(r[mapping.email] ?? '').trim().toLowerCase()).filter(Boolean))];
  const codes = mapping.student_code === null ? [] : [...new Set(chosen.rows.map((r) => String(r[mapping.student_code] ?? '').trim().toLowerCase()).filter(Boolean))];
  const phones = mapping.phone === null ? [] : [...new Set(chosen.rows.map((r) => String(r[mapping.phone] ?? '').replace(/\D/g, '')).filter(Boolean))];
  const existingEmails = new Set((await pool.query('SELECT lower(email::text) AS e FROM users WHERE lower(email::text) = ANY($1::text[])', [emails])).rows.map((r) => r.e));
  const existingCodes = new Set((await pool.query('SELECT lower(student_code) AS c FROM students WHERE lower(student_code) = ANY($1::text[])', [codes])).rows.map((r) => r.c));
  const existingPhones = new Set((await pool.query("SELECT regexp_replace(phone, '\\D', '', 'g') AS p FROM users WHERE regexp_replace(phone, '\\D', '', 'g') = ANY($1::text[])", [phones])).rows.map((r) => r.p));
  const updateExisting = options.import_mode === 'update_existing';
  const { valid, problems, warnings } = validateRows(chosen.rows, chosen.headers, mapping, { existingEmails, existingCodes, existingPhones, defaults, allowExisting: updateExisting });
  const matchByRow = new Map();
  if (updateExisting && valid.length) {
    const { rows: existing } = await pool.query(
      `SELECT s.id, s.user_id, lower(u.email::text) AS email, lower(s.student_code) AS code,
              regexp_replace(coalesce(u.phone, ''), '\\D', '', 'g') AS phone
       FROM students s JOIN users u ON u.id = s.user_id
       WHERE lower(u.email::text) = ANY($1::text[]) OR lower(s.student_code) = ANY($2::text[])
          OR regexp_replace(coalesce(u.phone, ''), '\\D', '', 'g') = ANY($3::text[])`, [emails, codes, phones]);
    const byEmail = new Map(existing.map((r) => [r.email, r]));
    const byCode = new Map(existing.filter((r) => r.code).map((r) => [r.code, r]));
    const byPhone = new Map(existing.filter((r) => r.phone).map((r) => [r.phone, r]));
    for (const entry of valid) {
      const matches = [byEmail.get(entry.rec.email), entry.rec.student_code ? byCode.get(entry.rec.student_code.toLowerCase()) : null, entry.rec.phone ? byPhone.get(entry.rec.phone) : null].filter(Boolean);
      const ids = [...new Set(matches.map((m) => m.id))];
      if (ids.length > 1) problems.push({ row: entry.rowNumber, name: entry.rec.name, email: entry.rec.email, reason: 'Email, student ID or mobile match different students; not updated' });
      else if (matches[0]) matchByRow.set(entry.rowNumber, matches[0]);
    }
  }
  const processable = valid.filter((entry) => !problems.some((p) => p.row === entry.rowNumber));
  const updateCount = [...matchByRow.keys()].filter((row) => processable.some((entry) => entry.rowNumber === row)).length;
  const createCount = processable.length - updateCount;

  if (dry_run) {
    return res.json({
      success: true, ...summary, ready: processable.length, creates: createCount, updates: updateCount, skipped: problems.length, problems: problems.slice(0, 300), warnings: warnings.slice(0, 200), warning_count: warnings.length,
      documents_will_be_stored: processable.filter((v) => v.rec.aadhaar || v.rec.pan).length, can_store_documents: canStoreViewable(),
      sample: processable.slice(0, 5).map(({ rowNumber, rec }) => ({ row: rowNumber, name: rec.name, email: rec.email, phone: rec.phone, city: rec.city })),
      batches_to_create: [...new Set(processable.map((v) => v.rec.batch).filter(Boolean))].slice(0, 10),
    });
  }

  // ---- real import
  const mode = options.password_mode || 'none';
  if (mode === 'common' && String(options.common_password || '').length < MIN_PASSWORD) return bad(res, `The shared password must be at least ${MIN_PASSWORD} characters`);
  if (mode === 'column' && mapping.password === null) return bad(res, 'Pick the column that holds the passwords');
  if (!processable.length) return bad(res, 'There are no valid rows to import or update');

  // Hash passwords first, a few at a time, so the database transaction stays short
  const secrets = new Array(processable.length).fill(null);
  let noPassword = 0;
  const wanted = (rec) => (mode === 'common' ? String(options.common_password) : mode === 'column' ? rec.password : '');
  for (let i = 0; i < processable.length; i += 16) {
    await Promise.all(processable.slice(i, i + 16).map(async ({ rec, rowNumber }, j) => {
      if (matchByRow.has(rowNumber)) return;
      const plain = wanted(rec);
      if (plain && plain.length >= MIN_PASSWORD) secrets[i + j] = [await hashPassword(plain), encryptPassword(plain)];
      else noPassword += 1;
    }));
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const batchIds = new Map();
    // Batches are matched by name. The course in the sheet stays on the student as a label; learning courses are built by the admin.
    const batchId = async (name) => {
      if (!name) return null;
      const key = name.toLowerCase();
      if (!batchIds.has(key)) {
        const f = await client.query('SELECT id FROM batches WHERE lower(name) = $1', [key]);
        batchIds.set(key, f.rows[0]?.id ?? (await client.query('INSERT INTO batches (name) VALUES ($1) RETURNING id', [name])).rows[0].id);
      }
      return batchIds.get(key);
    };

    const imp = await client.query(
      'INSERT INTO student_imports (file_name, uploaded_by, rows_total, rows_imported, rows_skipped, problems) VALUES ($1,$2,$3,$4,$5,$6) RETURNING id',
      [summary.file_name, req.user.id, chosen.rows.length, processable.length, problems.length, JSON.stringify(problems.slice(0, 500))]);
    const importId = imp.rows[0].id;

    const studentIds = [];
    let docsNotStored = 0;
    let updated = 0;
    for (let i = 0; i < processable.length; i += 1) {
      const { rec, rowNumber } = processable[i];
      const existingStudent = matchByRow.get(rowNumber);
      if (existingStudent) {
        const batch = rec.batch ? await batchId(rec.batch) : null;
        const extra = { ...rec.extra, ...(rec.course ? { course: rec.course } : {}) };
        await client.query('UPDATE users SET name = COALESCE($2, name), phone = COALESCE($3, phone) WHERE id = $1', [existingStudent.user_id, rec.name || null, rec.phone || null]);
        await client.query(
          `UPDATE students SET batch_id = COALESCE($2::uuid, batch_id), college = COALESCE($3, college), degree = COALESCE($4, degree), city = COALESCE($5, city),
             target_roles = CASE WHEN cardinality($6::text[]) > 0 THEN $6::text[] ELSE target_roles END,
             extra = COALESCE(extra, '{}'::jsonb) || $7::jsonb WHERE id = $1`,
          [existingStudent.id, batch, rec.college, rec.degree, rec.city, rec.target_roles, JSON.stringify(extra)]);
        studentIds.push(existingStudent.id); updated += 1;
        continue;
      }
      const [hash, enc] = secrets[i] || [null, null];
      const u = await client.query(
        "INSERT INTO users (name, email, phone, role, password_hash, password_enc) VALUES ($1,$2,$3,'student',$4,$5) RETURNING id",
        [rec.name, rec.email, rec.phone, hash, enc]);
      const extra = { ...rec.extra, ...(rec.course ? { course: rec.course } : {}) };
      // ID numbers are only ever stored encrypted; with no key they are dropped rather than saved as plain text
      const docs = { aadhaar: null, pan: null };
      if (canStoreViewable()) { docs.aadhaar = rec.aadhaar ? encryptPassword(rec.aadhaar) : null; docs.pan = rec.pan ? encryptPassword(rec.pan) : null; }
      else if (rec.aadhaar || rec.pan) docsNotStored += 1;
      const st = await client.query(
        `INSERT INTO students (user_id, student_code, batch_id, import_id, college, degree, city, target_roles, extra, aadhaar_enc, pan_enc)
         VALUES ($1, COALESCE($2, ${NEXT_CODE}), $3, $4, $5, $6, $7, $8, $9, $10, $11) RETURNING id`,
        [u.rows[0].id, rec.student_code, await batchId(rec.batch), importId, rec.college, rec.degree, rec.city, rec.target_roles, JSON.stringify(extra), docs.aadhaar, docs.pan]);
      studentIds.push(st.rows[0].id);
    }
    await client.query(
      "INSERT INTO activity_log (student_id, actor_id, kind, summary) SELECT unnest($1::uuid[]), $2, 'imported', $3",
      [studentIds, req.user.id, `Imported from ${summary.file_name}`]);
    await client.query('COMMIT');
    res.status(201).json({ success: true, imported: processable.length - updated, updated, skipped: problems.length, problems: problems.slice(0, 300), warnings: warnings.slice(0, 200), warning_count: warnings.length, documents_not_stored: docsNotStored, no_password: noPassword, import_id: importId });
  } catch (err) {
    await client.query('ROLLBACK');
    if (err.code === '23505') return bad(res, 'Someone else created one of these students while you were importing. Run the preview again.', 409);
    throw err;
  } finally {
    client.release();
  }
}));

export default router;
