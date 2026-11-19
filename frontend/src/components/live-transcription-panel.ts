export interface LiveTranscriptionPanelOptions {
  finalTranscript: string;
  interimTranscript: string;
  listening: boolean;
  supported: boolean;
  microphoneState: string;
}

function escapeHtml(value: string): string {
  const element = document.createElement('span');
  element.textContent = value;
  return element.innerHTML;
}

/** Read-only display of text produced by the browser's speech recognition API. */
export function renderLiveTranscriptionPanel(options: LiveTranscriptionPanelOptions): string {
  const recognizedText = `${options.finalTranscript} ${options.interimTranscript}`.trim();
  const micLabel = options.listening
    ? 'MICROPHONE ACTIVE'
    : options.microphoneState === 'denied'
      ? 'MICROPHONE PERMISSION DENIED'
      : options.supported
        ? 'MICROPHONE STANDBY'
        : 'RECOGNITION UNSUPPORTED';

  return `<section class="finxl-transcript-box" aria-live="polite" aria-label="Live spoken transcript">
    <div class="transcript-heading"><span>LIVE TRANSCRIPTION</span><span class="mic-state ${options.listening ? 'active' : ''}" role="status">${micLabel}</span></div>
    <div class="transcript-content" aria-label="Recognized speech"><span class="transcript-final">${escapeHtml(options.finalTranscript)}</span><span class="transcript-interim">${options.interimTranscript ? ` ${escapeHtml(options.interimTranscript)}` : ''}</span>${recognizedText ? '' : '<span class="transcript-empty">Your recognized speech will appear here when you start speaking.</span>'}</div>
    <div class="transcript-meta">${recognizedText ? `${recognizedText.split(/\s+/).length} WORDS RECOGNIZED` : 'VOICE INPUT · READ ONLY'}</div>
  </section>`;
}
