import { BannerKind, ErrorKind } from "../types/enums";

interface StatusBannerProps {
  kind: BannerKind;
  message?: string;
  errorKind?: ErrorKind;
}

const ERROR_COPY: Record<ErrorKind, { icon: string; title: string }> = {
  [ErrorKind.Validation]: { icon: "📅", title: "Please check your date selection" },
  [ErrorKind.Connection]: { icon: "🔌", title: "Can't reach the server right now" },
  [ErrorKind.Unknown]: { icon: "⚠️", title: "Something went wrong" },
};

export function StatusBanner({ kind, message, errorKind = ErrorKind.Unknown }: StatusBannerProps) {
  if (kind === BannerKind.Loading) {
    return (
      <div className="rounded-2xl border border-slate-700/80 bg-panel p-10 flex flex-col items-center gap-3 text-slate-400">
        <span className="h-8 w-8 rounded-full border-2 border-slate-600 border-t-accent animate-spin" aria-hidden="true" />
        <span className="text-sm">Loading wind forecast and actual generation data…</span>
      </div>
    );
  }
  if (kind === BannerKind.Empty) {
    return (
      <div className="rounded-2xl border border-amber-700/60 bg-amber-950/20 p-10 flex flex-col items-center gap-2 text-center">
        <span className="text-2xl" aria-hidden="true">🌬️</span>
        <p className="font-medium text-amber-300">No delivery periods found for the selected date range.</p>
        <p className="text-sm text-amber-500/80">Try widening the date range or picking a different preset.</p>
      </div>
    );
  }
  const { icon, title } = ERROR_COPY[errorKind];
  return (
    <div className="rounded-2xl border border-red-700/60 bg-red-950/20 p-10 flex flex-col items-center gap-2 text-center">
      <span className="text-2xl" aria-hidden="true">{icon}</span>
      <p className="font-medium text-red-300">{title}</p>
      <p className="text-sm text-red-400/90">{message}</p>
    </div>
  );
}
