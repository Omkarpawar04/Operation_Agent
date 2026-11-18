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
            localStorage.setItem("interviewSessionId", sessionId);
            totalQuestions = data.total_questions || 0;
            updateProgress(data.question?.id, data.question_index || 1);
            setupScreen.classList.add("hidden");
            completionScreen.classList.add("hidden");
            interviewScreen.classList.remove("hidden");
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
        const response = await fetch("/health");
        const status = await response.json();
        if (status.voice_available) {
            const kokoroStatus = status.tts_status === "ready"
                ? "Kokoro local voice is loaded."
                : "Kokoro loads locally on first speech; first use may take longer.";
            byId("voiceRequirements").textContent = `Voice services are ready. ${kokoroStatus} Starting an interview will request microphone access.`;
            startButton.disabled = false;
        } else {
            const missing = (status.voice_missing || []).join(" and ");
            byId("voiceRequirements").textContent = `Voice interview is unavailable until ${missing} is configured. Text-only interviews are disabled.`;
            startButton.disabled = true;
        }
    } catch { byId("voiceRequirements").textContent = "Could not verify voice service configuration."; }
}

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
            if (!sendEvent("start_interview", {candidate_name: candidateName || null, resume_text: resumeText, job_description: jobDescription})) {
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
            if (audioGenerating && !assistantSpeaking) return;
            const input = event.inputBuffer.getChannelData(0);
            const rms = Math.sqrt(input.reduce((sum, value) => sum + value * value, 0) / input.length);
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
    source.connect(audioContext.destination);
    activeSources.add(source);
    source.onended = () => activeSources.delete(source);
    const startAt = Math.max(audioContext.currentTime + 0.015, audioQueueTime);
    source.start(startAt);
    audioQueueTime = startAt + buffer.duration;
}

function stopOutputAudio() {
    for (const source of activeSources) { try { source.stop(); } catch {} }
    activeSources.clear();
    audioQueueTime = audioContext?.currentTime || 0;
}

function scheduleMicrophoneResume() {
    const remaining = audioContext ? Math.max(0, audioQueueTime - audioContext.currentTime) : 0;
    window.setTimeout(() => {
        if (assistantSpeaking && !interruptionSent) {
            assistantSpeaking = false;
            byId("voiceVisualizer").classList.remove("active");
            setState("listening");
        }
    }, remaining * 1000 + 100);
}

function setCaption(speaker, text) {
    conversation.replaceChildren();
    const label = document.createElement("strong");
    label.textContent = `${speaker}: `;
    const content = document.createElement("span");
    content.textContent = text;
    conversation.append(label, content);
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

byId("endButton").addEventListener("click", () => {
    if (!sessionId || !window.confirm("End this interview and generate its report?")) return;
    stopMicrophoneCapture();
    sendEvent("interrupt");
    sendEvent("finish_interview");
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
});

connectWebSocket();
loadVoiceRequirements();
loadHistory();
