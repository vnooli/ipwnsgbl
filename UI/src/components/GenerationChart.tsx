import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AlignedPeriod } from "../types/domain";

interface GenerationChartProps {
  periods: AlignedPeriod[];
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function GenerationChart({ periods }: GenerationChartProps) {
  const data = periods.map((p) => ({
    time: formatTime(p.startTime),
    "Actual (MW)": p.actualGenerationMw,
    "Decision-time forecast (MW)": p.decisionForecastMw,
  }));

  return (
    <div className="bg-panel border border-slate-700 rounded-xl p-4">
      <h3 className="text-sm font-medium text-slate-200 mb-3">
        Wind generation: actual vs. decision-time forecast (MW)
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2a3d" />
          <XAxis dataKey="time" stroke="#8aa0bd" fontSize={11} minTickGap={30} />
          <YAxis stroke="#8aa0bd" fontSize={11} label={{ value: "MW", angle: -90, position: "insideLeft", fill: "#8aa0bd" }} />
          <Tooltip contentStyle={{ backgroundColor: "#111a2c", border: "1px solid #334155" }} />
          <Legend />
          <Line type="monotone" dataKey="Actual (MW)" stroke="#2dd4bf" dot={false} strokeWidth={2} connectNulls />
          <Line
            type="monotone"
            dataKey="Decision-time forecast (MW)"
            stroke="#f59e0b"
            dot={false}
            strokeWidth={2}
            strokeDasharray="5 3"
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
