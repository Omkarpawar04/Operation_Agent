import { useEffect, useMemo, useRef } from "react";

function normalizeWord(word) {
  return word.toLocaleLowerCase().replace(/[^\w']/g, "");
}

function mergeSegments(segments) {
  const words = [];

  for (const segment of [...segments].sort((a, b) => a.sequence - b.sequence)) {
    const nextWords = segment.text.trim().split(/\s+/).filter(Boolean);
    if (!nextWords.length) continue;

    const maxOverlap = Math.min(words.length, nextWords.length, 14);
    let overlap = 0;
    for (let count = maxOverlap; count > 0; count -= 1) {
      const previous = words.slice(-count);
      if (previous.every((word, index) =>
        normalizeWord(word) === normalizeWord(nextWords[index]))) {
        overlap = count;
        break;
      }
    }

    words.push(...nextWords.slice(overlap));
  }

  return words.join(" ");
}

export default function LiveTranscription({
  segments,
  finalText,
  active,
  processing,
  error,
  micAvailable,
}) {
  const contentRef = useRef(null);
  const interimText = useMemo(() => mergeSegments(segments), [segments]);

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [finalText, interimText]);

  return (
    <section className="live-transcription-panel" aria-label="Live Transcription">
      <header className="live-transcription-header">
        <h2>Live Transcription</h2>
        {active && micAvailable && (
          <span className="live-transcription-badge">
            <span aria-hidden="true" />
            LIVE
          </span>
        )}
      </header>
      <div className="live-transcription-content" ref={contentRef} aria-live="polite">
        {finalText && <p className="live-transcription-final">{finalText}</p>}
        {interimText && (
          <p className="live-transcription-interim">
            {interimText}<span className="live-transcription-cursor" aria-hidden="true" />
          </p>
        )}
        {!finalText && !interimText && (
          <p className="live-transcription-placeholder">
            {!micAvailable
              ? "Microphone access is unavailable. The interview recording is unaffected."
              : processing
                ? "Processing the latest speech…"
                : active
                  ? "Listening for recognized words…"
                  : "Your recognized words will appear here as you speak."}
          </p>
        )}
      </div>
      {error ? (
        <span className="live-transcription-error">
          Live captions are temporarily unavailable. Your recorded answer is safe.
        </span>
      ) : processing && (finalText || interimText) ? (
        <span className="live-transcription-processing">Updating transcription…</span>
      ) : null}
    </section>
  );
}
