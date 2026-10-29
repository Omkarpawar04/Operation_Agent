import React, { useMemo, useState } from 'react';
import { X, Loader2, CheckCircle2, Plus, Info } from 'lucide-react';
import { api } from '../api.js';

const SKILL_SUGGESTIONS = ['Excel', 'Advanced Excel', 'Financial Modeling', 'Valuation', 'DCF', 'FP&A', 'Financial Statement Analysis', 'Equity Research', 'Investment Banking', 'M&A',
  'Credit Analysis', 'Budgeting', 'Forecasting', 'Accounting', 'Tally', 'Power BI', 'SQL', 'Python', 'VBA', 'Bloomberg', 'MIS Reporting', 'Taxation', 'Audit', 'Communication'];
const ROLE_SUGGESTIONS = ['Financial Analyst', 'Equity Research Analyst', 'Investment Banking Analyst', 'FP&A Analyst', 'Credit Analyst', 'Business Analyst',
  'Accountant', 'Audit Associate', 'Research Associate', 'Operations Analyst'];
const GENDERS = ['Male', 'Female', 'Other', 'Prefer not to say'];

const field = 'w-full bg-white border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-50 disabled:text-slate-500';

function Section({ title, why, children }) {
  return (
    <section className="space-y-3 border border-slate-200/80 rounded-3xl p-4 sm:p-5">
      <div><h3 className="text-sm font-bold text-slate-900">{title}</h3>{why && <p className="text-xs text-slate-500 mt-0.5">{why}</p>}</div>
      {children}
    </section>
  );
}

function Field({ label, hint, htmlFor, children }) {
  return (
    <div className="space-y-1 min-w-0">
      <label htmlFor={htmlFor} className="block text-xs font-bold text-slate-700">{label}</label>
      {children}
      {hint && <p className="text-[11px] text-slate-500">{hint}</p>}
    </div>
  );
}

// Type and press Enter (or comma) to add. Tap a suggestion to add it. Tap a chip to remove it.
function ChipInput({ id, label, items, onChange, suggestions, placeholder }) {
  const [text, setText] = useState('');
  const add = (value) => {
    const v = value.trim();
    if (v && !items.some((i) => i.toLowerCase() === v.toLowerCase())) onChange([...items, v]);
    setText('');
  };
  const left = suggestions.filter((s) => !items.some((i) => i.toLowerCase() === s.toLowerCase()));
  return (
    <div className="space-y-2">
      {items.length > 0 && (
        <ul className="flex flex-wrap gap-1.5" aria-label={`Your ${label}`}>
          {items.map((i) => (
            <li key={i}>
              <button type="button" onClick={() => onChange(items.filter((x) => x !== i))} aria-label={`Remove ${i}`}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-100 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-100 transition">
                {i}<X className="w-3 h-3" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <input id={id} className={field} value={text} placeholder={placeholder} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add(text); }
            else if (e.key === 'Backspace' && !text && items.length) onChange(items.slice(0, -1));
          }} />
        <button type="button" onClick={() => add(text)} disabled={!text.trim()} className="px-3 rounded-xl border border-slate-200 text-slate-600 hover:bg-blue-50 disabled:opacity-40 transition" aria-label={`Add ${label}`}><Plus className="w-4 h-4" /></button>
      </div>
      {left.length > 0 && (
        <div className="space-y-1">
          <p className="text-[11px] text-slate-400">Tap to add:</p>
          <div className="flex flex-wrap gap-1.5">
            {left.slice(0, 14).map((s) => (
              <button type="button" key={s} onClick={() => add(s)} className="px-2.5 py-1 rounded-lg text-xs font-medium text-slate-600 bg-slate-50 border border-slate-200 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-100 transition">+ {s}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// The student fills in their own details. Plain words, one short reason per section.
export default function MyDetailsModal({ token, profile, onClose, onSaved, onSessionExpired }) {
  const x = profile.extra || {};
  const [form, setForm] = useState({
    phone: profile.phone || '', whatsapp: x.whatsapp || '', city: profile.city || '', state: x.state || '',
    college: profile.college || '', degree: profile.degree || '', postgraduation: x.postgraduation || '',
    fresher: x.experience_years === undefined || x.experience_years === null ? null : x.experience_years === 0,
    years: x.experience_years > 0 ? String(x.experience_years) : '',
    target_roles: profile.target_roles || [], skills: x.skills || [], linkedin: x.linkedin || '',
    gender: x.gender || '', dob: x.dob || '', address: x.address || '', parent_name: x.parent_name || '', parent_phone: x.parent_phone || '',
  });
  const [sameAsMobile, setSameAsMobile] = useState(Boolean(x.whatsapp) && x.whatsapp === profile.phone);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  // Live progress, using the same eight things the team looks at
  const checks = useMemo(() => [
    ['Mobile number', form.phone.trim()], ['City', form.city.trim()], ['College', form.college.trim()], ['Graduation', form.degree.trim()],
    ['Work experience', form.fresher === true || (form.fresher === false && form.years !== '')], ['Skills', form.skills.length], ['Roles you want', form.target_roles.length], ['LinkedIn profile', form.linkedin.trim()],
  ], [form]);
  const done = checks.filter(([, ok]) => ok).length;
  const percent = Math.round((done / checks.length) * 100);
  const missing = checks.filter(([, ok]) => !ok).map(([label]) => label);

  const submit = async (e) => {
    e.preventDefault();
    if (form.fresher === false && form.years === '') return setError('Tell us how many years of work experience you have, for example 1 or 2.5.');
    setSaving(true);
    setError('');
    const body = {
      phone: form.phone, whatsapp: sameAsMobile ? form.phone : form.whatsapp, city: form.city, state: form.state, college: form.college, degree: form.degree,
      postgraduation: form.postgraduation, target_roles: form.target_roles, skills: form.skills, linkedin: form.linkedin, gender: form.gender, dob: form.dob,
      address: form.address, parent_name: form.parent_name, parent_phone: form.parent_phone,
    };
    if (form.fresher === true) body.experience_years = 0;
    else if (form.fresher === false) body.experience_years = Number(form.years);
    try {
      const d = await api('/students/me', { token, method: 'PATCH', body, onExpired: onSessionExpired });
      onSaved(d.profile);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-900/40 backdrop-blur-sm sm:p-4" role="dialog" aria-modal="true" aria-label="Fill in your details">
      <form onSubmit={submit} className="bg-white border border-slate-200 sm:rounded-3xl rounded-t-3xl shadow-2xl w-full max-w-2xl max-h-[94dvh] overflow-y-auto">
        <div className="sticky top-0 z-10 bg-white/95 backdrop-blur px-5 sm:px-6 pt-4 pb-3 border-b border-slate-100 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div><h2 className="text-base font-extrabold text-slate-900">Fill in your details</h2>
              <p className="text-xs text-slate-500">About 3 minutes. Your trainers and the placement team use this to match you to companies and to prepare your interviews.</p></div>
            <button type="button" onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-700 shrink-0"><X className="w-4 h-4" /></button>
          </div>
          <div>
            <div className="flex items-center justify-between text-[11px] font-bold mb-1"><span className="text-slate-600">{done} of {checks.length} key details filled</span><span className={percent === 100 ? 'text-emerald-600' : 'text-blue-600'}>{percent}%</span></div>
            <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label="Profile completeness">
              <div className={`h-full rounded-full transition-all duration-500 ${percent === 100 ? 'bg-emerald-500' : 'bg-gradient-to-r from-blue-500 to-indigo-600'}`} style={{ width: `${percent}%` }} />
            </div>
            {missing.length > 0 && <p className="text-[11px] text-slate-500 mt-1.5">Still to do: {missing.join(', ')}</p>}
          </div>
        </div>

        <div className="p-5 sm:p-6 space-y-4">
          {error && <p className="text-xs font-medium text-rose-600 bg-rose-50 border border-rose-100 rounded-2xl px-4 py-3" role="alert">{error}</p>}

          <Section title="1. How we reach you" why="Mock interview invites and reminders go to these numbers.">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Mobile number" htmlFor="md-phone" hint="10 digits, no spaces needed"><input id="md-phone" inputMode="tel" className={field} value={form.phone} onChange={set('phone')} placeholder="98765 43210" autoComplete="tel" /></Field>
              <Field label="WhatsApp number" htmlFor="md-wa">
                <input id="md-wa" inputMode="tel" className={field} value={sameAsMobile ? form.phone : form.whatsapp} onChange={set('whatsapp')} disabled={sameAsMobile} placeholder="98765 43210" />
                <label className="flex items-center gap-2 text-[11px] text-slate-600 mt-1"><input type="checkbox" className="accent-blue-600" checked={sameAsMobile} onChange={(e) => setSameAsMobile(e.target.checked)} />Same as my mobile number</label>
              </Field>
              <Field label="City you live in" htmlFor="md-city"><input id="md-city" className={field} value={form.city} onChange={set('city')} placeholder="Mumbai" autoComplete="address-level2" /></Field>
              <Field label="State" htmlFor="md-state"><input id="md-state" className={field} value={form.state} onChange={set('state')} placeholder="Maharashtra" autoComplete="address-level1" /></Field>
            </div>
          </Section>

          <Section title="2. Your education" why="Companies often ask for a minimum qualification.">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="College or university" htmlFor="md-college"><input id="md-college" className={field} value={form.college} onChange={set('college')} placeholder="Mumbai University" /></Field>
              <Field label="Graduation" htmlFor="md-degree" hint="For example B.Com, BBA, B.Sc, B.Tech"><input id="md-degree" className={field} value={form.degree} onChange={set('degree')} placeholder="B.Com" /></Field>
              <Field label="Post graduation (if any)" htmlFor="md-pg" hint="For example MBA, M.Com. Leave empty if none."><input id="md-pg" className={field} value={form.postgraduation} onChange={set('postgraduation')} placeholder="MBA Finance" /></Field>
            </div>
          </Section>

          <Section title="3. Work experience" why="This decides which jobs fit you: fresher roles or experienced roles.">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2" role="radiogroup" aria-label="Work experience">
              {[[true, 'I am a fresher', 'No full-time work experience yet'], [false, 'I have work experience', 'Internships and jobs count']].map(([val, title, sub]) => (
                <label key={String(val)} className={`flex items-start gap-3 border rounded-2xl px-4 py-3 cursor-pointer transition ${form.fresher === val ? 'border-blue-300 bg-blue-50/50' : 'border-slate-200 hover:bg-slate-50'}`}>
                  <input type="radio" name="fresher" className="mt-1 accent-blue-600" checked={form.fresher === val} onChange={() => setForm({ ...form, fresher: val })} />
                  <span><span className="block text-sm font-bold text-slate-800">{title}</span><span className="block text-[11px] text-slate-500">{sub}</span></span>
                </label>
              ))}
            </div>
            {form.fresher === false && (
              <Field label="How many years in total?" htmlFor="md-years" hint="Use decimals for months: 1.5 means one and a half years">
                <input id="md-years" type="number" min="0" max="60" step="0.5" inputMode="decimal" className={`${field} sm:max-w-[180px]`} value={form.years} onChange={set('years')} placeholder="2" />
              </Field>
            )}
          </Section>

          <Section title="4. What you want and what you can do" why="This is the most important part. Companies are matched to you using your skills and the roles you want.">
            <Field label="Roles you want" htmlFor="md-roles" hint="Add up to 10. Type your own, or tap a suggestion.">
              <ChipInput id="md-roles" label="roles" items={form.target_roles} onChange={(v) => setForm({ ...form, target_roles: v })} suggestions={ROLE_SUGGESTIONS} placeholder="Type a role and press Enter" />
            </Field>
            <Field label="Your skills" htmlFor="md-skills" hint="Add everything you can do, even if you are still learning it. More skills means better matches.">
              <ChipInput id="md-skills" label="skills" items={form.skills} onChange={(v) => setForm({ ...form, skills: v })} suggestions={SKILL_SUGGESTIONS} placeholder="Type a skill and press Enter" />
            </Field>
            <Field label="LinkedIn profile link" htmlFor="md-li" hint="Open your LinkedIn, copy the address of your profile, and paste it here."><input id="md-li" inputMode="url" className={field} value={form.linkedin} onChange={set('linkedin')} placeholder="linkedin.com/in/your-name" /></Field>
          </Section>

          <Section title="5. About you (optional)" why="Only the placement team sees this. Fill what you are comfortable with.">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Gender" htmlFor="md-gender">
                <select id="md-gender" className={field} value={form.gender} onChange={set('gender')}><option value="">Choose…</option>{GENDERS.map((g) => <option key={g} value={g}>{g}</option>)}</select>
              </Field>
              <Field label="Date of birth" htmlFor="md-dob"><input id="md-dob" type="date" className={field} value={form.dob} onChange={set('dob')} max={new Date().toISOString().slice(0, 10)} /></Field>
              <div className="sm:col-span-2"><Field label="Address" htmlFor="md-address"><input id="md-address" className={field} value={form.address} onChange={set('address')} placeholder="House, street, area" autoComplete="street-address" /></Field></div>
              <Field label="Parent or guardian name" htmlFor="md-pn"><input id="md-pn" className={field} value={form.parent_name} onChange={set('parent_name')} /></Field>
              <Field label="Parent or guardian phone" htmlFor="md-pp" hint="Used only in an emergency"><input id="md-pp" inputMode="tel" className={field} value={form.parent_phone} onChange={set('parent_phone')} /></Field>
            </div>
            <p className="flex items-start gap-1.5 text-[11px] text-slate-500"><Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />Your name, email and student ID are fixed. If one is wrong, ask the operations team.</p>
          </Section>

          <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 transition">Not now</button>
            <button disabled={saving} className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-sky-500 hover:brightness-105 disabled:opacity-60 shadow-md shadow-blue-500/20 transition">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}Save my details
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
