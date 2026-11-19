const DIMENSIONS = ["technical_depth", "communication", "problem_solving", "culture_fit"];

export default function ReportSummary({ report }) {
  if (!report) return null;
  return (
    <div className="report-content">
      <div className="report-score"><span>Overall score</span><strong>{report.overall_score ?? "—"}<small>/10</small></strong><span className="recommendation">{report.recommendation || "Interview complete"}</span></div>
      <div className="score-grid">
        {DIMENSIONS.filter((key) => report[key]).map((key) => (
          <section className="score-card" key={key}>
            <div><h3>{key.replaceAll("_", " ")}</h3><strong>{report[key].score}<small>/10</small></strong></div>
            <p>{(report[key].evidence || []).join("; ") || "No additional evidence provided."}</p>
          </section>
        ))}
      </div>
      <div className="report-lists">
        <section><h3>Strengths</h3>{report.strengths?.length ? <ul>{report.strengths.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="muted">No strengths were listed.</p>}</section>
        <section><h3>Areas to improve</h3>{report.concerns?.length ? <ul>{report.concerns.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="muted">No concerns were listed.</p>}</section>
      </div>
      {report.summary && <p className="report-summary">{report.summary}</p>}
    </div>
  );
}
