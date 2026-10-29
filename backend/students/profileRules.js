// Rules about a student's profile that more than one route needs.

// The eight things drive rankings and recruiters rely on. A profile is "complete" when all are filled.
const CORE = [
  ['phone', 'Mobile number', (p) => Boolean(p.phone)],
  ['city', 'City', (p) => Boolean(p.city)],
  ['college', 'College', (p) => Boolean(p.college)],
  ['degree', 'Graduation', (p) => Boolean(p.degree)],
  ['experience', 'Work experience (put 0 if you are a fresher)', (p) => p.extra?.experience_years !== undefined && p.extra?.experience_years !== null],
  ['skills', 'Skills', (p) => (p.extra?.skills || []).length > 0],
  ['target_roles', 'Roles you want', (p) => (p.target_roles || []).length > 0],
  ['linkedin', 'LinkedIn profile', (p) => Boolean(p.extra?.linkedin)],
];

// p: { phone, city, college, degree, target_roles, extra }
export function completeness(p) {
  const missing = CORE.filter(([, , filled]) => !filled(p)).map(([key, label]) => ({ key, label }));
  return { percent: Math.round(((CORE.length - missing.length) / CORE.length) * 100), missing };
}

// ID numbers are shown masked everywhere; the full number needs an explicit, logged "reveal" by operations
export const maskAadhaar = (v) => (v ? `•••• •••• ${v.slice(-4)}` : null);
export const maskPan = (v) => (v ? `••••••${v.slice(-4)}` : null);
