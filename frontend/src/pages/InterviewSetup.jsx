import { useState } from "react";
import { extractDocument } from "../services/api";
import VoicePicker from "../components/VoicePicker";
import { useInterview } from "../hooks/InterviewContext";

function HistoryList() {
  const { history, historyLoading, connected, openReport, resumeInterview, recordingReady } = useInterview();
  if (historyLoading) return <p className="muted">Loading interview history…</p>;
  if (!history.length) return <p className="muted">Your completed interviews and saved sessions will appear here.</p>;
  return (
    <div className="history-list">
      {history.map((item) => (
        <article className="history-row" key={item.id}>
          <div className="history-description">
            <strong>{item.candidate_name || "Candidate"}</strong>
            <span>{item.job_title || "Interview"} · {item.status.replaceAll("_", " ")}</span>
          </div>
          {item.status === "completed" ? (
            <button type="button" className="outline-button" onClick={() => openReport(item.id)}>View report</button>
          ) : item.status === "in_progress" ? (
            <button type="button" className="outline-button" disabled={!connected || !recordingReady} onClick={() => resumeInterview(item.id)}>Resume</button>
          ) : null}
        </article>
      ))}
    </div>
  );
}

export default function InterviewSetup() {
  const { connected, health, voices, defaultVoice, startInterview, setupError, setSetupError, startPending,
    recordingConsentAccepted, recordingReady, recordingPending, recordingRecovery, recordingError,
    updateRecordingConsent, restoreRecording } = useInterview();
  const [candidateName, setCandidateName] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [resumeFile, setResumeFile] = useState(null);
  const [jobFile, setJobFile] = useState(null);
  const [voiceId, setVoiceId] = useState("");
  const [extracting, setExtracting] = useState(false);

  async function readFile(file, setter) {
    if (!file) return;
    setSetupError("");
    setExtracting(true);
    try { setter(await extractDocument(file)); }
    catch (error) { setSetupError(error.message || "Document extraction failed."); }
    finally { setExtracting(false); }
  }

  async function submit(event) {
    event.preventDefault();
    let resume = resumeText;
    let job = jobDescription;
    try {
      if (resumeFile && !resume.trim()) resume = await extractDocument(resumeFile);
      if (jobFile && !job.trim()) job = await extractDocument(jobFile);
      await startInterview({ candidateName, resumeText: resume, jobDescription: job, voiceId: voiceId || defaultVoice });
    } catch (error) { setSetupError(error.message || "Could not prepare the interview."); }
  }

  const voiceReady = Array.isArray(voices) && voices.length > 0;
  const servicesReady = health?.voice_available === true;
  const canStart = connected && voiceReady && servicesReady && recordingReady && recordingConsentAccepted && !recordingPending && !startPending && !extracting;

  return (
    <div className="dashboard-page">
      <section className="hero">
        <span className="eyebrow">VOICE-FIRST MOCK INTERVIEW</span>
        <h1>Practice smarter.<br /><span>Interview confidently.</span></h1>
        <p>Prepare with a conversational AI interviewer, tailored to your experience and the role you want.</p>
      </section>

      <section className="setup-card" aria-labelledby="setupTitle">
        <div className="section-heading">
          <div><span className="eyebrow">PERSONALIZED PRACTICE</span><h2 id="setupTitle">Prepare your interview</h2></div>
          <span className={`connection-chip ${connected ? "ready" : ""}`}><i />{connected ? "Connected" : "Connecting"}</span>
        </div>
        <p className="muted">Share your background and target role. Camera, microphone, and recording must be ready before the interview can start.</p>
        <form onSubmit={submit}>
          <section className="recording-consent-card" aria-labelledby="recordingConsentTitle">
            <span className="eyebrow">REQUIRED BEFORE START</span>
            <h3 id="recordingConsentTitle">Recording and data use</h3>
            <p>Your camera video, microphone audio, and periodic camera snapshots will be recorded locally for this session. Microphone audio is also streamed for transcription. Your resume and job details are processed for interview planning, and your answers and transcript are saved with the session for the interview and report. Screen sharing is not enabled for this interview.</p>
            <label className="recording-consent-choice">
              <input type="checkbox" checked={recordingConsentAccepted} onChange={(event) => updateRecordingConsent(event.target.checked)} disabled={recordingPending} />
              <span>I have read this notice and explicitly consent to audio/video recording and processing of my interview data.</span>
            </label>
            <p className="recording-setup-status" role="status">{recordingPending ? "Requesting camera and microphone access and starting the recording…" : recordingReady ? "Camera, microphone, consent, and recording are ready." : recordingConsentAccepted ? "Complete camera and microphone setup to continue." : "Consent and camera/microphone permission are required."}</p>
            {recordingError && <p className="error-message" role="alert">{recordingError}</p>}
            {recordingConsentAccepted && recordingRecovery && (
              <button type="button" className="secondary-button" onClick={restoreRecording} disabled={recordingPending}>
                {recordingPending ? "Restoring recording…" : "Restore Recording"}
              </button>
            )}
          </section>
          <label htmlFor="candidateName">Your name <span className="optional-label">Optional</span></label>
          <input id="candidateName" value={candidateName} onChange={(event) => setCandidateName(event.target.value)} placeholder="Enter your name" maxLength={200} autoComplete="name" />

          <label htmlFor="resumeFile">Resume <span className="optional-label">TXT, PDF, DOCX or paste text</span></label>
          <input id="resumeFile" type="file" accept=".txt,.pdf,.docx" onChange={(event) => { setResumeFile(event.target.files?.[0] || null); readFile(event.target.files?.[0], setResumeText); }} />
          <textarea id="resumeText" rows={5} value={resumeText} onChange={(event) => setResumeText(event.target.value)} placeholder="Paste your resume text here…" />

          <label htmlFor="jobFile">Job description <span className="optional-label">TXT, PDF, DOCX or paste text</span></label>
          <input id="jobFile" type="file" accept=".txt,.pdf,.docx" onChange={(event) => { setJobFile(event.target.files?.[0] || null); readFile(event.target.files?.[0], setJobDescription); }} />
          <textarea id="jobDescription" rows={5} value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} placeholder="Paste the job description here…" />

          <VoicePicker voices={voices} defaultVoice={defaultVoice} value={voiceId || defaultVoice} onChange={setVoiceId} />
          {setupError && <p className="error-message" role="alert">{setupError}</p>}
          {!servicesReady && health && <p className="error-message" role="status">Voice interview unavailable: {(health.voice_missing || ["voice services"]).join(" and ")} must be configured.</p>}
          <button type="submit" className="primary-button start-interview-button" disabled={!canStart}>
            {startPending ? "Preparing your interview…" : extracting ? "Reading your document…" : "Start Interview"}
          </button>
          <p className="form-footnote">Resume and job description are sent to the interview service to tailor your questions.</p>
        </form>
      </section>

      <section className="history-panel" aria-labelledby="historyTitle">
        <div className="section-heading"><div><span className="eyebrow">YOUR PRACTICE</span><h2 id="historyTitle">Interview history</h2></div></div>
        <HistoryList />
      </section>
    </div>
  );
}
