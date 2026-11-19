import { createContext, useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../services/api";
import { createInterviewSocket, sendSocketEvent } from "../services/socket";
import { useMonitoring } from "./useMonitoring";

const InterviewContext = createContext(null);
const RECORDING_INTERRUPTED_MESSAGE = "Recording has been interrupted because browser access was lost. Please restore recording access to continue your interview.";
const EMPTY_LIVE_TRANSCRIPTION = {
  segments: [],
  turnId: null,
  finalText: "",
  active: false,
  processing: false,
  error: false,
};
const STATUS = {
  idle: "Waiting for your response",
  connecting: "Preparing the next question...",
  listening: "Listening to you...",
  speech_detected: "Hearing your response...",
  processing_answer: "Understanding your answer...",
  evaluating: "Evaluating your response...",
  generating_response: "Preparing the next question...",
  loading_voice: "Preparing the next question...",
  repeating: "Repeating the question...",
  interviewer_speaking: "AI interviewer is speaking...",
  interrupted: "Recording interrupted",
  paused: "Recording interrupted",
  restoring: "Restoring recording access...",
  completed: "Interview completed",
  error: "Something went wrong. Please try again.",
};

function resampleAudio(input, inRate, outRate) {
  if (inRate === outRate) return new Float32Array(input);
  const ratio = inRate / outRate;
  const output = new Float32Array(Math.floor(input.length / ratio));
  for (let i = 0; i < output.length; i += 1) {
    const position = i * ratio;
    const left = Math.floor(position);
    const right = Math.min(left + 1, input.length - 1);
    const fraction = position - left;
    output[i] = input[left] * (1 - fraction) + input[right] * fraction;
  }
  return output;
}

function toPcm16(samples) {
  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < samples.length; i += 1) {
    const value = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(i * 2, value < 0 ? value * 32768 : value * 32767, true);
  }
  return buffer;
}

function hasLiveMicrophone(stream) {
  return Boolean(stream?.getAudioTracks().some((track) => track.readyState === "live" && track.enabled));
}

export function InterviewProvider({ children }) {
  const navigate = useNavigate();
  const socketRef = useRef(null);
  const socketEffectGenerationRef = useRef(0);
  const messageHandlerRef = useRef(() => {});
  const sessionIdRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const microphoneSourceRef = useRef(null);
  const microphoneProcessorRef = useRef(null);
  const microphoneGainRef = useRef(null);
  const audioEnabledRef = useRef(false);
  const assistantSpeakingRef = useRef(false);
  const audioGeneratingRef = useRef(false);
  const interruptionSentRef = useRef(false);
  const interruptBlocksRef = useRef(0);
  const micEnabledRef = useRef(true);
  const speakerEnabledRef = useRef(true);
  const outputAnalyserRef = useRef(null);
  const outputGainRef = useRef(null);
  const activeSourcesRef = useRef(new Set());
  const audioQueueTimeRef = useRef(0);
  const inputRateRef = useRef(16000);
  const outputRateRef = useRef(24000);
  const completionTimerRef = useRef(null);
  const audioFrameRef = useRef(0);
  const elapsedStartRef = useRef(0);
  const totalQuestionsRef = useRef(0);
  const currentQuestionRef = useRef(null);
  const questionActionPendingRef = useRef(false);
  const repeatRequestedRef = useRef(false);
  const reportRef = useRef(null);
  const consentAckRef = useRef(null);
  const recordingAckRef = useRef(null);
  const permissionAttemptRef = useRef(0);
  const recordingStartedRef = useRef(false);
  const recordingPausedRef = useRef(false);
  const endingInterviewRef = useRef(false);

  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [sessionActive, setSessionActive] = useState(false);
  const [jobTitle, setJobTitle] = useState("Interview");
  const [interviewState, setInterviewState] = useState("idle");
  const [questionActionPending, setQuestionActionPending] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [micEnabled, setMicEnabled] = useState(true);
  const [speakerEnabled, setSpeakerEnabled] = useState(true);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [captions, setCaptions] = useState([]);
  const [liveTranscription, setLiveTranscription] = useState(EMPTY_LIVE_TRANSCRIPTION);
  const [report, setReport] = useState(null);
  const [reportError, setReportError] = useState("");
  const [setupError, setSetupError] = useState("");
  const [startPending, setStartPending] = useState(false);
  const [health, setHealth] = useState(null);
  const [voices, setVoices] = useState([]);
  const [defaultVoice, setDefaultVoice] = useState("af_heart");
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [evaluationRetryId, setEvaluationRetryId] = useState(null);
  const [recordingConsentAccepted, setRecordingConsentAccepted] = useState(false);
  const [recordingReady, setRecordingReady] = useState(false);
  const [recordingPending, setRecordingPending] = useState(false);
  const [recordingRecovery, setRecordingRecovery] = useState(false);
  const [recordingError, setRecordingError] = useState("");

  const monitoring = useMonitoring(sessionActive);

  function waitForSocketAck(ref, event, payload) {
    return new Promise((resolve, reject) => {
      const timer = window.setTimeout(() => {
        if (ref.current?.timer === timer) ref.current = null;
        reject(new Error("The server did not confirm the recording state. Please try again."));
      }, 10000);
      ref.current = { resolve, reject, timer };
      if (!sendEvent(event, payload)) {
        window.clearTimeout(timer);
        ref.current = null;
        reject(new Error("The server is not connected. Try again shortly."));
      }
    });
  }

  function settleAck(ref, error, value) {
    const pending = ref.current;
    if (!pending) return;
    ref.current = null;
    window.clearTimeout(pending.timer);
    if (error) pending.reject(error);
    else pending.resolve(value);
  }

  function setState(value) { setInterviewState(value); }

  function clearLiveTranscription() {
    setLiveTranscription({ ...EMPTY_LIVE_TRANSCRIPTION });
  }

  function sendEvent(event, payload = {}) {
    return sendSocketEvent(socketRef.current, event, payload);
  }

  function ensureAudioContext() {
    const AudioCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtor) throw new Error("This browser does not support audio.");
    if (!audioContextRef.current || audioContextRef.current.state === "closed") audioContextRef.current = new AudioCtor();
    return audioContextRef.current;
  }

  function stopOutputAudio() {
    for (const source of activeSourcesRef.current) { try { source.stop(); } catch { /* already stopped */ } }
    activeSourcesRef.current.clear();
    audioQueueTimeRef.current = audioContextRef.current?.currentTime || 0;
    assistantSpeakingRef.current = false;
    if (audioFrameRef.current) cancelAnimationFrame(audioFrameRef.current);
    audioFrameRef.current = 0;
    setAudioLevel(0);
  }

  function stopMicrophoneCapture() {
    audioEnabledRef.current = false;
    microphoneProcessorRef.current?.disconnect();
    if (microphoneProcessorRef.current) microphoneProcessorRef.current.onaudioprocess = null;
    microphoneProcessorRef.current = null;
    microphoneSourceRef.current?.disconnect();
    microphoneSourceRef.current = null;
    microphoneGainRef.current?.disconnect();
    microphoneGainRef.current = null;
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    stopOutputAudio();
    if (audioContextRef.current && audioContextRef.current.state !== "closed") audioContextRef.current.close().catch(() => {});
    audioContextRef.current = null;
    outputAnalyserRef.current = null;
    outputGainRef.current = null;
  }

  async function startMicrophoneCapture() {
    if (!mediaStreamRef.current) throw new Error("Microphone permission is required.");
    const audioContext = ensureAudioContext();
    await audioContext.resume();
    if (audioEnabledRef.current) return;
    const source = audioContext.createMediaStreamSource(mediaStreamRef.current);
    const processor = audioContext.createScriptProcessor(2048, 1, 1);
    const gain = audioContext.createGain();
    gain.gain.value = 0;
    processor.onaudioprocess = (event) => {
      const socket = socketRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) return;
      const input = event.inputBuffer.getChannelData(0);
      const rms = Math.sqrt(input.reduce((sum, value) => sum + value * value, 0) / input.length);
      if (!assistantSpeakingRef.current &&
          ["listening", "speech_detected"].includes(interviewStateRef.current) &&
          micEnabledRef.current) {
        setAudioLevel(Math.min(1, rms * 12));
      }
      if (!micEnabledRef.current || (audioGeneratingRef.current && !assistantSpeakingRef.current)) return;
      if (assistantSpeakingRef.current) {
        interruptBlocksRef.current = rms > 0.04 ? interruptBlocksRef.current + 1 : 0;
        if (interruptBlocksRef.current >= 6 && !interruptionSentRef.current) {
          interruptionSentRef.current = true;
          assistantSpeakingRef.current = false;
          stopOutputAudio();
          sendEvent("interrupt", { reason: "microphone activity" });
          setState("speech_detected");
        } else if (assistantSpeakingRef.current) return;
      }
      const pcm = toPcm16(resampleAudio(input, audioContext.sampleRate, inputRateRef.current));
      if (pcm.byteLength) socket.send(pcm);
    };
    source.connect(processor);
    processor.connect(gain);
    gain.connect(audioContext.destination);
    mediaStreamRef.current.getAudioTracks().forEach((track) => track.addEventListener("ended", () => {
      if (audioEnabledRef.current) monitoring.recordEvent("microphone_track_ended", "Microphone track ended (permission or device)");
    }, { once: true }));
    microphoneSourceRef.current = source;
    microphoneProcessorRef.current = processor;
    microphoneGainRef.current = gain;
    audioEnabledRef.current = true;
    setState("listening");
  }

  const interviewStateRef = useRef(interviewState);
  interviewStateRef.current = interviewState;

  const activityState = recordingRecovery
    ? (recordingPending ? "restoring" : "interrupted")
    : (!micEnabled && ["listening", "speech_detected"].includes(interviewState)
      ? "idle"
      : interviewState);
  const activityLabel = STATUS[activityState] || STATUS.error;

  function setQuestionActionPendingState(pending) {
    questionActionPendingRef.current = pending;
    setQuestionActionPending(pending);
  }

  function playAudioChunk(arrayBuffer) {
    const audioContext = audioContextRef.current;
    if (!audioContext || arrayBuffer.byteLength < 2 || !assistantSpeakingRef.current) return;
    const count = Math.floor(arrayBuffer.byteLength / 2);
    const data = new DataView(arrayBuffer);
    const buffer = audioContext.createBuffer(1, count, outputRateRef.current);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < count; i += 1) channel[i] = data.getInt16(i * 2, true) / 32768;
    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    if (!outputAnalyserRef.current) {
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const gain = audioContext.createGain();
      gain.gain.value = speakerEnabledRef.current ? 1 : 0;
      analyser.connect(gain);
      gain.connect(audioContext.destination);
      outputAnalyserRef.current = analyser;
      outputGainRef.current = gain;
    }
    source.connect(outputAnalyserRef.current);
    activeSourcesRef.current.add(source);
    source.onended = () => activeSourcesRef.current.delete(source);
    const startAt = Math.max(audioContext.currentTime + 0.015, audioQueueTimeRef.current);
    source.start(startAt);
    audioQueueTimeRef.current = startAt + buffer.duration;
    repeatRequestedRef.current = false;
    setState("interviewer_speaking");
    animateOrbAudio();
  }

  function animateOrbAudio() {
    const analyser = outputAnalyserRef.current;
    if (!analyser || !assistantSpeakingRef.current || audioFrameRef.current) return;
    const samples = new Uint8Array(analyser.frequencyBinCount);
    let lastUpdate = 0;
    const draw = (time) => {
      if (!assistantSpeakingRef.current || !outputAnalyserRef.current) { audioFrameRef.current = 0; setAudioLevel(0); return; }
      outputAnalyserRef.current.getByteTimeDomainData(samples);
      if (time - lastUpdate > 70) {
        let energy = 0;
        for (const sample of samples) { const value = (sample - 128) / 128; energy += value * value; }
        setAudioLevel(Math.min(1, Math.sqrt(energy / samples.length) * 2.2));
        lastUpdate = time;
      }
      audioFrameRef.current = requestAnimationFrame(draw);
    };
    audioFrameRef.current = requestAnimationFrame(draw);
  }

  function scheduleMicrophoneResume() {
    const audioContext = audioContextRef.current;
    const remaining = audioContext ? Math.max(0, audioQueueTimeRef.current - audioContext.currentTime) : 0;
    window.setTimeout(() => {
      if (assistantSpeakingRef.current && !interruptionSentRef.current) {
        assistantSpeakingRef.current = false;
        setAudioLevel(0);
        setState("listening");
      }
    }, remaining * 1000 + 100);
  }

  function addCaption(speaker, text, updateQuestion = true) {
    const entry = { id: `${Date.now()}-${Math.random()}`, speaker, text };
    setCaptions((items) => [...items, entry].slice(-40));
    if (speaker === "Interviewer" && updateQuestion) setCurrentQuestion(text);
  }

  function updateProgress(questionId, index) {
    if (questionId !== undefined && questionId !== null) currentQuestionRef.current = questionId;
    let number = Number(index);
    if (!Number.isFinite(number) || number < 1) {
      const match = String(currentQuestionRef.current || "").match(/\d+/);
      number = match ? Number(match[0]) : (currentQuestionRef.current ? 1 : 0);
    }
    number = Math.min(number, totalQuestionsRef.current || number);
    setQuestionIndex(number);
  }

  function finishInterviewNow() {
    completionTimerRef.current = null;
    endingInterviewRef.current = true;
    setState("completed");
    recordingStartedRef.current = false;
    recordingPausedRef.current = false;
    sendEvent("recording_status", { active: false });
    sendEvent("recording_consent", { accepted: false });
    setSessionActive(false);
    setRecordingConsentAccepted(false);
    setRecordingReady(false);
    setRecordingRecovery(false);
    if (sessionIdRef.current) setEvaluationRetryId(sessionIdRef.current);
    setSessionId(null);
    sessionIdRef.current = null;
    localStorage.removeItem("interviewSessionId");
    stopMicrophoneCapture();
    navigate("/report");
  }

  function finishInterview() {
    const audioContext = audioContextRef.current;
    if (assistantSpeakingRef.current && audioContext) {
      const remaining = Math.max(0, audioQueueTimeRef.current - audioContext.currentTime);
      if (completionTimerRef.current) window.clearTimeout(completionTimerRef.current);
      completionTimerRef.current = window.setTimeout(finishInterviewNow, remaining * 1000 + 120);
      return;
    }
    finishInterviewNow();
  }

  function renderEvent(data) {
    switch (data.event) {
      case "connection_ready": break;
      case "recording_consent_status":
        if (data.success && data.accepted === true) settleAck(consentAckRef, null, true);
        break;
      case "recording_status":
        if (data.success && data.active === true) settleAck(recordingAckRef, null, true);
        break;
      case "interview_paused":
        setQuestionActionPendingState(false);
        repeatRequestedRef.current = false;
        setLiveTranscription((current) => ({ ...current, active: false, processing: false }));
        recordingPausedRef.current = true;
        recordingStartedRef.current = false;
        setRecordingReady(false);
        setRecordingRecovery(true);
        setRecordingError(data.reason === "consent_withdrawn"
          ? (data.message || "Recording consent was withdrawn. The interview is paused.")
          : RECORDING_INTERRUPTED_MESSAGE);
        setState("paused");
        stopOutputAudio();
        stopMicrophoneCapture();
        break;
      case "planning_started": setSetupError(""); setStartPending(true); break;
      case "interview_started": {
        sessionIdRef.current = data.session_id;
        setSessionId(data.session_id);
        setJobTitle(data.job_profile?.job_title || "Interview");
        setQuestionActionPendingState(false);
        repeatRequestedRef.current = false;
        setStartPending(false);
        localStorage.setItem("interviewSessionId", data.session_id);
        setSessionActive(true);
        totalQuestionsRef.current = data.total_questions || 0;
        setTotalQuestions(data.total_questions || 0);
        updateProgress(data.question?.id, data.question_index || 1);
        setCaptions([]);
        clearLiveTranscription();
        setReport(null);
        reportRef.current = null;
        setReportError("");
        setState("connecting");
        navigate("/interview");
        if (data.greeting) addCaption("Interviewer", `${data.greeting} ${data.question?.text || ""}`);
        else if (data.question?.text) addCaption("Interviewer", data.question.text);
        if (data.question?.text) setCurrentQuestion(data.question.text);
        elapsedStartRef.current = Date.now();
        if (!sendEvent("start_audio")) setState("error");
        break;
      }
      case "audio_ready":
        inputRateRef.current = data.input_sample_rate || 16000;
        outputRateRef.current = data.output_sample_rate || 24000;
        startMicrophoneCapture().then(() => {
          sendEvent("audio_client_ready");
          recordingPausedRef.current = false;
          setRecordingRecovery(false);
          setRecordingError("");
        }).catch((error) => {
          sendEvent("stop_audio"); setSetupError(error.message || "Microphone access failed."); setState("paused");
        });
        break;
      case "speech_started":
        if (!assistantSpeakingRef.current && micEnabledRef.current) {
          setLiveTranscription((current) => ({ ...current, active: true, processing: false }));
          setState("speech_detected");
        }
        break;
      case "speech_ended":
        setLiveTranscription((current) => ({ ...current, active: false, processing: true }));
        setState("processing_answer");
        setAudioLevel(0);
        break;
      case "transcription_started":
        setLiveTranscription((current) => ({ ...current, processing: true }));
        setState("processing_answer");
        break;
      case "live_transcription":
        setLiveTranscription((current) => {
          const newTurn = current.turnId !== data.turn_id;
          const segments = newTurn ? [] : current.segments;
          const lastSequence = segments.length ? segments[segments.length - 1].sequence : 0;
          if (!newTurn && data.sequence <= lastSequence) return current;
          return {
            ...current,
            turnId: data.turn_id,
            segments: [...segments, { sequence: data.sequence, text: data.text }].slice(-40),
            active: micEnabledRef.current,
            processing: false,
            error: false,
          };
        });
        break;
      case "live_transcription_error":
        setLiveTranscription((current) => ({ ...current, processing: false, error: true }));
        break;
      case "transcript_received":
        if (data.text) {
          addCaption("You", data.text);
          setLiveTranscription((current) => ({
            ...current,
            segments: [],
            turnId: null,
            finalText: data.text,
            active: false,
            processing: false,
            error: false,
          }));
        }
        setState("evaluating");
        break;
      case "transcription_unclear":
        setLiveTranscription((current) => ({ ...current, active: false, processing: false }));
        addCaption("Interviewer", data.message || "I did not catch that. Please repeat your answer.", false);
        setState(micEnabledRef.current ? "listening" : "idle");
        break;
      case "interviewer_response":
        setQuestionActionPendingState(false);
        if (["continue", "skip"].includes(data.action)) clearLiveTranscription();
        if (data.text) addCaption("Interviewer", data.text);
        updateProgress(data.question_id, data.question_index);
        repeatRequestedRef.current = data.action === "repeat";
        setState(repeatRequestedRef.current ? "repeating" : "generating_response");
        break;
      case "interview_progress": updateProgress(data.question_id, data.question_index); break;
      case "audio_started":
        audioGeneratingRef.current = false;
        assistantSpeakingRef.current = true;
        outputRateRef.current = data.sample_rate || outputRateRef.current;
        interruptionSentRef.current = false;
        interruptBlocksRef.current = 0;
        audioQueueTimeRef.current = audioContextRef.current ? audioContextRef.current.currentTime + .04 : 0;
        setState(repeatRequestedRef.current ? "repeating" : "loading_voice");
        break;
      case "audio_generating":
        audioGeneratingRef.current = true;
        assistantSpeakingRef.current = false;
        setState(repeatRequestedRef.current ? "repeating" : "loading_voice");
        break;
      case "audio_completed": audioGeneratingRef.current = false; scheduleMicrophoneResume(); break;
      case "audio_interrupted":
        audioGeneratingRef.current = false;
        assistantSpeakingRef.current = false;
        audioQueueTimeRef.current = audioContextRef.current?.currentTime || 0;
        if (!questionActionPendingRef.current) {
          setState(micEnabledRef.current && recordingReady ? "listening" : "idle");
        }
        break;
      case "audio_error":
        audioGeneratingRef.current = false;
        assistantSpeakingRef.current = false;
        repeatRequestedRef.current = false;
        setQuestionActionPendingState(false);
        stopMicrophoneCapture();
        setSetupError(data.message || "Voice audio is unavailable.");
        setState("error");
        break;
      case "audio_stopped": stopMicrophoneCapture(); break;
      case "evaluation_result": setReport(data.report); reportRef.current = data.report; setReportError(""); refreshHistory(); break;
      case "evaluation_error": setReportError(data.message || "The report could not be generated yet."); refreshHistory(); break;
      case "interview_completed": finishInterview(); break;
      case "interview_error":
        setQuestionActionPendingState(false);
        repeatRequestedRef.current = false;
        settleAck(consentAckRef, new Error(data.message || "Recording consent was not accepted by the server."));
        settleAck(recordingAckRef, new Error(data.message || "The server did not accept the recording state."));
        setSetupError(data.message || "The interview could not continue.");
        setStartPending(false);
        if (sessionIdRef.current) setState("error");
        break;
      default: break;
    }
  }

  messageHandlerRef.current = renderEvent;

  function connect() {
    const socket = createInterviewSocket();
    socketRef.current = socket;
    socket.onopen = () => {
      setConnected(true);
      const savedId = localStorage.getItem("interviewSessionId");
      if (savedId && mediaStreamRef.current) sendSocketEvent(socket, "resume_session", { session_id: savedId });
    };
    socket.onmessage = (message) => {
      if (message.data instanceof ArrayBuffer) { playAudioChunk(message.data); return; }
      if (message.data instanceof Blob) { message.data.arrayBuffer().then(playAudioChunk); return; }
      try { messageHandlerRef.current(JSON.parse(message.data)); }
      catch { setState("error"); }
    };
    socket.onclose = () => {
      setConnected(false);
      setQuestionActionPendingState(false);
      repeatRequestedRef.current = false;
      if (sessionIdRef.current || localStorage.getItem("interviewSessionId")) {
        setState("error");
        window.setTimeout(() => { if (socketRef.current === socket) connect(); }, 1500);
      }
    };
    socket.onerror = () => setState("error");
    return socket;
  }

  useEffect(() => {
    socketEffectGenerationRef.current += 1;
    const currentSocket = socketRef.current;
    const socket = currentSocket && currentSocket.readyState !== WebSocket.CLOSED
      ? currentSocket
      : connect();
    api.getVoices().then((result) => {
      setVoices(Array.isArray(result.voices) ? result.voices : []);
      setDefaultVoice(result.default_voice || "af_heart");
    }).catch(() => setSetupError("Could not load supported Kokoro voices."));
    api.getHealth().then(setHealth).catch(() => setHealth({ voice_available: false, voice_missing: ["voice services"] }));
    refreshHistory();
    return () => {
      const cleanupGeneration = ++socketEffectGenerationRef.current;
      // React StrictMode replays effects in development. Defer teardown by one
      // microtask so the replay can reuse the in-flight WebSocket connection.
      queueMicrotask(() => {
        if (socketEffectGenerationRef.current !== cleanupGeneration) return;
        if (completionTimerRef.current) window.clearTimeout(completionTimerRef.current);
        stopMicrophoneCapture();
        if (socketRef.current === socket) {
          socket.onclose = null;
          socket.close();
          socketRef.current = null;
        }
      });
    };
  }, []);

  useEffect(() => {
    if (!sessionActive) return undefined;
    elapsedStartRef.current ||= Date.now();
    const timer = window.setInterval(() => setElapsedSeconds(Math.floor((Date.now() - elapsedStartRef.current) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [sessionActive]);

  useEffect(() => {
    if (!recordingStartedRef.current || monitoring.recording) return;
    if (!sessionActive) {
      recordingStartedRef.current = false;
      setRecordingReady(false);
      setRecordingRecovery(true);
      setRecordingError(RECORDING_INTERRUPTED_MESSAGE);
      monitoring.stopCamera(false);
      stopMicrophoneCapture();
      return;
    }
    if (recordingPausedRef.current || endingInterviewRef.current) return;
    recordingPausedRef.current = true;
    setRecordingReady(false);
    setRecordingRecovery(true);
    setRecordingError(RECORDING_INTERRUPTED_MESSAGE);
    setState("paused");
    sendEvent("recording_status", { active: false });
    stopOutputAudio();
    stopMicrophoneCapture();
  }, [monitoring.recording, sessionActive]);

  async function refreshHistory() {
    try { setHistory((await api.getInterviews()).interviews || []); }
    catch { setHistory([]); }
    finally { setHistoryLoading(false); }
  }

  async function updateRecordingConsent(accepted) {
    if (!accepted) {
      permissionAttemptRef.current += 1;
      recordingStartedRef.current = false;
      recordingPausedRef.current = Boolean(sessionIdRef.current);
      setRecordingConsentAccepted(false);
      setRecordingReady(false);
      setRecordingPending(false);
      setRecordingRecovery(Boolean(sessionIdRef.current));
      setRecordingError(sessionIdRef.current ? "Consent was withdrawn. The interview is paused; accept again to restore recording." : "Recording consent is required before starting.");
      sendEvent("recording_consent", { accepted: false });
      if (sessionIdRef.current) sendEvent("recording_status", { active: false });
      monitoring.stopRecording(true);
      monitoring.stopAll();
      stopMicrophoneCapture();
      return false;
    }

    const attempt = ++permissionAttemptRef.current;
    let acquiredStream = null;
    setRecordingPending(true);
    setRecordingError("");
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        throw new Error("This browser needs camera, microphone, and recording support to continue.");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      acquiredStream = stream;
      if (attempt !== permissionAttemptRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return false;
      }

      await waitForSocketAck(consentAckRef, "recording_consent", { accepted: true });
      if (attempt !== permissionAttemptRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return false;
      }
      setRecordingConsentAccepted(true);
      monitoring.setRecordingConsent(true);
      monitoring.setCameraConsent(true);
      mediaStreamRef.current = stream;
      if (!(await monitoring.startCamera(stream))) throw new Error("Camera permission is required for this interview.");
      if (!monitoring.startRecording()) throw new Error("Recording could not be started. Check browser recording support and try again.");
      recordingStartedRef.current = true;
      await waitForSocketAck(recordingAckRef, "recording_status", { active: true });
      if (attempt !== permissionAttemptRef.current) return false;
      setRecordingReady(true);
      recordingPausedRef.current = Boolean(sessionIdRef.current);
      if (sessionIdRef.current && !sendEvent("start_audio")) {
        throw new Error("Recording is ready, but the interview server is disconnected.");
      }
      return true;
    } catch (error) {
      if (attempt === permissionAttemptRef.current) {
        sendEvent("recording_status", { active: false });
        sendEvent("recording_consent", { accepted: false });
        recordingStartedRef.current = false;
        setRecordingConsentAccepted(false);
        setRecordingReady(false);
        setRecordingError(error.message || "Recording setup failed. Accept consent and try again.");
        if (sessionIdRef.current) {
          recordingPausedRef.current = true;
          setRecordingRecovery(true);
          setState("paused");
        }
        monitoring.stopRecording(true);
        monitoring.stopAll();
        acquiredStream?.getTracks().forEach((track) => track.stop());
        stopMicrophoneCapture();
      }
      return false;
    } finally {
      if (attempt === permissionAttemptRef.current) setRecordingPending(false);
    }
  }

  async function restoreRecording() {
    if (!recordingConsentAccepted) {
      setRecordingError("Your existing recording consent is required to restore recording.");
      return false;
    }

    const attempt = ++permissionAttemptRef.current;
    let acquiredStream = null;
    setRecordingPending(true);
    setRecordingError("");
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        throw new Error("This browser cannot restore camera, microphone, and recording access.");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      acquiredStream = stream;
      if (attempt !== permissionAttemptRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return false;
      }
      if (!stream.getAudioTracks().length || !stream.getVideoTracks().length ||
          !stream.getTracks().every((track) => track.readyState === "live" && track.enabled)) {
        throw new Error("Camera or microphone access did not become active. Please try restoring recording again.");
      }

      monitoring.setRecordingConsent(true);
      monitoring.setCameraConsent(true);
      mediaStreamRef.current = stream;
      if (!(await monitoring.startCamera(stream))) throw new Error("Camera access could not be restored.");
      if (!monitoring.startRecording()) throw new Error("The browser could not restart the recording.");
      recordingStartedRef.current = true;
      const captureCheck = await monitoring.waitForRecordingData();
      if (!captureCheck.captured || !stream.getTracks().every((track) => track.readyState === "live" && track.enabled)) {
        throw new Error(captureCheck.error || "The camera or microphone stopped before recording data was captured. Please try again.");
      }
      if (attempt !== permissionAttemptRef.current) return false;

      await waitForSocketAck(recordingAckRef, "recording_status", { active: true });
      if (attempt !== permissionAttemptRef.current) return false;
      setRecordingReady(true);
      recordingPausedRef.current = Boolean(sessionIdRef.current);
      if (sessionIdRef.current) {
        if (!sendEvent("start_audio")) throw new Error("Recording is ready, but the interview server is disconnected.");
      } else {
        setRecordingRecovery(false);
        setRecordingError("");
      }
      return true;
    } catch (error) {
      if (attempt === permissionAttemptRef.current) {
        sendEvent("recording_status", { active: false });
        recordingStartedRef.current = false;
        setRecordingReady(false);
        setRecordingRecovery(true);
        setRecordingError(error.message || "Recording could not be restored. The interview remains paused.");
        setState("paused");
        monitoring.stopRecording(true);
        monitoring.stopCamera(false);
        if (mediaStreamRef.current === acquiredStream) mediaStreamRef.current = null;
        acquiredStream?.getTracks().forEach((track) => track.stop());
        stopMicrophoneCapture();
      }
      return false;
    } finally {
      if (attempt === permissionAttemptRef.current) setRecordingPending(false);
    }
  }

  async function startInterview({ candidateName, resumeText, jobDescription, voiceId }) {
    if (!recordingConsentAccepted || !recordingReady || !recordingStartedRef.current) {
      setSetupError("Accept recording consent and enable camera, microphone, and recording before starting.");
      return;
    }
    setSetupError("");
    setStartPending(true);
    try {
      if (!resumeText?.trim() || !jobDescription?.trim()) throw new Error("Provide both your resume and the job description.");
      const audioContext = ensureAudioContext();
      await audioContext.resume();
      if (!hasLiveMicrophone(mediaStreamRef.current)) {
        throw new Error("Microphone permission was lost. Restore recording consent before starting.");
      }
      const sent = sendEvent("start_interview", {
        candidate_name: candidateName?.trim() || null,
        resume_text: resumeText.trim(), job_description: jobDescription.trim(),
        voice_id: voiceId || defaultVoice,
        recording_consent: true,
      });
      if (!sent) throw new Error("The server is not connected. Try again shortly.");
      setState("connecting");
    } catch (error) {
      setSetupError(error.message || "Microphone setup failed.");
      setStartPending(false);
    }
  }

  async function resumeInterview(id) {
    if (!recordingConsentAccepted || !recordingReady || !recordingStartedRef.current) {
      setRecordingError("Accept recording consent and restore camera, microphone, and recording before resuming.");
      return;
    }
    setSetupError("");
    try {
      await ensureAudioContext().resume();
      if (!hasLiveMicrophone(mediaStreamRef.current)) {
        throw new Error("Microphone permission was lost. Accept consent and restore recording first.");
      }
      localStorage.setItem("interviewSessionId", id);
      if (!sendEvent("resume_session", { session_id: id })) throw new Error("The server is not connected. Try again shortly.");
    } catch (error) { setSetupError(error.message || "Microphone permission is needed to resume by voice."); }
  }

  function repeatQuestion() {
    if (questionActionPendingRef.current || recordingRecovery || !recordingReady) return;
    setQuestionActionPendingState(true);
    repeatRequestedRef.current = true;
    if (assistantSpeakingRef.current) { stopOutputAudio(); sendEvent("interrupt"); }
    if (sendEvent("repeat_question")) setState("repeating");
    else {
      setQuestionActionPendingState(false);
      repeatRequestedRef.current = false;
    }
  }

  function nextQuestion() {
    if (questionActionPendingRef.current || recordingRecovery || !recordingReady) return;
    setQuestionActionPendingState(true);
    repeatRequestedRef.current = false;
    if (assistantSpeakingRef.current) { stopOutputAudio(); sendEvent("interrupt"); }
    if (sendEvent("candidate_action", { action: "skip" })) setState("generating_response");
    else setQuestionActionPendingState(false);
  }

  function endInterview() {
    if (!sessionIdRef.current || !window.confirm("End this interview and generate its report?")) return;
    endingInterviewRef.current = true;
    monitoring.stopAll();
    stopMicrophoneCapture();
    sendEvent("interrupt");
    sendEvent("finish_interview");
  }

  function toggleMicrophone() {
    micEnabledRef.current = !micEnabledRef.current;
    setMicEnabled(micEnabledRef.current);
    if (!micEnabledRef.current) {
      setAudioLevel(0);
      setLiveTranscription((current) => ({ ...current, active: false, processing: false }));
      if (["listening", "speech_detected"].includes(interviewStateRef.current)) setState("idle");
    } else if (audioEnabledRef.current && recordingReady &&
        ["idle", "listening"].includes(interviewStateRef.current) &&
        !assistantSpeakingRef.current) {
      setState("listening");
    }
  }

  function toggleSpeaker() {
    speakerEnabledRef.current = !speakerEnabledRef.current;
    setSpeakerEnabled(speakerEnabledRef.current);
    const audioContext = audioContextRef.current;
    if (outputGainRef.current && audioContext) outputGainRef.current.gain.setTargetAtTime(speakerEnabledRef.current ? 1 : 0, audioContext.currentTime, .025);
  }

  async function openReport(id) {
    setReportError("");
    try {
      const session = await api.getInterview(id);
      let nextReport = session.evaluation_report;
      if (!nextReport && session.status === "completed") nextReport = await api.getReport(id);
      setReport(nextReport || null);
      reportRef.current = nextReport || null;
      setEvaluationRetryId(id);
      navigate("/report");
    } catch (error) {
      setReportError(error.message || "Could not load this interview report.");
      setEvaluationRetryId(id);
      navigate("/report");
    }
  }

  async function retryEvaluation(id = evaluationRetryId) {
    if (!id) return;
    setEvaluationRetryId(id);
    setReportError("");
    try {
      const nextReport = await api.retryReport(id);
      setReport(nextReport);
      reportRef.current = nextReport;
      refreshHistory();
    } catch (error) { setReportError(error.message || "Report retry failed."); }
  }

  function newInterview() {
    setReport(null); reportRef.current = null; setReportError(""); setSetupError("");
    setCaptions([]); clearLiveTranscription(); setSessionId(null); sessionIdRef.current = null; setSessionActive(false); setJobTitle("Interview");
    setStartPending(false); setInterviewState("idle"); setElapsedSeconds(0); setQuestionIndex(0);
    setQuestionActionPendingState(false); repeatRequestedRef.current = false;
    micEnabledRef.current = true; setMicEnabled(true);
    setCurrentQuestion(null); currentQuestionRef.current = null; setEvaluationRetryId(null);
    endingInterviewRef.current = false;
    recordingStartedRef.current = false;
    recordingPausedRef.current = false;
    setRecordingConsentAccepted(false);
    setRecordingReady(false);
    setRecordingRecovery(false);
    setRecordingError("");
    navigate("/");
    refreshHistory();
  }

  const value = {
    connected, sessionId, sessionActive, jobTitle, interviewState, activityState,
    statusLabel: activityLabel, activityLabel, questionActionPending,
    audioLevel, micEnabled, speakerEnabled, elapsedSeconds, questionIndex, totalQuestions,
    currentQuestion, captions, liveTranscription, report, reportError, setupError, setSetupError, startPending,
    health, voices, defaultVoice, history, historyLoading, evaluationRetryId,
    recordingConsentAccepted, recordingReady, recordingPending, recordingRecovery, recordingError,
    startInterview, resumeInterview, restoreRecording, repeatQuestion, nextQuestion, endInterview,
    toggleMicrophone, toggleSpeaker, openReport, retryEvaluation, newInterview, refreshHistory,
    monitoring, setStartPending, updateRecordingConsent,
  };
  return <InterviewContext.Provider value={value}>{children}</InterviewContext.Provider>;
}

export function useInterview() {
  const value = useContext(InterviewContext);
  if (!value) throw new Error("useInterview must be rendered inside InterviewProvider.");
  return value;
}
