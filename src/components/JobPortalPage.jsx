import React, { useState } from 'react';
import { 
  Search, 
  Plus, 
  MapPin, 
  Briefcase, 
  IndianRupee, 
  ExternalLink, 
  Globe, 
  Sparkles,
  CheckCircle2,
  Send,
  ChevronDown,
  Grid
} from 'lucide-react';

export default function JobPortalPage() {
  const [selectedPortal, setSelectedPortal] = useState('All');
  const [showPortalGrid, setShowPortalGrid] = useState(true);

  // External partner job portals list
  const jobPortals = [
    { id: 'all', name: 'All Portals', desc: 'Show jobs across all sources', badge: 'All Jobs', url: '#' },
    { id: 'naukri', name: 'Naukri.com', desc: "India's No.1 Job Site", color: 'from-blue-600 to-indigo-700', badge: 'Popular', url: 'https://www.naukri.com' },
    { id: 'placementindia', name: 'Placement India', desc: 'Job Placement & Hiring Portal', color: 'from-sky-500 to-blue-600', badge: 'Placement', url: 'https://www.placementindia.com' },
    { id: 'instahyre', name: 'Instahyre', desc: 'AI-Powered Top Tech Hiring', color: 'from-emerald-500 to-teal-700', badge: 'AI Match', url: 'https://www.instahyre.com' },
    { id: 'iimjobs', name: 'iimjobs', desc: 'Management & Finance Jobs', color: 'from-amber-500 to-orange-600', badge: 'Executive', url: 'https://www.iimjobs.com' },
    { id: 'wellfound', name: 'Wellfound', desc: 'Startup Jobs & Investment', color: 'from-rose-500 to-pink-600', badge: 'Startups', url: 'https://wellfound.com' },
    { id: 'jobgreen', name: 'JobGreen', desc: 'Freshers & Experienced Roles', color: 'from-green-600 to-emerald-800', badge: 'Verified', url: 'https://www.jobgreen.com' },
    { id: 'todaywalkins', name: 'TodayWalkins', desc: 'Direct Walk-in Drive Alerts', color: 'from-violet-600 to-purple-700', badge: 'Walk-ins', url: 'https://www.todaywalkins.com' },
  ];

  // Expanded list of job openings with AI auto-apply
  const [jobs, setJobs] = useState([
    {
      id: 1,
      title: 'Financial Analyst',
      company: 'Deloitte India',
      match: '92% Match',
      location: 'Mumbai, India',
      experience: '0-2 Yrs',
      package: '₹6 - 8 LPA',
      skills: ['Financial Modeling', 'Excel', 'Valuation'],
      portal: 'Naukri.com',
      applied: false
    },
    {
      id: 2,
      title: 'Risk Advisory Associate',
      company: 'PwC India',
      match: '85% Match',
      location: 'Pune, India',
      experience: '0-1 Yrs',
      package: '₹7 - 9 LPA',
      skills: ['Internal Audit', 'Compliance', 'SAP'],
      portal: 'Placement India',
      applied: false
    },
    {
      id: 3,
      title: 'Equity Research Analyst',
      company: 'HDFC Securities',
      match: '78% Match',
      location: 'Hybrid (Mumbai)',
      experience: '1-3 Yrs',
      package: '₹8 - 11 LPA',
      skills: ['Equity Analysis', 'Bloomberg', 'DCF'],
      portal: 'iimjobs',
      applied: false
    },
    {
      id: 4,
      title: 'Investment Banking Associate',
      company: 'Goldman Sachs',
      match: '95% Match',
      location: 'Bengaluru / Pune',
      experience: '2-4 Yrs',
      package: '₹14 - 18 LPA',
      skills: ['M&A', 'Financial Analysis', 'Pitchbooks'],
      portal: 'Instahyre',
      applied: false
    },
    {
      id: 5,
      title: 'Credit Risk Analyst',
      company: 'Barclays',
      match: '88% Match',
      location: 'Pune, India',
      experience: '1-2 Yrs',
      package: '₹9 - 12 LPA',
      skills: ['Credit Risk', 'SQL', 'Risk Modeling'],
      portal: 'TodayWalkins',
      applied: false
    },
    {
      id: 6,
      title: 'Corporate Finance Intern',
      company: 'EY India',
      match: '91% Match',
      location: 'Mumbai, India',
      experience: '0-1 Yrs',
      package: '₹5 - 7 LPA',
      skills: ['Excel', 'Accounting', 'Corporate Finance'],
      portal: 'Wellfound',
      applied: false
    }
  ]);

  const handleAutoApply = (id) => {
    setJobs(jobs.map(j => j.id === id ? { ...j, applied: true } : j));
  };

  // Safe filter logic - returns matched portal jobs or fallback to all jobs
  const filteredJobs = selectedPortal === 'All' 
    ? jobs 
    : jobs.filter(j => j.portal.toLowerCase() === selectedPortal.toLowerCase());

  const displayJobs = filteredJobs.length > 0 ? filteredJobs : jobs;

  return (
    <div className="min-h-screen bg-slate-50/50 space-y-8 max-w-full mx-auto">
      
      {/* PARTNER JOB PORTALS GRID & DROPDOWN */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-sky-50 border border-sky-100 flex items-center justify-center text-sky-600">
              <Globe className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Partner Job Portals</h2>
              <p className="text-[11px] text-slate-500">Filter jobs or jump directly to partner portals</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Quick Dropdown Filter */}
            <div className="relative">
              <select
                value={selectedPortal}
                onChange={(e) => setSelectedPortal(e.target.value)}
                className="bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-bold px-3.5 py-2 rounded-xl outline-none transition cursor-pointer pr-8 appearance-none"
              >
                <option value="All">All Partner Portals</option>
                {jobPortals.filter(p => p.id !== 'all').map((portal) => (
                  <option key={portal.id} value={portal.name}>
                    {portal.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            {/* Grid Toggle Button */}
            <button
              onClick={() => setShowPortalGrid(!showPortalGrid)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold border transition ${
                showPortalGrid 
                  ? 'bg-sky-50 text-sky-600 border-sky-200' 
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              <Grid className="w-3.5 h-3.5" />
              <span>{showPortalGrid ? 'Hide Portal Grid' : 'View Portal Grid'}</span>
            </button>
          </div>
        </div>

        {/* Portals Grid */}
        {showPortalGrid && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 pt-3 border-t border-slate-100 animate-fadeIn">
            {jobPortals.map((portal, idx) => {
              const isSelected = (selectedPortal === 'All' && portal.id === 'all') || selectedPortal === portal.name;
              return (
                <div
                  key={idx}
                  onClick={() => setSelectedPortal(portal.id === 'all' ? 'All' : portal.name)}
                  className={`group bg-slate-50/70 border rounded-xl p-3 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between relative ${
                    isSelected
                      ? 'border-sky-500 bg-sky-50/50 ring-2 ring-sky-500/20'
                      : 'border-slate-200/80 hover:border-sky-300'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[9px] font-extrabold px-2 py-0.5 rounded-full bg-white border border-slate-200/80 text-slate-600">
                        {portal.badge}
                      </span>
                      {portal.url !== '#' && (
                        <a
                          href={portal.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-slate-400 hover:text-sky-600 p-0.5"
                          title={`Visit ${portal.name}`}
                        >
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 group-hover:text-sky-600 transition-colors line-clamp-1">
                        {portal.name}
                      </h3>
                      <p className="text-[10px] text-slate-400 line-clamp-1 font-medium mt-0.5">
                        {portal.desc}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Title & Post Job Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            Job Portal <Sparkles className="w-5 h-5 text-amber-500" />
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Explore AI-matched finance opportunities {selectedPortal !== 'All' ? `from ${selectedPortal}` : 'across all portals'}
          </p>
        </div>

        <button className="flex items-center justify-center space-x-2 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition shadow-md shadow-sky-500/20 active:scale-95">
          <Plus className="w-4 h-4" />
          <span>Post New Job</span>
        </button>
      </div>

      {/* AI Auto-Apply Jobs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {displayJobs.map((job) => (
          <div key={job.id} className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-4">
            
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{job.title}</h3>
                  <p className="text-xs text-slate-500 font-medium">{job.company}</p>
                </div>
                <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full whitespace-nowrap">
                  {job.match}
                </span>
              </div>

              <div className="space-y-1.5 text-xs text-slate-500 font-medium">
                <div className="flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-rose-500" />
                  <span>{job.location}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Briefcase className="w-3.5 h-3.5 text-amber-500" />
                  <span>{job.experience}</span>
                  <span className="text-slate-300">|</span>
                  <IndianRupee className="w-3.5 h-3.5 text-emerald-500" />
                  <span>{job.package}</span>
                </div>
              </div>

              {/* Skills and Portal Badges */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {job.skills.map((skill, sIdx) => (
                  <span key={sIdx} className="text-[10px] font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md">
                    {skill}
                  </span>
                ))}
                <span className="text-[10px] font-semibold bg-sky-50 text-sky-700 px-2 py-0.5 rounded-md border border-sky-100">
                  via {job.portal}
                </span>
              </div>
            </div>

            {/* AI Auto-Apply Action Button */}
            <button 
              onClick={() => handleAutoApply(job.id)}
              disabled={job.applied}
              className={`w-full font-bold text-xs py-2.5 rounded-xl transition shadow-sm flex items-center justify-center gap-2 ${
                job.applied 
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 cursor-default shadow-none' 
                  : 'bg-sky-500 hover:bg-sky-600 text-white shadow-sky-500/20 active:scale-95'
              }`}
            >
              {job.applied ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" /> AI Auto-Applied Successfully
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" /> AI Auto-Apply Now
                </>
              )}
            </button>
          </div>
        ))}
      </div>

    </div>
  );
}