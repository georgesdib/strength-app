# ATHLETE FEEDBACK AND COACHING (AFC) — PLAN

**Canonical location:** this file, in the portfolio repository. The backend `docs/AFC.md` is a
compatibility pointer and is not authoritative.

**Status:** AFC-2, AFC-2i, AFC-3 and AFC-4 are implemented 2026-11-13; physical iPhone acceptance
of the AFC-2i report is pending. AFC-5 is scoped (docs only) and remains separate and gated.

documentation only beyond AFC-2 — no runtime behaviour, prompt, API, schema, dependency or
training-rule change is included in this plan.
**Roadmap workstream:** [ROADMAP §4.33](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md).
**Owner:** the athlete. AFC-2i, AFC-3 and AFC-4 are implemented; any further scope and AFC-5
require explicit approval before implementation.
**Scope:** composition over the backend services in section 2, rendered by the server's browser
UI and, from AFC-2i, by the native iOS client. AFC-2 itself is backend and web UI only; AFC-2i
adds iPhone presentation of the same report and no calculation, capture or prescription change
anywhere.

This is a plan, not a claim that any described interface or capability exists. The current
implementation remains the source of truth until a phase is implemented and tested.

## 1. Purpose

AFC turns training, adherence, VBT, readiness and performance data that the server already
computes into reliable, evidence-linked and actionable feedback.

The principles are fixed:

- deterministic calculations remain authoritative;
- feedback is traceable to the actual underlying rows;
- missing data is reported as unknown, never as poor performance or poor adherence;
- observations are distinguished from hypotheses;
- nudges are supportive and non-punitive;
- initial functionality never changes a prescription;
- existing services are reused rather than reimplemented;
- the web UI consumes backend-generated metrics and observations;
- the native iOS client, from AFC-2i, renders the same report contract the web end screen renders
  and computes no metric, gate or eligibility itself;
- the same architecture can later supply an LLM without letting it calculate authoritative
  metrics.

**Relationship to the critique rubric.** The deterministic critique rubric is retired
(`DEC-EVAL-08` dormant, `DEC-EVAL-09` removed from the runtime): no session is scored any more,
and the end screen no longer offers a review step. AFC is canonical for what the athlete sees
after a session, and RIR effort and session duration — the rubric's only athlete-relevant items —
are computed here from `adherence` and `feedback`. Historical `critique`, `rubric_score` and
`rubric_mark` rows and the read-only `GET /api/review/<session>` sheet are retained for audit;
nothing recomputes or extends them.

## 2. What already exists

AFC is a composition layer. Every one of these is implemented and tested today:

| Capability | Owner |
|---|---|
| Per-set reps/load/RIR attainment, set completion, plan-change inventory, attribution loss | `strength_coach/adherence.py` |
| Multi-week adherence aggregation with coverage and exclusion reasons | `strength_coach/features/adherence_analytics.py` |
| Target-based attendance (`completed / (target × weeks)`) | `strength_coach/features/attendance.py` |
| Weekly set-volume targets per movement pattern with a tolerance band and exemptions | `strength_coach/prescribe/volume_budget.py`, `config/volume.v1.yaml` |
| Declared breaks (append-only range, cancellable) | `strength_coach/features/breaks.py` |
| Per-set VBT residual, band membership and comparability | `strength_coach/features/vbt_analysis.py` |
| Longitudinal VBT cohorts, weekly residuals, bootstrap CI, within-set drift, evidence gates | `strength_coach/features/vbt_performance.py` |
| Evidence gate vocabulary (`insufficient`, `signal`, `evaluation`) | `strength_coach/features/residual.py` |
| Readiness-reduction follow-up with explicit warnings and a small-sample guard | `strength_coach/features/readiness_feedback.py` |
| Session RPE, duration, productivity and notes | `strength_coach/features/session_feedback.py` |
| Descriptive monitoring analysis with a version and a database fingerprint | `strength_coach/features/monitoring_analysis.py` |
| Multi-source completed-workout payload | `strength_coach/workout.py` `summary()` |

The completed-workout payload already composes completion, strength, dose, special exposure,
feedback, ratios, comparison, adherence, VBT, quality and basis. AFC-2 does not need a new
calculation; it needs an evidence contract and a presentation surface.

Attendance is already rendered in Progress with the correct framing ("not a calendar",
"No planned-session calendar is stored", `web/static/progress.js`). AFC must not restate or
re-derive it.

## 3. What AFC does not do

Out of scope, permanently or until a separate approved decision:

- **Planned-session compliance.** `DEC-W7-01` stands: attendance is target-based and no
  planned-session calendar is stored. There is no eligible-session denominator, no "missed"
  session and no planned-vs-completed rate. `LIM-05` records this and is unchanged.
- **Prescription adaptation.** AFC-5 is a separate, gated initiative and does not block
  AFC-1 to AFC-4.
- **Prescription nudges.** A "nudge" in AFC is informative only. The completion-based volume nudge
  discussed in [`FREQUENCY-AND-VOLUME.md`](https://github.com/georgesdib/strength-training-app/blob/development/docs/FREQUENCY-AND-VOLUME.md) would change a prescription
  and remains training-engine scope, not AFC.
- **Native iOS or watchOS calculation.** AFC-2i renders the AFC-2 report on the iPhone; it adds
  no Swift calculation, no new capture, no watchOS report and no change to any endpoint's
  contract. AFC-2 itself remains backend and web UI only, and no AFC phase moves training
  authority out of Python.
- **Cardio, VBT calibration and training-engine scope.** They generate metrics but keep their
  own ownership, acceptance criteria and roadmap sections.
- **Changing any Phase 5A instrument** (see section 5).
- **Reimplementing any metric** owned by a module in section 2.

## 4. Decisions taken

| Ref | Decision |
|---|---|
| AFC scope | AFC composes existing services and adds no second calculation of a metric another module owns |
| Naming | Target-based attendance is never labelled "adherence"; it is "training frequency vs target" |
| Q1 | Nudge state reuses the append-only `maintenance_review` pattern; observation lifecycle justifies its own small table |
| Q2 | Per-workout observations render on the end screen, longitudinal observations in Progress, and at most one nudge on Today expressed as a review category |
| Q3 | `summary.completion` is removed; `adherence` becomes the single metric source; `comparison` is retained only as the pre-materialisation display contract and is never a metric source |
| Q4 | The "stagnation" observation is deferred; it is re-asked when AFC-3's second cut is scoped, and its definition must be written before any number is generated |
| Q5 | AFC-3 first cut: repeated RIR deviation, repeated incomplete work, VBT residual deviation. "Improving performance at stable effort" and stagnation are deferred |
| Q6 | No global observation gate; each family inherits its existing owner (VBT uses the residual gates; adherence uses the analytics display guard) |
| Q7 | CLI parity for the read-only observation report; no CLI for nudge rendering |
| Q8 | Snooze 14 days, permanent dismissal per `nudge_key` and window, at most one nudge per surface per day |
| Q9 | A declared break may be annotated beside attendance as a footnote; the percentage and denominator are unchanged |
| AFC-2i | The AFC-2 report is one cross-platform contract: the web end screen and the native iOS client render the same `workout.summary()` payload, and neither derives a metric, ratio, gate, comparability verdict or observation locally (`DEC-AFC-03`) |

## 5. Phase 5A protection

Phase 5A (2026-10-30 to 2027-01-22) is active. AFC is read-only composition and must not change
any value the validation reads, or any behaviour that produces those values.

Frozen until the 2027-01-22 gate:

- `attendance.summary` output: `target` and `pct` are unchanged. A declared break affects the
  DUP cycle and the deload clock only (`DEC-CONTINUITY-04`, `DEC-CONTINUITY-05`); it does not
  alter the attendance denominator.
- `features/prospective.py` thresholds, including the `ATTENDANCE_LOW` cut at 60 per cent.
- Monitoring, exposure, calibration and relationship configuration, and the hardcoded
  `features/residual.py` gates.
- The end-screen capture controls for session RPE, duration, productivity and "not recorded".
  This is a data-capture surface: `session_feedback` feeds `prospective.py` and
  `monitoring_analysis.py`, so changing where or how prominently those controls appear would
  change what the validation collects. No test can detect that.
- `workout.get` payload shape, because `prospective.py` consumes it.

Required before any AFC code merges:

1. a golden fixture of `prospective.report` captured from the last pre-AFC commit, committed
   and asserted equal;
2. an assertion that the locked configuration groups' `config_inventory.revision()` is
   unchanged;
3. a test that `features/prospective.py` does not consume `workout.summary`.

AFC-2 may extend `workout.summary()` and `summary.js`; `summary()` has exactly two consumers
(`web/server.py`, `cli.py`) and no feature module reads it.

## 6. Evidence contract

One module, `strength_coach/features/evidence.py`, owned jointly with the LLM workstream. It
is a serialiser, not a calculator. It generalises the shape `vbt_performance` already emits
per cohort (`set_ids`, `method_versions`, `calibration_ids`, `target_sources`, `reasons`,
`gate`, `reason`).

Each evidence item carries:

- a deterministic `evidence_id` derived from source, source rows and window;
- `source` and `source_ids` (the rows actually used);
- the analysis `window`;
- `value` and `unit`;
- `n` and the comparability verdict;
- `gate`, using the existing `insufficient` / `signal` / `evaluation` vocabulary;
- quality flags copied from the owning service;
- `method_versions` and `calibration_ids`;
- explicit `limitations`;
- `rule_ids` and `assumption_ids`.

Rules:

- a changed window or a changed input row changes the id;
- an observation without evidence is allowed only when labelled as interpretation;
- the UI can expand a claim to its evidence;
- no consumer computes a metric to build an evidence item.

`docs/LLM-INTEGRATION-PLAN.md` section 4 defines the same schema for the future
`AthleteContextBuilder`. There is one schema. The builder consumes AFC evidence; it does not
recalculate adherence, VBT, readiness or volume.

## 7. Phases

### AFC-0.5 — documentation consolidation (this commit)

Documentation only. Collapses the old ROADMAP section 4.23 into AFC-1 and AFC-4, creates this
document, records the decisions, and cross-references the LLM workstream. No code, no schema.

### AFC-1 — programme KPIs (dissolved)

AFC-1 does not survive as a phase. Attendance is already computed, rendered and correctly
labelled; weekly set-volume attainment already exists in the volume budget. The planned-session
part is out of scope by `DEC-W7-01`. The remaining items move:

- the programme-level KPI panel becomes part of AFC-4;
- abandoned attempts are **excluded from AFC reporting**. Abandonment is reachable by a web
  button, an iOS route and an automatic 24-hour idle sweep (`config/ios.v1.yaml`), so it is not a
  dependable signal of athlete intent. No `session` row is written, sets logged before the
  abandon never reach `clean_set`, and the status is execution-only. AFC treats it as neither a
  missed session nor a failure, and adds no coverage counter for it.

### AFC-2 — post-workout feedback report

**Status: completed 2026-11-13** (`2d0fc15`, merged to `development`), including the
three Phase 5A guards. This scope is frozen: AFC-2i is a separate presentation phase and does not
reopen it. AFC-3 and AFC-4 remain planned.

Scope: compose `workout.summary()` into observations with evidence, render them on the end
screen, fix the quality block, and remove the duplicate set-count source.

Work:

- remove `summary.completion`;
- mark `workout._comparison` as the pre-materialisation display contract only;
- repoint `features/readiness_feedback.py` `_adherence` from `original_comparison` to
  `adherence.analyse`, because it is a completed-workout metric and currently uses the weaker
  engine;
- populate `summary.quality.flags` from `adherence.quality` and `vbt.quality` (it is
  currently a hardcoded empty list);
- render adherence and quality on the end screen, from `final_plan` for the primary table and
  `original` when the plan was modified.

No schema change.

**What shipped.** The delivered implementation added the evidence envelope, populated
`quality.flags` and rendered adherence and data quality on the end screen. It did not add a
per-workout observation record: the payload carries evidence items and quality flags, and no
"observation" object exists to render (section 9). Recording that here does not reopen AFC-2.

### AFC-2i — native post-workout feedback report

**Status: implemented 2026-11-13; physical iPhone acceptance pending.** The backend exposes a
transport-only facade and the iPhone renders the same payload read-only. It depends on AFC-2 and
the report contract AFC-2 delivered; it does not depend on AFC-3 or AFC-4 and does not reopen
AFC-2.

**Purpose.** Expose the completed AFC-2 report in the native iOS workout completion experience, so
the athlete reads the same evidence-linked report the web end screen shows, without a browser. It
is a concise report, not an analytics dashboard and not a Progress replacement.

**Dependency on the delivered contract.** AFC-2i consumes, and adds no field to:

- `GET /api/workout/<id>/summary` (`strength_coach/workout.py` `summary()`), the canonical
  completed-workout payload: `adherence` (`original`, `final_plan`, `changes`, `quality`),
  `vbt`, `feedback`, `quality.flags`, `quality.coverage` and `evidence`;
- `GET /api/ios/v1/workouts/<id>/summary` — the transport-only facade added for the iPhone
  (unknown 404, in-progress 409), returning that payload unchanged;
- the evidence envelope `strength_coach/features/evidence.py` (`evidence_id`, `source`,
  `source_ids`, `window`, `value`, `n`, `comparability`, `gate`, `quality_flags`,
  `method_versions`, `calibration_ids`, `limitations`, `rule_ids`, `assumption_ids`);
- the calculations and interpretations owned by `adherence.py`, `vbt_analysis.py`,
  `session_feedback.py` and the other services in section 2.

The payload is documented in [`docs/API.md`](https://github.com/georgesdib/strength-training-app/blob/development/docs/API.md) under "Prescription adherence" and in
section 6 above.

**Scope.**

| Area | Renders from the payload | Must not do |
|---|---|---|
| Workout completion | `adherence.final_plan` (`original` too when `plan_modified`): `set_completion` numerator, denominator and ratio, missing and extra sets, `changes`, `unattributable_planned_sets`, and `quality` (unmatched, ambiguous, removed) | Recompute a ratio, label incomplete work as athlete failure, or drop an unattributable denominator |
| Effort / RIR | `adherence` repetition, load and RIR attainment; `quality.sets_without_rir`; `quality.unavailable_metrics` | Recalculate RIR adherence, or turn the backend interpretation into a pass/fail |
| Velocity | `vbt` `status`, `reason`, `quality.target_sets`/`comparable_sets`/`excluded_sets`, `target_metadata`, and the matching `evidence` items (`gate`, `comparability`) | Decide comparability, eligibility or validity in Swift |
| Coaching observation | At most one observation, and only if the payload carries an eligible one | Manufacture an observation, or borrow AFC-3/AFC-4 behaviour |
| Session feedback | `feedback` `srpe`, `duration_min`, `duration_source`, `session_load_au`, `session_load_status`, `productivity` | Treat a missing value as zero, or collapse "not recorded" and "unavailable" into one state |
| Data quality | `quality.flags` (`code`, `detail`) and `evidence[].limitations` | Map a code to a client-side severity, or hide a flag on a small screen |

**The per-workout observation (decided 2026-11-13).** `workout.summary()` now carries at most
one deterministic `observation` — the strongest qualifying family among RIR deviation,
unperformed prescribed slots and velocity sets outside the calibration band — always with the
evidence envelope, or `null` when nothing qualifies (`DEC-AFC-08`). The web end screen renders it, and the iPhone report now renders it too
(`7afde09`): a **What stood out** section with gate, sample size and limitations, absent when the
server sends none. Nothing is synthesised client-side. AFC-3's longitudinal observations remain a
separate report.

**Navigation.** The report is reached from the existing finish flow
(`POST /api/ios/v1/workouts/<id>/complete`), which keeps its current contract:

- present the report only after the completion is acknowledged, reusing the existing idempotency
  key and finish lock so a retry cannot submit the workout twice;
- dismissing returns to the surface the athlete came from; the completed workout stays reachable
  from History, which is also the return path for reading a report later;
- a report read failure after a successful completion retries the *read*, never the completion, and
  never traps the athlete in the flow;
- the report is read-only: no control changes a load, set, rep or prescription.

**Exclusions.** No new backend metric, field, endpoint contract, schema, migration, capture
control, Phase 5A instrument, configuration value, prescription rule or LLM call. No watchOS
report. No web redesign. No dependency on AFC-3, AFC-4 or AFC-5. No re-derivation of adherence,
attendance, volume, VBT, ratios or gates in Swift, including "just for layout" totals.

**Acceptance criteria.**

1. The screen renders the AFC-2 payload fields above for a completed workout, and every displayed
   value exists in that payload; a recorded contract fixture decoded by the client fails the build
   or test if the view needs a field the payload does not carry.
2. `status: unavailable` cases (`no_prescription_snapshot`, `session_voided`,
   `no_prescription_items`, `vbt_unavailable`) render as an explicit reason, not a zero, a dash
   read as poor performance, or an empty chart.
3. Missing, excluded and low-quality data carry the payload's own wording; each `quality.flags`
   entry is shown with its `detail`; no flag is reworded into a client judgement.
4. No client-side calculation of adherence, attendance, volume, VBT, ratios, gates or eligibility:
   review of the diff finds no arithmetic over report fields.
5. When the payload contains no eligible observation, no coaching message appears and no empty
   placeholder implies one is missing.
6. The finish flow issues exactly one completion request; the report opens after acknowledgement,
   and dismissing it never re-submits and never loses the completed workout.
7. Read failures and offline behaviour follow the existing client pattern (bounded retry, idempotent
   read, no duplicate completion), and the athlete can always leave the flow.
8. Existing completion behaviour — idempotency lock, ambiguous-response handling, History
   visibility — is unchanged and still covered by its current tests.
9. Native UI tests cover: the full report, unavailable/excluded data, an absent observation, and
   completion → report → dismiss.
10. Report correctness stays backend-owned: `tests/test_adherence.py`, `tests/test_evidence.py`,
    the summary API tests and the Phase 5A guards remain authoritative; the client adds no
    expected-value arithmetic.

**As implemented (2026-11-13).**

- **Transport resolved.** The backend added the transport-only facade
  `GET /api/ios/v1/workouts/<id>/summary` (`9e85865`), returning `workout.summary()` unchanged;
  unknown id 404, in-progress 409. `workout.summary()` itself was not extended, so the
  per-workout observation decision stays open.
- **Client.** The iPhone opens the report after an acknowledged completion and reopens it from
  History; the view is read-only, shows adherence, VBT, feedback, quality flags and evidence, and
  renders unavailable data with its reason. No client arithmetic, no coaching observation, and no
  second completion request (`00eda49`).
- **Verification.** 289 iOS unit tests pass and the report navigation build succeeds; the backend
  `test_ios_api` covers the facade plus 404/409; `docs` consistency and `ruff` pass.
- **Outstanding.** Physical iPhone acceptance of the report and its offline/retry behaviour is
  still owner-run and unchecked in `DEVICE-ACCEPTANCE.md`.

### AFC-3 — longitudinal observations

**Status: completed 2026-11-13** (`DEC-AFC-04`, `DEC-AFC-07`). The second cut is deferred to
AFC-5 and is not part of this phase. `features/observations.py` reads the existing
`adherence` and `vbt_performance` payloads, applies `config/observations.v1.yaml` and reports to
`GET /api/observations` and `strength-coach observations`. Produced observations are appended to
the new append-only `observation` table, idempotent on the evidence id; abstentions are returned
with a reason and never stored. Excluded sessions — imported, abandoned, technique, voided and
adherence-unavailable — are counted per category and surfaced in `abstain`, so a thin sample is
explained rather than silent. No metric is recomputed and `workout.summary()` is unchanged. The
second cut is deferred to AFC-5.

Scope: a read-only observation service over AFC-2's evidence contract.

First cut only: repeated RIR deviation, repeated incomplete work, VBT residual deviation.
Deferred to AFC-5: "improving performance with stable effort" (no joint model exists) and
stagnation (no agreed definition).

Rules:

- no observation below its family's existing minimum;
- `insufficient` produces an abstention with a reason, never a value;
- a non-comparable input suppresses the observation and is listed in `abstain`;
- no causal language and no diagnosis;
- observations are descriptive and never change a prescription.

**Scoping decisions (2026-11-13, approved).**

- **First cut only.** The three families above are the whole phase. "Improving performance with
  stable effort" and stagnation stay out; the second cut is a separate decision, not part of this
  phase. Anything added later needs its definition written before a number is generated.
- **"Repeated" is 3 of the last 5 comparable sessions inside an 8-week window.** Those values live
  in `config/` with a recorded assumption, never as literals in code. They are new configuration,
  not a Phase 5A instrument, and changing them later is a decision, not a tuning knob.
- **Persistence.** A new append-only observation table stores identity, window, gate, `n` and the
  evidence id, written when observations are requested and idempotent on `evidence_id`. No
  backfill: a historical session simply has no stored observation until one is requested, and an
  observation is never rewritten.
- **Surfaces.** The web (Progress, with AFC-4) and a read-only CLI report (Q7). `workout.summary()`
  is unchanged in this phase; the single per-workout observation contract is decided at AFC-2i's
  kickoff.
- **Eligibility.** Imported sessions without a prescription snapshot, abandoned attempts,
  technique sessions and voided sessions are non-comparable: they appear in `abstain` with a
  reason and can never produce a value. Incomplete work is judged against `final_plan`, with
  `original` shown beside it when the plan was modified.

### AFC-4 — web UI coaching and nudges

**Status: implemented 2026-11-13** (`DEC-AFC-05`). Today promotes at most one AFC-3 observation
as a review category with the gate, sample size, evidence id and its limitations; dismiss and
14-day snooze are append-only `maintenance_review` rows. Progress carries the programme-KPI
panel (target-based attendance, volume patterns, summed adherence, observation count) and the
AFC-3 observations. No notification channel, no new metric and no prescription effect.

Scope: extend existing hosts only. No new tab.

- Progress carries the programme-level panel and longitudinal observations;
- the end screen carries the per-workout report;
- Today carries at most one nudge, expressed as a review category rather than a competing list;
- one shared nudge component with expandable trigger and evidence;
- suppression uses the `maintenance_review` pattern: snooze 14 days, permanent dismissal per
  key and window, at most one nudge per surface per day.

### AFC-5 — evidence-gated prescription adaptation (separate)

**Status: scoped 2026-11-13 (`DEC-AFC-09`); not implemented, no code.** Not part of AFC-1 to
AFC-4 and not a dependency of them. It also owns the deferred AFC-3 second cut — stagnation and
"improving performance with stable effort".

- AFC-5a historical evaluation of adaptation candidates;
- AFC-5b prospective shadow proposals;
- AFC-5c narrow, user-approved prescription changes.

**Levers in scope.** Only two: external load within the current prescription's intent, and set
count within the existing volume policy. Out of scope: exercise selection or rotation, deload
timing, session type, RIR target changes, and anything a Phase 5A instrument reads. No new data
capture.

**AFC-5a — historical evaluation (design and analysis only).** A counterfactual over stored
sessions with a single named outcome: the e1RM trend at stable effort. Pre-registered before any
number is inspected: a 12-week window, at least 20 comparable sessions, and success/failure
criteria written in advance. It produces a report, never a proposal, and it may start now because
it changes nothing.

**Stagnation definition (inherited from AFC-3, written before use).** A lift is stagnant when its
e1RM shows no positive trend over 12 weeks while median RIR stayed inside the engine's tolerance,
with at least 8 comparable sessions. Fewer sessions or an effort drift means *unknown*, never
stagnant. The definition is fixed here and is not retuned after seeing output.

**Safety gate for AFC-5b/5c.** Written into `DECISIONS.md` before any proposal is generated, and
satisfied only with shadow-only evidence: a four-week shadow period, a rollback rule, per-change
explicit athlete approval, and no automatic application. AFC-5b may show proposals only after
the gate is declared satisfied; AFC-5c is limited to the two levers above and to narrow,
approved changes.

**Timing.** Until the Phase 5A review on 2027-01-22 only design and AFC-5a historical analysis are
allowed. Shadow proposals, any user-visible surface, and any prescription change wait until after
that gate and the separate safety gate.

**Out of scope permanently.** Automatic adaptation, a learned policy that writes prescriptions,
selection/rotation changes, deload-timing changes, and any adaptation justified only by a
correlation.

## 8. Sequence

Documentation consolidation (AFC-0.5) → AFC-2 (completed) → AFC-2i (implemented) → AFC-3
(completed) → AFC-4 (implemented) → AFC-5 (scoped, separate and gated).

AFC-1 is dissolved and is not a step. AFC-2 came first because it needed no schema, no decision
change and no new calculation, and because it produces the evidence contract AFC-3, AFC-4 and
LLM Iteration 1 phase 2 all consume. AFC-2i follows AFC-2 immediately because it is pure
presentation of that delivered contract; it is independent of AFC-3 and AFC-4 and may ship before,
beside or after them, but never before AFC-2.

## 9. Open items

- **Stagnation definition (written 2026-11-13, unused).** The definition is fixed in AFC-5 above:
  no positive e1RM trend over 12 weeks at median RIR within tolerance, with at least 8 comparable
  sessions; otherwise *unknown*. It must not be retuned after seeing output, and no number has
  been produced under it yet.
- **Per-workout observation (closed 2026-11-13, native rendering pending).** The decision is
  taken: `workout.summary()` carries one deterministic, evidence-wrapped observation
  (`DEC-AFC-08`). The backend, web end screen and iPhone report render it; no client may
  synthesise or reword it.
- **Interpretation caveat for the gate.** A declared break depresses `attendance.pct` and can
  raise `ATTENDANCE_LOW` in the Phase 5A read-out. This is expected behaviour under
  `DEC-W7-01`, not a defect. Note it when reading the 2027-01-22 review.

## 10. Related

- [ROADMAP](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md) section 4.33 — roadmap summary of this plan.
- [LLM-INTEGRATION-PLAN.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/LLM-INTEGRATION-PLAN.md) — the shared context and evidence layer.
- [API.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/API.md) "Prescription adherence" — the completed-workout summary payload and its
  stable fields.
- [DECISIONS.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/DECISIONS.md) — `DEC-W7-01`, `DEC-AFC-01`, `DEC-AFC-02`, `DEC-AFC-03`.
- [iOS client plan](IOS-CLIENT-PLAN.md)
  — the shared iOS phase plan AFC-2i's client work would sit beside (cross-repository, portfolio
  canonical).
- [LIMITATIONS-REGISTER.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/LIMITATIONS-REGISTER.md) — `LIM-05`, unchanged.
