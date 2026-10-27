import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AlignedPeriod } from "../types/domain";

interface ErrorChartProps {
  periods: AlignedPeriod[];
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function ErrorChart({ periods }: ErrorChartProps) {
  const data = periods
    .filter((p) => p.forecastErrorMw !== null)
    .map((p) => ({ time: formatTime(p.startTime), "Forecast error (MW)": p.forecastErrorMw }));

  return (
    <div className="bg-panel border border-slate-700 rounded-xl p-4">
      <h3 className="text-sm font-medium text-slate-200 mb-1">Forecast error over time (forecast − actual, MW)</h3>
      <p className="text-xs text-slate-500 mb-3">
        Positive = forecast over-stated wind generation. Negative = forecast under-stated it.
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2a3d" />
          <XAxis dataKey="time" stroke="#8aa0bd" fontSize={11} minTickGap={30} />
          <YAxis stroke="#8aa0bd" fontSize={11} label={{ value: "MW", angle: -90, position: "insideLeft", fill: "#8aa0bd" }} />
          <Tooltip contentStyle={{ backgroundColor: "#111a2c", border: "1px solid #334155" }} />
          <Bar dataKey="Forecast error (MW)" fill="#f59e0b" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
