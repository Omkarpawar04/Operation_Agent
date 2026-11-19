export type NeuralOrbState = 'idle' | 'speaking' | 'ready' | 'listening' | 'processing' | 'error';

const STATE_LABELS: Record<NeuralOrbState, string> = {
  idle: 'INITIALIZING',
  speaking: 'SPEAKING QUESTION',
  ready: 'READY FOR YOUR ANSWER',
  listening: 'LISTENING',
  processing: 'PROCESSING RESPONSE',
  error: 'ATTENTION NEEDED',
};

/** Markup for the lifecycle-driven orb used by the production interview screen. */
export function renderNeuralOrb(state: NeuralOrbState): string {
  return `<section class="neural-stage" aria-label="Interview state: ${STATE_LABELS[state]}">
    <div class="neural-orb" aria-hidden="true"><span class="orb-core"></span><i class="orb-particle orb-particle-one"></i><i class="orb-particle orb-particle-two"></i></div>
    <div class="orb-state" role="status" aria-live="polite">${STATE_LABELS[state]}</div>
    <div class="audio-wave" aria-hidden="true">${Array.from({ length: 25 }, (_, index) => `<i style="--bar:${(index % 5) + 1}"></i>`).join('')}</div>
  </section>`;
}
