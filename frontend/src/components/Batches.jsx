import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  Search, 
  Calendar, 
  Clock, 
  MoreVertical,
  ChevronRight,
  PieChart as PieIcon,
  Sparkles,
  TrendingUp,
  Award,
  AlertCircle,
  X,
  ShieldCheck,
  BookOpen
} from 'lucide-react';

export default function Batches() {
  const [searchTerm, setSearchTerm] = useState('');
  const [scheduleFilter, setScheduleFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [activeHoverSlice, setActiveHoverSlice] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => setIsLoaded(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const [batches, setBatches] = useState([
    {
      id: 1,
      code: 'FIN-04',
      name: 'Financial Modeling & Valuation',
      trainer: 'Arjun Mehta',
      type: 'Weekday',
      schedule: 'Mon, Wed, Fri',
      time: '10:00 AM - 12:00 PM',
      status: 'Ongoing',
      totalStudents: 40,
      room: 'Virtual Room A',
      progress: 75,
      metrics: {
        completed: 18, 
        mockGiven: 12, 
        regular: 7,    
        absent: 3      
      }
    },
    {
      id: 2,
      code: 'CFA-01',
      name: 'CFA Level 1 Intensive Batch',
      trainer: 'Sara Joshi',
      type: 'Weekend',
      schedule: 'Sat & Sun',
      time: '02:00 PM - 05:00 PM',
      status: 'Ongoing',
      totalStudents: 50,
      room: 'Auditorium 2',
      progress: 60,
      metrics: {
        completed: 20,
        mockGiven: 15,
        regular: 10,
        absent: 5
      }
    },
    {
      id: 3,
      code: 'PBI-02',
      name: 'Power BI & Advanced Excel',
      trainer: 'Dev Tripathi',
      type: 'Weekday',
      schedule: 'Mon - Fri',
      time: '05:00 PM - 06:30 PM',
      status: 'Upcoming',
      totalStudents: 35,
      room: 'Lab 3',
      progress: 15,
      metrics: {
        completed: 10,
        mockGiven: 12,
        regular: 8,
        absent: 5
      }
    },
    {
      id: 4,
      code: 'INV-09',
      name: 'Investment Banking & M&A',
      trainer: 'Neha Sharma',
      type: 'Weekend',
      schedule: 'Sat & Sun',
      time: '10:00 AM - 01:00 PM',
      status: 'Completed',
      totalStudents: 45,
      room: 'Virtual Room B',
      progress: 100,
      metrics: {
        completed: 30,
        mockGiven: 10,
        regular: 3,
        absent: 2
      }
    },
  ]);

  const filteredBatches = batches.filter(batch => {
    const matchesSearch = batch.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          batch.trainer.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          batch.code.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSchedule = scheduleFilter === 'All' || batch.type === scheduleFilter;
    const matchesStatus = statusFilter === 'All' || batch.status === statusFilter;
    return matchesSearch && matchesSchedule && matchesStatus;
  });

  const renderResponsivePieChart = (batchId, metrics, total) => {
    const slices = [
      { key: 'completed', label: 'Completed Course', count: metrics.completed, color: '#10B981', bgClass: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-100 dark:border-emerald-900' },
      { key: 'mockGiven', label: 'Giving Mocks', count: metrics.mockGiven, color: '#3B82F6', bgClass: 'bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border-blue-100 dark:border-blue-900' },
      { key: 'regular', label: 'Regular to Classes', count: metrics.regular, color: '#8B5CF6', bgClass: 'bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border-purple-100 dark:border-purple-900' },
      { key: 'absent', label: 'Absent / Irregular', count: metrics.absent, color: '#F59E0B', bgClass: 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-100 dark:border-amber-900' }
    ];

    let cumulativePercent = 0;
    const getCoordinatesForPercent = (percent) => {
      const x = Math.cos(2 * Math.PI * percent);
      const y = Math.sin(2 * Math.PI * percent);
      return [x, y];
    };

    const slicePaths = slices.map((slice) => {
      const percent = total > 0 ? slice.count / total : 0;
      if (percent <= 0) return { ...slice, path: '', percent: 0 };
      
      const [startX, startY] = getCoordinatesForPercent(cumulativePercent);
      cumulativePercent += percent;
      const [endX, endY] = getCoordinatesForPercent(cumulativePercent);
      const largeArcFlag = percent > 0.5 ? 1 : 0;
      
      const path = `M 0 0 L ${startX} ${startY} A 1 1 0 ${largeArcFlag} 1 ${endX} ${endY} Z`;
      return { ...slice, path, percent };
    });

    const hoveredKey = activeHoverSlice?.batchId === batchId ? activeHoverSlice.key : null;

    return (
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-1 w-full">
        <div className="relative w-36 h-36 sm:w-40 sm:h-40 flex items-center justify-center shrink-0 group mx-auto">
          <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/10 to-blue-500/15 rounded-full blur-xl group-hover:scale-110 transition-transform duration-700"></div>
          
          <svg viewBox="-1.2 -1.2 2.4 2.4" className="w-full h-full -rotate-90 transform drop-shadow-md">
            {slicePaths.map((slice) => {
              if (slice.percent === 0) return null;
              const isHovered = hoveredKey === slice.key;
              return (
                <path 
                  key={slice.key}
                  d={slice.path} 
                  fill={slice.color} 
                  onMouseEnter={() => setActiveHoverSlice({ batchId, key: slice.key })}
                  onMouseLeave={() => setActiveHoverSlice(null)}
                  className={`transition-all duration-300 cursor-pointer origin-center ${
                    isHovered ? 'scale-110 brightness-110 drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]' : 'hover:opacity-95'
                  }`}
                  style={{
                    transform: isHovered ? 'scale(1.08)' : 'scale(1)',
                    transformOrigin: '0px 0px'
                  }}
                />
              );
            })}
            <circle cx="0" cy="0" r="0.68" className="fill-white dark:fill-slate-900 transition-colors shadow-inner" />
          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none px-2">
            <span className="text-[9px] text-slate-400 dark:text-slate-500 font-extrabold uppercase tracking-widest">
              {hoveredKey ? hoveredKey.toUpperCase() : 'TOTAL'}
            </span>
            <span className="text-sm sm:text-base font-black text-slate-900 dark:text-white">
              {hoveredKey ? slices.find(s => s.key === hoveredKey)?.count : total}
            </span>
            <span className="text-[8px] text-slate-500 dark:text-slate-400 font-medium">Students</span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2 w-full flex-1">
          {slices.map((slice) => {
            const isHovered = hoveredKey === slice.key;
            return (
              <div 
                key={slice.key}
                onMouseEnter={() => setActiveHoverSlice({ batchId, key: slice.key })}
                onMouseLeave={() => setActiveHoverSlice(null)}
                className={`flex items-center justify-between px-3 py-1.5 rounded-xl border transition-all duration-300 cursor-pointer text-xs ${slice.bgClass} ${
                  isHovered ? 'scale-[1.02] shadow-sm border-indigo-500 dark:border-indigo-400' : 'opacity-90 hover:opacity-100'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span 
                    className="w-2.5 h-2.5 rounded-full shadow-sm transition-transform duration-300"
                    style={{ backgroundColor: slice.color, transform: isHovered ? 'scale(1.3)' : 'scale(1)' }} 
                  />
                  <span className="font-bold tracking-tight">{slice.label}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="font-black">{slice.count}</span>
                  <span className="text-[10px] opacity-70">({Math.round((slice.count / total) * 100)}%)</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className={`space-y-4 transition-opacity duration-700 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}>
      
      {/* Top Header - Matches Student Directory Header Style */}
      <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-3 py-0.5 rounded-full bg-indigo-50 text-indigo-600 text-xs font-bold flex items-center gap-1 border border-indigo-100">
              <Sparkles size={12} /> Live Academic Command Center
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Student Batches & Analytics</h1>
          <p className="text-slate-500 text-xs mt-0.5">Real-time interactive telemetry on student attendance and course velocity.</p>
        </div>

        <button 
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-5 py-2.5 rounded-2xl text-xs font-semibold shadow-sm hover:shadow-md transition-all"
        >
          <Plus size={16} />
          <span>Create New Batch</span>
        </button>
      </div>

      {/* Summary Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="group bg-white p-4 rounded-2xl border border-slate-100 shadow-sm transition-all hover:border-blue-300">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Total Active Batches</p>
              <h3 className="text-2xl font-black text-slate-900 mt-0.5">12</h3>
              <p className="text-[11px] text-emerald-600 font-semibold mt-0.5 flex items-center gap-1">
                <TrendingUp size={10} /> +18% vs last month
              </p>
            </div>
            <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center">
              <Users size={20} />
            </div>
          </div>
        </div>

        <div className="group bg-white p-4 rounded-2xl border border-slate-100 shadow-sm transition-all hover:border-emerald-300">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Weekday Cohorts</p>
              <h3 className="text-2xl font-black text-slate-900 mt-0.5">8</h3>
              <p className="text-[11px] text-slate-500 mt-0.5">High engagement rate</p>
            </div>
            <div className="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center">
              <Calendar size={20} />
            </div>
          </div>
        </div>

        <div className="group bg-white p-4 rounded-2xl border border-slate-100 shadow-sm transition-all hover:border-purple-300">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Weekend Cohorts</p>
              <h3 className="text-2xl font-black text-slate-900 mt-0.5">4</h3>
              <p className="text-[11px] text-purple-600 font-semibold mt-0.5 flex items-center gap-1">
                <Award size={10} /> 96% retention
              </p>
            </div>
            <div className="w-10 h-10 bg-purple-50 text-purple-600 rounded-xl flex items-center justify-center">
              <Clock size={20} />
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Search & Filter Toolbar */}
      <div className="bg-white p-3.5 rounded-2xl border border-slate-100 shadow-sm flex flex-col lg:flex-row items-center justify-between gap-3">
        <div className="relative w-full lg:w-80">
          <Search className="absolute left-3.5 top-3 text-slate-400" size={16} />
          <input 
            type="text" 
            placeholder="Search by code, batch name or trainer..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
          <div className="flex items-center bg-slate-100 p-1 rounded-xl">
            {['All', 'Weekday', 'Weekend'].map((filter) => (
              <button
                key={filter}
                onClick={() => setScheduleFilter(filter)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  scheduleFilter === filter 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {filter === 'All' ? 'All Schedules' : filter}
              </button>
            ))}
          </div>

          <div className="flex items-center bg-slate-100 p-1 rounded-xl">
            {['All', 'Ongoing', 'Upcoming', 'Completed'].map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  statusFilter === status 
                    ? 'bg-blue-600 text-white shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Batches Grid (Restored your individual batch cards) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredBatches.map((batch, index) => {
          const statusColor = 
            batch.status === 'Ongoing' ? 'bg-emerald-50 text-emerald-600 border-emerald-200' :
            batch.status === 'Upcoming' ? 'bg-amber-50 text-amber-600 border-amber-200' : 
            'bg-slate-100 text-slate-600 border-slate-200';

          const typeColor = batch.type === 'Weekday' ? 'bg-blue-50 text-blue-600' : 'bg-purple-50 text-purple-600';

          return (
            <div 
              key={batch.id} 
              style={{ animationDelay: `${index * 100}ms` }}
              className="group bg-white rounded-2xl border border-slate-100 shadow-sm p-5 hover:shadow-md transition-all duration-300 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="px-2.5 py-0.5 rounded-lg text-[11px] font-mono font-black bg-slate-900 text-white">
                      {batch.code}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-lg text-[11px] font-bold ${typeColor}`}>
                      {batch.type}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-lg text-[11px] font-bold border ${statusColor} flex items-center gap-1`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${batch.status === 'Ongoing' ? 'bg-emerald-500 animate-pulse' : batch.status === 'Upcoming' ? 'bg-amber-500' : 'bg-slate-400'}`} />
                      {batch.status}
                    </span>
                  </div>
                  <button className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100">
                    <MoreVertical size={16} />
                  </button>
                </div>

                <h3 className="text-base font-black text-slate-900 group-hover:text-indigo-600 transition-colors">{batch.name}</h3>
                <p className="text-xs text-slate-500 mb-4 flex items-center gap-1 mt-0.5">
                  <BookOpen size={12} className="text-indigo-500" />
                  Lead Trainer: <span className="font-bold text-slate-700">{batch.trainer}</span>
                </p>

                {/* Progress Bar */}
                <div className="mb-4 bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <div className="flex items-center justify-between text-xs font-bold mb-1">
                    <span className="text-slate-500">Course Progress</span>
                    <span className="text-indigo-600">{batch.progress}%</span>
                  </div>
                  <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                    <div 
                      className="bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 h-full rounded-full transition-all duration-1000 ease-out" 
                      style={{ width: `${batch.progress}%` }}
                    />
                  </div>
                </div>

                {/* Schedule info badges */}
                <div className="grid grid-cols-2 gap-2 bg-slate-50 p-3 rounded-xl text-xs text-slate-600 mb-4 border border-slate-100">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-blue-100 text-blue-600 rounded-lg">
                      <Calendar size={14} />
                    </div>
                    <span className="font-semibold">{batch.schedule}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-purple-100 text-purple-600 rounded-lg">
                      <Clock size={14} />
                    </div>
                    <span className="font-semibold">{batch.time}</span>
                  </div>
                </div>

                {/* Donut Chart Section */}
                <div className="bg-slate-50 border border-slate-100 rounded-xl p-3.5 mb-4 shadow-inner">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1.5 text-xs font-black text-slate-800 uppercase tracking-wide">
                      <PieIcon size={14} className="text-blue-600" />
                      <span>Student Status Headcount</span>
                    </div>
                    <span className="text-[10px] font-bold text-slate-400">{batch.room}</span>
                  </div>
                  {renderResponsivePieChart(batch.id, batch.metrics, batch.totalStudents)}
                </div>
              </div>

              {/* Card Footer */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                <div className="flex items-center gap-1 text-xs font-semibold text-emerald-600">
                  <ShieldCheck size={14} />
                  <span>Health: Optimal</span>
                </div>
                <button 
                  onClick={() => setSelectedBatch(batch)}
                  className="group/btn flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-indigo-700 bg-blue-50 px-3 py-1.5 rounded-lg transition-all"
                >
                  <span>View Details</span>
                  <ChevronRight size={14} className="transition-transform group-hover/btn:translate-x-1" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {filteredBatches.length === 0 && (
        <div className="text-center py-12 bg-white rounded-2xl border border-slate-100 mt-4">
          <AlertCircle size={36} className="mx-auto text-slate-400 mb-2" />
          <h3 className="text-base font-bold text-slate-800">No batches found</h3>
          <p className="text-xs text-slate-500 mt-0.5">Try adjusting your search query or schedule filters.</p>
        </div>
      )}

      {/* Batch Details Modal */}
      {selectedBatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl border border-slate-100 max-w-md w-full p-6 shadow-xl relative">
            <button 
              onClick={() => setSelectedBatch(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 bg-slate-50 p-1.5 rounded-full"
            >
              <X size={16} />
            </button>

            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-lg text-xs font-mono font-bold bg-indigo-600 text-white">
                {selectedBatch.code}
              </span>
              <span className="px-2.5 py-0.5 rounded-lg text-xs font-bold bg-emerald-50 text-emerald-600">
                {selectedBatch.status}
              </span>
            </div>

            <h2 className="text-xl font-black text-slate-900 mb-1">{selectedBatch.name}</h2>
            <p className="text-xs text-slate-500 mb-4">Led by <span className="font-semibold text-slate-800">{selectedBatch.trainer}</span> in {selectedBatch.room}</p>

            <div className="space-y-3 mb-5">
              <div className="bg-slate-50 p-3 rounded-xl flex items-center justify-between text-xs">
                <span className="text-slate-600 font-medium">Schedule Timing</span>
                <span className="font-bold text-slate-800">{selectedBatch.schedule} | {selectedBatch.time}</span>
              </div>
              <div className="bg-slate-50 p-3 rounded-xl flex items-center justify-between text-xs">
                <span className="text-slate-600 font-medium">Total Enrollment</span>
                <span className="font-bold text-slate-800">{selectedBatch.totalStudents} Students</span>
              </div>
              <div className="bg-slate-50 p-3 rounded-xl flex items-center justify-between text-xs">
                <span className="text-slate-600 font-medium">Course Completion Rate</span>
                <span className="font-bold text-emerald-600">{selectedBatch.progress}%</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2">
              <button 
                onClick={() => setSelectedBatch(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200"
              >
                Close
              </button>
              <button 
                onClick={() => {
                  alert(`Exporting telemetry report for ${selectedBatch.name}`);
                  setSelectedBatch(null);
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md"
              >
                Export Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Batch Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl border border-slate-100 max-w-md w-full p-6 shadow-xl relative">
            <button 
              onClick={() => setIsCreateModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 bg-slate-50 p-1.5 rounded-full"
            >
              <X size={16} />
            </button>

            <h2 className="text-xl font-black text-slate-900 mb-1">Create New Batch</h2>
            <p className="text-xs text-slate-500 mb-4">Setup a new student cohort and schedule.</p>

            <form onSubmit={(e) => {
              e.preventDefault();
              setIsCreateModalOpen(false);
            }} className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">Batch Name</label>
                <input required type="text" placeholder="e.g., Python for Finance" className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-blue-500" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">Batch Code</label>
                  <input required type="text" placeholder="e.g., PY-05" className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">Trainer Name</label>
                  <input required type="text" placeholder="e.g., Rahul Verma" className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-blue-500" />
                </div>
              </div>
              <div className="flex items-center justify-end gap-2 pt-3">
                <button 
                  type="button" 
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-100 text-slate-700"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md"
                >
                  Save Batch
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}