import { useEffect, useRef, useState } from "react";
import { previewVoice } from "../services/api";

export default function VoicePicker({ voices, defaultVoice, value, onChange }) {
  const audioRef = useRef(null);
  const contextRef = useRef(null);
  const requestRef = useRef(0);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const selected = voices.find((voice) => voice.id === value);

  function stopPreview() {
    requestRef.current += 1;
    if (audioRef.current) {
      try { audioRef.current.stop(); } catch { /* already stopped */ }
      audioRef.current.disconnect();
      audioRef.current = null;
    }
    setPending(false);
  }

  useEffect(() => () => {
    requestRef.current += 1;
    try { audioRef.current?.stop(); } catch { /* already stopped */ }
    audioRef.current?.disconnect();
    contextRef.current?.close().catch(() => {});
  }, []);

  async function preview() {
    stopPreview();
    const request = requestRef.current;
    const voiceId = value || defaultVoice;
    setError("");
    setPending(true);
    try {
      const AudioCtor = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtor) throw new Error("This browser does not support audio playback.");
      contextRef.current ||= new AudioCtor();
      await contextRef.current.resume();
      const blob = await previewVoice(voiceId);
      if (request !== requestRef.current) return;
      const bytes = await blob.arrayBuffer();
      const buffer = await contextRef.current.decodeAudioData(bytes);
      if (request !== requestRef.current) return;
      const source = contextRef.current.createBufferSource();
      source.buffer = buffer;
      source.connect(contextRef.current.destination);
      audioRef.current = source;
      source.onended = () => {
        if (audioRef.current === source) { audioRef.current = null; setPending(false); }
      };
      source.start();
    } catch (cause) {
      if (request === requestRef.current) setError(cause.message || "Voice preview failed.");
    } finally {
      if (request === requestRef.current) setPending(false);
    }
  }

  return (
    <div className="field-group">
      <label htmlFor="ttsVoice">Interviewer voice</label>
      <div className="voice-picker">
        <select id="ttsVoice" value={value || defaultVoice} onChange={(event) => { stopPreview(); onChange(event.target.value); }} disabled={!voices.length}>
          {voices.map((voice) => <option key={voice.id} value={voice.id}>{voice.name} ({voice.id}) · {voice.accent}</option>)}
        </select>
        <button type="button" className="secondary-button" onClick={preview} disabled={!voices.length || pending}>
          {pending ? "Playing…" : "Preview"}
        </button>
      </div>
      <p className="field-hint" role="status">{selected ? `${selected.name} · ${selected.id} · Verified accent: ${selected.accent}` : "Loading supported Kokoro voices…"}</p>
      {error && <p className="error-message" role="alert">{error}</p>}
    </div>
  );
}
