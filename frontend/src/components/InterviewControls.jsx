export default function InterviewControls({
  onRepeat,
  onToggleListening,
  onNext,
  onEnd,
  listening,
  listeningDisabled,
  busy,
}) {
  return (
    <div className="bottom-controls" aria-label="Interview controls">
      <button type="button" className="control-button" onClick={onRepeat} disabled={busy}>
        <span className="control-icon icon-repeat" aria-hidden="true" /><small>Repeat question</small>
      </button>
      <button
        type="button"
        className={`control-button control-listening${listening ? " is-active" : ""}`}
        onClick={onToggleListening}
        disabled={listeningDisabled}
        aria-pressed={listening}
      >
        <span className="control-icon icon-mic" aria-hidden="true" />
        <small>{listening ? "Stop listening" : "Start listening"}</small>
      </button>
      <button type="button" className="control-button" onClick={onNext} disabled={busy}>
        <span className="control-icon icon-next" aria-hidden="true" /><small>Next question</small>
      </button>
      <button type="button" className="control-button control-end" onClick={onEnd}>
        <span className="control-icon icon-end" aria-hidden="true" /><small>End interview</small>
      </button>
    </div>
  );
}
