import React from 'react';

// Shared building blocks so every section has the same widths, spacing and card style.

// Every page sits in this: one max width, one rhythm, centred
export const Page = ({ children }) => <div className="space-y-5 sm:space-y-6 max-w-[1600px] mx-auto pb-10 animate-fadeIn">{children}</div>;

// The white banner at the top of a page: title, one line of context, and one main button
export function PageHeader({ title, subtitle, icon: Icon, action, children }) {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/80 backdrop-blur-md p-5 sm:p-6 rounded-3xl border border-slate-200/80 shadow-sm">
      <div className="min-w-0">
        <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
          {Icon && <span className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center shrink-0"><Icon className="w-4 h-4" /></span>}
          <span className="truncate">{title}</span>
        </h1>
        {subtitle && <p className="text-xs font-medium text-slate-500 mt-1.5">{subtitle}</p>}
        {children}
      </div>
      {action}
    </div>
  );
}

export const PrimaryButton = ({ icon: Icon, children, className = '', ...props }) => (
  <button
    {...props}
    className={`flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 via-indigo-600 to-sky-500 hover:brightness-105 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-md shadow-blue-500/20 transition active:scale-95 shrink-0 disabled:opacity-60 ${className}`}
  >
    {Icon && <Icon className="w-4 h-4" />}<span>{children}</span>
  </button>
);

export function Card({ title, icon: Icon, action, children, className = '' }) {
  return (
    <section className={`bg-white p-5 sm:p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-4 min-w-0 ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xs font-bold text-slate-800 tracking-wide flex items-center gap-2">
            {Icon && <Icon className="w-4 h-4 text-indigo-500" />}{title}
          </h2>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

const TONES = {
  blue: ['bg-blue-50 text-blue-600', 'from-blue-500 to-indigo-600'],
  indigo: ['bg-indigo-50 text-indigo-600', 'from-indigo-500 to-purple-600'],
  sky: ['bg-sky-50 text-sky-600', 'from-sky-400 to-blue-500'],
  emerald: ['bg-emerald-50 text-emerald-600', 'from-emerald-500 to-teal-600'],
  orange: ['bg-orange-50 text-orange-600', 'from-orange-500 to-amber-500'],
  amber: ['bg-amber-50 text-amber-600', 'from-amber-400 to-orange-500'],
  violet: ['bg-violet-50 text-violet-600', 'from-violet-500 to-purple-600'],
  rose: ['bg-rose-50 text-rose-600', 'from-rose-500 to-pink-600'],
};

// KPI row. 2 columns on a phone, 3 on a tablet, up to 6 on a wide screen.
export function KpiGrid({ children, count = 6 }) {
  const wide = count >= 6 ? 'xl:grid-cols-6' : count === 5 ? 'xl:grid-cols-5' : 'xl:grid-cols-4';
  return <div className={`grid grid-cols-2 sm:grid-cols-3 ${wide} gap-3 sm:gap-3.5`}>{children}</div>;
}

export function Kpi({ label, value, icon: Icon, tone = 'blue', hint, onClick }) {
  const [chip, bar] = TONES[tone] || TONES.blue;
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag
      onClick={onClick}
      className={`group text-left bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 relative overflow-hidden flex flex-col justify-between min-h-[104px] min-w-0 ${onClick ? 'cursor-pointer' : ''}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-[10px] text-slate-400 font-extrabold uppercase tracking-wider leading-snug">{label}</span>
        <span className={`p-2 rounded-xl shrink-0 group-hover:scale-110 transition-transform ${chip}`}><Icon size={16} /></span>
      </div>
      <div>
        <span className="text-2xl font-black text-slate-900 tracking-tight tabular-nums block truncate">{value}</span>
        <span className="text-[11px] text-slate-400 font-medium block truncate min-h-[1rem]">{hint}</span>
      </div>
      <div className={`h-1 w-full bg-gradient-to-r ${bar} absolute bottom-0 left-0 opacity-0 group-hover:opacity-100 transition-opacity`} />
    </Tag>
  );
}

// One labelled bar: used for funnels, progress and "by status" breakdowns
export function BarRow({ label, value, shown, pct, tone = 'blue' }) {
  const [, bar] = TONES[tone] || TONES.blue;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-3 text-[11px]">
        <span className="font-semibold text-slate-600 truncate">{label}</span>
        <span className="font-bold text-slate-800 tabular-nums shrink-0">{shown ?? value}</span>
      </div>
      <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden p-0.5" role="img" aria-label={`${label}: ${shown ?? value}`}>
        <div className={`h-full rounded-full bg-gradient-to-r ${bar} transition-all duration-500`} style={{ width: `${Math.max(0, Math.min(100, pct))}%`, minWidth: pct > 0 ? '6px' : 0 }} />
      </div>
    </div>
  );
}

export const Empty = ({ children }) => <p className="text-xs text-slate-400 py-3 text-center">{children}</p>;

export function Initials({ name = '?', className = 'w-8 h-8' }) {
  return (
    <span className={`${className} rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 text-white flex items-center justify-center font-bold text-[10px] shrink-0`} aria-hidden="true">
      {name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('')}
    </span>
  );
}

export function Pill({ children, className = '' }) {
  return <span className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border whitespace-nowrap ${className}`}>{children}</span>;
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-5 sm:space-y-6 max-w-[1600px] mx-auto" aria-busy="true" aria-label="Loading">
      <div className="h-24 bg-white rounded-3xl border border-slate-200/80 animate-pulse" />
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
        {Array.from({ length: 6 }, (_, i) => <div key={i} className="bg-white rounded-2xl border border-slate-200/80 h-[104px] animate-pulse" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 sm:gap-6">
        {Array.from({ length: 4 }, (_, i) => <div key={i} className="bg-white rounded-3xl border border-slate-200/80 h-52 animate-pulse" />)}
      </div>
    </div>
  );
}
