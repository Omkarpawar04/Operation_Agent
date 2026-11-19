import { useEffect } from "react";

export default function WebcamPreview({ monitor }) {
  useEffect(() => {
    const video = monitor.cameraVideoRef.current;
    if (!monitor.cameraOn || !video || !monitor.cameraStream) return;
    video.srcObject = monitor.cameraStream;
    video.play().catch(() => {});
  }, [monitor.cameraOn, monitor.cameraStream]);

  return (
    <div className={`camera-tile ${monitor.cameraOn ? "is-live" : "is-off"}`}>
      <video ref={monitor.cameraVideoRef} autoPlay muted playsInline aria-label="Your live camera preview" />
      <span className={`live-indicator ${monitor.cameraOn ? "" : "is-inactive"}`}>
        {monitor.cameraOn ? <i /> : null}
        {monitor.cameraOn ? "Camera live" : monitor.cameraPaused ? "Camera paused" : "Camera off"}
      </span>
      <button
        type="button"
        className="camera-action"
        onClick={monitor.cameraOn ? monitor.pauseCamera : monitor.cameraPaused ? monitor.resumeCamera : monitor.startCamera}
        disabled={monitor.cameraPending}
        aria-pressed={monitor.cameraOn}
      >
        {monitor.cameraPending ? "Opening camera…" : monitor.cameraOn ? "Pause camera" : monitor.cameraPaused ? "Resume camera" : "Turn camera on"}
      </button>
      {monitor.cameraError && <span className="camera-error" role="alert">{monitor.cameraError}</span>}
    </div>
  );
}
