# WATCH MOTION METRICS — TEMPO, CONSISTENCY AND DEVICE VELOCITY

**Canonical location:** this file, in the portfolio repository. It is the cross-repository plan for
deriving movement metrics from Apple Watch motion sensors. Component implementation documentation
remains in its owning repository.

**Status: closed and abandoned, 2026-11-22 — a failed project.** The automatic rep segmentation and
wrist-derived velocity were abandoned after a day of testing on twelve real captures. Capture works
(raw accelerometer, gyroscope and gravity at 100 Hz, exported off the watch); **inference does not**:
on the only clip with a trustworthy label the detector found one rep where three were performed, and
no combination of rest, burst, lobe or velocity-maximum detection separated reps from racking
without ground truth to calibrate against. Working capture is not a deliverable on its own.

Nothing was deployed: no migration applied, no flag enabled, no client build shipped, no
capture-contract amendment merged. The implementation is retained, unmerged, on the branch
`watch-motion-capture-defunct` in both the backend and the iOS repository (the former
`wp3-rep-motion-capture` and `wp4-watch-motion-capture`).

This document is the historical record of an attempt, not a commitment, a backlog item or a
resume point. **Nothing in it is open or pending** — the full disposition is §0. There is no
monitoring cadence and no re-measurement date; unlike per-set heart-rate recovery (a separate,
live, display-only measurement), nothing here is expected to be revisited.

**What a future attempt would need:** labelled sets (known rep times) rather than more unlabelled
clips, or a sensor other than the wrist. The literature measures wrist mean velocity at SEE ≈
0.064 m/s against Vicon, so the placement is capable — this project's detector and evaluation were
not. Do not restart by tuning thresholds against unlabelled recordings, and do not reopen this
plan: that evidence would justify a new one.

**Owner:** the athlete.

**Autonomy:** descriptive only. These metrics are facts about a set. They must never feed a
prescription, a load, a readiness score, a progression rule or a training decision. The structural
guarantee was the module boundary in §8, not good intentions.

**Primary objective (not met, and no longer pursued):** turn the watch from a rest timer into an
honest movement recorder — rep segmentation, phase durations, consistency — without claiming
accuracy it has not demonstrated.

## 0. Closure record, 2026-11-22

Closed by the owner as a failed project. The disposition below is complete, so no part of this
document reads as pending work:

| Item | Disposition |
|---|---|
| WP0 scope and decisions (§3, §5, §7, §10, §13, D1–D16) | Historical. Design record only; none of it is in force. |
| WP1 read-only analysis (§15.4) | Completed 2026-11-22. Results retained as the evidence that closed the project. |
| WP2 capture-contract amendment (`IOS-WATCH-CONTRACT.md`) | Withdrawn 2026-11-22, never merged. The watch contract carries no motion-capture amendment and none is planned. |
| WP3 phase table, materialisation, `rep_tempo.py`, session-detail field | Abandoned, unmerged, not deployed. Retained on `watch-motion-capture-defunct` (`c0baf46`). |
| WP4 watch capture (100 Hz recorder, set stamping, debug export, ad-hoc recorder) | Abandoned, unmerged, not deployed. The physical-device check was never run. Retained on `watch-motion-capture-defunct` (`576f14e`). |
| WP5 offline segmentation and velocity (`tools/motion_segmentation.py`) | Reference implementation only, abandoned with the project. |
| WP6–WP9 pilot, validation study, promotion, shadow mode | Not started; closed with the project. |
| Branches | `watch-motion-capture-defunct` in both repositories — kept for history, never merged, not to be resumed. |
| Gates G1–G4 (§10) | Never run. No verdict exists and none is owed. |
| Residual questions (§13) | Closed as moot; see §13. |
| Follow-up | None. No owner review, no re-measurement cadence, no roadmap entry. |

One piece of knowledge is carried forward: wrist capture is feasible, wrist **inference without
labels** is not, and timing-derived analysis of any kind inherits the watch's user-tapped set
boundaries — recorded as accepted design choice `LIM-72` in the backend's
[`LIMITATIONS-REGISTER.md`](https://github.com/georgesdib/strength-training-app/blob/development/docs/LIMITATIONS-REGISTER.md)
and in [`HR-RECOVERY-PROBE.md`](https://github.com/georgesdib/strength-training-app/blob/development/docs/HR-RECOVERY-PROBE.md#L68).

## 1. Why this exists

*Historical rationale, written before the attempt. It is not current intent — see §0.*

The watch already has the sensors and the runtime session. What it does not have is a defensible
definition of what a rep is, when a phase starts, or how much a derived velocity can be trusted.
This plan supplies those definitions, the storage for them, and the evidence gates that decide what
reaches the athlete.

The sequencing is deliberate: **tempo first, velocity second.** Phase boundaries are timing
measurements at 100 Hz sampling (±10 ms) and require no integration and no load. They are also the
zero-velocity anchors that any credible velocity estimate needs for drift correction. Tempo is
therefore both the easier deliverable and the foundation of the harder one.

## 2. What already exists

Verified in the repositories on 2026-11-22. The plan's shape follows from these, not from a blank
page.

| Existing thing | Where | Why it constrains the plan |
|---|---|---|
| `clean_rep` — per-rep velocity, append-only, `UNIQUE (clean_set_id, rep_index)`, `source` in `('import','device','manual')` | `strength_coach/store/migrations/0028_rep_velocity.sql` | A device source was already anticipated. One velocity per rep, so two sources for the same rep cannot coexist here. |
| `workout_rep_event` — raw per-rep snapshots, append-only, materialised into `clean_rep` | same migration | The ingestion seam for any new per-rep field. |
| `_append_reps` normalises each rep to exactly `{rep_index, velocity_mps}` and drops unknown keys | `strength_coach/workout.py` | Any new field is silently lost at the server boundary until this is changed. |
| `rep_velocity.py` — descriptive per-set report, "never feeds a prescription" | `strength_coach/features/rep_velocity.py` | The template for the tempo report module, including its abstention posture. |
| `vbt_analysis.py` / `vbt_performance.py` — targets, residual bands, cohorts, within-set drift | `strength_coach/features/` | Consistency metrics should reuse these bands rather than invent statistics. |
| Calibration eligibility: RIR 2–3, 1–8 reps, load ≥ 0.60 × e1RM, band = median ± 2·MAD | `docs/VBT-CALIBRATION.md` | The study only needs sets that can move a target. Everything else is wasted effort. |
| Watch contract D17 — optional mean and per-rep velocity per set | `docs/contracts/IOS-WATCH-CONTRACT.md` | The capture contract existed for velocity; it was the document to extend, and no motion amendment was merged. |
| Session detail exposes `device_reps` as `{rep_index, velocity_mps}` only | `strength_coach/history.py` | The API shape must be extended additively. |
| `clean_set` already carries set-level `tut_s`, `rom_mm`, `power_w`, `form_score` and `velocity_present` | `store/migrations/0001_initial.sql` | Time under tension and ROM already exist at set level. This plan adds per-rep resolution, not the concept — do not add duplicate columns. |
| Calibration eligibility is implemented, with per-reason exclusion counts | `features/vbt_calibration.py` | WP1 must reuse it rather than re-express the filters, so the garbage accounting is identical to production. |

## 3. Scope

*Historical scope: approved, then closed unbuilt. Nothing below is a backlog item.*

**In scope, v1 (descriptive) — never shipped:**

1. Rep count and set bounds, with confidence.
2. Phase durations: lowering, lifting, pause, per rep.
3. Time under tension, rep duration, set duration.
4. Rest intervals (already anchored at the End-set stamp).
5. Rep-to-rep temporal consistency (CV of rep duration, reported against the athlete's own baseline).
6. Range-of-motion consistency as a within-set ratio, not absolute centimetres.
7. Wrist steadiness as an internal, relative diagnostic — not shown as a score (§6).

**In scope, gated:**

8. Per-rep velocity from the device, and its agreement with LPT, per §10 G2/G3.
9. Velocity loss computed from device data.
10. Every `vbt_family` member is captured; a family is displayed only after it clears G1 (§10, D8).

**Candidate follow-on, not this cycle:** prescribed-tempo compliance ("3-1-1" measured against what the
server asked for). It is deliberately excluded here because no prescription currently carries a tempo
field — verified 2026-11-22, zero occurrences of `tempo` or `eccentric` in `strength-training-app` or
`docs/contracts`. It needs a plan-model change and a rule review before it can be displayed as
adherence, and both belong to a separate decision.

**Out of scope:**

- Any new training decision, threshold, readiness input or progression rule.
- A "form score" or any single composite quality number.
- Exercise auto-identification; the session plan already names the exercise.
- Left/right asymmetry (single watch).
- True bar path or bar wobble; the watch measures the wrist (§6).
- Machine, cable or bodyweight velocity claims beyond what the study demonstrates.

## 4. Metric definitions

Definitions are versioned. A metric without a stated convention is not shipped.

| Metric | Definition (v1) |
|---|---|
| Movement axis | Configured per exercise: vertical for squat, deadlift, bench, press; horizontal for row and hip thrust. Fallback: dominant principal axis of the set's motion. Never inferred from gravity alone. |
| Rep start | First sustained departure from rest along the axis, sustained ≥ 150 ms. |
| Rep end | Return to rest along the axis, sustained ≥ 200 ms. |
| Turnaround | Sign change of along-axis velocity with hysteresis; the bottom or top of the rep. |
| Lowering phase | Rep start to turnaround. |
| Lifting phase | Turnaround to rep end. |
| Pause | Interval inside the rep where along-axis speed stays below threshold for ≥ 100 ms. |
| TUT | Sum of lowering, lifting and pause durations. |
| Velocity loss | **Primary: from the best rep**, `(max − last) / max`. Secondary: first-to-last, `(first − last) / first`. A set whose last rep is its fastest is labelled `ramping` rather than reported as negative loss. |
| Rep consistency | CV of rep duration within a set, against the athlete's `(lift, rep_count)` baseline. |
| ROM consistency | CV of integrated displacement within a set; the absolute value is not reported. |
| Wrist steadiness | RMS of gyro magnitude during the lifting phase, normalised within set. Internal diagnostic. |

Conventions that must be stated wherever these are shown: rounding to 10 ms; the deadlift lowering
phase is reported only when the bar was controlled, otherwise omitted; "lowering" is used instead of
"eccentric" where the load is unloaded or dropped.

## 5. Capture payload

Per rep, only `rep_index` is mandatory:

```
{"rep_index": 1, "velocity_mps": 0.62, "lower_ms": 1450, "lift_ms": 620,
 "pause_ms": 180, "rom_m": 0.41, "steadiness": 0.12, "confidence": 0.93,
 "method_version": "tempo/v1"}
```

`velocity_mps` is **optional** (owner decision 2026-11-22, D7). A tempo-only capture carries phases
and no velocity. **Consequences of that decision:**

1. `clean_rep.velocity_mps` stays `NOT NULL` and the table is not migrated. Tempo-only sets write
   phase rows only, so "a `clean_rep` row exists" stops meaning "the set has velocity detail".
2. Ingestion must accept phase-only reps. `_append_reps` currently does
   `float(item["velocity_mps"])` and fails on a missing key; it must branch, and `_rep_summary` must
   skip velocity-less sets rather than emit 0 or NaN.
3. **Rep count and velocity-bearing rep count stop being the same number.**
   `rep_velocity.summarize` returns `count = len(values)`, which becomes "reps with velocity". Rep
   count must be read from `clean_set.reps` or `clean_rep_phase`, never inferred from `clean_rep`.
4. **All-or-none invariant.** A set is all-velocity or no-velocity; a mixed set is rejected at
   ingestion. Otherwise first-versus-last velocity loss is computed across a gap and is silently
   wrong.
5. **It is a client change, not only a server change.** `RepVelocity.velocityMps` is a non-optional
   `Double` (`StrengthCore/Models/Phase2Models.swift:776`), so a `null` will not decode. Making it
   optional is a coordinated server + watch + phone contract change, and `0` must never be used as
   the placeholder — 0 is column-specific, never a global sentinel.
6. Downstream VBT analysis already degrades honestly: a set with no mean velocity abstains with
   `missing_velocity`, so nothing needs a special case there.

Clients that send only `{rep_index, velocity_mps}` must keep working unchanged.

**None of this is in force.** On `development`, `_append_reps` still requires `velocity_mps` and
drops unknown keys, so the payload above is not accepted, and `RepVelocity.velocityMps` is still
non-optional. The changes exist only on the defunct branch.

## 6. Wrist steadiness is not wobble

The watch measures the wrist. Gyro magnitude there is dominated by wrist rotation, grip, forearm
anatomy and **strap tightness**; bar sway cannot be separated from wrist tremor with one IMU on the
forearm. The metric is therefore defined as a relative, per-user, within-set diagnostic, is not
aggregated across sets or exercises, and is not exposed as a quality score. Naming it "wobble" or
"stability" in user-facing copy would be a claim the data cannot support.

Strap position is recorded per set as a covariate, because it will explain more variance than any
filter choice.

## 7. Storage

New append-only table, sibling to `clean_rep`, materialised from `workout_rep_event`:

```
clean_rep_phase(clean_set_id, rep_index, lower_ms, lift_ms, pause_ms, rom_m,
                steadiness, confidence, method_version, started_at, source, created_at)
UNIQUE (clean_set_id, rep_index)
```

Rules:

- `method_version` is mandatory because production keeps no traces by default (D10). A changed
  on-device algorithm cannot be recomputed, so a version change is a step change in the numbers and
  baselines must never mix versions.
- **Export-aware retention.** Raw traces are off by default and stored locally only. A recording is
  the only copy of its data until it is exported, so **age alone never deletes one**: only files
  marked exported are eligible for automatic removal, after a 30-day backstop, and unexported files
  stay until deleted by hand. They are never uploaded to the server. Without retention at all, G4
  could count field failures but not diagnose them, and a rep-detection fix could not be re-derived
  against real data.
- `started_at` is nullable metadata, never part of the join (D9). It exists to diagnose a replayed or diverged set, not to resolve one.
- `clean_rep` is **not** altered; its uniqueness and readers stay as they are.
- `UPDATE`/`DELETE` refused by trigger, matching every other clean table.
- Materialisation is replay-safe and idempotent.
- `source` uses the existing vocabulary, so a set remains single-source.

**`clean_rep_phase` does not exist in any database**: the migration was never applied and is not on
`development`. The table and its triggers live only on the defunct branch. The retention rule above
is therefore also not implemented, and no recording is being retained or exported anywhere.

## 8. Descriptive module contract

`features/rep_tempo.py`, modelled on `rep_velocity.py`:

- reads the clean layer, writes nothing;
- returns per set: rep count, median and mean phase durations, TUT, duration CV, steadiness, and
  the source;
- abstains explicitly with a reason rather than guessing: `no_detail`, `incomplete_set`,
  `ambiguous_axis`, `low_confidence`, `dropped_lowering`;
- has no import path from any prescription, calibration or readiness module. A test asserts it.

**`features/rep_tempo.py` does not exist on `development`** — the module, its tests and the session-detail
field are all confined to the defunct branch, so nothing today reports tempo.

## 9. Source precedence

A set has one velocity source, which keeps `clean_rep`'s uniqueness intact:

1. A manual or LPT value wins whenever it exists.
2. Device values fill sets with no LPT value.
3. A set is never silently upgraded from LPT to device.

Consequence: rollout is incremental and reversible, historical calibration targets keep their
meaning, and no session is mixed within a set.

This precedence was never implemented: nothing writes device velocity today, so imported and manual
values remain the only source.

## 10. Validation and gates

**Study:** 8–12 lifters × 3 sessions × 4 lifts (squat, bench, deadlift, press), two sessions at
identical load for the noise floor. Video at 120 fps for the tempo gate; LPT for the velocity gate.
Only calibration-eligible sets are analysed.

Tempo validation is cheap because it checks *when*, not *how fast*. Velocity validation runs in a
scratch database copy that writes device values with `source='device'`, so both sources can be
compared for the same rep without touching `clean_rep`'s constraints in production.

| Gate | Criterion | If it fails |
|---|---|---|
| G1 Tempo fidelity | Phase-boundary error ≤ 2 frames at 120 fps (≈ ±33 ms); rep detection F1 ≥ 0.98 | Fix segmentation; do not ship visible numbers |
| G2 Velocity precision | MDC95 ≤ 50% of the median within-set loss the athlete acts on, from the historical analysis (§11 WP1) | Trend-only velocity, or no velocity |
| G3 Target stability | Recomputing calibration targets from device-only data moves no band by more than one step and flips `vbt_status` for < 5% of eligible sets | LPT stays the calibration source; device values are additive only |
| G4 Field false positives | ≤ 1 false rep per 20 sets in shadow mode | Tighten detection; keep the feature hidden |

**These gates were never run.** The project closed after WP1: no study was scheduled, no clip set
was labelled, and G1–G4 have no verdict. The "if it fails" column is design history, not a pending
branch.

**Per-family gating (never applied).** Capture covers every `vbt_family` member, but a family is displayed only after
it clears G1 with adequate coverage (D8). The gate report lists, per family, the set count, the
abstention counts by reason, and the verdict. Families that fail stay hidden. Families are never
pooled to rescue a sample size, for the same reason `VBT-CALIBRATION.md` refuses pooled L2/L3 fits —
the load–velocity curve is family-specific and pooling hides exactly the garbage the coverage buys.

G2 is deliberately expressed against the athlete's own loss distribution rather than a generic 5%
CV. If typical losses are 20%, an 8% MDC is useful; if they are 5%, no wrist sensor carries it.

## 11. Work packages

| WP | Work | Repo | Exit criterion |
|---|---|---|---|
| WP0 | Scope and the five decisions: metrics in/out, optional velocity, family coverage, tiebreaker, retention, informational-only | portfolio | **Closed 2026-11-22 (historical)** — §3, §5, §7, §10, §13, D7–D11; design record only |
| WP1 | Read-only historical analysis: loss distribution per lift, velocity scatter within `(lift, reps, RIR band)`, band sensitivity to velocity error, share of tempo-eligible sets. Aggregates only; owner-run or explicitly approved | backend (read-only) | **Completed 2026-11-22** — results in §15.4; retained as the closing evidence |
| WP2 | This plan plus the capture-contract delta in `IOS-WATCH-CONTRACT.md` | portfolio | **Withdrawn 2026-11-22** — never merged; the watch contract carries no motion-capture amendment |
| WP3 | Migration: `clean_rep_phase`, materialisation, normaliser extension, `rep_tempo.py`, additive session-detail field, tests | backend | **Abandoned 2026-11-22** — unmerged, not deployed; retained on `watch-motion-capture-defunct` (`c0baf46`) |
| WP4 | Watch capture: 100 Hz recorder inside the workout session, set identity stamping, debug export, plus an ad-hoc recorder that needs no workout or server; measure sample gaps and battery | iOS | **Abandoned 2026-11-22** — unmerged, not deployed; the physical-device check was never run; retained on `watch-motion-capture-defunct` (`576f14e`) |
| WP5 | Offline segmentation and velocity work against recorded files | backend / analysis | **Abandoned 2026-11-22** — reference implementation only (`tools/motion_segmentation.py`); no gate number was ever produced |
| WP6 | Pilot: one lifter, one lift, one load, end to end | all | **Not started** — closed with the project |
| WP7 | Validation study and gate report | all | **Not started** — closed with the project; no gate report exists |
| WP8 | Promotion: ship descriptive metrics; device velocity only if G2/G3 pass | all | **Closed** — nothing promoted; capture is not a shipped feature |
| WP9 | Shadow mode, no UI, compare against manual logs | iOS | **Not started** — closed with the project |

WP3 and WP4 were built in parallel after WP2 was approved, which is why the payload contract was
frozen first; both are now abandoned and the freeze has no remaining purpose. Nothing in this table
is pending.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Sensor stream gaps under a workout session invalidate everything downstream | Measured in WP4, before the study, not after |
| `clean_rep` uniqueness blocks two-source comparison | Scratch database for validation; single source in production |
| Metric sprawl makes the report unreadable | Three numbers on the watch, the rest in the post-session report |
| Strap tightness confounds steadiness | Recorded per set; steadiness internal only |
| Velocity gate fails after the tempo work ships | Tempo is independently useful; no dependency on G2 |
| Battery and thermal cost of 100 Hz capture | Measured in WP4 against a normal session |
| A changed on-device algorithm silently shifts every number | `method_version` is stored and baselines never mix versions |
| Debug retention quietly becomes an indefinite archive | Hard auto-expiry in the capture path, local only, never uploaded |
| A mixed-velocity set corrupts first-versus-last loss | All-or-none invariant enforced at ingestion (§5) |
| A nullable velocity breaks an older client's decoding | Coordinated contract change; `0` is never a placeholder (§5) |

These are design-stage risks of a closed project: none is monitored, and none needs a mitigation.
The risk that materialised was the one the gates existed to catch — G1 was never run, so no
stream-gap or battery measurement could compensate for a detector with no labelled data.

## 13. Resolved questions

All seven were settled by 2026-11-22; none is open. Q1–Q5 were answered by the owner while the plan
was live; R1–R2 were mooted when the project closed.

| # | Question | Answer | Where |
|---|---|---|---|
| Q1 | Is `velocity_mps` optional in the rep payload? | **Yes**, with an all-or-none rule per set and a coordinated client change | §5, D7 |
| Q2 | Which families get tempo in v1? | **All `vbt_family` members are captured**; display is gated per family on G1 evidence, and garbage is excluded structurally rather than averaged in | §10, D8 |
| Q3 | Ordinal join, or a timestamp per set? | **Ordinal is the join key** — the watch owns set state, so rep order is enough. `started_at` is optional metadata for diagnosing replay divergence, never a join input | §7, D9 |
| Q4 | Keep raw 100 Hz traces? | **Debug-only**, opt-in, removed only once exported and past a 30-day backstop, so field failures can be diagnosed. Hence `method_version` on every phase row | §7, D10 |
| Q5 | Does a tempo breach ever become a training decision? | **No. Informational only** — no alert, nudge, gate or prescription input | §3, D11 |

**Residual questions — closed 2026-11-22, both moot.** They were recorded as non-blocking for WP1;
the project closed before either could matter, and neither is a backlog item:

| # | Question | Disposition |
|---|---|---|
| R1 | The minimum set count per family before G1 could be judged | Moot: G1 was never run, and the tempo track closed with the project. |
| R2 | Whether the nullable-velocity contract change ships in one client release or behind a capability flag | Moot: the contract change was never merged, so no client release ever carries it. |

## 14. Decision log

| ID | Decision | Date |
|---|---|---|
| D1 | This cycle is descriptive only; no prescription, load or readiness consumer | 2026-11-22 |
| D2 | `clean_rep` is not altered; phase detail goes to a sibling append-only table | 2026-11-22 |
| D3 | Validation compares sources in a scratch database copy | 2026-11-22 |
| D4 | A set has one velocity source; manual/LPT wins where present | 2026-11-22 |
| D5 | Wrist steadiness is an internal diagnostic, never a user-facing score | 2026-11-22 |
| D6 | Tempo is delivered before velocity, and does not depend on it | 2026-11-22 |
| D7 | `velocity_mps` is optional per rep; a set is all-velocity or no-velocity | 2026-11-22 |
| D8 | Capture every `vbt_family`; display per family on G1 evidence; never pool families | 2026-11-22 |
| D9 | Ordinal join is the only key; `started_at` is optional metadata for replay divergence, never a join | 2026-11-22 |
| D10 | Raw traces are debug-only; local capture is opt-in, and removal requires export plus a 30-day backstop — never age alone | 2026-11-22 |
| D11 | Tempo metrics are informational only: no alert, nudge, gate or prescription input | 2026-11-22 |
| D12 | G2 uses history plus study data; the per-rep base is recent and small, not absent | 2026-11-22 |
| D15 | ~~Confirm per-rep order against the LPT~~ — closed: order correct, ramping is real | 2026-11-22 |
| D16 | Velocity loss = `(max − last)/max`; first-to-last secondary; faster-ending sets labelled `ramping` | 2026-11-22 |
| D13 | Tempo is validated against the LPT export's `tut_s`/`rom_mm`, not only video | 2026-11-22 |
| D14 | Velocity is trend-first; absolute targets are not the v1 claim | 2026-11-22 |

D1–D16 are historical design decisions of a closed project. None is in force; they are retained
because §15.4's evidence refers to them.

## 15. WP1 analysis specification

Read-only, owner-run or explicitly approved, against a database copy. It emits **aggregates only** —
no raw rows, no set-level output. Conclusions (thresholds, decisions) are recorded here; the numbers
stay in `private/`.

**Method.** Load clean sets → `features.derived.enrich` (provides `velocity_present`, `rir_class`,
`e1rm_kg`) → reuse `features.vbt_calibration` for eligibility and its per-reason `excluded` counts.
No new filtering logic: if WP1 and production disagree about which sets are eligible, the study is
measuring a different population than the one that gets calibrated.

### 15.1 Outputs

| # | Analysis | Definition | What it decides |
|---|---|---|---|
| O0 | Existing-field population | Share of working sets with `velocity_present`, `tut_s`, `rom_mm`, `power_w` populated, per family and per year | Whether tempo has any historical base at all — a two-minute query that can reframe the project |
| O1 | Per-rep coverage | Sets with ≥1 `clean_rep` row and sets with `count(clean_rep) = reps`, per family per quarter | Whether the loss distribution is computable from history or must come from the study |
| O2 | Velocity-loss distribution | On complete per-rep sets with `reps ≥ 2`: both definitions from §4 — best-to-last and first-to-last — with the `ramping` share; n, median, IQR, p90, share > 10/20/30% | The G2 target — whether any wrist velocity can resolve the loss that is acted on |
| O3 | Band width | Per (family, reps, RIR band), eligible sets: median, MAD, band = median ± 2·MAD, width in m/s and as % of median | How much error the existing bands can absorb |
| O4 | Error budget | Inject bias and noise into set means, recompute bands, measure band-edge movement and P(wrong band) against σ; report the largest σ at 5% misassignment | G3's threshold, expressed before anything is built |
| O5 | Calendar reality | Working sets per family per month, and velocity-bearing sets per family per month | Which families can sustain calibration, and the per-family gate runway |

### 15.2 Decision rules

| Observation | Consequence |
|---|---|
| O2 median loss < 8% | Wrist velocity cannot resolve the effect; ship tempo only and retire the velocity track |
| O2 median loss 10–25% | Velocity is worth pursuing; G2 is viable if O4's tolerable σ ≥ 5–8% |
| O4 tolerable σ < 0.02 m/s | No wrist-worn sensor passes; stop before WP3 spends anything on velocity |
| O1 complete per-rep sets < 50 per family | Take the loss distribution from the study, not history; O2 becomes advisory |
| O0 shows `tut_s` / `rom_mm` already populated | Tempo has a historical base; the new work is per-rep resolution and trust, not first capture |
| O5 < 12 velocity sets per family per month | Expect a long calibration runway; limit v1 to the four main lifts |

The velocity track was retired and the tempo track then failed on rep detection; §0 records the
closure. No branch of this table is live, and O3–O5 remain evidence only.

### 15.3 Effort

Half a day to write `tools/watch_metrics_profile.py` in the server repository (read-only, no writes),
half a day to run and interpret. Reviewed before it touches real data.

### 15.4 Results, 2026-11-22

Run read-only against `data/coach.db` on the ODROID:
`python tools/watch_metrics_profile.py --db data/coach.db`. 8,033 clean sets, 6,065 working sets,
106 per-rep rows.

| # | Result | Consequence |
|---|---|---|
| O0 | Velocity on 30–55% of main-lift working sets. `tut_s` and `rom_mm` populated on 97–100%. `power_w` on 0 of 8,037. `form_score` on 0. | Tempo has a strong **set-level** historical base; velocity is patchy; power and form were never captured. |
| O1 | Per-rep logging is **recent, not absent**: 26 sets (106 rep rows) since 2026-10-25, 19 of them in November. Every `workout_rep_event` materialised into `clean_rep`, so capture works end to end; the old history above that date is set-mean only. | The loss distribution can come from history, but only from the recent months and only at ~6–10 sets/month. |
| O2 | 26 complete LPT sets; pooled median first-to-last loss 0.0%, and **42% of sets got faster** — confirmed by the owner as real ramping, not an entry artefact. | First-to-last loss is the wrong primary metric for this athlete: it reports a fatigued touch-and-go set as negative. §4 now measures from the best rep (D16). |
| O3 | Bands are wide: width 40–140% of median velocity (bench, 3 reps: 0.216–0.400 m/s). | The existing band absorbs more noise than expected. |
| O4 | 6 qualifying targets: median tolerable error **0.030 m/s (9.1%)**, range 0.016–0.037. | A wrist sensor needs roughly 0.03 m/s to keep target bands within 10% of width. Marginal, not impossible. |
| O5 | Velocity sets per month: bench 5.9, squat 6.6, horizontal push 10.8, hinge 4.4 — every family under 12. | The calibration runway is long; v1 should be the main lifts only. |

Decisions taken on this evidence:

- **D12** G2 is computed from history plus study data, not study data alone. The per-rep base is real
  but small (26 sets, all since 2026-10-25) and grows at roughly 6–10 sets a month.
- **D15** ~~Confirm per-rep order before trusting loss.~~ Closed 2026-11-22: the order is correct and
  the 42% increasing share is real ramping, so the metric changes instead of the data.
- **D16** Velocity loss is measured from the best rep by default; first-to-last is secondary and a set
  that ends faster than it started is labelled `ramping`, never negative loss.
- **D13** Tempo is validated against the LPT export's own `tut_s` and `rom_mm`, not only video —
  those columns are 97–100% populated, so a second reference already exists.
- **D14** Velocity is trend-first. At a 0.030 m/s tolerable error, absolute targets are marginal
  while velocity loss and band membership stay usable.

O4 assumes a normal group distribution seeded from each target's own median and MAD. It estimates
band stability, not per-set accuracy. G1 and G2 were never run: no study followed, and the project
closed on the rep-detection failure.

## 16. Related documents

- [iOS client phase plan](IOS-CLIENT-PLAN.md) — R10 closed the watch set-timing and VBT entry work.
- [iOS watch contract](../contracts/IOS-WATCH-CONTRACT.md) — carries **no** motion-capture amendment;
  the 2026-11-22 amendment was withdrawn and the contract is unchanged by this attempt.
- [VBT calibration](https://github.com/georgesdib/strength-training-app/blob/development/docs/VBT-CALIBRATION.md)
  — target eligibility that defined the (never-run) study population.
- [Training Intelligence plan](TRAINING-INTELLIGENCE.md) — where a post-session narrative over these
  metrics would have lived; no narrative consumes them.
- [Per-set heart-rate recovery](https://github.com/georgesdib/strength-training-app/blob/development/docs/HR-RECOVERY-PROBE.md)
  — the separate measurement that is live and display-only; it exposed the same user-tapped set
  boundary that defeated this project's timing analysis.
