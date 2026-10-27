import { useEffect, useState } from "react";
import { ApiError, fetchAccuracyMetrics, fetchWindSeries } from "../api/client";
import { ErrorKind, FetchState } from "../types/enums";
import type { AccuracyResponse, WindSeriesResponse } from "../types/domain";

interface ProcurementData {
  state: FetchState;
  error: string | null;
  errorKind: ErrorKind;
  series: WindSeriesResponse | null;
  accuracy: AccuracyResponse | null;
}

function classifyError(err: unknown): ErrorKind {
  if (err instanceof ApiError) {
    if (err.status === 400) return ErrorKind.Validation;
    if (err.status === 0 || err.status === 503) return ErrorKind.Connection;
  }
  return ErrorKind.Unknown;
}

export function useProcurementData(start: string, end: string): ProcurementData {
  const [state, setState] = useState<FetchState>(FetchState.Idle);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ErrorKind>(ErrorKind.Unknown);
  const [series, setSeries] = useState<WindSeriesResponse | null>(null);
  const [accuracy, setAccuracy] = useState<AccuracyResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState(FetchState.Loading);
    setError(null);

    Promise.all([fetchWindSeries(start, end), fetchAccuracyMetrics(start, end)])
      .then(([seriesResult, accuracyResult]) => {
        if (cancelled) return;
        setSeries(seriesResult);
        setAccuracy(accuracyResult);
        setState(seriesResult.results.length === 0 ? FetchState.Empty : FetchState.Success);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
        setErrorKind(classifyError(err));
        setState(FetchState.Error);
      });

    return () => {
      cancelled = true;
    };
  }, [start, end]);

  return { state, error, errorKind, series, accuracy };
}
