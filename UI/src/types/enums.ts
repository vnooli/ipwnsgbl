export enum FetchState {
  Idle = "idle",
  Loading = "loading",
  Success = "success",
  Error = "error",
  Empty = "empty",
}

// Lets the UI choose a heading/tone appropriate to the failure instead of
// always saying "could not load data" - a bad date selection, an
// unreachable API, and a flaky upstream service all call for different
// framing and next steps for the user.
export enum ErrorKind {
  Validation = "validation",
  Connection = "connection",
  Unknown = "unknown",
}

export enum BannerKind {
  Loading = "loading",
  Error = "error",
  Empty = "empty",
}

export enum KpiTone {
  Neutral = "neutral",
  Good = "good",
  Warn = "warn",
}
