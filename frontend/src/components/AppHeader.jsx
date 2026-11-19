import { Link } from "react-router-dom";

export default function AppHeader({ connected, sessionActive }) {
  return (
    <header className="topbar">
      <Link className="brand" to={sessionActive ? "/interview" : "/"} aria-label="InterviewAI dashboard">
        <span className="brand-icon">IA</span>
        <span>Interview<span className="brand-accent">AI</span></span>
      </Link>
      <div className="connection-status" aria-live="polite">
        <span className={`status-dot ${connected ? "connected" : ""}`} />
        <span>{connected ? "Connected" : "Disconnected"}</span>
      </div>
    </header>
  );
}
