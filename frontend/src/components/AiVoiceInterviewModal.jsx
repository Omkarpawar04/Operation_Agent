import React, { useState } from 'react';
import { Mic, MicOff, Video, VideoOff, PhoneOff, Volume2, Sparkles, MessageSquare } from 'lucide-react';

export default function AiVoiceInterviewModal({ isOpen, onClose, candidateName = "Candidate" }) {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [transcript, setTranscript] = useState([
    { speaker: 'AI', text: "Hello! Welcome to your AI Mock Interview. Let's start with your technical background. Can you describe a complex full-stack project you built?" },
    { speaker: candidateName, text: "Sure! I recently built an autonomous placement portal using React, Node.js, and PostgreSQL..." },
    { speaker: 'AI', text: "That sounds impressive. How did you handle secure authentication and role-based permissions?" }
  ]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in">
      <div className="w-full max-w-4xl bg-slate-900 border border-indigo-500/30 rounded-3xl shadow-2xl overflow-hidden flex flex-col h-[650px] relative">
        
        {/* Top Header */}
        <div className="bg-slate-950/60 px-6 py-4 border-b border-indigo-500/20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
            <span className="font-bold text-white text-sm">AI Voice Mock Interview · Live Session</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs rounded-full">
            <Sparkles className="w-3.5 h-3.5 animate-spin" />
            <span>Active Voice Node</span>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 overflow-hidden">
          
          {/* Left / Center: AI Visualizer / Avatar Arena */}
          <div className="lg:col-span-2 bg-gradient-to-br from-slate-950 via-indigo-950/40 to-slate-900 p-6 flex flex-col items-center justify-center relative border-r border-indigo-500/20">
            
            {/* Pulsing 3D AI Voice Orb */}
            <div className="relative flex items-center justify-center my-auto">
              <div className="absolute w-48 h-48 rounded-full bg-cyan-500/20 blur-2xl animate-pulse"></div>
              <div className="absolute w-36 h-36 rounded-full bg-indigo-600/30 blur-xl animate-ping" style={{ animationDuration: '3s' }}></div>
              <div className="w-28 h-28 rounded-full bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center shadow-2xl shadow-cyan-500/50 ring-4 ring-cyan-400/30 relative z-10">
                <Volume2 className="w-12 h-12 text-white animate-bounce" style={{ animationDuration: '2s' }} />
              </div>
            </div>

            <div className="text-center mt-6 space-y-1">
              <h3 className="text-white font-bold text-lg">AI Interviewer is listening...</h3>
              <p className="text-xs text-slate-400">Speak clearly into your microphone to answer.</p>
            </div>

            {/* Bottom Controls Bar */}
            <div className="flex items-center gap-4 mt-6 bg-slate-900/80 backdrop-blur-md px-6 py-3 rounded-2xl border border-indigo-500/30 shadow-xl">
              <button 
                onClick={() => setIsMuted(!isMuted)}
                className={`p-3 rounded-xl transition ${isMuted ? 'bg-rose-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
              >
                {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>
              <button 
                onClick={() => setIsVideoOff(!isVideoOff)}
                className={`p-3 rounded-xl transition ${isVideoOff ? 'bg-rose-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
              >
                {isVideoOff ? <VideoOff className="w-5 h-5" /> : <Video className="w-5 h-5" />}
              </button>
              <button 
                onClick={onClose}
                className="flex items-center gap-2 px-5 py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl transition shadow-lg shadow-rose-600/30"
              >
                <PhoneOff className="w-4 h-4" />
                <span>End Session</span>
              </button>
            </div>
          </div>

          {/* Right Sidebar: Live Transcription Chat View */}
          <div className="bg-slate-950 p-4 flex flex-col justify-between overflow-hidden">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-800 text-xs font-bold text-slate-300">
              <MessageSquare className="w-4 h-4 text-cyan-400" />
              <span>Live Transcript</span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 py-4 text-xs pr-1">
              {transcript.map((item, idx) => (
                <div key={idx} className={`space-y-1 ${item.speaker === 'AI' ? 'text-left' : 'text-right'}`}>
                  <span className="text-[10px] text-cyan-400 font-semibold">{item.speaker}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}