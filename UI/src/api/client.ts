import type { AccuracyResponse, DataStatus, WindSeriesResponse } from "../types/domain";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function getJson<T>(path: string, params: Record<string, string>): Promise<T> {
  const query = new URLSearchParams(params).toString();
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}?${query}`);
  } catch {
    // The browser's own network error (e.g. "Failed to fetch") isn't
    // meaningful to an end user and gives no next step - translate it into
    // something actionable instead.
    throw new ApiError(
      0,
      "We couldn't reach the API. Check that it's running and reachable, then try again."
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    // `message` (set by the API's exception handler) is written to be
    // user-facing; `detail` can carry technical internals (upstream URLs,
    // exception text) that are useful in logs but not on screen, so it's
    // only used as a last-resort fallback, never preferred over `message`.
    throw new ApiError(
      response.status,
      body.message ?? body.detail ?? "Something went wrong loading this data. Please try again."
    );
  }
  return response.json();
}

export function fetchWindSeries(start: string, end: string): Promise<WindSeriesResponse> {
  return getJson<WindSeriesResponse>("/forecasts/wind-series/", { start, end });
}

export function fetchAccuracyMetrics(start: string, end: string): Promise<AccuracyResponse> {
  return getJson<AccuracyResponse>("/analytics/accuracy/", { start, end });
}

export function fetchDataStatus(): Promise<DataStatus> {
  return getJson<DataStatus>("/forecasts/status/", {});
}
