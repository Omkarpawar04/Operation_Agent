import React, { useCallback, useEffect, useRef, useState } from 'react';
import { UploadCloud, X, Loader2, FileSpreadsheet, CheckCircle2, AlertTriangle, ChevronDown } from 'lucide-react';
import { api } from '../api.js';
import { PrimaryButton } from './ui.jsx';

const MAX_MB = 12;
const field = 'w-full bg-slate-50/80 border border-slate-200/80 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-400';

const toBase64 = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(String(reader.result).split(',')[1] || '');
  reader.onerror = () => reject(new Error('Could not read that file'));
  reader.readAsDataURL(file);
});

// Four steps: choose a file -> check what will happen -> import -> result.
export default function ImportStudentsModal({ token, onClose, onImported, onSessionExpired }) {
  const [step, setStep] = useState('choose'); // choose | review | importing | done
  const [file, setFile] = useState(null); // { name, base64 }
  const [preview, setPreview] = useState(null);
  const [mapping, setMapping] = useState({});
  const [sheet, setSheet] = useState('');
  const [batchName, setBatchName] = useState('');
  const [courseName, setCourseName] = useState('');
  const [passwordMode, setPasswordMode] = useState('none'); // none | common | column
  const [commonPassword, setCommonPassword] = useState('');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [batches, setBatches] = useState([]);
  const expiredRef = useRef(onSessionExpired);
  expiredRef.current = onSessionExpired;
  const fileInput = useRef(null);

  const call = useCallback((body) => api('/students/import', { token, method: 'POST', body, onExpired: () => expiredRef.current?.() }), [token]);

  useEffect(() => {
    api('/students/meta/batches', { token }).then((d) => setBatches(d.batches)).catch(() => {});
  }, [token]);

  const options = () => ({ batch_name: batchName, course_name: courseName, password_mode: passwordMode, common_password: commonPassword });

  const runPreview = async (next = {}) => {
    const f = next.file || file;
    setBusy(true);
    setError('');
    try {
      const d = await call({
        file_name: f.name, file_base64: f.base64, dry_run: true,
        sheet: next.sheet ?? sheet, mapping: next.mapping ?? mapping,
        options: { ...options(), ...(next.options || {}) },
      });
      setPreview(d);
      setMapping(d.mapping);
      setSheet(d.sheet);
      setStep('review');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const onPick = async (picked) => {
    if (!picked) return;
    if (!/\.xlsx$/i.test(picked.name)) return setError('Please choose an Excel .xlsx file. (In Excel: File > Save As > Excel Workbook.)');
    if (picked.size > MAX_MB * 1024 * 1024) return setError(`That file is larger than ${MAX_MB} MB.`);
    setBusy(true);
    setError('');
    try {
      const f = { name: picked.name, base64: await toBase64(picked) };
      setFile(f);
      setSheet('');
      setMapping({});
      await runPreview({ file: f, sheet: '', mapping: {} });
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  };

  const doImport = async () => {
    if (passwordMode === 'common' && commonPassword.length < 6) return setError('The shared password must be at least 6 characters.');
    if (passwordMode === 'column' && (mapping.password === null || mapping.password === undefined || mapping.password === '')) return setError('Pick the column that holds the passwords.');
    setStep('importing');
    setError('');
    try {
      const d = await call({ file_name: file.name, file_base64: file.base64, dry_run: false, sheet, mapping, options: options() });
      setResult(d);
      setStep('done');
      onImported?.();
    } catch (e) {
      setError(e.message);
      setStep('review');
    }
  };

  const changeMapping = (key, value) => {
    const next = { ...mapping, [key]: value === '' ? null : Number(value) };
    setMapping(next);
    runPreview({ mapping: next });
  };

  const headers = preview?.headers || [];
  const ready = preview?.ready ?? 0;
  const mainFields = (preview?.fields || []).filter((f) => f.required);
  const otherFields = (preview?.fields || []).filter((f) => !f.required && f.key !== 'password');

  const select = (key, label) => (
    <label key={key} className="text-[11px] font-bold text-slate-500 uppercase space-y-1 block min-w-0">{label}
      <select className={field} value={mapping[key] ?? ''} onChange={(e) => changeMapping(key, e.target.value)} disabled={busy}>
        <option value="">— not in this file —</option>
        {headers.map((h, i) => <option key={`${h}-${i}`} value={i}>{h}</option>)}
      </select>
    </label>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-900/40 backdrop-blur-sm sm:p-4" role="dialog" aria-modal="true" aria-label="Import students from Excel">
      <div className="bg-white border border-slate-200 sm:rounded-3xl rounded-t-3xl shadow-2xl w-full max-w-3xl max-h-[94dvh] overflow-y-auto">
        <div className="sticky top-0 z-10 bg-white/95 backdrop-blur flex items-center justify-between gap-3 px-5 sm:px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-2 min-w-0">
            <FileSpreadsheet className="w-5 h-5 text-emerald-600 shrink-0" />
            <h2 className="text-sm font-bold text-slate-900 truncate">Import students from Excel</h2>
          </div>
          <button onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-700"><X className="w-4 h-4" /></button>
        </div>

        <div className="p-5 sm:p-6 space-y-5">
          {error && <p className="text-xs font-medium text-rose-600 bg-rose-50 border border-rose-100 rounded-2xl px-4 py-3" role="alert">{error}</p>}

          {step === 'choose' && (
            <>
              <button
                onClick={() => fileInput.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => { e.preventDefault(); onPick(e.dataTransfer.files?.[0]); }}
                disabled={busy}
                className="w-full flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 hover:border-blue-400 hover:bg-blue-50/40 rounded-3xl px-4 py-10 transition text-center"
              >
                {busy ? <Loader2 className="w-8 h-8 text-blue-500 animate-spin" /> : <UploadCloud className="w-8 h-8 text-blue-500" />}
                <span className="text-sm font-bold text-slate-800">{busy ? 'Reading your file…' : 'Choose an Excel file, or drop it here'}</span>
                <span className="text-xs text-slate-500">.xlsx, up to {MAX_MB} MB. The first row should be the column titles.</span>
              </button>
              <input ref={fileInput} type="file" accept=".xlsx" className="hidden" onChange={(e) => { onPick(e.target.files?.[0]); e.target.value = ''; }} />
              <p className="text-xs text-slate-500">Nothing is saved until you review it on the next screen. I recognise columns like Name, Email, Mobile, City, Experience, Skills, Student ID, Batch and Course, and keep every other column on the student&apos;s record.</p>
            </>
          )}

          {(step === 'review' || step === 'importing') && preview && (
            <>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
                <span className="font-semibold text-slate-800 truncate max-w-full">{preview.file_name}</span>
                {preview.sheets.length > 1 && (
                  <label className="flex items-center gap-2 text-slate-500">Sheet
                    <select className={`${field} w-auto`} value={sheet} onChange={(e) => { setSheet(e.target.value); setMapping({}); runPreview({ sheet: e.target.value, mapping: {} }); }} disabled={busy}>
                      {preview.sheets.map((s) => <option key={s.name} value={s.name}>{s.name} ({s.rows} rows)</option>)}
                    </select>
                  </label>
                )}
                {busy && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />}
              </div>

              {preview.blocking ? (
                <p className="text-xs font-medium text-amber-800 bg-amber-50 border border-amber-100 rounded-2xl px-4 py-3">{preview.blocking}</p>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-4"><p className="text-2xl font-black text-emerald-700 tabular-nums">{ready}</p><p className="text-xs font-semibold text-emerald-700">will be created</p></div>
                  <div className={`${preview.skipped ? 'bg-amber-50 border-amber-100' : 'bg-slate-50 border-slate-200'} border rounded-2xl p-4`}><p className={`text-2xl font-black tabular-nums ${preview.skipped ? 'text-amber-700' : 'text-slate-500'}`}>{preview.skipped}</p><p className={`text-xs font-semibold ${preview.skipped ? 'text-amber-700' : 'text-slate-500'}`}>will be skipped</p></div>
                </div>
              )}

              <div className="space-y-3">
                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Which column is which</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{mainFields.map((f) => select(f.key, `${f.label} *`))}</div>
                <details className="group">
                  <summary className="flex items-center gap-1 text-xs font-bold text-blue-600 cursor-pointer select-none list-none"><ChevronDown className="w-3.5 h-3.5 group-open:rotate-180 transition" />Other columns ({otherFields.filter((f) => mapping[f.key] !== null && mapping[f.key] !== undefined).length} found)</summary>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">{otherFields.map((f) => select(f.key, f.label))}</div>
                </details>
              </div>

              {!preview.blocking && (
                <>
                  <div className="space-y-3">
                    <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Batch and course (for rows that do not have their own)</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1 block">Batch name
                        <input list="batch-names" className={field} value={batchName} onChange={(e) => setBatchName(e.target.value)} placeholder="e.g. Batch Nov-26 (optional)" />
                        <datalist id="batch-names">{batches.map((b) => <option key={b.id} value={b.name} />)}</datalist>
                      </label>
                      <label className="text-[11px] font-bold text-slate-500 uppercase space-y-1 block">Course
                        <input className={field} value={courseName} onChange={(e) => setCourseName(e.target.value)} placeholder="e.g. FMER (optional)" />
                      </label>
                    </div>
                  </div>

                  <fieldset className="space-y-2">
                    <legend className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Password for these students</legend>
                    {[
                      ['none', 'Leave it empty for now', 'They cannot log in until you set a password in Master.'],
                      ['common', 'The same password for everyone', 'You type one. You can change any student later.'],
                      ['column', 'Use a column from the file', 'For example a Password or ID column.'],
                    ].map(([value, title, hint]) => (
                      <label key={value} className={`flex items-start gap-3 border rounded-2xl px-4 py-3 cursor-pointer transition ${passwordMode === value ? 'border-blue-300 bg-blue-50/50' : 'border-slate-200 hover:bg-slate-50'}`}>
                        <input type="radio" name="password-mode" className="mt-0.5 accent-blue-600" checked={passwordMode === value} onChange={() => setPasswordMode(value)} />
                        <span className="min-w-0 flex-1"><span className="block text-xs font-bold text-slate-800">{title}</span><span className="block text-[11px] text-slate-500">{hint}</span>
                          {value === 'common' && passwordMode === 'common' && <input className={`${field} mt-2`} value={commonPassword} onChange={(e) => setCommonPassword(e.target.value)} placeholder="Type the password (6+ characters)" aria-label="Shared password" autoComplete="off" />}
                          {value === 'column' && passwordMode === 'column' && (
                            <select className={`${field} mt-2`} value={mapping.password ?? ''} onChange={(e) => setMapping({ ...mapping, password: e.target.value === '' ? null : Number(e.target.value) })} aria-label="Password column">
                              <option value="">Choose the column…</option>
                              {headers.map((h, i) => <option key={`${h}-${i}`} value={i}>{h}</option>)}
                            </select>
                          )}
                        </span>
                      </label>
                    ))}
                  </fieldset>

                  {preview.sample?.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">First few students</p>
                      <ul className="divide-y divide-slate-100 border border-slate-200 rounded-2xl overflow-hidden">
                        {preview.sample.map((s) => <li key={s.row} className="px-4 py-2.5 text-xs flex flex-wrap items-center justify-between gap-x-4"><span className="font-semibold text-slate-800">{s.name}</span><span className="text-slate-500 truncate">{s.email}{s.phone ? ` · ${s.phone}` : ''}{s.city ? ` · ${s.city}` : ''}</span></li>)}
                      </ul>
                    </div>
                  )}

                  {preview.ignored_headers?.length > 0 && (
                    <p className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3">Left out on purpose and never saved: <b>{preview.ignored_headers.join(', ')}</b>.</p>
                  )}
                  {preview.documents_will_be_stored > 0 && (
                    <p className={`text-xs rounded-2xl px-4 py-3 border ${preview.can_store_documents ? 'text-slate-600 bg-slate-50 border-slate-200' : 'text-rose-700 bg-rose-50 border-rose-100'}`}>
                      {preview.can_store_documents
                        ? `${preview.documents_will_be_stored} student${preview.documents_will_be_stored === 1 ? ' has' : 's have'} an Aadhaar or PAN number. They are saved encrypted and shown masked; only operations can reveal one, and each view is logged.`
                        : 'Aadhaar and PAN numbers will NOT be saved, because the encryption key (PASSWORD_VIEW_KEY) is missing in backend/.env.'}
                    </p>
                  )}
                  {preview.warnings?.length > 0 && (
                    <div className="space-y-2">
                      <p className="flex items-center gap-1.5 text-[11px] font-bold text-amber-700 uppercase tracking-wider"><AlertTriangle className="w-3.5 h-3.5" />Imported, but these values are left blank ({preview.warning_count})</p>
                      <ul className="max-h-36 overflow-y-auto divide-y divide-amber-100 border border-amber-100 bg-amber-50/50 rounded-2xl">
                        {preview.warnings.map((w, i) => <li key={i} className="px-4 py-2 text-xs flex flex-wrap gap-x-3"><span className="font-bold text-amber-800">Row {w.row}</span><span className="text-slate-600 truncate">{w.name}</span><span className="text-amber-700">{w.field}: {w.reason}</span></li>)}
                      </ul>
                    </div>
                  )}

                  {preview.problems?.length > 0 && (
                    <div className="space-y-2">
                      <p className="flex items-center gap-1.5 text-[11px] font-bold text-amber-700 uppercase tracking-wider"><AlertTriangle className="w-3.5 h-3.5" />Rows that will be skipped</p>
                      <ul className="max-h-48 overflow-y-auto divide-y divide-amber-100 border border-amber-100 bg-amber-50/50 rounded-2xl">
                        {preview.problems.map((p, i) => <li key={i} className="px-4 py-2 text-xs flex flex-wrap gap-x-3"><span className="font-bold text-amber-800">Row {p.row}</span><span className="text-slate-600 truncate">{p.name || p.email || '(blank)'}</span><span className="text-amber-700">{p.reason}</span></li>)}
                      </ul>
                    </div>
                  )}
                </>
              )}

              <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-between gap-3 pt-2">
                <button onClick={() => { setStep('choose'); setPreview(null); setFile(null); setError(''); }} className="text-xs font-semibold text-slate-500 hover:text-slate-800" disabled={step === 'importing'}>Choose a different file</button>
                <PrimaryButton onClick={doImport} disabled={busy || step === 'importing' || !ready || !!preview.blocking} icon={step === 'importing' ? Loader2 : CheckCircle2}>
                  {step === 'importing' ? 'Importing… this can take a minute' : `Import ${ready} student${ready === 1 ? '' : 's'}`}
                </PrimaryButton>
              </div>
            </>
          )}

          {step === 'done' && result && (
            <>
              <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-100 rounded-2xl px-4 py-4">
                <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
                <div><p className="text-sm font-bold text-emerald-800">{result.imported} student{result.imported === 1 ? '' : 's'} imported</p>
                  <p className="text-xs text-emerald-700">{result.skipped ? `${result.skipped} skipped (see below). ` : ''}{result.no_password ? `${result.no_password} have no password yet; set them in Master.` : 'Passwords are set.'}{result.warning_count ? ` ${result.warning_count} ID value${result.warning_count === 1 ? ' was' : 's were'} left blank because they looked wrong.` : ''}{result.documents_not_stored ? ` ${result.documents_not_stored} ID number${result.documents_not_stored === 1 ? ' was' : 's were'} NOT saved: the encryption key is missing.` : ''}</p></div>
              </div>
              {result.problems?.length > 0 && (
                <ul className="max-h-56 overflow-y-auto divide-y divide-amber-100 border border-amber-100 bg-amber-50/50 rounded-2xl">
                  {result.problems.map((p, i) => <li key={i} className="px-4 py-2 text-xs flex flex-wrap gap-x-3"><span className="font-bold text-amber-800">Row {p.row}</span><span className="text-slate-600 truncate">{p.name || p.email || '(blank)'}</span><span className="text-amber-700">{p.reason}</span></li>)}
                </ul>
              )}
              <PrimaryButton onClick={onClose} className="w-full sm:w-auto">Done</PrimaryButton>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
