# CARDIO STAGE — HEALTHKIT INGESTION AND CARDIOVASCULAR MONITORING

**Canonical location:** this file, in the portfolio repository. It is the cross-repository plan for
HealthKit ingestion, cardio analytics and the monitoring dashboards. Component implementation
documentation remains in its owning repository.

**Status:** proposed 2026-11-17. C0 (the measured audit) is complete — see
[CARDIO-C0-AUDIT.md](CARDIO-C0-AUDIT.md), which corrected three decisions in this plan. Nothing else is
implemented: C1 to C7 are gated on the C1 decision record, and no runtime behaviour, API, schema,
dependency, contract or training rule changes until a workstream is implemented and tested.

**Roadmap workstream:** [ROADMAP §4.13a](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md)
(v1.6, cardio depth). This plan delivers its A0/A1 evidence and defers A2/A3 — see
[DEC-CARDIO-08](#dec-cardio-08--413a-a2a3-is-deferred-not-superseded) and §11.

**Owner:** the athlete. Every decision in §4 was taken 2026-11-17.

**Autonomy:** monitor and report only. No automatic cardio prescription, no strength-programme
modification, no training-load adjustment, no unified fatigue score.

**Primary objective:** long-term cardiovascular health and longevity, with strength-training
recovery preserved. Not competitive endurance performance and not maximising VO₂max at the expense
of strength development.

## 1. Purpose

Give the athlete a reliable, auditable record of everything HealthKit knows about their physical
activity and cardiovascular fitness, enrich — never duplicate or rewrite — the existing strength
history, and report it in a form that is honest about data quality.

The stage exists because the backend currently has no view of physical activity outside the gym:
`cardio_log` is manual and rarely used, and HealthKit contributes only HRV, resting HR and body
mass to readiness. The largest untapped signal is the athlete's own Apple Watch workouts.

## 2. What already exists

This section is a precondition, not background. Every item was verified in the repositories on
2026-11-17; the plan's shape follows from them.

| Existing thing | Where | Why it constrains the plan |
|---|---|---|
| `cardio_log` — manual cardio, append-only, `UPDATE`/`DELETE` refused by trigger | `store/migrations/0011_cardio_log.sql` | A second cardio history will exist. It is not migrated and not merged (§4, DEC-CARDIO-07). |
| Phase 3A HealthKit observation ingestion: sample identity, immutable-field conflict → HTTP 409, source class/bundle/model, append-only | `store/healthkit_readiness.py`, `web/server.py`, migrations `0054`/`0055` | The ingestion idiom already exists. The new work extends it; it does not invent a second one. |
| Device-scoped uniqueness `UNIQUE (device_id, field, sample_id)` | `migrations/0054_healthkit_readiness.sql` | Correct for readiness, wrong for workouts: re-pairing or a second device would duplicate them. |
| `high_intensity_exposure` with `UNIQUE (source, source_id)` and `supersedes_id` | `migrations/0024_high_intensity_exposure.sql` | Precedent for external identity plus correction-by-new-row. |
| Append-only void/unvoid event table plus derived state | `migrations/0031_session_void_vbt.sql` | The pattern deletion must follow (§4, DEC-CARDIO-04). |
| Derived-analytics layer: `analytics_revision`, `analytics_build`, `method_version`, disposable rebuildable derived rows | `migrations/0061`–`0063`, `docs/design/DERIVED-ANALYTICS-ARCHITECTURE.md` | Derived cardio metrics are a family there, not a second promotion mechanism (§4, DEC-CARDIO-12). |
| `cardio_log` holds **0 rows**; `healthkit_readiness` holds 94, all from 2026 | production database read 2026-11-17 | Manual cardio has never been used, and HealthKit reaches readiness for one year only. |
| 373 of 378 sessions have `duration_basis='unavailable'` and no timestamp; only 5 carry a measured interval | production database read 2026-11-17 | Interval overlap cannot be the primary matching signal for history (§4, DEC-CARDIO-02). |
| `workout_session` with `started_at`, `ended_at`, `duration_measured_s`, `status` | `migrations/0017_workout.sql` | Overlap matching needs only these columns; no session schema change is required to match. |
| Watch already saves every recorded strength session as an `HKWorkout`, tagged `HKMetadataKeyExternalUUID` | `StrengthWatch/WatchHealthKitAnchor.swift` | A full history import will contain the app's own strength sessions. Reconciliation is core work, not an enhancement. |
| That external UUID is the watch-local `sessionUUID`; no server column stores it | `StrengthCore/Execution/WatchSessionRecord.swift` | No exact link exists for history. Overlap matching carries the stage; an explicit link is added forward (§4, DEC-CARDIO-02 and DEC-CARDIO-11). |
| HealthKit read authorisation currently covers HRV, resting HR and body mass only | `StrengthApp/Core/HealthKitService.swift` | New read scopes, a usage-description review and a re-consent path are part of C2. |
| Single athlete; multiple paired `ios_device` rows; no `account_id` | `store/migrations/*`, `store/ios_devices.py` | "Account isolation" means device-scoped isolation plus cross-device de-duplication. |

## 3. Principles

1. **HealthKit is an external source, not a session.** A HealthKit workout is evidence about the
   world; it is not a Strength App training session and never becomes one.
2. **The backend owns canonical data and derived metrics.** The app reads HealthKit and ships
   records; iOS and the web dashboard display backend results and compute none.
3. **Six things stay distinct:** HealthKit workouts, Strength App sessions, cardio analytical
   sessions, physiological observations, and the links between them, and their provenance.
4. **Captured before modelled.** No metric is introduced before the data that feeds it is measured.
5. **Cardiovascular, mechanical and resistance exposure stay separate.** No combined fatigue scalar,
   no silent double counting.
6. **Deterministic and labelled.** Every value identifies its method and its inputs. Missing is not
   zero, and unclassified is not a category to be filled in by guesswork.
7. **Append-only survives contact with HealthKit.** Corrections, deletions and re-links are events.
8. **Observational only.** Nothing in this stage can change a load, a set, a prescription or a
   schedule, and no observation claims causation.

## 4. Decisions taken

### DEC-CARDIO-01 — HealthKit is an external source and a link never creates a session

**Decision.** Imported workouts live in their own canonical representation. Reconciliation attaches
data to an existing session or leaves the workout unlinked. No code path creates, edits, voids or
reschedules a session from HealthKit data.

**Consequences.** A bad match degrades enrichment (visible, correctable), not training history. Tests
assert that the import path has no write access to `session`, `workout_session` or prescription
tables.

### DEC-CARDIO-02 — Time-first reconciliation in two tiers, with append-only links

**Decision.** Match on time, and say which method produced the link. Two tiers, because the data has
two shapes:

| Tier | Signal | Bands |
|---|---|---|
| A — interval overlap | Jaccard on `[started_at, ended_at]` vs the workout interval | ≥ 0.90 with exactly one candidate → auto-link; 0.60–0.90 → queue; < 0.60 → no link |
| B — day containment | same `occurred_on` as the workout's start date | unique on both sides → auto-link (`DEC-CARDIO-13`); ≥ 2 candidates on either side → queue, never auto |

Tier A applies to every session that has an interval: the 5 watch-recorded sessions today and every
session recorded from now on. Tier B is the only available signal for the 373 imported sessions, which
store a date and no timestamps, and it is labelled `day_containment` wherever it is shown.

The method, tier and band version are recorded on every link. Links are append-only events with
`supersedes_id`; unlink is an event; an explicit link is never superseded by an inferred one. Tier B
auto-links only under the bidirectional uniqueness rule of `DEC-CARDIO-13`.

**Alternatives rejected.** Requiring an exact shared identifier — C0 measured exactly one historically
(`DEC-CARDIO-11`). Requiring an interval for every link — that would leave 99 % of the history
permanently unlinked.

**Consequences.** The queue is a permanent, first-class surface with counts, split by tier so the
confidence mix stays visible.

### DEC-CARDIO-03 — Staging store, declared promotion rule, canonical tables hold promoted data only

**Decision.** Raw HealthKit data lands in a disposable staging store. A versioned promotion job
moves what the policy admits into canonical append-only tables. The promotion rule is declared data
(which modalities, which measurements, which retention), not code scattered through ingestion.

**Consequences.** Re-importing after a policy change never touches canonical history. Retention
choices are reversible by re-running promotion from staging. The staging store's own retention is
free.

### DEC-CARDIO-04 — Deletion is an event, never a row mutation

**Decision.** Absence from a HealthKit query creates an append-only status event (`absent_from_source`,
`source_unavailable`, `access_unconfirmed`, `partial_result`, `confirmed_deleted`). Current state is
derived in the query. Rows are never updated or deleted.

**Consequences.** No page shows imported data as missing without saying why. Reappearance emits an
event too, so a flapping source is visible rather than silent.

### DEC-CARDIO-05 — Intensity classification is provisional; the method is chosen at C5

**Amended 2026-11-17 after a concordance check that contradicted the earlier ladder.** 829 workouts
carry both Apple's `AverageMETs` and an average heart rate. Classifying each way — MET bands (light
< 3, moderate 3–6, vigorous > 6) against `%HRmax` with the observed maximum of 200 bpm (light < 64 %,
moderate 64–76 %, vigorous > 76 %) — they agree on **109 (13 %)**. Every disagreement runs the same way:
METs count the workout, heart rate calls it light (walking 414/452, strength 141/284, cycling 13/23,
swimming 14/17). Not one goes the other way.

Neither figure measures the truth. Apple's workout METs are themselves modelled from heart rate, motion
and personal data, and for resistance training they are close to a table constant. `%HRmax` is
hypersensitive to the assumed maximum: with a true maximum of 190 rather than 200, strength's average of
127 bpm moves from 64 % to 67 % and 601 classifications flip. A single observed sample is a weak anchor
for the whole denominator.

**Decided now — definitional, not empirical.** Resistance-type workouts (traditional and functional
strength training) never produce aerobic moderate or vigorous minutes under any method. WHO states the
aerobic and the muscle-strengthening recommendations separately; neither proxy can describe resistance
work, and counting it as moderate aerobic activity is a category error rather than an estimate.
Resistance work is counted as resistance exposure and nothing else.

**Deferred to C5.** For aerobic modalities no method is fixed. C5 computes the WHO-equivalent number
under at least three candidates — Apple's own exercise minutes, MET-based (pace-derived where distance
and duration exist), and `%HRmax` from an observed maximum — and reports coverage, year-on-year
stability and agreement with Apple's exercise minutes for each, before one becomes
`method_version = cardio_v1`. The chosen method is recorded as a modelling decision, not as a
conclusion the data forces.

**Consequences.** C2/C3 store the inputs and no verdict: METs, heart-rate series, pace, distance and
Apple exercise minutes. `unclassified` stays a first-class value and never zero. Flipping the method
later is a `method_version` bump (`DEC-CARDIO-12`), not a migration. No VO₂max estimator is introduced
(`DEC-CARDIO-10`).

### DEC-CARDIO-06 — Standalone physiological metrics reuse the Phase 3A convention

**Decision.** VO₂max, resting HR, HRV, body mass and Apple exercise minutes are stored as timestamped
observations using the existing sample-identity, provenance and conflict semantics. VO₂max is stored
with its source class and is labelled in every surface as *Apple's estimate*, never a measurement.

**Open detail.** `healthkit_readiness.field` is a `CHECK` constraint, so a new field needs the
table-rebuild pattern already used by `0055`. Before reusing it, confirm the readiness reader selects
named fields only; if a rebuild is unattractive, a sibling table with an identical shape and
provenance convention is acceptable, but the two must not diverge in semantics.

### DEC-CARDIO-07 — Manual cardio is preserved, not migrated, not merged

**Decision.** `cardio_log` stays exactly as it is. Imported workouts are the analytics basis. A manual
entry that overlaps an imported workout of compatible modality gets a computed de-dup hint; it is
excluded from totals only when the owner explicitly marks it as the same activity, and that mark is
append-only.

**Consequences.** One hint query and one flag. No second reconciliation engine, and no path that
deletes the athlete's own entry.

### DEC-CARDIO-08 — §4.13a A2/A3 is deferred, not superseded

**Decision.** This stage delivers the §4.13a A0 (data audit) and A1 (capture completion) evidence.
Impulse (A2) and shadow load (A3) are deferred to v1.6 proper, because the impulse is computable only
after this stage's data exists. `ROADMAP.md` §4.13a keeps its approved scope; v1.6 stays open.

**Consequences.** No "supersedes" claim is made over an approved document. The backend roadmap needs
one status line added (see §12).

### DEC-CARDIO-09 — Workout uniqueness is the HealthKit object UUID, not device-scoped

**Decision.** `UNIQUE (healthkit_uuid)` for imported workouts, deliberately unlike the readiness
table's device-scoped key.

**Consequences.** A re-paired device or a second iPhone re-uploads the same workouts idempotently.
The originating device is recorded as provenance, not as identity.

### DEC-CARDIO-10 — Deterministic metrics only

**Decision.** No proprietary VO₂max estimator, no Banister-style fitness/fatigue fit, no unified
strength/cardio score, no AI-generated programming. Apple's VO₂max estimate is imported and labelled;
it is not reproduced.

### DEC-CARDIO-11 — Forward exact link from new sessions

**Decision.** New watch-recorded sessions persist the HealthKit workout's `externalUUID` alongside the
session at creation, so future reconciliation is exact.

**C0 measured the history, and it does not repair.** The export does carry the identifier — under
`HKExternalUUID`, the raw value of `HKMetadataKeyExternalUUID` — on 27 workouts, of which exactly one
is `source_name = "StrengthApp"`. Idempotency receipts are pruned, so no server-side mapping is
recoverable. History therefore rests on `DEC-CARDIO-02`, and the forward link is the only path to exact
matching.

**Consequences.** A small contract addition in the iOS finish path; no change to how sessions are
recorded today.

### DEC-CARDIO-12 — Derived cardio metrics join the existing derived-analytics layer

**Decision.** Weekly activity, exposure and fitness-trend values are materialised as a family in the
layer that already exists (`analytics_revision`, `analytics_build`, `method_version`, disposable rows,
availability gated on a ready build) rather than through a new promotion or caching mechanism. The
staging → canonical promotion of `DEC-CARDIO-03` feeds source tables; the derived layer reads them.

**Consequences.** Cardio analytics inherit the existing rebuild, invalidation and versioning behaviour,
and a metric change is a `method_version` bump rather than a migration. The ODROID cost profile is the
one already measured for the core family.

### DEC-CARDIO-13 — Tier B auto-links when the day is unique on both sides

**Decision.** Both tiers are in scope. A session and a workout sharing a calendar day link
**automatically** when all three hold: exactly one session on that day, exactly one strength-type workout
on that day, and that workout is not already linked to another session. Anything else — two sessions,
two workouts, or an existing link — goes to the queue and links only on confirmation. Every tier-B link
records `method = day_containment`, is labelled as such wherever it is shown, and can be unlinked in one
action.

**Rationale.** C0 measured 378 sessions on 378 distinct days — no day carries two sessions — with 320
days holding exactly one strength workout. A 320-row confirmation screen would be abandoned, and an
abandoned queue enriches nothing. The bidirectional uniqueness rule is what makes automatic linking
safe: the case that would go wrong (two sessions, one workout) cannot be linked by rule, and it is the
only ambiguous case the history can produce.

**Consequences.** No review surface for the 320; a queue only for genuine ambiguity (3 days today).
Links are labelled and reversible, so a wrong one can be found and undone without auditing the set.

### DEC-CARDIO-14 — Every source is imported and labelled; none is excluded from totals

**Decision.** Workouts and samples from third-party apps (Sheiko Gold, Strongur, Strong, RunGap, JEFIT,
Athlytic, HeavySet, Bevel, Shortcuts and any future source) are imported on equal terms and displayed
with their source. Activity totals include them. No series is silently merged across sources: a
third-party estimate is labelled as such wherever it appears, including Athlytic's VO₂max.

**Consequences.** The history is complete rather than Apple-shaped. The cost is that a source change is
visible as a step in a trend — which is information, not noise, and is the honest alternative to
silently preferring Apple.

### DEC-CARDIO-15 — Activity Health recorded but StrengthApp did not is shown, read-only

**Decision.** The 55 strength workouts on days with no session (47 in 2022) appear in the activity
history, labelled as recorded in Health but never logged in StrengthApp. They never become sessions and
never enter strength volume, tonnage or set counts.

**Consequences.** The record stops being invisible without contaminating the training ledger. The same
rule covers every future external workout that has no counterpart.

### DEC-CARDIO-16 — 2021 is real training without a wearable record

**Decision.** The 40 imported 2021 sessions are taken as genuine training in a period when the watch was
not worn (HealthKit holds 3 training days that year). They are not treated as import loss, duplication
or a data-quality defect, and no reconciliation rule penalises them.

**Consequences.** Coverage reporting distinguishes "no wearable record" from "no training" — the same
distinction `DEC-CARDIO-04` makes for deletion.

## 5. What this stage does not do

Automatic cardio prescription or scheduling; automatic strength-programme changes; unified
strength/cardio fatigue scores; proprietary VO₂max estimation; AI-generated programming; automated
session scheduling or optimisation; native Watch cardio recording; individualised HR-zone
optimisation; fitness–fatigue modelling. Nothing in the stage may reduce volume, change loads or RIR,
reschedule a session, or override an injury constraint. Observations are never presented as causal.

## 6. Architecture

```
HealthKit (iPhone + Watch)          C0 spike: export.xml
        |                                   |
        | C2 upload (batched, resumable)    v
        v                            staging.sqlite (throwaway, gitignored)
  staging store  -------------------------->  promotion job (versioned rule)
                                                   |
                                                   v
                                    canonical append-only tables
                                    (external_workout, health_sample, metric,
                                     workout_link, status events, provenance)
                                                   |
                                    +--------------+--------------+
                                    v                             v
                              analytics (deterministic)     coverage/quality
                                    v                             v
                              web dashboard                 iOS overview
```

Logical entities, in the vocabulary the schema should use:

| Entity | Responsibility |
|---|---|
| `external_workout` | One imported HealthKit workout: UUID, activity type, interval, summary statistics, source provenance |
| `health_sample` | Timestamped samples (HR, power) with workout association and association confidence. Not `observation`: that name already means AFC-3 rendered observations |
| `health_metric` | Standalone observations: VO₂max, resting HR, HRV, body mass, exercise minutes |
| `workout_link` | Append-only link events between an external workout and a session, with method, confidence and `supersedes_id` |
| `external_status_event` | Append-only absence/deletion/reappearance events |
| `cardio_session` | Analytical view over an imported workout for supported modalities; never a second source of truth |

`external_workout` is deliberately not named `health_workout`: the existing `workout_session` table
already means an in-progress strength execution, and the two names will be confused otherwise.

## 7. Workstreams

### C0 — Local spike and measured audit

**Status:** complete 2026-11-17 — [CARDIO-C0-AUDIT.md](CARDIO-C0-AUDIT.md). No shipped code, no schema,
no endpoint, no migration.

Apple's own export (`Settings → Health → Export All Health Data`) was parsed with a stdlib streaming
parser into a throwaway store under `private/`, and joined read-only against the production database.

The audit answered all six questions with figures:

1. Workout inventory by activity type and year, with counts.
2. Per modality: share with HR samples, distance, active energy, `AverageMETs`, power, elevation.
3. HR sample interval distribution per modality → projected row count and bytes for full history.
4. Overlap-ratio distribution between imported workouts and existing sessions, read from a read-only
   copy of the live database → calibration of the §4 bands.
5. Whether strength workouts export `HKMetadataKeyExternalUUID`, and whether any receipt-based repair
   of historical links is viable.
6. Whether Apple exercise minutes and VO₂max samples are present, with their sources and date range.

**Acceptance — met.** Every question is answered with figures; §8 of the audit states plainly what it
does not establish. It re-checked and corrected three things: matching had to become two-tier
(`DEC-CARDIO-02`), the intensity ladder had to invert for running and cycling (`DEC-CARDIO-05`), and
the derived layer already exists (`DEC-CARDIO-12`).

### C1 — Decision record and versioned policy

Turn the audit into the versioned inputs the pipeline reads: modality whitelist (analytics) vs
import-only list; measurement classification (mandatory / optional / deferred / ignored); HR retention
and downsampling; historical range and resumability; import trigger; data-quality thresholds per
metric; final link bands. The measured basis to decide against: 546 k of 1.1 M HR samples fall inside
workout windows (≈65 MB canonical), METs exist for 99 % of walks but 8 % of runs, and 810 routes sit
unmatched.

**Acceptance.** Each item is a named, versioned artefact. Nothing is left implicit in code. The policy
is re-derivable from the audit without re-opening the debate.

### C2 — iOS HealthKit connector

Extend read authorisation to workouts, workout routes, HR, HRV, resting HR, VO₂max, body mass, active
energy, distance, power and exercise minutes. The phone usage description already covers that full
scope (owner decision 2026-11-17); the authorisation request and the re-consent path still land here,
and a scope that was never granted is never silently extended. Full historical backfill in bounded, retryable batches; anchored incremental
queries with persisted anchors; deletion and change handling emitting status events rather than
deletes; resumable progress; visible coverage.

**Acceptance.** Import resumes after interruption; repeated import is idempotent on HealthKit UUID;
no confirmed-absent record is silently deleted; no duplicate appears after re-pair; authorisation
denied is representable and never rendered as zero activity.

### C3 — Canonical model and promotion

Extend the Phase 3A ingestion idiom. Promote from staging under the C1 rule. Times in UTC with source
offset retained; canonical units; original activity type retained; provenance on every row; raw
observations separate from derived aggregates; indexes for the 7-day, 28-day and per-workout access
paths.

**Acceptance.** Promotion is re-runnable and deterministic; the same staging data always yields the
same canonical rows; append-only triggers hold; `cardio_log` and existing readiness behaviour are
unchanged.

### C4 — Linking and the reconciliation queue

Overlap matching per `DEC-CARDIO-02`, the queue surface, manual link and unlink, and the de-dup hint
for manual cardio per `DEC-CARDIO-07`. Every link records method, confidence, band version and inputs.

**Acceptance.** A link never creates a session; an explicit link is never displaced; ambiguous matches
are visible and countable; unlink restores the prior state; the queue count is shown, not buried. A
tier-B auto-link requires uniqueness on both sides (`DEC-CARDIO-13`), and every auto-link is labelled
and reversible.

### C5 — Analytics

WHO-equivalent minutes and coverage by tier; weekly moderate/vigorous/equivalents; session counts;
duration and modality distribution; rolling 4-week, 12-week, 7-day and 28-day windows; resting HR,
VO₂max (labelled estimate), HR recovery and comparable-workload trends; descriptive cardiovascular
exposure kept separate from mechanical and resistance exposure.

**Acceptance.** Every metric names its method and inputs; fixed fixtures reproduce every value; missing
inputs produce `unclassified` or `insufficient data`, never zero; no metric mixes exposures. The
intensity method is chosen here from a written three-method comparison (`DEC-CARDIO-05`), and that
comparison is part of the release evidence.

### C6 — Dashboards

Web: weekly overview, guideline progress, modality distribution, history — including Health-only
workouts labelled per `DEC-CARDIO-15` — workout detail with HR series, fitness trends, source labels per
`DEC-CARDIO-14`, coverage and synchronisation status. iOS: this week's aerobic minutes, session
count and 4-week trend; recent workouts; resting HR and VO₂max where available; recovery context;
last successful sync and coverage. Detailed charts stay on the web.

**Acceptance.** Web and iOS render identical values for the same window; both show coverage beside
each metric; neither computes a metric locally.

### C7 — Hardening and release

Backfill and resume; incremental sync; duplicate prevention under re-pair and multi-device upload;
deletion and reappearance events; linking including ambiguity; HR integrity, ordering and association
confidence; timezone and DST boundaries; partial coverage; unit normalisation; reproducibility;
web/iOS agreement; device-scoped isolation; realistic storage and query performance at the audited
volume; regression of existing strength and cardio workflows.

**Acceptance.** Every C2–C6 acceptance criterion has a test or a recorded manual verification. A guard
test asserts that no prescription, load, RIR, volume or scheduling path reads the health tables.

## 8. Sequence and gates

| Step | Content | Gate to proceed |
|---|---|---|
| 0 | C0 spike and audit | Six questions answered with figures |
| 1 | C1 decisions and versioned policy | Bands and tiers fixed; whitelist declared |
| 2 | C2 connector, backfill first | Resumable, idempotent, events not deletes |
| 3 | C3 canonical model and promotion | Promotion re-runnable; append-only intact |
| 4 | C4 linking and queue | Bands reproduce; unlink works |
| 5 | C5 analytics | Fixtures reproduce; unclassified ≠ 0 |
| 6 | C6 dashboards | Web/iOS agree |
| 7 | C7 hardening | Guard test passes; performance at audited volume |

Each gate is a stop, not a formality. A failed gate sends the work back to the previous step; it does
not proceed under a caveat.

## 9. Definition of done

1. Every workout the store returns for the granted read scopes is imported, with coverage measured
   and displayed. (Deliberately not "all workouts exist": HealthKit cannot distinguish denied read
   access from an empty result.)
2. HR and other available measurements are retained under the declared retention policy, with
   timestamps, source and association confidence.
3. Existing strength sessions are enriched without duplication, and ambiguity is visible rather than
   resolved by guessing.
4. Unmatched workouts remain in the activity history with their original classification.
5. Cardio and longevity metrics are deterministic, versioned and backend-owned.
6. Web and iOS show consistent values and consistent coverage.
7. Recovery context is available and changes no strength programming.
8. Import, promotion and linking are repeatable, resumable and auditable.
9. Provenance, coverage and data quality are visible wherever a number is shown.
10. Existing strength functionality, constraints and safety rules are intact, and a test proves the
    health tables are not read by prescription logic.

## 10. Risks and rollback

| Risk | Mitigation |
|---|---|
| Backfill writes to a live database with approvals disabled | Staging-first: the backfill writes only to staging; canonical writes are a separate, dry-run-by-default promotion pass with a re-run path |
| Wrong link enriches a session with another workout's HR | Link is an event, unlink exists, confidence and band are displayed, queue is reviewed |
| Two device uploads duplicate history | UUID-keyed uniqueness (DEC-CARDIO-09), not device-scoped |
| Storage growth beyond the home server | C0 measured volume, HR downsampling policy, staging retention independent |
| "Monitoring" drifts into advice | Separation rules in §3 and §5; guard test in C7; observations labelled with inputs and window |
| Roadmap divergence | §12 accompanying edits land with the plan, not after |

Rollback for every workstream is "delete staging, re-run promotion from source". Canonical tables are
dropped only by an explicit migration with a documented reverse, and the ODroid main server requires a
verified backup and one restore drill before the first such migration.

## 11. Open items

- **O-1** What the export actually contains (metadata, dense HR, `AverageMETs`, VO₂max coverage) —
  answered by C0, and it can invalidate C5's tier order.
- **O-2** HR retention resolution, chosen against the audited volume rather than in advance.
- **O-3** Whether staging receives upload endpoints or a file import; deferred until C0 shows whether
  the export path is sufficient for history and only incremental sync needs the app.
- **O-4** Whether historical exact links are recoverable from existing idempotency receipts; verified,
  never assumed.
- **O-5** Whether Apple exercise minutes are useful as a cross-check on classified minutes, or noise —
  partly answered: C0 found 71 k records, and `DEC-CARDIO-05` makes them one of the three candidate
  methods.
- **O-6** Which method becomes `cardio_v1` — a C5 gate, decided from the comparison `DEC-CARDIO-05`
  requires, not in advance.

## 12. Accompanying edits

Landed 2026-11-17 on task branches. Not merged into `development` and not pushed; nothing is committed
to `main`.

| Repository | Change | Commits |
|---|---|---|
| Portfolio | This plan, the plan-index entry and the documentation registration | `5e473cf`, `efc3e0c`, `6909d1b` |
| Backend | `ROADMAP.md` §4.13a status note: A0/A1 evidence is scoped here, A2/A3 stay v1.6, v1.6 stays open | `9ac0a67`, `9a9a39e` |
| iOS | `docs/README.md` index pointer, `docs/HEALTHKIT.md` (current read/write scope and privacy limits), and the widened `NSHealthShareUsageDescription` | `a2e84e6`, `359baf4`, `2c644d6`, `ded27d4` |

Links to this plan point at the portfolio `development` branch: `main` carries release pins and lags
`development`, so a `main` link would 404 until the next release merge.

`docs/HEALTHKIT.md` was the missing iOS-side reference this plan needed for C2. It describes shipped
behaviour only and records the entitlement/usage-string discrepancy C2 must resolve.

No submodule pointer update and no portfolio consolidation is part of this task. `ROADMAP.md` remains
the backend status authority and this plan does not restate its status tables.

## 13. Related

- [C0 audit](CARDIO-C0-AUDIT.md) — the measured export and matchability numbers behind this plan
- [Plan index](README.md) ·
  [iOS client phase plan](IOS-CLIENT-PLAN.md) ·
  [Athlete Feedback & Coaching](AFC.md) ·
  [Training Intelligence](TRAINING-INTELLIGENCE.md)
- Canonical contracts: [contract index](../contracts/README.md)
- Backend roadmap: [ROADMAP §4.13](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md)
