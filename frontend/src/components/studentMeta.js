// Labels and colours for student stages, shared by the list and the profile.
export const STAGES = ['learning', 'communication', 'technical_mocks', 'final_mock', 'job_ready', 'placed'];

export const STAGE_LABEL = {
  learning: 'Learning', communication: 'Communication', technical_mocks: 'Technical mocks',
  final_mock: 'Final mock', job_ready: 'Job ready', placed: 'Placed',
};

export const STAGE_CHIP = {
  learning: 'bg-blue-50 text-blue-700 border-blue-100',
  communication: 'bg-sky-50 text-sky-700 border-sky-100',
  technical_mocks: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  final_mock: 'bg-violet-50 text-violet-700 border-violet-100',
  job_ready: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  placed: 'bg-emerald-100 text-emerald-800 border-emerald-200',
};

export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—');
export const fmtDateTime = (iso) => (iso ? new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—');

// "3 days ago" style, for last-login columns
export function ago(iso) {
  if (!iso) return 'Never';
  const mins = Math.floor((Date.now() - new Date(iso)) / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  return days < 30 ? `${days} day${days === 1 ? '' : 's'} ago` : fmtDate(iso);
}
