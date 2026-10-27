import { useState } from "react";
import { DateRangeFilter } from "./components/DateRangeFilter";
import { ErrorChart } from "./components/ErrorChart";
import { ForecastTable } from "./components/ForecastTable";
import { GenerationChart } from "./components/GenerationChart";
import { KpiCard } from "./components/KpiCard";
import { StatusBanner } from "./components/StatusBanner";
import { useProcurementData } from "./hooks/useProcurementData";
import { BannerKind, FetchState, KpiTone } from "./types/enums";

function fmtMetric(n: number | null, digits = 1): string {
  return n === null ? "n/a" : n.toFixed(digits);
}

export default function App() {
  const [start, setStart] = useState("2026-01-01");
  const [end, setEnd] = useState("2026-01-07");
  const { state, error, errorKind, series, accuracy } = useProcurementData(start, end);

  const coverage =
    accuracy && accuracy.metrics.totalPeriods > 0
      ? Math.round((accuracy.metrics.sampleCountMaeRmseBias / accuracy.metrics.totalPeriods) * 100)
      : null;

  return (
    <div className="min-h-screen bg-ink bg-[radial-gradient(circle_at_top,_rgba(45,212,191,0.08),_transparent_55%)]">
      <header className="border-b border-slate-800/80 px-6 py-6 sticky top-0 z-10 bg-ink/90 backdrop-blur">
        <div className="max-w-6xl mx-auto flex items-start gap-3">
          <span className="text-2xl mt-0.5" aria-hidden="true">🌬️</span>
          <div>
            <h1 className="text-xl font-semibold text-slate-50 tracking-tight">
              UK Wind Forecast &amp; Day-Ahead Procurement Analytics
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              National wind generation forecast accuracy for January 2026 day-ahead purchasing decisions. Source:
              Elexon FUELHH (actuals) &amp; WINDFOR (forecasts).
            </p>
          </div>
        </div>
      </header>

      <main className="px-6 py-6 flex flex-col gap-6 max-w-6xl mx-auto">
        <DateRangeFilter start={start} end={end} onChange={(s, e) => { setStart(s); setEnd(e); }} />

        {state === FetchState.Loading && <StatusBanner kind={BannerKind.Loading} />}
        {state === FetchState.Error && (
          <StatusBanner kind={BannerKind.Error} message={error ?? undefined} errorKind={errorKind} />
        )}
        {state === FetchState.Empty && <StatusBanner kind={BannerKind.Empty} />}

        {state === FetchState.Success && series && accuracy && (
          <>
            <section className="flex flex-wrap gap-4">
              <KpiCard
                label="MAE"
                value={fmtMetric(accuracy.metrics.maeMw)}
                unit="MW"
                sampleCount={accuracy.metrics.sampleCountMaeRmseBias}
                tooltip="Mean Absolute Error between decision-time forecast and actual generation"
              />
              <KpiCard
                label="RMSE"
                value={fmtMetric(accuracy.metrics.rmseMw)}
                unit="MW"
                sampleCount={accuracy.metrics.sampleCountMaeRmseBias}
                tooltip="Root Mean Squared Error - penalises large errors more heavily than MAE"
              />
              <KpiCard
                label="Bias"
                value={fmtMetric(accuracy.metrics.biasMw)}
                unit="MW"
                sampleCount={accuracy.metrics.sampleCountMaeRmseBias}
                tone={
                  accuracy.metrics.biasMw === null
                    ? KpiTone.Neutral
                    : accuracy.metrics.biasMw > 0
                    ? KpiTone.Warn
                    : KpiTone.Good
                }
                tooltip="Mean signed error (forecast - actual). Positive = forecast over-predicts wind."
              />
              <KpiCard
                label="MAPE"
                value={accuracy.metrics.mapePercent === null ? "n/a" : accuracy.metrics.mapePercent.toFixed(1)}
                unit="%"
                sampleCount={accuracy.metrics.sampleCountMape}
                tooltip="Mean Absolute Percentage Error, computed only over periods with nonzero actual generation"
              />
              <KpiCard
                label="Data coverage"
                value={coverage === null ? "n/a" : `${coverage}%`}
                sampleCount={accuracy.metrics.totalPeriods}
                tooltip="Share of delivery periods with both an actual and a decision-time forecast available"
              />
            </section>

            <section className="rounded-2xl border border-accent/30 bg-gradient-to-br from-panel to-panel/60 p-4 text-sm text-slate-300 flex gap-3">
              <span className="text-lg" aria-hidden="true">💡</span>
              <div>
                <p className="mb-2 text-slate-200">{accuracy.procurementInterpretation.summary}</p>
                <p className="text-xs text-slate-500">{accuracy.procurementInterpretation.disclaimer}</p>
              </div>
            </section>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <GenerationChart periods={series.results} />
              <ErrorChart periods={series.results} />
            </div>

            <section>
              <div className="flex items-baseline justify-between mb-3">
                <h2 className="text-sm font-medium text-slate-200">Forecast explorer</h2>
                <span className="text-xs text-slate-500">{series.results.length} delivery periods</span>
              </div>
              <ForecastTable periods={series.results} />
            </section>
          </>
        )}

        <footer className="text-xs text-slate-600 pt-4 pb-8 border-t border-slate-800/60 mt-2">
          Decision cutoff: the latest forecast published on or before 11:00 Europe/London on the day
          before delivery is used for decision-time accuracy. This is a documented assumption, not an
          official market rule — see README.
        </footer>
      </main>
    </div>
  );
}
