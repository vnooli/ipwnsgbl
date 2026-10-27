export interface AlignedPeriod {
  startTime: string;
  actualGenerationMw: number | null;
  decisionForecastMw: number | null;
  decisionForecastPublishTime: string | null;
  latestForecastMw: number | null;
  latestForecastPublishTime: string | null;
  hasActual: boolean;
  hasDecisionForecast: boolean;
  forecastErrorMw: number | null;
  absoluteErrorMw: number | null;
}

export interface WindSeriesResponse {
  start: string;
  end: string;
  count: number;
  results: AlignedPeriod[];
}

export interface AccuracyMetrics {
  maeMw: number | null;
  rmseMw: number | null;
  biasMw: number | null;
  mapePercent: number | null;
  sampleCountMaeRmseBias: number;
  sampleCountMape: number;
  totalPeriods: number;
  periodsMissingActual: number;
  periodsMissingDecisionForecast: number;
}

export interface AccuracyResponse {
  start: string;
  end: string;
  metrics: AccuracyMetrics;
  procurementInterpretation: {
    summary: string;
    disclaimer: string;
  };
}

export interface DataStatus {
  cached_keys: string[];
  cache_ttl_seconds: number;
}
