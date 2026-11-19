import { useCallback, useEffect, useRef, useState } from "react";

const timestamp = () =>
  new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

export function useMonitoring(active) {
  const activeRef = useRef(active);
  const wasActiveRef = useRef(active);
  const cameraStreamRef = useRef(null);
  const cameraStartRef = useRef(null);
  const cameraOperationRef = useRef(0);
  const screenStreamRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const recordingSegmentsRef = useRef([]);
  const discardRef = useRef(false);
  const timerRef = useRef(null);
  const lastEventsRef = useRef(new Map());
  const lastSnapshotRef = useRef(0);
  const cameraVideoRef = useRef(null);
  const screenVideoRef = useRef(null);
  const recordingUrlRef = useRef(null);
  const recordingConsentRef = useRef(false);

  const [cameraOn, setCameraOn] = useState(false);
  const [cameraPaused, setCameraPaused] = useState(false);
  const [cameraPending, setCameraPending] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [screenOn, setScreenOn] = useState(false);
  const [recording, setRecording] = useState(false);
  const [cameraConsent, setCameraConsent] = useState(false);
  const [screenConsent, setScreenConsent] = useState(false);
  const [recordingConsent, setRecordingConsent] = useState(false);
  const [captureInterval, setCaptureInterval] = useState(60);
  const [timeline, setTimeline] = useState([]);
  const [snapshotCount, setSnapshotCount] = useState(0);
  const [recordingUrl, setRecordingUrl] = useState("");
  const [cameraStatus, setCameraStatus] = useState("Off");
  const [screenStatus, setScreenStatus] = useState("Not shared");

  const updateRecordingConsent = useCallback((accepted) => {
    recordingConsentRef.current = accepted === true;
    setRecordingConsent(recordingConsentRef.current);
  }, []);

  activeRef.current = active;

  const captureSnapshot = useCallback(
    (kind, label) => {
      if (!activeRef.current) return;
      const stream =
        kind === "screen" ? screenStreamRef.current : cameraStreamRef.current;
      const video =
        kind === "screen" ? screenVideoRef.current : cameraVideoRef.current;
      const consented = kind === "screen" ? screenConsent : cameraConsent;
      if (
        !consented ||
        !stream
          ?.getVideoTracks()
          .some((track) => track.readyState === "live") ||
        !video ||
        video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
        !video.videoWidth ||
        !video.videoHeight
      )
        return;
      const scale = Math.min(1, 1280 / video.videoWidth);
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
      canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
      const context = canvas.getContext("2d", { alpha: false });
      if (!context) return;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => {
          if (!blob || !activeRef.current) return;
          const entry = {
            type: "snapshot",
            label: `${label} · ${kind}`,
            time: Date.now(),
            blob,
          };
          setTimeline((items) => [...items, entry].slice(-100));
          setSnapshotCount((count) => Math.min(50, count + 1));
        },
        "image/jpeg",
        0.82,
      );
    },
    [cameraConsent, screenConsent],
  );

  const recordEvent = useCallback(
    (type, label) => {
      if (!activeRef.current) return;
      const now = Date.now();
      if (now - (lastEventsRef.current.get(type) || 0) < 3000) return;
      lastEventsRef.current.set(type, now);
      setTimeline((items) =>
        [...items, { type, label, time: now }].slice(-100),
      );
      const candidate =
        screenConsent && screenStreamRef.current
          ? { kind: "screen", stream: screenStreamRef.current }
          : cameraConsent && cameraStreamRef.current
            ? { kind: "camera", stream: cameraStreamRef.current }
            : null;
      if (
        candidate?.stream
          .getVideoTracks()
          .some((track) => track.readyState === "live") &&
        now - lastSnapshotRef.current >= 3000
      ) {
        lastSnapshotRef.current = now;
        captureSnapshot(candidate.kind, "Event snapshot");
      }
    },
    [cameraConsent, captureSnapshot, screenConsent],
  );

  const stopRecording = useCallback((discard = false) => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    discardRef.current = discard;
    recorder.stop();
  }, []);

  const stopCamera = useCallback(
    (log = true) => {
      cameraOperationRef.current += 1;
      const stream = cameraStreamRef.current;
      cameraStreamRef.current = null;
      stream?.getVideoTracks().forEach((track) => track.stop());
      if (cameraVideoRef.current) {
        cameraVideoRef.current.pause();
        cameraVideoRef.current.srcObject = null;
      }
      setCameraOn(false);
      setCameraStatus("Off");
      setCameraPaused(false);
      setCameraPending(false);
      setCameraError("");
      if (log && stream)
        recordEvent("camera_stopped", "Camera disabled by candidate");
    },
    [recordEvent],
  );

  const pauseCamera = useCallback(() => {
    cameraOperationRef.current += 1;
    const stream = cameraStreamRef.current;
    const wasLive = stream
      ?.getVideoTracks()
      .some((track) => track.readyState === "live");
    cameraStreamRef.current = null;
    stream?.getVideoTracks().forEach((track) => track.stop());
    if (cameraVideoRef.current) {
      cameraVideoRef.current.pause();
      cameraVideoRef.current.srcObject = null;
    }
    setCameraOn(false);
    setCameraPaused(true);
    setCameraPending(false);
    setCameraStatus("Paused");
    setCameraError("");
    if (wasLive) {
      recordEvent("camera_paused", "Camera temporarily paused by candidate");
    }
  }, [recordEvent]);

  const stopScreenShare = useCallback(
    (log = true) => {
      const stream = screenStreamRef.current;
      screenStreamRef.current = null;
      stream?.getTracks().forEach((track) => track.stop());
      if (screenVideoRef.current) {
        screenVideoRef.current.pause();
        screenVideoRef.current.srcObject = null;
      }
      setScreenOn(false);
      setScreenStatus("Not shared");
      if (log && stream)
        recordEvent("screen_share_stopped", "Screen sharing stopped");
    },
    [recordEvent],
  );

  const stopAll = useCallback(() => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = null;
    stopRecording(true);
    const cameraStream = cameraStreamRef.current;
    stopCamera(false);
    cameraStream?.getAudioTracks().forEach((track) => track.stop());
    stopScreenShare(false);
    setTimeline([]);
    setSnapshotCount(0);
    recordingSegmentsRef.current = [];
    if (recordingUrlRef.current) URL.revokeObjectURL(recordingUrlRef.current);
    recordingUrlRef.current = null;
    setRecordingUrl("");
    setRecording(false);
    setCameraConsent(false);
    setScreenConsent(false);
    updateRecordingConsent(false);
    setCameraStatus("Off");
    setScreenStatus("Not shared");
  }, [stopCamera, stopRecording, stopScreenShare, updateRecordingConsent]);

  const startCamera = useCallback(
    async (providedStream = null) => {
      if (
        cameraStreamRef.current
          ?.getVideoTracks()
          .some((track) => track.readyState === "live")
      )
        return true;
      if (cameraStartRef.current) return cameraStartRef.current;
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraStatus("Unavailable");
        setCameraError("Camera access is not supported by this browser.");
        recordEvent(
          "camera_unavailable",
          "Camera is not supported by this browser",
        );
        return false;
      }
      setCameraPending(true);
      setCameraError("");
      const operationId = ++cameraOperationRef.current;
      const startPromise = (async () => {
        let stream = providedStream;
        try {
          stream ||= await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: false,
          });
          if (operationId !== cameraOperationRef.current) {
            stream.getVideoTracks().forEach((track) => track.stop());
            return false;
          }
          if (
            !stream
              .getVideoTracks()
              .some((track) => track.readyState === "live")
          ) {
            throw new Error("The browser did not provide a live camera track.");
          }

          cameraStreamRef.current = stream;
          stream.getVideoTracks().forEach((track) =>
            track.addEventListener(
              "ended",
              () => {
                if (cameraStreamRef.current === stream) {
                  recordEvent(
                    "camera_track_ended",
                    "Camera track ended (permission or device)",
                  );
                  stopCamera(false);
                  setCameraPaused(true);
                  setCameraStatus("Unavailable");
                  setCameraError(
                    "Camera access was interrupted. Use Resume camera to reconnect it.",
                  );
                }
              },
              { once: true },
            ),
          );
          stream.getAudioTracks().forEach((track) =>
            track.addEventListener(
              "ended",
              () => {
                if (cameraStreamRef.current === stream) {
                  recordEvent(
                    "microphone_track_ended",
                    "Microphone track ended (permission or device)",
                  );
                  stopRecording(false);
                }
              },
              { once: true },
            ),
          );
          if (cameraVideoRef.current) {
            cameraVideoRef.current.srcObject = stream;
            await cameraVideoRef.current.play().catch(() => {});
          }
          if (operationId !== cameraOperationRef.current) {
            stream.getVideoTracks().forEach((track) => track.stop());
            if (cameraStreamRef.current === stream)
              cameraStreamRef.current = null;
            return false;
          }
          setCameraOn(true);
          setCameraPaused(false);
          setCameraStatus("On");
          setCameraError("");
          recordEvent("camera_started", "Camera enabled by candidate");
          return true;
        } catch (error) {
          if (stream && cameraStreamRef.current !== stream)
            stream.getVideoTracks().forEach((track) => track.stop());
          const message =
            error.name === "NotAllowedError" ||
            error.name === "PermissionDeniedError"
              ? "Camera permission was denied. Allow camera access in your browser and try again."
              : error.name === "NotFoundError"
                ? "No camera was found. Connect a camera and try again."
                : error.name === "NotReadableError" ||
                    error.name === "TrackStartError"
                  ? "The camera is in use by another app or could not start. Close other camera apps and try again."
                  : error.message ||
                    "Camera could not be started. Check the camera and try again.";
          setCameraStatus(
            error.name === "NotAllowedError" ||
              error.name === "PermissionDeniedError"
              ? "Permission denied"
              : "Unavailable",
          );
          setCameraError(message);
          recordEvent("camera_denied", message);
          return false;
        } finally {
          if (operationId === cameraOperationRef.current)
            setCameraPending(false);
        }
      })();
      cameraStartRef.current = startPromise;
      try {
        return await startPromise;
      } finally {
        if (cameraStartRef.current === startPromise)
          cameraStartRef.current = null;
      }
    },
    [recordEvent, stopCamera, stopRecording],
  );

  const resumeCamera = useCallback(() => startCamera(), [startCamera]);

  const startScreenShare = useCallback(async () => {
    if (screenStreamRef.current) {
      stopScreenShare();
      return;
    }
    if (!navigator.mediaDevices?.getDisplayMedia) {
      recordEvent(
        "screen_unavailable",
        "Screen sharing is not supported by this browser",
      );
      return;
    }
    try {
      // getDisplayMedia requires a direct user gesture.
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false,
      });
      if (!activeRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      screenStreamRef.current = stream;
      stream
        .getVideoTracks()
        .forEach((track) =>
          track.addEventListener("ended", () => stopScreenShare(true), {
            once: true,
          }),
        );
      if (screenVideoRef.current) {
        screenVideoRef.current.srcObject = stream;
        await screenVideoRef.current.play().catch(() => {});
      }
      setScreenOn(true);
      setScreenStatus("Sharing");
      recordEvent(
        "screen_share_started",
        "Screen sharing started by candidate",
      );
    } catch (error) {
      setScreenStatus(
        error.name === "NotAllowedError" ? "Not shared" : "Unavailable",
      );
      if (error.name !== "NotAllowedError")
        recordEvent(
          "screen_share_error",
          "Screen sharing could not be started",
        );
    }
  }, [recordEvent, stopScreenShare]);

  const startRecording = useCallback(() => {
    const stream = cameraStreamRef.current;
    if (!recordingConsentRef.current || !stream || !window.MediaRecorder)
      return false;
    try {
      const mimeType = [
        "video/webm;codecs=vp9,opus",
        "video/webm;codecs=vp8,opus",
        "video/webm",
      ].find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(
        stream,
        mimeType ? { mimeType } : undefined,
      );
      recorderRef.current = recorder;
      chunksRef.current = [];
      discardRef.current = false;
      recorder.addEventListener("dataavailable", (event) => {
        if (event.data?.size) chunksRef.current.push(event.data);
      });
      recorder.addEventListener(
        "error",
        () => {
          setRecording(false);
          recordEvent(
            "recording_error",
            "The browser stopped the active recording",
          );
        },
        { once: true },
      );
      recorder.addEventListener(
        "stop",
        () => {
          setRecording(false);
          if (!discardRef.current && chunksRef.current.length) {
            const segment = new Blob(chunksRef.current, {
              type: recorder.mimeType || "video/webm",
            });
            recordingSegmentsRef.current.push(segment);
            const blob = new Blob(recordingSegmentsRef.current, {
              type: recorder.mimeType || "video/webm",
            });
            if (recordingUrlRef.current)
              URL.revokeObjectURL(recordingUrlRef.current);
            const url = URL.createObjectURL(blob);
            recordingUrlRef.current = url;
            setRecordingUrl(url);
          } else chunksRef.current = [];
          if (!discardRef.current)
            recordEvent("recording_stopped", "Local video recording stopped");
        },
        { once: true },
      );
      recorder.start(1000);
      setRecording(true);
      recordEvent(
        "recording_started",
        "Local audio/video recording started with consent",
      );
      return true;
    } catch {
      recordEvent(
        "recording_error",
        "Local video recording could not be started",
      );
      return false;
    }
  }, [recordEvent, recordingConsent]);

  const waitForRecordingData = useCallback(
    (timeoutMs = 15000) =>
      new Promise((resolve) => {
        const recorder = recorderRef.current;
        if (!recorder || recorder.state !== "recording") {
          resolve({
            captured: false,
            error: "The browser did not leave the recording state.",
          });
          return;
        }
        if (chunksRef.current.some((chunk) => chunk.size > 0)) {
          resolve({ captured: true, error: "" });
          return;
        }

        let settled = false;
        let timeout;
        let requestTimer;
        const finish = (captured, error = "") => {
          if (settled) return;
          settled = true;
          window.clearTimeout(timeout);
          window.clearInterval(requestTimer);
          recorder.removeEventListener("dataavailable", onData);
          recorder.removeEventListener("error", onFailure);
          recorder.removeEventListener("stop", onFailure);
          resolve({
            captured: captured && recorder.state === "recording",
            error:
              error ||
              (recorder.state === "recording"
                ? ""
                : "The browser stopped the recorder unexpectedly."),
          });
        };
        const onData = (event) => {
          if (event.data?.size > 0) finish(true);
        };
        const onFailure = () =>
          finish(
            false,
            recorder.error?.message ||
              "The browser reported a MediaRecorder error.",
          );
        timeout = window.setTimeout(
          () =>
            finish(
              false,
              "No recording data arrived from the camera or microphone.",
            ),
          timeoutMs,
        );
        recorder.addEventListener("dataavailable", onData);
        recorder.addEventListener("error", onFailure, { once: true });
        recorder.addEventListener("stop", onFailure, { once: true });
        requestTimer = window.setInterval(() => {
          if (recorder.state !== "recording") {
            finish(
              false,
              "The browser stopped the recorder before it produced recording data.",
            );
            return;
          }
          try {
            recorder.requestData();
          } catch {
            finish(
              false,
              "The browser could not read data from the active recorder.",
            );
          }
        }, 2500);
      }),
    [],
  );

  const clearData = useCallback(() => {
    stopRecording(true);
    setTimeline([]);
    setSnapshotCount(0);
    recordingSegmentsRef.current = [];
    if (recordingUrlRef.current) URL.revokeObjectURL(recordingUrlRef.current);
    recordingUrlRef.current = null;
    setRecordingUrl("");
    lastEventsRef.current.clear();
    lastSnapshotRef.current = 0;
  }, [stopRecording]);

  useEffect(() => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = null;
    if (!active) return undefined;
    if ((cameraConsent && cameraOn) || (screenConsent && screenOn)) {
      timerRef.current = window.setInterval(() => {
        if (cameraConsent && cameraStreamRef.current)
          captureSnapshot("camera", "Periodic snapshot");
        if (screenConsent && screenStreamRef.current)
          captureSnapshot("screen", "Periodic snapshot");
      }, captureInterval * 1000);
    }
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [
    active,
    cameraConsent,
    cameraOn,
    captureInterval,
    captureSnapshot,
    screenConsent,
    screenOn,
  ]);

  useEffect(() => {
    if (!active) {
      if (wasActiveRef.current) stopAll();
      wasActiveRef.current = false;
      return undefined;
    }
    wasActiveRef.current = true;
    const handleVisibility = () => {
      if (document.visibilityState === "hidden")
        recordEvent("tab_hidden", "Interview tab became hidden");
    };
    const handleBlur = () =>
      recordEvent("window_blur", "Interview window lost focus");
    const handleFullscreen = () => {
      if (!document.fullscreenElement)
        recordEvent("fullscreen_exited", "Fullscreen mode was exited");
    };
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("blur", handleBlur);
    document.addEventListener("fullscreenchange", handleFullscreen);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("blur", handleBlur);
      document.removeEventListener("fullscreenchange", handleFullscreen);
    };
  }, [active, recordEvent, stopAll]);

  useEffect(
    () => () => {
      cameraOperationRef.current += 1;
      if (timerRef.current) window.clearInterval(timerRef.current);
      recorderRef.current?.stop?.();
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
      screenStreamRef.current?.getTracks().forEach((track) => track.stop());
      if (recordingUrlRef.current) URL.revokeObjectURL(recordingUrlRef.current);
    },
    [],
  );

  const downloadRecording = useCallback(() => {
    if (!recordingUrl) return;
    const link = document.createElement("a");
    link.href = recordingUrl;
    link.download = `interview-recording-${Date.now()}.webm`;
    link.click();
  }, [recordingUrl]);

  return {
    cameraOn,
    cameraPaused,
    cameraPending,
    cameraError,
    screenOn,
    recording,
    cameraStatus,
    screenStatus,
    cameraConsent,
    setCameraConsent,
    screenConsent,
    setScreenConsent,
    recordingConsent,
    setRecordingConsent: updateRecordingConsent,
    captureInterval,
    setCaptureInterval,
    timeline,
    snapshotCount,
    recordingUrl,
    cameraVideoRef,
    cameraStream: cameraStreamRef.current,
    screenVideoRef,
    startCamera,
    resumeCamera,
    pauseCamera,
    stopCamera,
    startScreenShare,
    startRecording,
    waitForRecordingData,
    stopRecording,
    clearData,
    stopAll,
    recordEvent,
    downloadRecording,
  };
}
