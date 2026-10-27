import type { AlignedPeriod } from "../types/domain";

interface ForecastTableProps {
  periods: AlignedPeriod[];
}

function fmt(n: number | null, digits = 1): string {
  return n === null ? "—" : n.toFixed(digits);
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ForecastTable({ periods }: ForecastTableProps) {
  return (
    <div className="bg-panel border border-slate-700/80 rounded-2xl overflow-hidden shadow-sm shadow-black/20">
      <div className="overflow-x-auto max-h-[480px]">
        <table className="w-full text-sm text-left border-collapse">
          <thead className="bg-ink/90 text-slate-400 text-[11px] font-medium uppercase tracking-wider sticky top-0 backdrop-blur">
            <tr>
              <th className="px-3 py-2.5">Delivery period</th>
              <th className="px-3 py-2.5">Actual (MW)</th>
              <th className="px-3 py-2.5">Decision forecast (MW)</th>
              <th className="px-3 py-2.5">Forecast published</th>
              <th className="px-3 py-2.5">Signed error (MW)</th>
              <th className="px-3 py-2.5">Abs. error (MW)</th>
              <th className="px-3 py-2.5">Data quality</th>
            </tr>
          </thead>
          <tbody>
            {periods.map((p) => {
              const complete = p.hasActual && p.hasDecisionForecast;
              return (
                <tr key={p.startTime} className="border-t border-slate-800 hover:bg-slate-800/40">
                  <td className="px-3 py-2 text-slate-200">{fmtTime(p.startTime)}</td>
                  <td className="px-3 py-2">{fmt(p.actualGenerationMw)}</td>
                  <td className="px-3 py-2">{fmt(p.decisionForecastMw)}</td>
                  <td className="px-3 py-2 text-slate-400">{fmtTime(p.decisionForecastPublishTime)}</td>
                  <td
                    className={`px-3 py-2 ${
                      p.forecastErrorMw === null
                        ? "text-slate-500"
                        : p.forecastErrorMw > 0
                        ? "text-amber-400"
                        : "text-sky-400"
                    }`}
                  >
                    {fmt(p.forecastErrorMw)}
                  </td>
                  <td className="px-3 py-2">{fmt(p.absoluteErrorMw)}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        complete
                          ? "bg-emerald-900/50 text-emerald-300"
                          : "bg-amber-900/50 text-amber-300"
                      }`}
                    >
                      {complete ? "Complete" : !p.hasActual && !p.hasDecisionForecast ? "No data" : "Partial"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
