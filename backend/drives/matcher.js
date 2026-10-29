import { norm } from './jdParser.js';

// Weights add up to 100. Course completion is left out until the learning tables (phase 3) have data.
const W = { skills: 50, role: 20, location: 15, experience: 15 };

const list = (v) => (Array.isArray(v) ? v : []).map(norm);

// student: { target_roles, city, extra: { skills, experience_years } }   req: output of parseJd
export function scoreStudent(student, req, role) {
  const have = new Set(list(student.extra?.skills));
  const reasons = [];

  // Skills: required skills count 3x preferred. If the JD lists only one kind, that kind carries all the weight.
  const reqd = list(req.required_skills);
  const pref = list(req.preferred_skills).filter((s) => !reqd.includes(s));
  const hit = (arr) => arr.filter((s) => have.has(s)).length;
  const wReq = reqd.length ? 3 : 0;
  const wPref = pref.length ? 1 : 0;
  const skillRatio = wReq + wPref === 0 ? 0
    : ((reqd.length ? (hit(reqd) / reqd.length) * wReq : 0) + (pref.length ? (hit(pref) / pref.length) * wPref : 0)) / (wReq + wPref);
  const all = [...reqd, ...pref];
  reasons.push({
    factor: 'skills', points: Math.round(skillRatio * W.skills), max: W.skills,
    detail: `${hit(all)} of ${all.length} JD skills matched`, missing: all.filter((s) => !have.has(s)),
  });

  // Target role: share of the drive role's words found in the student's closest target role (partial credit)
  const roleWords = norm(role).split(' ').filter((w) => w.length > 2);
  const roleRatio = roleWords.length
    ? Math.max(0, ...list(student.target_roles).map((t) => roleWords.filter((w) => t.includes(w)).length / roleWords.length))
    : 0;
  reasons.push({
    factor: 'role', points: Math.round(roleRatio * W.role), max: W.role,
    detail: roleRatio === 1 ? 'Target role matches' : roleRatio > 0 ? 'Target role partly matches' : 'Target role differs',
  });

  // Location
  const locOk = !req.location || norm(student.city || '') === norm(req.location);
  reasons.push({
    factor: 'location', points: locOk ? W.location : 0, max: W.location,
    detail: !req.location ? 'No location set for the drive' : locOk ? 'Same city' : `Based in ${student.city || 'unknown'}`,
  });

  // Experience: full marks if there is no minimum or it is met, partial otherwise
  const years = Number(student.extra?.experience_years || 0);
  const need = req.min_experience_years || 0;
  reasons.push({
    factor: 'experience', points: Math.round((need === 0 ? 1 : Math.min(years / need, 1)) * W.experience), max: W.experience,
    detail: need === 0 ? 'No minimum experience in the JD' : `${years} of ${need} years required`,
  });

  return { score: Math.min(100, reasons.reduce((a, r) => a + r.points, 0)), reasons };
}
