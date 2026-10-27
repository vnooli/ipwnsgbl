import { KpiTone } from "../types/enums";

interface KpiCardProps {
  label: string;
  value: string;
  unit?: string;
  sampleCount?: number;
  tooltip?: string;
  tone?: KpiTone;
}

const toneClasses: Record<KpiTone, string> = {
  [KpiTone.Neutral]: "border-slate-700/80 hover:border-slate-600",
  [KpiTone.Good]: "border-emerald-600/60 hover:border-emerald-500",
  [KpiTone.Warn]: "border-amber-600/60 hover:border-amber-500",
};

const toneAccent: Record<KpiTone, string> = {
  [KpiTone.Neutral]: "bg-slate-500",
  [KpiTone.Good]: "bg-emerald-500",
  [KpiTone.Warn]: "bg-amber-500",
};

export function KpiCard({ label, value, unit, sampleCount, tooltip, tone = KpiTone.Neutral }: KpiCardProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-panel border ${toneClasses[tone]} p-4 pl-5 flex flex-col gap-1.5 min-w-[168px] flex-1 shadow-sm shadow-black/20 transition-colors cursor-default`}
      title={tooltip}
    >
      <span className={`absolute left-0 top-0 h-full w-1 ${toneAccent[tone]}`} aria-hidden="true" />
      <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{label}</span>
      <span className="text-[28px] leading-tight font-semibold text-slate-50 tabular-nums">
        {value}
        {unit && <span className="text-sm font-normal text-slate-400 ml-1">{unit}</span>}
      </span>
      {sampleCount !== undefined && (
        <span className="text-xs text-slate-500">n = {sampleCount} periods</span>
      )}
    </div>
  );
}
