# UK Wind Forecast & Day-Ahead Procurement Analytics

A web application that helps a UK electricity utility's day-ahead procurement team
understand the latest national wind generation forecast, how it compares to what
actually happened, and how accurate those forecasts have historically been — so they
can factor forecast uncertainty into how much power they buy from other sources.

Built as a scoped product-engineering assignment (16-hour effort budget). **AI tools
(Claude / Claude Code) were used extensively to design, implement, and document this
project** — see "Use of AI tools" below.

## 1. Business problem

The client buys electricity on the UK day-ahead wholesale market to cover demand not
met by their own/contracted generation. Wind is a major weather-dependent renewable
source, and day-ahead purchase decisions are made roughly a day before delivery, before
actual wind output is known — so the team relies on **forecasts**. This app answers two
questions for them:

1. What is the latest wind generation forecast that was actually available when a given
   purchasing decision had to be made?
2. How accurate have those forecasts historically been, in quantified terms, so that
   forecast uncertainty can be factored into the purchase decision?

Scope is deliberately limited to the two Elexon datasets specified in the brief —
**FUELHH** (actual generation, filtered to `fuelType=WIND`) and **WINDFOR** (forecast
generation) — for **January 2026** delivery periods. No demand forecasts, other
generation, or market prices are introduced, and the app never claims to compute a
definitive purchase volume, financial loss, or realised procurement cost (see
"Procurement interpretation" below).

## 2. Architecture & technology stack

```
/
├── UI/            React + Vite + TypeScript + Tailwind dashboard
├── API/           Django + DRF backend
│   ├── config/            settings, urls, wsgi
│   └── apps/
│       ├── forecasts/     Elexon integration, forecast selection, data status/refresh
│       │   ├── repositories/   ElexonClient (HTTP), in-memory TTL cache, repo facade
│       │   ├── services/       forecast_selection.py (alignment + decision-cutoff logic)
│       │   ├── queries/        WindSeriesQuery (read use case)
│       │   ├── commands/       RefreshDataCommand (state-changing use case)
│       │   ├── serializers/    request validation + response shaping
│       │   ├── views/          DRF APIViews (thin; no business logic)
│       │   └── tests/
│       └── analytics/     Forecast accuracy metrics & procurement interpretation
│           ├── services/       accuracy_metrics.py (MAE/RMSE/bias/MAPE, pure functions)
│           ├── queries/        AccuracyQuery
│           ├── views/
│           └── tests/
├── docker-compose.yml
└── README.md
```

### Backend: lightweight CQRS, no mediator

Reads flow `View → Query → Service → Repository/Elexon client → Result`.
Writes (the controlled refresh) flow `View → Command → Service → Repository → Result`.
There is no mediator/dispatcher — a view directly instantiates the query or command
object it needs and calls `.execute()`. This keeps the indirection a large enterprise
app would use, without the dispatch-framework overhead that isn't justified here.

- **Elexon client** (`forecasts/repositories/elexon_client.py`): the only place that
  calls `requests`. Handles retries with backoff, timeouts, JSON-shape normalisation,
  and field validation; never leaks raw HTTP objects or stack traces upward.
- **Forecast selection** (`forecasts/services/forecast_selection.py`): pure, HTTP-free
  business logic — aligning actual/forecast records to shared 30-minute delivery
  periods and selecting the forecast version that was actually available at the
  procurement decision cutoff. This is the module most worth reading to understand the
  domain, and it is the most heavily unit-tested.
- **Accuracy metrics** (`analytics/services/accuracy_metrics.py`): pure functions over
  aligned periods — no Django/HTTP coupling, so they're testable and reusable in
  isolation from the API.

### Frontend

React + Vite + TypeScript, styled with Tailwind. API calls live in `src/api/client.ts`
and a `useProcurementData` hook; presentational components (`KpiCard`, `GenerationChart`,
`ErrorChart`, `ForecastTable`, `DateRangeFilter`, `StatusBanner`) never call the API
directly. Loading, empty, and error states are modelled explicitly (see `FetchState` in
the hook) rather than inferred from the shape of the data.

## 3. Data sources & forecast-selection rules

| Dataset | Use | Key fields used |
|---|---|---|
| [FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) | Actual generation, filtered to `fuelType=WIND` | `startTime`, `generation` |
| [WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) | Forecast wind generation | `startTime`, `publishTime`, `generation` |

**Alignment:** actual and forecast records are matched on `startTime` (the 30-minute
delivery period).

**Decision-cutoff assumption (important, and configurable):** the assignment does not
specify an exact day-ahead decision cutoff. This app assumes decisions for a delivery
date `D` must be made by `DECISION_CUTOFF_HOUR:00` **Europe/London local time** on `D-1`
(default `11:00`, a reasonable approximation of the late-morning EPEX/N2EX day-ahead
auction window — not an official market rule). It is a Django setting
(`DECISION_CUTOFF_HOUR` / env var of the same name) and can be overridden per-request
via the `cutoff_hour` query parameter on the forecast endpoints, independent of the
alignment logic itself.

For each delivery period, the service selects the **most recently published forecast
whose `publishTime` is on or before that period's cutoff instant**. A forecast published
after the cutoff is never used for decision-time accuracy — it may only be shown
separately as the "latest forecast" for comparison (see
`AlignedPeriod.latest_forecast_mw` vs. `decision_forecast_mw`, and the UI's publication
history view).

**Timezone handling:** the cutoff is computed as a timezone-aware `Europe/London`
datetime and converted to UTC, so UK clock changes (GMT ↔ BST) are handled correctly
rather than via a fixed UTC offset — see `decision_cutoff_for_delivery_date` and its
tests for both a GMT and a BST example.

## 4. Accuracy metrics & sign convention

All metrics are computed only over delivery periods that have **both** an actual and a
decision-time forecast value; missing values are counted and reported, never treated as
zero.

- **Forecast error** = `forecast − actual` (MW), per period.
- **MAE** = mean of `|error|`.
- **RMSE** = sqrt(mean of `error²`).
- **Bias** = mean of signed `error`. **Positive bias → forecasts tend to over-state wind
  generation**; negative → under-state.
- **MAPE** = mean of `|error| / actual`, computed **only** over periods where actual
  generation is nonzero (otherwise the percentage is undefined/meaningless). Its sample
  count is reported separately from MAE/RMSE/bias's.

### Procurement interpretation (and what this app does *not* claim)

If the decision-time forecast over-stated wind generation (positive bias), the implied
residual demand from other sources was, on average, larger than planned — assuming
demand and other generation held as expected; the reverse holds for under-statement.
**This is explicitly labelled as a wind-forecast-derived estimate.** The assignment
supplies no demand forecast, no other-generation data, and no market prices, so the app
never computes — and the API/UI never present — a definitive purchase volume, financial
loss, or realised procurement cost.

## 5. Data handling & persistence

No relational database is used. Trade-off, documented here rather than hidden: the
assignment's scope is a single month of 30-minute national data, which is small,
re-derivable from Elexon at any time, and read-heavy — so a process-local **in-memory
TTL cache** (`forecasts/repositories/cache.py`, default 15 minutes) sits in front of the
Elexon client instead of a database. This avoids infrastructure the assignment says not
to add "solely for architectural appearance," at the cost of: the cache is lost on
restart, is not shared across multiple API processes, and does not retain forecast
publish-time history beyond whatever Elexon itself still serves. If this were extended
beyond the assignment (e.g. to guarantee reproducing a decision-time forecast after
Elexon's own retention window has passed), the next step would be a small Postgres table
keyed on `(startTime, publishTime)` with idempotent upserts — the repository interface
is already isolated so that swap would not touch services or views.

A `POST /api/forecasts/refresh/` command clears the cache and re-fetches for a given
window. No fixture/sample data is fabricated anywhere in the running app; if Elexon is
unreachable, the API returns a `503` with a clear error rather than inventing values.

## 6. API reference

Base path: `/api/`

| Method & path | Purpose |
|---|---|
| `GET /forecasts/wind-series/?start=YYYY-MM-DD&end=YYYY-MM-DD[&cutoff_hour=H]` | Aligned actual vs. decision-time-forecast series for the range |
| `GET /forecasts/publication-history/?start=...&end=...` | Same alignment, framed for inspecting decision-time vs. latest-published forecast per period |
| `GET /forecasts/status/` | Cache/data-source status |
| `POST /forecasts/refresh/` `{"start": "...", "end": "..."}` | Force-refresh cached Elexon data for a window |
| `GET /analytics/accuracy/?start=...&end=...[&cutoff_hour=H]` | MAE/RMSE/bias/MAPE + procurement interpretation |

Date ranges are validated to lie within January 2026 (`2026-01-01`–`2026-01-31`); all
errors return structured JSON (`{"error": "...", "detail": "..."}`) with an appropriate
HTTP status — `400` for invalid parameters, `503` if Elexon is unreachable. No internal
stack traces or credentials are ever exposed to the client.

## 7. Local setup

### Backend

```bash
cd API
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
python manage.py runserver 0.0.0.0:8000
```

### Frontend

```bash
cd UI
npm install
cp .env.example .env
npm run dev
```

The UI defaults to calling the API at `http://localhost:8000/api` (`VITE_API_BASE_URL`).

### Tests

```bash
cd API
pytest
```

> **Verification status:** Python was installed and the full stack was actually run and
> exercised in this session. `pytest` passes (27/27). The Django dev server was started
> and hit directly, including against the **live** Elexon API — this is how two real bugs
> were caught and fixed: WINDFOR/FUELHH both reject a `publishDateTime` span over 7 days
> (requests are now chunked, see `_chunk_date_range` in `elexon_client.py`), and WINDFOR
> uses `publishDateTimeFrom`/`publishDateTimeTo` rather than `from`/`to`. A third issue -
> WINDFOR is published hourly while FUELHH actuals are half-hourly, so exact-timestamp
> alignment silently dropped every `HH:30` period - was found and fixed by bucketing
> forecasts to their containing hour (see `_hour_bucket` in `forecast_selection.py`). The
> UI was run against this live backend end-to-end (not just mocked): KPI cards, the
> generation/error charts, and the forecast explorer all render correctly with real
> January 2026 Elexon data for single-day, week, and full-month ranges.

## 8. Docker

```bash
docker compose up --build
```

Starts the API (port 8000, gunicorn) and the UI (port 5173, nginx serving the built
static bundle). Health checks are configured for both services. Secrets/config are kept
out of source control via `.env` (backend) and build-time `VITE_API_BASE_URL` (frontend);
`.env.example` files document every variable.

Note: this is a production-style build (nginx serving a static bundle, gunicorn for the
API) - it does not hot-reload on source changes. After editing code, re-run
`docker compose up --build` to pick up the changes. For active development, run the API
and UI directly on the host instead (see §7), which does hot-reload.

## 9. Environment variables

**API** (`API/.env`, see `API/.env.example`): `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`,
`DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `ELEXON_API_BASE_URL`,
`DECISION_CUTOFF_HOUR`, `ELEXON_CACHE_TTL_SECONDS`.

**UI** (`UI/.env`, see `UI/.env.example`): `VITE_API_BASE_URL`.

## 10. Deployment (Vercel / Heroku)

Planned arrangement, chosen for the stack: **UI → Vercel** (static build of a Vite app),
**API → Heroku** (Django/gunicorn needs a long-running process, which Vercel's serverless
model doesn't fit well for this app's shape).

- **API on Heroku:** add a `Procfile` (`web: gunicorn config.wsgi:application`), set
  `DJANGO_ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` (to the Vercel URL) as Heroku config
  vars, and deploy the `API/` subdirectory (`git subtree push` or a monorepo buildpack).
- **UI on Vercel:** set the project root to `UI/`, build command `npm run build`, output
  directory `dist`, and set `VITE_API_BASE_URL` to the deployed Heroku API URL as a
  Vercel environment variable.
- **CORS:** the Heroku API's `CORS_ALLOWED_ORIGINS` must include the exact Vercel
  domain; no database/persistent storage is required by either platform.

**This has not actually been deployed in this session** — no deployed URL is given here.
Do not treat this section as more than a documented plan until a real deployment has
been performed and verified (per the assignment's own instruction not to claim deployment
that hasn't succeeded).

## 11. Known limitations & assumptions

- Decision cutoff hour is a documented assumption (11:00 Europe/London, D-1), not an
  official market rule — configurable via `DECISION_CUTOFF_HOUR` / `cutoff_hour`.
- No database: forecast publish-time history is only as deep as Elexon's own API
  currently serves; an in-memory cache is used instead (see §5).
- Scope is hard-limited to January 2026 and to FUELHH(WIND)/WINDFOR, per the brief; the
  API rejects date ranges outside that window.
- Procurement figures are wind-forecast-derived estimates only — no demand, other
  generation, or price data is used or implied.
- The backend test suite is written but **unexecuted** in this environment (see §7);
  the Elexon integration has not been exercised against the live API in this session
  either, since that also requires the Python runtime.
- No authentication/multi-tenancy — out of scope per the brief.

## 12. Deliverables status (per assignment)

- ✅ Code: API + UI, Dockerized, documented here.
- ❌ **Video demo** (client pitch + technical walkthrough, ≤10 min, unlisted YouTube) —
  **not recorded**. A demo script/outline is provided below so one can be recorded.
- ❌ **Public GitHub repo with an anonymous name** — **not created/published**; this
  repository is currently local only. Creating and pushing to a public repo, and
  submitting the challenge form, are actions with real external/irreversible
  consequences (publishing code publicly) that were intentionally left for explicit
  user action rather than performed automatically.
- ❌ **Deployment** — not performed (see §10).

### Demo script outline (for the two-part video)

**Part 1 — client pitch (≤5 min):** (1) the business problem in one sentence; (2) show
the dashboard with a week of January 2026 loaded — KPI cards, generation chart, error
chart; (3) walk through one specific delivery period in the forecast explorer, pointing
out the forecast-publish-time column; (4) state the procurement interpretation sentence
and its disclaimer out loud; (5) close on "this quantifies forecast risk you can fold
into tomorrow's buy."

**Part 2 — technical walkthrough (≤5 min):** (1) repo structure and the CQRS-without-
mediator flow; (2) `forecast_selection.py` — the decision-cutoff/timezone logic, and why
it's isolated and unit-tested; (3) `accuracy_metrics.py` — sign convention, MAPE's
nonzero-actual exclusion, missing-data handling; (4) the deliberate choice not to add a
database, and what would change if one were added later; (5) Docker/compose and the
honest caveat about what has and hasn't been run in this environment.

## 13. Use of AI tools

This project — architecture, backend, frontend, tests, and this README — was built with
substantial assistance from **Claude Code** (Anthropic), as permitted and expected by the
assignment brief. Human review and editing were applied throughout; the assumptions,
trade-offs, and limitations documented above reflect judgment calls made explicit during
that process rather than unexamined AI output.
