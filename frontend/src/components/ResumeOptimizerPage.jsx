import React, { useEffect, useRef, useState } from 'react';

/* ===============================================================
   Styles: original UJMA theme, scoped to .ro-page
   =============================================================== */

const ROP_STYLES = `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ==========================================================================
   FINXL Resume Optimizer: original UJMA theme, scoped to .ro-page
   ========================================================================== */

.ro-page {
  --bg-card: #FFFFFF; --bg-subtle: #F8FAFC; --bg-hover: #F1F5F9;
  --text-primary: #0F172A; --text-secondary: #475569; --text-muted: #64748B; --text-subtle: #94A3B8;
  --border-light: #E2E8F0; --border-subtle: #CBD5E1;
  --accent-primary: #2563EB; --accent-hover: #1D4ED8; --accent-dark: #1E40AF; --accent-light: #EFF6FF; --accent-border: #BFDBFE;
  --status-matched-bg: #ECFDF5; --status-matched-text: #065F46; --status-matched-border: #A7F3D0;
  --status-related-bg: #FFFBEB; --status-related-text: #92400E; --status-related-border: #FDE68A;
  --status-missing-bg: #F8FAFC; --status-missing-text: #64748B; --status-missing-border: #E2E8F0;
  --danger-bg: #FEF2F2; --danger-text: #991B1B; --danger-border: #FECACA;
  --radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px; --radius-pill: 9999px;
  --shadow-subtle: 0 1px 3px 0 rgba(0,0,0,0.04), 0 1px 2px -1px rgba(0,0,0,0.02);
  --shadow-card: 0 4px 6px -1px rgba(0,0,0,0.04), 0 2px 4px -2px rgba(0,0,0,0.02);
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: var(--text-primary); font-family: var(--font-sans); font-size: 14px; line-height: 1.5;
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
}
.ro-page *, .ro-page *::before, .ro-page *::after { box-sizing: border-box; }
.ro-page :where(h1,h2,h3,h4,h5,h6,p,ul,ol) { margin: 0; padding: 0; }
.ro-page :where(button, input, select, textarea) { font-family: inherit; }
.ro-page .hidden { display: none !important; }
.ro-page .text-subtle { color: var(--text-subtle); }

.ro-page .main-workspace { padding: 24px 0 48px; }
.ro-page .workspace-container { width: 100%; max-width: 1120px; margin: 0 auto; padding: 0 24px; }

/* Welcome */
.ro-page .welcome-section { padding: 8px 0 20px; }
.ro-page .welcome-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; color: var(--accent-primary); background: var(--accent-light); border: 1px solid var(--accent-border); padding: 4px 12px; border-radius: var(--radius-pill); margin-bottom: 12px; }
.ro-page .badge-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent-primary); display: inline-block; }
.ro-page .badge-dot.pulse { animation: ro-pulse 1s infinite; background: currentColor; }
@keyframes ro-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
.ro-page .welcome-heading { font-size: 26px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.5px; margin-bottom: 6px; }
.ro-page .welcome-subtext { font-size: 14px; color: var(--text-muted); max-width: 680px; line-height: 1.5; }

/* Stepper */
.ro-page .workflow-stepper { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 12px 20px; margin-bottom: 24px; box-shadow: var(--shadow-subtle); }
.ro-page .stepper-track { display: flex; align-items: center; justify-content: space-between; }
.ro-page .step-item { display: flex; align-items: center; gap: 8px; color: var(--text-subtle); font-size: 13px; font-weight: 500; cursor: default; transition: all 0.2s ease; }
.ro-page .step-num { font-size: 11px; font-weight: 700; padding: 3px 7px; border-radius: 6px; background: var(--bg-subtle); color: var(--text-subtle); border: 1px solid var(--border-light); }
.ro-page .step-item.active { color: var(--accent-primary); font-weight: 600; }
.ro-page .step-item.active .step-num { background: var(--accent-primary); color: #FFFFFF; border-color: var(--accent-primary); }
.ro-page .step-item.done { color: var(--text-secondary); }
.ro-page .step-item.done .step-num { background: #ECFDF5; color: #059669; border-color: #A7F3D0; }
.ro-page .step-connector { flex: 1; height: 1px; background: var(--border-light); margin: 0 12px; }

/* Input grid */
.ro-page .workspace-cards-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: start; }
.ro-page .app-card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-subtle); }
.ro-page .card-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 0.8px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px; }
.ro-page .card-title { font-size: 18px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.3px; margin-bottom: 4px; }
.ro-page .card-subtitle { font-size: 13px; color: var(--text-muted); margin-bottom: 18px; }

.ro-page .source-options-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 18px; }
.ro-page .source-card { border: 1px solid var(--border-light); border-radius: var(--radius-sm); padding: 10px 8px; text-align: center; cursor: pointer; background: var(--bg-card); transition: all 0.15s ease; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.ro-page .source-card:hover { border-color: var(--accent-border); background: var(--accent-light); }
.ro-page .source-card.selected { border-color: var(--accent-primary); background: var(--accent-light); box-shadow: 0 0 0 1px var(--accent-primary); }
.ro-page .source-icon { color: var(--accent-primary); display: grid; place-items: center; }
.ro-page .source-meta b { display: block; font-size: 12px; font-weight: 600; color: var(--text-primary); }
.ro-page .source-meta small { display: block; font-size: 10px; color: var(--text-muted); margin-top: 1px; white-space: nowrap; }

.ro-page .source-input-container { margin-bottom: 16px; }
.ro-page .source-panel { display: flex; flex-direction: column; gap: 6px; }
.ro-page .input-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.ro-page .form-select, .ro-page .form-input, .ro-page .form-textarea { width: 100%; padding: 9px 12px; font-family: inherit; font-size: 13.5px; color: var(--text-primary); background: #FFFFFF; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); outline: none; transition: border-color 0.15s ease; }
.ro-page .form-select:focus, .ro-page .form-input:focus, .ro-page .form-textarea:focus { border-color: var(--accent-primary); box-shadow: 0 0 0 3px rgba(37,99,235,0.12); }
.ro-page .mini-dropzone { border: 1px dashed var(--border-subtle); border-radius: var(--radius-sm); padding: 20px; text-align: center; background: var(--bg-subtle); color: var(--text-muted); font-size: 12px; cursor: pointer; }
.ro-page .mini-dropzone:hover { border-color: var(--accent-primary); background: var(--accent-light); }

.ro-page .job-preview-box { background: var(--bg-subtle); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 16px; }
.ro-page .job-preview-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
.ro-page .job-preview-title { font-size: 15px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px; }
.ro-page .job-preview-company { font-size: 12px; color: var(--text-muted); }
.ro-page .dot-sep { margin: 0 4px; color: var(--border-subtle); }
.ro-page .job-preview-company strong { color: var(--text-secondary); }
.ro-page .role-badge { font-size: 11px; font-weight: 600; padding: 2px 8px; background: #FFFFFF; border: 1px solid var(--border-light); border-radius: var(--radius-pill); color: var(--text-secondary); white-space: nowrap; }
.ro-page .job-preview-desc { font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 10px; white-space: pre-wrap; max-height: 200px; overflow-y: auto; }
.ro-page .job-preview-footer { display: flex; justify-content: flex-end; }
.ro-page .inline-link { font-size: 12px; font-weight: 600; color: var(--accent-primary); text-decoration: none; background: none; border: 0; cursor: pointer; padding: 0; }
.ro-page .inline-link:hover { text-decoration: underline; }

.ro-page .upload-dropzone { border: 2px dashed var(--border-subtle); background: var(--bg-subtle); border-radius: var(--radius-md); padding: 28px 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; cursor: pointer; transition: all 0.2s ease; text-align: center; margin-bottom: 16px; }
.ro-page .upload-dropzone:hover, .ro-page .upload-dropzone.drag { border-color: var(--accent-primary); background: var(--accent-light); }
.ro-page .upload-dropzone input[type="file"] { display: none; }
.ro-page .upload-icon-circle { width: 44px; height: 44px; border-radius: 50%; background: #FFFFFF; border: 1px solid var(--border-light); display: grid; place-items: center; color: var(--accent-primary); box-shadow: var(--shadow-subtle); }
.ro-page .dropzone-text { display: flex; flex-direction: column; gap: 2px; }
.ro-page .dropzone-primary-text { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.ro-page .dropzone-secondary-text { font-size: 12px; color: var(--text-muted); }
.ro-page .browse-pill { font-size: 12px; font-weight: 600; color: var(--accent-primary); background: #FFFFFF; border: 1px solid var(--accent-border); padding: 5px 14px; border-radius: var(--radius-pill); transition: background 0.15s ease; }
.ro-page .upload-dropzone:hover .browse-pill { background: var(--accent-primary); color: #FFFFFF; }

.ro-page .uploaded-file-card { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; background: #FFFFFF; border: 1px solid var(--border-light); border-radius: var(--radius-md); box-shadow: var(--shadow-subtle); margin-bottom: 16px; }
.ro-page .file-card-info { display: flex; align-items: center; gap: 12px; }
.ro-page .file-icon-box { width: 36px; height: 36px; border-radius: var(--radius-sm); background: var(--accent-light); color: var(--accent-primary); display: grid; place-items: center; }
.ro-page .file-card-name { font-size: 13.5px; font-weight: 600; color: var(--text-primary); max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ro-page .file-card-sub { font-size: 11.5px; color: var(--text-muted); }
.ro-page .file-card-actions { display: flex; align-items: center; gap: 8px; }
.ro-page .btn-text-action { background: none; border: none; font-size: 12px; font-weight: 600; color: var(--accent-primary); cursor: pointer; padding: 4px 6px; border-radius: 4px; }
.ro-page .btn-text-action:hover { background: var(--bg-subtle); }
.ro-page .btn-text-action.danger { color: #DC2626; }
.ro-page .action-divider { color: var(--border-subtle); font-size: 12px; }

.ro-page .app-btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 20px; font-family: inherit; font-size: 13.5px; font-weight: 600; border-radius: var(--radius-sm); cursor: pointer; transition: all 0.15s ease; text-decoration: none; border: 1px solid transparent; }
.ro-page .primary-btn { background: var(--accent-primary); color: #FFFFFF; }
.ro-page .primary-btn:hover:not(:disabled) { background: var(--accent-hover); box-shadow: 0 2px 4px rgba(37,99,235,0.2); }
.ro-page .secondary-btn { background: #FFFFFF; border-color: var(--border-light); color: var(--text-secondary); }
.ro-page .secondary-btn:hover:not(:disabled) { background: var(--bg-subtle); border-color: var(--border-subtle); color: var(--text-primary); }
.ro-page .full-width { width: 100%; }
.ro-page .app-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ro-page .privacy-note { display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--text-muted); margin-top: 14px; }
.ro-page .alert-box { padding: 10px 14px; border-radius: var(--radius-sm); font-size: 12.5px; margin-bottom: 12px; }
.ro-page .error-alert { background: var(--danger-bg); color: var(--danger-text); border: 1px solid var(--danger-border); }

/* Results */
.ro-page .results-layout { display: flex; flex-direction: column; gap: 20px; }
.ro-page .result-header-card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 20px 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; box-shadow: var(--shadow-subtle); }
.ro-page .result-header-info h2 { font-size: 20px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px; }
.ro-page .result-header-info p { font-size: 13px; color: var(--text-muted); }
.ro-page .metric-summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.ro-page .metric-card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 16px 20px; box-shadow: var(--shadow-subtle); }
.ro-page .metric-card strong { display: block; font-size: 24px; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
.ro-page .metric-card span { font-size: 12px; color: var(--text-muted); font-weight: 500; }
.ro-page .metric-card.matched strong { color: #059669; }
.ro-page .metric-card.related strong { color: #D97706; }
.ro-page .metric-card.missing strong { color: var(--text-muted); }

.ro-page .analysis-dashboard-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.ro-page .analysis-card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 20px; box-shadow: var(--shadow-subtle); }
.ro-page .analysis-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; border-bottom: 1px solid var(--border-light); padding-bottom: 10px; }
.ro-page .analysis-card-title { font-size: 14px; font-weight: 700; color: var(--text-primary); text-transform: uppercase; letter-spacing: 0.5px; }
.ro-page .count-pill { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: var(--radius-pill); background: var(--bg-subtle); color: var(--text-secondary); }
.ro-page .analysis-list { list-style: none; display: flex; flex-direction: column; gap: 8px; font-size: 13px; color: var(--text-secondary); }
.ro-page .analysis-list li { position: relative; padding-left: 18px; line-height: 1.5; }
.ro-page .analysis-list li::before { content: "•"; position: absolute; left: 4px; color: var(--accent-primary); font-weight: bold; }
.ro-page .responsibilities-numbered-list { list-style: decimal; padding-left: 20px; display: flex; flex-direction: column; gap: 8px; font-size: 13px; color: var(--text-secondary); line-height: 1.5; }

.ro-page .categorized-panel { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 20px 24px; box-shadow: var(--shadow-subtle); }
.ro-page .categorized-group { margin-bottom: 14px; }
.ro-page .categorized-group:last-child { margin-bottom: 0; }
.ro-page .categorized-group h5 { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: var(--text-muted); margin-bottom: 8px; }
.ro-page .chips-cluster { display: flex; flex-wrap: wrap; gap: 6px; }
.ro-page .chip-tag { font-size: 12px; font-weight: 500; padding: 4px 10px; border-radius: var(--radius-pill); background: var(--bg-subtle); color: var(--text-primary); border: 1px solid var(--border-light); }
.ro-page .chip-tag.primary { background: var(--accent-light); color: var(--accent-primary); border-color: var(--accent-border); }
.ro-page .chip-tag.matched { background: var(--status-matched-bg); color: var(--status-matched-text); border-color: var(--status-matched-border); }
.ro-page .chip-tag.related { background: var(--status-related-bg); color: var(--status-related-text); border-color: var(--status-related-border); }
.ro-page .chip-tag.missing { background: var(--status-missing-bg); color: var(--status-missing-text); border-color: var(--status-missing-border); }

.ro-page .matching-card-container { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-subtle); }
.ro-page .matching-header { margin-bottom: 16px; }
.ro-page .matching-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.ro-page .matching-header p { font-size: 13px; color: var(--text-muted); }
.ro-page .match-sections-list { display: flex; flex-direction: column; gap: 16px; }
.ro-page .match-category-box { border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 16px; }
.ro-page .match-category-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.ro-page .match-status-heading { display: flex; align-items: center; gap: 8px; }
.ro-page .status-badge { font-size: 11px; font-weight: 700; letter-spacing: 0.5px; padding: 3px 9px; border-radius: var(--radius-pill); text-transform: uppercase; }
.ro-page .status-badge.matched { background: var(--status-matched-bg); color: var(--status-matched-text); border: 1px solid var(--status-matched-border); }
.ro-page .status-badge.related { background: var(--status-related-bg); color: var(--status-related-text); border: 1px solid var(--status-related-border); }
.ro-page .status-badge.not-detected { background: var(--status-missing-bg); color: var(--status-missing-text); border: 1px solid var(--status-missing-border); }
.ro-page .match-disclaimer-note { font-size: 12px; color: var(--text-muted); font-style: italic; margin-bottom: 12px; background: var(--bg-subtle); padding: 8px 12px; border-radius: var(--radius-sm); border-left: 3px solid var(--border-subtle); }
.ro-page .match-rows-list { display: flex; flex-direction: column; gap: 8px; }
.ro-page .match-item-row { display: flex; flex-direction: column; gap: 6px; padding: 10px 12px; border-radius: var(--radius-sm); background: var(--bg-subtle); border: 1px solid var(--border-light); }
.ro-page .match-item-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.ro-page .match-item-name { font-size: 13.5px; font-weight: 600; color: var(--text-primary); }
.ro-page .match-item-meta { font-size: 11px; color: var(--text-muted); }
.ro-page .match-evidence-details { font-size: 12px; color: var(--text-secondary); }
.ro-page .match-evidence-details summary { color: var(--accent-primary); cursor: pointer; font-weight: 500; }
.ro-page .match-evidence-details ul { list-style: disc; margin: 6px 0 2px; padding-left: 20px; }
.ro-page .match-evidence-details li { margin-bottom: 4px; color: var(--text-secondary); line-height: 1.4; }

.ro-page .quality-review-panel { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 20px 24px; box-shadow: var(--shadow-subtle); }
.ro-page .quality-issues-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 12px; }
.ro-page .quality-issue-badge { border: 1px solid var(--border-light); border-radius: var(--radius-sm); padding: 10px 12px; background: var(--bg-subtle); display: flex; align-items: flex-start; gap: 8px; font-size: 12px; }
.ro-page .issue-sev { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 1px 6px; border-radius: 4px; }
.ro-page .issue-sev.high { background: var(--danger-bg); color: var(--danger-text); }
.ro-page .issue-sev.medium { background: var(--status-related-bg); color: var(--status-related-text); }
.ro-page .issue-sev.low { background: var(--bg-hover); color: var(--text-secondary); }

/* Optimize card */
.ro-page .ai-optimize-card { background: var(--bg-card); border: 1px solid var(--accent-border); border-radius: var(--radius-lg); padding: 28px; box-shadow: var(--shadow-card); position: relative; overflow: hidden; }
.ro-page .ai-optimize-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, var(--accent-primary), #6366F1); }
.ro-page .ai-card-heading { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; color: var(--accent-primary); }
.ro-page .ai-card-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.ro-page .ai-card-desc { font-size: 13.5px; color: var(--text-secondary); margin-bottom: 18px; max-width: 680px; }
.ro-page .ai-features-checklist { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 20px; }
.ro-page .ai-feature-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-primary); font-weight: 500; }
.ro-page .check-green { color: #059669; font-weight: bold; }
.ro-page .ai-guarantee-callout { background: var(--accent-light); border: 1px solid var(--accent-border); border-radius: var(--radius-sm); padding: 10px 14px; font-size: 12.5px; color: var(--accent-dark); margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }

/* Templates */
.ro-page .template-selection-container { margin: 20px 0; }
.ro-page .template-cards-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.ro-page .template-category-label { grid-column: 1 / -1; margin: 4px 0 -8px; color: var(--text-muted); font-size: 11px; font-weight: 700; letter-spacing: 1.2px; }
.ro-page .template-card { border: 2px solid var(--border-light); border-radius: var(--radius-md); padding: 18px; cursor: pointer; background: var(--bg-card); transition: all 0.2s ease; display: flex; flex-direction: column; }
.ro-page .template-card:hover { border-color: var(--accent-border); box-shadow: var(--shadow-card); }
.ro-page .template-card.selected { border-color: var(--accent-primary); background: var(--accent-light); box-shadow: 0 0 0 1px var(--accent-primary); }
.ro-page .template-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.ro-page .template-card-title { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.ro-page .template-card-desc { font-size: 12px; color: var(--text-muted); margin-bottom: 14px; }

.ro-page .mini-resume-preview { background: #FFFFFF; border: 1px solid var(--border-light); border-radius: 6px; padding: 14px; height: 180px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-size: 9px; line-height: 1.35; }
.ro-page .mini-resume-preview.theme-professional { font-family: var(--font-sans); border-top: 3px solid #0D766E; text-align: center; }
.ro-page .mini-resume-preview.theme-professional .mini-name { font-weight: 700; font-size: 12px; color: #0D5D58; }
.ro-page .mini-resume-preview.theme-professional .mini-rule { height: 1px; background: #D8E8E2; margin: 6px 0; }
.ro-page .mini-resume-preview.theme-corporate { font-family: Georgia, 'Times New Roman', serif; text-align: left; }
.ro-page .mini-resume-preview.theme-corporate .mini-name { font-weight: 700; font-size: 12px; color: #1E3A5F; }
.ro-page .mini-resume-preview.theme-corporate .mini-rule { height: 2px; background: #253D55; margin: 6px 0; }
.ro-page .mini-resume-preview.theme-finance { font-family: Calibri, 'Segoe UI', Candara, sans-serif; text-align: left; }
.ro-page .mini-resume-preview.theme-finance .mini-name { font-weight: 700; font-size: 12px; color: #17365D; }
.ro-page .mini-resume-preview.theme-finance .mini-rule { height: 2px; background: #17365D; margin: 6px 0; }
.ro-page .mini-resume-preview.theme-fresher { font-family: var(--font-sans); border-top: 3px solid #6B4C7A; text-align: center; }
.ro-page .mini-resume-preview.theme-fresher .mini-name { font-weight: 700; font-size: 12px; color: #6B4C7A; }
.ro-page .mini-resume-preview.theme-fresher .mini-rule { height: 1px; background: #E9D5FF; margin: 6px 0; }
.ro-page .mini-resume-preview.theme-sidebar, .ro-page .mini-resume-preview.theme-sidebar_corporate { position: relative; padding-left: 36%; text-align: left; }
.ro-page .mini-resume-preview.theme-sidebar::before, .ro-page .mini-resume-preview.theme-sidebar_corporate::before { content: ''; position: absolute; inset: 0 auto 0 0; width: 31%; background: #F3F5F7; }
.ro-page .mini-resume-preview.theme-sidebar_corporate::before { background: #17365D; }
.ro-page .mini-resume-preview.theme-sidebar .mini-rule, .ro-page .mini-resume-preview.theme-sidebar_corporate .mini-rule { height: 1px; background: #CBD5E1; margin: 6px 0; }
.ro-page .mini-line { height: 4px; background: #E2E8F0; border-radius: 2px; margin: 4px 0; }
.ro-page .mini-line.short { width: 50%; }
.ro-page .mini-line.mid { width: 75%; }
.ro-page .mini-line.long { width: 90%; }

/* Completion banner */
.ro-page .completion-banner-card { background: var(--bg-card); border: 1px solid #A7F3D0; border-radius: var(--radius-lg); padding: 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; box-shadow: var(--shadow-subtle); margin-bottom: 20px; }
.ro-page .completion-info { display: flex; align-items: center; gap: 16px; }
.ro-page .completion-icon-circle { width: 44px; height: 44px; border-radius: 50%; background: #ECFDF5; color: #059669; display: grid; place-items: center; font-size: 20px; font-weight: bold; }
.ro-page .completion-heading { font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px; }
.ro-page .completion-subtext { font-size: 13px; color: var(--text-secondary); }
.ro-page .completion-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }

/* Resume document preview */
.ro-page .resume-preview-container { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-subtle); overflow-x: auto; }
.ro-page .resume-live-selection-preview { margin: 18px 0; overflow-x: auto; }
.ro-page .resume-preview-sheet { background: #FFFFFF; border: 1px solid var(--border-light); border-radius: var(--radius-sm); padding: 32px 36px; max-width: 800px; margin: 0 auto; box-shadow: 0 2px 8px rgba(0,0,0,0.06); font-size: 12.5px; line-height: 1.55; color: var(--text-primary); }
.ro-page .resume-preview-sheet header { margin-bottom: 16px; }
.ro-page .resume-preview-sheet header h2 { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.ro-page .resume-preview-sheet .resume-contact { font-size: 11.5px; color: var(--text-muted); }
.ro-page .resume-preview-sheet h3 { font-size: 13px; font-weight: 700; margin: 16px 0 8px; text-transform: uppercase; letter-spacing: 0.5px; }
.ro-page .resume-preview-sheet.theme-professional { font-family: var(--font-sans); border-top: 4px solid #0D766E; }
.ro-page .resume-preview-sheet.theme-professional header { text-align: center; }
.ro-page .resume-preview-sheet.theme-professional header h2 { color: #0D5D58; }
.ro-page .resume-preview-sheet.theme-professional h3 { color: #0D766E; border-bottom: 1px solid #D8E8E2; padding-bottom: 4px; }
.ro-page .resume-preview-sheet.theme-corporate { font-family: Georgia, 'Times New Roman', serif; }
.ro-page .resume-preview-sheet.theme-corporate header { text-align: left; border-bottom: 2px solid #253D55; padding-bottom: 8px; }
.ro-page .resume-preview-sheet.theme-corporate header h2 { color: #1E3A5F; }
.ro-page .resume-preview-sheet.theme-corporate h3 { color: #253D55; border-bottom: 1px solid #CBD5E1; padding-bottom: 4px; }
.ro-page .resume-preview-sheet.theme-finance { font-family: Calibri, 'Segoe UI', Candara, sans-serif; }
.ro-page .resume-preview-sheet.theme-finance header { text-align: left; border-bottom: 2px solid #17365D; padding-bottom: 8px; }
.ro-page .resume-preview-sheet.theme-finance header h2 { color: #17365D; }
.ro-page .resume-preview-sheet.theme-finance h3 { color: #17365D; border-bottom: 1px solid #CBD5E1; padding-bottom: 4px; }
.ro-page .resume-preview-sheet.theme-fresher { font-family: var(--font-sans); border-top: 4px solid #6B4C7A; }
.ro-page .resume-preview-sheet.theme-fresher header { text-align: center; }
.ro-page .resume-preview-sheet.theme-fresher header h2 { color: #6B4C7A; }
.ro-page .resume-preview-sheet.theme-fresher h3 { color: #6B4C7A; border-bottom: 1px solid #E9D5FF; padding-bottom: 4px; }
.ro-page .resume-preview-sheet .resume-entry { margin-bottom: 12px; }
.ro-page .resume-preview-sheet .entry-heading { display: flex; justify-content: space-between; font-weight: 700; }
.ro-page .resume-preview-sheet .entry-subheading { font-weight: 600; margin-top: 2px; }
.ro-page .resume-preview-sheet ul { list-style: disc; padding-left: 20px; margin: 4px 0 8px; }
.ro-page .resume-preview-sheet li { margin-bottom: 3px; }
.ro-page .resume-preview-sheet .project-entry { margin-bottom: 14px; }
.ro-page .resume-preview-sheet .project-heading { display: flex; justify-content: space-between; align-items: baseline; font-size: 13.5px; font-weight: 700; color: #0F172A; margin-top: 10px; margin-bottom: 4px; }
.ro-page .resume-preview-sheet .project-heading span { font-weight: 700; color: #0F172A; letter-spacing: -0.01em; }
.ro-page .resume-preview-sheet .project-subheading { font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 4px; }
.ro-page .resume-preview-sheet .project-tech { font-size: 11.5px; color: #475569; margin: 2px 0 6px; }
.ro-page .resume-preview-sheet .project-description { font-size: 12px; line-height: 1.55; color: #334155; margin: 3px 0 6px; }
.ro-page .resume-preview-sheet .project-bullets { list-style-type: disc; padding-left: 20px; margin: 4px 0 10px; }
.ro-page .resume-preview-sheet .project-bullets li { font-size: 12px; line-height: 1.55; color: #334155; margin-bottom: 4px; word-break: break-word; overflow: visible; }
.ro-page .resume-preview-sheet .project-bullets li strong { font-weight: 600; color: #0F172A; }
.ro-page .resume-preview-sheet.theme-professional .project-heading span { color: #0D5D58; }
.ro-page .resume-preview-sheet.theme-corporate .project-heading span { color: #1E3A5F; }
.ro-page .resume-preview-sheet.theme-finance .project-heading span { color: #17365D; }
.ro-page .resume-preview-sheet.theme-fresher .project-heading span { color: #6B4C7A; }

.ro-page .resume-preview-sheet.theme-sidebar, .ro-page .resume-preview-sheet.theme-sidebar_corporate { display: grid; grid-template-columns: 30% 70%; width: 794px; min-height: 1123px; max-width: none; padding: 0; border-radius: 0; overflow: hidden; font-family: Arial, Helvetica, sans-serif; font-size: 11px; line-height: 1.45; border-top: 0; }
.ro-page .resume-sidebar { padding: 40px 20px; background: #F3F5F7; color: #222; overflow-wrap: anywhere; }
.ro-page .theme-sidebar_corporate .resume-sidebar { background: #17365D; color: #D9E2F3; }
.ro-page .resume-identity h2 { color: #222; font-size: 25px; line-height: 1.08; overflow-wrap: anywhere; margin-bottom: 9px; }
.ro-page .theme-sidebar_corporate .resume-identity h2 { color: #fff; }
.ro-page .resume-target-role { margin-bottom: 22px; color: #17365D; font-weight: 700; font-size: 10px; text-transform: uppercase; }
.ro-page .theme-sidebar_corporate .resume-target-role { color: #D9E2F3; }
.ro-page .resume-side-section { margin: 20px 0; }
.ro-page .resume-side-section h3 { margin: 0 0 8px; padding-bottom: 5px; border-bottom: 1px solid rgba(23,54,93,.22); color: #17365D; font-size: 10px; letter-spacing: 1px; text-transform: uppercase; }
.ro-page .theme-sidebar_corporate .resume-side-section h3 { color: #D9E2F3; border-color: rgba(217,226,243,.38); }
.ro-page .resume-preview-sheet .resume-side-section ul { list-style: none; padding: 0; margin: 0; }
.ro-page .resume-side-section li { margin: 0 0 7px; overflow-wrap: anywhere; }
.ro-page .theme-sidebar_corporate .resume-side-section li { color: #D9E2F3; }
.ro-page .resume-main-column { min-width: 0; padding: 40px 38px; background: #fff; color: #222; }
.ro-page .resume-main-column h3 { color: #17365D; border-bottom: 1px solid #C9D3DE; padding-bottom: 5px; margin: 16px 0 8px; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; break-after: avoid; }
.ro-page .resume-main-column .resume-entry { break-inside: avoid; }
.ro-page .resume-main-column p, .ro-page .resume-main-column li { overflow-wrap: anywhere; }
.ro-page .resume-preview-sheet.theme-sidebar .project-heading span, .ro-page .resume-preview-sheet.theme-sidebar_corporate .project-heading span { color: #17365D; }

/* Toast */
.ro-page .toast-notification { position: fixed; bottom: 24px; right: 24px; background: #0F172A; color: #FFFFFF; padding: 12px 18px; border-radius: var(--radius-sm); font-size: 13px; box-shadow: 0 8px 16px rgba(0,0,0,0.15); z-index: 99; white-space: pre-wrap; max-width: 420px; }

/* Responsive */
@media (max-width: 900px) {
  .ro-page .workspace-cards-grid, .ro-page .analysis-dashboard-grid, .ro-page .template-cards-row { grid-template-columns: 1fr; }
  .ro-page .metric-summary-grid, .ro-page .source-options-grid { grid-template-columns: repeat(2, 1fr); }
  .ro-page .completion-banner-card { flex-direction: column; align-items: flex-start; gap: 16px; }
  .ro-page .completion-actions { width: 100%; justify-content: flex-start; }
}
@media (max-width: 640px) {
  .ro-page .workspace-container { padding: 0 16px; }
  .ro-page .welcome-heading { font-size: 22px; }
  .ro-page .stepper-track { overflow-x: auto; padding-bottom: 4px; }
  .ro-page .step-connector { min-width: 16px; }
  .ro-page .ai-features-checklist, .ro-page .quality-issues-grid { grid-template-columns: 1fr; }
  .ro-page .result-header-card { flex-direction: column; align-items: flex-start; }
}
`;

/* ===============================================================
   Resume document renderer (ported from the original app.js)
   =============================================================== */

// Resume document renderer, ported from the original UJMA app.js.
// Every value is passed through escapeHtml before it is placed in markup,
// so the returned HTML string is safe to render with dangerouslySetInnerHTML.

const escapeHtml = (value = '') =>
  String(value).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const list = (v) => (Array.isArray(v) ? v : []);
const asValues = (v) => (v == null || v === '' ? [] : Array.isArray(v) ? v : [v]);
const skillGroups = (skills = {}) =>
  Object.entries(skills || {}).filter(([, values]) => Array.isArray(values) && values.length);

const RESUME_ACTION_VERBS = new Set([
  'analyzed', 'analysed', 'created', 'performed', 'presented', 'used', 'built', 'developed', 'designed',
  'implemented', 'engineered', 'conducted', 'maintained', 'managed', 'collaborated', 'configured', 'delivered',
  'automated', 'deployed', 'integrated', 'executed', 'evaluated', 'formulated', 'generated', 'identified',
  'monitored', 'optimized', 'organized', 'organised', 'programmed', 'produced', 'reduced', 'resolved', 'reviewed',
  'streamlined', 'supported', 'trained', 'upgraded', 'utilized', 'utilised', 'wrote', 'cleaned', 'assisted', 'led',
  'researched', 'calculated', 'modeled', 'modelled', 'spearheaded', 'established', 'authored', 'administered',
  'architected', 'customized', 'directed', 'facilitated', 'guided', 'improved', 'initiated', 'inspected',
  'instituted', 'mentored', 'orchestrated', 'overhauled', 'planned', 'pioneered', 'restructured', 'supervised',
  'tested', 'transformed', 'validated', 'verified',
]);

function stripOuterMarkdown(text) {
  if (!text) return '';
  let str = String(text).trim();
  if (str.startsWith('**') && str.endsWith('**') && str.length >= 4) str = str.slice(2, -2).trim();
  else if (str.startsWith('*') && str.endsWith('*') && str.length >= 2) str = str.slice(1, -1).trim();
  return str;
}

function cleanHeadingText(text) {
  if (!text) return '';
  let str = stripOuterMarkdown(text);
  str = str.replace(/^([•\-–—]|\*(?!\*))\s*/, '').replace(/^\d+[.)]\s*/, '').trim();
  return escapeHtml(str);
}

function formatInlineMarkdown(text) {
  if (!text) return '';
  let str = String(text).trim();
  str = str.replace(/^([•\-–—]|\*(?!\*))\s*/, '').replace(/^\d+[.)]\s*/, '').trim();
  if (str.startsWith('**') && str.endsWith('**') && str.length >= 4) {
    const inner = str.slice(2, -2);
    if (!inner.includes('**')) str = inner.trim();
  }
  str = escapeHtml(str);
  str = str.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
  str = str.replace(/(^|[^*])\*([^*]+?)\*(?!\*)/g, '$1<em>$2</em>');
  return str;
}

function isBulletLine(rawLine) {
  const line = String(rawLine).trim();
  if (!line) return false;
  if (/^([•\-–—]|\*(?!\*))\s+/.test(line) || /^\d+[.)]\s+/.test(line)) return true;
  const clean = stripOuterMarkdown(line);
  const endsWithPunct = /[.;!]$/.test(clean);
  const firstWord = (clean.match(/^[a-zA-Z]+/)?.[0] || '').toLowerCase();
  if (RESUME_ACTION_VERBS.has(firstWord)) return true;
  return endsWithPunct && clean.length > 25;
}

function parseProjectLines(lines) {
  const projects = [];
  let current = null;
  for (const raw of lines) {
    const line = String(raw || '').trim();
    if (!line) continue;
    if (!isBulletLine(line)) {
      if (!current || current.bullets.length > 0 || current.description) {
        current = { name: cleanHeadingText(line), technologies: [], description: '', bullets: [] };
        projects.push(current);
        continue;
      }
    }
    if (!current) {
      current = { name: cleanHeadingText(line), technologies: [], description: '', bullets: [] };
      projects.push(current);
    } else {
      current.bullets.push(formatInlineMarkdown(line));
    }
  }
  return projects;
}

function normalizeProjects(data) {
  if (!data) return [];
  if (typeof data === 'string') return parseProjectLines(data.split(/\r?\n/).map((l) => l.trim()).filter(Boolean));
  if (!Array.isArray(data) || data.length === 0) return [];
  if (typeof data[0] === 'string') return parseProjectLines(data);

  const isFlat =
    data.length > 1 &&
    data.every((i) => (!i.bullets || !i.bullets.length) && !i.description && (!i.technologies || !i.technologies.length)) &&
    data.some((i) => isBulletLine(i.name || i.title || ''));
  if (isFlat) return parseProjectLines(data.map((i) => i.name || i.title || '').filter(Boolean));

  const results = [];
  for (const item of data) {
    if (!item) continue;
    if (typeof item === 'string') { results.push(...parseProjectLines([item])); continue; }
    const name = cleanHeadingText(item.name || item.project_name || item.title || '');
    const tech = [...asValues(item.technologies), ...asValues(item.technology), ...asValues(item.tech_stack), ...asValues(item.tech)];
    const dates = [item.start_date, item.end_date].filter(Boolean).map(escapeHtml).join(' – ');
    const subtitle = cleanHeadingText(item.subtitle || item.role || '');
    let bullets = [];
    let description = '';
    if (Array.isArray(item.bullets) && item.bullets.length) bullets = item.bullets.map(formatInlineMarkdown).filter(Boolean);
    bullets.push(...[...asValues(item.responsibilities), ...asValues(item.achievements)].map(formatInlineMarkdown));
    if (item.description) {
      if (Array.isArray(item.description)) {
        bullets = [...bullets, ...item.description.map(formatInlineMarkdown).filter(Boolean)];
      } else if (typeof item.description === 'string') {
        const d = item.description.trim();
        if (d.includes('\n')) d.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).forEach((l) => bullets.push(formatInlineMarkdown(l)));
        else if (isBulletLine(d)) bullets.push(formatInlineMarkdown(d));
        else description = formatInlineMarkdown(d);
      }
    }
    results.push({ name, subtitle, dates, technologies: tech, url: item.url || item.link || '', description, bullets });
  }
  return results;
}

function renderProjects(data) {
  const projects = normalizeProjects(data);
  if (!projects.length) return '';
  return projects.map((item) => {
    const tech = list(item.technologies);
    const bullets = list(item.bullets);
    return `
      <div class="resume-entry project-entry">
        <div class="entry-heading project-heading">
          <span>${item.name || ''}</span>
          ${item.dates ? `<small style="font-weight: normal; color: #64748B;">${item.dates}</small>` : ''}
        </div>
        ${item.subtitle ? `<div class="entry-subheading project-subheading">${item.subtitle}</div>` : ''}
        ${tech.length ? `<p class="project-tech"><strong>Tech:</strong> ${escapeHtml(tech.join(', '))}</p>` : ''}
        ${item.url ? `<p class="project-link"><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.url)}</a></p>` : ''}
        ${item.description ? `<p class="project-description">${item.description}</p>` : ''}
        ${bullets.length ? `<ul class="project-bullets">${bullets.map((b) => `<li>${b}</li>`).join('')}</ul>` : ''}
      </div>`;
  }).join('');
}

function renderResumeDocument(resume, theme, targetRole = '') {
  if (!resume || typeof resume !== 'object') return '';
  const info = resume.personal_info || {};
  const contactValues = [info.email, info.phone, info.location, info.linkedin, info.github, info.portfolio].filter(Boolean);
  const headerContacts = contactValues.map((v) => String(v).trim().toLowerCase());
  const contact = contactValues.map(escapeHtml).join(' · ');

  const renderEntries = (items) => list(items).map((item) => {
    if (item == null || typeof item !== 'object') return `<div class="resume-entry"><p>${formatInlineMarkdown(item)}</p></div>`;
    const heading = cleanHeadingText(item.job_title || item.role || item.company || item.name || item.project_name || item.title || item.institution || item.organization || '');
    const subheading = cleanHeadingText(item.company || item.employer || item.degree || item.field || '');
    const dates = escapeHtml(item.dates || [item.start_date, item.end_date].filter(Boolean).join(' – '));
    const bullets = [...asValues(item.bullets), ...asValues(item.responsibilities), ...asValues(item.achievements)];
    const description = asValues(item.description).filter(Boolean).map((t) => `<p>${formatInlineMarkdown(t)}</p>`).join('');
    const tech = [...asValues(item.technologies), ...asValues(item.technology), ...asValues(item.tech_stack), ...asValues(item.tech)];
    const grade = item.gpa || item.cgpa || item.grade;
    const other = [...asValues(item.other), ...asValues(item.details)];
    const known = new Set(['company', 'name', 'project_name', 'title', 'institution', 'organization', 'role', 'degree', 'field', 'dates', 'start_date', 'end_date', 'location', 'bullets', 'responsibilities', 'achievements', 'description', 'technologies', 'technology', 'tech_stack', 'tech', 'gpa', 'cgpa', 'grade', 'other', 'details']);
    const extra = Object.entries(item)
      .filter(([k, v]) => !known.has(k) && v != null && v !== '' && (!Array.isArray(v) || v.length))
      .map(([k, v]) => `<p><strong>${escapeHtml(k.replaceAll('_', ' '))}:</strong> ${escapeHtml(Array.isArray(v) ? v.join(', ') : v)}</p>`).join('');
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
        ${other.map((v) => `<p>${formatInlineMarkdown(v)}</p>`).join('')}
        ${description}
        ${extra}
        ${bullets.length ? `<ul>${bullets.map((b) => `<li>${formatInlineMarkdown(b)}</li>`).join('')}</ul>` : ''}
      </div>`;
  }).join('');

  let body = '';
  if (resume.summary) body += `<h3>Professional Summary</h3><p>${formatInlineMarkdown(resume.summary)}</p>`;
  if (list(resume.experience).length) body += `<h3>Experience</h3>${renderEntries(resume.experience)}`;
  if (list(resume.internships).length) body += `<h3>Internships</h3>${renderEntries(resume.internships)}`;
  if (resume.projects && (Array.isArray(resume.projects) ? resume.projects.length : typeof resume.projects === 'string')) {
    body += `<h3>Projects</h3>${renderProjects(resume.projects)}`;
  }
  if (list(resume.education).length) body += `<h3>Education</h3>${renderEntries(resume.education)}`;
  const groups = skillGroups(resume.skills);
  if (groups.length) {
    body += `<h3>Skills</h3>${groups.map(([name, values]) => `<p><strong>${escapeHtml(name.replace('_', ' '))}:</strong> ${escapeHtml(values.join(', '))}</p>`).join('')}`;
  }
  for (const [key, title] of [['certifications', 'Certifications'], ['achievements', 'Achievements'], ['languages', 'Languages']]) {
    const values = list(resume[key]).map((i) => String(i ?? '').trim()).filter(Boolean);
    if (values.length) body += `<h3>${title}</h3><ul>${values.map((i) => `<li>${formatInlineMarkdown(i)}</li>`).join('')}</ul>`;
  }

  const internal = new Set(['personal_info', 'summary', 'experience', 'internships', 'projects', 'education', 'skills', 'certifications', 'achievements', 'languages', 'source_lines', 'format_signals', 'normalized_skills', 'legacy_skills', 'skill_category_labels', 'section_order', 'section_heading_labels', 'sections_detected', 'headline', 'contact_details']);
  Object.entries(resume).forEach(([key, value]) => {
    if (internal.has(key) || value == null || value === '' || (Array.isArray(value) && !value.length)) return;
    let values = Array.isArray(value) ? value : [value];
    if (key === 'other') {
      values = values.filter((i) => {
        const t = String(i ?? '').trim().toLowerCase();
        return t && !headerContacts.includes(t) && !/(?:linkedin\.com|github\.com)/i.test(t);
      });
    }
    const lines = values.map((i) => {
      if (i && typeof i === 'object') {
        return Object.entries(i).filter(([, v]) => v != null && v !== '')
          .map(([k, v]) => `${escapeHtml(k.replaceAll('_', ' '))}: ${escapeHtml(Array.isArray(v) ? v.join(', ') : v)}`).join(' · ');
      }
      return formatInlineMarkdown(i);
    }).filter(Boolean);
    const label = resume.section_heading_labels?.[key]?.[0] || key.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    if (lines.length) body += `<h3>${escapeHtml(label)}</h3><ul>${lines.map((l) => `<li>${l}</li>`).join('')}</ul>`;
  });

  if (theme === 'sidebar' || theme === 'sidebar_corporate') {
    const skills = skillGroups(resume.skills).flatMap(([, v]) => v);
    const sideList = (title, values) => values.length
      ? `<section class="resume-side-section"><h3>${title}</h3><ul>${values.map((v) => `<li>${formatInlineMarkdown(v)}</li>`).join('')}</ul></section>` : '';
    const clean = (arr) => list(arr).map((i) => String(i ?? '').trim()).filter(Boolean);
    const sideContact = [['Email', info.email], ['Phone', info.phone], ['Location', info.location], ['LinkedIn', info.linkedin], ['GitHub', info.github], ['Portfolio', info.portfolio]]
      .filter(([, v]) => v && String(v).trim());
    const sidebar = `<aside class="resume-sidebar"><div class="resume-identity"><h2>${escapeHtml(info.name || 'Candidate')}</h2>${targetRole ? `<p class="resume-target-role">${escapeHtml(targetRole)}</p>` : ''}</div>${sideContact.length ? `<section class="resume-side-section"><h3>Contact</h3><ul>${sideContact.map(([l, v]) => `<li><strong>${l}</strong><br>${escapeHtml(v)}</li>`).join('')}</ul></section>` : ''}${sideList(theme === 'sidebar_corporate' ? 'Core Skills' : 'Skills', skills)}${sideList('Certifications', clean(resume.certifications))}${sideList('Languages', clean(resume.languages))}</aside>`;
    return `<article class="resume-preview-sheet theme-${theme}">${sidebar}<div class="resume-main-column">${body}</div></article>`;
  }

  return `
    <article class="resume-preview-sheet theme-${theme}">
      <header>
        <h2>${escapeHtml(info.name || 'Candidate')}</h2>
        <div class="resume-contact">${contact}</div>
      </header>
      ${body}
    </article>`;
}

/* ---------------------------------------------------------------
   Constants
---------------------------------------------------------------- */

const STEPS = ['Job', 'Resume', 'Analysis', 'Match', 'Optimize', 'Preview'];

const TEMPLATES = [
  { id: 'professional', number: 1, name: 'Professional', category: 'SINGLE COLUMN', description: 'Existing resume layout' },
  { id: 'corporate', number: 2, name: 'Corporate', category: 'SINGLE COLUMN', description: 'Formal navy styling' },
  { id: 'finance', number: 3, name: 'Finance', category: 'SINGLE COLUMN', description: 'Conservative navy hierarchy' },
  { id: 'fresher', number: 4, name: 'Fresher', category: 'SINGLE COLUMN', description: 'Education and projects forward' },
  { id: 'sidebar', number: 5, name: 'Sidebar', category: 'TWO COLUMN', description: 'Light sidebar · Professional' },
  { id: 'sidebar_corporate', number: 6, name: 'Sidebar Two-Column', category: 'TWO COLUMN', description: 'Dark navy sidebar · Corporate' },
];

const SOURCES = [
  { id: 'finxl', label: 'FINXL Job', sub: 'Select from catalog' },
  { id: 'external', label: 'External Job', sub: 'Enter reference ID' },
  { id: 'paste', label: 'Paste JD', sub: 'Paste text directly' },
  { id: 'upload', label: 'Upload JD', sub: 'Attach PDF/DOCX' },
];

const EMPTY_PREVIEW = 'Select a job or provide a job description to see its preview.';
const emptyJob = (description = EMPTY_PREVIEW) => ({
  title: 'Untitled Position', company: 'Company not specified', job_id: 'N/A', description, domain: 'General',
});

/* ---------------------------------------------------------------
   Helpers
---------------------------------------------------------------- */

function errorText(body) {
  if (!body) return '';
  const d = body.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => x.msg).join('; ');
  return body.error || '';
}

async function api(path, options) {
  let res;
  try {
    res = await fetch(path, options);
  } catch {
    throw new Error('Cannot reach the resume backend. Is uvicorn running on port 8000?');
  }
  let body = null;
  try { body = await res.json(); } catch { /* non-JSON response */ }
  if (!res.ok) throw new Error(errorText(body) || `Request failed (${res.status})`);
  return body;
}

function deriveJobTitle(text) {
  const lines = String(text || '').split(/\r?\n/).map((l) => l.replace(/^\s*[#*-]+\s*/, '').trim()).filter(Boolean);
  for (const line of lines.slice(0, 8)) {
    const labeled = line.match(/^(?:job\s*title|role|position)\s*:\s*(.+)$/i);
    if (labeled?.[1]) return labeled[1].trim().slice(0, 90);
  }
  const sentence = String(text || '').match(/\b(?:looking for|seeking|hiring)\s+(?:an?\s+)?(.+?)(?=\s+(?:to|who|that|for)\b|[.,\n]|$)/i)?.[1]?.trim();
  if (sentence && sentence.length <= 90) return sentence;
  const candidate = lines.find((l) => !/^(?:company|employer|organization|industry|domain|category|department|job\s*id|requisition\s*id)\s*:/i.test(l)) || '';
  if (candidate.length <= 90 && !/^(we are|we're|about (the|this)|job description|overview|responsibilities|qualifications|requirements)\b/i.test(candidate)) return candidate;
  return 'Untitled Position';
}

function normalizePreviewJob(value, fallback = {}) {
  const source = typeof value === 'string' ? { description: value } : (value || {});
  const description = String(source.description || source.summary || source.job_description || source.jd_text || source.text || source.content || fallback.description || '').trim();
  const labeled = (re) => description.match(re)?.[1]?.trim() || '';
  let title = String(source.title || source.job_title || source.role || source.position || labeled(/^\s*(?:job\s*title|role|position)\s*:\s*(.+)$/im) || fallback.title || '').trim();
  if (!title || /^(pasted job description|uploaded job description|job description)$/i.test(title)) title = deriveJobTitle(description);
  const company = String(source.company || source.employer || source.organization || labeled(/^\s*(?:company|employer|organization)\s*:\s*(.+)$/im) || fallback.company || '').trim();
  const jobId = String(source.job_id || source.id || source.requisition_id || labeled(/^\s*(?:job\s*id|requisition\s*id)\s*:\s*(.+)$/im) || fallback.job_id || '').trim();
  const domain = String(source.domain || source.industry || source.category || source.department || labeled(/^\s*(?:industry|domain|category|department)\s*:\s*(.+)$/im) || fallback.domain || '').trim();
  const text = `${title} ${description}`.toLowerCase();
  const inferred = /finance|financial|accounting|investment|banking|fp&a/.test(text) ? 'Finance'
    : /software|developer|engineer|technology|data|devops/.test(text) ? 'Technology'
      : /marketing|seo|growth|content|branding/.test(text) ? 'Marketing' : 'General';
  return {
    ...source, title: title || 'Untitled Position', company: company || 'Company not specified',
    job_id: jobId || 'N/A', description: description || 'Job description unavailable.', domain: domain || inferred,
  };
}

/* ---------------------------------------------------------------
   Small presentational pieces
---------------------------------------------------------------- */

const Svg = ({ size = 16, children }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
);

const Arrow = () => (<Svg><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></Svg>);
const DownloadIcon = () => (<Svg size={14}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></Svg>);

const SOURCE_ICONS = {
  finxl: <Svg size={18}><rect x="2" y="7" width="20" height="14" rx="2" ry="2" /><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" /></Svg>,
  external: <Svg size={18}><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></Svg>,
  paste: <Svg size={18}><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" ry="1" /></Svg>,
  upload: <Svg size={18}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></Svg>,
};

function Chips({ values, kind = '' }) {
  const items = list(values);
  if (!items.length) return <span className="text-subtle">None detected</span>;
  return <>{items.map((v, i) => <span key={i} className={`chip-tag ${kind}`}>{String(v)}</span>)}</>;
}

function MatchBox({ badgeClass, badge, title, items, note }) {
  return (
    <div className="match-category-box">
      <div className="match-category-header">
        <div className="match-status-heading">
          <span className={`status-badge ${badgeClass}`}>{badge}</span>
          <strong>{title}</strong>
        </div>
        <span className="count-pill">{items.length} items</span>
      </div>
      {note && <div className="match-disclaimer-note">{note}</div>}
      {!items.length ? (
        <div className="match-disclaimer-note">None detected in this category.</div>
      ) : (
        <div className="match-rows-list">
          {items.map((it, i) => {
            const evidence = list(it.evidence);
            return (
              <div className="match-item-row" key={i}>
                <div className="match-item-top">
                  <div>
                    <span className={`status-badge ${badgeClass}`}>{badge}</span>
                    <strong className="match-item-name" style={{ marginLeft: 6 }}>{it.requirement}</strong>
                  </div>
                  <span className="match-item-meta">{String(it.type || '').replace('_', ' ')} · {it.importance}</span>
                </div>
                {evidence.length ? (
                  <details className="match-evidence-details">
                    <summary>Verified resume evidence ({evidence.length})</summary>
                    <ul>{evidence.map((line, j) => <li key={j}>{line}</li>)}</ul>
                  </details>
                ) : (
                  <div className="match-item-meta" style={{ fontSize: 11, color: 'var(--text-subtle)', marginTop: 2 }}>
                    No direct evidence found in uploaded resume.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function MiniPreview({ tpl, name }) {
  const lines = {
    professional: ['mid centered', 'long', 'mid', 'short'],
    corporate: ['mid', 'long', 'mid', 'short'],
    finance: ['long', 'mid', 'long', 'short'],
    fresher: ['mid centered', 'long', 'short', 'mid'],
    sidebar: ['long', 'long', 'mid', 'short'],
    sidebar_corporate: ['long', 'mid', 'short'],
  }[tpl.id];
  return (
    <div className={`mini-resume-preview theme-${tpl.id}`}>
      <div className="mini-name">{name}</div>
      <div className="mini-rule" />
      {lines.map((cls, i) => {
        const centered = cls.includes('centered');
        return <div key={i} className={`mini-line ${cls.replace(' centered', '')}`} style={centered ? { margin: '0 auto 6px' } : undefined} />;
      })}
    </div>
  );
}

/* ---------------------------------------------------------------
   Page
---------------------------------------------------------------- */

export default function ResumeOptimizerPage() {
  // Job source
  const [source, setSource] = useState('finxl');
  const [jobs, setJobs] = useState([]);
  const [jobsFailed, setJobsFailed] = useState(false);
  const [jobId, setJobId] = useState('');
  const [externalId, setExternalId] = useState('');
  const [pasteText, setPasteText] = useState('');
  const [jdFile, setJdFile] = useState(null);
  const [job, setJob] = useState(emptyJob());

  // Resume files
  const [files, setFiles] = useState([]);
  const [drag, setDrag] = useState(false);

  // Flow
  const [stage, setStage] = useState('input'); // input | results | batch
  const [step, setStep] = useState(0);
  const [error, setError] = useState('');
  const [toastMsg, setToastMsg] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [batch, setBatch] = useState([]);
  const [optimizing, setOptimizing] = useState(false);
  const [optimized, setOptimized] = useState(null); // { resume, method }
  const [templateId, setTemplateId] = useState('professional');
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(null);

  const fileInputRef = useRef(null);
  const jdInputRef = useRef(null);
  const previewRef = useRef(null);
  const toastTimer = useRef(null);
  const reqRef = useRef(0); // invalidates in-flight job previews

  const showToast = (message) => {
    setToastMsg(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastMsg(''), 4000);
  };
  useEffect(() => () => clearTimeout(toastTimer.current), []);

  /* ----- Job catalogue and preview ----- */

  useEffect(() => {
    let live = true;
    api('/api/jobs')
      .then((data) => live && setJobs(Array.isArray(data) ? data : data?.jobs || []))
      .catch(() => {
        if (!live) return;
        setJobsFailed(true);
        setJob(emptyJob('The job catalogue could not be loaded. You can still paste or upload a job description.'));
      });
    return () => { live = false; };
  }, []);

  const showJob = (value, fallback) => { reqRef.current += 1; setJob(normalizePreviewJob(value, fallback)); };
  const resetJob = (description) => { reqRef.current += 1; setJob(emptyJob(description)); };

  const loadJob = async (id) => {
    const my = ++reqRef.current;
    setJob(normalizePreviewJob({ title: 'Loading job…', company: '', job_id: id, description: 'Loading the selected job description.' }));
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(id)}`);
      if (my !== reqRef.current) return;
      if (!res.ok) {
        setJob(emptyJob('No job description was found for this reference ID. Check the selection and try again.'));
        return;
      }
      const data = await res.json();
      if (my === reqRef.current) setJob(normalizePreviewJob(data));
    } catch {
      if (my === reqRef.current) setJob(emptyJob('The selected job description could not be loaded.'));
    }
  };

  const previewPasted = (text) => {
    const t = text.trim();
    if (!t) return resetJob();
    showJob({ title: deriveJobTitle(t), description: t, job_id: 'Pasted JD' });
  };

  const previewUpload = (file) => {
    if (!file) {
      return showJob({ title: 'Untitled Position', job_id: 'N/A', description: 'Attach a PDF, DOCX, TXT, or JSON file to use it as the target job description.' });
    }
    const name = file.name;
    const ext = name.split('.').pop().toLowerCase();
    const title = name.replace(/\.[^.]+$/, '') || 'Uploaded Job Description';
    showJob({ title, job_id: name, description: `Reading the selected ${ext.toUpperCase()} job description…` });
    const my = reqRef.current;
    if (ext === 'txt' || ext === 'json') {
      const reader = new FileReader();
      reader.onload = () => {
        if (my !== reqRef.current) return;
        const text = String(reader.result || '');
        if (ext === 'txt') return setJob(normalizePreviewJob({ title: deriveJobTitle(text), job_id: name, description: text.trim() }));
        try {
          const parsed = JSON.parse(text || '{}');
          setJob(normalizePreviewJob(parsed, { title, job_id: name, description: JSON.stringify(parsed, null, 2) }));
        } catch {
          setJob(normalizePreviewJob({ title, job_id: name, description: 'This JSON file could not be previewed. It will be validated when you analyze the resume.' }));
        }
      };
      reader.readAsText(file);
    } else {
      setJob(normalizePreviewJob({ title, job_id: name, description: `Selected ${ext.toUpperCase()} job description. Its extracted text will be used for matching.` }));
    }
  };

  const chooseSource = (id) => {
    setSource(id);
    if (id === 'finxl') { if (jobId) loadJob(jobId); else resetJob(); }
    else if (id === 'external') {
      showJob({ title: 'Untitled Position', job_id: externalId.trim() || 'N/A', description: 'Enter an external job reference ID to load its job description preview.' });
      if (externalId.trim()) loadJob(externalId.trim());
    } else if (id === 'paste') previewPasted(pasteText);
    else previewUpload(jdFile);
  };

  const attachJdFile = (file) => {
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx', 'txt', 'json'].includes(ext)) return setError('Please upload a PDF, DOCX, TXT, or JSON job description.');
    if (file.size > 8 * 1024 * 1024) return setError(`${file.name} exceeds the 8 MB limit.`);
    setError('');
    setJdFile(file);
    previewUpload(file);
    showToast(`Attached JD: ${file.name}`);
  };

  /* ----- Resume files ----- */

  const pickFiles = (selection) => {
    setError('');
    const picked = Array.from(selection || []);
    if (!picked.length) return;
    if (picked.length > 5) { setFiles([]); return setError('Maximum 5 resumes can be optimized at once.'); }
    for (const f of picked) {
      const ext = f.name.split('.').pop().toLowerCase();
      if (!['pdf', 'docx'].includes(ext)) return setError('Please upload a PDF or DOCX resume.');
      if (f.size > 8 * 1024 * 1024) return setError(`${f.name} exceeds the 8 MB limit.`);
    }
    setFiles(picked);
    setStep(1);
  };

  const removeFiles = () => {
    setFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = '';
    setError('');
    setTemplateId('professional');
    setStep(0);
  };

  const fileMeta = () => {
    if (files.length !== 1) return `${files.length} resumes selected`;
    const f = files[0];
    const size = f.size < 1048576 ? `${(f.size / 1024).toFixed(0)} KB` : `${(f.size / 1048576).toFixed(1)} MB`;
    return `${f.name.split('.').pop().toUpperCase()} · ${size}`;
  };

  /* ----- Backend actions ----- */

  const analyze = async () => {
    if (!files.length) return;
    setAnalyzing(true);
    setError('');
    try {
      const body = new FormData();
      if (files.length === 1) body.append('file', files[0]);
      else files.forEach((f) => body.append('files', f));
      body.append('source', source);
      if (source === 'paste') {
        const t = pasteText.trim();
        if (!t) throw new Error('Paste a job description before analyzing.');
        body.append('jd_text', t);
      } else if (source === 'upload') {
        if (!jdFile) throw new Error('Upload a job description before analyzing.');
        body.append('jd_file', jdFile);
      } else {
        const id = source === 'external' ? externalId.trim() : jobId;
        if (!id) throw new Error('Select or enter a job ID before analyzing.');
        body.append('job_id', id);
      }
      const data = await api(files.length === 1 ? '/api/optimize-resume' : '/api/optimize-resumes', { method: 'POST', body });
      if (files.length === 1) {
        setResult(data);
        setOptimized(null);
        setGenerated(null);
        setTemplateId('professional');
        setStage('results');
        setStep(2);
      } else {
        setBatch(data.results || []);
        setStage('batch');
        setStep(5);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const optimize = async () => {
    setOptimizing(true);
    try {
      const data = await api(`/api/resumes/${result.id}/optimize`, { method: 'POST' });
      setOptimized({ resume: data.optimized_resume, method: data.optimization_method });
      setStep(4);
    } catch (e) {
      showToast(e.message);
    } finally {
      setOptimizing(false);
    }
  };

  const generate = async () => {
    setGenerating(true);
    try {
      const body = new FormData();
      body.append('template_id', templateId);
      const data = await api(`/api/resumes/${result.id}/generate`, { method: 'POST', body });
      setGenerated(data);
      setStep(5);
    } catch (e) {
      showToast(e.message);
    } finally {
      setGenerating(false);
    }
  };

  useEffect(() => {
    if (generated) previewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [generated]);

  const backToInputs = () => { setStage('input'); setStep(files.length ? 1 : 0); };

  const newResume = () => {
    removeFiles();
    setResult(null);
    setOptimized(null);
    setGenerated(null);
    setBatch([]);
    setStage('input');
    setStep(0);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  /* ----- Derived values for the results screens ----- */

  const resume = result?.resume_analysis || {};
  const match = result?.match || {};
  const jobAnalysis = result?.job_analysis || {};
  const quality = result?.quality_analysis || {};
  const counts = match.counts || {};
  const detectedSkills = skillGroups(resume.skills).flatMap(([, v]) => v);
  const matchItems = list(match.items);
  const required = list(jobAnalysis.required_skills);
  const preferred = list(jobAnalysis.preferred_skills);
  const qualifications = list(jobAnalysis.qualifications);
  const responsibilities = list(jobAnalysis.responsibilities);
  const candidateName = resume.personal_info?.name || 'Alex Morgan';
  const targetRole = result?.job?.title || '';

  return (
    <div className="ro-page">
      <style>{ROP_STYLES}</style>
      <div className="main-workspace">
        <div className="workspace-container">

          {/* Welcome */}
          <section className="welcome-section">
            <div className="welcome-badge"><span className="badge-dot" />AI Resume Optimizer</div>
            <h1 className="welcome-heading">Optimize your resume for your next opportunity.</h1>
            <p className="welcome-subtext">
              Analyze job requirements, identify skill matches, and create a tailored, ATS-friendly resume.
            </p>
          </section>

          {/* Stepper */}
          <nav className="workflow-stepper" aria-label="Optimization Workflow">
            <div className="stepper-track">
              {STEPS.map((name, i) => (
                <React.Fragment key={name}>
                  <div className={`step-item${i === step ? ' active' : ''}${i < step ? ' done' : ''}`}>
                    <span className="step-num">{String(i + 1).padStart(2, '0')}</span>
                    <span className="step-name">{name}</span>
                  </div>
                  {i < STEPS.length - 1 && <div className="step-connector" />}
                </React.Fragment>
              ))}
            </div>
          </nav>

          {/* ================= INPUTS (steps 01 and 02) ================= */}
          {stage === 'input' && (
            <div className="workspace-cards-grid">

              {/* 01 JOB DESCRIPTION */}
              <section className="app-card job-source-card">
                <div className="card-eyebrow">01 &nbsp;·&nbsp; JOB DESCRIPTION</div>
                <h2 className="card-title">Where is your job description?</h2>
                <p className="card-subtitle">Select a target job from FINXL catalogue or specify your own role.</p>

                <div className="source-options-grid">
                  {SOURCES.map((s) => (
                    <div key={s.id} className={`source-card${source === s.id ? ' selected' : ''}`} onClick={() => chooseSource(s.id)}>
                      <div className="source-icon">{SOURCE_ICONS[s.id]}</div>
                      <div className="source-meta"><b>{s.label}</b><small>{s.sub}</small></div>
                    </div>
                  ))}
                </div>

                <div className="source-input-container">
                  {source === 'finxl' && (
                    <div className="source-panel">
                      <label className="input-label" htmlFor="ro-job-select">Select FINXL Role</label>
                      <select
                        id="ro-job-select"
                        className="form-select"
                        value={jobId}
                        onChange={(e) => { setJobId(e.target.value); if (e.target.value) loadJob(e.target.value); else resetJob(); }}
                      >
                        <option value="">{jobsFailed ? 'Job catalogue unavailable' : 'Select a FINXL role'}</option>
                        {jobs.map((j) => (
                          <option key={j.job_id} value={j.job_id}>{j.title} · {j.company || 'FINXL'}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {source === 'external' && (
                    <div className="source-panel">
                      <label className="input-label" htmlFor="ro-external-id">External Job Requisition ID</label>
                      <input
                        id="ro-external-id"
                        type="text"
                        className="form-input"
                        placeholder="e.g. finance-demo-001"
                        value={externalId}
                        onChange={(e) => {
                          setExternalId(e.target.value);
                          const v = e.target.value.trim();
                          showJob({ title: v ? 'Loading job…' : 'Untitled Position', job_id: v || 'N/A', description: v ? 'Press Enter or click outside the box to load this job.' : 'Enter an external job reference ID to load its preview.' });
                        }}
                        onBlur={() => externalId.trim() && loadJob(externalId.trim())}
                        onKeyDown={(e) => e.key === 'Enter' && externalId.trim() && loadJob(externalId.trim())}
                      />
                    </div>
                  )}

                  {source === 'paste' && (
                    <div className="source-panel">
                      <label className="input-label" htmlFor="ro-paste">Paste Job Description Text</label>
                      <textarea
                        id="ro-paste"
                        className="form-textarea"
                        rows={4}
                        placeholder="Paste full job description, qualifications, and responsibilities..."
                        value={pasteText}
                        onChange={(e) => { setPasteText(e.target.value); previewPasted(e.target.value); }}
                      />
                    </div>
                  )}

                  {source === 'upload' && (
                    <div className="source-panel">
                      <label className="input-label">Upload Job Description File</label>
                      <div
                        className="mini-dropzone"
                        onClick={() => jdInputRef.current?.click()}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={(e) => { e.preventDefault(); attachJdFile(e.dataTransfer.files[0]); }}
                      >
                        <span>{jdFile ? jdFile.name : <>Drop JD file or <u>browse</u></>}</span>
                        <input
                          ref={jdInputRef}
                          type="file"
                          accept=".pdf,.docx,.txt,.json"
                          className="hidden"
                          onChange={(e) => { attachJdFile(e.target.files[0]); e.target.value = ''; }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                <div className="job-preview-box">
                  <div className="job-preview-header">
                    <div>
                      <h3 className="job-preview-title">{job.title}</h3>
                      <div className="job-preview-company">
                        {job.company} <span className="dot-sep">·</span> Job ID: <strong>{job.job_id}</strong>
                      </div>
                    </div>
                    <span className="role-badge">{job.domain}</span>
                  </div>
                  <p className="job-preview-desc">{job.description}</p>
                  <div className="job-preview-footer">
                    <button type="button" className="inline-link" onClick={() => showToast(`${job.title} (${job.job_id})\n${job.description.slice(0, 400)}`)}>
                      View role requirements ↗
                    </button>
                  </div>
                </div>
              </section>

              {/* 02 YOUR RESUME */}
              <section className="app-card resume-upload-card">
                <div className="card-eyebrow">02 &nbsp;·&nbsp; YOUR RESUME</div>
                <h2 className="card-title">Upload your resume</h2>
                <p className="card-subtitle">We will review your factual experience against the target role.</p>

                <label
                  className={`upload-dropzone${drag ? ' drag' : ''}${files.length ? ' hidden' : ''}`}
                  onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
                  onDragLeave={() => setDrag(false)}
                  onDrop={(e) => { e.preventDefault(); setDrag(false); pickFiles(e.dataTransfer.files); }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    multiple
                    onChange={(e) => { pickFiles(e.target.files); e.target.value = ''; }}
                  />
                  <div className="upload-icon-circle">
                    <Svg size={22}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></Svg>
                  </div>
                  <div className="dropzone-text">
                    <strong className="dropzone-primary-text">Drop your resume here</strong>
                    <span className="dropzone-secondary-text">PDF or DOCX · Up to 5 resumes · 8 MB each</span>
                  </div>
                  <span className="browse-pill">Browse files</span>
                </label>

                {files.length > 0 && (
                  <div className="uploaded-file-card">
                    <div className="file-card-info">
                      <div className="file-icon-box">
                        <Svg size={20}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></Svg>
                      </div>
                      <div>
                        <div className="file-card-name">{files.map((f) => f.name).join(', ')}</div>
                        <div className="file-card-sub">{fileMeta()}</div>
                      </div>
                    </div>
                    <div className="file-card-actions">
                      <button type="button" className="btn-text-action" onClick={() => fileInputRef.current?.click()}>Replace</button>
                      <span className="action-divider">·</span>
                      <button type="button" className="btn-text-action danger" onClick={removeFiles}>Remove</button>
                    </div>
                  </div>
                )}

                {error && <div className="alert-box error-alert">{error}</div>}

                <button className="app-btn primary-btn full-width" onClick={analyze} disabled={!files.length || analyzing}>
                  {analyzing ? (
                    <><span className="badge-dot pulse" /><span>Analyzing resume &amp; matching requirements...</span></>
                  ) : (
                    <><span>Analyze Resume &amp; Match</span><Arrow /></>
                  )}
                </button>

                <div className="privacy-note">
                  <Svg size={14}><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></Svg>
                  <span>Your resume is analyzed privately. Content is never used to train external AI models.</span>
                </div>
              </section>
            </div>
          )}

          {/* ================= RESULTS (steps 03 to 06) ================= */}
          {stage === 'results' && result && (
            <div className="results-layout">

              <div className="result-header-card">
                <div className="result-header-info">
                  <h2>{result.job?.title}</h2>
                  <p>{result.job?.company} <span className="dot-sep">·</span> Target Job ID: <strong>{result.job?.job_id}</strong></p>
                </div>
                <button className="app-btn secondary-btn" onClick={backToInputs}>
                  <Svg size={14}><line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" /></Svg>
                  <span>Change resume / role</span>
                </button>
              </div>

              <div className="metric-summary-grid">
                <div className="metric-card"><strong>{detectedSkills.length}</strong><span>Skills Detected</span></div>
                <div className="metric-card matched"><strong>{counts.matched ?? 0}</strong><span>Matched</span></div>
                <div className="metric-card related"><strong>{counts.related ?? 0}</strong><span>Related</span></div>
                <div className="metric-card missing"><strong>{counts.missing ?? 0}</strong><span>Not Detected in Resume</span></div>
              </div>

              {/* 03 ANALYSIS */}
              <div className="analysis-dashboard-grid">
                <div className="analysis-card">
                  <div className="analysis-card-header"><span className="analysis-card-title">Required Skills</span><span className="count-pill">{required.length}</span></div>
                  <div className="chips-cluster"><Chips values={required} kind="matched" /></div>
                </div>
                <div className="analysis-card">
                  <div className="analysis-card-header"><span className="analysis-card-title">Preferred Skills</span><span className="count-pill">{preferred.length}</span></div>
                  <div className="chips-cluster"><Chips values={preferred} kind="related" /></div>
                </div>
                <div className="analysis-card">
                  <div className="analysis-card-header"><span className="analysis-card-title">Qualifications &amp; Education</span><span className="count-pill">{qualifications.length}</span></div>
                  <ul className="analysis-list">
                    {qualifications.length ? qualifications.map((q, i) => <li key={i}>{String(q)}</li>) : <li className="text-subtle">None specified.</li>}
                  </ul>
                </div>
                <div className="analysis-card">
                  <div className="analysis-card-header"><span className="analysis-card-title">Key Responsibilities</span><span className="count-pill">{responsibilities.length}</span></div>
                  <ol className="responsibilities-numbered-list">
                    {responsibilities.length ? responsibilities.map((r, i) => <li key={i}>{String(r)}</li>) : <li className="text-subtle">None specified.</li>}
                  </ol>
                </div>
              </div>

              <div className="categorized-panel">
                <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Requirements By Type</h4>
                <div className="categorized-group"><h5>Domain Skills</h5><div className="chips-cluster"><Chips values={jobAnalysis.domain_skills} /></div></div>
                <div className="categorized-group"><h5>Technical Skills</h5><div className="chips-cluster"><Chips values={jobAnalysis.technical_skills} /></div></div>
                <div className="categorized-group"><h5>Tools &amp; Platforms</h5><div className="chips-cluster"><Chips values={jobAnalysis.tools} /></div></div>
                {list(jobAnalysis.soft_skills).length > 0 && (
                  <div className="categorized-group"><h5>Soft Skills</h5><div className="chips-cluster"><Chips values={jobAnalysis.soft_skills} /></div></div>
                )}
              </div>

              {/* 04 MATCH */}
              <div className="matching-card-container">
                <div className="matching-header">
                  <h3>Resume ↔ Job Requirement Matching</h3>
                  <p>Verified match outcomes based on candidate evidence. Unmentioned requirements are never invented.</p>
                </div>
                <div className="match-sections-list">
                  <MatchBox badgeClass="matched" badge="MATCHED" title="Direct Skills & Qualifications" items={matchItems.filter((i) => i.status === 'matched')} />
                  <MatchBox badgeClass="related" badge="RELATED" title="Contextual & Transferable Experience" items={matchItems.filter((i) => i.status === 'related')} />
                  <MatchBox
                    badgeClass="not-detected" badge="NOT DETECTED" title="Not Detected in Resume"
                    items={matchItems.filter((i) => i.status === 'not_detected')}
                    note="Not detected in the uploaded resume. Missing skills are never assumed or added to your resume."
                  />
                </div>
              </div>

              {/* Quality */}
              <div className="quality-review-panel">
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Structural Quality Review</h3>
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{quality.method}</p>
                <div className="quality-issues-grid">
                  {list(quality.issues).length ? list(quality.issues).map((iss, i) => (
                    <div className="quality-issue-badge" key={i}>
                      <span className={`issue-sev ${iss.severity}`}>{iss.severity}</span>
                      <span>{iss.message}</span>
                    </div>
                  )) : <div style={{ fontSize: 12, color: '#059669' }}>✓ No structural formatting issues detected.</div>}
                </div>
              </div>

              {/* 05 OPTIMIZE */}
              <div className="ai-optimize-card">
                {!optimized ? (
                  <>
                    <div className="ai-card-heading">
                      <Svg size={22}><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" /></Svg>
                      <h3 className="ai-card-title">Optimize your resume</h3>
                    </div>
                    <p className="ai-card-desc">Improve the wording and relevance of your existing resume based on the selected job description.</p>
                    <div className="ai-features-checklist">
                      {['Improve existing content', 'Prioritize relevant experience', 'Improve professional wording', 'Optimize relevant keywords'].map((t) => (
                        <div className="ai-feature-item" key={t}><span className="check-green">✓</span><span>{t}</span></div>
                      ))}
                    </div>
                    <div className="ai-guarantee-callout">
                      <Svg><circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" /></Svg>
                      <span><strong>Factuality Guarantee:</strong> AI does not invent skills, experience, achievements, qualifications, or metrics.</span>
                    </div>
                    <button className="app-btn primary-btn" onClick={optimize} disabled={optimizing}>
                      {optimizing ? (
                        <><span className="badge-dot pulse" /><span>Optimizing resume content...</span></>
                      ) : (
                        <><span>Optimize Resume</span><Arrow /></>
                      )}
                    </button>
                  </>
                ) : (
                  <>
                    <div className="ai-card-heading">
                      <Svg size={20}><polyline points="20 6 9 17 4 12" /></Svg>
                      <h3 className="ai-card-title">Content Optimized</h3>
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>{optimized.method}</p>

                    <div className="template-selection-container">
                      <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Choose Document Template</h4>
                      <div className="template-cards-row">
                        {TEMPLATES.map((t, i) => (
                          <React.Fragment key={t.id}>
                            {(i === 0 || TEMPLATES[i - 1].category !== t.category) && <div className="template-category-label">{t.category}</div>}
                            <div className={`template-card${templateId === t.id ? ' selected' : ''}`} onClick={() => setTemplateId(t.id)}>
                              <div className="template-card-header">
                                <span className="template-card-title">Template {t.number} — {t.name}</span>
                                <input type="radio" name="ro-template" checked={templateId === t.id} onChange={() => setTemplateId(t.id)} />
                              </div>
                              <p className="template-card-desc">{t.description}</p>
                              <MiniPreview tpl={t} name={candidateName} />
                            </div>
                          </React.Fragment>
                        ))}
                      </div>

                      <div
                        className="resume-live-selection-preview"
                        dangerouslySetInnerHTML={{ __html: renderResumeDocument(optimized.resume, templateId, targetRole) }}
                      />

                      <button className="app-btn primary-btn" onClick={generate} disabled={generating}>
                        {generating ? <span>Generating ATS-friendly DOCX &amp; PDF...</span> : <><span>Generate Selected Version</span><Arrow /></>}
                      </button>
                    </div>
                  </>
                )}
              </div>

              {/* 06 PREVIEW */}
              <div ref={previewRef}>
                {generated && (
                  <>
                    <div className="completion-banner-card">
                      <div className="completion-info">
                        <div className="completion-icon-circle">✓</div>
                        <div>
                          <h3 className="completion-heading">Resume ready</h3>
                          <p className="completion-subtext">Your optimized resume has been generated.</p>
                        </div>
                      </div>
                      <div className="completion-actions">
                        <a className="app-btn secondary-btn" href={generated.docx_url} download><DownloadIcon /><span>Download DOCX</span></a>
                        <a className="app-btn primary-btn" href={generated.pdf_url} download><DownloadIcon /><span>Download PDF</span></a>
                        <button className="app-btn secondary-btn" onClick={newResume}><span>Create another resume</span></button>
                      </div>
                    </div>

                    <div className="resume-preview-container">
                      <div style={{ marginBottom: 18 }}>
                        <h3 style={{ fontSize: 16, fontWeight: 700 }}>Document Preview</h3>
                        <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                          Formatted with {(TEMPLATES.find((t) => t.id === templateId)?.name || templateId).toUpperCase()} template
                        </p>
                      </div>
                      <div dangerouslySetInnerHTML={{ __html: renderResumeDocument(generated.preview, templateId, generated.job_title || '') }} />
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* ================= BATCH RESULTS ================= */}
          {stage === 'batch' && (
            <section className="app-card">
              <div className="card-eyebrow">OPTIMIZATION COMPLETE</div>
              <h2 className="card-title">Resume results</h2>
              {batch.map((item, i) => (
                <article className="app-card" style={{ marginTop: 16 }} key={i}>
                  <h3 style={{ fontSize: 15, fontWeight: 700 }}>{item.original_filename}</h3>
                  <p style={{ margin: '6px 0 12px' }}>
                    {item.status === 'completed' ? '✓ Successfully optimized' : `✗ Failed: ${item.error || 'Processing failed'}`}
                  </p>
                  {item.status === 'completed' && (
                    <div className="completion-actions">
                      <a className="app-btn primary-btn" href={item.docx_url} download>Download {item.optimized_docx}</a>
                      <a className="app-btn secondary-btn" href={item.pdf_url} download>Download {item.optimized_pdf}</a>
                    </div>
                  )}
                </article>
              ))}
              <div style={{ marginTop: 20 }}>
                <button className="app-btn secondary-btn" onClick={newResume}>Create another resume</button>
              </div>
            </section>
          )}

        </div>
      </div>

      {toastMsg && <div className="toast-notification">{toastMsg}</div>}
    </div>
  );
}
