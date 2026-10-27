import { DatePicker } from "./DatePicker";

interface DateRangeFilterProps {
  start: string;
  end: string;
  onChange: (start: string, end: string) => void;
}

const MIN_DATE = "2026-01-01";
const MAX_DATE = "2026-01-31";

const PRESETS = [
  { label: "1 Jan", s: "2026-01-01", e: "2026-01-01" },
  { label: "Week 1", s: "2026-01-01", e: "2026-01-07" },
  { label: "Full month", s: "2026-01-01", e: "2026-01-31" },
];

export function DateRangeFilter({ start, end, onChange }: DateRangeFilterProps) {
  const activePreset = PRESETS.find((p) => p.s === start && p.e === end)?.label;

  return (
    <div className="relative z-30 flex flex-wrap items-end justify-between gap-4 bg-panel/80 backdrop-blur border border-slate-700/80 rounded-2xl p-4 shadow-sm shadow-black/20">
      <div className="flex flex-wrap items-end gap-4">
        <DatePicker
          label="Delivery date from"
          value={start}
          min={MIN_DATE}
          max={MAX_DATE}
          onChange={(value) => onChange(value, end)}
        />
        <DatePicker
          label="Delivery date to"
          value={end}
          min={MIN_DATE}
          max={MAX_DATE}
          onChange={(value) => onChange(start, value)}
        />
      </div>

      <div className="flex items-center gap-1.5 bg-ink/60 rounded-xl p-1 border border-slate-800">
        {PRESETS.map((preset) => {
          const active = activePreset === preset.label;
          return (
            <button
              key={preset.label}
              onClick={() => onChange(preset.s, preset.e)}
              aria-pressed={active}
              className={`text-xs font-medium px-3 py-1.5 rounded-lg transition-all ${
                active
                  ? "bg-accent text-ink shadow-sm"
                  : "text-slate-300 hover:bg-slate-800 hover:text-accent"
              }`}
            >
              {preset.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
