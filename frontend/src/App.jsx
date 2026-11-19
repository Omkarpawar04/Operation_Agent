import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AppHeader from "./components/AppHeader";
import InterviewReport from "./pages/InterviewReport";
import InterviewRoom from "./pages/InterviewRoom";
import InterviewSetup from "./pages/InterviewSetup";
import { InterviewProvider, useInterview } from "./hooks/InterviewContext";
import "./styles/theme.css";
import "./styles/global.css";
import "./styles/interview.css";

function ApplicationShell() {
  const { connected, sessionActive } = useInterview();
  return (
    <div className={`app-shell${sessionActive ? " is-interview-active" : ""}`}>
      <AppHeader connected={connected} sessionActive={sessionActive} />
      <main className="main-content">
        <Routes>
          <Route path="/" element={sessionActive ? <Navigate to="/interview" replace /> : <InterviewSetup />} />
          <Route path="/interview" element={<InterviewRoom />} />
          <Route path="/report" element={<InterviewReport />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer><span>InterviewAI</span><span>Voice-first interview practice</span></footer>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <InterviewProvider><ApplicationShell /></InterviewProvider>
    </BrowserRouter>
  );
}
