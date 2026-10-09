import React, { useState } from 'react';

export default function App() {
  const [activeStep, setActiveStep] = useState(1);
  const [activeTab, setActiveTab] = useState('finxl');
  const [selectedRole, setSelectedRole] = useState('');
  const [externalId, setExternalId] = useState('');
  const [pastedText, setPastedText] = useState('');
  const [jdFile, setJdFile] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const steps = [
    { num: '01', label: 'Job' },
    { num: '02', label: 'Resume' },
    { num: '03', label: 'Analysis' },
    { num: '04', label: 'Match' },
    { num: '05', label: 'Optimize' },
    { num: '06', label: 'Preview' },
  ];

  const finxlRoles = {
    'software-engineer': {
      title: 'Senior Software Engineer',
      company: 'FINXL Tech Corp',
      id: 'FX-SE-892',
      category: 'Engineering',
      description: 'Looking for a skilled developer with experience in React, Node.js, and cloud architecture.'
    },
    'data-scientist': {
      title: 'Lead Data Scientist',
      company: 'FINXL Analytics',
      id: 'FX-DS-412',
      category: 'Data & AI',
      description: 'Seeking an expert in Python, Machine Learning models, and large-scale data pipelines.'
    },
    'product-manager': {
      title: 'Product Manager',
      company: 'FINXL Global',
      id: 'FX-PM-105',
      category: 'Product',
      description: 'Manage SaaS product lifecycles, coordinate cross-functional teams, and drive roadmap execution.'
    }
  };

  const currentJob = finxlRoles[selectedRole] || {
    title: 'Untitled Position',
    company: 'Company not specified',
    id: 'N/A',
    category: 'General',
    description: 'Select a job or provide a job description to see its preview.'
  };

  const handleResumeUpload = (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      setResumes((prev) => [...prev, ...files].slice(0, 5));
    }
  };

  const removeResume = (index) => {
    setResumes((prev) => prev.filter((_, i) => i !== index));
  };

  const handleAnalyze = () => {
    setIsAnalyzing(true);
    setTimeout(() => {
      setIsAnalyzing(false);
      setActiveStep(3);
    }, 1200);
  };

  return (
    <div className="space-y-4 font-sans">
      
      {/* Header section */}
      <header className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-blue-50 border border-blue-100 text-blue-600 text-xs font-semibold mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"></span>
            AI Resume Optimizer
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Optimize your resume for your next opportunity.
          </h1>
          <p className="text-slate-500 text-xs mt-0.5">
            Analyze job requirements, identify skill matches, and create a tailored, ATS-friendly resume.
          </p>
        </div>
      </header>

      {/* Steps Navigation Bar */}
      <div className="bg-white border border-slate-100 rounded-2xl p-3 shadow-sm">
        <div className="flex items-center justify-between overflow-x-auto py-1 px-1 gap-2">
          {steps.map((step, idx) => {
            const stepNum = idx + 1;
            const isActive = activeStep === stepNum;
            const isPassed = activeStep > stepNum;
            return (
              <div 
                key={step.num} 
                onClick={() => setActiveStep(stepNum)}
                className="flex items-center gap-3 flex-1 min-w-[120px] cursor-pointer group"
              >
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl transition-all ${
                  isActive ? 'bg-blue-600 text-white shadow-sm font-medium scale-[1.02]' :
                  isPassed ? 'bg-blue-50 text-blue-700 font-medium hover:bg-blue-100' : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
                }`}>
                  <span className="text-xs font-bold">{step.num}</span>
                  <span className="text-xs">{step.label}</span>
                </div>
                {idx < steps.length - 1 && (
                  <div className={`h-0.5 flex-1 mx-1 rounded transition-colors ${isPassed ? 'bg-blue-600' : 'bg-slate-200'}`}></div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Grid Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* Left Card: Job Description */}
        <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
          <div className="space-y-4">
            <div className="space-y-0.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">01 &bull; Job Description</span>
              <h2 className="text-lg font-bold text-slate-900">Where is your job description?</h2>
              <p className="text-slate-500 text-xs">Select a target job from FINXL catalogue or specify your own role.</p>
            </div>

            {/* Selector Tabs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[
                { id: 'finxl', label: 'FINXL Job', sub: 'Select from catalog', icon: '💼' },
                { id: 'external', label: 'External Job', sub: 'Enter reference ID', icon: '🌐' },
                { id: 'paste', label: 'Paste JD', sub: 'Paste text directly', icon: '📋' },
                { id: 'upload', label: 'Upload JD', sub: 'Attach PDF/DOCX', icon: '📤' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex flex-col items-center text-center p-3 rounded-xl border transition-all ${
                    activeTab === tab.id
                      ? 'border-blue-600 bg-blue-50/50 text-blue-900 shadow-sm ring-1 ring-blue-600'
                      : 'border-slate-200 hover:border-slate-300 text-slate-600 bg-white'
                  }`}
                >
                  <span className="text-base mb-1">{tab.icon}</span>
                  <span className="text-xs font-bold">{tab.label}</span>
                  <span className="text-[10px] text-slate-400 mt-0.5 line-clamp-1">{tab.sub}</span>
                </button>
              ))}
            </div>

            {/* Dynamic Tab Inputs */}
            {activeTab === 'finxl' && (
              <div className="space-y-1.5 animate-fadeIn">
                <label className="block text-xs font-semibold text-slate-700">Select FINXL Role</label>
                <div className="relative">
                  <select
                    value={selectedRole}
                    onChange={(e) => setSelectedRole(e.target.value)}
                    className="w-full appearance-none bg-white border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  >
                    <option value="">Select a FINXL role</option>
                    <option value="software-engineer">Senior Software Engineer</option>
                    <option value="data-scientist">Lead Data Scientist</option>
                    <option value="product-manager">Product Manager</option>
                  </select>
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-500">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'external' && (
              <div className="space-y-1.5 animate-fadeIn">
                <label className="block text-xs font-semibold text-slate-700">External Job Reference ID / URL</label>
                <input
                  type="text"
                  placeholder="e.g. https://company.com/jobs/12345 or JOB-9988"
                  value={externalId}
                  onChange={(e) => setExternalId(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
              </div>
            )}

            {activeTab === 'paste' && (
              <div className="space-y-1.5 animate-fadeIn">
                <label className="block text-xs font-semibold text-slate-700">Paste Job Description Text</label>
                <textarea
                  rows={3}
                  placeholder="Paste full job description requirements here..."
                  value={pastedText}
                  onChange={(e) => setPastedText(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-xl p-2.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
              </div>
            )}

            {activeTab === 'upload' && (
              <div className="space-y-1.5 animate-fadeIn">
                <label className="block text-xs font-semibold text-slate-700">Upload Job Description Document</label>
                <div className="border border-dashed border-slate-300 rounded-xl p-3 text-center bg-slate-50">
                  <input
                    type="file"
                    accept=".pdf,.docx"
                    onChange={(e) => setJdFile(e.target.files[0])}
                    className="text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
                  />
                  {jdFile && <p className="text-xs text-blue-600 mt-1 font-medium">Attached: {jdFile.name}</p>}
                </div>
              </div>
            )}

            {/* Role Preview Card */}
            <div className="bg-slate-50/80 border border-slate-200/80 rounded-xl p-4 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{currentJob.title}</h3>
                  <p className="text-[11px] text-slate-500 mt-0.5">{currentJob.company} &bull; Job ID: <span className="font-medium text-slate-700">{currentJob.id}</span></p>
                </div>
                <span className="px-2.5 py-0.5 bg-slate-200/70 text-slate-600 text-[10px] font-semibold rounded-full">
                  {currentJob.category}
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                {currentJob.description}
              </p>
              <div className="pt-2 border-t border-slate-200/60 flex justify-between items-center">
                <span className="text-[11px] text-emerald-600 font-medium">Status: Ready for match</span>
                <a href="#requirements" onClick={(e) => e.preventDefault()} className="text-xs font-semibold text-blue-600 hover:text-blue-700 inline-flex items-center gap-1">
                  View role requirements
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </div>
            </div>

          </div>
        </div>

        {/* Right Card: Your Resume Upload */}
        <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
          <div className="space-y-4">
            <div className="space-y-0.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">02 &bull; YOUR RESUME</span>
              <h2 className="text-lg font-bold text-slate-900">Upload your resume</h2>
              <p className="text-slate-500 text-xs">We will review your factual experience against the target role.</p>
            </div>

            {/* Drag and Drop Zone */}
            <label className="border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-xl p-5 flex flex-col items-center justify-center text-center bg-slate-50/50 transition cursor-pointer group block">
              <input 
                type="file" 
                multiple 
                accept=".pdf,.docx" 
                onChange={handleResumeUpload}
                className="hidden" 
              />
              <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mb-2 group-hover:scale-110 transition-transform shadow-sm">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              </div>
              <h3 className="text-xs font-bold text-slate-800">Drop your resume here</h3>
              <p className="text-[11px] text-slate-400 mt-0.5">PDF or DOCX &bull; Up to 5 resumes &bull; 8 MB each</p>
              <span className="mt-3 px-3 py-1.5 bg-white border border-slate-200 hover:border-slate-300 text-slate-700 text-xs font-semibold rounded-lg shadow-xs transition inline-block">
                Browse files
              </span>
            </label>

            {/* Uploaded Files List */}
            {resumes.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-bold text-slate-700">Uploaded Resumes ({resumes.length}/5):</span>
                <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
                  {resumes.map((file, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-xl text-xs">
                      <span className="font-medium text-slate-700 truncate max-w-[220px]">{file.name}</span>
                      <button 
                        onClick={() => removeResume(idx)}
                        className="text-red-500 hover:text-red-700 font-bold ml-2"
                      >
                        &times;
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Action and Privacy Note */}
          <div className="space-y-3 pt-2">
            <button 
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-md flex items-center justify-center gap-2 transition active:scale-[0.99] disabled:opacity-50 text-xs"
            >
              {isAnalyzing ? (
                <>
                  <svg className="animate-spin w-4 h-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Analyzing & Matching...
                </>
              ) : (
                <>
                  Analyze Resume & Match
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </>
              )}
            </button>

            <div className="flex items-center gap-1.5 text-slate-400 text-[10px]">
              <svg className="w-3.5 h-3.5 shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <span>Your resume is analyzed privately. Content is never used to train external AI models.</span>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
