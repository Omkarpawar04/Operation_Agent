export default function AIOrb({ state, audioLevel = 0 }) {
  const level = Number.isFinite(audioLevel) ? Math.max(0, Math.min(1, audioLevel)) : 0;
  const isListening = state === "listening" || state === "speech_detected";
  const isSpeaking = state === "interviewer_speaking";
  const shapeLevel = isListening ? level * 0.8 : isSpeaking ? level : 0;
  const activeLevel = isListening || isSpeaking ? level : 0;
  const radiusShift = shapeLevel;

  return (
    <div className={`orb-stage orb-state-${state}`}>
      <div
        className="ai-orb"
        style={{
          "--audio-level": level,
          "--audio-scale": 1 + activeLevel * (isSpeaking ? 0.02 : 0.012),
          "--shape-scale-x": 1 + shapeLevel * 0.016,
          "--shape-scale-y": 1 - shapeLevel * 0.012,
          "--shape-skew-x": `${shapeLevel * (isSpeaking ? 1.2 : 0.45)}deg`,
          "--shape-skew-y": `${shapeLevel * (isSpeaking ? -0.85 : -0.35)}deg`,
          "--shape-rotate-x": `${shapeLevel * (isSpeaking ? 1.8 : 0.7)}deg`,
          "--shape-rotate-y": `${shapeLevel * (isSpeaking ? -1.5 : 0.7)}deg`,
          "--shape-rotate-z": `${shapeLevel * (isSpeaking ? 1.2 : 0.6)}deg`,
          "--orb-radius": `${50 + radiusShift}% ${50 - radiusShift}% ${50 + radiusShift * 0.7}% ${50 - radiusShift * 0.7}% / ${50 - radiusShift * 0.55}% ${50 + radiusShift * 0.55}% ${50 - radiusShift * 0.5}% ${50 + radiusShift * 0.5}%`,
          "--fluid-scale": 1 + activeLevel * (isSpeaking ? 0.12 : 0.07),
          "--fluid-saturation": 1.08 + activeLevel * 0.28,
          "--white-cloud-opacity": 0.56 + activeLevel * 0.12,
          "--white-cloud-secondary-opacity": 0.44 + activeLevel * 0.1,
          "--blue-cloud-opacity": 0.74 + activeLevel * 0.17,
          "--deep-cloud-opacity": 0.4 + activeLevel * 0.2,
          "--orb-brightness": 1 + activeLevel * (isSpeaking ? 0.035 : 0.02),
          "--highlight-opacity": 0.42 + Math.min(level, 0.6) * 0.06,
        }}
        aria-hidden="true"
      >
        <div className="orb-fluid orb-fluid-one" />
        <div className="orb-fluid orb-fluid-two" />
        <div className="orb-fluid orb-fluid-three" />
        <div className="orb-fluid orb-fluid-four" />
      </div>
    </div>
  );
}
