import { useEffect, useRef, useState } from "react";

interface DatePickerProps {
  label: string;
  value: string; // YYYY-MM-DD
  min: string;
  max: string;
  onChange: (value: string) => void;
}

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const MONTH_LABEL = "January 2026";

function toDate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

function fmtDisplay(iso: string): string {
  return toDate(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

function daysInGrid(min: string, max: string): (number | null)[] {
  const first = toDate(min);
  const firstWeekday = first.getUTCDay();
  const totalDays = toDate(max).getUTCDate();
  const cells: (number | null)[] = Array(firstWeekday).fill(null);
  for (let d = 1; d <= totalDays; d++) cells.push(d);
  return cells;
}

export function DatePicker({ label, value, min, max, onChange }: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const selectedDay = toDate(value).getUTCDate();
  const grid = daysInGrid(min, max);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  function selectDay(day: number) {
    const iso = `2026-01-${String(day).padStart(2, "0")}`;
    onChange(iso);
    setOpen(false);
  }

  return (
    <div className="flex flex-col gap-1.5 relative" ref={containerRef}>
      <label className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{label}</label>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="flex items-center gap-2 bg-ink border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-slate-100 outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/30 hover:border-slate-500 min-w-[140px]"
      >
        <svg className="w-3.5 h-3.5 text-accent shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        {fmtDisplay(value)}
      </button>

      {open && (
        <div
          role="dialog"
          className="absolute z-20 top-full mt-2 left-0 bg-panel border border-slate-700 rounded-xl shadow-xl shadow-black/40 p-3 w-[260px]"
        >
          <div className="text-center text-sm font-medium text-slate-200 mb-2">{MONTH_LABEL}</div>
          <div className="grid grid-cols-7 gap-1 text-center text-[11px] text-slate-500 mb-1">
            {WEEKDAYS.map((w) => (
              <span key={w}>{w}</span>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {grid.map((day, i) => {
              if (day === null) return <span key={`empty-${i}`} />;
              const isSelected = day === selectedDay;
              return (
                <button
                  key={day}
                  type="button"
                  onClick={() => selectDay(day)}
                  className={`h-7 w-7 rounded-md text-xs transition-colors ${
                    isSelected
                      ? "bg-accent text-ink font-semibold"
                      : "text-slate-300 hover:bg-slate-700 hover:text-accent"
                  }`}
                >
                  {day}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
