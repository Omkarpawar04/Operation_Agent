import { Link } from "react-router-dom";
import ReportSummary from "../components/ReportSummary";
import { useInterview } from "../hooks/InterviewContext";

export default function InterviewReport() {
  const { report, reportError, evaluationRetryId, retryEvaluation, newInterview } = useInterview();
  return (
    <section className="report-page">
      <div className="report-header"><div><span className="eyebrow">SESSION FINISHED</span><h1>Interview report</h1><p className="muted">Review your interview feedback and plan what to practice next.</p></div><span className="completion-mark">✓</span></div>
      {report ? <ReportSummary report={report} /> : (
        <div className="report-empty"><h2>Report not ready yet</h2><p className="muted">The interview is saved. You can retry report generation from here.</p></div>
      )}
      {reportError && <p className="error-message" role="alert">{reportError}</p>}
      <div className="report-actions">
        {!report && <button type="button" className="secondary-button" onClick={() => retryEvaluation()} disabled={!evaluationRetryId}>Retry report</button>}
        <button type="button" className="primary-button" onClick={newInterview}>Start another interview</button>
        <Link className="text-link" to="/">Back to dashboard</Link>
      </div>
    </section>
  );
}
