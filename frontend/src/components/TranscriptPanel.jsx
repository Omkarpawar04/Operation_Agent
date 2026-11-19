export default function TranscriptPanel({ captions }) {
  return (
    <details className="transcript-panel">
      <summary>Live transcript <span>Expand</span></summary>
      <div className="captions" aria-live="polite" aria-label="Read-only interview transcript">
        {captions.map((entry) => (
          <div className={`message ${entry.speaker === "You" ? "user" : "assistant"}`} key={entry.id}>
            <span className="message-label">{entry.speaker}</span>
            <span>{entry.text}</span>
          </div>
        ))}
      </div>
    </details>
  );
}
