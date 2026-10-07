import React, { useState } from 'react';
import { 
  Search, 
  Plus, 
  Calendar, 
  Clock, 
  Users, 
  BookOpen, 
  Filter, 
  X, 
  ChevronRight,
  MoreVertical
} from 'lucide-react';

export default function StudentBatchesSection() {
  // State variables for search and filtering
  const [searchQuery, setSearchQuery] = useState('');
  const [statusTab, setStatusTab] = useState('All'); // All | Ongoing | Upcoming | Completed
  const [scheduleType, setScheduleType] = useState('All'); // All | Weekdays | Weekends
  const [courseFilter, setCourseFilter] = useState('All');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form State for creating a new batch
  const [newBatch, setNewBatch] = useState({
    title: '',
    course: 'Financial Modeling',
    trainer: '',
    scheduleType: 'Weekdays',
    days: 'Mon, Wed, Fri',
    time: '08:00 AM - 10:00 AM',
    maxCapacity: 30
  });

  // Sample Batches Data
  const [batches, setBatches] = useState([
    {
      id: 'B001',
      title: 'Financial Modeling & Valuation - B4',
      course: 'Financial Modeling',
      trainer: 'Arjun Mehta',
      status: 'Ongoing',
      scheduleType: 'Weekdays',
      days: 'Mon, Wed, Fri',
      time: '08:00 AM - 10:00 AM',
      studentsCount: 28,
      maxCapacity: 30
    },
    {
      id: 'B002',
      title: 'CFA Level 1 Intensive Batch',
      course: 'Corporate Finance',
      trainer: 'Sara Joshi',
      status: 'Ongoing',
      scheduleType: 'Weekends',
      days: 'Sat, Sun',
      time: '10:00 AM - 02:00 PM',
      studentsCount: 35,
      maxCapacity: 40
    },
    {
      id: 'B003',
      title: 'DSA & Tech Support - Batch 01',
      course: 'DSA',
      trainer: 'Rohan Sharma',
      status: 'Upcoming',
      scheduleType: 'Weekdays',
      days: 'Tue, Thu, Sat',
      time: '06:00 PM - 08:00 PM',
      studentsCount: 18,
      maxCapacity: 25
    },
    {
      id: 'B004',
      title: 'Equity Research Masterclass',
      course: 'Equity Research',
      trainer: 'Priya Verma',
      status: 'Ongoing',
      scheduleType: 'Weekends',
      days: 'Sat, Sun',
      time: '02:00 PM - 06:00 PM',
      studentsCount: 30,
      maxCapacity: 30
    }
  ]);

  // Handle New Batch Creation
  const handleCreateBatch = (e) => {
    e.preventDefault();
    if (!newBatch.title || !newBatch.trainer) return;

    const created = {
      id: `B00${batches.length + 1}`,
      ...newBatch,
      status: 'Upcoming',
      studentsCount: 0
    };

    setBatches([created, ...batches]);
    setIsModalOpen(false);
    setNewBatch({
      title: '',
      course: 'Financial Modeling',
      trainer: '',
      scheduleType: 'Weekdays',
      days: 'Mon, Wed, Fri',
      time: '08:00 AM - 10:00 AM',
      maxCapacity: 30
    });
  };

  // Multi-level filtering
  const filteredBatches = batches.filter((b) => {
    const matchesSearch =
      b.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.trainer.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusTab === 'All' || b.status === statusTab;
    const matchesSchedule = scheduleType === 'All' || b.scheduleType === scheduleType;
    const matchesCourse = courseFilter === 'All' || b.course === courseFilter;

    return matchesSearch && matchesStatus && matchesSchedule && matchesCourse;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 bg-slate-50/50 min-h-screen">
      
      {/* 1. TOP HEADER BANNER */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Student Batches</h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage active, upcoming, and completed course-wise student batches.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 via-indigo-600 to-sky-500 hover:brightness-105 text-white text-xs font-bold px-5 py-3 rounded-xl transition shadow-md shadow-blue-500/20 active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>Create New Batch</span>
        </button>
      </div>

      {/* 2. STATS OVERVIEW CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400">Total Batches</p>
            <h2 className="text-2xl font-extrabold text-slate-800 mt-1">{batches.length}</h2>
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
            <Users className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400">Ongoing Batches</p>
            <h2 className="text-2xl font-extrabold text-slate-800 mt-1">
              {batches.filter((b) => b.status === 'Ongoing').length}
            </h2>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400">Upcoming Batches</p>
            <h2 className="text-2xl font-extrabold text-slate-800 mt-1">
              {batches.filter((b) => b.status === 'Upcoming').length}
            </h2>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
            <Calendar className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* 3. CONTROLS BAR (Search, Schedule Toggle, Course, and Status Filters) */}
      <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
        
        {/* Search Input */}
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search batch name or trainer..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2 text-xs font-medium text-slate-700 outline-none focus:bg-white focus:ring-2 focus:ring-blue-500 transition"
          />
        </div>

        {/* Filters Group */}
        <div className="flex flex-wrap items-center gap-3">
          
          {/* Weekdays / Weekends Toggle Bar */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-medium">
            <span className="text-[10px] font-bold text-slate-400 px-2 uppercase">Schedule:</span>
            {['All', 'Weekdays', 'Weekends'].map((type) => (
              <button
                key={type}
                onClick={() => setScheduleType(type)}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  scheduleType === type
                    ? 'bg-white text-blue-600 font-bold shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          {/* Course Selector Dropdown */}
          <select
            value={courseFilter}
            onChange={(e) => setCourseFilter(e.target.value)}
            className="bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 outline-none transition cursor-pointer"
          >
            <option value="All">Course: All</option>
            <option value="Financial Modeling">Financial Modeling</option>
            <option value="Corporate Finance">Corporate Finance</option>
            <option value="DSA">DSA</option>
            <option value="Equity Research">Equity Research</option>
          </select>

          {/* Status Tabs */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-medium">
            {['All', 'Ongoing', 'Upcoming', 'Completed'].map((tab) => (
              <button
                key={tab}
                onClick={() => setStatusTab(tab)}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  statusTab === tab
                    ? 'bg-blue-600 text-white font-bold shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

        </div>
      </div>

      {/* 4. BATCH CARDS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-5">
        {filteredBatches.length > 0 ? (
          filteredBatches.map((batch) => (
            <div
              key={batch.id}
              className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition space-y-4 relative group"
            >
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2">
                  {/* Status Badge */}
                  <span
                    className={`px-2.5 py-1 font-bold text-[10px] rounded-md border ${
                      batch.status === 'Ongoing'
                        ? 'bg-emerald-50 text-emerald-600 border-emerald-100'
                        : batch.status === 'Upcoming'
                        ? 'bg-amber-50 text-amber-600 border-amber-100'
                        : 'bg-slate-100 text-slate-600 border-slate-200'
                    }`}
                  >
                    {batch.status}
                  </span>

                  {/* Weekdays / Weekends Badge */}
                  <span
                    className={`px-2.5 py-1 font-bold text-[10px] rounded-md border ${
                      batch.scheduleType === 'Weekends'
                        ? 'bg-purple-50 text-purple-600 border-purple-100'
                        : 'bg-blue-50 text-blue-600 border-blue-100'
                    }`}
                  >
                    {batch.scheduleType}
                  </span>
                </div>

                <button className="text-slate-400 hover:text-slate-600 p-1 rounded-lg">
                  <MoreVertical className="w-4 h-4" />
                </button>
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-800 group-hover:text-blue-600 transition">
                  {batch.title}
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Trainer: <span className="font-semibold text-slate-700">{batch.trainer}</span>
                </p>
              </div>

              {/* Progress / Enrollment Bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-[11px] font-semibold text-slate-500">
                  <span>Capacity</span>
                  <span>
                    {batch.studentsCount} / {batch.maxCapacity} Enrolled
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-indigo-600 h-full rounded-full transition-all duration-300"
                    style={{ width: `${(batch.studentsCount / batch.maxCapacity) * 100}%` }}
                  />
                </div>
              </div>

              {/* Card Footer Meta */}
              <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs text-slate-500 gap-2">
                <div className="flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>{batch.days}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>{batch.time}</span>
                </div>
                <div className="flex items-center gap-1 text-blue-600 font-bold hover:underline cursor-pointer">
                  <span>Manage</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-2 py-12 text-center text-slate-400 font-medium bg-white rounded-2xl border border-slate-100">
            No batches found for the selected filters.
          </div>
        )}
      </div>

      {/* 5. CREATE NEW BATCH MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 animate-fadeIn">
            
            <div className="flex justify-between items-center pb-3 border-b border-slate-100 mb-4">
              <h2 className="text-base font-bold text-slate-800">Create New Student Batch</h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateBatch} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Batch Name / Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Financial Modeling - Batch 05"
                  value={newBatch.title}
                  onChange={(e) => setNewBatch({ ...newBatch, title: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Course</label>
                  <select
                    value={newBatch.course}
                    onChange={(e) => setNewBatch({ ...newBatch, course: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="Financial Modeling">Financial Modeling</option>
                    <option value="Corporate Finance">Corporate Finance</option>
                    <option value="DSA">DSA</option>
                    <option value="Equity Research">Equity Research</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Trainer Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Arjun Mehta"
                    value={newBatch.trainer}
                    onChange={(e) => setNewBatch({ ...newBatch, trainer: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Schedule Type</label>
                  <select
                    value={newBatch.scheduleType}
                    onChange={(e) =>
                      setNewBatch({
                        ...newBatch,
                        scheduleType: e.target.value,
                        days: e.target.value === 'Weekends' ? 'Sat, Sun' : 'Mon, Wed, Fri'
                      })
                    }
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="Weekdays">Weekdays</option>
                    <option value="Weekends">Weekends</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Days</label>
                  <input
                    type="text"
                    value={newBatch.days}
                    onChange={(e) => setNewBatch({ ...newBatch, days: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Time Slot</label>
                  <input
                    type="text"
                    placeholder="e.g. 08:00 AM - 10:00 AM"
                    value={newBatch.time}
                    onChange={(e) => setNewBatch({ ...newBatch, time: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Max Capacity</label>
                  <input
                    type="number"
                    value={newBatch.maxCapacity}
                    onChange={(e) => setNewBatch({ ...newBatch, maxCapacity: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 mt-4">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 font-medium text-slate-600 hover:bg-slate-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-md"
                >
                  Save & Launch Batch
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

    </div>
  );
}