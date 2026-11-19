import React, { useMemo, useState } from 'react';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Plus,
  Search,
  Video,
  BookOpen,
  CheckCircle2,
  Clock,
  PlaneTakeoff,
  AlertTriangle,
  Users,
  Trash2,
  Pencil,
  X,
  Sparkles,
  Check,
} from 'lucide-react';

const TRAINERS = [
  {
    id: 'vikram',
    name: 'Vikram Desai',
    initials: 'VD',
    track: 'Full Stack & System Design',
    leaveQuota: 6,
    accent: 'border-blue-500 bg-blue-50/70 text-blue-700',
    badge: 'bg-blue-600 text-white',
  },
  {
    id: 'ananya',
    name: 'Ananya Kulkarni',
    initials: 'AK',
    track: 'Communication & HR Readiness',
    leaveQuota: 6,
    accent: 'border-emerald-500 bg-emerald-50/70 text-emerald-700',
    badge: 'bg-emerald-600 text-white',
  },
  {
    id: 'siddharth',
    name: 'Siddharth Joshi',
    initials: 'SJ',
    track: 'Financial Modelling & Analytics',
    leaveQuota: 6,
    accent: 'border-purple-500 bg-purple-50/70 text-purple-700',
    badge: 'bg-purple-600 text-white',
  },
  {
    id: 'neha',
    name: 'Neha Deshmukh',
    initials: 'ND',
    track: 'DSA & Aptitude',
    leaveQuota: 6,
    accent: 'border-amber-500 bg-amber-50/70 text-amber-800',
    badge: 'bg-amber-600 text-white',
  },
];

// Dates formatted YYYY-MM-DD (default anchor: 2026-11-19)
const INITIAL_ITEMS = [
  {
    id: 1,
    date: '2026-11-18',
    trainerId: 'vikram',
    type: 'Technical Mock',
    studentOrBatch: 'Aarav Sharma · Batch A - Full Stack',
    timeSlot: '10:00 – 10:45 (45 mins)',
    hours: 0.75,
    topic: 'React Hooks, Context API & REST API Integration',
    notes: 'Focus on state management efficiency and error handling.',
    done: true,
  },
  {
    id: 2,
    date: '2026-11-18',
    trainerId: 'vikram',
    type: 'Class Session',
    studentOrBatch: 'Batch FinXL-04 · Node.js & Express',
    timeSlot: '11:00 – 12:00 (60 mins)',
    hours: 1.0,
    topic: 'Middleware, JWT Auth & REST API Routing',
    notes: 'Live coding walkthrough + Postman collection check.',
    done: false,
  },
  {
    id: 3,
    date: '2026-11-18',
    trainerId: 'vikram',
    type: 'Technical Mock',
    studentOrBatch: 'Rohan Kulkarni · Batch A - Full Stack',
    timeSlot: '14:00 – 14:45 (45 mins)',
    hours: 0.75,
    topic: 'System Design: URL Shortener & Rate Limiter',
    notes: 'Check caching strategy and DB indexing choices.',
    done: false,
  },
  {
    id: 4,
    date: '2026-11-19',
    trainerId: 'vikram',
    type: 'Technical Mock',
    studentOrBatch: 'Sneha Patil · Batch A - Full Stack',
    timeSlot: '10:00 – 11:00 (60 mins)',
    hours: 1.0,
    topic: 'PostgreSQL Joins, Transactions & Query Tuning',
    notes: 'Review EXPLAIN ANALYZE plans.',
    done: false,
  },
  {
    id: 5,
    date: '2026-11-19',
    trainerId: 'vikram',
    type: 'Class Session',
    studentOrBatch: 'Batch FinXL-04 · FastAPI & Python',
    timeSlot: '15:00 – 16:30 (90 mins)',
    hours: 1.5,
    topic: 'Pydantic Validation & Async Endpoints',
    notes: 'Hands-on lab exercise.',
    done: false,
  },
  {
    id: 6,
    date: '2026-11-18',
    trainerId: 'ananya',
    type: 'HR Mock',
    studentOrBatch: 'Pooja Nair · Batch FinXL-03',
    timeSlot: '11:30 – 12:15 (45 mins)',
    hours: 0.75,
    topic: 'STAR Method Behavioral & Salary Negotiation',
    notes: 'Work on concise 90-second answers.',
    done: true,
  },
  {
    id: 7,
    date: '2026-11-19',
    trainerId: 'ananya',
    type: 'Class Session',
    studentOrBatch: 'Batch FinXL-03 · Group Discussion',
    timeSlot: '13:00 – 14:30 (90 mins)',
    hours: 1.5,
    topic: 'Corporate Etiquette & Case Debate',
    notes: 'Evaluate turn-taking and clarity.',
    done: false,
  },
  {
    id: 8,
    date: '2026-11-19',
    trainerId: 'siddharth',
    type: 'Technical Mock',
    studentOrBatch: 'Karan Mehta · Batch Fin-02',
    timeSlot: '11:00 – 12:00 (60 mins)',
    hours: 1.0,
    topic: '3-Statement Financial Model & WACC',
    notes: 'Verify formula links and sensitivity table.',
    done: false,
  },
  {
    id: 9,
    date: '2026-11-20',
    trainerId: 'neha',
    type: 'Class Session',
    studentOrBatch: 'Batch MCA-A · Dynamic Programming',
    timeSlot: '09:30 – 11:00 (90 mins)',
    hours: 1.5,
    topic: '0/1 Knapsack, LCS & Memoization Patterns',
    notes: 'Solve 4 medium problems together.',
    done: false,
  },
];

const INITIAL_LEAVES = [
  {
    id: 'lv-1',
    trainerId: 'siddharth',
    date: '2026-11-18',
    reason: 'Personal / Medical Leave',
    status: 'Auto-Approved',
    autoApplied: true,
  },
  {
    id: 'lv-2',
    trainerId: 'neha',
    date: '2026-11-19',
    reason: 'Outstation Travel',
    status: 'Auto-Approved (Needs Reassign)',
    autoApplied: true,
  },
];

function toDateKey(dateObj) {
  const y = dateObj.getFullYear();
  const m = String(dateObj.getMonth() + 1).padStart(2, '0');
  const d = String(dateObj.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function formatPrettyDate(dateKey) {
  const [y, m, d] = dateKey.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  return dt.toLocaleDateString('en-US', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function buildMonthCells(year, month) {
  const firstDay = new Date(year, month, 1);
  const startWeekday = firstDay.getDay(); // 0 = Sun
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const prevMonthDays = new Date(year, month, 0).getDate();

  const cells = [];
  for (let i = startWeekday - 1; i >= 0; i--) {
    const day = prevMonthDays - i;
    const prevMonth = month === 0 ? 11 : month - 1;
    const prevYear = month === 0 ? year - 1 : year;
    cells.push({
      dateKey: toDateKey(new Date(prevYear, prevMonth, day)),
      dayNumber: day,
      inMonth: false,
    });
  }

  for (let day = 1; day <= daysInMonth; day++) {
    cells.push({
      dateKey: toDateKey(new Date(year, month, day)),
      dayNumber: day,
      inMonth: true,
    });
  }

  const remaining = (7 - (cells.length % 7)) % 7;
  for (let day = 1; day <= remaining; day++) {
    const nextMonth = month === 11 ? 0 : month + 1;
    const nextYear = month === 11 ? year + 1 : year;
    cells.push({
      dateKey: toDateKey(new Date(nextYear, nextMonth, day)),
      dayNumber: day,
      inMonth: false,
    });
  }

  return cells;
}

export default function LiveMocksCalendar({ role = 'Admin' }) {
  const isTrainer = role === 'Trainer';
  const isOperations = role === 'Operations' || role === 'Admin';

  const [selectedTrainerId, setSelectedTrainerId] = useState('vikram');
  const [timetableMode, setTimetableMode] = useState('trainer'); // 'trainer' | 'daywise'
  const [selectedDate, setSelectedDate] = useState('2026-11-19');
  const [viewMonth, setViewMonth] = useState(() => new Date(2026, 10, 1)); // Nov 2026
  const [searchQuery, setSearchQuery] = useState('');

  const [items, setItems] = useState(INITIAL_ITEMS);
  const [leaves, setLeaves] = useState(INITIAL_LEAVES);

  // Modals
  const [showSlotModal, setShowSlotModal] = useState(false);
  const [editingSlotId, setEditingSlotId] = useState(null);
  const [showLeaveModal, setShowLeaveModal] = useState(false);

  const [slotForm, setSlotForm] = useState({
    trainerId: 'vikram',
    date: '2026-11-19',
    type: 'Technical Mock',
    studentOrBatch: '',
    timeSlot: '11:00 – 11:45 (45 mins)',
    hours: 0.75,
    topic: '',
    notes: '',
  });

  const [leaveForm, setLeaveForm] = useState({
    trainerId: isTrainer ? 'vikram' : selectedTrainerId,
    date: selectedDate,
    reason: 'Personal / Family Leave',
  });

  const activeTrainer = useMemo(
    () => TRAINERS.find((t) => t.id === selectedTrainerId) || TRAINERS[0],
    [selectedTrainerId]
  );

  const monthLabel = viewMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const monthCells = useMemo(
    () => buildMonthCells(viewMonth.getFullYear(), viewMonth.getMonth()),
    [viewMonth]
  );

  // Leave lookup helper
  const getTrainerLeaveOnDate = (trainerId, dateKey) =>
    leaves.find((lv) => lv.trainerId === trainerId && lv.date === dateKey);

  const activeTrainerLeaveToday = getTrainerLeaveOnDate(activeTrainer.id, selectedDate);

  // Daily timetable items (either filtered by active trainer or all trainers on that day)
  const dailyTimetableItems = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return items
      .filter((it) => {
        const matchesDate = it.date === selectedDate;
        const matchesTrainer = timetableMode === 'daywise' || it.trainerId === activeTrainer.id;
        const trainer = TRAINERS.find((t) => t.id === it.trainerId);
        const matchesSearch =
          !q ||
          it.studentOrBatch.toLowerCase().includes(q) ||
          it.topic.toLowerCase().includes(q) ||
          it.type.toLowerCase().includes(q) ||
          (trainer && trainer.name.toLowerCase().includes(q));
        return matchesDate && matchesTrainer && matchesSearch;
      })
      .sort((a, b) => a.timeSlot.localeCompare(b.timeSlot));
  }, [items, selectedDate, timetableMode, activeTrainer.id, searchQuery]);

  // Metrics for selected date & trainer
  const daySessionsCount = dailyTimetableItems.length;
  const dailyHours = dailyTimetableItems.reduce((sum, it) => sum + Number(it.hours || 0), 0);
  const completedCount = dailyTimetableItems.filter((it) => it.done).length;
  const totalTrainerHours = items
    .filter((it) => it.trainerId === activeTrainer.id)
    .reduce((sum, it) => sum + Number(it.hours || 0), 0);

  // Trainer leave balances
  const trainerLeaveStats = useMemo(() => {
    return TRAINERS.map((t) => {
      const used = leaves.filter((lv) => lv.trainerId === t.id).length;
      return {
        ...t,
        usedLeaves: used,
        remainingLeaves: Math.max(t.leaveQuota - used, 0),
        scheduledDates: leaves.filter((lv) => lv.trainerId === t.id),
      };
    });
  }, [leaves]);

  const shiftMonth = (delta) => {
    setViewMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1));
  };

  const openNewSlot = () => {
    setEditingSlotId(null);
    setSlotForm({
      trainerId: activeTrainer.id,
      date: selectedDate,
      type: 'Technical Mock',
      studentOrBatch: '',
      timeSlot: '11:00 – 11:45 (45 mins)',
      hours: 0.75,
      topic: '',
      notes: '',
    });
    setShowSlotModal(true);
  };

  const openEditSlot = (slot) => {
    setEditingSlotId(slot.id);
    setSlotForm({
      trainerId: slot.trainerId,
      date: slot.date,
      type: slot.type,
      studentOrBatch: slot.studentOrBatch,
      timeSlot: slot.timeSlot,
      hours: slot.hours,
      topic: slot.topic,
      notes: slot.notes || '',
    });
    setShowSlotModal(true);
  };

  const handleSaveSlot = (e) => {
    e.preventDefault();
    if (!slotForm.topic.trim()) return;

    const payload = {
      ...slotForm,
      hours: Number(slotForm.hours) || 1,
      studentOrBatch: slotForm.studentOrBatch.trim() || 'Assigned Batch',
    };

    if (editingSlotId) {
      setItems((prev) => prev.map((it) => (it.id === editingSlotId ? { ...it, ...payload } : it)));
    } else {
      setItems((prev) => [...prev, { id: Date.now(), ...payload, done: false }]);
    }
    setSelectedDate(payload.date);
    setShowSlotModal(false);
  };

  const toggleSlotDone = (id) => {
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, done: !it.done } : it)));
  };

  const deleteSlot = (id) => {
    setItems((prev) => prev.filter((it) => it.id !== id));
  };

  // Auto-apply leave for a trainer on a selected date
  const handleAutoApplyLeave = (e) => {
    e.preventDefault();
    const exists = leaves.some(
      (lv) => lv.trainerId === leaveForm.trainerId && lv.date === leaveForm.date
    );
    if (exists) {
      alert('Leave is already recorded for this trainer on the selected date.');
      return;
    }

    const hasConflict = items.some(
      (it) => it.trainerId === leaveForm.trainerId && it.date === leaveForm.date
    );

    const newLeave = {
      id: `lv-${Date.now()}`,
      trainerId: leaveForm.trainerId,
      date: leaveForm.date,
      reason: leaveForm.reason.trim() || 'Auto-Applied Leave',
      status: hasConflict ? 'Auto-Approved (Sessions Impacted)' : 'Auto-Approved',
      autoApplied: true,
    };

    setLeaves((prev) => [...prev, newLeave]);
    setSelectedTrainerId(leaveForm.trainerId);
    setSelectedDate(leaveForm.date);
    setShowLeaveModal(false);
  };

  const removeLeave = (leaveId) => {
    setLeaves((prev) => prev.filter((lv) => lv.id !== leaveId));
  };

  return (
    <div className="space-y-5">
      {/* Top Banner Card */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-5 sm:p-6 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              Trainer Calendar, Leaves & Daily Timetable
            </h1>
            <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
              Role: {role}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Manage trainer-wise and day-wise timetables, live mocks & classes, and instant trainer leave auto-applications.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Timetable View Switcher: Trainer-Wise vs Day-Wise */}
          <div className="inline-flex rounded-xl bg-slate-100 p-1 border border-slate-200 text-xs font-bold">
            <button
              onClick={() => setTimetableMode('trainer')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer ${
                timetableMode === 'trainer'
                  ? 'bg-white text-indigo-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Trainer-Wise
            </button>
            <button
              onClick={() => setTimetableMode('daywise')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer ${
                timetableMode === 'daywise'
                  ? 'bg-white text-indigo-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Day-Wise (All)
            </button>
          </div>

          {/* Trainer Auto-Apply Leave Button */}
          <button
            onClick={() => {
              setLeaveForm({
                trainerId: activeTrainer.id,
                date: selectedDate,
                reason: 'Auto-Applied Leave',
              });
              setShowLeaveModal(true);
            }}
            className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-xl border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 text-xs font-bold transition cursor-pointer"
          >
            <PlaneTakeoff className="w-4 h-4 text-amber-700" />
            <span>Auto-Apply Leave</span>
          </button>

          {/* Add Mock / Class Slot */}
          <button
            onClick={openNewSlot}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 hover:brightness-110 text-white text-xs font-bold shadow-sm transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Add Slot</span>
          </button>
        </div>
      </div>

      {/* Trainer Selector Strip + Search */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-4 shadow-xs space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Select Trainer Calendar & Daily Timetable
          </span>
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search student, batch, topic..."
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-xl bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/25"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {TRAINERS.map((trainer) => {
            const isSelected = trainer.id === activeTrainer.id;
            const countForTrainer = items.filter((it) => it.trainerId === trainer.id).length;
            const onLeaveSelectedDay = Boolean(getTrainerLeaveOnDate(trainer.id, selectedDate));

            return (
              <button
                key={trainer.id}
                onClick={() => setSelectedTrainerId(trainer.id)}
                className={`text-left p-3.5 rounded-xl border-2 transition flex items-start justify-between gap-2 cursor-pointer ${
                  isSelected
                    ? 'border-indigo-600 bg-indigo-50/40 shadow-2xs'
                    : 'border-slate-200/80 bg-white hover:border-slate-300'
                }`}
              >
                <div className="flex items-start gap-2.5 min-w-0">
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center font-extrabold text-xs shrink-0 ${trainer.badge}`}
                  >
                    {trainer.initials}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-slate-900 truncate">{trainer.name}</span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
                        {countForTrainer}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 truncate mt-0.5">{trainer.track}</p>
                    {onLeaveSelectedDay && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full mt-1.5">
                        <PlaneTakeoff className="w-3 h-3" /> On Leave ({formatPrettyDate(selectedDate)})
                      </span>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 4 Summary Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl border border-slate-200/90 p-4 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              {timetableMode === 'trainer' ? `SESSIONS · ${activeTrainer.name.toUpperCase()}` : `ALL TRAINERS · ${selectedDate}`}
            </p>
            <p className="text-2xl font-extrabold text-slate-900 mt-1">{daySessionsCount}</p>
            <p className="text-[11px] text-indigo-600 font-semibold mt-0.5">{formatPrettyDate(selectedDate)}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Video className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/90 p-4 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">DAILY TEACHING LOAD</p>
            <p className="text-2xl font-extrabold text-slate-900 mt-1">{dailyHours.toFixed(2)}h</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Scheduled hours for selected day</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/90 p-4 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">SLOTS TICKED OFF</p>
            <p className="text-2xl font-extrabold text-emerald-600 mt-1">{completedCount}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {Math.max(daySessionsCount - completedCount, 0)} pending on {selectedDate}
            </p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/90 p-4 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">TRAINER CYCLE HOURS</p>
            <p className="text-2xl font-extrabold text-slate-900 mt-1">{totalTrainerHours.toFixed(2)}h</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Across {activeTrainer.name}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <CalendarIcon className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Main Split: Left Month Picker + Trainer Leave Tracker | Right Daily Timetable */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column (5 cols): Month Calendar + Trainer Leaves */}
        <div className="lg:col-span-5 space-y-5">
          {/* Month Grid */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-extrabold text-slate-900">{monthLabel}</h2>
                <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700">
                  {activeTrainer.name}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => shiftMonth(-1)}
                  className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 cursor-pointer"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    setViewMonth(new Date(2026, 10, 1));
                    setSelectedDate('2026-11-19');
                  }}
                  className="px-2.5 py-1 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-bold text-slate-700 cursor-pointer"
                >
                  Today
                </button>
                <button
                  onClick={() => shiftMonth(1)}
                  className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 cursor-pointer"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-7 text-center text-[10px] font-bold text-slate-400">
              {['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'].map((d) => (
                <div key={d} className="py-1.5">
                  {d}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-1">
              {monthCells.map((cell) => {
                const isSelected = cell.dateKey === selectedDate;
                const daySlots = items.filter(
                  (it) =>
                    it.date === cell.dateKey &&
                    (timetableMode === 'daywise' || it.trainerId === activeTrainer.id)
                );
                const hasLeave = Boolean(getTrainerLeaveOnDate(activeTrainer.id, cell.dateKey));

                return (
                  <button
                    key={cell.dateKey}
                    onClick={() => setSelectedDate(cell.dateKey)}
                    className={`h-12 rounded-xl border p-1 flex flex-col items-center justify-between transition cursor-pointer ${
                      isSelected
                        ? 'border-indigo-600 bg-indigo-50/70'
                        : cell.inMonth
                        ? 'border-slate-100 hover:border-slate-300 bg-white'
                        : 'border-transparent bg-slate-50/50 text-slate-300'
                    }`}
                  >
                    <span
                      className={`text-xs font-bold w-6 h-6 rounded-full flex items-center justify-center ${
                        isSelected
                          ? 'bg-indigo-600 text-white'
                          : cell.inMonth
                          ? 'text-slate-800'
                          : 'text-slate-400'
                      }`}
                    >
                      {cell.dayNumber}
                    </span>

                    <div className="flex items-center gap-1">
                      {daySlots.length > 0 && (
                        <span className="text-[9px] font-extrabold px-1.5 rounded bg-blue-100 text-blue-700">
                          {daySlots.length}
                        </span>
                      )}
                      {hasLeave && (
                        <span
                          title="Trainer on Leave"
                          className="w-2 h-2 rounded-full bg-amber-500 inline-block"
                        />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Trainer Leave & Auto-Apply Panel */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                  <PlaneTakeoff className="w-4 h-4 text-amber-600" />
                  Trainer Leave Management
                </h3>
                <p className="text-[11px] text-slate-500">
                  Trainers can auto-apply leaves; impacted sessions are flagged for quick reassignment.
                </p>
              </div>
              <button
                onClick={() => {
                  setLeaveForm({
                    trainerId: activeTrainer.id,
                    date: selectedDate,
                    reason: 'Auto-Applied Leave',
                  });
                  setShowLeaveModal(true);
                }}
                className="inline-flex items-center gap-1 text-xs font-bold px-3 py-1.5 rounded-xl bg-amber-100 hover:bg-amber-200 text-amber-900 transition cursor-pointer shrink-0"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Auto-Apply
              </button>
            </div>

            {/* Leave Balance Pills per Trainer */}
            <div className="grid grid-cols-2 gap-2">
              {trainerLeaveStats.map((t) => (
                <div
                  key={t.id}
                  onClick={() => setSelectedTrainerId(t.id)}
                  className="p-2.5 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/70 cursor-pointer"
                >
                  <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                    <span className="truncate">{t.name.split(' ')[0]}</span>
                    <span className="text-[11px] text-indigo-700">
                      {t.remainingLeaves}/{t.leaveQuota} left
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 mt-0.5">{t.usedLeaves} leave(s) used</p>
                </div>
              ))}
            </div>

            {/* Recorded Leaves List */}
            <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
              {leaves.length === 0 ? (
                <p className="text-xs text-slate-400 text-center py-4">No trainer leaves recorded.</p>
              ) : (
                leaves.map((lv) => {
                  const tr = TRAINERS.find((t) => t.id === lv.trainerId);
                  return (
                    <div
                      key={lv.id}
                      className="p-3 rounded-xl border border-amber-200/80 bg-amber-50/40 flex items-start justify-between gap-2"
                    >
                      <div className="text-xs space-y-0.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-slate-900">{tr?.name}</span>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white border border-amber-200 text-amber-800">
                            {formatPrettyDate(lv.date)}
                          </span>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                            {lv.status}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-600">{lv.reason}</p>
                      </div>
                      {isOperations && (
                        <button
                          onClick={() => removeLeave(lv.id)}
                          title="Cancel / Remove Leave"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column (7 cols): Daily Timetable (Trainer-Wise or Day-Wise) */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div>
              <p className="text-[10px] font-extrabold uppercase tracking-wider text-indigo-600">
                {timetableMode === 'trainer' ? 'TRAINER-WISE DAILY TIMETABLE' : 'DAY-WISE ALL TRAINERS TIMETABLE'}
              </p>
              <h2 className="text-base sm:text-lg font-extrabold text-slate-900 mt-0.5">
                {formatPrettyDate(selectedDate)}
              </h2>
              <p className="text-xs text-slate-500">
                {timetableMode === 'trainer'
                  ? `${activeTrainer.name} · ${daySessionsCount} slot(s) (${dailyHours.toFixed(2)}h)`
                  : `All Trainers · ${daySessionsCount} total slot(s) (${dailyHours.toFixed(2)}h)`}
              </p>
            </div>

            <button
              onClick={openNewSlot}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Mock / Class</span>
            </button>
          </div>

          {/* Leave Warning Banner if Selected Trainer is on Leave on Selected Date */}
          {timetableMode === 'trainer' && activeTrainerLeaveToday && (
            <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-300 flex items-start gap-2.5 text-xs text-amber-950">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-bold">
                  {activeTrainer.name} is on Leave on {formatPrettyDate(selectedDate)} ({activeTrainerLeaveToday.status})
                </p>
                <p className="text-[11px] text-amber-800 mt-0.5">
                  Reason: {activeTrainerLeaveToday.reason}. Reassign or edit any scheduled slots below if needed.
                </p>
              </div>
            </div>
          )}

          {/* Timetable Entries */}
          <div className="space-y-3">
            {dailyTimetableItems.length === 0 ? (
              <div className="border border-dashed border-slate-200 rounded-2xl p-8 text-center space-y-2">
                <p className="text-sm font-bold text-slate-700">No sessions or mocks on this date</p>
                <p className="text-xs text-slate-400">
                  Pick another date on the calendar or click &ldquo;Add Mock / Class&rdquo; to schedule a slot.
                </p>
              </div>
            ) : (
              dailyTimetableItems.map((slot) => {
                const slotTrainer = TRAINERS.find((t) => t.id === slot.trainerId);
                const trainerOnLeave = Boolean(getTrainerLeaveOnDate(slot.trainerId, slot.date));

                return (
                  <div
                    key={slot.id}
                    className={`rounded-2xl border p-4 transition space-y-2.5 ${
                      slot.done
                        ? 'bg-slate-50/80 border-slate-200/80 opacity-80'
                        : 'bg-white border-slate-200 hover:border-indigo-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-2.5 min-w-0">
                        <button
                          onClick={() => toggleSlotDone(slot.id)}
                          aria-label="Toggle completed"
                          className={`mt-0.5 w-5 h-5 rounded-md border flex items-center justify-center shrink-0 cursor-pointer ${
                            slot.done
                              ? 'bg-emerald-600 border-emerald-600 text-white'
                              : 'border-slate-300 bg-white hover:border-indigo-500'
                          }`}
                        >
                          {slot.done && <Check className="w-3.5 h-3.5" />}
                        </button>

                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-bold text-slate-900">
                              {slot.studentOrBatch}
                            </span>
                            <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">
                              {slot.type}
                            </span>
                            {timetableMode === 'daywise' && slotTrainer && (
                              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
                                {slotTrainer.name}
                              </span>
                            )}
                            {trainerOnLeave && (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-700">
                                Trainer on Leave
                              </span>
                            )}
                          </div>

                          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1.5">
                            <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span>{slot.timeSlot}</span>
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <button
                          onClick={() => openEditSlot(slot)}
                          title="Edit Slot"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 cursor-pointer"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => deleteSlot(slot.id)}
                          title="Delete Slot"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="rounded-xl bg-slate-50 border border-slate-100 p-3 space-y-1">
                      <p className="text-[10px] font-extrabold uppercase tracking-wider text-indigo-600 flex items-center gap-1">
                        <BookOpen className="w-3 h-3" /> Topic / Agenda
                      </p>
                      <p className="text-xs font-bold text-slate-800">{slot.topic}</p>
                      {slot.notes && <p className="text-[11px] text-slate-500">{slot.notes}</p>}
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <button
                        onClick={() => toggleSlotDone(slot.id)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                          slot.done
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                        }`}
                      >
                        {slot.done ? 'Ticked Off' : 'Tick Off Slot'}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Add / Edit Mock or Class Slot Modal */}
      {showSlotModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <form
            onSubmit={handleSaveSlot}
            className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">
                {editingSlotId ? 'Edit Timetable Slot' : 'Add Mock / Class Slot'}
              </h3>
              <button
                type="button"
                onClick={() => setShowSlotModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Trainer</label>
                  <select
                    value={slotForm.trainerId}
                    onChange={(e) => setSlotForm({ ...slotForm, trainerId: e.target.value })}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2 bg-white"
                  >
                    {TRAINERS.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Date</label>
                  <input
                    type="date"
                    required
                    value={slotForm.date}
                    onChange={(e) => setSlotForm({ ...slotForm, date: e.target.value })}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Session Type</label>
                  <select
                    value={slotForm.type}
                    onChange={(e) => setSlotForm({ ...slotForm, type: e.target.value })}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2 bg-white"
                  >
                    <option value="Technical Mock">Technical Mock</option>
                    <option value="HR Mock">HR Mock</option>
                    <option value="Class Session">Class Session</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Hours</label>
                  <input
                    type="number"
                    step="0.25"
                    min="0.25"
                    max="8"
                    value={slotForm.hours}
                    onChange={(e) => setSlotForm({ ...slotForm, hours: e.target.value })}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Student / Batch</label>
                  <input
                    type="text"
                    value={slotForm.studentOrBatch}
                    onChange={(e) => setSlotForm({ ...slotForm, studentOrBatch: e.target.value })}
                    placeholder="e.g., Batch FinXL-04 or Aarav"
                    className="w-full border border-slate-300 rounded-xl px-3 py-2"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Time Slot</label>
                  <input
                    type="text"
                    value={slotForm.timeSlot}
                    onChange={(e) => setSlotForm({ ...slotForm, timeSlot: e.target.value })}
                    placeholder="10:00 – 10:45 (45 mins)"
                    className="w-full border border-slate-300 rounded-xl px-3 py-2"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Topic to Cover</label>
                <input
                  type="text"
                  required
                  value={slotForm.topic}
                  onChange={(e) => setSlotForm({ ...slotForm, topic: e.target.value })}
                  placeholder="e.g., System Design, React Hooks, SQL"
                  className="w-full border border-slate-300 rounded-xl px-3 py-2"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Focus / Notes</label>
                <textarea
                  rows={2}
                  value={slotForm.notes}
                  onChange={(e) => setSlotForm({ ...slotForm, notes: e.target.value })}
                  placeholder="Key points or evaluation notes..."
                  className="w-full border border-slate-300 rounded-xl px-3 py-2"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowSlotModal(false)}
                className="px-4 py-2 text-xs font-bold text-slate-600 bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl cursor-pointer"
              >
                {editingSlotId ? 'Save Changes' : 'Add to Timetable'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Trainer Auto-Apply Leave Modal */}
      {showLeaveModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <form
            onSubmit={handleAutoApplyLeave}
            className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PlaneTakeoff className="w-4 h-4 text-amber-600" />
                <h3 className="text-base font-bold text-slate-900">Trainer Auto-Apply Leave</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowLeaveModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-500">
              Automatically logs the leave against the trainer&apos;s quota and flags any mocks or classes on that date.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Trainer</label>
                <select
                  value={leaveForm.trainerId}
                  onChange={(e) => setLeaveForm({ ...leaveForm, trainerId: e.target.value })}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2 bg-white"
                >
                  {TRAINERS.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.track})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Leave Date</label>
                <input
                  type="date"
                  required
                  value={leaveForm.date}
                  onChange={(e) => setLeaveForm({ ...leaveForm, date: e.target.value })}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Reason</label>
                <input
                  type="text"
                  required
                  value={leaveForm.reason}
                  onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })}
                  placeholder="e.g., Personal leave, medical, travel"
                  className="w-full border border-slate-300 rounded-xl px-3 py-2"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowLeaveModal(false)}
                className="px-4 py-2 text-xs font-bold text-slate-600 bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 rounded-xl cursor-pointer"
              >
                Auto-Apply Leave
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}