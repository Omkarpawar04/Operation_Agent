import { Navigate } from "react-router-dom";
import AIOrb from "../components/AIOrb";
import InterviewControls from "../components/InterviewControls";
import LiveTranscription from "../components/LiveTranscription";
import TranscriptPanel from "../components/TranscriptPanel";
import WebcamPreview from "../components/WebcamPreview";
import { useInterview } from "../hooks/InterviewContext";

function clock(seconds) {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

export default function InterviewRoom() {
  const interview = useInterview();
  if (!interview.sessionActive) return <Navigate to="/" replace />;
  const progress = interview.totalQuestions
    ? Math.min(100, (interview.questionIndex / interview.totalQuestions) * 100)
    : 0;
  const canListen = interview.connected && interview.recordingReady &&
    !interview.recordingRecovery && interview.interviewState !== "error";
  const busy = [
    "connecting",
    "loading_voice",
    "processing_answer",
    "evaluating",
    "generating_response",
    "repeating",
  ].includes(interview.interviewState) || interview.questionActionPending ||
    !interview.connected || interview.interviewState === "error";

  return (
    <section className="interview-screen">
      <div className="interview-heading">
        <div>
          <span className="eyebrow">LIVE VOICE SESSION</span>
          <h1>{interview.jobTitle}</h1>
        </div>
      </div>
      <div className="voice-room" aria-label="Interview">
        <div className="session-summary">
          <span className="session-role">AI-guided interview</span>
          <div className="interview-metrics">
            <span>Question {interview.questionIndex} of {interview.totalQuestions || "…"}</span>
            <span>{clock(interview.elapsedSeconds)} elapsed</span>
          </div>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-label="Interview progress"
          aria-valuenow={Math.round(progress)}
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <div id="progressBar" style={{ width: `${progress}%` }} />
        </div>
        <div className="interview-stage">
          <div className="orb-column">
            <span className="interviewer-caption">AI INTERVIEWER</span>
            <AIOrb state={interview.activityState} audioLevel={interview.audioLevel} />
            <div className={`activity-status activity-${interview.activityState}`} role="status" aria-live="polite">
              <span className="activity-indicator" aria-hidden="true" />
              <span>{interview.activityLabel}</span>
            </div>
          </div>
          <div className="camera-column">
            <span className="interviewer-caption">YOUR CAMERA</span>
            <WebcamPreview monitor={interview.monitoring} />
            <LiveTranscription
              segments={interview.liveTranscription.segments}
              finalText={interview.liveTranscription.finalText}
              active={interview.liveTranscription.active}
              processing={interview.liveTranscription.processing}
              error={interview.liveTranscription.error}
              micAvailable={interview.recordingReady && interview.micEnabled && !interview.recordingRecovery}
            />
          </div>
        </div>
        <div className="question-card" aria-live="polite">
          <span className="question-kicker">CURRENT QUESTION</span>
          <p>{interview.currentQuestion || "Your interviewer is getting ready…"}</p>
        </div>
        <div className="recording-indicator" role="status">
          <span className={interview.recordingReady ? "recording-dot is-live" : "recording-dot"} />
          {interview.recordingReady ? "Recording active · consent confirmed" : "Recording paused"}
          <button type="button" className="withdraw-consent" onClick={() => interview.updateRecordingConsent(false)} disabled={!interview.recordingConsentAccepted}>Withdraw consent</button>
        </div>
        {interview.recordingRecovery && (
          <div className="recording-recovery" role="alert">
            <strong>{interview.recordingPending ? "Restoring recording access" : "Interview paused"}</strong>
            {interview.recordingConsentAccepted ? (
              <>
                <p>Recording has been interrupted because browser access was lost. Please restore recording access to continue your interview.</p>
                {interview.recordingError && interview.recordingError !== "Recording has been interrupted because browser access was lost. Please restore recording access to continue your interview." && <p className="error-message">{interview.recordingError}</p>}
              </>
            ) : (
              <p>{interview.recordingError || "Recording consent is required to continue."}</p>
            )}
            {interview.recordingConsentAccepted ? (
              <button type="button" className="secondary-button" onClick={interview.restoreRecording} disabled={interview.recordingPending}>
                {interview.recordingPending ? "Restoring recording…" : "Restore Recording"}
              </button>
            ) : (
              <label className="recording-consent-choice">
                <input type="checkbox" onChange={(event) => interview.updateRecordingConsent(event.target.checked)} disabled={interview.recordingPending} />
                <span>I explicitly consent again and want to restore audio/video recording.</span>
              </label>
            )}
          </div>
        )}
        <TranscriptPanel captions={interview.captions} />
        <InterviewControls
          onRepeat={interview.repeatQuestion}
          onToggleListening={interview.toggleMicrophone}
          onNext={interview.nextQuestion}
          onEnd={interview.endInterview}
          listening={interview.micEnabled}
          listeningDisabled={!canListen}
          busy={busy || interview.recordingRecovery || !interview.recordingReady}
        />
        <p className="voice-note">
          Camera and microphone recording must remain active throughout the interview.
        </p>
        {interview.setupError && (
          <p className="error-message" role="alert">
            {interview.setupError}
          </p>
        )}
      </div>
    </section>
  );
}
