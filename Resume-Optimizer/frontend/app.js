/**
 * FINXL AI Workspace — Modern Application Controller
 * High-performance, clean UI interactions, deterministic state management.
 */

// Selector helper
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// Core State
let selectedFiles = [];
let currentJobId = '';
let currentJobData = null;
let activeSource = 'finxl';
let resultData = null;
let generatedData = null;
let templateId = 'professional';

// Elements
const fileInput = $('#resumeFile');
const analyzeBtn = $('#analyzeBtn');
const dropzone = $('#dropzone');
const fileMeta = $('#fileMeta');
const fileNameDisplay = $('#fileNameDisplay');
const fileMetaDisplay = $('#fileMetaDisplay');
const replaceFileBtn = $('#replaceFileBtn');
const removeFileBtn = $('#removeFileBtn');
const errorBox = $('#error');
const jobSelect = $('#jobSelect');
const customJobId = $('#customJobId');
const pasteJdText = $('#pasteJdText');
const jdFileInput = $('#jdFileInput');
const jdDropzone = $('#jdDropzone');
const sourceOptions = $('#sourceOptions');

// Utilities
const escapeHtml = (value = '') =>
  String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));

const list = (value) => (Array.isArray(value) ? value : []);
const asValues = (value) => (value == null || value === '' ? [] : Array.isArray(value) ? value : [value]);
const skillGroups = (skills = {}) =>
  Object.entries(skills).filter(([, values]) => Array.isArray(values) && values.length);

/**
 * Update 6-step workflow stepper
 * @param {number} stepIndex - 0 to 5
 */
function setWorkflowStep(stepIndex) {
  const steps = $$('.step-item');
  steps.forEach((element, index) => {
    element.classList.toggle('active', index === stepIndex);
    element.classList.toggle('done', index < stepIndex);
  });
}

function setError(message) {
  if (!errorBox) return;
  errorBox.textContent = message;
  errorBox.classList.remove('hidden');
}

function clearError() {
  if (!errorBox) return;
  errorBox.textContent = '';
  errorBox.classList.add('hidden');
}

function toast(message) {
  const element = $('#toast');
  if (!element) return;
  element.textContent = message;
  element.classList.remove('hidden');
  setTimeout(() => element.classList.add('hidden'), 4000);
}

/**
 * Handle File Selection
 */
function pickResumeFile(selection) {
  clearError();
  if (!selection) return;
  const files = Array.from(selection instanceof FileList ? selection : [selection]);
  if (files.length > 5) {
    selectedFiles = [];
    fileInput.value = '';
    analyzeBtn.disabled = true;
    return setError('Maximum 5 resumes can be optimized at once.');
  }
  for (const file of files) {
    const extension = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx'].includes(extension)) return setError('Please upload a PDF or DOCX resume.');
    if (file.size > 8 * 1024 * 1024) return setError(`${file.name} exceeds the 8 MB limit.`);
  }
  if (!files.length) return;
  selectedFiles = files;
  const file = files[0];
  const extension = file.name.split('.').pop().toLowerCase();

  // Update File Meta Card
  const sizeFormatted = file.size < 1048576
    ? `${(file.size / 1024).toFixed(0)} KB`
    : `${(file.size / 1048576).toFixed(1)} MB`;

  if (fileNameDisplay) fileNameDisplay.textContent = files.map(item => item.name).join(', ');
  if (fileMetaDisplay) fileMetaDisplay.textContent = files.length === 1 ? `${extension.toUpperCase()} · ${sizeFormatted}` : `${files.length} resumes selected`;

  dropzone.classList.add('hidden');
  fileMeta.classList.remove('hidden');
  analyzeBtn.disabled = false;

  // Advance stepper to Step 2 (Resume ready)
  setWorkflowStep(1);
}

function removeResumeFile() {
  selectedFiles = [];
  fileInput.value = '';
  fileMeta.classList.add('hidden');
  dropzone.classList.remove('hidden');
  analyzeBtn.disabled = true;
  clearError();
  setWorkflowStep(0);
}

// Drag and drop event listeners
if (dropzone) {
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag');
    pickResumeFile(e.dataTransfer.files);
  });
}

if (fileInput) {
  fileInput.addEventListener('change', () => pickResumeFile(fileInput.files));
}

if (replaceFileBtn) {
  replaceFileBtn.addEventListener('click', () => fileInput.click());
}

if (removeFileBtn) {
  removeFileBtn.addEventListener('click', removeResumeFile);
}

/**
 * Load and display Job Details
 */
async function loadJob(jobId) {
  const requestedSource = activeSource;
  if (!['finxl', 'external'].includes(requestedSource) || !jobId) return;
  showJobPreview({ title: 'Loading job…', company: '', job_id: jobId, description: 'Loading the selected job description.' });
  currentJobData = null;
  try {
    const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
    if (!response.ok) {
      if (requestedSource === activeSource && ((requestedSource === 'external' && customJobId?.value.trim() === jobId) || (requestedSource === 'finxl' && jobSelect?.value === jobId))) {
        currentJobData = null;
        showJobPreview({ title: 'Untitled Position', job_id: 'N/A', description: 'No job description was found for this reference ID. Check the selection and try again.' });
      }
      return;
    }
    const job = await response.json();
    if (requestedSource !== activeSource ||
        (activeSource === 'finxl' && jobSelect?.value !== jobId) ||
        (activeSource === 'external' && customJobId?.value.trim() !== jobId)) return;
    showJobPreview(job);
  } catch (err) {
    console.warn('Could not load job info:', err);
    if (requestedSource === activeSource) {
      currentJobData = null;
      showJobPreview({ title: 'Untitled Position', job_id: 'N/A', description: 'The selected job description could not be loaded.' });
    }
  }
}

function deriveJobTitle(text) {
  const lines = String(text || '').split(/\r?\n/).map(line => line.replace(/^\s*[#*\-]+\s*/, '').trim()).filter(Boolean);
  for (const line of lines.slice(0, 8)) {
    const labeled = line.match(/^(?:job\s*title|role|position)\s*:\s*(.+)$/i);
    if (labeled?.[1]) return labeled[1].trim().slice(0, 90);
  }
  const sentenceTitle = String(text || '').match(/\b(?:looking for|seeking|hiring)\s+(?:an?\s+)?(.+?)(?=\s+(?:to|who|that|for)\b|[.,\n]|$)/i)?.[1]?.trim();
  if (sentenceTitle && sentenceTitle.length <= 90) return sentenceTitle;
  const candidate = lines.find(line => !/^(?:company|employer|organization|industry|domain|category|department|job\s*id|requisition\s*id)\s*:/i.test(line)) || '';
  if (candidate.length <= 90 && !/^(we are|we're|about (the|this)|job description|overview|responsibilities|qualifications|requirements)\b/i.test(candidate)) return candidate;
  return 'Untitled Position';
}

function normalizePreviewJob(value, fallback = {}) {
  const source = typeof value === 'string' ? { description: value } : (value || {});
  const description = String(source.description || source.summary || source.job_description || source.jd_text || source.text || source.content || fallback.description || '').trim();
  const labeled = (pattern) => description.match(pattern)?.[1]?.trim() || '';
  let title = String(source.title || source.job_title || source.role || source.position || labeled(/^\s*(?:job\s*title|role|position)\s*:\s*(.+)$/im) || fallback.title || '').trim();
  if (!title || /^(pasted job description|uploaded job description|job description)$/i.test(title)) title = deriveJobTitle(description);
  const company = String(source.company || source.employer || source.organization || labeled(/^\s*(?:company|employer|organization)\s*:\s*(.+)$/im) || fallback.company || '').trim();
  const jobId = String(source.job_id || source.id || source.requisition_id || labeled(/^\s*(?:job\s*id|requisition\s*id)\s*:\s*(.+)$/im) || fallback.job_id || '').trim();
  const domain = String(source.domain || source.industry || source.category || source.department || labeled(/^\s*(?:industry|domain|category|department)\s*:\s*(.+)$/im) || fallback.domain || '').trim();
  const domainText = `${title} ${description}`.toLowerCase();
  const inferredDomain = /finance|financial|accounting|investment|banking|fp&a/.test(domainText) ? 'Finance'
    : /software|developer|engineer|technology|data|devops/.test(domainText) ? 'Technology'
      : /marketing|seo|growth|content|branding/.test(domainText) ? 'Marketing' : 'General';
  return { ...source, title: title || 'Untitled Position', company: company || 'Company not specified',
    job_id: jobId || 'N/A', description: description || 'Job description unavailable.',
    domain: domain || inferredDomain };
}

function showJobPreview(value, fallback = {}) {
  const job = normalizePreviewJob(value, fallback);
  currentJobData = job;
  currentJobId = job.job_id === 'N/A' ? '' : job.job_id;
  $('#jobCardTitle').textContent = job.title;
  $('#jobCardCompany').innerHTML = `${escapeHtml(job.company)} <span class="dot-sep">·</span> Job ID: <strong id="jobCardId">${escapeHtml(job.job_id)}</strong>`;
  $('#jobCardDescription').textContent = job.description;
  $('#jobDomainBadge').textContent = job.domain;
  return job;
}

function resetJobPreview(description = 'Select a job or provide a job description to see its preview.') {
  currentJobData = null;
  currentJobId = '';
  $('#jobCardTitle').textContent = 'Untitled Position';
  $('#jobCardCompany').innerHTML = 'Company not specified <span class="dot-sep">·</span> Job ID: <strong id="jobCardId">N/A</strong>';
  $('#jobCardDescription').textContent = description;
  $('#jobDomainBadge').textContent = 'General';
}

function showPastedJobPreview() {
  const text = pasteJdText.value.trim();
  showJobPreview({ title: deriveJobTitle(text), description: text, job_id: text ? 'Pasted JD' : 'N/A' });
}

/**
 * Populate job selector from API
 */
async function initJobCatalogue() {
  try {
    const response = await fetch('/api/jobs');
    if (!response.ok) throw new Error('Job catalogue request failed.');
    const jobs = await response.json();
    if (jobSelect) {
      jobSelect.innerHTML = '<option value="">Select a FINXL role</option>' + (Array.isArray(jobs) ? jobs : []).map((j) =>
        `<option value="${escapeHtml(j.job_id)}">${escapeHtml(j.title)} · ${escapeHtml(j.company || 'FINXL')}</option>`
      ).join('');
      if (activeSource === 'finxl') resetJobPreview();
    }
  } catch {
    if (activeSource === 'finxl') {
      if (jobSelect) jobSelect.innerHTML = '<option value="">Job catalogue unavailable</option>';
      resetJobPreview('The job catalogue could not be loaded. You can still paste or upload a job description.');
    }
  }
}

// Job Source Switching (FINXL Job / External Job / Paste JD / Upload JD)
if (sourceOptions) {
  $$('.source-card').forEach((card) => {
    card.addEventListener('click', () => {
      $$('.source-card').forEach((c) => c.classList.remove('selected'));
      card.classList.add('selected');
      activeSource = card.dataset.source;

      // Toggle input panels
      $('#finxlSourceInput').classList.toggle('hidden', activeSource !== 'finxl');
      $('#externalSourceInput').classList.toggle('hidden', activeSource !== 'external');
      $('#pasteSourceInput').classList.toggle('hidden', activeSource !== 'paste');
      $('#uploadJdInput').classList.toggle('hidden', activeSource !== 'upload');

      if (activeSource === 'finxl' && jobSelect) {
        if (jobSelect.value) loadJob(jobSelect.value);
        else resetJobPreview();
      } else if (activeSource === 'external' && customJobId) {
        currentJobData = null;
        showJobPreview({ title: 'Untitled Position', job_id: customJobId.value.trim() || 'N/A', description: 'Enter an external job reference ID to load its job description preview.' });
        customJobId.focus();
        if (customJobId.value.trim()) {
          loadJob(customJobId.value.trim());
        }
      } else if (activeSource === 'paste') {
        showPastedJobPreview();
      } else if (activeSource === 'upload') {
        currentJobData = null;
        showUploadedJobPreview();
      }
    });
  });
}

if (jobSelect) {
  jobSelect.addEventListener('change', () => {
    if (jobSelect.value) loadJob(jobSelect.value);
    else resetJobPreview();
  });
}

if (customJobId) {
  customJobId.addEventListener('input', () => {
    const val = customJobId.value.trim();
    currentJobData = null;
    showJobPreview({ title: val ? 'Loading job…' : 'Untitled Position', job_id: val || 'N/A', description: val ? 'Loading the job description for this reference.' : 'Enter an external job reference ID to load its preview.' });
  });
  customJobId.addEventListener('change', () => {
    const val = customJobId.value.trim();
    if (val) loadJob(val);
  });
}

if (pasteJdText) pasteJdText.addEventListener('input', showPastedJobPreview);

function showUploadedJobPreview() {
  const file = jdFileInput?.files?.[0];
  if (!file) return showJobPreview({ title: 'Untitled Position', job_id: 'N/A', description: 'Attach a PDF, DOCX, TXT, or JSON file to use it as the target job description.' });
  const filename = file.name;
  const ext = filename.split('.').pop().toLowerCase();
  const title = filename.replace(/\.[^.]+$/, '') || 'Uploaded Job Description';
  const isCurrentFile = () => activeSource === 'upload' && jdFileInput.files[0] === file;
  showJobPreview({ title, job_id: filename, description: `Reading the selected ${ext.toUpperCase()} job description…` });
  if (ext === 'txt') {
    const reader = new FileReader();
    reader.onload = () => { if (isCurrentFile()) showJobPreview({ title: deriveJobTitle(reader.result), job_id: filename, description: String(reader.result || '').trim() }); };
    reader.readAsText(file);
  } else if (ext === 'json') {
    const reader = new FileReader();
    reader.onload = () => {
      if (!isCurrentFile()) return;
      try {
        const job = JSON.parse(String(reader.result || '{}'));
        showJobPreview(job, { title, job_id: filename, description: JSON.stringify(job, null, 2) });
      } catch {
        showJobPreview({ title, job_id: filename, description: 'This JSON file could not be previewed. It will be validated when you analyze the resume.' });
      }
    };
    reader.readAsText(file);
  } else {
    showJobPreview({ title, job_id: filename, description: `Selected ${ext.toUpperCase()} job description. Its extracted text will be used for matching.` });
  }
}

if (jdDropzone && jdFileInput) {
  jdDropzone.addEventListener('click', (event) => {
    if (event.target !== jdFileInput) jdFileInput.click();
  });
  const attachJdFile = (file) => {
    if (!file) return;
    const extension = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx', 'txt', 'json'].includes(extension)) {
      jdFileInput.value = '';
      return setError('Please upload a PDF, DOCX, TXT, or JSON job description.');
    }
    if (file.size > 8 * 1024 * 1024) {
      jdFileInput.value = '';
      return setError(`${file.name} exceeds the 8 MB limit.`);
    }
    clearError();
    showUploadedJobPreview();
    toast(`Attached JD: ${file.name}`);
  };
  jdFileInput.addEventListener('change', () => {
    attachJdFile(jdFileInput.files[0]);
  });
  jdDropzone.addEventListener('dragover', (event) => event.preventDefault());
  jdDropzone.addEventListener('drop', (event) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    jdFileInput.files = transfer.files;
    attachJdFile(file);
  });
}

$('#jobDetails').addEventListener('click', async (e) => {
  e.preventDefault();
  const job = currentJobData;
  if (!job) return toast('Job details are not available yet.');
  toast(`${job.title} (${job.job_id})\n${job.description}`);
});

/**
 * Chips Renderer
 */
function renderChips(values, kind = '') {
  const items = list(values);
  return items.length
    ? items.map((val) => `<span class="chip-tag ${kind}">${escapeHtml(val)}</span>`).join(' ')
    : '<span class="text-subtle">None detected</span>';
}

/**
 * Format resume experience item
 */
function formatExperienceItem(item) {
  const title = item.role || item.degree || item.name || item.company || 'Entry';
  const org = item.company || item.institution || '';
  const dates = [item.start_date, item.end_date].filter(Boolean).join(' – ');
  const bullets = [...list(item.bullets), ...(item.other || [])];
  return `
    <div class="match-item-row" style="margin-bottom: 8px;">
      <div class="match-item-top">
        <strong class="match-item-name">${escapeHtml(org || title)}</strong>
        ${dates ? `<span class="match-item-meta">${escapeHtml(dates)}</span>` : ''}
      </div>
      ${org && item.role ? `<div class="match-item-meta" style="color: var(--text-secondary);">${escapeHtml(item.role)}</div>` : ''}
      ${bullets.length ? `<ul style="padding-left: 18px; margin-top: 4px; font-size: 12px; color: var(--text-secondary);">${bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join('')}</ul>` : ''}
    </div>
  `;
}

/**
 * Render Matching Section (04 Match) with Evidence
 */
function renderMatchingSection(match) {
  const matchedItems = list(match.items).filter((it) => it.status === 'matched');
  const relatedItems = list(match.items).filter((it) => it.status === 'related');
  const notDetectedItems = list(match.items).filter((it) => it.status === 'not_detected');

  const renderGroup = (items, statusClass, badgeLabel) => {
    if (!items.length) {
      return '<div class="match-disclaimer-note">None detected in this category.</div>';
    }
    return `
      <div class="match-rows-list">
        ${items.map((it) => `
          <div class="match-item-row">
            <div class="match-item-top">
              <div>
                <span class="status-badge ${statusClass}">${badgeLabel}</span>
                <strong class="match-item-name" style="margin-left: 6px;">${escapeHtml(it.requirement)}</strong>
              </div>
              <span class="match-item-meta">${escapeHtml(it.type.replace('_', ' '))} · ${escapeHtml(it.importance)}</span>
            </div>
            ${it.evidence && it.evidence.length ? `
              <details class="match-evidence-details">
                <summary>Verified resume evidence (${it.evidence.length})</summary>
                <ul>
                  ${it.evidence.map((line) => `<li>${escapeHtml(line)}</li>`).join('')}
                </ul>
              </details>
            ` : '<div class="match-item-meta" style="font-size: 11px; color: var(--text-subtle); margin-top: 2px;">No direct evidence found in uploaded resume.</div>'}
          </div>
        `).join('')}
      </div>
    `;
  };

  return `
    <div class="match-sections-list">
      <!-- MATCHED -->
      <div class="match-category-box">
        <div class="match-category-header">
          <div class="match-status-heading">
            <span class="status-badge matched">MATCHED</span>
            <strong>Direct Skills & Qualifications</strong>
          </div>
          <span class="count-pill">${matchedItems.length} items</span>
        </div>
        ${renderGroup(matchedItems, 'matched', 'MATCHED')}
      </div>

      <!-- RELATED -->
      <div class="match-category-box">
        <div class="match-category-header">
          <div class="match-status-heading">
            <span class="status-badge related">RELATED</span>
            <strong>Contextual & Transferable Experience</strong>
          </div>
          <span class="count-pill">${relatedItems.length} items</span>
        </div>
        ${renderGroup(relatedItems, 'related', 'RELATED')}
      </div>

      <!-- NOT DETECTED IN RESUME -->
      <div class="match-category-box">
        <div class="match-category-header">
          <div class="match-status-heading">
            <span class="status-badge not-detected">NOT DETECTED</span>
            <strong>Not Detected in Resume</strong>
          </div>
          <span class="count-pill">${notDetectedItems.length} items</span>
        </div>
        <div class="match-disclaimer-note">
          Not detected in the uploaded resume. Missing skills are never assumed or added to your resume.
        </div>
        ${renderGroup(notDetectedItems, 'not-detected', 'NOT DETECTED')}
      </div>
    </div>
  `;
}

/**
 * Render Complete Analysis Screen (Steps 3 & 4)
 */
function renderAnalysis(data) {
  const resume = data.resume_analysis;
  const match = data.match;
  const job = data.job_analysis;
  const detectedSkills = skillGroups(resume.skills).flatMap(([, values]) => values);
  const requiredSkills = list(job.required_skills);
  const preferredSkills = list(job.preferred_skills);
  const qualifications = list(job.qualifications);
  const responsibilities = list(job.responsibilities);

  // Hide initial inputs, show results
  $('#workspace').classList.add('hidden');
  const resultsContainer = $('#results');
  resultsContainer.classList.remove('hidden');

  // Advance stepper to Step 3 (Analysis)
  setWorkflowStep(2);

  resultsContainer.innerHTML = `
    <!-- Top Result Header -->
    <div class="result-header-card">
      <div class="result-header-info">
        <h2>${escapeHtml(data.job.title)}</h2>
        <p>${escapeHtml(data.job.company)} <span class="dot-sep">·</span> Target Job ID: <strong>${escapeHtml(data.job.job_id)}</strong></p>
      </div>
      <button class="app-btn secondary-btn" id="backBtn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
        <span>Change resume / role</span>
      </button>
    </div>

    <!-- Metric Summary Grid -->
    <div class="metric-summary-grid">
      <div class="metric-card">
        <strong>${detectedSkills.length}</strong>
        <span>Skills Detected</span>
      </div>
      <div class="metric-card matched">
        <strong>${match.counts.matched}</strong>
        <span>Matched</span>
      </div>
      <div class="metric-card related">
        <strong>${match.counts.related}</strong>
        <span>Related</span>
      </div>
      <div class="metric-card missing">
        <strong>${match.counts.missing}</strong>
        <span>Not Detected in Resume</span>
      </div>
    </div>

    <!-- 03 ANALYSIS: 4 Dashboard Cards Grid -->
    <div class="analysis-dashboard-grid">
      <!-- 1. Required Skills -->
      <div class="analysis-card">
        <div class="analysis-card-header">
          <span class="analysis-card-title">Required Skills</span>
          <span class="count-pill">${requiredSkills.length}</span>
        </div>
        <div class="chips-cluster">
          ${renderChips(requiredSkills, 'matched')}
        </div>
      </div>

      <!-- 2. Preferred Skills -->
      <div class="analysis-card">
        <div class="analysis-card-header">
          <span class="analysis-card-title">Preferred Skills</span>
          <span class="count-pill">${preferredSkills.length}</span>
        </div>
        <div class="chips-cluster">
          ${renderChips(preferredSkills, 'related')}
        </div>
      </div>

      <!-- 3. Qualifications & Education -->
      <div class="analysis-card">
        <div class="analysis-card-header">
          <span class="analysis-card-title">Qualifications & Education</span>
          <span class="count-pill">${qualifications.length}</span>
        </div>
        <ul class="analysis-list">
          ${qualifications.map((q) => `<li>${escapeHtml(q)}</li>`).join('') || '<li class="text-subtle">None specified.</li>'}
        </ul>
      </div>

      <!-- 4. Responsibilities -->
      <div class="analysis-card">
        <div class="analysis-card-header">
          <span class="analysis-card-title">Key Responsibilities</span>
          <span class="count-pill">${responsibilities.length}</span>
        </div>
        <ol class="responsibilities-numbered-list">
          ${responsibilities.map((r) => `<li>${escapeHtml(r)}</li>`).join('') || '<li class="text-subtle">None specified.</li>'}
        </ol>
      </div>
    </div>

    <!-- Categorized Requirements Panel -->
    <div class="categorized-panel">
      <h4 style="font-size: 13px; font-weight: 700; margin-bottom: 12px; color: var(--text-primary);">Requirements By Type</h4>
      <div class="categorized-group">
        <h5>Domain Skills</h5>
        <div class="chips-cluster">${renderChips(list(job.domain_skills))}</div>
      </div>
      <div class="categorized-group">
        <h5>Technical Skills</h5>
        <div class="chips-cluster">${renderChips(list(job.technical_skills))}</div>
      </div>
      <div class="categorized-group">
        <h5>Tools & Platforms</h5>
        <div class="chips-cluster">${renderChips(list(job.tools))}</div>
      </div>
      ${list(job.soft_skills).length ? `
        <div class="categorized-group">
          <h5>Soft Skills</h5>
          <div class="chips-cluster">${renderChips(list(job.soft_skills))}</div>
        </div>
      ` : ''}
    </div>

    <!-- 04 MATCH: Requirement Evidence Section -->
    <div class="matching-card-container">
      <div class="matching-header">
        <h3>Resume ↔ Job Requirement Matching</h3>
        <p>Verified match outcomes based on candidate evidence. Unmentioned requirements are never invented.</p>
      </div>
      ${renderMatchingSection(match)}
    </div>

    <!-- Resume Quality Review Panel -->
    <div class="quality-review-panel">
      <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 4px;">Structural Quality Review</h3>
      <p style="font-size: 12px; color: var(--text-muted);">${escapeHtml(data.quality_analysis.method)}</p>
      <div class="quality-issues-grid">
        ${list(data.quality_analysis.issues).length
          ? data.quality_analysis.issues.map((iss) => `
              <div class="quality-issue-badge">
                <span class="issue-sev ${escapeHtml(iss.severity)}">${escapeHtml(iss.severity)}</span>
                <span>${escapeHtml(iss.message)}</span>
              </div>
            `).join('')
          : '<div style="font-size: 12px; color: #059669;">✓ No structural formatting issues detected.</div>'}
      </div>
    </div>

    <!-- 05 OPTIMIZE: Focused AI Workspace Card -->
    <div class="ai-optimize-card" id="optimizationPanel">
      <div class="ai-card-heading">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path></svg>
        <h3 class="ai-card-title">Optimize your resume</h3>
      </div>
      <p class="ai-card-desc">
        Improve the wording and relevance of your existing resume based on the selected job description.
      </p>

      <div class="ai-features-checklist">
        <div class="ai-feature-item">
          <span class="check-green">✓</span>
          <span>Improve existing content</span>
        </div>
        <div class="ai-feature-item">
          <span class="check-green">✓</span>
          <span>Prioritize relevant experience</span>
        </div>
        <div class="ai-feature-item">
          <span class="check-green">✓</span>
          <span>Improve professional wording</span>
        </div>
        <div class="ai-feature-item">
          <span class="check-green">✓</span>
          <span>Optimize relevant keywords</span>
        </div>
      </div>

      <div class="ai-guarantee-callout">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
        <span><strong>Factuality Guarantee:</strong> AI does not invent skills, experience, achievements, qualifications, or metrics.</span>
      </div>

      <div>
        <button class="app-btn primary-btn" id="optimizeBtn">
          <span>Optimize Resume</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </button>
      </div>
    </div>

    <!-- Final Preview & Download Area (Injected in step 6) -->
    <div id="previewArea"></div>
  `;

  // Bind Back button
  $('#backBtn').onclick = () => {
    resultsContainer.classList.add('hidden');
    $('#workspace').classList.remove('hidden');
    setWorkflowStep(selectedFile ? 1 : 0);
  };

  // Bind Optimize button
  $('#optimizeBtn').onclick = runOptimizationFlow;
}

// Common resume action verbs for dynamic bullet detection
const RESUME_ACTION_VERBS = new Set([
  'analyzed', 'analysed', 'created', 'performed', 'presented', 'used', 'built',
  'developed', 'designed', 'implemented', 'engineered', 'conducted', 'maintained',
  'managed', 'collaborated', 'configured', 'delivered', 'automated', 'deployed',
  'integrated', 'executed', 'evaluated', 'formulated', 'generated', 'identified',
  'monitored', 'optimized', 'organized', 'organised', 'programmed', 'produced',
  'reduced', 'resolved', 'reviewed', 'streamlined', 'supported', 'trained',
  'upgraded', 'utilized', 'utilised', 'wrote', 'cleaned', 'assisted', 'led',
  'researched', 'calculated', 'modeled', 'modelled', 'spearheaded', 'established',
  'authored', 'administered', 'architected', 'customized', 'directed', 'facilitated',
  'guided', 'improved', 'initiated', 'inspected', 'instituted', 'mentored',
  'orchestrated', 'overhauled', 'planned', 'pioneered', 'restructured',
  'supervised', 'tested', 'transformed', 'validated', 'verified'
]);

function stripOuterMarkdown(text) {
  if (!text) return '';
  let str = String(text).trim();
  if (str.startsWith('**') && str.endsWith('**') && str.length >= 4) {
    str = str.slice(2, -2).trim();
  } else if (str.startsWith('*') && str.endsWith('*') && str.length >= 2) {
    str = str.slice(1, -1).trim();
  }
  return str;
}

function cleanHeadingText(text) {
  if (!text) return '';
  let str = stripOuterMarkdown(text);
  str = str.replace(/^([•\-\–—]|\*(?!\*))\s*/, '').replace(/^\d+[\.\)]\s*/, '').trim();
  return escapeHtml(str);
}

function formatInlineMarkdown(text) {
  if (!text) return '';
  let str = String(text).trim();

  // 1. Strip leading bullet markers (•, -, *, 1.)
  str = str.replace(/^([•\-\–—]|\*(?!\*))\s*/, '').replace(/^\d+[\.\)]\s*/, '').trim();

  // 2. If the entire line is wrapped in **...**, unwrap it
  if (str.startsWith('**') && str.endsWith('**') && str.length >= 4) {
    const inner = str.slice(2, -2);
    if (!inner.includes('**')) {
      str = inner.trim();
    }
  }

  // 3. Escape HTML to prevent XSS
  str = escapeHtml(str);

  // 4. Convert inline **bold** to <strong>bold</strong>
  str = str.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');

  // 5. Convert inline *italic* to <em>italic</em>
  str = str.replace(/(^|[^\*])\*([^\*]+?)\*(?!\*)/g, '$1<em>$2</em>');

  return str;
}

function isBulletLine(rawLine) {
  const line = String(rawLine).trim();
  if (!line) return false;

  // 1. Explicit bullet marker: •, -, –, —, 1., or single * followed by whitespace
  if (/^([•\-\–—]|\*(?!\*))\s+/.test(line) || /^\d+[\.\)]\s+/.test(line)) {
    return true;
  }

  const clean = stripOuterMarkdown(line);

  // 2. Ends with sentence terminator
  const endsWithPunct = /[.;!]$/.test(clean);

  // 3. First word is an action verb
  const firstWord = (clean.match(/^[a-zA-Z]+/)?.[0] || '').toLowerCase();
  const startsWithActionVerb = RESUME_ACTION_VERBS.has(firstWord);

  if (startsWithActionVerb) return true;
  if (endsWithPunct && clean.length > 25) return true;

  return false;
}

function parseProjectLines(lines) {
  const projects = [];
  let currentProject = null;

  for (const raw of lines) {
    const line = String(raw || '').trim();
    if (!line) continue;

    const isBullet = isBulletLine(line);

    if (!isBullet) {
      // It's a heading line
      if (!currentProject || currentProject.bullets.length > 0 || currentProject.description) {
        currentProject = {
          name: cleanHeadingText(line),
          technologies: [],
          description: '',
          bullets: []
        };
        projects.push(currentProject);
        continue;
      }
    }

    // It's a bullet description
    if (!currentProject) {
      currentProject = {
        name: cleanHeadingText(line),
        technologies: [],
        description: '',
        bullets: []
      };
      projects.push(currentProject);
    } else {
      currentProject.bullets.push(formatInlineMarkdown(line));
    }
  }

  return projects;
}

function normalizeProjects(projectsData) {
  if (!projectsData) return [];

  if (typeof projectsData === 'string') {
    const lines = projectsData.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    return parseProjectLines(lines);
  }

  if (!Array.isArray(projectsData)) return [];
  if (projectsData.length === 0) return [];

  // If array of strings
  if (typeof projectsData[0] === 'string') {
    return parseProjectLines(projectsData);
  }

  // Check if it's a flat list of line objects (e.g. [{name: '**Title**'}, {name: '**Bullet 1**'}])
  const isFlatLineObjects =
    projectsData.length > 1 &&
    projectsData.every((item) => {
      const bulletsEmpty = !item.bullets || item.bullets.length === 0;
      const descEmpty = !item.description;
      const techEmpty = !item.technologies || item.technologies.length === 0;
      return bulletsEmpty && descEmpty && techEmpty;
    }) &&
    projectsData.some((item) => isBulletLine(item.name || item.title || ''));

  if (isFlatLineObjects) {
    const lines = projectsData.map((item) => item.name || item.title || '').filter(Boolean);
    return parseProjectLines(lines);
  }

  // Structured project objects
  const results = [];
  for (const item of projectsData) {
    if (!item) continue;
    if (typeof item === 'string') {
      results.push(...parseProjectLines([item]));
      continue;
    }

    const name = cleanHeadingText(item.name || item.project_name || item.title || '');
    const tech = [...asValues(item.technologies), ...asValues(item.technology), ...asValues(item.tech_stack), ...asValues(item.tech)];
    const dates = [item.start_date, item.end_date].filter(Boolean).map(escapeHtml).join(' – ');
    const subtitle = cleanHeadingText(item.subtitle || item.role || '');

    let bullets = [];
    let description = '';

    if (Array.isArray(item.bullets) && item.bullets.length > 0) {
      bullets = item.bullets.map((b) => formatInlineMarkdown(b)).filter(Boolean);
    }
    bullets.push(...[...asValues(item.responsibilities), ...asValues(item.achievements)].map(formatInlineMarkdown));

    if (item.description) {
      if (Array.isArray(item.description)) {
        const descBullets = item.description.map((b) => formatInlineMarkdown(b)).filter(Boolean);
        bullets = [...bullets, ...descBullets];
      } else if (typeof item.description === 'string') {
        const descStr = item.description.trim();
        if (descStr.includes('\n')) {
          const lines = descStr.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
          for (const l of lines) {
            bullets.push(formatInlineMarkdown(l));
          }
        } else if (isBulletLine(descStr)) {
          bullets.push(formatInlineMarkdown(descStr));
        } else {
          description = formatInlineMarkdown(descStr);
        }
      }
    }

    results.push({
      name,
      subtitle,
      dates,
      technologies: tech,
      url: item.url || item.link || '',
      description,
      bullets,
    });
  }

  return results;
}

function renderProjects(projectsData) {
  const projects = normalizeProjects(projectsData);
  if (!projects.length) return '';

  return projects
    .map((item) => {
      const heading = item.name || '';
      const dates = item.dates || '';
      const subtitle = item.subtitle || '';
      const tech = list(item.technologies);
      const bullets = list(item.bullets);
      const description = item.description ? `<p class="project-description">${item.description}</p>` : '';

      return `
        <div class="resume-entry project-entry">
          <div class="entry-heading project-heading">
            <span>${heading}</span>
            ${dates ? `<small style="font-weight: normal; color: #64748B;">${dates}</small>` : ''}
          </div>
          ${subtitle ? `<div class="entry-subheading project-subheading">${subtitle}</div>` : ''}
          ${tech.length ? `<p class="project-tech"><strong>Tech:</strong> ${escapeHtml(tech.join(', '))}</p>` : ''}
          ${item.url ? `<p class="project-link"><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.url)}</a></p>` : ''}
          ${description}
          ${bullets.length ? `<ul class="project-bullets">${bullets.map((b) => `<li>${b}</li>`).join('')}</ul>` : ''}
        </div>
      `;
    })
    .join('');
}

/**
 * Render Resume Document Preview
 */
function renderResumeDocument(resume, theme) {
  const info = resume.personal_info || {};
  const headerContacts = [info.email, info.phone, info.location, info.linkedin, info.github]
    .filter(Boolean).map((value) => String(value).trim().toLowerCase());
  const contact = [info.email, info.phone, info.location, info.linkedin, info.github]
    .filter(Boolean)
    .map(escapeHtml)
    .join(' · ');

  const renderEntries = (items) =>
    list(items)
      .map((item) => {
        if (item == null || typeof item !== 'object') return `<div class="resume-entry"><p>${formatInlineMarkdown(item)}</p></div>`;
        const heading = cleanHeadingText(item.job_title || item.role || item.company || item.name || item.project_name || item.title || item.institution || item.organization || '');
        const subheading = cleanHeadingText(item.company || item.employer || item.degree || item.field || '');
        const dates = escapeHtml(item.dates || [item.start_date, item.end_date].filter(Boolean).join(' – '));
        const bullets = [...asValues(item.bullets), ...asValues(item.responsibilities), ...asValues(item.achievements)];
        const description = asValues(item.description).filter(Boolean).map((text) => `<p>${formatInlineMarkdown(text)}</p>`).join('');
        const tech = [...asValues(item.technologies), ...asValues(item.technology), ...asValues(item.tech_stack), ...asValues(item.tech)];
        const grade = item.gpa || item.cgpa || item.grade;
        const other = [...asValues(item.other), ...asValues(item.details)];
        const knownFields = new Set(['company','name','project_name','title','institution','organization','role','degree','field','dates','start_date','end_date','location','bullets','responsibilities','achievements','description','technologies','technology','tech_stack','tech','gpa','cgpa','grade','other','details']);
        const extra = Object.entries(item).filter(([key, value]) => !knownFields.has(key) && value != null && value !== '' && (!Array.isArray(value) || value.length))
          .map(([key, value]) => `<p><strong>${escapeHtml(key.replaceAll('_', ' '))}:</strong> ${escapeHtml(Array.isArray(value) ? value.join(', ') : value)}</p>`).join('');
        return `
          <div class="resume-entry">
            <div class="entry-heading">
              <span>${heading}</span>
              ${dates ? `<small style="font-weight: normal; color: #64748B;">${dates}</small>` : ''}
            </div>
            ${subheading ? `<div class="entry-subheading">${subheading}</div>` : ''}
            ${item.location ? `<small style="color: #64748B;">${escapeHtml(item.location)}</small>` : ''}
            ${tech.length ? `<p style="font-size: 11.5px;"><strong>Tech:</strong> ${escapeHtml(tech.join(', '))}</p>` : ''}
            ${grade ? `<p><strong>GPA/Grade:</strong> ${escapeHtml(grade)}</p>` : ''}
            ${other.map((value) => `<p>${formatInlineMarkdown(value)}</p>`).join('')}
            ${description}
            ${extra}
            ${bullets.length ? `<ul>${bullets.map((b) => `<li>${formatInlineMarkdown(b)}</li>`).join('')}</ul>` : ''}
          </div>
        `;
      })
      .join('');

  let body = '';
  if (resume.summary) {
    body += `<h3>Professional Summary</h3><p>${formatInlineMarkdown(resume.summary)}</p>`;
  }
  if (list(resume.experience).length) {
    body += `<h3>Experience</h3>${renderEntries(resume.experience)}`;
  }
  if (list(resume.internships).length) {
    body += `<h3>Internships</h3>${renderEntries(resume.internships)}`;
  }
  if (resume.projects && (Array.isArray(resume.projects) ? resume.projects.length : typeof resume.projects === 'string')) {
    body += `<h3>Projects</h3>${renderProjects(resume.projects)}`;
  }
  if (list(resume.education).length) {
    body += `<h3>Education</h3>${renderEntries(resume.education)}`;
  }
  const groups = skillGroups(resume.skills);
  if (groups.length) {
    body += `<h3>Skills</h3>${groups
      .map(([name, values]) => `<p><strong>${escapeHtml(name.replace('_', ' '))}:</strong> ${escapeHtml(values.join(', '))}</p>`)
      .join('')}`;
  }
  for (const [key, title] of [
    ['certifications', 'Certifications'],
    ['achievements', 'Achievements'],
    ['languages', 'Languages'],
  ]) {
    const values = list(resume[key]).map((item) => String(item ?? '').trim()).filter(Boolean);
    if (values.length) {
      body += `<h3>${title}</h3><ul>${values.map((item) => `<li>${formatInlineMarkdown(item)}</li>`).join('')}</ul>`;
    }
  }
  const previewInternal = new Set(['personal_info','summary','experience','internships','projects','education','skills','certifications','achievements','languages','source_lines','format_signals','normalized_skills','legacy_skills','skill_category_labels','section_order','section_heading_labels','sections_detected']);
  Object.entries(resume || {}).forEach(([key, value]) => {
    if (previewInternal.has(key) || value == null || value === '' || (Array.isArray(value) && !value.length)) return;
    let values = Array.isArray(value) ? value : [value];
    if (key === 'other') {
      values = values.filter((item) => {
        const text = String(item ?? '').trim().toLowerCase();
        return text && !headerContacts.includes(text) && !/(?:linkedin\.com|github\.com)/i.test(text);
      });
    }
    const lines = values.map((item) => {
      if (item && typeof item === 'object') return Object.entries(item).filter(([, v]) => v != null && v !== '').map(([k, v]) => escapeHtml(k.replaceAll('_', ' ')) + ': ' + escapeHtml(Array.isArray(v) ? v.join(', ') : v)).join(' · ');
      return formatInlineMarkdown(item);
    }).filter(Boolean);
    const sourceLabel = resume.section_heading_labels?.[key]?.[0];
    const label = sourceLabel || key.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    if (lines.length) body += '<h3>' + escapeHtml(label) + '</h3><ul>' + lines.map((line) => '<li>' + line + '</li>').join('') + '</ul>';
  });

  return `
    <article class="resume-preview-sheet theme-${theme}">
      <header>
        <h2>${escapeHtml(info.name || 'Candidate')}</h2>
        <div class="resume-contact">${contact}</div>
      </header>
      ${body}
    </article>
  `;
}


/**
 * Step 5: Optimization & Template Selection
 */
async function runOptimizationFlow() {
  const button = $('#optimizeBtn');
  button.disabled = true;
  button.innerHTML = `
    <span class="badge-dot" style="animation: pulse 1s infinite;"></span>
    <span>Optimizing resume content...</span>
  `;

  try {
    const response = await fetch(`/api/resumes/${resultData.id}/optimize`, { method: 'POST' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Resume optimization failed.');

    resultData.optimized_resume = data.optimized_resume;
    setWorkflowStep(4); // Step 5: Optimize

    const panel = $('#optimizationPanel');
    panel.innerHTML = `
      <div class="ai-card-heading">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
        <h3 class="ai-card-title">Content Optimized</h3>
      </div>
      <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">
        ${escapeHtml(data.optimization_method)}
      </p>

      <!-- Template Selection Cards -->
      <div class="template-selection-container">
        <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 12px;">Choose Document Template</h4>
        <div class="template-cards-row">
          <!-- Professional Template -->
          <div class="template-card selected" data-template="professional">
            <div class="template-card-header">
              <span class="template-card-title">Professional</span>
              <input type="radio" name="templateRadio" checked>
            </div>
            <p class="template-card-desc">Modern sans-serif typography, teal headings, airy spacing.</p>
            <div class="mini-resume-preview theme-professional">
              <div class="mini-name">${escapeHtml(resultData.resume_analysis.personal_info?.name || 'Alex Morgan')}</div>
              <div class="mini-rule"></div>
              <div class="mini-line mid" style="margin: 0 auto 6px;"></div>
              <div class="mini-line long"></div>
              <div class="mini-line mid"></div>
              <div class="mini-line short"></div>
            </div>
          </div>

          <!-- Corporate Template -->
          <div class="template-card" data-template="corporate">
            <div class="template-card-header">
              <span class="template-card-title">Corporate</span>
              <input type="radio" name="templateRadio">
            </div>
            <p class="template-card-desc">Formal executive serif styling, navy divider rules, compact layout.</p>
            <div class="mini-resume-preview theme-corporate">
              <div class="mini-name">${escapeHtml(resultData.resume_analysis.personal_info?.name || 'Alex Morgan')}</div>
              <div class="mini-rule"></div>
              <div class="mini-line long"></div>
              <div class="mini-line long"></div>
              <div class="mini-line mid"></div>
              <div class="mini-line short"></div>
            </div>
          </div>
          <!-- Finance Template -->
          <div class="template-card" data-template="finance">
            <div class="template-card-header">
              <span class="template-card-title">Finance</span>
              <input type="radio" name="templateRadio">
            </div>
            <p class="template-card-desc">Navy styling, compact spacing, and finance focused section ordering.</p>
            <div class="mini-resume-preview theme-corporate">
              <div class="mini-name">${escapeHtml(resultData.resume_analysis.personal_info?.name || 'Alex Morgan')}</div>
              <div class="mini-rule"></div>
              <div class="mini-line long"></div>
              <div class="mini-line mid"></div>
              <div class="mini-line short"></div>
            </div>
          </div>

          <!-- Fresher Template -->
          <div class="template-card" data-template="fresher">
            <div class="template-card-header">
              <span class="template-card-title">Fresher</span>
              <input type="radio" name="templateRadio">
            </div>
            <p class="template-card-desc">Education and projects first, with a centered header.</p>
            <div class="mini-resume-preview theme-fresher">
              <div class="mini-name">${escapeHtml(resultData.resume_analysis.personal_info?.name || 'Alex Morgan')}</div>
              <div class="mini-rule"></div>
              <div class="mini-line mid"></div>
              <div class="mini-line long"></div>
              <div class="mini-line short"></div>
            </div>
          </div>
        </div>

        <button class="app-btn primary-btn" id="generateDocBtn">
          <span>Generate Selected Version</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </button>
      </div>
    `;

    // Handle template card clicks
    $$('.template-card').forEach((card) => {
      card.addEventListener('click', () => {
        $$('.template-card').forEach((c) => c.classList.remove('selected'));
        card.classList.add('selected');
        card.querySelector('input').checked = true;
        templateId = card.dataset.template;
      });
    });

    $('#generateDocBtn').onclick = generateFinalDocuments;
  } catch (error) {
    toast(error.message);
    button.disabled = false;
    button.innerHTML = '<span>Optimize Resume</span>';
  }
}

/**
 * Step 6: Generate Final Documents & Display Completion State
 */
async function generateFinalDocuments() {
  const button = $('#generateDocBtn');
  button.disabled = true;
  button.innerHTML = '<span>Generating ATS-friendly DOCX & PDF...</span>';

  try {
    const body = new FormData();
    body.append('template_id', templateId);
    const response = await fetch(`/api/resumes/${resultData.id}/generate`, { method: 'POST', body });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Document generation failed.');

    generatedData = data;
    setWorkflowStep(5); // Step 6: Preview / Ready

    const previewArea = $('#previewArea');
    previewArea.innerHTML = `
      <!-- Simple Completion Banner Card -->
      <div class="completion-banner-card">
        <div class="completion-info">
          <div class="completion-icon-circle">✓</div>
          <div>
            <h3 class="completion-heading">Resume ready</h3>
            <p class="completion-subtext">Your optimized resume has been generated.</p>
          </div>
        </div>
        <div class="completion-actions">
          <a class="app-btn secondary-btn" href="${data.docx_url}" download>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            <span>Download DOCX</span>
          </a>
          <a class="app-btn primary-btn" href="${data.pdf_url}" download>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            <span>Download PDF</span>
          </a>
          <button class="app-btn secondary-btn" id="newResumeBtn">
            <span>Create another resume</span>
          </button>
        </div>
      </div>

      <!-- Live Interactive Document Preview -->
      <div class="resume-preview-container">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
          <div>
            <h3 style="font-size: 16px; font-weight: 700;">Document Preview</h3>
            <p style="font-size: 12px; color: var(--text-muted);">Formatted with ${escapeHtml(templateId.toUpperCase())} template</p>
          </div>
        </div>
        ${renderResumeDocument(data.preview, templateId)}
      </div>
    `;

    // Handle "Create another resume"
    $('#newResumeBtn').onclick = () => {
      removeResumeFile();
      $('#results').classList.add('hidden');
      $('#workspace').classList.remove('hidden');
      setWorkflowStep(0);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    previewArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = '<span>Generate Selected Version</span>';
  }
}

/**
 * Handle Start Analyze Click
 */
if (analyzeBtn) {
  analyzeBtn.addEventListener('click', async () => {
    if (!selectedFiles.length) return;

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = `
      <span class="badge-dot" style="animation: pulse 1s infinite;"></span>
      <span>Analyzing resume & matching requirements...</span>
    `;
    clearError();

    try {
      const submittedSource = activeSource;
      const submittedJdKey = submittedSource === 'paste' ? pasteJdText.value.trim()
        : submittedSource === 'upload' ? jdFileInput.files[0]
          : submittedSource === 'external' ? customJobId.value.trim() : jobSelect.value;
      const body = new FormData();
      if (selectedFiles.length === 1) body.append('file', selectedFiles[0]);
      else selectedFiles.forEach(file => body.append('files', file));
      body.append('source', activeSource);
      if (activeSource === 'paste') {
        const text = pasteJdText.value.trim();
        if (!text) throw new Error('Paste a job description before analyzing.');
        body.append('jd_text', text);
      } else if (activeSource === 'upload') {
        if (!jdFileInput.files[0]) throw new Error('Upload a job description before analyzing.');
        body.append('jd_file', jdFileInput.files[0]);
      } else {
        const jobId = activeSource === 'external' ? customJobId.value.trim() : jobSelect.value;
        if (!jobId) throw new Error('Select or enter a job ID before analyzing.');
        body.append('job_id', jobId);
      }

      const response = await fetch(selectedFiles.length === 1 ? '/api/optimize-resume' : '/api/optimize-resumes', { method: 'POST', body });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Could not analyze resume.');
      }

      const stillSelected = activeSource === submittedSource && (submittedSource === 'paste' ? pasteJdText.value.trim() === submittedJdKey
        : submittedSource === 'upload' ? jdFileInput.files[0] === submittedJdKey
          : submittedSource === 'external' ? customJobId.value.trim() === submittedJdKey : jobSelect.value === submittedJdKey);
      if (stillSelected && data.job) {
        const processedJob = { ...data.job };
        if (submittedSource === 'paste' || (submittedSource === 'upload' && !/\.json$/i.test(submittedJdKey?.name || ''))) {
          processedJob.title = deriveJobTitle(processedJob.description);
        }
        showJobPreview(processedJob);
      }

      if (selectedFiles.length === 1) {
        resultData = data;
        renderAnalysis(data);
        return;
      }
      const results = data.results || [];
      $('#workspace').classList.add('hidden');
      const panel = $('#results');
      panel.classList.remove('hidden');
      panel.innerHTML = `<section class="app-card"><div class="card-eyebrow">OPTIMIZATION COMPLETE</div><h2 class="card-title">Resume results</h2>${results.map(item => `<article class="app-card" style="margin-top:16px"><h3>${escapeHtml(item.original_filename)}</h3><p>${item.status === 'completed' ? '✓ Successfully optimized' : `✗ Failed: ${escapeHtml(item.error || 'Processing failed')}`}</p>${item.status === 'completed' ? `<a class="app-btn primary-btn" href="${escapeHtml(item.docx_url)}">Download ${escapeHtml(item.optimized_docx)}</a> <a class="app-btn" href="${escapeHtml(item.pdf_url)}">Download ${escapeHtml(item.optimized_pdf)}</a>` : ''}</article>`).join('')}</section>`;
      setWorkflowStep(5);
    } catch (error) {
      setError(error.message);
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = `
        <span>Analyze Resume & Match</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
      `;
    }
  });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  initJobCatalogue();
});
