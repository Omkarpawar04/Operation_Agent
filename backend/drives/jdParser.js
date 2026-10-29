import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const CLI = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'resume_optimizer', 'backend', 'jd_cli.py');
const PYTHON = process.env.PYTHON_BIN || 'python';

export const norm = (s) => String(s).toLowerCase().replace(/modelling/g, 'modeling').replace(/\s+/g, ' ').trim();

// Runs the resume optimizer's JD analyzer. Swap this function for a Gemini call later; keep the return shape.
function analyze(job) {
  return new Promise((resolve, reject) => {
    const p = spawn(PYTHON, [CLI], { stdio: ['pipe', 'pipe', 'pipe'] });
    let out = '', err = '';
    p.stdout.on('data', (d) => (out += d));
    p.stderr.on('data', (d) => (err += d));
    p.on('error', reject);
    p.on('close', (code) => {
      if (code !== 0) return reject(new Error(err.trim().split('\n').pop() || `jd_cli exited ${code}`));
      try { resolve(JSON.parse(out)); } catch (e) { reject(e); }
    });
    p.stdin.end(JSON.stringify(job));
  });
}

// Returns { required_skills, preferred_skills, min_experience_years, qualifications, location, keywords, industry }
export async function parseJd({ company, role, location, jdText }) {
  const a = await analyze({ title: role, company, description: jdText });
  const years = [...jdText.matchAll(/(\d+)\s*\+?\s*(?:-\s*\d+\s*)?years?/gi)].map((m) => Number(m[1]));
  return {
    required_skills: [...new Set(a.required_skills || [])],
    preferred_skills: [...new Set(a.preferred_skills || [])],
    min_experience_years: years.length ? Math.min(...years) : 0,
    qualifications: a.qualifications || [],
    location: location || null,
    keywords: a.keywords || [],
    industry: a.industry,
  };
}
