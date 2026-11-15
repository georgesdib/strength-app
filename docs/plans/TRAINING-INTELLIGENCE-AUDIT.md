# TRAINING INTELLIGENCE — ARCHITECTURE AND CAPABILITY AUDIT (INT-0)

**Status:** audit record, 2026-11-14. Documentation only: no runtime, API, schema, dependency,
prompt, training-rule or iOS deployment-target change is included.
**Scope:** the actual state of the portfolio, backend and iOS/watchOS repositories before the
Training Intelligence workstream starts, and the constraints any intelligence architecture must
respect.
**Companion documents:** the canonical plan is [`TRAINING-INTELLIGENCE.md`](TRAINING-INTELLIGENCE.md);
the tool and evidence contracts are [`../contracts/TRAINING-INTELLIGENCE-CONTRACT.md`](../contracts/TRAINING-INTELLIGENCE-CONTRACT.md);
the decisions are [`../decisions/TRAINING-INTELLIGENCE-ADR.md`](../decisions/TRAINING-INTELLIGENCE-ADR.md).

This audit is a dated snapshot. It supersedes no existing plan, decision or roadmap item; where it
contradicts older documentation the measured implementation wins, and the discrepancy is listed in
section 8 rather than silently reconciled.

## 1. Repositories, branches and commits actually inspected

Inspected from the owner's working copy at `/Users/georgesdib/Dev/strength-app`, on
2026-11-14, with all three remotes fetched.

| Repository | Branch | Commit inspected | Commit date | Note |
|---|---|---|---|---|
| `georgesdib/strength-app` (portfolio) | `development` | `1375f15e53c91a659c2d1e31950161f854640728` | 2026-11-14 | one commit behind `origin/development` (`524208c`, docs-only) |
| `georgesdib/strength-training-app` (backend) | `development` | `15474058f896d706b5b7fa9ec19afe4da95cc0f8` (tag `v1.4.1`) | 2026-11-14 | one commit behind `origin/development` (`2c70d60`, docs-only) |
| `georgesdib/StrengthApp` (iOS/watchOS) | `development` | `dc3fec78840c7ed192ccf1f857475dd6488592eb` | 2026-11-14 | one commit behind `origin/development` (`d763fba`, docs-only) |

Submodule pins (declared in `.gitmodules`; HEAD tree entries):

| Submodule | Pinned in the portfolio index | Checked out in the working tree |
|---|---|---|
| `StrengthApp` | `11a6b700fee311cfd36eb7017f5b87f63ca1b3ee` | `dc3fec7` (portfolio reports ` M StrengthApp`) |
| `strength-training-app` | `15474058f896d706b5b7fa9ec19afe4da95cc0f8` | `1547405` (matches) |

The three "behind" commits are documentation-only on every branch, so the code audited below is
identical to the current remote development tips. **The iOS submodule pin is stale relative to the
checked-out work.** Moving it is an existing portfolio-consolidation task and is **not** changed by
this work: portfolio rules forbid moving submodule pointers as a side effect of ordinary work.

## 2. Backend — what actually exists

### 2.1 Shape and framework

- **There is no FastAPI, Flask, Starlette, uvicorn or Pydantic in the backend.** A repository-wide
  search for those names returns nothing. The HTTP surface is a single
  `http.server.ThreadingHTTPServer` handler in `strength_coach/web/server.py` (**5,466 lines**,
  ~249 KB) that dispatches on `path` with `if/elif` chains and calls feature/repository
  functions directly. Any architecture that assumes a typed router, dependency injection, OpenAPI
  or a middleware stack is describing a service that does not exist here.
- The package is `strength_coach` (159 Python files, ~52,900 lines), Python `>=3.11`, runtime
  dependencies `pandas`, `numpy`, `PyYAML` only. One console script: `strength-coach`.
  Tests: 167 modules under `tests/`, pytest with xdist and marker-based exclusions.
- Declared layering (`strength_coach/__init__.py`): `utils → domain → ingest → store → features →
  rules → prescribe → critique → agents → eval`, enforced by import direction. `prescribe` may
  not call an LLM; `agents` may only call deterministic functions.
- Persistence is SQLite through `strength_coach/store/` with **59 append-only migrations** (latest
  `0059_observation.sql`) and a **single-athlete database** (`data/coach.db`). There is no
  `user_id` or tenant column anywhere in the clinical schema; `ROADMAP.md` §4.19.1 describes a
  per-user database plan that is explicitly **not implemented**.
- Existing observability is modest and adequate for a home server: `logging` plus a 500-record
  in-memory ring buffer exposed at `GET /api/logs`; `run`/`run_event` tables record LLM and
  analytical runs; the e1RM calibration and programme-schedule caches already use
  `PRAGMA data_version` + `conn.total_changes` as an invalidation stamp.

### 2.2 Authentication and isolation (the decisive constraint)

- `/api/ios/v1/` is **the only authenticated surface**: a per-device 32-byte bearer token stored as
  a SHA-256 digest in `ios_device`; pairing is CLI-only (`strength-coach ios pair`); revoked
  devices return `403`; mutations require an `Idempotency-Key` with a 30-day receipt.
- Every other route — including every analytical route — is **unauthenticated** on the home LAN
  (`DEC-WEB-03`, accepted risk `LIM-57`).
- There is **no OAuth 2.x authorization server, no session store, no users table and no
  multi-tenancy**. "Per-user authorization" therefore cannot be implemented today as multi-tenant
  isolation. It can only mean: one deployment serves exactly one athlete, each client holds its own
  credential, and every capability resolves the one configured database.

### 2.3 Analytical surface that already exists and is authoritative

This is the material finding for the workstream: almost every analytical capability the intelligence
layer needs **already exists, is tested, and is the documented single source of truth**. The
intelligence layer must compose these, not re-derive them.

| Capability | Authoritative module / function | Exposed today as |
|---|---|---|
| Target-based attendance | `features/attendance.py` `summary()` | `/api/progress`, `/api/outcomes` |
| Progress dashboard (performance ratio, volume, back status) | `features/progress.py` `dashboard()` | `/api/progress`, `/api/ios/v1/progress` |
| 4/8/12-week outcomes review | `features/outcomes.py` `report()` | `/api/outcomes` |
| Weekly history | `features/weekly.py` `history()` | `/api/overview` |
| Prescription adherence (per set, per workout) | `adherence.py`, `workout.summary()["adherence"]` | `/api/workout/<id>/summary`, `/api/history/<id>` |
| Multi-week adherence analytics | `features/adherence_analytics.py` `analytics()` | `/api/adherence/analytics` |
| e1RM observations, rolling median, breaks | `features/strength_trend.py` `observations()`, `rolling_median()`, `summarize()`, `series_breaks()` | `/api/performance/e1rm` |
| Per-exercise history with analytics | `features/exercise_history.py` `history()` | `/api/exercise-history`, `/api/ios/v1/exercises/<id>/history` |
| e1RM calibration (measured tests vs formula) | `features/e1rm_calibration.py`, `features/e1rm_source.py`, `features/e1rm_decay.py` | `/api/e1rm/calibration`, `/api/e1rm/tests-needed` |
| VBT longitudinal analysis (cohorts, residuals, bands, drift, gates) | `features/vbt_performance.py` `analyse()`, `features/vbt_analysis.py` | `/api/performance/vbt` |
| Readiness scoring and series | `features/readiness.py`, `features/readiness_score.py`, `queries.readiness_series()` | `/api/readiness/<date>`, `/api/readiness/history` |
| Readiness follow-up of fatigue reductions | `features/readiness_feedback.py` | `/api/readiness/feedback` |
| Volume ledger, budget, landmarks | `features/volume.py`, `prescribe/volume_budget.py` | `/api/volume`, `/api/volume/budget` |
| Deload state | `features/deload.py`, `prescribe/deload.py` | prescription warnings, `/api/outcomes` |
| Regime change (main lift vs substitute) | `features/regime_change.py` `detect()` | `/api/regime` |
| Declared breaks and continuity | `features/breaks.py`, `features/continuity_calibration.py` | `/api/continuity`, programme |
| Fatigue, exposure and substitution advisories | `features/fatigue_fitness.py`, `features/exposure.py`, `prescribe/fatigue_selection.py` | `/api/fatigue`, `/api/exposure`, `/api/substitution` |
| Sessions and session detail | `history.list_sessions()`, `history.detail()` | `/api/history`, `/api/ios/v1/history` |
| Completed-workout report with evidence | `workout.summary()` | `/api/workout/<id>/summary`, `/api/ios/v1/workouts/<id>/summary` |
| Longitudinal observations (AFC-3) | `features/observations.py` `analyse()` | `/api/observations`, nudge |
| Coaching nudges (AFC-4) | `features/nudges.py` | `/api/nudge` |
| Prescription facts and provenance | `prescribe/persistence.py`, `features/prescription_provenance.py` | `/api/prescribe`, prescription pages |
| **Evidence envelope** | `features/evidence.py` (`EVIDENCE_VERSION "2.0.0"`, `EvidenceItem`) | embedded in summary, observations, AFC |

### 2.4 The existing shared evidence contract

`strength_coach/features/evidence.py` is a **serialiser, not a calculator**, jointly owned by AFC
and the future LLM layer. Each item carries `evidence_id` (deterministic over source ids, window and
value), `evidence_version`, `source_fingerprint`, `source`, `source_ids`, `window`, `value`,
`unit`, `n`, `comparability` (`comparable|partial|not_comparable`), `gate`
(`insufficient|signal|evaluation`), `quality_flags`, `method_versions`, `calibration_ids`,
`limitations`, `rule_ids` and `assumption_ids`.

There is **no confidence-score field, and none should be invented**. Gate, `n`, comparability and
quality flags are the whole uncertainty vocabulary the system can justify. `workout.summary()`
already emits an `evidence` array plus `quality`, `basis` and at most one `observation`
(`DEC-AFC-08`), and the native iPhone client already decodes and renders it.

### 2.5 What does not exist in the backend

- No intelligence capability layer, no shared context package, no `AthleteContextBuilder`.
  `LLM-INTEGRATION-PLAN.md` §4.1 says this explicitly and is correct.
- No MCP dependency, server, tool, resource or prompt. No `mcp` package in `pyproject.toml`.
- No model tool-calling: `agents/client.py` is text-in/text-out. `agents/selection.py` (the minimal
  chooser) is scheduled for retirement (`DEC-LLM-14`, Phase 1b) and must not be extended.
- No structured-output validator for reports: `LLM-INTEGRATION-PLAN.md` §5.2 defines one on paper.
- No rate limiting or per-caller accounting on read routes; `/api/logs` is global.
- No OpenTelemetry and no request ids on the home-LAN routes.
- Some read logic exists **only inside the monolith** as private handler methods (for example
  `_readiness_history`). Most are thin validation over a `queries`/`features` function
  (`_readiness_history` → `queries.readiness_series`), but a few compose several services inline.
  A separate process must not import `strength_coach.web.server`; it should call the same
  `queries`/`features` functions and own its own validation.

## 3. iOS/watchOS — what actually exists

- Targets: `IPHONEOS_DEPLOYMENT_TARGET = 27.0`, `WATCHOS_DEPLOYMENT_TARGET = 27.0` (watch
  UI-test target 27.2), `SWIFT_VERSION = 5.0`, `TARGETED_DEVICE_FAMILY` iPhone/iPad plus watch,
  generated Info.plists, one `StrengthApp` and one `StrengthWatch` target with shared XCTest
  bundles.
- `StrengthCore` is a local SwiftPM package shared by the iPhone app, the watch app and the tests:
  models (`APIModels`, `Phase2Models`, `WorkoutSummaryModels`, `ExecutionModels`,
  `ExerciseLibraryModels`), `IOSAPIClient` (~1,000 lines: bearer auth, idempotency, retry ladder,
  same-host redirect guard), mutation journal, offline capture, session engine and watch execution.
  The client plan forbids `StrengthCore` from importing SwiftUI, UIKit, WatchKit, HealthKit or
  WatchConnectivity.
- App state is one `@MainActor final class AppModel: ObservableObject` (~2,629 lines in
  `StrengthApp/Core/AppModel.swift`) holding readiness, prescription/plan state, active workout,
  history, HealthKit, rest timer and watch pairing. Feature views are SwiftUI under
  `StrengthApp/Features/{Today,Readiness,Prescription,Workout,History,Progress,Settings,Pairing}`.
- HealthKit is opt-in and read-only (HRV, RHR, bodyweight) with provenance carried to the server; the
  phone never computes a score. The watch adds heart rate and an exactly-once workout save.
- **There is no App Intents, no Siri integration, no Shortcuts provider, no FoundationModels import
  and no Apple Intelligence code of any kind.** A repository-wide search for
  `import FoundationModels`, `LanguageModelSession`, `import AppIntents`, `AppIntent`,
  `AppShortcutsProvider` and `SystemLanguageModel` returns nothing. `FinishIntent.swift` is a
  HealthKit finalisation value object, not an `AppIntent`.
- Tests are XCTest (`StrengthAppTests`), including `IOSAPIClientTests`, `WorkoutSummaryTests`,
  `Phase2ClientTests` and nine watch suites. Client tests are contract-shaped and decode server
  payloads from synthetic fixtures.

## 4. Portfolio — documentation state

- `docs/` holds `plans/` (`IOS-CLIENT-PLAN.md`, `AFC.md`, index), `contracts/` (seven iOS phase
  contracts plus an index), `agent/` (routing, prompts, handoff) and the ownership policy
  `DOCUMENTATION.md`. `docs/decisions/`, `docs/specifications/` and `docs/operations/` are named
  in the ownership policy but did not exist before this task; `docs/decisions/` is created by it,
  the other two still do not exist.
- Ownership rule (verified): cross-repository plans, shared architecture, server/client contracts and
  cross-component decisions belong here; Python architecture/API/schema detail stays in the backend;
  Swift/Xcode detail stays in the iOS repository. Component repositories may keep short
  compatibility pointers, never a second copy.
- The backend `ROADMAP.md` is the **live backend implementation-status authority**, consumed by the
  docs viewer and consistency tests. Portfolio documents link to it and do not restate it.
- `scripts/check-doc-headings.sh` fails a documentation change that silently drops a `##` or
  `###` heading from a modified file. Any edit to an existing shared document must preserve headings.

## 5. Reusable capabilities — do not rebuild these

The intelligence layer should be a **composition layer**, exactly as AFC is (`DEC-AFC-01`):

1. `features/evidence.py` — the evidence envelope.
2. `workout.summary()` — the completed-session report, already carrying adherence, VBT, dose,
   quality, basis, evidence and one observation.
3. `features/observations.py` — the only sanctioned "this looks like a trend" producer.
4. `features/adherence_analytics.py`, `features/attendance.py`, `features/volume.py`,
   `prescribe/volume_budget.py`, `features/strength_trend.py`, `features/vbt_performance.py`,
   `features/outcomes.py`, `features/progress.py`, `features/regime_change.py` and
   `features/deload.py` — the metrics themselves.
5. `features/prescription_provenance.py` — why a persisted prescription has the shape it has.
6. `agents/config.py` and `agents/client.py` — the provider-agnostic LLM client and settings, with
   `NullLLM` as the default.
7. `trace/run.py` plus `run`/`run_event` — provenance for any model call, with no schema change
   (`DEC-LLM-01`).
8. `queries.clean_sets_snapshot()` and the `PRAGMA data_version` + `total_changes` stamp — read
   consistency and cache invalidation.
9. iOS `IOSAPIClient`, `WorkoutSummaryModels` and the existing summary/report screens — the client
   already renders a server-produced structured report with evidence.

## 6. Missing components the workstream must build

| Missing | Why it is needed | Where it belongs |
|---|---|---|
| Provider-neutral capability layer (deterministic facts + envelope) | one assembly path for MCP, REST and the iOS adapter | backend package, not `agents/` |
| Compact baseline context builder with hash and version | small models cannot take the database, and every consumer needs the same facts | capability layer |
| MCP transport adapter (auth, tools, resources, errors) | the AI-facing interface | backend repository, separately deployable |
| Read-only REST intelligence surface for iOS | Apple Foundation Models cannot speak MCP, and Swift must not re-assemble facts | `/api/ios/v1/intelligence/…` |
| Structured narrative validator (claims, evidence refs, numeric grounding) | a model must not invent a number | capability/model layer |
| Weekly Review composition | first user-facing feature | capability layer |
| Evaluation harness with golden facts | proves grounding and catches regression | backend `tests/` and `eval/` |

## 7. Architectural constraints this audit establishes

1. **No second calculation.** Any capability that returns a metric calls the module that owns it. A
   test must fail if the intelligence layer re-implements a threshold or imports a data frame to do
   metric maths.
2. **No second evidence schema.** `features/evidence.py` is the schema; the envelope wraps it.
3. **No router-framework assumption.** A separate process imports `queries`/`features` and owns its
   own validation; it never imports `web.server`.
4. **Single athlete, not multi-tenant.** Per-user isolation is a future `ROADMAP` §4.19
   deliverable. The intelligence layer must not fake a tenant model and must not accept an
   `athlete_id` argument it cannot enforce.
5. **No writes.** No intelligence tool may create, edit, void, start, complete or prescribe.
6. **No beta dependency.** iOS 27.3 Siri AI and any point-release API is a preview, not a foundation.
7. **No new public surface.** The web UI stays unauthenticated on the home LAN; a new authenticated
   MCP endpoint must not widen that exposure.

## 8. Discrepancies between documentation and implementation

| # | Document claim | Actual state | Disposition |
|---|---|---|---|
| D1 | The work request describes an "existing FastAPI architecture and domain/service layers" | stdlib `ThreadingHTTPServer` monolith plus function modules; no FastAPI, no service layer | design for what exists; `ADR-INT-001` |
| D2 | `LLM-INTEGRATION-PLAN.md` §4.1/§11 place the future context builder at `agents/context.py` | nothing exists yet; `agents/` is the model layer and must not own deterministic assembly | path superseded by a provider-neutral `intelligence/` package (`ADR-INT-002`); the plan gets a pointer |
| D3 | `LLM-INTEGRATION-PLAN.md` §9.2 and `ROADMAP.md` §4.24 treat an MCP server as a conditional Iteration-2 candidate after a needs assessment | this workstream makes a read-only MCP server the primary AI-facing interface in Iteration 1 | reconciled by `ADR-INT-003`; the "no second engine, no writes, tailnet plus application auth" conditions are retained verbatim |
| D4 | `docs/plans/IOS-CLIENT-PLAN.md` §8 shows `StrengthApp/{App,Networking,Persistence,HealthKit}` | actual tree is `StrengthApp/{Core,Features}`; networking and models live in `StrengthCore` | noted; corrected only if §8 is edited for another reason |
| D5 | `ARCHITECTURE.md` §6 says "no authentication yet" | true of the web UI; `/api/ios/v1/` has per-device bearer auth | wording is scoped but easy to misread; no edit required now |
| D6 | `ROADMAP.md` §4.19.1 and `LIM-57` describe per-user auth as backlog | confirmed backlog; nothing implemented | the intelligence plan must not assume it exists |
| D7 | The work request implies a stored "training block" | there is no block entity; `DEC-PROGRAMME-01` says there is no fixed programme block and `DEC-W7-01` says there is no planned-session calendar | the candidate tool is renamed `get_programme_block_summary` and defined as a derived reporting window with an explicit limitation |

## 9. What could not be verified

- The behaviour of the iOS 27.3 Siri AI Developer Preview on the owner's device: it needs a beta OS,
  an internal build and region availability, and Apple states the App Intents API "may change" during
  the preview. Nothing here depends on it.
- Private Cloud Compute access: `PrivateCloudComputeLanguageModel` is documented for iOS 27, but use
  requires Apple's managed entitlement and a per-day quota. Entitlement status is not knowable from
  the repositories.
- Production latency of the heavier analytical calls (VBT analysis, adherence analytics, a 365-day
  e1RM series) on the ODROID host: no benchmark was run in this audit and none was added.
- Whether any hosted MCP client the owner uses accepts a static bearer token instead of OAuth
  discovery. That is an interoperability question for the owner, not a repository fact.

## Related

- [Training Intelligence plan](TRAINING-INTELLIGENCE.md)
- [Training Intelligence contract](../contracts/TRAINING-INTELLIGENCE-CONTRACT.md)
- [Architecture decision records](../decisions/TRAINING-INTELLIGENCE-ADR.md)
- [Backend LLM integration plan](https://github.com/georgesdib/strength-training-app/blob/development/docs/LLM-INTEGRATION-PLAN.md)
- [Documentation ownership](../DOCUMENTATION.md)
