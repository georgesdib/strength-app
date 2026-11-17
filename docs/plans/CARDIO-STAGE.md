# CARDIO STAGE — HEALTHKIT INGESTION AND CARDIOVASCULAR MONITORING

**Canonical location:** this file, in the portfolio repository. It is the cross-repository plan for
HealthKit ingestion, cardio analytics and the monitoring dashboards. Component implementation
documentation remains in its owning repository.

**Status:** proposed 2026-11-17. C0 (the measured audit) is complete — see
[CARDIO-C0-AUDIT.md](CARDIO-C0-AUDIT.md), which corrected several decisions in this plan. Nothing else is
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
5. **Cardiovascular, mechanical and resistance exposure stay separate as exposures.** No combined
   fatigue scalar, and no session is counted twice for the same minutes. This is a bookkeeping rule,
   not a claim about physiology: a resistance session can be cardiovascular, and classification
   follows the evidence (`DEC-CARDIO-05`).
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

**Not claimed by this decision.** That a strength session cannot be cardiovascular. Classification
follows the evidence (`DEC-CARDIO-05`): a resistance session that holds a sustained aerobic intensity
produces aerobic minutes like any other, while still never entering strength volume, tonnage or set
counts.

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

### DEC-CARDIO-05 — A cascade: Apple's METs, then heart rate, then unclassified

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

**Decision — the cascade, fixed now.** Per workout, in order:

1. `HKMetadataKeyAverageMETs` where Apple supplies it; Apple's value is authoritative and is never
   re-derived or "corrected" by us;
2. otherwise `%HRmax` from the athlete's observed maximum of 200 bpm, using heart-rate statistics where
   present and the series otherwise;
3. otherwise `unclassified`.

`WHO-equivalent minutes = moderate + 2 × vigorous`, computed over classified minutes only, with the
unclassified balance reported separately.

**Resistance work is not excluded.** A strength session that sustains an aerobic intensity produces
aerobic minutes like any other workout, and its minutes are counted. What it never does is enter
strength volume, tonnage or set counts — the separation in principle 5 is about double counting, not
about physiology. Preferring Apple's figure for lifting is the more conservative choice anyway: heart
rate overstates aerobic intensity during resistance work because of the pressor response, so a raw
`%HRmax` reading there is an upper bound.

**Coverage, measured.** The cascade classifies 1,298 of 1,431 workouts (90.7 %): 970 by METs, 328 by
heart rate, 133 unclassified. Pre-2021 is better than assumed — 230 of the 312 workouts in 2016–2020
carry heart rate written by **RunGap** from a non-Apple sensor, so those years are mostly classifiable
even without a watch.

**Accepting Apple's values has a price, stated once.** Apple's workout METs are its own model, and
Apple's exercise minutes begin only in 2021 (zero records before). When Apple changes that model, the
series steps and the step is not auditable from our side. Every value therefore stores the vendor and
the tier that produced it, and no value is silently recomputed.

**Consequences.** C2/C3 store the inputs and no verdict: METs, heart-rate series, pace, distance and
Apple exercise minutes. `unclassified` stays a first-class value and never zero. Flipping the method
later is a `method_version` bump (`DEC-CARDIO-12`), not a migration. No VO₂max estimator is introduced
(`DEC-CARDIO-10`).

### DEC-CARDIO-06 — Standalone metrics go where the backend already keeps them; no new metric table

**Decision.** No `health_metric` table. Each standalone metric uses the store the backend already
designed for its meaning:

| Metric | Store | Why there |
|---|---|---|
| VO₂max (Apple and third-party) | `measurement`, `metric_key = 'vo2max'`, `source = 'device'` | A periodic outcome that must never change a prescription. The definition already exists with direction, unit and aggregation declared |
| Resting HR, HRV, body weight | `healthkit_readiness` | Daily state that can gate a load (Phase 3A, unchanged) |
| Apple exercise minutes | cardio corpus, daily series | Neither state nor periodic outcome; a daily activity quantity (deferred to C5) |

`measurement.method` is what keeps protocols apart: "Apple Watch estimate" and "Athlytic" are separate
values in one column, which is the table's stated purpose — comparing two protocols as one series is a
silent data error. VO₂max is labelled *Apple's estimate* in every surface, never a measurement.

**Two additive columns.** `measurement` has a uuid primary key and no natural uniqueness, so a re-run
would duplicate 399 VO₂max rows silently: C3 adds `external_id TEXT` with a partial unique index
(`WHERE external_id IS NOT NULL`, the `high_intensity_exposure` pattern) and a nullable `measured_at`
for the sample timestamp. Additive, no existing row touched, readiness path untouched.

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

**Decision.** One identity column, filled from whichever source produced the row: the HealthKit object
UUID when the row came from the app, and a deterministic `sha256` content key — activity, start, end,
source bundle, duration — when it came from the export, which carries no sample UUIDs. Never
device-scoped, unlike the readiness table.

**Consequences.** A re-paired device or a second iPhone re-uploads the same workouts idempotently, and
history promoted from a file stays idempotent on re-run. The two regimes never meet, because
`DEC-CARDIO-18` splits the timeline rather than letting them overlap (§C1b, §C2).

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

### DEC-CARDIO-17 — `cardio-policy/v3` is the only source of import and retention values

**Decision.** The values C2–C5 read — whitelist, measurement classes, retention, quality gates, import
range, link bands — live in [CARDIO-C1-POLICY.md](CARDIO-C1-POLICY.md) and change only by version bump
with the audit evidence that forced the change. A threshold that exists only in code is a defect.

**Consequences.** Policy changes are reviewable without reading the implementation, and a retune is a
version bump plus a rebuild rather than a migration.

### DEC-CARDIO-18 — History is promoted from the export; only new data arrives through HealthKit

**Decision.** Everything up to the export's own cutoff is promoted offline from `export.xml`; everything
after it arrives through the app's HealthKit queries. The app never performs the historical backfill.
The cutoff is not a date someone chooses: promotion records `history_cutoff` = the maximum sample
timestamp in the file, and incremental sync queries `start > history_cutoff` with a 7-day lookback,
deduplicated on `DEC-CARDIO-09` identity.

**Rationale.** Ten years of resumable, retryable backfill through a phone is the least testable part of
the connector, and the data is already on the machine and already verified by C0. Splitting the
timeline by construction also keeps the two identity regimes (content key, UUID) from ever having to
reconcile.

**Consequences.** History is fixed: a gap needs a fresh export, not a backfill re-run, and deletions in
the history are undetectable. The lookback window covers samples that land with older timestamps after
the cutoff — a late-syncing device, not a policy edge case.

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
| — | No standalone metric table: VO₂max lives in `measurement`, readiness state in `healthkit_readiness` (`DEC-CARDIO-06`) |
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

**Status:** complete 2026-11-17 — [CARDIO-C1-POLICY.md](CARDIO-C1-POLICY.md), `cardio-policy/v3`.

The policy fixes, with the audit's numbers behind each: modality whitelist (nine analytics modalities,
everything else import-only by default); measurement classification into mandatory, optional, deferred
and ignored; heart-rate retention (in-workout only, full resolution, background dropped); standalone
metric source rules and display minimums; per-metric data-quality gates including the 5-minute floor
that removes 44 micro-workouts from totals; import range, order and resumability; and the numeric link
bands from `DEC-CARDIO-02`/`DEC-CARDIO-13`.

**Acceptance — met.** Every item is a named, versioned artefact in one document. Nothing is left
implicit in code. Where the audit could not settle a value, the policy states the rule that settles it
later (a policy bump or a `method_version` bump), rather than a placeholder.

### C1b — History promotion from the export (offline)

**Scope.** A one-time, re-runnable, CLI-only promotion of `export.xml` through the canonical model, under
`cardio-policy`. Not an endpoint, not part of the app, not reachable from the network. Runs where the
file is — this machine or the server — and records `history_cutoff` on completion.

**Acceptance.** Re-running the promotion produces no duplicates and no changes; `history_cutoff` is
recorded and exported for C2; the promoted count matches the audit (1,431 workouts, ≈546 k in-workout
and tail samples); nothing outside the whitelist is classified; a second run after a fresh export is
additive only.

### C2 — iOS HealthKit connector (new data only)

**Status:** implemented and accepted on the iPhone 2026-11-17. Settings → Recorded activity → *Sync
workouts and heart rate*; consent prompts for Workouts and Heart Rate separately; the first sync
uploaded one post-cutoff session (36 min, 437 samples) that the linker queued at 0.76 interval
overlap and which was then linked manually.

Three defects were found by the device pass and fixed the same day: the endpoint rejected the
phone's 16-byte UUID keys (guard written for the export's 32-byte digests); the client applied the
seven-day lookback to workouts, duplicating three pre-cutoff sessions and forcing a corpus rebuild
(`0066`); and the sync cursor advanced to "now", hiding a workout that ended before the sync ran.

**Not wired yet:** deletion events (the endpoint exists, the client does not send them), and METs for
phone-uploaded workouts, so new ones classify by heart rate.


Extend read authorisation to workouts, workout routes, HR, HRV, resting HR, VO₂max, body mass, active
energy, distance, power and exercise minutes. The phone usage description already covers that full
scope (owner decision 2026-11-17); the authorisation request and the re-consent path land here, and a
scope that was never granted is never silently extended. Anchored incremental queries from
`history_cutoff` with a 7-day lookback, for workouts **and** heart-rate samples separately so recovery
tails arrive separately; deletion and change handling emitting status events rather than deletes;
visible coverage.

**Acceptance.** Incremental sync is idempotent on HealthKit UUID; no confirmed-absent record is
silently deleted; no duplicate appears after re-pair; a recovery tail arriving in a later sync attaches
to its workout; records before `history_cutoff` are never re-uploaded; authorisation denied is
representable and never rendered as zero activity.

### C3 — Canonical model and promotion

**Status:** complete 2026-11-17 — **deployed to the main server**: backup
`coach-pre-0064-20261117T195520.db`, schema 0064 applied, export promoted, service restarted and
answering. The production corpus holds 1,430 workouts, 599,927 samples and 400 VO₂max rows (399
imported plus the 1 manual row that already existed), cutoff `2026-11-17T17:49:23Z`, `quick_check` ok,
240 MB.

The server checkout is 13 commits behind `development`: the migration, store module and CLI were
copied in for the backfill and removed afterwards, so the working tree stayed clean. The recorded
migration checksum came from the committed file, so the next fast-forward deploy matches it and
`db.migrate` stays a no-op.

Migration `0064_cardio_corpus`, the store module and the offline promotion CLI are on `development`. Promotion of the real export into a scratch database produced
1,430 workouts (1,431 seen — one export duplicate collapsed on identical key), 599,927 samples
(560,167 in-workout, 39,760 tail), 399 VO₂max rows with the Apple/Athlytic split preserved, and
`history_cutoff = 2026-11-17T17:49:23Z`; a second run created nothing. Not applied to the production
database.

**Storage:** the first promotion produced 263 MB, not the ≈65 MB estimated in C0 — the 64-character
hex identity keys and their indexes dominated. Keys are now stored as the 32-byte digest, which
measured 222 MB — under the policy's 250 MB trigger, so no retention change is needed. The remaining
31 MB of `idx_health_sample_kind` is left in place until C5 shows whether any metric reads samples
without going through a workout.

Extend the Phase 3A ingestion idiom. Promote from staging under the C1 rule. Times in UTC with source
offset retained; canonical units; original activity type retained; provenance on every row; raw
observations separate from derived aggregates; indexes for the 7-day, 28-day and per-workout access
paths. Plus the two additive `measurement` columns that make a VO₂max import idempotent
(`DEC-CARDIO-06`).

**Acceptance.** Promotion is re-runnable and deterministic; the same staging data always yields the
same canonical rows; append-only triggers hold; a re-run adds no duplicate `measurement` row; `cardio_log`,
the readiness path and existing `measurement` rows are unchanged.

### C4 — Linking and the reconciliation queue

**Status:** applied and resolved on the main server 2026-11-17. **322 sessions linked** — 315
`day_containment`, 3 `interval_overlap` (overlaps 0.97–1.00), 4 `manual` — 378 sessions unchanged,
`quick_check` ok, a second run finding nothing to link.

The queue was resolved by hand the same day. Three days held two strength workouts each; every pair
was a 1–7 minute watch start/stop artefact beside the real 41–52 minute session, so the real workout
was linked and the artefact left unlinked. The fourth was a measured session whose workout overlapped
at 0.80, just under the auto threshold. Deliberately left unlinked: the four short artefacts, and one
65-minute Bevel workout on a day whose only session is a **one-second** measured session at 07:29 — a
session-side artefact, not a cardio one, and worth a separate look.

Remaining: 56 sessions with no workout record that day, which is the honest state of a history that
predates the watch, not a queue.

**Interface (implemented).** Linking is a re-runnable backend job, never a read-time view:

```
# report what would link, by tier and method; writes nothing
python tools/cardio_link.py --db data/coach.db --dry-run

# append link events for unambiguous pairs; leave the rest queued
python tools/cardio_link.py --db data/coach.db --apply

# after the fact: unresolved queue and link counts by method
python tools/cardio_link.py --db data/coach.db --report
```

`--apply` is the only writing mode and the only mode that requires an explicit database
(`--db`, no default). Matching is restricted to strength activity types
(`TraditionalStrengthTraining`, `FunctionalStrengthTraining`); a run on the same day as a session
is not a candidate. An existing link is never modified by a later run — correcting one is an explicit
unlink (`DEC-CARDIO-02`). The day basis for tier B is the server's zone: the workout's start is
converted from its `HKTimeZone` before comparison, and the basis is recorded on the link.

The queue is surfaced as this report plus an unresolved count on the web dashboard; no review screen
until the queue is non-trivial.

Overlap matching per `DEC-CARDIO-02`, the queue surface, manual link and unlink, and the de-dup hint
for manual cardio per `DEC-CARDIO-07`. Every link records method, confidence, band version and inputs.

**Acceptance.** A link never creates a session; an explicit link is never displaced; ambiguous matches
are visible and countable; unlink restores the prior state; the queue count is shown, not buried. A
tier-B auto-link requires uniqueness on both sides (`DEC-CARDIO-13`), and every auto-link is labelled
and reversible.

### C5 — Analytics

**Status:** first slice implemented and reporting against the live corpus 2026-11-17
(`features/cardio_metrics.py`, `tools/cardio_report.py`); no dashboard yet. Cascade classification,
coverage by year, per-modality breakdown, rolling 7/28-day windows and time-in-zone are computed from
1,430 workouts and 319,980 classified minutes (**54,724 WHO-equivalent**).

Findings worth the stage: **resistance contributes 20,301 of the 54,724 equivalent minutes (37 %)**,
reported separately rather than excluded; coverage is 100 % for 2022–2024 but 0 % for 2019–2020 (no
heart rate, no METs) and 83–89 % for 2025–2026; **275 workouts pass continuity** for time-in-zone —
dense in 2016–2018 and 2026, sparse in 2019–2025, exactly as the density analysis predicted.

WHO-equivalent minutes and coverage by tier; weekly moderate/vigorous/equivalents; session counts;
duration and modality distribution; rolling 4-week, 12-week, 7-day and 28-day windows; resting HR,
VO₂max (labelled estimate), HR recovery and comparable-workload trends; descriptive cardiovascular
exposure kept separate from mechanical and resistance exposure.

**Acceptance.** Every metric names its method and inputs; fixed fixtures reproduce every value; missing
inputs produce `unclassified` or `insufficient data`, never zero; no metric mixes exposures. Every
classified minute records which tier produced it (`DEC-CARDIO-05`), and coverage is reported per year
and per modality so a change in Apple's model cannot masquerade as a change in behaviour.

### C6 — Dashboards

**Status:** web slice live 2026-11-17. `GET /api/cardio/summary?weeks=12` serves weekly activity,
rolling 7/28-day windows, per-year coverage and the resistance share from a classification cache
(migration `0065`); measured 0.11 s on the ODROID against a 0.66 s `/api/settings` baseline.

The Cardio view now carries a **Recorded activity** panel: rolling 7- and 28-day equivalents,
resistance share for the calendar year, weekly and yearly tables, and unclassified minutes printed as
their own column. It is read-only and has no controls — imported activity is not editable here. The
iOS overview and the time-in-zone chart are still to come.

**Why a cache appeared.** The first endpoint version recomputed classification per request and took
~4 s, because classifying a workout falls back to the mean of its heart-rate series. `0065` stores
one classification row per workout and is rebuilt from source whenever the corpus grows, so the only
slow request is the first after an import. The cache is disposable by design and carries no
append-only triggers — a cache that cannot be rewritten is a second source of truth.

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
| 0 | C0 spike and audit | Six questions answered with figures — **done 2026-11-17** |
| 1 | C1 decisions and versioned policy | Bands and tiers fixed; whitelist declared — **done 2026-11-17** |
| 2 | C3 canonical model | Append-only intact; identity column per `DEC-CARDIO-09` |
| 3 | C1b history promotion | Re-run is a no-op; `history_cutoff` recorded |
| 4 | C2 connector, incremental only | Idempotent; tails attach late; nothing before the cutoff |
| 5 | C4 linking and queue | Bands reproduce; unlink works |
| 6 | C5 analytics | Fixtures reproduce; unclassified ≠ 0 |
| 7 | C6 dashboards | Web/iOS agree |
| 8 | C7 hardening | Guard test passes; performance at audited volume |

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
- **O-5** *Closed.* Apple exercise minutes exist for 71 k records but only from 2021, so they are a
  cross-check on post-2021 totals and not a history-long baseline.
- **O-6** *Closed.* The method is the cascade in `DEC-CARDIO-05`; nothing is deferred to C5.

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
- [C1 policy](CARDIO-C1-POLICY.md) — `cardio-policy/v3`, the values the implementation reads
- [Plan index](README.md) ·
  [iOS client phase plan](IOS-CLIENT-PLAN.md) ·
  [Athlete Feedback & Coaching](AFC.md) ·
  [Training Intelligence](TRAINING-INTELLIGENCE.md)
- Canonical contracts: [contract index](../contracts/README.md)
- Backend roadmap: [ROADMAP §4.13](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md)
