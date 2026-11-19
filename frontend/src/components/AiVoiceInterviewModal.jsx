
import React, { useState } from 'react';
import {
  Mic, MicOff, Video, VideoOff, PhoneOff,
  Volume2, Sparkles, MessageSquare
} from 'lucide-react';

export default function AiVoiceInterviewModal({
  isOpen,
  onClose,
  candidateName = "Candidate"
}) {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);

  const [transcript] = useState([
    {
      speaker: 'AI Interviewer',
      text: "Hello! Welcome to your AI Mock Interview. Let's start with your technical background. Can you describe a complex full-stack project you built?"
    },
    {
      speaker: candidateName,
      text: "Sure! I recently built an autonomous placement portal using React, Node.js, and PostgreSQL..."
    },
    {
      speaker: 'AI Interviewer',
      text: "That sounds impressive. How did you handle secure authentication and role-based permissions?"
    }
  ]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#020617]/90 backdrop-blur-xl">

      <div className="w-full max-w-5xl h-[650px] max-h-[90vh] rounded-3xl overflow-hidden border border-indigo-400/30 shadow-2xl shadow-indigo-950/60 flex flex-col relative"
        style={{
          background: 'linear-gradient(135deg, #080d25 0%, #111746 45%, #10102e 100%)'
        }}>

        {/* Header */}
        <div className="px-6 py-4 flex items-center justify-between border-b border-white/10 bg-white/[0.04] relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-rose-500 animate-pulse shadow-lg shadow-rose-500/70" />
            <div>
              <h2 className="text-white font-bold text-sm">
                AI Voice Mock Interview
              </h2>
              <p className="text-indigo-300 text-[11px]">
                Live Interview Session
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 px-4 py-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 text-cyan-300 text-xs font-semibold">
            <Sparkles size={14} />
            AI Interviewer Active
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 overflow-hidden relative">

          {/* Decorative Background Lights */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute w-96 h-96 bg-blue-600/20 rounded-full blur-[120px] -top-32 -left-20" />
            <div className="absolute w-96 h-96 bg-purple-600/20 rounded-full blur-[130px] bottom-0 right-1/4" />
            <div className="absolute w-72 h-72 bg-cyan-500/10 rounded-full blur-[100px] top-1/3 right-0" />
          </div>

          {/* AI Interview Area */}
          <div
            className="lg:col-span-2 relative flex flex-col items-center justify-center p-8 border-r border-white/10 overflow-hidden"
            style={{
              background: 'radial-gradient(ellipse at 50% 40%, rgba(79,70,229,0.22), transparent 55%)'
            }}
          >

            {/* Background Decorative Circles */}
            <div className="absolute w-[420px] h-[420px] rounded-full border border-indigo-400/10" />
            <div className="absolute w-[330px] h-[330px] rounded-full border border-cyan-400/10" />
            <div className="absolute w-[240px] h-[240px] rounded-full border border-purple-400/10" />

            {/* AI Voice Orb */}
            <div className="relative flex items-center justify-center z-10">

              <div className="absolute w-64 h-64 rounded-full bg-indigo-500/20 blur-3xl animate-pulse" />

              <div
                className="absolute w-44 h-44 rounded-full border border-cyan-300/30 animate-ping"
                style={{ animationDuration: '3s' }}
              />

              <div
                className="w-36 h-36 rounded-full flex items-center justify-center relative"
                style={{
                  background: 'linear-gradient(145deg, #22d3ee, #4f46e5 55%, #9333ea)',
                  boxShadow: '0 0 35px rgba(59,130,246,0.55), 0 0 90px rgba(124,58,237,0.3)',
                  border: '3px solid rgba(255,255,255,0.25)'
                }}
              >
                <Volume2
                  className="w-16 h-16 text-white"
                  strokeWidth={1.8}
                />
              </div>
            </div>

            {/* Interview Status */}
            <div className="text-center mt-12 relative z-10 space-y-3">
              <div className="flex items-center justify-center gap-2">
                <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
                <h3 className="text-white font-bold text-2xl">
                  Your AI Interviewer is listening
                </h3>
              </div>

              <p className="text-indigo-200/80 text-sm">
                Speak naturally. Your interview session is in progress.
              </p>

              <div className="flex items-center justify-center gap-2 pt-2">
                <span className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-cyan-300 text-xs">
                  ✦ AI Powered Interview
                </span>
                <span className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-purple-300 text-xs">
                  Real-time Session
                </span>
              </div>
            </div>

            {/* Controls */}
            <div className="relative z-10 flex items-center gap-4 mt-12 px-7 py-4 rounded-2xl border border-white/15 bg-white/[0.08] backdrop-blur-xl shadow-2xl">

              <button
                onClick={() => setIsMuted(!isMuted)}
                title={isMuted ? "Unmute microphone" : "Mute microphone"}
                className={`p-4 rounded-xl transition-all ${
                  isMuted
                    ? 'bg-rose-500 text-white'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                {isMuted
                  ? <MicOff size={21} />
                  : <Mic size={21} />
                }
              </button>

              <button
                onClick={() => setIsVideoOff(!isVideoOff)}
                title={isVideoOff ? "Turn on camera" : "Turn off camera"}
                className={`p-4 rounded-xl transition-all ${
                  isVideoOff
                    ? 'bg-rose-500 text-white'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                {isVideoOff
                  ? <VideoOff size={21} />
                  : <Video size={21} />
                }
              </button>

              <button
                onClick={onClose}
                className="flex items-center gap-2 px-6 py-4 rounded-xl text-white font-bold text-sm transition-all hover:scale-105 shadow-lg"
                style={{
                  background: 'linear-gradient(90deg, #e11d48, #be123c)',
                  boxShadow: '0 5px 25px rgba(225,29,72,0.3)'
                }}
              >
                <PhoneOff size={17} />
                End Interview
              </button>
            </div>

            <p className="absolute bottom-4 text-slate-500 text-[10px]">
              FINXL AI INTERVIEW EXPERIENCE
            </p>
          </div>

          {/* Transcript Sidebar */}
          <div className="relative z-10 flex flex-col bg-[#090e25]/80 backdrop-blur-xl p-5 overflow-hidden">

            <div className="flex items-center gap-2 pb-4 border-b border-white/10">
              <MessageSquare size={18} className="text-cyan-400" />
              <h3 className="text-white font-bold text-sm">
                Live Transcript
              </h3>
              <span className="ml-auto text-[10px] text-cyan-300 bg-cyan-400/10 px-2 py-1 rounded-full">
                LIVE
              </span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-5 py-5 pr-1">
              {transcript.map((item, index) => (
                <div
                  key={index}
                  className={`flex flex-col ${
                    item.speaker === candidateName
                      ? 'items-end'
                      : 'items-start'
                  }`}
                >
                  <span className="text-[10px] text-indigo-300 font-bold mb-2">
                    {item.speaker}
                  </span>

                  <div
                    className={`max-w-[95%] p-3 rounded-2xl text-xs leading-relaxed ${
                      item.speaker === candidateName
                        ? 'bg-indigo-600 text-white rounded-tr-sm'
                        : 'bg-white/[0.08] border border-white/10 text-slate-200 rounded-tl-sm'
                    }`}
                  >
                    {item.text}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-auto p-3 rounded-xl bg-indigo-500/10 border border-indigo-400/20">
              <div className="flex items-center gap-2 text-cyan-300 text-xs font-semibold">
                <Sparkles size={14} />
                AI Interview Assistant
              </div>
              <p className="text-slate-400 text-[10px] mt-1 leading-relaxed">
                Your interview conversation will appear here during the session.
              </p>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
