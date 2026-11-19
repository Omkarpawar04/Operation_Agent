function formatTime(value) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function MonitoringPanel({ monitor, speakerEnabled, onToggleSpeaker }) {
  return (
    <aside className="monitor-panel" aria-label="Candidate-controlled monitoring">
      <div className="monitor-heading">
        <div><span className="eyebrow">PRIVACY CONTROLS</span><h2>Session monitoring</h2></div>
        <span className="local-only-badge">LOCAL ONLY</span>
      </div>
      <p className="muted monitor-intro">Optional. Captures stay in this browser session and are never uploaded.</p>

      <div className="monitor-status-grid">
        <div><span>Camera</span><strong className={monitor.cameraOn ? "status-success" : "status-neutral"}>{monitor.cameraStatus}</strong></div>
        <div><span>Screen sharing</span><strong className={monitor.screenOn ? "status-blue" : "status-neutral"}>{monitor.screenStatus}</strong></div>
        <div><span>Recording</span><strong className={monitor.recording ? "status-recording" : "status-neutral"}>{monitor.recording ? "Recording" : "Off"}</strong></div>
        <div><span>Snapshots captured</span><strong className="status-blue">{monitor.snapshotCount}</strong></div>
      </div>

      <label className="consent-row"><input type="checkbox" checked={monitor.cameraConsent} onChange={(event) => monitor.setCameraConsent(event.target.checked)} /><span>Allow camera snapshots during this interview</span></label>
      <label className="consent-row"><input type="checkbox" checked={monitor.screenConsent} onChange={(event) => monitor.setScreenConsent(event.target.checked)} /><span>Allow screen snapshots while sharing</span></label>
      <label className="consent-row"><input type="checkbox" checked={monitor.recordingConsent} onChange={(event) => { monitor.setRecordingConsent(event.target.checked); if (!event.target.checked) monitor.stopRecording(); }} /><span>I consent to local video recording</span></label>

      <label className="interval-control" htmlFor="captureInterval">Snapshot interval</label>
      <select id="captureInterval" value={monitor.captureInterval} onChange={(event) => monitor.setCaptureInterval(Number(event.target.value))}>
        <option value={30}>Every 30 seconds</option><option value={60}>Every 60 seconds</option>
      </select>
      <div className="monitor-actions">
        <button type="button" className="secondary-button" onClick={monitor.startScreenShare} aria-pressed={monitor.screenOn}>{monitor.screenOn ? "Stop screen sharing" : "Share screen"}</button>
        <button type="button" className="secondary-button" onClick={monitor.cameraOn ? monitor.pauseCamera : monitor.cameraPaused ? monitor.resumeCamera : monitor.startCamera} disabled={monitor.cameraPending} aria-pressed={monitor.cameraOn}>
          {monitor.cameraPending ? "Opening camera…" : monitor.cameraOn ? "Pause camera" : monitor.cameraPaused ? "Resume camera" : "Turn camera on"}
        </button>
        {monitor.cameraError && <p className="error-message" role="alert">{monitor.cameraError}</p>}
      </div>
      <div className="speaker-setting"><span>Interviewer audio</span><button type="button" className="text-button" onClick={onToggleSpeaker} aria-pressed={speakerEnabled}>{speakerEnabled ? "Speaker on · Mute" : "Speaker muted · Unmute"}</button></div>
      <div className="recording-actions">
        {monitor.recordingConsent && monitor.cameraOn && (
          <button type="button" className={monitor.recording ? "record-button is-recording" : "record-button"} onClick={() => monitor.recording ? monitor.stopRecording() : monitor.startRecording()}>
            <i />{monitor.recording ? "Stop recording" : "Start recording"}
          </button>
        )}
        {monitor.recordingUrl && <button type="button" className="text-button" onClick={monitor.downloadRecording}>Download local recording</button>}
        <button type="button" className="text-button delete-data" onClick={monitor.clearData}>Delete local monitoring data</button>
      </div>

      <section className="event-section">
        <h3>Integrity event timeline</h3>
        {!monitor.timeline.length ? <p className="muted">No events or snapshots captured.</p> : (
          <ol className="monitor-timeline" aria-live="polite">
            {[...monitor.timeline].sort((a, b) => a.time - b.time).slice(-60).map((entry, index) => (
              <li key={`${entry.time}-${entry.type}-${index}`}><span>{entry.label}</span><time dateTime={new Date(entry.time).toISOString()}>{formatTime(entry.time)}</time></li>
            ))}
          </ol>
        )}
      </section>
      <p className="privacy-note">Events describe browser state only. They do not determine intent or honesty. Data is cleared when the session ends or you delete it.</p>
      <video ref={monitor.screenVideoRef} className="screen-capture-source" autoPlay muted playsInline aria-hidden="true" />
    </aside>
  );
}
