"use strict";

const byId = (id) => document.getElementById(id);
const setupScreen = byId("setupScreen");
const interviewScreen = byId("interviewScreen");
const completionScreen = byId("completionScreen");
const startButton = byId("startButton");
const repeatButton = byId("repeatButton");
const connectionDot = byId("connectionDot");
const connectionStatus = byId("connectionStatus");
const voiceStatus = byId("voiceStatus");
const conversation = byId("conversation");
const progressText = byId("questionProgress");
const progressBar = byId("progressBar");
const evaluationReport = byId("evaluationReport");
const ttsVoiceSelect = byId("ttsVoice");
const previewVoiceButton = byId("previewVoice");

let socket;
let sessionId = null;
let audioContext = null;
let mediaStream = null;
let microphoneSource = null;
let microphoneProcessor = null;
let microphoneGain = null;
let audioEnabled = false;
let assistantSpeaking = false;
let audioGenerating = false;
let interruptBlocks = 0;
let interruptionSent = false;
let audioQueueTime = 0;
let outputSampleRate = 24000;
let inputSampleRate = 16000;
let currentQuestion = null;
let totalQuestions = 0;
let startedAt = 0;
let elapsedTimer = null;
let activeSources = new Set();
let completionTimer = null;
let voiceCatalogReady = false;
let voicePreviewSource = null;
let voicePreviewRequest = 0;
let kokoroVoices = [];
let micEnabled = true;
let speakerEnabled = true;
let outputAnalyser = null;
let outputGain = null;
let cameraStream = null;
let screenStream = null;
let snapshotTimer = null;
let snapshots = [];
let monitorEvents = [];
let lastMonitorEvent = new Map();
let mediaRecorder = null;
let recordingChunks = [];
let localRecording = null;
let discardRecordingOnStop = false;
let monitoringCleanup = false;
let lastEventSnapshotAt = 0;

const STATES = {
    idle: "Waiting to start",
    connecting: "Connecting",
    loading_voice: "Preparing local interviewer voice",
    interviewer_speaking: "Interviewer speaking",
    listening: "Listening to you",
    processing_answer: "Processing your answer",
    generating_response: "Preparing interviewer response",
    interrupted: "Listening to your interruption",
    completed: "Interview completed",
    error: "Voice session needs attention"
};

function setState(state) {
    document.body.dataset.interviewState = state;
    const label = STATES[state] || state;
    voiceStatus.textContent = label;
    byId("interviewStatus").textContent = label;
    byId("voiceVisualizer").dataset.state = state;
}

function connectWebSocket() {
    const scheme = location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${scheme}//${location.host}/ws/interview`);
    socket.binaryType = "arraybuffer";
    socket.onopen = () => {
        connectionStatus.textContent = "Connected";
        connectionDot.classList.add("connected");
        const saved = localStorage.getItem("interviewSessionId");
        if (saved && mediaStream) sendEvent("resume_session", {session_id: saved});
    };
    socket.onmessage = (message) => {
        if (message.data instanceof ArrayBuffer) { playAudioChunk(message.data); return; }
        if (message.data instanceof Blob) { message.data.arrayBuffer().then(playAudioChunk); return; }
        try { handleServerEvent(JSON.parse(message.data)); }
        catch { showError("The server sent an unreadable message. Reconnect and try again."); }
    };
    socket.onclose = () => {
        connectionStatus.textContent = "Disconnected";
        connectionDot.classList.remove("connected");
        if (sessionId || localStorage.getItem("interviewSessionId")) {
            setState("error");
            window.setTimeout(connectWebSocket, 1500);
        }
    };
    socket.onerror = () => showError("Could not connect to the interview server.");
}

function sendEvent(event, data = {}) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify({event, ...data}));
    return true;
}

function handleServerEvent(data) {
    switch (data.event) {
        case "connection_ready": break;
        case "planning_started":
            startButton.disabled = true;
            startButton.textContent = "Preparing your interview...";
            byId("setupError").textContent = "";
            break;
        case "interview_started":
            sessionId = data.session_id;
            monitoringCleanup = false;
            localStorage.setItem("interviewSessionId", sessionId);
            totalQuestions = data.total_questions || 0;
            updateProgress(data.question?.id, data.question_index || 1);
            setupScreen.classList.add("hidden");
            completionScreen.classList.add("hidden");
            interviewScreen.classList.remove("hidden");
            byId("monitorPanel").classList.remove("hidden");
            if (data.greeting) setCaption("Interviewer", `${data.greeting} ${data.question?.text || ""}`);
            else if (data.question?.text) setCaption("Interviewer", data.question.text);
            repeatButton.disabled = false;
            if (!startedAt) {
                startedAt = Date.now();
                elapsedTimer = window.setInterval(updateElapsed, 1000);
            }
            setState("connecting");
            if (!sendEvent("start_audio")) showError("Voice connection is not ready.");
            break;
        case "audio_ready":
            inputSampleRate = data.input_sample_rate || 16000;
            outputSampleRate = data.output_sample_rate || 24000;
            startMicrophoneCapture().then(() => sendEvent("audio_client_ready"))
                .catch((error) => {
                    sendEvent("stop_audio");
                    showError(error.message || "Microphone access failed.");
                });
            break;
        case "speech_started":
            if (!assistantSpeaking) {
                setState("listening");
                byId("voiceVisualizer").classList.add("active");
            }
            break;
        case "speech_ended":
            setState("processing_answer");
            byId("voiceVisualizer").classList.remove("active");
            break;
        case "transcription_started": setState("processing_answer"); break;
        case "transcript_received":
            if (data.text) setCaption("You", data.text);
            setState("generating_response");
            break;
        case "transcription_unclear":
            setCaption("Interviewer", data.message || "I did not catch that. Please repeat your answer.");
            setState("listening");
            break;
        case "interviewer_response":
            if (data.text) setCaption("Interviewer", data.text);
            currentQuestion = data.question_id ?? currentQuestion;
            updateProgress(currentQuestion, data.question_index);
            setState("generating_response");
            break;
        case "interview_progress":
            updateProgress(data.question_id, data.question_index);
            break;
        case "audio_started":
            audioGenerating = false;
            assistantSpeaking = true;
            outputSampleRate = data.sample_rate || outputSampleRate;
            interruptionSent = false;
            interruptBlocks = 0;
            audioQueueTime = audioContext ? audioContext.currentTime + 0.04 : 0;
            setState("interviewer_speaking");
            byId("voiceVisualizer").classList.add("active");
            break;
        case "audio_generating":
            audioGenerating = true;
            assistantSpeaking = false;
            setState("loading_voice");
            break;
        case "audio_completed":
            audioGenerating = false;
            scheduleMicrophoneResume();
            break;
        case "audio_interrupted":
            audioGenerating = false;
            assistantSpeaking = false;
            audioQueueTime = audioContext?.currentTime || 0;
            setState("interrupted");
            break;
        case "audio_error":
            audioGenerating = false;
            assistantSpeaking = false;
            stopMicrophoneCapture();
            showError(data.message || "Voice audio is unavailable. Check the configured provider credentials.");
            break;
        case "audio_stopped": stopMicrophoneCapture(); break;
        case "evaluation_result": renderEvaluation(data.report); break;
        case "evaluation_error":
            byId("evaluationError").textContent = `${data.message} You can retry from interview history.`;
            loadHistory();
            break;
        case "interview_completed": finishInterview(); break;
        case "interview_error":
            byId("setupError").textContent = data.message || "The interview could not continue.";
            startButton.disabled = false;
            startButton.textContent = "Start voice interview";
            if (sessionId) showError(data.message || "Interview error.");
            break;
        default: break;
    }
}

async function extractFile(file) {
    const body = new FormData();
    body.append("file", file);
    const response = await fetch("/api/extract", {method: "POST", body});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Document extraction failed.");
    return result.text;
}

for (const [inputId, textId] of [["resumeFile", "resumeText"], ["jobFile", "jobDescription"]]) {
    byId(inputId).addEventListener("change", async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        try { byId(textId).value = await extractFile(file); }
        catch (error) { byId("setupError").textContent = error.message; }
    });
}

async function loadVoiceRequirements() {
    try {
        const [response, voicesResponse] = await Promise.all([
            fetch("/health"),
            fetch("/api/tts/voices")
        ]);
        if (!voicesResponse.ok) throw new Error("Could not load supported Kokoro voices.");
        const voiceData = await voicesResponse.json();
        kokoroVoices = Array.isArray(voiceData.voices) ? voiceData.voices : [];
        ttsVoiceSelect.replaceChildren();
        for (const voice of kokoroVoices) {
            const option = document.createElement("option");
            option.value = voice.id;
            option.textContent = `${voice.name} (${voice.id}) · ${voice.accent}`;
            ttsVoiceSelect.append(option);
        }
        if (!kokoroVoices.length) throw new Error("No supported Kokoro English voices were found.");
        ttsVoiceSelect.value = voiceData.default_voice || "af_heart";
        if (!ttsVoiceSelect.value) ttsVoiceSelect.selectedIndex = 0;
        voiceCatalogReady = true;
        previewVoiceButton.disabled = false;
        updateSelectedVoiceDetails();

        if (!response.ok) throw new Error("Could not check voice service status.");
        const status = await response.json();
        if (status.voice_available) {
            const kokoroStatus = status.tts_status === "ready"
                ? "Kokoro local voice is loaded."
                : "Kokoro loads locally on first speech; first use may take longer.";
            byId("voiceRequirements").textContent = `Voice services are ready. ${kokoroStatus} Starting an interview will request microphone access.`;
            startButton.disabled = !voiceCatalogReady;
        } else {
            const missing = (status.voice_missing || []).join(" and ");
            byId("voiceRequirements").textContent = `Voice interview is unavailable until ${missing} is configured. Text-only interviews are disabled.`;
            startButton.disabled = true;
        }
    } catch (error) {
        voiceCatalogReady = false;
        previewVoiceButton.disabled = true;
        startButton.disabled = true;
        byId("voiceRequirements").textContent = error.message || "Could not verify voice service configuration.";
        byId("ttsVoiceDetails").textContent = "Supported voices could not be loaded.";
    }
}

function updateSelectedVoiceDetails() {
    const voice = kokoroVoices.find((item) => item.id === ttsVoiceSelect.value);
    byId("ttsVoiceDetails").textContent = voice
        ? `${voice.name} · ${voice.id} · Verified accent: ${voice.accent}`
        : "Choose a supported Kokoro voice.";
}

function stopVoicePreview() {
    voicePreviewRequest += 1;
    if (voicePreviewSource) {
        try { voicePreviewSource.stop(); } catch {}
        voicePreviewSource.disconnect();
        voicePreviewSource = null;
    }
}

ttsVoiceSelect.addEventListener("change", () => {
    stopVoicePreview();
    updateSelectedVoiceDetails();
    byId("setupError").textContent = "";
});

previewVoiceButton.addEventListener("click", async () => {
    stopVoicePreview();
    const requestId = voicePreviewRequest;
    const voiceId = ttsVoiceSelect.value;
    previewVoiceButton.disabled = true;
    try {
        const AudioCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtor) throw new Error("This browser does not support audio playback.");
        audioContext = audioContext || new AudioCtor();
        await audioContext.resume();
        const response = await fetch("/api/tts/preview", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({voice_id: voiceId})
        });
        if (!response.ok) throw new Error("Could not generate this voice preview.");
        const audioBuffer = await audioContext.decodeAudioData(await response.arrayBuffer());
        if (requestId !== voicePreviewRequest || voiceId !== ttsVoiceSelect.value) return;
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.onended = () => {
            if (voicePreviewSource === source) voicePreviewSource = null;
        };
        voicePreviewSource = source;
        source.start();
    } catch (error) {
        if (requestId === voicePreviewRequest) {
            byId("setupError").textContent = error.message || "Voice preview failed.";
        }
    } finally {
        previewVoiceButton.disabled = !voiceCatalogReady;
    }
});

interviewFormSubmit();
function interviewFormSubmit() {
    byId("interviewForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        byId("setupError").textContent = "";
        if (startButton.disabled) return;
        const candidateName = byId("candidateName").value.trim();
        let resumeText = byId("resumeText").value.trim();
        let jobDescription = byId("jobDescription").value.trim();
        try {
            // Unlock browser audio and request permission inside the Start click gesture.
            const AudioCtor = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtor) throw new Error("This browser does not support audio capture.");
            audioContext = audioContext || new AudioCtor();
            await audioContext.resume();
            mediaStream = mediaStream || await navigator.mediaDevices.getUserMedia({
                audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true}
            });
            const resumeFile = byId("resumeFile").files[0];
            const jobFile = byId("jobFile").files[0];
            if (resumeFile && !resumeText) resumeText = await extractFile(resumeFile);
            if (jobFile && !jobDescription) jobDescription = await extractFile(jobFile);
            if (!resumeText || !jobDescription) throw new Error("Provide both your resume and the job description.");
            if (!socket || socket.readyState !== WebSocket.OPEN) throw new Error("The server is not connected. Try again shortly.");
            startButton.disabled = true;
            startButton.textContent = "Preparing voice interview...";
            setState("connecting");
            stopVoicePreview();
            if (!sendEvent("start_interview", {candidate_name: candidateName || null, resume_text: resumeText, job_description: jobDescription, voice_id: ttsVoiceSelect.value})) {
                throw new Error("Could not start the voice session.");
            }
        } catch (error) {
            stopMicrophoneCapture();
            byId("setupError").textContent = error.message || "Microphone setup failed.";
            startButton.disabled = false;
            startButton.textContent = "Start voice interview";
        }
    });
}

function startMicrophoneCapture() {
    if (!mediaStream) return Promise.reject(new Error("Microphone permission is required."));
    if (!audioContext) return Promise.reject(new Error("Audio playback could not be initialized."));
    return audioContext.resume().then(() => {
        if (audioEnabled) return;
        microphoneSource = audioContext.createMediaStreamSource(mediaStream);
        // A smaller callback buffer reduces capture-to-WebSocket delay while
        // keeping the existing ScriptProcessor audio path.
        microphoneProcessor = audioContext.createScriptProcessor(2048, 1, 1);
        microphoneGain = audioContext.createGain();
        microphoneGain.gain.value = 0;
        microphoneProcessor.onaudioprocess = (event) => {
            if (!socket || socket.readyState !== WebSocket.OPEN) return;
            const input = event.inputBuffer.getChannelData(0);
            const rms = Math.sqrt(input.reduce((sum, value) => sum + value * value, 0) / input.length);
            byId("voiceVisualizer").style.setProperty("--audio-level", Math.min(1, rms * 12).toFixed(2));
            if (!micEnabled || (audioGenerating && !assistantSpeaking)) return;
            if (assistantSpeaking) {
                // Require clear, sustained microphone speech. Short echo spikes
                // from the laptop speakers should not cut off the question.
                interruptBlocks = rms > 0.04 ? interruptBlocks + 1 : 0;
                if (interruptBlocks >= 6 && !interruptionSent) {
                    interruptionSent = true;
                    assistantSpeaking = false;
                    stopOutputAudio();
                    sendEvent("interrupt", {reason: "microphone activity"});
                    setState("interrupted");
                } else if (assistantSpeaking) return;
            }
            const pcm = convertFloatToPCM16(resampleAudio(input, audioContext.sampleRate, inputSampleRate));
            if (pcm.byteLength) socket.send(pcm);
        };
        microphoneSource.connect(microphoneProcessor);
        microphoneProcessor.connect(microphoneGain);
        microphoneGain.connect(audioContext.destination);
        mediaStream.getAudioTracks().forEach((track) => track.addEventListener("ended", () => {
            if (audioEnabled) addMonitorEvent("microphone_track_ended", "Microphone track ended (permission or device)");
        }, {once: true}));
        audioEnabled = true;
        setState("listening");
    });
}

function stopMicrophoneCapture() {
    audioEnabled = false;
    if (microphoneProcessor) { microphoneProcessor.disconnect(); microphoneProcessor.onaudioprocess = null; microphoneProcessor = null; }
    if (microphoneSource) { microphoneSource.disconnect(); microphoneSource = null; }
    if (microphoneGain) { microphoneGain.disconnect(); microphoneGain = null; }
    if (mediaStream) { mediaStream.getTracks().forEach((track) => track.stop()); mediaStream = null; }
    stopOutputAudio();
    if (audioContext) { audioContext.close().catch(() => {}); audioContext = null; }
    outputAnalyser = null;
    outputGain = null;
}

function resampleAudio(input, inRate, outRate) {
    if (inRate === outRate) return new Float32Array(input);
    const ratio = inRate / outRate;
    const output = new Float32Array(Math.floor(input.length / ratio));
    for (let i = 0; i < output.length; i++) {
        const position = i * ratio;
        const left = Math.floor(position);
        const right = Math.min(left + 1, input.length - 1);
        const fraction = position - left;
        output[i] = input[left] * (1 - fraction) + input[right] * fraction;
    }
    return output;
}

function convertFloatToPCM16(samples) {
    const buffer = new ArrayBuffer(samples.length * 2);
    const view = new DataView(buffer);
    for (let i = 0; i < samples.length; i++) {
        const value = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(i * 2, value < 0 ? value * 32768 : value * 32767, true);
    }
    return buffer;
}

function playAudioChunk(arrayBuffer) {
    if (!audioContext || arrayBuffer.byteLength < 2 || !assistantSpeaking) return;
    const count = Math.floor(arrayBuffer.byteLength / 2);
    const sourceData = new DataView(arrayBuffer);
    const buffer = audioContext.createBuffer(1, count, outputSampleRate);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < count; i++) channel[i] = sourceData.getInt16(i * 2, true) / 32768;
    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(getOutputAnalyser());
    activeSources.add(source);
    source.onended = () => activeSources.delete(source);
    const startAt = Math.max(audioContext.currentTime + 0.015, audioQueueTime);
    source.start(startAt);
    audioQueueTime = startAt + buffer.duration;
    animateOrbFromAudio();
}

function getOutputAnalyser() {
    if (!audioContext) return null;
    if (!outputAnalyser) {
        outputAnalyser = audioContext.createAnalyser();
        outputAnalyser.fftSize = 256;
        outputGain = audioContext.createGain();
        outputGain.gain.value = speakerEnabled ? 1 : 0;
        outputAnalyser.connect(outputGain);
        outputGain.connect(audioContext.destination);
    }
    return outputAnalyser;
}

let orbAnimationFrame = 0;
function animateOrbFromAudio() {
    if (!outputAnalyser || !assistantSpeaking || orbAnimationFrame) return;
    const values = new Uint8Array(outputAnalyser.frequencyBinCount);
    const animate = () => {
        if (!assistantSpeaking || !outputAnalyser) {
            orbAnimationFrame = 0;
            byId("voiceVisualizer").style.setProperty("--audio-level", "0");
            return;
        }
        outputAnalyser.getByteTimeDomainData(values);
        let sum = 0;
        for (const value of values) { const sample = (value - 128) / 128; sum += sample * sample; }
        const level = Math.min(1, Math.sqrt(sum / values.length) * 2.2);
        byId("voiceVisualizer").style.setProperty("--audio-level", level.toFixed(2));
        orbAnimationFrame = requestAnimationFrame(animate);
    };
    orbAnimationFrame = requestAnimationFrame(animate);
}

function stopOutputAudio() {
    for (const source of activeSources) { try { source.stop(); } catch {} }
    activeSources.clear();
    audioQueueTime = audioContext?.currentTime || 0;
    assistantSpeaking = false;
    if (orbAnimationFrame) cancelAnimationFrame(orbAnimationFrame);
    orbAnimationFrame = 0;
    byId("voiceVisualizer").style.setProperty("--audio-level", "0");
}

function scheduleMicrophoneResume() {
    const remaining = audioContext ? Math.max(0, audioQueueTime - audioContext.currentTime) : 0;
    window.setTimeout(() => {
        if (assistantSpeaking && !interruptionSent) {
            assistantSpeaking = false;
            byId("voiceVisualizer").classList.remove("active");
            byId("voiceVisualizer").style.setProperty("--audio-level", "0");
            setState("listening");
        }
    }, remaining * 1000 + 100);
}

function setCaption(speaker, text) {
    const entry = document.createElement("div");
    entry.className = `message ${speaker === "You" ? "user" : "assistant"}`;
    const label = document.createElement("span");
    label.className = "message-label";
    label.textContent = speaker;
    const content = document.createElement("span");
    content.textContent = text;
    entry.append(label, content);
    conversation.append(entry);
    while (conversation.children.length > 40) conversation.firstElementChild.remove();
    conversation.scrollTop = conversation.scrollHeight;
    if (speaker === "Interviewer") byId("questionText").textContent = text;
}

function updateProgress(questionId, index) {
    if (questionId !== undefined && questionId !== null) currentQuestion = questionId;
    let number = Number(index);
    if (!Number.isFinite(number) || number < 1) {
        const match = String(currentQuestion || "").match(/\d+/);
        number = match ? Number(match[0]) : (currentQuestion ? 1 : 0);
    }
    number = Math.min(number, totalQuestions || number);
    progressText.textContent = `Question ${number} of ${totalQuestions || "..."}`;
    progressBar.style.width = totalQuestions ? `${(number / totalQuestions) * 100}%` : "0%";
}

function updateElapsed() {
    if (!startedAt) return;
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    byId("elapsedTime").textContent = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")} elapsed`;
}

function timestamp() {
    return new Date().toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"});
}

function renderMonitoringTimeline() {
    const timeline = byId("monitorTimeline");
    timeline.replaceChildren();
    const entries = [...monitorEvents, ...snapshots].sort((a, b) => a.time - b.time).slice(-60);
    byId("monitorEmpty").classList.toggle("hidden", entries.length > 0);
    for (const entry of entries) {
        const item = document.createElement("li");
        const label = document.createElement("span");
        label.textContent = entry.label;
        const time = document.createElement("time");
        time.dateTime = new Date(entry.time).toISOString();
        time.textContent = new Date(entry.time).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"});
        item.append(label, time);
        timeline.append(item);
    }
    byId("snapshotCount").textContent = String(snapshots.length);
}

function addMonitorEvent(type, label) {
    if (!sessionId || monitoringCleanup) return;
    const now = Date.now();
    if (now - (lastMonitorEvent.get(type) || 0) < 3000) return;
    lastMonitorEvent.set(type, now);
    monitorEvents.push({type, label, time: now});
    if (monitorEvents.length > 100) monitorEvents.shift();
    renderMonitoringTimeline();
    const source = screenStream && byId("screenSnapshotConsent").checked
        ? {kind: "screen", video: byId("screenCaptureVideo")}
        : cameraStream && byId("cameraSnapshotConsent").checked
            ? {kind: "camera", video: byId("cameraPreview")}
            : null;
    if (source && now - lastEventSnapshotAt >= 3000) {
        lastEventSnapshotAt = now;
        captureSnapshot(source.kind, source.video, "Event snapshot");
    }
}

function captureSnapshot(kind, video, label = "Snapshot") {
    if (!video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA || !video.videoWidth || !video.videoHeight) return;
    const maxWidth = 1280;
    const scale = Math.min(1, maxWidth / video.videoWidth);
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
    canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
    const context = canvas.getContext("2d", {alpha: false});
    if (!context) return;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
        if (!blob || !sessionId) return;
        snapshots.push({kind, label: `${label} · ${kind}`, time: Date.now(), blob});
        if (snapshots.length > 50) snapshots.shift();
        renderMonitoringTimeline();
    }, "image/jpeg", 0.82);
}

function configureSnapshotTimer() {
    if (snapshotTimer) window.clearInterval(snapshotTimer);
    snapshotTimer = null;
    const interval = Number(byId("captureInterval").value) * 1000;
    const cameraAllowed = byId("cameraSnapshotConsent").checked && cameraStream;
    const screenAllowed = byId("screenSnapshotConsent").checked && screenStream;
    if (cameraAllowed || screenAllowed) snapshotTimer = window.setInterval(() => {
        if (cameraAllowed && cameraStream) captureSnapshot("camera", byId("cameraPreview"));
        if (screenAllowed && screenStream) captureSnapshot("screen", byId("screenCaptureVideo"));
    }, interval);
}

async function toggleCamera() {
    if (cameraStream) { stopCamera(); return; }
    if (!navigator.mediaDevices?.getUserMedia) {
        addMonitorEvent("camera_unavailable", "Camera is not supported by this browser");
        return;
    }
    const button = byId("cameraToggle");
    button.disabled = true;
    try {
        const stream = await navigator.mediaDevices.getUserMedia({video: {width: {ideal: 1280}, height: {ideal: 720}}, audio: false});
        if (!sessionId) { stream.getTracks().forEach((track) => track.stop()); return; }
        cameraStream = stream;
        const video = byId("cameraPreview");
        video.srcObject = stream;
        byId("cameraTile").classList.remove("hidden");
        byId("cameraStatus").textContent = "On";
        byId("cameraToggle").setAttribute("aria-pressed", "true");
        byId("cameraToggle").querySelector("small").textContent = "Camera on";
        byId("recordToggle").disabled = !byId("recordingConsent").checked || !window.MediaRecorder;
        stream.getVideoTracks().forEach((track) => track.addEventListener("ended", () => {
            if (cameraStream === stream) {
                addMonitorEvent("camera_track_ended", "Camera track ended (permission or device)");
                stopCamera(false);
            }
        }, {once: true}));
        await video.play().catch(() => {});
        configureSnapshotTimer();
        addMonitorEvent("camera_started", "Camera enabled by candidate");
    } catch (error) {
        addMonitorEvent("camera_denied", error.name === "NotAllowedError" ? "Camera permission denied" : "Camera could not be started");
        byId("cameraStatus").textContent = "Permission denied";
    } finally {
        button.disabled = false;
    }
}

function stopCamera(logEvent = true) {
    const stream = cameraStream;
    cameraStream = null;
    if (stream) stream.getTracks().forEach((track) => track.stop());
    const video = byId("cameraPreview");
    video.pause();
    video.srcObject = null;
    byId("cameraTile").classList.add("hidden");
    byId("cameraStatus").textContent = "Off";
    byId("cameraToggle").setAttribute("aria-pressed", "false");
    byId("cameraToggle").querySelector("small").textContent = "Camera off";
    byId("recordToggle").disabled = true;
    if (mediaRecorder?.state === "recording") stopRecording();
    configureSnapshotTimer();
    if (logEvent && stream) addMonitorEvent("camera_stopped", "Camera disabled by candidate");
}

async function toggleScreenShare() {
    if (screenStream) { stopScreenShare(true); return; }
    if (!navigator.mediaDevices?.getDisplayMedia) {
        addMonitorEvent("screen_unavailable", "Screen sharing is not supported by this browser");
        return;
    }
    const button = byId("screenToggle");
    button.disabled = true;
    try {
        // This API must run directly from the candidate's click gesture.
        const stream = await navigator.mediaDevices.getDisplayMedia({video: true, audio: false});
        if (!sessionId) { stream.getTracks().forEach((track) => track.stop()); return; }
        screenStream = stream;
        let video = byId("screenCaptureVideo");
        if (!video) {
            video = document.createElement("video");
            video.id = "screenCaptureVideo";
            video.muted = true;
            video.playsInline = true;
            video.className = "hidden";
            document.body.append(video);
        }
        video.srcObject = stream;
        await video.play().catch(() => {});
        stream.getVideoTracks().forEach((track) => track.addEventListener("ended", () => stopScreenShare(true), {once: true}));
        byId("screenStatus").textContent = "Sharing";
        byId("screenToggle").textContent = "Stop sharing";
        byId("screenToggle").setAttribute("aria-pressed", "true");
        configureSnapshotTimer();
        addMonitorEvent("screen_share_started", "Screen sharing started by candidate");
    } catch (error) {
        if (error.name !== "NotAllowedError") addMonitorEvent("screen_share_error", "Screen sharing could not be started");
        byId("screenStatus").textContent = error.name === "NotAllowedError" ? "Not shared" : "Unavailable";
    } finally {
        button.disabled = false;
    }
}

function stopScreenShare(logEvent = true) {
    const stream = screenStream;
    screenStream = null;
    if (stream) stream.getTracks().forEach((track) => track.stop());
    const video = byId("screenCaptureVideo");
    if (video) { video.pause(); video.srcObject = null; }
    byId("screenStatus").textContent = "Not shared";
    byId("screenToggle").textContent = "Share screen";
    byId("screenToggle").setAttribute("aria-pressed", "false");
    configureSnapshotTimer();
    if (logEvent && stream) addMonitorEvent("screen_share_stopped", "Screen sharing stopped");
}

function startRecording() {
    if (!byId("recordingConsent").checked || !cameraStream || !window.MediaRecorder) return;
    try {
        const mimeType = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"]
            .find((type) => MediaRecorder.isTypeSupported(type));
        mediaRecorder = new MediaRecorder(cameraStream, mimeType ? {mimeType} : undefined);
        recordingChunks = [];
        discardRecordingOnStop = false;
        mediaRecorder.addEventListener("dataavailable", (event) => { if (event.data?.size) recordingChunks.push(event.data); });
        mediaRecorder.addEventListener("stop", () => {
            if (!discardRecordingOnStop && recordingChunks.length) {
                if (localRecording) URL.revokeObjectURL(localRecording.url);
                const blob = new Blob(recordingChunks, {type: mediaRecorder?.mimeType || "video/webm"});
                localRecording = {blob, url: URL.createObjectURL(blob)};
                byId("downloadRecording").classList.remove("hidden");
            } else recordingChunks = [];
            byId("recordingStatus").textContent = "Off";
            byId("recordToggle").textContent = "Start recording";
            byId("recordToggle").disabled = !byId("recordingConsent").checked || !cameraStream || !window.MediaRecorder;
            if (!discardRecordingOnStop) addMonitorEvent("recording_stopped", "Local video recording stopped");
        }, {once: true});
        mediaRecorder.start(1000);
        byId("recordingStatus").textContent = "Recording";
        byId("recordToggle").textContent = "Stop recording";
        addMonitorEvent("recording_started", "Local video recording started with consent");
    } catch {
        byId("recordingStatus").textContent = "Unavailable";
        addMonitorEvent("recording_error", "Local video recording could not be started");
    }
}

function stopRecording(discard = false) {
    if (!mediaRecorder || mediaRecorder.state === "inactive") return;
    discardRecordingOnStop = discard;
    byId("recordToggle").disabled = true;
    mediaRecorder.stop();
}

function clearMonitoringData() {
    snapshots = [];
    monitorEvents = [];
    lastMonitorEvent.clear();
    lastEventSnapshotAt = 0;
    recordingChunks = [];
    if (mediaRecorder?.state === "recording") stopRecording(true);
    if (localRecording) URL.revokeObjectURL(localRecording.url);
    localRecording = null;
    byId("downloadRecording").classList.add("hidden");
    renderMonitoringTimeline();
}

function stopAllMonitoring() {
    monitoringCleanup = true;
    if (snapshotTimer) window.clearInterval(snapshotTimer);
    snapshotTimer = null;
    stopRecording(true);
    stopCamera(false);
    stopScreenShare(false);
    clearMonitoringData();
    byId("cameraStatus").textContent = "Off";
    byId("screenStatus").textContent = "Not shared";
    byId("recordingStatus").textContent = "Off";
}

function finishSessionMonitoring() {
    stopAllMonitoring();
    byId("cameraSnapshotConsent").checked = false;
    byId("screenSnapshotConsent").checked = false;
    byId("recordingConsent").checked = false;
}

function endInterview() {
    if (!sessionId || !window.confirm("End this interview and generate its report?")) return;
    finishSessionMonitoring();
    stopMicrophoneCapture();
    sendEvent("interrupt");
    sendEvent("finish_interview");
}

byId("micToggle").addEventListener("click", () => {
    micEnabled = !micEnabled;
    byId("micToggle").setAttribute("aria-pressed", String(micEnabled));
    byId("micToggle").querySelector("small").textContent = micEnabled ? "Mic on" : "Mic muted";
    byId("micToggle").classList.toggle("is-active", micEnabled);
});

byId("cameraToggle").addEventListener("click", toggleCamera);
byId("screenToggle").addEventListener("click", toggleScreenShare);
byId("recordToggle").addEventListener("click", () => {
    if (mediaRecorder?.state === "recording") stopRecording();
    else startRecording();
});
byId("speakerToggle").addEventListener("click", () => {
    speakerEnabled = !speakerEnabled;
    if (outputGain) outputGain.gain.setTargetAtTime(speakerEnabled ? 1 : 0, audioContext.currentTime, 0.025);
    byId("speakerToggle").setAttribute("aria-pressed", String(speakerEnabled));
    byId("speakerToggle").querySelector("small").textContent = speakerEnabled ? "Speaker on" : "Speaker off";
});
byId("settingsToggle").addEventListener("click", () => {
    const panel = byId("monitorPanel");
    const expanded = !panel.classList.contains("settings-collapsed");
    panel.classList.toggle("settings-collapsed", expanded);
    byId("settingsToggle").setAttribute("aria-expanded", String(!expanded));
});
byId("endButtonBottom").addEventListener("click", endInterview);
byId("cameraSnapshotConsent").addEventListener("change", configureSnapshotTimer);
byId("screenSnapshotConsent").addEventListener("change", configureSnapshotTimer);
byId("captureInterval").addEventListener("change", configureSnapshotTimer);
byId("recordingConsent").addEventListener("change", (event) => {
    byId("recordToggle").disabled = !event.target.checked || !cameraStream || !window.MediaRecorder;
    if (!event.target.checked && mediaRecorder?.state === "recording") stopRecording();
});
byId("clearMonitoring").addEventListener("click", clearMonitoringData);
byId("downloadRecording").addEventListener("click", () => {
    if (!localRecording) return;
    const link = document.createElement("a");
    link.href = localRecording.url;
    link.download = `interview-recording-${Date.now()}.webm`;
    link.click();
});

document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") addMonitorEvent("tab_hidden", "Interview tab became hidden");
});
window.addEventListener("blur", () => addMonitorEvent("window_blur", "Interview window lost focus"));
document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement) addMonitorEvent("fullscreen_exited", "Fullscreen mode was exited");
});

function showError(message) {
    setState("error");
    voiceStatus.textContent = message;
}

repeatButton.addEventListener("click", () => {
    if (assistantSpeaking) {
        stopOutputAudio();
        assistantSpeaking = false;
        sendEvent("interrupt");
    }
    if (sendEvent("repeat_question")) setState("generating_response");
});

function finishInterview() {
    if (assistantSpeaking && audioContext) {
        const remaining = Math.max(0, audioQueueTime - audioContext.currentTime);
        if (completionTimer) window.clearTimeout(completionTimer);
        completionTimer = window.setTimeout(finishInterviewNow, remaining * 1000 + 120);
        return;
    }
    finishInterviewNow();
}

function finishInterviewNow() {
    completionTimer = null;
    finishSessionMonitoring();
    stopMicrophoneCapture();
    sessionId = null;
    localStorage.removeItem("interviewSessionId");
    if (elapsedTimer) window.clearInterval(elapsedTimer);
    elapsedTimer = null;
    startedAt = 0;
    interviewScreen.classList.add("hidden");
    setupScreen.classList.add("hidden");
    completionScreen.classList.remove("hidden");
    setState("completed");
}

function renderEvaluation(report) {
    if (!report) return;
    evaluationReport.replaceChildren();
    const heading = document.createElement("h2");
    heading.textContent = `Evaluation: ${report.overall_score}/10 - ${report.recommendation}`;
    evaluationReport.append(heading);
    for (const key of ["technical_depth", "communication", "problem_solving", "culture_fit"]) {
        const item = report[key];
        if (!item) continue;
        const section = document.createElement("section");
        const title = document.createElement("h3");
        title.textContent = `${key.replaceAll("_", " ")} - ${item.score}/10`;
        const evidence = document.createElement("p");
        evidence.textContent = (item.evidence || []).join("; ");
        section.append(title, evidence);
        evaluationReport.append(section);
    }
    for (const [key, label] of [["strengths", "Strengths"], ["concerns", "Areas for improvement"]]) {
        const title = document.createElement("h3"); title.textContent = label;
        const list = document.createElement("ul");
        for (const value of report[key] || []) { const li = document.createElement("li"); li.textContent = value; list.append(li); }
        evaluationReport.append(title, list);
    }
    const summary = document.createElement("p"); summary.textContent = report.summary || "";
    evaluationReport.append(summary);
    completionScreen.classList.remove("hidden");
    loadHistory();
}

async function loadHistory() {
    try {
        const response = await fetch("/api/interviews");
        const data = await response.json();
        const container = byId("historyList");
        container.replaceChildren();
        if (!data.interviews?.length) { container.textContent = "No interviews yet."; return; }
        for (const item of data.interviews) {
            const row = document.createElement("div"); row.className = "history-row";
            const label = document.createElement("span");
            label.textContent = `${item.candidate_name || "Candidate"} - ${item.job_title || "Interview"} - ${item.status}`;
            row.append(label);
            if (item.status === "completed") {
                const button = document.createElement("button"); button.type = "button";
                button.textContent = item.evaluation_report ? "View report" : "Retry report";
                button.onclick = async () => {
                    if (item.evaluation_report) renderEvaluation(item.evaluation_report);
                    else {
                        const result = await fetch(`/api/interviews/${encodeURIComponent(item.id)}/evaluate`, {method: "POST"});
                        const report = await result.json();
                        if (result.ok) renderEvaluation(report);
                        else byId("evaluationError").textContent = report.detail || "Report retry failed.";
                    }
                };
                row.append(button);
            } else if (item.status === "in_progress") {
                const button = document.createElement("button"); button.type = "button"; button.textContent = "Resume";
                button.onclick = async () => {
                    try {
                        const AudioCtor = window.AudioContext || window.webkitAudioContext;
                        audioContext = audioContext || new AudioCtor(); await audioContext.resume();
                        mediaStream = mediaStream || await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true}});
                        localStorage.setItem("interviewSessionId", item.id);
                        if (socket?.readyState === WebSocket.OPEN) sendEvent("resume_session", {session_id: item.id});
                    } catch { byId("setupError").textContent = "Microphone permission is needed to resume by voice."; }
                };
                row.append(button);
            }
            container.append(row);
        }
    } catch { byId("historyList").textContent = "Interview history is temporarily unavailable."; }
}

byId("newInterviewButton").addEventListener("click", () => location.reload());
window.addEventListener("beforeunload", () => {
    if (elapsedTimer) window.clearInterval(elapsedTimer);
    if (mediaStream) mediaStream.getTracks().forEach((track) => track.stop());
    finishSessionMonitoring();
});

connectWebSocket();
loadVoiceRequirements();
loadHistory();
