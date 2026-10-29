import readXlsxFile from 'read-excel-file/node';

// Everything a student row can carry. `aliases` are header spellings we recognise (letters and digits only, lower-case),
// most specific first: when two columns could match, the earlier alias wins.
export const FIELDS = [
  { key: 'name', label: 'Full name', required: true, aliases: ['name', 'fullname', 'studentname', 'student'] },
  { key: 'email', label: 'Email', required: true, aliases: ['email', 'emailid', 'emailaddress', 'mail', 'eemail'] },
  { key: 'phone', label: 'Phone', aliases: ['mobile', 'phone', 'mobileno', 'mobilenumber', 'phoneno', 'phonenumber', 'contact', 'contactno'] },
  { key: 'student_code', label: 'Student ID', aliases: ['stdid', 'studentid', 'studentcode', 'rollno', 'rollnumber', 'enrollmentno', 'enrolmentno', 'regno', 'registrationno', 'id'] },
  { key: 'batch', label: 'Batch', aliases: ['batch', 'batchname'] },
  { key: 'course', label: 'Course', aliases: ['courseenrolled', 'course', 'coursename', 'program', 'programme'] },
  { key: 'course_mode', label: 'Course mode', aliases: ['coursemode', 'learningmode', 'mode'] },
  { key: 'student_status', label: 'Student status', aliases: ['studentstatus', 'status'] },
  { key: 'attendance', label: 'Attendance', aliases: ['attendance', 'attendence'] },
  { key: 'course_completion', label: 'Course completion', aliases: ['coursecompletionpercentage', 'coursecompletion', 'completionpercentage'] },
  { key: 'operations_remark', label: 'Remark for placement team', aliases: ['remarkforplacementteam', 'operationsremark'] },
  { key: 'current_ctc', label: 'Current / previous CTC', aliases: ['currentpreviousctc', 'currentctc', 'previousctc'] },
  { key: 'expected_ctc', label: 'Expected CTC', aliases: ['expectedctc'] },
  { key: 'education_detail', label: 'Education details', aliases: ['education'] },
  { key: 'current_location', label: 'Current location', aliases: ['currentlocation'] },
  { key: 'preferred_location', label: 'Preferred location', aliases: ['preferredlocationforjob', 'preferredlocation'] },
  { key: 'management_remark', label: 'Management remark', aliases: ['priyankasremark', 'priyankareview', 'managementremark'] },
  { key: 'mock_count', label: 'Number of mocks given', aliases: ['numberofmocksgiven', 'mockcount'] },
  { key: 'mock_remark', label: 'Mock remark', aliases: ['mockremark', 'remark'] },
  { key: 'mock_final_status', label: 'Mock final status', aliases: ['mockfinalstatus', 'finalstatus'] },
  { key: 'technical_feedback', label: 'Technical feedback', aliases: ['technicalfeedback'] },
  { key: 'mock_final_remark', label: 'Mock final remark', aliases: ['mockfinalremark', 'finalremark'] },
  { key: 'opportunities_given', label: 'Total opportunities given', aliases: ['totalopportunitiesgiven', 'opportunitiesgiven'] },
  { key: 'interview_feedback', label: 'Interview feedback', aliases: ['interviewsattendedorfeedback', 'interviewfeedback'] },
  { key: 'placement_status', label: 'Placement status', aliases: ['placementstatus'] },
  { key: 'placement_remark', label: 'Placement remark', aliases: ['placementremark', 'remark'] },
  { key: 'source_status', label: 'Old system status', aliases: ['oldsyststatus', 'sourcestatus'] },
  { key: 'city', label: 'City', aliases: ['city', 'town'] },
  { key: 'college', label: 'College', aliases: ['college', 'institute', 'university', 'collegename'] },
  { key: 'degree', label: 'Graduation / degree', aliases: ['graduation', 'degree', 'qualification'] },
  { key: 'postgraduation', label: 'Post graduation', aliases: ['postgraduation', 'pg', 'postgraduate'] },
  { key: 'experience_years', label: 'Experience (years)', aliases: ['yearofexperience', 'yearsofexperience', 'experienceyears', 'totalexperience', 'workexperience', 'experience'] },
  { key: 'experience_note', label: 'Experience (notes)', aliases: ['experience'] },
  { key: 'skills', label: 'Skills', aliases: ['skills', 'skillset', 'keyskills'] },
  { key: 'target_roles', label: 'Target roles', aliases: ['targetrole', 'targetroles', 'jobrole', 'desiredrole'] },
  { key: 'whatsapp', label: 'WhatsApp', aliases: ['whatsapp', 'whatapp', 'whatsappno', 'whatsappnumber'] },
  { key: 'telegram', label: 'Telegram', aliases: ['telegram'] },
  { key: 'state', label: 'State', aliases: ['state'] },
  { key: 'gender', label: 'Gender', aliases: ['gender', 'sex'] },
  { key: 'dob', label: 'Date of birth', aliases: ['dob', 'dateofbirth', 'birthdate'] },
  { key: 'address', label: 'Address', aliases: ['address'] },
  { key: 'parent_name', label: 'Parent / guardian', aliases: ['parentname', 'parentgaurdianname', 'parentguardianname', 'guardianname', 'guardian'] },
  { key: 'parent_phone', label: 'Parent contact', aliases: ['parentmobile', 'parentcontact', 'parentphone', 'guardiancontact'] },
  { key: 'counsellor', label: 'Counsellor', aliases: ['counsellor', 'counselor', 'counsellorname'] },
  { key: 'admission_date', label: 'Admission date', aliases: ['admissiondate', 'dateofadmission', 'joiningdate', 'enrolleddate'] },
  { key: 'linkedin', label: 'LinkedIn', aliases: ['linkedin', 'linkein', 'linkedinurl', 'linkedinprofile'] },
  { key: 'reference_of', label: 'Referred by', aliases: ['reference', 'referenceof', 'referredby', 'referral'] },
  { key: 'aadhaar', label: 'Aadhaar number', aliases: ['aadharcard', 'aadhaarcard', 'aadhar', 'aadhaar', 'aadharno', 'aadhaarno', 'aadhaarnumber', 'aadharnumber'] },
  { key: 'pan', label: 'PAN number', aliases: ['pannum', 'pannumber', 'pancard', 'panno', 'pan'] },
  { key: 'password', label: 'Password', aliases: ['password', 'pwd', 'initialpassword'] },
];

// Money columns are never imported, never stored, and never shown (decision: fees live elsewhere)
const IGNORED = new Set(['fees', 'fee', 'paidfee', 'paidfees', 'duefees', 'duefee', 'feespaid', 'feepaid', 'totalfees', 'feedue', 'feebalance', 'pendingfees', 'amountpaid', 'balancefees']);

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PAN = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const MAX_ROWS = 5000;
export const MIN_PASSWORD = 6;

export const normHeader = (s) => String(s ?? '').toLowerCase().replace(/[^a-z0-9]/g, '');

export function toText(v) {
  if (v === null || v === undefined) return '';
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? '' : v.toISOString().slice(0, 10);
  if (typeof v === 'number') return String(v);
  return String(v).replace(/\s+/g, ' ').trim();
}

export function parseYears(v) {
  if (typeof v === 'number') return v >= 0 && v < 60 ? v : null;
  const t = toText(v).toLowerCase();
  if (!t) return null;
  if (/^(fresher|none|nil|no|na|n\/a|0)$/.test(t)) return 0;
  const n = parseFloat((t.match(/\d+(\.\d+)?/) || [])[0]);
  if (Number.isNaN(n)) return null;
  return /month/.test(t) && !/year|yr/.test(t) ? Math.round((n / 12) * 10) / 10 : n;
}

const toList = (v) => toText(v).split(/[,;|\n]/).map((x) => x.trim()).filter(Boolean);
const digits = (v) => toText(v).replace(/\D/g, '');

// Read every sheet. Blank phantom columns and rows (common in real exports) are dropped.
export async function readWorkbook(buffer) {
  if (buffer.length < 4 || buffer[0] !== 0x50 || buffer[1] !== 0x4b) throw new Error('not-xlsx');
  const sheets = await readXlsxFile(buffer);
  return sheets.map(({ sheet, data }) => {
    const rows = data.filter((r) => r.some((c) => c !== null && toText(c) !== ''));
    if (!rows.length) return { name: sheet, headers: [], rows: [] };
    // Operational workbooks often start with a legend and team headings. Pick the
    // first of the first 12 rows that looks most like the actual field-name row.
    const headerAt = Math.max(0, Math.min(11, rows.length - 1));
    let headerIndex = 0;
    let bestScore = -1;
    for (let i = 0; i <= headerAt; i += 1) {
      const labels = rows[i].map(normHeader);
      const score = FIELDS.reduce((n, field) => n + (labels.some((label) => field.aliases.includes(label)) ? 1 : 0), 0);
      if (score > bestScore) { bestScore = score; headerIndex = i; }
    }
    const headerRow = rows[headerIndex] || [];
    const body = rows.slice(headerIndex + 1);
    const keep = headerRow.map((h, i) => (toText(h) ? i : -1)).filter((i) => i >= 0);
    return {
      name: sheet,
      headers: keep.map((i) => toText(headerRow[i])),
      rows: body.map((r) => keep.map((i) => r[i] ?? null)),
    };
  });
}

// The sheet most likely to be the student list: has an email column and the most rows
export function pickSheet(sheets, wanted) {
  const byName = sheets.find((s) => s.name === wanted);
  if (byName) return byName;
  const withEmail = sheets.filter((s) => s.headers.some((h) => FIELDS[1].aliases.includes(normHeader(h))));
  const pool = withEmail.length ? withEmail : sheets;
  return pool.reduce((best, s) => (s.rows.length > best.rows.length ? s : best), pool[0]);
}

// field key -> column index (or null). Each column is used once, and a field tries its aliases in order.
export function autoMap(headers) {
  const used = new Set();
  const mapping = {};
  const norm = headers.map(normHeader);
  for (const f of FIELDS) {
    let found = -1;
    for (const alias of f.aliases) {
      found = norm.findIndex((h, i) => !used.has(i) && !IGNORED.has(h) && h === alias);
      if (found >= 0) break;
    }
    mapping[f.key] = found >= 0 ? found : null;
    if (found >= 0) used.add(found);
  }
  return mapping;
}

export const ignoredHeaders = (headers) => headers.filter((h) => IGNORED.has(normHeader(h)));

// One spreadsheet row -> the record we store. Columns that are not mapped are kept under `other`, except fee columns.
export function toRecord(row, headers, mapping, defaults = {}) {
  const cell = (key) => (mapping[key] === null || mapping[key] === undefined ? null : row[mapping[key]]);
  const text = (key) => toText(cell(key));
  const mapped = new Set(Object.values(mapping).filter((i) => i !== null && i !== undefined));
  const warnings = [];

  const extra = {};
  const put = (k, v) => { if (v !== '' && v !== null && v !== undefined && !(Array.isArray(v) && !v.length)) extra[k] = v; };
  put('skills', toList(cell('skills')));
  put('experience_years', parseYears(cell('experience_years')));
  for (const k of ['whatsapp', 'telegram', 'state', 'gender', 'dob', 'address', 'parent_name', 'parent_phone', 'counsellor', 'admission_date',
    'postgraduation', 'linkedin', 'reference_of', 'course_mode', 'source_status', 'experience_note', 'student_status', 'attendance',
    'course_completion', 'operations_remark', 'management_remark', 'mock_remark', 'mock_final_status', 'technical_feedback',
    'mock_final_remark', 'interview_feedback', 'placement_status', 'placement_remark', 'current_ctc', 'expected_ctc', 'education_detail', 'current_location', 'preferred_location']) {
    put(k, ['whatsapp', 'parent_phone'].includes(k) ? digits(cell(k)) : text(k));
  }
  for (const k of ['mock_count', 'opportunities_given']) {
    const value = text(k);
    if (value !== '') put(k, Number.isFinite(Number(value)) && Number(value) >= 0 ? Math.floor(Number(value)) : value);
  }
  const other = {};
  headers.forEach((h, i) => {
    if (!mapped.has(i) && !IGNORED.has(normHeader(h)) && toText(row[i]) && Object.keys(other).length < 30) other[h] = toText(row[i]);
  });
  put('other', Object.keys(other).length ? other : '');

  // ID numbers: kept only when they look right, so a typo never ends up stored as if it were real
  let aadhaar = null;
  const rawAadhaar = text('aadhaar');
  if (rawAadhaar) {
    const d = digits(cell('aadhaar'));
    if (/^\d{12}$/.test(d)) aadhaar = d; else warnings.push({ field: 'Aadhaar number', reason: 'Not 12 digits, left blank' });
  }
  let pan = null;
  const rawPan = text('pan').toUpperCase().replace(/\s/g, '');
  if (rawPan) {
    if (PAN.test(rawPan)) pan = rawPan; else warnings.push({ field: 'PAN number', reason: 'Not in the format ABCDE1234F, left blank' });
  }

  return {
    name: text('name'),
    email: text('email').toLowerCase(),
    phone: digits(cell('phone')) || null,
    student_code: text('student_code') || null,
    batch: text('batch') || defaults.batch || '',
    course: text('course') || defaults.course || '',
    city: text('city') || null,
    college: text('college') || null,
    degree: text('degree') || null,
    target_roles: toList(cell('target_roles')),
    password: text('password'),
    aadhaar,
    pan,
    warnings,
    extra,
  };
}

// Split rows into the ones we can create and the ones we must skip, with a plain-English reason for each skip
export function validateRows(rows, headers, mapping, { existingEmails, existingCodes, existingPhones = new Set(), defaults, allowExisting = false }) {
  const valid = [];
  const problems = [];
  const warnings = [];
  const seenEmail = new Map();
  const seenCode = new Map();
  const seenPhone = new Map();

  rows.forEach((row, i) => {
    const rowNumber = i + 2; // row 1 is the header
    const rec = toRecord(row, headers, mapping, defaults);
    const skip = (reason) => problems.push({ row: rowNumber, name: rec.name || null, email: rec.email || null, reason });

    if (!rec.name) return skip('Name is missing');
    if (!rec.email) return skip('Email is missing');
    if (!EMAIL.test(rec.email)) return skip('Email is not valid');
    if (seenEmail.has(rec.email)) return skip(`Same email as row ${seenEmail.get(rec.email)} in this file`);
    if (!allowExisting && existingEmails.has(rec.email)) return skip('Already has a login');
    if (rec.phone) {
      if (seenPhone.has(rec.phone)) return skip(`Same mobile number as row ${seenPhone.get(rec.phone)} in this file`);
      if (!allowExisting && existingPhones.has(rec.phone)) return skip('Mobile number already belongs to another student');
      seenPhone.set(rec.phone, rowNumber);
    }
    if (rec.student_code) {
      const code = rec.student_code.toLowerCase();
      if (seenCode.has(code)) return skip(`Same student ID as row ${seenCode.get(code)} in this file`);
      if (!allowExisting && existingCodes.has(code)) return skip('Student ID already used by another student');
      seenCode.set(code, rowNumber);
    }
    seenEmail.set(rec.email, rowNumber);
    rec.warnings.forEach((w) => warnings.push({ row: rowNumber, name: rec.name, ...w }));
    valid.push({ rowNumber, rec });
  });
  return { valid, problems, warnings };
}

export const limits = { MAX_ROWS };
