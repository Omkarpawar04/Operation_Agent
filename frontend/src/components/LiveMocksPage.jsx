import React, { useState } from 'react';
import { Video, Sparkles, Clock, ShieldCheck, Cpu, Mic, Volume2, ArrowRight } from 'lucide-react';
import AiVoiceInterviewModal from './AiVoiceInterviewModal.jsx';

export default function LiveMocksPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const candidateName = "Piyanshi Vegad"; // Or active student profile name

  return (
    <div className="p-6 lg:p-10 max-w-7xl mx-auto space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-8 rounded-3xl border border-indigo-500/30 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
        
        <div className="space-y-2 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-bold rounded-full">
            <Sparkles className="w-3.5 h-3.5 animate-spin" />
            <span>Autonomous AI Interview Arena</span>
          </div>
          <h1 className="text-3xl lg:text-4xl font-black text-white tracking-tight">Live AI Mock Interviews</h1>
          <p className="text-sm text-slate-300 max-w-xl">
            Experience real-time adaptive questioning, instantaneous speech-to-text processing, and deep behavioral evaluation powered by neural nodes.
          </p>
        </div>

        <div className="flex items-center gap-3 bg-slate-900/80 backdrop-blur-md px-5 py-3 rounded-2xl border border-indigo-500/30 shadow-lg relative z-10">
          <span className="w-3 h-3 bg-emerald-500 rounded-full animate-ping"></span>
          <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">AI Core: Online</span>
        </div>
      </div>

      {/* Single Immersive 3D Interactive AI Interview Card */}
      <div className="relative group">
        {/* Glowing Aura Background */}
        <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 via-indigo-600 to-purple-600 rounded-[2.5rem] blur-xl opacity-40 group-hover:opacity-75 transition duration-500"></div>

        <div className="relative bg-slate-900 border border-indigo-500/40 rounded-[2.5rem] p-8 lg:p-12 shadow-2xl overflow-hidden flex flex-col lg:flex-row items-center justify-between gap-8">
          
          {/* Left Details */}
          <div className="space-y-6 flex-1 text-left">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-500 to-indigo-600 text-white flex items-center justify-center shadow-lg shadow-cyan-500/30">
                <Cpu className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest">Neural Assessment Node</span>
                <h3 className="text-2xl font-black text-white">Full-Stack & AI/ML Viva Engine</h3>
              </div>
            </div>

            <p className="text-slate-300 text-sm leading-relaxed">
              This session evaluates code architecture decisions, database optimization routines, and real-time problem-solving proficiency under simulated pressure.
            </p>

            <div className="flex flex-wrap gap-4 pt-2">
              <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/80 rounded-xl border border-slate-700 text-xs text-slate-300 font-medium">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>Dynamic Timing</span>
              </div>
              <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/80 rounded-xl border border-slate-700 text-xs text-slate-300 font-medium">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Instant Feedback Report</span>
              </div>
            </div>
          </div>

          {/* Right 3D Visualizer & Action Trigger */}
          <div className="w-full lg:w-auto flex flex-col items-center justify-center bg-slate-950/60 p-8 rounded-3xl border border-indigo-500/20 shadow-inner gap-6 min-w-[320px]">
            <div className="relative flex items-center justify-center">
              <div className="absolute w-32 h-32 bg-cyan-500/20 rounded-full blur-xl animate-pulse"></div>
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-500 flex items-center justify-center shadow-2xl shadow-purple-500/50 transform group-hover:scale-110 group-hover:rotate-6 transition duration-300 ring-4 ring-cyan-400/30">
                <Mic className="w-8 h-8 text-white animate-bounce" />
              </div>
            </div>

            <button
              onClick={() => setIsModalOpen(true)}
              className="w-full bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:brightness-110 text-white font-black py-4 px-8 rounded-2xl text-xs uppercase tracking-wider flex items-center justify-center gap-3 transition transform active:scale-95 shadow-xl shadow-cyan-500/30 cursor-pointer group/btn"
            >
              <Video className="w-5 h-5 group-hover/btn:scale-110 transition" />
              <span>Launch AI Voice Interview</span>
              <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition" />
            </button>
          </div>

        </div>
      </div>

      {/* AI Voice Interview Modal Popup */}
      <AiVoiceInterviewModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        candidateName={candidateName}
      />
    </div>
  );
}