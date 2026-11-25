# READINESS METRIC REGISTRY — PLAN

**Status:** **implemented 2026-11-25** on the backend `readiness-registry` branch, WP1–WP6;
**WP8 (real-data comparison and release checklist) is pending.** The owner approved the plan and
all five decisions below. Canonical location: this file, in the portfolio repository.
**Decision owner:** the athlete.
**Related:** [READINESS-SCORE.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/READINESS-SCORE.md),
[API.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/API.md),
[DATA-MODEL.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/DATA-MODEL.md),
[contracts](../contracts/README.md), [LIM-37](https://github.com/georgesdib/strength-training-app/blob/development/docs/LIMITATIONS-REGISTER.md).

---

## 1. Problem

The global readiness score is a **gate**: it can move a load and cut sets. Its inputs, weights,
direction, scale and minimum-field rule are hard-coded in `features/readiness_score.py` and
`utils/readiness.py`:

- five subjective fields (sleep, energy, mood, stress, soreness), 1-5, normalised `value / 5`,
  weight 1.0;
- HRV and RHR only with a 28-day baseline (>= 7 readings), mapped by a 0.5 slope, half weight;
- an optional wearable score blended at 10%;
- at least three core fields, and sleep or energy must be among them;
- category overrides, manual overrides and the injury ceiling applied after the score.

Adding or retiring a daily input therefore needs code, tests and a release. The roadmap lists the
idea in section 6; `LIM-37` closed `metric_definition` as a measurements catalogue, not a live
readiness driver. This plan makes the readiness side a versioned registry without changing the
score in release one.

## 2. Goal

One append-only, date-effective registry of readiness inputs, editable through Settings and the CLI,
with strict validation, history and a preview. **Release one reproduces today's score exactly**
(golden equivalence). Any later change to weights or inputs is a registry edit plus a decision, not
a code change.

## 3. Non-goals

- No new daily inputs shipped now; the registry is seeded with today's eight inputs.
- No change to per-lift readiness, the injury ceiling, category overrides, factor bands or any
  prescription behaviour.
- No iOS dynamic form in this workstream: the iPhone readiness screen is a separate MacBook
  session. The backend contract is built for it.
- No multi-user, auth or per-user isolation.

## 4. Storage

New table `readiness_registry` (additive migration):

```sql
CREATE TABLE readiness_registry (
    registry_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    effective_from  TEXT    NOT NULL,
    schema_version  INTEGER NOT NULL,
    payload_json    TEXT    NOT NULL,
    note            TEXT,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX idx_readiness_registry_effective
    ON readiness_registry(effective_from, registry_id);
-- append-only triggers: no UPDATE, no DELETE
```

Effective registry for a date = the latest row with `effective_from <= date` (the
`settings_profile` semantic). The migration seeds **version 1, effective 1970-01-01**, containing
today's defaults, so historical prescriptions resolve to the same inputs they used.

Payload (validated in code, never trusted). Label, scale and direction live in
`metric_definition`, so the registry carries only the operational fields:

```json
{
  "schema_version": 1,
  "min_core_fields": 3,
  "require_any_of": ["sleep", "energy"],
  "wearable_weight": 0.10,
  "metrics": [
    {"key": "sleep",    "role": "core",   "enabled": true, "weight": 1.0,
     "baseline_days": 0,  "counts_as_core": true,  "order": 1},
    {"key": "energy",   "role": "core",   "enabled": true, "weight": 1.0,
     "baseline_days": 0,  "counts_as_core": true,  "order": 2},
    {"key": "mood",     "role": "core",   "enabled": true, "weight": 1.0,
     "baseline_days": 0,  "counts_as_core": true,  "order": 3},
    {"key": "stress",   "role": "core",   "enabled": true, "weight": 1.0,
     "baseline_days": 0,  "counts_as_core": true,  "order": 4},
    {"key": "soreness", "role": "core",   "enabled": true, "weight": 1.0,
     "baseline_days": 0,  "counts_as_core": true,  "order": 5},
    {"key": "hrv_ms",   "role": "device", "enabled": true, "weight": 0.5,
     "baseline_days": 28, "counts_as_core": false, "min_readings": 7,
     "slope": 0.5, "order": 6},
    {"key": "rhr_bpm",  "role": "device", "enabled": true, "weight": 0.5,
     "baseline_days": 28, "counts_as_core": false, "min_readings": 7,
     "slope": 0.5, "order": 7}
  ]
}
```

A metric key must exist in `metric_definition` (label, scale, unit, direction); a new input
therefore needs a catalogue row **and** a registry row. Free-text keys are rejected.

## 5. Editing and versioning

- A save appends a new row with `effective_from = today` (no backdating in release one) and an
  optional note; there is no in-place update, enforced by triggers.
- "Rollback" appends a new version whose payload copies an older one; history is never rewritten.
- Legal edits: enable/disable a metric, change its weight (0-2), change its baseline window and
  minimum readings, and change `min_core_fields` / `require_any_of` within the enabled core set.
- Validation rejects: unknown keys, disabled fields still referenced, fewer enabled core metrics
  than `min_core_fields`, `require_any_of` outside the enabled core set, weights outside 0-2,
  missing direction/scale, wearable weight outside 0-0.5, and a schema version the code does not
  know.

## 6. Score engine

`readiness_score` loads the effective registry and builds components generically:

- **core** metrics: linear map from `scale` to 0-1, weight from the registry;
- **device** metrics: existing baseline-ratio transform with the registry's window, minimum
  readings and slope;
- weighted mean of components (no renormalisation when a metric is missing, matching today),
  wearable blend at the registry weight;
- unchanged afterwards: manual/category override precedence, injury ceiling, factor bands,
  status rules.

`utils/readiness.validate` becomes date-aware so only enabled registry metrics are accepted.
`readiness_setting` currently carries `baseline_days`, `hrv_slope`, `rhr_slope`,
`hrv_weight`, `rhr_weight`, `wearable_weight`; those move into the registry and the old
endpoint/UI fields are removed (breaking change, accepted).

## 7. API

- `GET /api/readiness/schema?date=` (web) and `GET /api/ios/v1/readiness/schema` (bearer auth)
  return: registry version, effective date, metrics (key, label, scale, direction, role, required,
  order, enabled), `min_core_fields`, `require_any_of`, wearable weight.
- `POST /api/readiness` and `POST /api/ios/v1/readiness` keep their `{date, values, note}`
  shape; validation follows the effective registry, so new fields need no new payload shape.
- Readiness responses gain `registry_version` and the schema list is the source for forms.
- No backward-compatibility shim is required; the read/schema endpoints are additive, and the only
  removed surface is the old readiness-settings fields.

## 8. Surfaces

- **Web:** the readiness form is rendered from the schema (labels, scale, required marker, order,
  enabled set); presets, context flags and the score panel are unchanged. Settings gains
  **Readiness inputs**: edit weights/enabled/baseline/min fields with inline validation, a
  preview of today's score using the draft payload, and a Save that appends a version. History and
  rollback lists are read-only.
- **CLI:** `readiness registry list|show|set|history|preview`, matching the Settings operations
  and validation (CLI/UI parity rule).
- **iOS:** out of scope here; the schema endpoint is the contract for the separate session.

## 9. Migration, deployment, rollback

- One additive migration (table, triggers, seed). Old code ignores the table, so the schema is
  forward-compatible during a staged deploy.
- The worktree has no `data/`; the production database is never migrated in development. At
  release: verify backup, apply migration, deploy. Rollback = deploy the previous release; the
  table is inert.
- No score changes in release one, so no shadow period is required. A read-only comparison runs
  against a copy of the real database before release.

## 10. Acceptance criteria

1. Seeded registry reproduces the current score **exactly** (status, score, components, basis) on a
   fixture matrix: all fields, each missing, HRV/RHR with and without baseline, wearable on/off,
   three-field boundary, sleep-or-energy boundary, injury ceiling, category and manual overrides,
   unknown/insufficient.
2. The same comparison passes on a read-only copy of the real database for a set of dates.
3. Append-only triggers, date-effective selection and history/rollback are tested.
4. Invalid payloads are rejected with field-specific errors; valid edits create a new version and
   do not change past dates.
5. Web form is schema-driven; CLI and Settings perform identical operations; parity tests pass.
6. `check.sh` fast lane and full suite pass; docs consistency and manifest tests pass.
7. No behaviour change to per-lift readiness, injury ceiling, category overrides, factor bands or
   prescriptions in release one.

## 11. Work packages

| WP | Content | Status |
|---|---|---|
| WP0 | Plan approval (this document) | approved 2026-11-25 |
| WP1 | Migration, table, triggers, seed defaults, store queries, migration tests | done (`18a0230`) |
| WP2 | Registry model, payload validation, effective-version selection, CLI | done (`dfb078d`) |
| WP3 | Score-engine refactor, `validate` by date, equivalence harness and fixtures | done (`c7b7189`); 19-scenario golden fixture bit-exact |
| WP4 | Schema endpoint (web and iOS), response version, API tests | done (`01771b5`) |
| WP5 | Schema-driven web readiness form | done (`e19fb7f`) |
| WP6 | Settings panel: edit, preview, history; remove the old settings surface | done (`a542a30`) |
| WP7 | Docs: READINESS-SCORE, API, DATA-MODEL, UI-MAP, LIM-37, decisions, this plan; portfolio index | done with this status update |
| WP8 | Verification: real-data comparison on a copy, full suite, release checklist | pending |

iOS dynamic form: separate plan and session (MacBook), using the schema endpoint.

### Implementation record

- **Breaking changes, accepted:** `POST /api/readiness/settings`, the `readiness settings` CLI
action/flags, the `readiness_setting` overlay, the `settings` block in readiness payloads and the
old panel are removed. `readiness_setting` rows remain as history but nothing writes them
(`DEC-READINESS-21`).
- **Equivalence:** the golden fixture was captured from the pre-registry engine before the
refactor and still passes: status, score, components, normalised values, weights, basis,
overrides, category factors, flags and suppression.
- **Scores are unchanged** by the seeded version; the registry is the only source for inputs,
weights and the minimum-field rule.

## 12. Risks

- **The score is a gate.** Any drift changes loads; the equivalence harness and the "no edits in
  release one" rule are the guard.
- **Two sources of truth.** Moving the old readiness-settings fields into the registry must remove
  the old UI/endpoint in the same release, not leave both.
- **JSON without typing.** Payload validation is the only guard; it needs its own test matrix and
  cannot be bypassed by the Settings/CLI writers.
- **Silent future change.** A saved version applies to future dates; the preview, note and history
  make the change explicit, and there is no backdating.
- **iOS lag.** New fields are invisible to the shipped app until the iOS session ships; existing
  fields keep working. A coordinated release is preferable.
- **Migration on the production database.** Additive only, backup first, never run from the
  worktree.

## 13. Decisions (approved 2026-11-25)

1. **Yes** — slopes and `min_readings` move into the registry, one source per metric.
2. **Yes** — the old readiness-settings API, CLI, overlay, payload block and panel are removed in
   this branch rather than kept read-only.
3. **Yes** — a metric key must exist in `metric_definition`; no free-text keys.
4. **Yes** — `effective_from` defaults to today and the API/CLI reject backdating.
5. **Yes, with role-aware bounds:** core 0.05–2.0, device 0.05–1.0, wearable blend 0–0.5. Zero is
   not a weight; disabling is the off switch. The bounds stop one input from dominating a gate.
6. **No backward compatibility and no kill switch** — the server and iPhone must ship together, and
   rollback is a deploy.
