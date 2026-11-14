# TRAINING INTELLIGENCE — MCP, ENVELOPE AND ADAPTER CONTRACT

**Status:** proposed 2026-11-14 (v0.1). Not implemented. Normative for INT-1 onward once approved.
**Canonical location:** this file, in the portfolio repository. Server implementation stays in
`georgesdib/strength-training-app`; client implementation stays in `georgesdib/StrengthApp`.
**Companions:** [plan](../plans/TRAINING-INTELLIGENCE.md), [audit](../plans/TRAINING-INTELLIGENCE-AUDIT.md),
[decisions](../decisions/TRAINING-INTELLIGENCE-ADR.md).

The key words MUST, MUST NOT, SHOULD and MAY are used in the RFC 2119 sense.

## 1. Scope

This contract fixes five things so that three transports and two model paths cannot drift:

1. the **response envelope** every capability returns (§3);
2. the **evidence and provenance rules** (§4);
3. the **MCP surface**: tools, resources, schemas, errors and limits (§7–§9);
4. the **REST adapter** the iPhone uses (§10);
5. the **native iOS adapter** and its five-tool cap (§11).

It does not fix prompt text, model choice, provider configuration or UI layout. Those are
implementation decisions inside the plan.

## 2. Versioning and compatibility

| Identifier | Value in v1 | Change rule |
|---|---|---|
| `intelligence_version` | `1.0.0` | minor = additive field; major = breaking field or semantic change |
| `schema_version` (envelope) | `intelligence.envelope.v1` | new major = new URI/name, old one kept until clients migrate |
| `evidence_version` | `2.0.0` (owned by `features/evidence.py`) | change only in that module |
| tool schema | published by `tools/list` | a breaking input change MUST use a new tool name |
| resource URI | `strength://…` | a breaking payload change MUST use a new URI path or a `v2` segment |
| MCP protocol | revision `2026-07-28`; legacy ≤2025-11-25 accepted by the SDK | the SDK negotiates; the server MUST NOT reject a supported era |

Clients MUST tolerate unknown fields. The server MUST NOT remove or repurpose a field in a v1
envelope. New fields are added with a default that preserves the old meaning.

## 3. The response envelope

Every capability returns exactly this object. Nothing wraps it; MCP puts it in
`structuredContent`, REST returns it as the body.

~~~json
{
  "intelligence_version": "1.0.0",
  "schema_version": "intelligence.envelope.v1",
  "capability": "exercise_progression",
  "status": "ok",
  "as_of": "2026-11-14",
  "period": {
    "start": "2026-08-22",
    "end": "2026-11-14",
    "days": 84,
    "weeks": 12,
    "timezone": "Europe/London"
  },
  "subject": {"athlete": "self"},
  "units": {"load": "kg", "velocity": "m/s", "duration": "min"},
  "facts": {"<fact_name>": {"<FactBlock>": "..."}},
  "evidence": ["<EvidenceItem>"],
  "observations": ["<Observation>"],
  "coverage": {"<string>": "number | string | null"},
  "missing": ["<string>"],
  "limitations": ["<string>"],
  "quality_flags": ["<string>"],
  "privacy": {"class": "training", "excluded_fields": ["notes"], "redactions": []},
  "provenance": {
    "services": [{"module": "strength_coach.features.attendance", "version": "1.4.1"}],
    "config_revision": "sha256:…",
    "database_revision": 4711,
    "builder_version": "context.v1",
    "context_hash": "sha256:…"
  },
  "generated_at": "2026-11-14T09:12:03Z"
}
~~~

### 3.1 Field rules

| Field | Required | Rule |
|---|---|---|
| `status` | yes | one of `ok`, `no_data`, `insufficient`; never an error code |
| `capability` | yes | the capability name, stable, snake_case, equal to the tool name where a tool exists |
| `as_of` | yes | the server-local training date the answer is computed for |
| `period` | yes | the analysed window; `start` ≤ `end`; `weeks` may be null when the window is not week-aligned |
| `subject` | yes | `{"athlete": "self"}` until tenancy exists; MUST NOT be client-supplied |
| `units` | yes | explicit units for every unit-bearing value in `facts` |
| `facts` | yes | object of named **FactBlocks**; may be empty only when `status` is `no_data` |
| `evidence` | yes | array of the untouched `EvidenceItem` objects referenced by facts; may be empty |
| `observations` | yes | 0–2 AFC-3 observations; MUST be `[]` when the capability has no observation source |
| `coverage` | yes | numeric coverage facts; MUST name what was counted |
| `missing` | yes | human-readable missing inputs, in plain language, no numbers invented |
| `limitations` | yes | capability limitations, including the relevant register ids where they exist |
| `quality_flags` | yes | copied from the owning service, never synthesised |
| `privacy` | yes | sensitivity class and the fields deliberately excluded |
| `provenance` | yes | services, revisions and the context hash |
| `generated_at` | yes | UTC ISO-8601 with `Z` |

### 3.2 FactBlock

~~~json
{
  "value": 0.67,
  "basis": "derived",
  "method": "strength_coach.features.attendance.summary",
  "unit": "ratio",
  "n": 8,
  "gate": "signal",
  "comparability": "comparable",
  "evidence_ids": ["ev:3f2a…"],
  "quality_flags": [],
  "note": null
}
~~~

Rules:

- `basis` is `observed` (read from stored rows, `method` names the repository function) or
  `derived` (`method` names the computing function).
- `method` MUST be a fully qualified function that exists in the service registry. A test asserts
  every emitted method string is registered; a capability cannot invent a method name.
- `evidence_ids` MUST all exist in `evidence`. No dangling reference.
- `gate` and `comparability` use the vocabularies in `features/evidence.py`; `null` means
  the owning service did not express one, never "good".
- `value` may be a scalar, array or object. A series MUST carry its own `n` per element when the
  owning service does.

### 3.3 Status semantics

| Status | Meaning | Client requirement |
|---|---|---|
| `ok` | the capability produced the facts it promises | render facts and limitations |
| `no_data` | the window legitimately contains no observations | render "no data", never zeros |
| `insufficient` | data exists but is below the owning gate | render the fact with its gate and `n`, never a verdict |

## 4. Evidence and provenance

The evidence object is `features/evidence.py` `EvidenceItem.as_dict()`, unchanged:

~~~json
{
  "evidence_id": "ev:9c1d…",
  "evidence_version": "2.0.0",
  "source_fingerprint": "sf:4a7b…",
  "source": "adherence.set_completion",
  "source_ids": ["812", "813"],
  "window": {"start": "2026-11-08", "end": "2026-11-14"},
  "value": {"numerator": 18, "denominator": 21, "ratio": 0.857},
  "unit": null,
  "n": 21,
  "comparability": "comparable",
  "gate": "signal",
  "quality_flags": [],
  "method_versions": {"adherence": "1"},
  "calibration_ids": [],
  "limitations": [],
  "rule_ids": ["PRG-SET-001"],
  "assumption_ids": []
}
~~~

Rules:

- No capability constructs an evidence object by hand. It copies what the owning service produced or
  calls `EvidenceItem` with values the service supplied.
- No confidence percentage, score or probability is added anywhere in this contract. `gate`, `n`,
  `comparability`, `coverage` and `quality_flags` are the uncertainty vocabulary.
- `provenance.services` lists the modules whose functions produced facts, with the installed
  package version.
- `provenance.database_revision` is the `PRAGMA data_version` plus `conn.total_changes` stamp
  already used by the e1RM calibration cache.
- `provenance.context_hash` is SHA-256 over canonical JSON (`features/evidence.canonical_json`) of
  the baseline package plus builder and schema versions. Two identical requests against an unchanged
  database MUST produce the same hash.

## 5. Dates, windows, units

- Dates are the **server-local calendar date** in `YYYY-MM-DD`. The server's timezone is
  authoritative; `period.timezone` reports the IANA name used.
- Windows are inclusive at both ends. `as_of` may not be in the future relative to the server date.
- Loads are kilograms, velocities metres per second, durations minutes, bodyweight kilograms. A
  capability MUST declare any other unit in `units`.
- Percentages and ratios are 0–1 fractions unless the fact name says `pct`; `pct` values are
  0–100. Mixing the two in one capability is a defect.

## 6. Privacy classes and field policy

| Class | Examples | Default in intelligence output |
|---|---|---|
| `training` | sets, load, reps, RIR, session type, adherence, volume | included |
| `performance` | e1RM, velocity, VBT residuals, strength trend | included |
| `health` | readiness values, HRV, resting HR, bodyweight, symptoms, injuries | **excluded** unless the capability's purpose requires them and the caller opts in |
| `free_text` | session notes, symptom descriptions, form comments | **excluded** (no parameter in v1) |
| `identity` | device ids, tokens, database paths | never included |

A capability that includes `health` data MUST set `privacy.class` to `health`, list the fields,
and record the reason in `limitations`. The field-level outbound inventory required by
`LLM-INTEGRATION-PLAN.md` §8.1 MUST be completed for any model path before it is enabled.

## 7. MCP surface

### 7.1 Endpoint and transport

- One endpoint: `POST /mcp` (path configurable, default `/mcp`).
- Transport: Streamable HTTP, protocol revision `2026-07-28`; legacy clients (≤2025-11-25) are
  served by the SDK's compatibility path. No HTTP+SSE transport, no stdio in production.
- The server MUST validate the `Origin` header and MUST keep DNS-rebinding protection enabled with
  an explicit `allowed_hosts` list.
- Responses use `application/json` for tool calls (`json_response`) unless a tool declares
  progress; no tool in v1 does.

### 7.2 Capabilities advertised

| Capability | v1 |
|---|---|
| `tools` | yes, `listChanged: false` (static registry) |
| `resources` | yes, `subscribe: false`, `listChanged: false` |
| `prompts` | **no** |
| `logging` | no (deprecated; use stderr/structured logs) |
| `sampling`, `roots`, `elicitation` | no |
| `tasks` / extensions | no |

### 7.3 Authentication

- Every request MUST carry `Authorization: Bearer <token>`. Missing or invalid → `401` with
  `WWW-Authenticate: Bearer realm="strength-intelligence"` before JSON-RPC parsing.
- Tokens are opaque, per-client, 32 random bytes, stored only as SHA-256 digests in the git-ignored
  `config/intelligence.local.yaml`; comparison is constant-time; revocation is deletion.
- The server MUST NOT publish an OAuth protected-resource-metadata document, because no
  authorization server exists. If one is added later, this section is replaced, not extended.
- No tool accepts an athlete, user, database or connection parameter.

### 7.4 Tool definition rules

- Names: `^[a-z][a-z0-9_]{2,63}$`, `get_` or `compare_` prefix, unique, deterministic order in
  `tools/list` (alphabetical), ≤ 128 characters.
- Every tool MUST declare `inputSchema` (`additionalProperties: false`) and `outputSchema`
  (the envelope).
- Every tool MUST declare `annotations`: `readOnlyHint: true`, `destructiveHint: false`,
  `idempotentHint: true`, `openWorldHint: false`.
- Descriptions MUST state what the tool returns, the window limits, and that it is read-only. No
  description may instruct the model about training policy.
- Tools MUST NOT return a resource that requires another tool to interpret a number.

### 7.5 Tool catalogue

| # | Tool | MVP | Deterministic | Reusable by iOS | Primary source |
|---|---|---|---|---|---|
| 1 | `get_training_overview` | **yes** | yes | yes | `features/progress.py`, `features/attendance.py`, `features/strength_trend.py` |
| 2 | `get_session_details` | **yes** | yes | yes | `workout.summary()`, `history.detail()` |
| 3 | `get_exercise_progression` | INT-2 | yes | yes | `features/strength_trend.py`, `features/exercise_history.py` |
| 4 | `get_readiness_history` | INT-2 | yes | yes | `queries.readiness_series()`, `features/readiness_score.py` |
| 5 | `get_adherence_analysis` | INT-2 | yes | yes | `features/adherence_analytics.py` |
| 6 | `get_prescription` | INT-2 | yes | yes | `prescribe/persistence.py`, `features/prescription_provenance.py` |
| 7 | `get_vbt_analysis` | INT-2 | yes | limited | `features/vbt_performance.py` |
| 8 | `get_programme_block_summary` | INT-2 | yes | yes | `features/deload.py`, `features/regime_change.py`, `prescribe/volume_budget.py` |
| 9 | `compare_training_periods` | INT-2 | yes | yes | `features/attendance.py`, `features/adherence_analytics.py`, `features/volume.py` |
| 10 | `get_weekly_review` | INT-3 | yes | yes | composition of 5, 8, and the trends |
| — | `explain_prescription` | **rejected as a tool** | — | — | model capability over tool 6 (see §7.9) |

`get_weekly_review_data` is not a separate tool: `get_weekly_review` returns the deterministic
package, and narration is a host capability.

#### 7.5.1 `get_training_overview`

**Purpose.** One compact, evidence-linked answer to "how is training going?" for a recent window.

**Input**

| Field | Type | Required | Range / default |
|---|---|---|---|
| `as_of` | string (date) | no | `YYYY-MM-DD`; default server today; MUST NOT be in the future |
| `window_weeks` | integer | no | 1–52, default 4 |

**Validation.** Unknown fields rejected. `as_of` before 2000-01-01 rejected. A window that extends
before the first stored session is allowed and returns reduced coverage.

**Output facts.** `attendance`, `sessions`, `strength` (main lifts only, direction and `n`),
`volume` (per pattern vs budget), `readiness_coverage` (counts only, no health values),
`deload`, `observations`, `quality`.

**Source of truth.** `features/progress.dashboard()` for the window, `features/attendance.summary()`
for target-based attendance, `features/strength_trend.summarize()` for per-lift direction,
`features/volume.compute()` for pattern volume. Symptom/back fields returned by `dashboard()` are
**projected out**.

**Deterministic.** Yes.

**Evidence.** One item per reported aggregate, copied from the owning service, plus one per main-lift
series.

**Coverage and limits.** Reports `sessions_considered`, `weeks_with_data`, `readiness_days`.
Limitations include "`attendance is target-based; no planned-session calendar exists (DEC-W7-01)`".

**Authorization.** Authenticated client; read-only; subject is fixed.

**iOS.** Yes. It is the `trainingOverview` tool.

**MVP.** Yes.

#### 7.5.2 `get_session_details`

**Input**

| Field | Type | Required | Rule |
|---|---|---|---|
| `workout_id` | string (uuid) | one of the two | exact workout id |
| `session_id` | string | one of the two | exact session id |
| `include_ratios` | boolean | no | default `false`; relative-strength ratios walk the whole lift history |

Exactly one of `workout_id`/`session_id`. Both or neither → `invalid_argument`.

**Output facts.** `session` (date, type, status, duration basis), `strength`, `dose`,
`adherence`, `vbt` (when present), `feedback` (sRPE, duration, productivity — **never notes**),
`quality`, `observation`.

**Source.** `workout.summary(conn, workout_id, include_ratios=…)` for an app workout;
`history.detail()` for an imported session with no workout row.

**Deterministic.** Yes.

**Coverage.** In-progress workout → `invalid_state` tool error (not `no_data`). Voided session →
`no_data` with the void reason.

**Imported sessions.** When the identifier resolves to a session with no workout row, the facts are
`session`, `sets` (bounded and allowlisted), `adherence` and `vbt` as status/reason only, and
`feedback`; `strength`, `dose` and `quality` are workout-only. The response reports the analysis as
unavailable instead of estimating it.

**Privacy.** `free_text` excluded: no notes field, no note parameter.

**iOS.** Yes; identical to the existing summary route, so the app may reuse its decoder.

**MVP.** Yes.

#### 7.5.3 `get_exercise_progression`

**Input**

| Field | Type | Required | Range / default |
|---|---|---|---|
| `exercise_id` | string | yes | must exist in the canonical catalogue |
| `window_days` | integer | no | 28–365, default 84 |
| `include_sessions` | boolean | no | default `false` |
| `limit_sessions` | integer | no | 1–20, default 5; ignored unless `include_sessions` |

**Output facts.** `exercise` (`id`, `display`, `pattern`, `e1rm_applicable`),
`series` (`observations`, `rolling_median`, `breaks`), `summary` (`latest`,
`change_absolute`, `change_pct`, `direction`, `n`, `gate`, `comparability`),
`sessions` (optional), `quality`.

**Source.** `features/strength_trend.observations()`, `rolling_median()`, `series_breaks()`,
`summarize()`; `features/exercise_history.history()` for sessions; `features/e1rm_source.py`
for the source rule.

**Deterministic.** Yes.

**Coverage.** Fewer than three observations → `status: "insufficient"` (the owning gate), with the
observations still returned. No e1RM applicability → `status: "no_data"` and
`limitations` explains why.

**Limitations.** MUST include: a calculated e1RM is not a tested maximum; decay and calibration are
not applied unless the owning service says so; a changed load basis breaks the series.

**iOS.** Yes, as `exerciseProgression`.

**MVP.** INT-2 (INT-1 ships only `get_training_overview` and `get_session_details`).

**Representative output** (synthetic; trimmed):

~~~json
{
  "intelligence_version": "1.0.0",
  "schema_version": "intelligence.envelope.v1",
  "capability": "exercise_progression",
  "status": "ok",
  "as_of": "2026-11-14",
  "period": {"start": "2026-08-22", "end": "2026-11-14", "days": 84, "weeks": 12, "timezone": "Europe/London"},
  "subject": {"athlete": "self"},
  "units": {"load": "kg", "velocity": "m/s", "duration": "min"},
  "facts": {
    "exercise": {
      "value": {"id": "bench_press", "display": "Bench Press", "pattern": "horizontal_push", "e1rm_applicable": true},
      "basis": "observed",
      "method": "strength_coach.features.exercise_history.history",
      "evidence_ids": []
    },
    "summary": {
      "value": {"latest": 102.5, "change_absolute": 2.5, "change_pct": 2.5, "direction": "up", "n": 6},
      "basis": "derived",
      "method": "strength_coach.features.strength_trend.summarize",
      "unit": "kg",
      "n": 6,
      "gate": "signal",
      "comparability": "comparable",
      "evidence_ids": ["ev:1a2b…"]
    }
  },
  "evidence": [{"evidence_id": "ev:1a2b…", "evidence_version": "2.0.0", "source": "strength_trend.e1rm", "source_ids": ["901", "903"], "window": {"start": "2026-08-22", "end": "2026-11-14"}, "value": 102.5, "unit": "kg", "n": 6, "comparability": "comparable", "gate": "signal", "quality_flags": [], "method_versions": {"strength_trend": "1"}, "limitations": ["formula e1RM; not a tested maximum"], "rule_ids": ["DEC-E1RM-SOURCE-01"], "assumption_ids": []}],
  "observations": [],
  "coverage": {"observations": 6, "sessions_with_the_lift": 5, "window_days": 84},
  "missing": [],
  "limitations": ["A calculated e1RM is not a tested maximum.", "Load-basis changes break the series."],
  "quality_flags": [],
  "privacy": {"class": "performance", "excluded_fields": ["notes"], "redactions": []},
  "provenance": {"services": [{"module": "strength_coach.features.strength_trend", "version": "1.4.1"}], "config_revision": "sha256:…", "database_revision": 4711, "builder_version": "context.v1", "context_hash": "sha256:…"},
  "generated_at": "2026-11-14T09:12:03Z"
}
~~~

#### 7.5.4 `get_readiness_history`

**Input**

| Field | Type | Required | Rule |
|---|---|---|---|
| `from` | string (date) | yes | inclusive start |
| `to` | string (date) | yes | inclusive end; `from` ≤ `to`; span ≤ 366 days |
| `fields` | array of enum | no | default `["score"]`; the enum is generated from `strength_coach.utils.readiness.READINESS_FIELDS` plus `score`; unknown names rejected |

**Output facts.** `points` (observed entries only, one object per date with the requested fields and
their sources), `score_series` (when `score` requested; derived by the server), `coverage`
(`observed_days`, `window_days`, `missing_days`), `sources`.

**Source.** `queries.readiness_series()` for observations; `features/readiness_score.py` for the
score. No fill, no interpolation, no imputation.

**Deterministic.** Yes.

**Privacy.** `health` class. Default `["score"]` only; raw HRV/RHR/bodyweight require an explicit
request and the caller's disclosure. The tool MUST refuse `fields` containing a value the deployment
has marked excluded.

**iOS.** Yes, as `readinessStatus` (score and coverage only by default).

**MVP.** INT-2, restricted to `["score"]` by default.

#### 7.5.5 `get_adherence_analysis`

**Input.** `weeks` (1–52, default 8), `as_of`, `group_by` (`week|month`, default `week`),
`exercise_id` (optional), `session_type` (optional).

**Output facts.** `totals`, `periods`, `exercise_comparison`, `exclusions` (reason → count),
`quality`. App-tracked completed workouts only; imported sessions are excluded by the owning
service and the exclusion is reported.

**Source.** `features/adherence_analytics.analytics(query)` — the query mapping is built by the
capability, the aggregation is entirely the owning module.

**Deterministic.** Yes.

**Coverage.** Reports `workouts_considered`, `prescribed_sets`, `matched_sets`, and every
`unavailable_metrics` code from the payload.

**MVP.** INT-2.

#### 7.5.6 `get_prescription`

**Input.** `prescription_id` (optional), `for_date` (optional), `include_provenance` (default
`true`). At most one identifier; neither means "latest persisted prescription at `as_of`".

**Output facts.** `prescription` (`id`, `for_date`, `session_type`, `approved_by`,
`created_at`), `items` (exercise, sets, reps, RIR, load, scheme — as stored), `modifiers`
(rule ids, reason codes), `warnings`, `unknown_inputs`, `rule_ids`, `provenance_links`.

**Source.** The append-only `prescription`/`prescription_item`/`prescription_modifier` rows via
`prescribe/persistence.py`; `features/prescription_provenance.extract()` for the decision trace.

**Deterministic.** Yes. **It explains nothing**; it returns the facts an explanation would cite.

**Coverage.** No persisted prescription in the window → `no_data`. A forecast is not a
prescription; the tool MUST NOT return an unstarted plan as if it were persisted (the existing iOS
rule that an issued plan is a preview applies).

**MVP.** INT-2.

#### 7.5.7 `get_vbt_analysis`

**Input.** `from`/`to` **or** `window_days` (28–365, default 84); `exercise_id` optional.
Providing both a window and explicit dates → `invalid_argument`.

**Output facts.** `cohorts` (target, load basis, sets, residuals, band), `weekly`,
`drift`, `gates`, `abstentions` (reason per cohort).

**Source.** `features/vbt_performance.analyse()` only.

**Deterministic.** Yes.

**Coverage.** VBT is sparse: `status: "insufficient"` is the normal answer, and every abstention
reason is returned verbatim. No fallback estimate is invented.

**iOS.** Limited (the native report does not render it); not an iOS tool.

**MVP.** INT-2.

#### 7.5.8 `get_programme_block_summary`

**Purpose.** Summarise the current **reporting window** of the rolling programme. There is no stored
training block (`DEC-PROGRAMME-01`) and no planned-session calendar (`DEC-W7-01`); the name is
retained for catalogue familiarity and the limitation is mandatory.

**Input.** `as_of` (optional), `block_weeks` (`4`, `6` or `8`, default 4).

**Output facts.** `window`, `cycle` (DUP rotation and week position), `deload` (scheduled and
reactive state, reasons), `volume_budget` (target, exemptions, completed, projection, feasibility),
`regime` (main-lift/substitute counts and review status), `breaks`, `attendance`.

**Source.** `settings_profile` effective period, `features/deload.py`,
`features/regime_change.detect()`, `prescribe/volume_budget.py`, `features/breaks.py`,
`features/attendance.summary()`.

**Deterministic.** Yes.

**Limitations (mandatory).** "No stored training block exists; this is a reporting window derived
from the current settings profile and the rolling programme forecast (DEC-PROGRAMME-01,
DEC-W7-01)."

**MVP.** INT-2.

#### 7.5.9 `compare_training_periods`

**Input.** `period_a` and `period_b`, each `{start, end}` (each ≤ 366 days); `metric` enum
`attendance|adherence|volume|strength_direction`; `exercise_id` required when
`metric = strength_direction`; optional `group_by`.

**Output facts.** `metric`, `a`, `b`, `delta` (`absolute`, `pct`), `comparability` per
period, `caveats`.

**Source.** The owning module for the chosen metric. A metric without an authoritative implementation
MUST NOT be added to the enum.

**Deterministic.** Yes.

**Limitation.** Two windows over the same single-athlete data are descriptive; a difference is not a
treatment effect (`LIM-26`). The envelope MUST say so.

**MVP.** INT-2.

#### 7.5.10 `get_weekly_review`

**Purpose.** The deterministic package for one Monday–Sunday week: what happened, what changed, what
the data cannot say.

**Input.** `week_end` (date; the week containing it is Monday–Sunday; default the most recently
completed week), `include_observations` (default `true`).

**Output facts.** `activity`, `adherence`, `sessions`, `progression` (tracked lifts),
`volume`, `readiness` (coverage and trend unless the caller requests values), `programme`
(deload, regime, breaks), `observations`, `quality`.

**Source.** Composition only: `attendance`, `adherence_analytics`, `history.list_sessions`,
`strength_trend`, `volume`, `readiness`, `deload`/`regime_change`/`breaks`,
`observations`.

**Deterministic.** Yes.

**Coverage.** Empty week → `no_data` with `missing` listing the expected inputs. A partially
measured week reports which sections are unavailable rather than zero.

**iOS.** Yes, as `weeklyReview`.

**MVP.** INT-3.

**Representative output** (synthetic, trimmed to the fact keys):

~~~json
{
  "intelligence_version": "1.0.0",
  "schema_version": "intelligence.envelope.v1",
  "capability": "weekly_review",
  "status": "ok",
  "as_of": "2026-11-14",
  "period": {"start": "2026-11-09", "end": "2026-11-15", "days": 7, "weeks": 1, "timezone": "Europe/London"},
  "subject": {"athlete": "self"},
  "units": {"load": "kg", "velocity": "m/s", "duration": "min"},
  "facts": {
    "activity": {"value": {"completed_sessions": 3, "target_sessions": 4, "working_sets": 41}, "basis": "derived", "method": "strength_coach.features.attendance.summary", "evidence_ids": ["ev:aa…"]},
    "adherence": {"value": {"final_plan_ratio": 0.86, "missing_sets": 3, "extra_sets": 1}, "basis": "derived", "method": "strength_coach.features.adherence_analytics.analytics", "evidence_ids": ["ev:bb…"]},
    "progression": {"value": [{"exercise_id": "bench_press", "direction": "up", "change_pct": 2.5, "n": 6}], "basis": "derived", "method": "strength_coach.features.strength_trend.summarize", "evidence_ids": ["ev:cc…"]},
    "volume": {"value": {"status": "within_budget", "groups": []}, "basis": "derived", "method": "strength_coach.features.volume.compute", "evidence_ids": ["ev:dd…"]},
    "readiness": {"value": {"observed_days": 4, "direction": "flat"}, "basis": "derived", "method": "strength_coach.features.readiness_score.compute", "gate": "signal", "evidence_ids": ["ev:ee…"]},
    "programme": {"value": {"deload": "none_scheduled", "regime_review": "stable", "breaks": []}, "basis": "derived", "method": "strength_coach.features.deload.decision", "evidence_ids": []}
  },
  "evidence": ["…"],
  "observations": [{"family": "rir", "text": "RIR was below the prescribed band in two comparable sessions.", "gate": "signal", "n": 2, "evidence_id": "ev:ff…", "limitations": ["Descriptive only."]}],
  "coverage": {"sessions_considered": 3, "days_with_readiness": 4, "planned_sessions": "not_tracked"},
  "missing": ["no readiness entry for 2026-11-15"],
  "limitations": ["Attendance is target-based; no planned-session calendar exists (DEC-W7-01)."],
  "quality_flags": [],
  "privacy": {"class": "health", "excluded_fields": ["notes", "hrv_ms", "resting_hr_bpm"], "redactions": ["readiness values reduced to coverage and direction"]},
  "provenance": {"services": [{"module": "strength_coach.features.attendance", "version": "1.4.1"}], "config_revision": "sha256:…", "database_revision": 4711, "builder_version": "context.v1", "context_hash": "sha256:…"},
  "generated_at": "2026-11-16T07:02:11Z"
}
~~~

#### 7.5.11 Why `explain_prescription` is not a tool

`explain_prescription` was a candidate. It is rejected for v1 because:

- its useful output is prose, which is a model capability, not a deterministic fact;
- as a tool it would be non-deterministic, cost-bearing and hard to cache, breaking the read-only
  fact contract;
- the deterministic predecessor already exists as `get_prescription`, which returns the modifiers,
  warnings, unknowns and rule ids an explanation must cite.

An explanation is produced by a model over `get_prescription` (host-side for iOS, server-side in
INT-5) and must be validated for evidence references and numeric grounding.

### 7.6 Resources

Resources are compact, cacheable context the host may attach without a tool call. They are
**optional for the model to read**, small by construction, and never the only way to obtain a fact
(a tool exists for anything a decision depends on).

| URI | Payload | `ttlMs` | `cacheScope` | Privacy |
|---|---|---|---|---|
| `strength://athlete/profile` | training profile (days/week, session cap, block start, volume budget, main-lift policy) and non-injury structured constraints | 300000 | `private` | training (injuries withheld and counted) |
| `strength://programme/current` | sessions/week, session-type rotation, deload state, volume policy summary | 60000 | `private` | training |
| `strength://overview/current` | the `get_training_overview` fact set at 4 weeks, compacted | 300000 | `private` | training |

Rules:

- `resources/read` MUST return `ttlMs` and `cacheScope` (required by revision 2026-07-28) plus
  `mimeType: application/json`.
- No `resources/subscribe`; `subscribe: false`.
- A resource payload MUST be a valid envelope (same schema, smaller facts), so one decoder handles
  both.
- The profile resource MUST NOT include free text, notes, injuries or measurements. Injury
  constraints are withheld and reported only as a count. Goal, goal-rank and focus-lift fields are
  retired (`DEC-STATE-02`) and are not part of the payload.
- The resource payload is a valid envelope with `capability: athlete_profile`; it is not a
  registered tool and cannot be invoked as one.

### 7.7 Prompts

None. `prompts` is not advertised. Prompt text belongs to the host or the server-side model layer,
is versioned there, and must not be discoverable as protocol content.

### 7.8 Error semantics

| Code | Transport | When | Model-visible message |
|---|---|---|---|
| `invalid_argument` | `isError` result | type/range/enum failure after schema, unknown field combination, both/neither identifiers | names the field and the allowed range |
| `not_found` | `isError` result | unknown exercise/session/workout/prescription id | names the identifier, no internals |
| `invalid_state` | `isError` result | in-progress workout, unconsumed plan requested as a prescription | states the state and the next valid action |
| `unavailable` | `isError` result | capability disabled by config, data source unavailable | states what is unavailable |
| `internal` | `isError` result | unexpected exception | fixed text only; traceback stays in the server log |
| `401` / `403` | HTTP | missing/invalid/revoked token | none (no JSON-RPC parse) |
| `-32601` | JSON-RPC | unknown tool | standard |
| `-32602` | JSON-RPC | malformed params / unknown resource | standard |
| `-32022` | JSON-RPC | unsupported protocol version | standard, lists supported versions |

A tool MUST NOT return a successful result to signal an execution failure. A tool MUST NOT return an
error for "no data"; that is `status: "no_data"`.

### 7.9 Limits

| Limit | Value |
|---|---|
| Request body | 256 KiB |
| Tool result | 1 MiB serialised |
| Window | 400 days maximum, per tool as specified |
| Sessions per page | 20 |
| Observability rows per tool | 2 |
| Concurrency | 4 |
| Rate | 60 calls/minute per token |
| Timeout | 20 s |
| Open transaction | one read transaction per call; no transaction survives the call |

Exceeding a result limit truncates deterministically and records it in `coverage.truncated` and
`missing`. Silent truncation is a defect.

## 8. Taxonomies

- `exercise_id` MUST be a canonical catalogue id; the tool returns the canonical id and display
  name, never a free-text exercise name.
- Session types, patterns and volume groups use the server's existing vocabularies; the contract does
  not define a parallel list.
- `metric` values in `compare_training_periods` are exactly the four listed; adding one requires
  an authoritative implementation and a contract revision.

## 9. REST adapter (iOS)

- Base: `/api/ios/v1/intelligence/`, existing device bearer token, existing error envelope,
  existing idempotency rules do not apply (all reads).
- Routes (INT-3 onward):
  - `GET /api/ios/v1/intelligence/weekly-review?week_end=YYYY-MM-DD`
  - `GET /api/ios/v1/intelligence/overview?as_of=&window_weeks=`
  - `GET /api/ios/v1/intelligence/exercises/{id}/progression?window_days=`
  - `GET /api/ios/v1/intelligence/readiness?from=&to=&fields=`
- Every route returns the envelope unchanged. No route returns a partial or re-shaped payload.
- Capability advertisement: `bootstrap.capabilities` gains `intelligence_read: true` only when the
  routes exist, so an older server and a newer app negotiate explicitly.
- The routes are additive; no existing route changes shape.

## 10. iOS native adapter

- `StrengthCore/Intelligence/IntelligenceEnvelope.swift` MUST decode the envelope with unknown-field
  tolerance and MUST fail decoding on a missing required field.
- `IntelligenceCapabilityProviding` exposes exactly five capabilities: `trainingOverview`,
  `exerciseProgression`, `weeklyReview`, `sessionDetails`, `readinessStatus`.
- Foundation Models `Tool` implementations MUST return a **compact text projection** (one to three
  short paragraphs, or a small JSON object) and MUST NOT return the whole envelope.
- The projection MUST preserve: the fact name, the value, the unit, the gate where present, and a
  short limitation. It MUST omit: evidence arrays, provenance internals, database revisions.
- No Swift code may compute a metric, a delta, a percentage, a gate or an evidence id. A derived
  comparison MUST come from `compare_training_periods` or a fact block.
- Numeric formatting is presentation only (rounding for display) and MUST be lossless enough that the
  grounding validator still matches the value.
- The narrative output type (`@Generable`) MUST cap: one headline (≤ 120 characters), 2–4
  observations (each ≤ 240 characters), one limitation (≤ 160 characters).
- The app MUST show `status`, `coverage` and `limitations` even when a narrative is present.

## 11. Conformance fixtures and test obligations

Synthetic fixtures, committed in both repositories (no personal data), one per capability:

~~~text
fixtures/intelligence/
  overview.ok.json
  overview.no_data.json
  progression.insufficient.json
  session.ok.json
  readiness.score_only.json
  weekly_review.ok.json
  weekly_review.empty.json
  errors.invalid_argument.json
~~~

Each fixture contains the request, the database seed description (synthetic), the expected envelope
with `generated_at` and revision fields normalised, and the expected tool error where applicable.

Obligations:

1. The backend MUST validate every fixture against the envelope schema in CI.
2. The iOS test target MUST decode every fixture and fail on drift.
3. The MCP transport test MUST produce the same envelope as the in-process client for each fixture.
4. A capability MUST NOT pass with a fact whose `method` is unregistered.
5. A tool MUST NOT pass a schema test without `outputSchema`, annotations and a read-only hint.
6. A regression test MUST fail if a new tool name contains a mutating verb (`create`, `update`,
   `delete`, `set`, `start`, `complete`, `apply`).

## 12. Change control

- Adding a tool: new name, new contract section, MVP/phase assignment, tests, and a plan update.
- Changing an input in a breaking way: new tool name; the old one is deprecated with a planned
  removal date.
- Changing a fact's semantics: major `intelligence_version` bump, contract revision, iOS fixture
  update.
- Changing the envelope: new `schema_version` and a migration note for both clients.
- Any change that would require a write, a model call inside a tool, or an unauthenticated route is
  **out of contract** and needs a new decision, not a revision.

## Related

- [Training Intelligence plan](../plans/TRAINING-INTELLIGENCE.md)
- [Implementation audit](../plans/TRAINING-INTELLIGENCE-AUDIT.md)
- [Architecture decision records](../decisions/TRAINING-INTELLIGENCE-ADR.md)
- [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)
- [MCP tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [MCP authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- [Backend API reference](https://github.com/georgesdib/strength-training-app/blob/development/docs/API.md)
