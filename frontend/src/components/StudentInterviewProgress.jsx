
import React, { useState } from 'react';
import {
  Users, CheckCircle, Clock, TrendingUp,
  Search, Filter, Eye
} from 'lucide-react';

const students = [
  {
    id: 1,
    name: 'Aarav Sharma',
    email: 'aarav@gmail.com',
    batch: 'Batch 2026',
    completed: 4,
    total: 5,
    score: 85,
    status: 'In Progress'
  },
  {
    id: 2,
    name: 'Priya Patel',
    email: 'priya@gmail.com',
    batch: 'Batch 2026',
    completed: 5,
    total: 5,
    score: 92,
    status: 'Completed'
  },
  {
    id: 3,
    name: 'Rahul Verma',
    email: 'rahul@gmail.com',
    batch: 'Batch 2025',
    completed: 2,
    total: 5,
    score: 68,
    status: 'In Progress'
  },
  {
    id: 4,
    name: 'Sneha Gupta',
    email: 'sneha@gmail.com',
    batch: 'Batch 2025',
    completed: 0,
    total: 5,
    score: 0,
    status: 'Not Started'
  }
];

export default function StudentInterviewProgress() {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('All');

  const filteredStudents = students.filter(student => {
    const matchesSearch =
      student.name.toLowerCase().includes(search.toLowerCase()) ||
      student.batch.toLowerCase().includes(search.toLowerCase());

    const matchesFilter =
      filter === 'All' || student.status === filter;

    return matchesSearch && matchesFilter;
  });

  const completedCount = students.filter(
    s => s.status === 'Completed'
  ).length;

  const inProgressCount = students.filter(
    s => s.status === 'In Progress'
  ).length;

  const notStartedCount = students.filter(
    s => s.status === 'Not Started'
  ).length;

  const averageScore = Math.round(
    students.reduce((sum, s) => sum + s.score, 0) / students.length
  );

  const stats = [
    {
      title: 'Total Students',
      value: students.length,
      icon: Users,
      color: 'blue'
    },
    {
      title: 'Completed',
      value: completedCount,
      icon: CheckCircle,
      color: 'green'
    },
    {
      title: 'In Progress',
      value: inProgressCount,
      icon: Clock,
      color: 'amber'
    },
    {
      title: 'Average Score',
      value: `${averageScore}%`,
      icon: TrendingUp,
      color: 'purple'
    }
  ];

  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    amber: 'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600'
  };

  return (
    <div className="space-y-6">

      {/* Dashboard Heading */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">
          Student Interview Progress
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Monitor interview completion, performance and student readiness.
        </p>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <div
              key={stat.title}
              className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">
                    {stat.title}
                  </p>
                  <h2 className="text-2xl font-bold text-slate-800 mt-2">
                    {stat.value}
                  </h2>
                </div>

                <div className={`p-3 rounded-xl ${colors[stat.color]}`}>
                  <Icon size={22} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Progress Overview */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h2 className="font-bold text-slate-800 mb-4">
          Overall Interview Status
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-green-50 rounded-xl p-4">
            <p className="text-sm text-green-700">Completed</p>
            <h3 className="text-2xl font-bold text-green-700">
              {completedCount}
            </h3>
          </div>

          <div className="bg-amber-50 rounded-xl p-4">
            <p className="text-sm text-amber-700">In Progress</p>
            <h3 className="text-2xl font-bold text-amber-700">
              {inProgressCount}
            </h3>
          </div>

          <div className="bg-slate-100 rounded-xl p-4">
            <p className="text-sm text-slate-600">Not Started</p>
            <h3 className="text-2xl font-bold text-slate-700">
              {notStartedCount}
            </h3>
          </div>
        </div>
      </div>

      {/* Student Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">

        <div className="p-5 border-b border-slate-100">
          <h2 className="font-bold text-slate-800 text-lg">
            Student-wise Progress
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Track individual student interview performance.
          </p>

          <div className="flex flex-col md:flex-row gap-3 mt-5">
            <div className="relative flex-1">
              <Search
                size={18}
                className="absolute left-3 top-3 text-slate-400"
              />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search student or batch..."
                className="w-full border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-100"
              />
            </div>

            <div className="relative">
              <Filter
                size={16}
                className="absolute left-3 top-3 text-slate-400"
              />
              <select
                value={filter}
                onChange={e => setFilter(e.target.value)}
                className="border border-slate-200 rounded-xl pl-9 pr-4 py-2.5 text-sm outline-none bg-white w-full"
              >
                <option value="All">All Students</option>
                <option value="Completed">Completed</option>
                <option value="In Progress">In Progress</option>
                <option value="Not Started">Not Started</option>
              </select>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
              <tr>
                <th className="px-5 py-4">Student</th>
                <th className="px-5 py-4">Batch</th>
                <th className="px-5 py-4">Interview Progress</th>
                <th className="px-5 py-4">Score</th>
                <th className="px-5 py-4">Status</th>
                <th className="px-5 py-4">Action</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100">
              {filteredStudents.map(student => {
                const percentage = Math.round(
                  (student.completed / student.total) * 100
                );

                return (
                  <tr key={student.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <p className="font-semibold text-sm text-slate-800">
                        {student.name}
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        {student.email}
                      </p>
                    </td>

                    <td className="px-5 py-4 text-sm text-slate-600">
                      {student.batch}
                    </td>

                    <td className="px-5 py-4 min-w-48">
                      <div className="flex justify-between text-xs mb-2">
                        <span className="text-slate-600">
                          {student.completed}/{student.total} Interviews
                        </span>
                        <span className="font-semibold text-slate-700">
                          {percentage}%
                        </span>
                      </div>

                      <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-600 rounded-full"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </td>

                    <td className="px-5 py-4 text-sm font-semibold text-slate-700">
                      {student.score ? `${student.score}%` : '—'}
                    </td>

                    <td className="px-5 py-4">
                      <span className={`text-xs font-semibold px-3 py-1.5 rounded-full ${
                        student.status === 'Completed'
                          ? 'bg-green-50 text-green-700'
                          : student.status === 'In Progress'
                          ? 'bg-amber-50 text-amber-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}>
                        {student.status}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      <button
                        title="View student"
                        onClick={() =>
                          alert(`Student: ${student.name}\nInterview Progress: ${percentage}%`)
                        }
                        className="p-2 rounded-lg text-blue-600 hover:bg-blue-50"
                      >
                        <Eye size={18} />
                      </button>
                    </td>
                  </tr>
                );
              })}

              {filteredStudents.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center py-8 text-slate-500 text-sm">
                    No students found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
