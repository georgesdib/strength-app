# Resolver prescription structure and programme context

**Status:** complete 2026-11-21. WP0–WP9 are implemented; the WP6 role-quality corrective
closeout and the reviewed stimulus extension (`DEC-RESOLVER-32`) were owner-accepted on
2026-11-21, and their corrected A/B and benchmark evidence are below. The original WP6 four-case
A/B remains owner-accepted from 2026-11-20. The production ODROID service was deployed from
`development` at `5a3c1df` on 2026-11-21 after a verified database backup. The owner chose a
direct development pull, so `main` was not merged or tagged. The WP4 real-data latency check
remains deferred; the WP6 ODROID benchmark is recorded below. Work packages and release trains
are in §6.
**Scope:** cross-repository. Backend prescription structure, top-set intent, evaluation and
programme context; the shared plan/execution contract; iPhone and Watch execution surfaces.
**Backend implementation status:** [strength-training-app ROADMAP](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md).
**Related contracts:** [contract index](../contracts/README.md), [iOS R7](../contracts/IOS-R7-CONTRACT.md), [iOS R8](../contracts/IOS-R8-CONTRACT.md), [watch](../contracts/IOS-WATCH-CONTRACT.md).
**Related backend references:** [resolver algorithm](https://github.com/georgesdib/strength-training-app/blob/development/docs/RESOLVER-ALGORITHM.md), [main lifts vs accessories](https://github.com/georgesdib/strength-training-app/blob/development/docs/RESOLVER-MAIN-LIFTS-VS-ACCESSORIES.md), [dwell and rotation](https://github.com/georgesdib/strength-training-app/blob/development/docs/DWELL-AND-ROTATION.md), [top-set evidence](https://github.com/georgesdib/strength-training-app/blob/development/docs/TOP-SET-BACKOFF-EVIDENCE.md), [API](https://github.com/georgesdib/strength-training-app/blob/development/docs/API.md), [data model](https://github.com/georgesdib/strength-training-app/blob/development/docs/DATA-MODEL.md), [decisions](https://github.com/georgesdib/strength-training-app/blob/development/docs/DECISIONS.md).

## 1. Purpose

The resolver already has the correct boundary: the programme and engine calculate the
prescription, the resolver assigns exercises, the evaluator builds the real prescription and
scores it, and the winner is persisted with provenance. The remaining problems are narrower:

- native clients cannot display or prefill an item with more than one load/RIR group, so a
  top-set plan is shown and executed as its back-off load;
- top-set intent is split across a persisted mode and a per-request boolean, and an unmet
  intent degrades silently;
- the plan can be edited mid-session, which blurs planned and performed and forces structure
  rules for every edit path;
- the evaluator has only an additive penalty score and no role-aware or programme-aware
  diagnostics;
- ranking has no positive role-specific training-quality term, so a maximal week can select work
  that does not support the week's intent;
- actual data cannot describe planned versus performed structure without a manually entered
  set role, and the load-shape descriptors do not identify a top-set/back-off pattern;
- the candidate shortlist is biased by catalogue order;
- Today does not expose DUP, deload or competition context.

This plan fixes those. It is not a resolver V2 rewrite and does not add named phases, a new
periodisation engine, per-muscle volume targets, a composite strength score, or plan editing.

## 2. Principles

- Python remains authoritative for readiness, loads, sets, structure, deload, competition and
  evaluation.
- The prescription is frozen at start. Planned and performed are separate records.
- The athlete records what was performed. The server derives descriptions, never roles.
- No composite physiological score: explicit feasibility gates, a deterministic hierarchy and
  reasons.
- Append-only history. Historical rows are read-only; nothing is rewritten.
- No backward-compatibility commitments. Server, iPhone and Watch ship together; old protocol
  shapes are not supported, and existing rows are read without reinterpretation.
- The LLM explains server facts; it never computes phase, deload, competition or structure.

## 3. Decisions

| ID | Decision |
|---|---|
| D1 | No named phases, no periodisation engine, no full resolver rewrite. Improve the existing pipeline. |
| D2 | No per-muscle volume targets and no composite strength-stimulus score. |
| D3 | A prescription item carries an ordered list of planned set groups. The wire accepts 1..N; the engine emits the existing top-set + back-off structure (one or two groups). |
| D4 | Groups are identified by order on the wire, in persistence and in the API. No role is stored or inferred there; the engine keeps a build-time internal role only. Straight sets are emitted as an empty list; a single full-item group is accepted on read. |
| D5 | Top-set intent is one tri-state: `off`, `preferred`, `required`. It lives in the settings profile with an optional per-request override. Default `off`; legacy `ask` reads as `off`, legacy `on` as `required`. |
| D6 | `preferred` asks for the structured prescription and accepts a straight-set fallback with a reason; `required` asks for it and marks an unexpected fallback as unsatisfied. The distinction is whether fallback is acceptable, not a comparison of two builds. |
| D7 | The plan is immutable once started. Plan editing is removed; there is no plan swap, add, remove, reorder or set-count edit. |
| D8 | Substitution and addition are execution concepts, not plan edits: an append-only execution event plus a per-set attribution field. The performed set is the durable record. |
| D9 | The watch does not originate substitutions. It renders the phone-authored execution view and logs sets against it. |
| D10 | The watch is offline-capable only while the phone is online. There is no pending-session shell and no start without a reachable phone or server. |
| D11 | Set-role input is removed from every logging surface. Legacy role columns and values remain read-only provenance and are not used for matching or decisions. |
| D12 | The programme header is a server-computed reporting model reused by Today and intelligence facts; it labels trained week and calendar deload week separately and is not an evaluator input. |
| D13 | Evaluation is a deterministic, role-aware hierarchy, not a composite score, and reuses the existing intensity, exposure, volume, suitability and tie-break definitions. |
| D14 | Candidate ordering is slot-role aware, deterministic and measured before any beam or cap change. |
| D15 | This plan supersedes the R8 plan-edit surface and updates the top-set evidence review's mode reference; the review's no-default-change conclusion and the opt-in default are retained. |
| D16 | Programme context reaches evaluation through the applied build and its notes, never through the header. |
| D17 | Main, secondary and accessory assignments are ranked by deterministic role-quality classes (specificity, exposure adequacy, suitability, complementarity, redundancy, coverage, stimulus-to-fatigue). One owner per signal, volume as a gate, no composite, and only with measured evidence. |
| D18 | RIR 6 is the warm-up sentinel by definition: every warm-up is logged at RIR 6, an RIR-6 row is never working volume, and a stored working flag that disagrees is a data-quality anomaly. An import must not map a working set to RIR 6. |
| D19 | Derived actual structure is a separate analysis layer over the recorded sequence: segmented classes with ordinal confidence and named evidence, separate from planned matching, never written to raw sets, and with no training-policy effect until a separate decision. |
| D20 | Repetition and variation are owned by the pre-build dwell layer: the cap, the deterministic exploration draw and a bounded factor ordering, after required-pattern coverage and within the slot's structural class. Role quality does not re-score dwell counts or last used. |

## 4. Baseline before this plan (recorded 2026-11-19)

This is the assessment that motivated the plan, not a snapshot of production on 2026-11-21.
Some bullets describe the cutover the plan then implemented; current implementation status is
in §6 and the backend ROADMAP.

- `prescribe/resolver.py` runs candidate pools, a bounded beam, full evaluation, integrity
  checks and snapshot provenance. `prescribe/engine.py` remains authoritative for load, reps,
  RIR, readiness, continuity, deload, volume, spinal exposure, top sets, warm-ups and validation.
- `prescribe/top_set.py` produces one top set plus one back-off group for the session primary
  main lift, and sets the item-level `load_kg` to the back-off load.
- The plan payload carries ordered `set_groups` (`group_index`, no role), but the shared Swift
  `PrescriptionItem` does not decode it, so iPhone and Watch show the back-off load only.
- `validate_plan_set_groups` accepts 1..N ordered groups and ignores a legacy role; the five
  core plan-edit functions and their web/iOS routes are deleted and a plan is frozen at start.
- `set_role` is no longer an input on any logging surface; the stored column is legacy
  provenance that the analysis no longer reads for matching, and the web role picker is removed.
- `GET /api/ios/v1/today` returns date, readiness, score, active workout and plan state, but
  not trained week, DUP, deload or competition.
- The watch start gate requires the server or a reachable phone relay; offline start with both
  devices offline is deferred. Idempotency receipts are scoped `(device_id, operation_id)`, and a
  plan is readable by its requester or its execution target.

## 5. Target model

### 5.1 Frozen plan and execution view

A plan is a preview until it is started. Before start, changing parameters means issuing a new
plan request (the R7 supersede path); that is not a plan edit. After start the plan is frozen:
no route mutates `plan_json`, and `plan_revision` is plan identity only, never a plan-edit
counter. The execution watermark orders view updates. `plan_item_mismatch` is retired for new
clients (an annotated substitution is accepted); the legacy off-plan fallback remains for old
replayed sets.

What the athlete does differently is execution state, not plan state:

- a **substitution** replaces one plan item for the session: `{plan_item_index, exercise_id,
  prefill_load_kg, reps_low, reps_high, rir_target}`;
- an **addition** adds extra work after an item: `{after_item_index, exercise_id,
  prefill_load_kg, reps_low, reps_high, rir_target}`.

Both are append-only `workout_event` rows with a client-generated id, pushed to the watch over
WatchConnectivity and stored when the phone can reach the server. `GET .../execution` returns the current
substitutions and additions with an execution watermark (the latest event identity); the watch
applies a server payload only when its watermark is at least its local one, and keeps
WatchConnectivity events the server has not confirmed. The watch reuses its existing rules:
apply at an idle point, never over unacknowledged work, refresh on foreground and after a set.

The performed set is self-describing and does not depend on the event having arrived:
`exercise_id` is what was performed, `plan_item_index` is the planned slot it was logged
against, and `substitutes_plan_item_index` is set when it replaced that slot. Sets for an
addition carry `plan_item_index = null` and count as extra work. This is the durable attribution;
the event only supplies the live view and the prefill.

Plan editing is removed: the core plan-edit functions and their web/iOS routes are deleted, and
`plan_modified_json` / `plan_revision` become legacy-only columns for historical rows. The R8
plan-edit sections are superseded.

### 5.2 Planned set groups

A prescription item carries an ordered list of groups:

```json
{
  "exercise_id": "ssb_squat",
  "sets": 4,
  "set_groups": [
    {"group_index": 0, "sets": 1, "load_kg": 120.0, "reps_low": 3, "reps_high": 5, "rir_target": 1},
    {"group_index": 1, "sets": 3, "load_kg": 102.5, "reps_low": 3, "reps_high": 5, "rir_target": 3}
  ]
}
```

Invariants:

- `group_index` is contiguous from 0 and defines order; order is the only identity;
- the sum of group sets equals `item.sets`;
- every group has a usable load, rep range and RIR where applicable;
- an empty list is straight sets; a single group with the full set count is also accepted;
- no role is stored or required on the wire; the wire accepts 1..N groups and the engine emits
  only the top-set + back-off structure (D3). The engine's internal build-time tag is not part of
  the contract: serializers, persistence, clients and analysis never see it; straight sets and
  legacy rows are read by order;
- the engine decides groups; the resolver never invents group loads;
- a display label may be derived for presentation, never for analysis.

Derived rules:

- the warm-up ramp uses the heaviest group load, not the first group;
- `item.load_kg` remains the ordinary summary load (the back-off load for a top-set item) and is
  never the source for per-set display or intensity;
- intensity is the set-weighted mean over groups, computed after every engine modifier. The
  current `item.intensity` is computed before the top set is applied and understates a
  structured item; it is recomputed from the groups;
- volume remains the existing working-set ledger; groups change load distribution, not sets;
- deload and technique throttle scale every group and preserve the sum invariant;
- the item-level VBT target describes the working (back-off) sets; a structured item does not
  display that target for the top set in this phase, and per-group VBT targets are not added;
- validation accepts 1..N groups, enforces the sum invariant and requires numeric loads; a
  persisted or wire role is ignored. Legacy rows that carry one are read by list order. The
  internal build-time tag is used only while the engine constructs the structure; warm-up uses
  the heaviest group.

Plan-edit resize rules are deleted with the edit paths (D7), so no structure rule has to survive
an edit.

### 5.3 Top-set intent

One tri-state, resolved as: per-request override, else the settings-profile value, else the
registry default `off`.

| Value | Behaviour |
|---|---|
| `off` | Build straight sets. Status `not_applicable`, reason `intent_off`. |
| `preferred` | Build the structured prescription when the lift is eligible and unblocked; otherwise straight sets. An unexpected blocker records status `fallback` and its reason. |
| `required` | Build the structured prescription when the lift is eligible and unblocked; otherwise straight sets with status `not_applicable` (blocked by design) or `unsatisfied` (unexpected blocker). The plan remains a valid, startable plan. |

Blocked by design means the engine deliberately withholds the structure: deload, competition
taper, a safety-driven readiness fallback, or a session without an eligible main lift.
Unexpected blockers are configuration or data problems: no usable load or e1RM, fewer than two
working sets, a lift that is not an essential RIR main lift, or a lift outside the resolver
policy's top-set eligibility.

Status is stored on the frozen plan as `{status, reason_code, reason}` and is immutable for
that session. It is never a mutable plan-level boolean. There is no dual-structure evaluation:
the resolver builds one structure per intent, so resolver cost is unchanged and the
`preferred` dual-build budget is withdrawn.

Legacy profile values are normalised once when settings load: `ask` reads as `off`, `on` as
`required`. Profiles that never stored a value take the default `off`, which preserves the
previous effective behaviour; no programme change is implied. The tri-state is about acceptable
outcome, not structure optimisation: `preferred` permits a straight-set fallback, `required` does
not.

### 5.4 Programme header

One read-only header, assembled on the server:

```json
{
  "trained_week": 2,
  "dup": {
    "enabled": true,
    "cycle_weeks": 4,
    "cycle_week": 2,
    "main_scheme": "strength",
    "accessory_scheme": "volume"
  },
  "deload": {
    "calendar_week": 3,
    "status": "none",
    "trigger": null,
    "reason": null
  },
  "competition": {
    "date": "2027-01-16",
    "days_until": 58,
    "window": "none"
  }
}
```

Rules:

- `trained_week` is the trained-week index the engine uses for DUP and the ramp; it is null when
  no block anchor is declared. It is not the calendar week.
- `deload.calendar_week` is the calendar week since the anchor used by the deload policy. It is
  labelled separately because the two definitions can disagree.
- DUP is present only when undulation is enabled and an anchor exists; `cycle_week` is derived
  from the trained week and the effective cycle. Schemes come from the applied undulation table.
- `deload.status` is `active` when a reactive decision applies today or when the live ready plan
  was built with a deload; `suggested` when a scheduled deload awaits confirmation; otherwise
  `none`. `trigger` and `reason` are copied from the policy decision.
- Competition status reuses the existing competition window; a past date is not counted down and
  a date whose override is disabled reports `window: "none"` while `days_until` still reflects
  the real date.
- The header is computed without loading the full rule context or history: profile anchor,
  trained-week query, effective settings and deload decisions.
- The header is a reporting model and is not passed into resolver evaluation. Applied context
  reaches each candidate through the evaluation inputs and the built prescription's notes.
- `GET /api/ios/v1/today` gains the additive header; the top-level `date` is not duplicated.
- The facts are added to the existing programme-context intelligence resource (`dup`,
  `competition`, `trained_week`) with registered methods (`undulation.for_week`,
  `top_set.competition_window`, `rules.context.trained_week_index`) in the intelligence method
  registry and module list, and are available to nudge, weekly-summary and chat dossiers. The LLM
  may explain them; it may not compute or alter them.

### 5.5 Evaluation hierarchy

Replace the additive score with a deterministic, role-aware hierarchy. One assignment wins; hard
feasibility precedes every soft level; there is no composite score.

1. **Hard feasibility and safety** — executable, no validation or constraint issues, spinal cap,
   exact assignment preservation, required movement patterns.
2. **Programme consistency and non-negotiable intent** — a `required` plan whose structure was
   blocked unexpectedly ranks below one that applied it; deload, taper and competition
   restrictions are honoured; the volume band is a gate, so a candidate outside the adjusted
   tolerance ranks below every inside-band candidate and an inside-band candidate is neutral. The
   band is the deload- and taper-adjusted band, so intentional reduction is not a gate failure.
3. **Role-specific training quality** — lexicographic per role, using deterministic classes. The
   applied build already applies load-level progression, continuity, readiness, DUP, deload and
   competition effects; the level reads their outcome and does not re-score them. Repetition and
   variation are owned by the pre-build dwell layer (§5.7); the level does not re-score dwell
   counts or last used.

   | Role | Ranking criteria | Source |
   |---|---|---|
   | Main | Specificity class (same lift, same family, same pattern, comparable pattern); heavy-exposure adequacy (band plus e1RM confidence and age, not a point estimate); technical suitability (ratings, technique throttle, form) | taxonomy and lift family, e1RM age and quality, lift readiness, form assessment, suitability |
   | Secondary (support) | Complementarity with the selected main lift's pattern, materialised volume key and lift family; marginal volume usefulness against the candidate's own pattern target (missing neutral); redundancy against the main and other selected exercises (pattern/key/family/muscle overlap, not set count) | taxonomy patterns, volume ledger, lift groups, primary muscles |
   | Accessory | Coverage of patterns not already covered by the main or other selected work (own slot excluded); productive volume against the pattern target (not a set count); stimulus-to-fatigue as a two-input ordinal matrix: a provisional 1-3 stimulus rating seeded from the evidence-graded local-muscular demand profile, compared with the role-specific mandatory tax axes; missing either input is neutral | taxonomy, volume ledger, demand profiles, selection tax |

   Within a role, order the criteria as listed; across roles, order role priority first (main,
   then secondary, then accessory). Missing data is neutral, never a guess, and power slots are
   excluded from quality ranking because their intent is fixed by the quality stop.

   Eligibility filters (injury, can_do, will_do, feels_bad, pattern) are pass/fail and never
   quality points; the suitability class ranks only candidates that passed. The dwell cap and the
   exploration draw are pre-build controls (§5.7); role quality does not re-score them.
4. **Volume adequacy and distribution** — only within the band: the existing symmetric volume
   error is a soft tie-break after the role vector, not a gate and not a role-quality composite.
   The band remains the hard gate; the legacy additive score remains a final fallback, and for
   feasible finalists it repeats the same volume/time/warning terms already compared, so it
   cannot reverse an earlier level.
5. **Recovery and practicality** — session time, fatigue and spinal context, warnings.
6. **Deterministic tie-break** — the existing resolver tie-break, then stable assignment order.
   Repetition is not re-added here; it is owned by the pre-build dwell layer (§5.7).

Implementation notes:

- one owner per signal: the dwell layer owns repetition and variation and orders the pool;
  the evaluator owns specificity, exposure, redundancy and suitability; injury, can_do and
  suitability vetoes remain eligibility filters, not quality points;
- each criterion is recorded as a small deterministic class in the snapshot, per finalist; any
  scalar kept for the beam is derived from the lexicographic vector, not defined separately;
- role quality reads the applied context from the built prescription's notes (`undulation`,
  `deload`, `top_set`); the programme header is not an input;
- heavy-exposure adequacy reuses the relative-intensity bands from `features/monitoring.py`, the
  set-weighted group intensity from §5.2, and `features/exposure.py` /
  `features/high_intensity_exposure.py`; no new bands, and precise %e1RM is not optimised;
- the fingerprint version is bumped when structure intent and the selected structure enter it;
- role quality is enabled only after the fixed-history comparison shows it does not trade safety,
  the volume gate or session time for specificity; the comparison is recorded in the snapshot;
- class boundaries, family membership and any recency window are versioned config with domain
  reasons and need owner approval before implementation;
- no composite score, no per-muscle dose and no second scoring engine.

### 5.6 Actual data and derived structure

The athlete records exercise, actual load, reps or seconds, RIR/RPE where available, velocity
where available, and optional feedback. No set role is stored on a raw set or solicited from the
athlete. Four layers stay separate:

1. **planned groups** — what the programme prescribed;
2. **raw performed sets** — what the athlete recorded;
3. **planned-versus-performed matching** — which recorded set corresponds to which planned group,
   or is extra or missing;
4. **derived actual structure** — what the recorded sequence looks like on its own.

Warm-ups:

- RIR 6 is the warm-up sentinel by definition, and every warm-up is logged at RIR 6. An RIR-6 row
  is a warm-up, is never working volume, and is excluded from planned-group matching and from
  derived working structure; the planned ramp is used only to label its rung. No heuristic may
  override this.
- The planned ramp labels which rung an RIR-6 row matched. An RIR-6 row that matches no planned
  rung is still a warm-up (unplanned preparation).
- A missing RIR is not a warm-up. It is unknown warm-up status, counted as working volume by the
  existing conservative rule, and the analysis reports reduced confidence.
- The stored working-set flag is expected to equal `rir != 6`. A disagreement is visible as a
  data-quality note; RIR 6 wins and the row is a warm-up.
- RIR 6 is never rejected on import. The current RPE mapping that turns RPE 4 into RIR 6
  therefore imports a warm-up, which is the sentinel's definition (owner clarification
  2026-11-20).

Matching:

- ordered actual sets (`set_index`, `created_at` which carries the client's performed time);
- the frozen plan's ordered groups and the item identity;
- load, reps and RIR, plus any group annotation;
- one matcher shared by adherence, VBT and the structure analysis, reporting `matched`,
  `missing`, `extra`, `ambiguous` or `unknown` per planned group, with load tolerance (one
  rounding increment), rep range and RIR tolerance. The substitution annotation is stored on
  `workout_set` and copied to `clean_set` during materialisation;
- no top set is inferred because the plan had one. A substituted set is matched through
  `substitutes_plan_item_index`; an addition is extra work.

Derived actual structure:

- the full recorded sequence is segmented. RIR-6 rows form **preparatory progression** segments
  (labelled as matched or unplanned preparation) and are excluded from working metrics. The
  remaining segments are classified as **heavy working exposure**, **top-set-like effort**,
  **back-off sequence**, **straight working sets**, **multiple heavy exposures**, or
  **ambiguous/insufficient data**;
- each segment carries an ordinal confidence (`high`, `medium`, `low`, `unknown`), its
  boundaries, and the evidence used: relative load, reps, RIR/RPE, and planned context;
- loads within one rounding increment count as equal; a missing load or RIR lowers confidence;
  when the evidence cannot support a class the segment is `unknown`;
- the load-shape descriptors (`constant`, `ascending`, `descending`,
  `ascending_then_descending`, `irregular`, `insufficient_data`) remain a compact summary of the
  working loads, subordinate to the structure layer and not a competing classification;
- derived structure is post-workout description only. It never rewrites raw sets, the working-set
  flag, working-set volume, e1RM or fatigue metrics, and it has no training-policy effect until a
  separate decision says so. Reporting, history and adherence explanation are its consumers.

### 5.7 Candidate diversity

Retain the bounded beam and full evaluation. Candidate selection has two owners: the pre-build
dwell layer decides which exercise enters the search; the evaluator decides which completed
prescription wins. The candidate cap stays at its current width until a measured change justifies
otherwise.

**Dwell layer (pre-build).**

- The cap is unchanged: `_apply_dwell_exclusion` drops candidates at or above
  `resolver.dwell.target`; when every candidate is at the cap, the pool is kept with a warning.
- The exploration draw is the rotation: with probability `resolver.dwell.probability`, the slot's
  last choice is demoted to the end of its structural pattern class, using the existing
  deterministic draw keyed on `(date, session type, slot id)`, so a preview and the saved
  prescription agree. It is never removed: it stays available as a fallback. The last choice
  comes from the same history mapping the generator used; if it is absent from the pool, the
  draw has no effect.
- The factor `f(c) = 1 - exp(-c / tau)` is a bounded preference. It orders candidates only within
  a structural class; it never crosses required-pattern coverage and never overrides eligibility
  or the cap. A pure factor sort is rejected because `f` saturates quickly: it would let any used
  lift beat any never-used lift regardless of readiness, fatigue or spinal cost.
- Precedence in the pool: structural grouping, bounded factor ordering within the group,
  deterministic draw/demotion within the group, then catalogue order. Required-pattern coverage
  is a beam reserve, not a pool sort key: coverage must survive the draw so the only candidate
  for a required pattern cannot be lost. The beam still reserves required-pattern candidates
  when it truncates.
- The dwell layer owns repetition and variation. Role quality does not score dwell counts or last
  used, so there is no second continuity signal.
- The template supplies the slot identity, session type and slot order used by the draw and the
  last-choice lookup; it is otherwise unchanged.

**Structural ordering.** Family membership and catalogue order remain the deterministic
tie-breaks; family membership is explicit config, not a judgement call.

**Measurement.** Compare cap-only, cap plus draw, and cap plus draw plus bounded factor on a fixed
history, with a pure-factor variant only as a rejected reference. Report how often the chosen
exercise changes and whether the volume band, session time, spinal cost, warnings and adherence
change. A variant that trades safety or the volume band for stickiness is rejected. Pool order is
the beam's rank cost, so reordering changes the search trajectory, not only the shortlist.

### 5.7.1 Minimum session and accessory-only

`minimum_session.build_resolver_shape` runs before the resolver and is not changed by this
plan: it chooses the surviving slots, clamps main sets to the floor and accessory sets to the cap.
The resolver fills those slots only and never adds or removes a slot or a set.

- Role quality applies only to roles present. With `include_main` the retained essential slots
  are main and secondary; accessory-only has accessory criteria only and no main specificity or
  exposure criteria.
- A session without an eligible main lift records top-set status `not_applicable` by design,
  including under `required`; it is never `unsatisfied`.
- The weekly volume band is not a valid gate for these modes: both intentionally undershoot it.
  The gate is `not_applicable` (or is replaced by the shaped session's own target), and the
  level-4 distribution is neutral rather than undershoot or overshoot.
- For a minimum session the target minutes is a level-2 programme constraint, not a level-5
  tie-break. A candidate that would push the shaped session over target ranks below one that fits.
- The dwell cap, draw and bounded factor still apply per shaped slot, but the draw's last-choice
  key must be stable across shaped templates (pattern and role, or the exercise's own last used),
  not slot order, because the shape varies with target minutes and history.
- Structural ordering uses the shape's retained required patterns; accessory-only has none, so it
  reserves no coverage.
- Acceptance cases: a 30-minute accessory-only session (shape, accessory quality, top set
  `not_applicable`, gate neutral); a 45-minute session with the main lift (main quality, time
  target); `required` on accessory-only; and a candidate that would exceed the target.

### 5.8 Phone gateway and offline watch execution (later slice)

The watch is offline-capable only while the phone is online (D10). There is no pending-session
shell, no offline start without a reachable phone, and no new server lifecycle state.

- **Plan delivery.** The phone reads the watch-targeted plan (a plan is readable by its requester
  or its execution target) and pushes the full plan payload to the watch over
  WatchConnectivity. The watch caches it as its session snapshot.
- **Start.** The phone fetches the watch-targeted plan and performs the start with the watch
  token, so the server sees the watch as the execution device and the existing ownership, target,
  expiry and consumption checks run unchanged. The watch does not call the server.
- **Sync.** The phone relays the watch's queued set, event and finish bodies with the watch token
  and their original operation ids, so `(device_id, operation_id)` receipts deduplicate and a
  later direct retry cannot duplicate. The watch keeps operations pending until the phone
  confirms server acceptance, not merely receipt.
- **Fallback.** When the watch can reach the server directly it does so, as today. The gateway is
  additive, never the only copy.
- **Expired plan.** If the cached plan has expired when the athlete starts, the phone requests a
  fresh plan and waits for the asynchronous build; the watch shows a preparing state. The
  four-hour ready window is accepted and not extended.
- **Reliability.** WatchConnectivity delivery is queued and may be delayed; the phone may be
  suspended and must be launched or woken to run the relay. The watch shows a waiting state with
  a timeout and retry, and the contract's WatchConnectivity spike runs before this slice.
- **Prefill.** A substitution or addition prefill is server-solved (`resolve_replacement`). The
  execution row is the client's authoritative target for load, reps and RIR, so the phone and
  watch prefill the logging controls from it. A null prefill stays null and is never replaced by
  the original exercise's load. When the phone cannot reach the server, the event carries no
  prefill and the athlete enters the load as actual data; the client never computes it.
- **Security.** The watch token is handed over per session over WatchConnectivity and is not
  persisted at rest on the phone; the phone can revoke it. Relayed operations are recorded with
  both device identities.
- **No watch-originated substitutions** (D9). The watch renders and logs the phone-authored
  execution view; the phone is the only author of substitutions and additions.
- **Late substitution.** A substitution is accepted only before any set is attributed to the
  plan slot. After that it is rejected; the athlete continues the original item or logs extra
  work, and the replacement never inherits a partly completed slot.
- **Set identity.** A performed set is identified by `(exercise_id, set_index)`. The next index is
  allocated per performed exercise, not per plan slot, and an index reuse with a different
  payload is rejected rather than treated as an idempotent retry.

If neither device can reach the server and the watch cannot reach the phone, the session cannot
start. That is the accepted limitation of D10.

## 6. Implementation order

The work runs as nine packages in three release trains. Only the packages named as parallel may
overlap; the server foundation precedes every client step.

### 6.1 Work packages

- **WP0 — decisions and fixtures (done 2026-11-19).** Approve the role-quality class boundaries,
  family membership and recency window in versioned config with domain reasons; confirm the
  intelligence method names; add synthetic fixtures (legacy two-group role plan, straight-set
  plan performed as top-set/back-off, RIR-6 import row, deload and taper days); create the
  ROADMAP tracking entry. **Exit:** config approved, fixtures committed, no real
  data. **Evidence:** `config/resolver-role-quality.v1.yaml`,
  `tests/fixtures/resolver_structure/`, `tests/test_resolver_role_quality_config.py`,
  `DEC-RESOLVER-21`, ROADMAP §4.37.
- **WP1a — server ordered groups (done 2026-11-19).** `group_index`, serializers omit role,
  internal build-time role retained, validation 1..N, warm-up from the heaviest group,
  set-weighted intensity, persistence, legacy rows read by order. **Evidence:**
  `tests/test_ordered_set_groups.py`, `tests/test_top_set_engine.py`,
  `tests/test_top_set_storage.py`, `tests/test_web.py`, `tests/test_resolver_wiring.py`;
  the stored intensity is the set-weighted mean and the weekly spinal projection keeps the
  pre-structure value until its own measured comparison.
- **WP1b — server frozen plan (done 2026-11-20).** Remove the five plan-edit routes and core
  services; `plan_revision` becomes identity only; add substitution/addition events on
  `workout_event` with an execution watermark; migration `0073` adds
  `substitutes_plan_item_index` to `workout_set` and `clean_set`; execution view in
  `GET .../execution`; retire `plan_item_mismatch` for new sets; stop writing `set_role` and the
  role inputs. **Evidence:** `tests/test_execution_changes.py`, `tests/test_migration_0073.py`,
  `tests/test_ios_workflow.py`, `tests/test_ios_watch_ownership.py`, `tests/test_workout.py`;
  `DEC-RESOLVER-23`.
- **WP2 — clients (done 2026-11-20; owner-confirmed visual acceptance).** iPhone, Watch and web decode ordered groups,
  render one row per group, prefill by order and remove the plan-edit menus and role picker.
  Web prefill becomes group-aware before the picker is deleted. The watch renders the
  phone-authored execution view and merges by watermark; it never originates a substitution.
  **Done so far:** the web workout view is read-only and renders one unlabelled row per planned
  group in order (backend `7680ffb`); the iPhone/Watch branch decodes groups, prefills the next
  group by cumulative working sets, renders substitutions and additions, and merges the
  execution view by watermark (`StrengthApp` `resolver-structure-wp2`); verified with
  `scripts/ci.sh`, the watch simulator smoke run and the live phone UI acceptance test on
  2026-11-20. **Owner acceptance:** confirmed the visual two-group display and watch
  substitution on 2026-11-20. **Merged:** the client branch is merged into `development`
  (2026-11-20).
  **Depends on:** WP1a. **Exit:** two-group display and prefill on phone and watch, substitution
  appears on the watch, no plan-edit UI.
- **WP3 — tri-state intent (done 2026-11-20).** Settings/registry tri-state with default `off`,
  per-request `top_set_intent`, legacy `ask→off` / `on→required` normalised on load, frozen
  `{status, reason_code, reason}` with the applied loads, preferred fallback and required
  unsatisfied, client picker mapping; the boolean is removed. **Depends on:** WP1a.
  **Exit:** off/preferred/required tests, deload `not_applicable`, required fallback
  `unsatisfied`, closed iOS request schema. **Evidence:** `tests/test_top_set_engine.py`,
  `tests/test_top_set.py`, `tests/test_settings_profile.py`, `tests/test_web.py`,
  `tests/test_ios_workflow.py`, `tests/test_evaluator.py`, `tests/test_resolver_wiring.py`;
  `DEC-RESOLVER-24`.
- **WP4 — programme header (implemented 2026-11-20; latency check deferred).** One server
  helper; Today payload; the intelligence facts and registered methods; the AFC-4 nudge,
  weekly review and chat facts; iPhone and web display, including the AFC-4 review nudge on
  both; trained week and deload calendar week labelled separately.
  **Depends on:** WP0. **Exit:** Today and intelligence parity, no-history derivation, read-latency
  target. **Evidence:** `tests/test_programme_header.py`, `tests/test_nudges.py`,
  `tests/test_intelligence_weekly.py`, `tests/test_web.py`, `tests/test_ios_workflow.py`,
  `StrengthAppTests/Phase2ClientTests`; `DEC-RESOLVER-25`, `DEC-RESOLVER-26`. The real-data
  p50 measurement is deferred by the owner.
- **WP5 — actual data (done 2026-11-20).** Order matcher shared by adherence, VBT and structure
  analysis; substitution attribution; the RIR-6 warm-up invariant; config-backed segmented
  derived structure with ordinal confidence; role branches removed from matching. **Depends on:**
  WP1b. **Exit:** the 180×4 @RIR 1 + 160×5 @RIR 3 ×3 example, missing/extra/ambiguous cases, raw
  metrics untouched. **Evidence:** `tests/test_derived_structure.py`,
  `tests/test_actual_structure_adherence.py`, `tests/test_adherence.py`,
  `tests/test_vbt_analysis.py`, `tests/test_order_matching.py`; `DEC-RESOLVER-27`.
- **WP6 — evaluator (original 2026-11-20; owner accepted the original four A/B cases. Corrective closeout and stimulus extension accepted 2026-11-21).** Role-quality classes in config (no last-used continuity); six-level hierarchy with the volume gate; intensity profile; snapshot vector; fingerprint bump; fixed-history A/B with owner review of straight, top-set, substitution, divergent and the corrected full-template secondary/accessory cases. Enable only if it does not trade safety, band or time. **Done:** the lexicographic snapshot and beam key; response-only snapshot; fingerprint `prescription-input-v4`; class semantics `role-quality-v3`. The original four-case synthetic A/B changes the winner from `competition_squat` to `ssb_squat` in three cases, keeps the substitution unchanged, and keeps every case inside the band with zero time overrun; the owner accepted those four cases on 2026-11-20. **Corrective closeout (2026-11-21):** complementarity is relative to the selected main lift; secondary volume usefulness and accessory productive volume remove the candidate's sets from its own ledger group and reward a genuine deficit without rewarding excess; redundancy compares pattern/key/family/primary-muscle overlap with the main and other selected exercises, not set count; accessory coverage excludes the candidate's own slot; stimulus-to-fatigue uses a provisional 1-3 stimulus rating seeded from the evidence-graded local-muscular demand profile and the role-specific mandatory tax axes in a config matrix, with missing either input neutral and the provisional-rating limitation reported in the snapshot. The extended synthetic A/B adds full-template cases: secondary complementarity leaves the choice unchanged, secondary redundancy changes the support choice, accessory coverage changes the accessory choice, and accessory stimulus cost and a higher-stimulus case change the accessory choice; every finalist remains feasible, inside the band and with zero time overrun. The A/B is synthetic and does not claim generalisation. The owner accepted all nine A/B rows and approved the reviewed stimulus extension (`DEC-RESOLVER-32`) on 2026-11-21. **Performance:** `tools/resolver_benchmark.py --synthetic --case secondary_complementarity --runs 10` reports cold start, p50/p95, finalist evaluations, prescription builds, candidate count and beam truncation for the corrected path and the same builds with the role-quality snapshot disabled; the ODROID-C4 full-fixture measurement was p50/p95 3.183/3.194 s corrected and 3.018/3.144 s with the snapshot disabled, and the straight case measured 1.128/1.214 s and 0.921/1.179 s; the historical 1.21/1.24 s row is not a current guarantee. **Depends on:** WP1a and WP0. **Exit:** measured comparison and p50/p95 recorded; owner review complete (accepted 2026-11-21). **Evidence:** `tests/test_role_quality.py`, `tests/test_resolver_role_quality_config.py`, `tests/test_evaluator_ab.py`, `tests/test_evaluator_ab_report.py`, `python -m strength_coach.prescribe.evaluator_ab`, `tools/resolver_benchmark.py`, `DEC-RESOLVER-30`, `DEC-RESOLVER-31`, `DEC-RESOLVER-32`.
- **WP7a — resolver dwell completion (done 2026-11-20).** The cap, deterministic draw and bounded
  factor now order the production `candidate_pools`. The draw demotes the last choice within its
  structural pattern class instead of removing it; the last-choice key is the most recent working
  date per exercise, stable across shaped templates; all-at-cap keeps the pool; coverage remains
  the beam's structural reserve. The factor changes the beam's rank cost, not the evaluator's
  winner. **Depends on:** WP1a and WP0; can run in parallel with WP6. **Evidence:**
  `tests/test_generator.py`, `docs/DWELL-AND-ROTATION.md`, `DEC-RESOLVER-29`.
- **WP7b — structural ordering and measurement (done 2026-11-20; owner accepted the comparison).**
  Family and catalogue ordering; fixed-history comparison of cap-only, cap plus draw, and cap
  plus draw plus bounded factor; a pure-factor variant only as a rejected reference; no beam or
  cap widening without evidence. **Done so far:** the synthetic squat comparison moves the later
  `competition_squat` ahead of `ssb_squat` in the draw and full orders while the evaluator still
  selects `ssb_squat`; every variant stays feasible, inside the band, with zero time overrun. The
  pure-factor order is recorded as rejected. **Depends on:** WP7a; measured separately from WP6.
  **Exit:** a later-catalogue candidate is not excluded by position; selection changes and outcome
  metrics recorded; owner review complete. **Evidence:** `tests/test_generator.py`,
  `tests/test_dwell_ab.py`, `python -m strength_coach.prescribe.dwell_ab`.
- **WP8 — gateway (done 2026-11-21; owner-accepted).** The phone relay is implemented with the
  watch token, original operation ids, direct-first fallback, per-operation acknowledgement and
  waiting/timeout states; plan push carries the frozen plan and execution view. The physical run
  started a watch-owned session with the watch unable to reach the server, relayed the set, form
  and finish, and recorded one set with no duplicate. **Depends on:** WP2. **Exit met:** watch
  starts and syncs with the server unreachable but the phone reachable; no duplicates;
  offline-from-both remains a documented limitation. **Evidence:** `WatchRelayModels.swift`,
  `WatchRelayTests`, `WatchRelayGatewayTests`, `docs/WATCH-GATEWAY.md`; physical run on
  ODROID development 2026-11-21.

- **WP9 — documentation and algorithm reference (done 2026-11-21).** Publish one canonical
  reference for the resolver algorithm and workout selection: the end-to-end pipeline, the formulas
  (dwell factor, draw and cap; volume projection and band; role-quality class vector and
  hierarchy; top-set load, RIR and back-off; warm-up; minimum-session time estimate; fingerprint
  and snapshot), a code map with links to the exact files and functions, and worked examples for
  straight sets, top set, deload, taper, minimum session, accessory-only, substitution and derived
  structure. Update every affected document; archive or add superseding pointers to old documents;
  remove links to superseded documents from `AGENTS.md`, the docs index, agent prompts and the
  manifest so agents load only the canonical set; run the docs manifest, consistency, link and
  heading checks. **Depends on:** WP1–WP8. **Exit:** a new reader can trace template → pool → beam
  → winner from the formulas and examples alone; every example is mirrored by a test or fixture;
  no stale canonical links remain; docs checks pass. **Done:** `RESOLVER-ALGORITHM.md` rewritten
  with the production pipeline, formulas, code map and the nine worked examples; specialist
  documents point to it; manifest and index updated; docs checks pass.

### 6.2 Release trains

- **Release A — structure and context:** WP1a, WP1b, WP2, WP3, WP4. This is the only coordinated
  cutover, because the plan-edit routes and the request schema change. Finish or abandon in-flight
  workouts first; apply migration `0073`; no dual protocol and no capability negotiation.
  **Status:** deployed to the production ODROID from `development` at `5a3c1df` on
  2026-11-21; `main` not merged or tagged.
- **Release B — actual data and evaluation:** WP5, WP6, WP7a, WP7b. Server-only; no client change.
  **Status:** WP5–WP7b complete 2026-11-20; both the evaluator A/B and the dwell ordering
  comparison were owner-accepted. Release B is complete on `development`. The WP6 corrective
  closeout is a source-only correction on `development`; it does not change the deployed SHA or
  the historical release record.
- **Release C — gateway:** WP8. Additive and independent; it can follow Release A without blocking
  Release B. **Status:** complete 2026-11-21; owner accepted the physical relay run with no
  follow-ups.
- **Release D — documentation closeout:** WP9. **Status:** complete 2026-11-21; the canonical
  algorithm reference is published and the docs checks pass.

### 6.3 Verification per package

Every package runs its narrowest backend tests and `ruff check` for the changed area, and a
migration test on a database copy when schema changes. Client packages run the narrowest Swift
tests plus the web UI checks. WP7a adds the dwell unit tests (draw determinism, cap fallback,
coverage preservation). WP6 adds the corrected fixed-history comparison, owner review and p50/p95 (measured on the MacBook and ODROID-C4),
measured separately; WP7b adds its own pool-order comparison; WP8 adds the WatchConnectivity
spike and a physical-device run. WP9 runs the
docs manifest, consistency, link and heading checks and requires every worked example to be
mirrored by a test or fixture. No package claims completion from code presence; the backend
ROADMAP records status only with that evidence.

## 7. Acceptance

**Functional**

- A top-set plan displays and prefills two different target rows on iPhone and Watch and is not
  collapsed to the item-level load.
- `off`, `preferred` and `required` take distinct, tested paths; `required` with an unexpected
  blocker returns a startable plan marked `unsatisfied` with a reason; `preferred` falls back with
  `fallback` and its reason; a deload is `not_applicable`, not unsatisfied.
- The default is `off`, so existing effective behaviour is preserved; only an explicit
  `preferred` or `required` requests a top set.
- The plan cannot be edited after start; a substitution or addition appears in the watch view and
  is attributed on the performed sets; no plan route mutates the plan.
- Today shows trained week and deload calendar week separately, DUP only when enabled and
  anchored, the correct deload status and a competition countdown only for a future date.
- The same header facts reach the intelligence facts without LLM calculation.
- Role quality is role-specific: a main-lift candidate with better specificity, exposure
  adequacy or suitability beats an otherwise comparable candidate; a secondary candidate that
  complements the selected main lift and adds less redundancy wins; a secondary candidate that
  fills a genuine pattern-volume deficit beats one that adds redundant volume; an accessory that
  covers an otherwise uncovered pattern wins, and at equal coverage the stimulus-to-fatigue
  matrix prefers higher stimulus at lower mandatory-axis cost while leaving incomparable
  trade-offs neutral; missing data is neutral. The stimulus rating is provisional and seeded
  from the evidence-graded local-muscular demand profile, not a measured magnitude, and the
  snapshot reports that limitation.
- Dwell rotation is live in the resolver: the cap, the deterministic draw and the bounded factor
  order the pool; the all-at-cap fallback keeps it; the draw never removes the only candidate for
  a required pattern; role quality does not score dwell or last used.
- The volume band is a gate: a candidate outside it ranks below every inside-band candidate, and
  inside-band candidates are decided by role quality, not by set-count closeness.
- The programme header is not an evaluator input: the evaluator reads the applied context from
  the build and its notes.

**Safety and invariants**

- Hard feasibility, assignment preservation, spinal, constraint, injury, unknown and
  executability checks are unchanged.
- The engine remains the only source of loads, reps, RIR, warm-ups, structure and deload.
- No named phases, per-muscle targets, composite score, set role in the payload, persistence or
  API, or manual role entry is introduced; the engine's build-time internal tag is never
  serialized.
- Role quality never outranks hard feasibility, programme intent or the volume gate.
- Each signal affects the result once: the dwell layer orders the pool; role quality does not
  re-score repetition or last used.
- Raw actual sets are never rewritten; working-set volume and e1RM are unchanged.

**Actual data**

- A skipped planned group is missing, not performed; extra work stays visible; a substitution is
  attributed to its planned slot; ambiguous data remains unknown.
- Missing RIR or e1RM limits the analysis to unknown or reduced confidence, never a guess.
- Warm-ups are exactly the RIR-6 rows: excluded from working volume, matching and derived working
  structure; a stored working flag that disagrees is reported as an anomaly; a missing RIR is
  unknown, not a warm-up; an import cannot turn a working set into RIR 6.
- Derived structure identifies a top-set-like exposure plus back-off sequence from the recorded
  loads, reps and RIR even when the plan prescribed straight sets, with an ordinal confidence; a
  straight-set plan performed as 180×4 @RIR 1 then 160×5 @RIR 3 ×3 is not merely "descending".
- Derived structure never changes raw sets, working-set volume, e1RM or fatigue metrics and has no
  training-policy effect.

**Performance**

- A single-structure build per intent: no dual evaluation, no resolver budget increase.
- Today and the programme header stay within the existing read latency target; the header does
  not load history.
- Role quality uses the single build per assignment; it does not add evaluations or a second
  resolver pass.
- The corrected WP6 benchmark reports cold start, steady-state p50/p95, finalist evaluations,
  prescription builds, candidate count and beam truncation for the corrected path and for the
  same builds with the role-quality snapshot disabled. It is reproducible with
  `tools/resolver_benchmark.py --synthetic --case secondary_complementarity --runs 10`. The
  MacBook measurement on 2026-11-21 (20 steady-state runs, full fixture, `role-quality-v3`) was
  corrected p50/p95 0.218/0.224 s and 0.204/0.210 s for the same builds with the role-quality
  snapshot disabled. On the ODROID-C4 (Linux 6.18.44 aarch64, Python 3.13.5, 4 CPUs) the same
  fixture measured 3.183/3.194 s corrected and 3.018/3.144 s with the snapshot disabled; the
  straight case measured 1.128/1.214 s and 0.921/1.179 s. Both hosts evaluated 2 finalists and
  built 2 prescriptions. The historical 1.21/1.24 s row is not a current guarantee.
- Candidate ordering and each dwell variant are measured before any beam or cap change.

**Documentation**

- One canonical reference covers the pipeline, the formulas, a code map with file and function
  links, and worked examples for straight sets, top set, deload, taper, minimum session,
  accessory-only, substitution and derived structure.
- Every formula and example is mirrored by code or a fixture; links resolve; the docs manifest,
  consistency, link and heading checks pass.
- Superseded documents carry a pointer or are archived, and `AGENTS.md`, the docs index, agent
  prompts and the manifest link only the canonical set.

**Evidence**

- Fixture tests are necessary but not sufficient. Run the current and proposed paths over a fixed
  copy of representative history and have the owner review straight-set, top-set, substitution
  and divergent workouts before the opt-in intents and the hierarchy are relied on.
- The backend roadmap and this plan record status only with that evidence.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Profiles that stored `on` now read as `required` and will flag unexpected fallbacks | Documented compatibility mapping; the evidence review and the plan record it; `off` remains available. |
| A stale watch renders a structured plan as its back-off load | No compatibility is claimed; apps and server ship together, and the gateway phase keeps the direct path. |
| WatchConnectivity delivery is delayed or the phone is suspended | Waiting state with timeout and retry; the WatchConnectivity spike runs first; the direct watch path remains. |
| Programme header drifts from engine context | One server-side helper, one source of week definitions, reused by Today and intelligence facts. |
| Role quality trades safety, volume or time for specificity | It ranks after feasibility, intent and the volume gate; neutral when data is missing; enabled only with the fixed-history comparison. |
| Role criteria become a second scoring engine | Fixed role table, deterministic classes, one owner per signal, no weighted total. |
| The corrected role classes overfit a small synthetic A/B | Evidence is explicitly synthetic and does not claim generalisation; unit tests pin each class's direction and missing-data neutrality; the owner reviews every A/B row; no beam, cap or budget change. |
| The provisional stimulus rating overfits the demand profile | It is seeded from the evidence-graded `local_muscular` profile plus taxonomy flags; only demand-rated exercises are rated; missing data is neutral; the config test pins the rubric and coverage; the owner reviews the A/B rows. |
| Dwell and role quality double-count repetition | Role quality does not score dwell or last used; the dwell layer owns repetition. |
| A pure dwell factor overrides readiness, fatigue or spinal cost | The factor orders only within a structural class, after required-pattern coverage; a pure sort is a rejected reference. |
| The exploration draw removes the only candidate for a required pattern | Coverage precedes the draw, and the beam still reserves required-pattern candidates when it truncates. |
| Wiring the dwell layer changes production selection | Fixed-history comparison of cap-only, cap plus draw, and cap plus draw plus factor; no beam or cap widening; owner review. |
| The header becomes a second source of applied context | Reporting only; evaluation reads the build inputs and the built prescription's notes. |
| Derived structure becomes a role taxonomy | Segmented description with ordinal confidence; never stored on raw sets; no metric or policy effect. |
| The RIR-6 convention is broken by an import or manual edit | The invariant is checked; conflicts are reported as anomalies; an import may not manufacture RIR 6 for a working set. |
| Candidate ordering changes search results | Deterministic rules, explicit thresholds, measured before and after. |
| Documentation drifts from the shipped algorithm | WP9 rewrites the canonical reference from the shipped code; every worked example is mirrored by a test or fixture; docs checks run in CI. |
| Superseded documents stay linked by agents | WP9 audits `AGENTS.md`, the docs index, prompts and the manifest, archives or points retired documents, and keeps only the canonical set in agent entry points. |
| Substitution events arrive after the sets | The performed set is self-describing and is the durable attribution; the event is a view hint. |
| Legacy plans with role-based groups | Read by list order; no rewrite, no dual write path. |

## 9. Out of scope

- Named phase model or automatic phase transitions; periodisation engine; resolver V2.
- Using the programme header as an evaluator input; a weighted composite role score or a second
  scoring engine.
- Per-muscle volume targets; composite strength-stimulus score.
- Plan editing after start.
- Storing an inferred set role on raw sets; manual role entry; training-policy use of derived
  structure without a separate decision.
- Watch-originated substitutions or additions.
- Pending-session shell or a start with neither device online.
- LLM-calculated programme context.
- Destructive migration or historical-row rewrite.

## 10. Documentation and status ownership

- Backend implementation status and phase completion belong in the backend
  [ROADMAP.md](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md).
- Backend decisions, including the tri-state and its default, the frozen plan, the substitution
  model, the ordered groups, the role-quality hierarchy and the dwell ownership of repetition, are
  recorded in
  [DECISIONS.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/DECISIONS.md).
  New entries supersede the plan-edit decisions (`DEC-IOS-04`, `DEC-IOS-08`, `DEC-IOS-09`).
- Backend references updated with the implementation: `RESOLVER-ALGORITHM.md`,
  `RESOLVER-MAIN-LIFTS-VS-ACCESSORIES.md`, `DWELL-AND-ROTATION.md` (resolver wiring status and
  bounded ordering), `TOP-SET-BACKOFF-EVIDENCE.md` (mode reference and opt-in default retained),
  `API.md` (today, workouts, add-set, execution, removed plan routes), `DATA-MODEL.md` (annotation
  columns and legacy columns), `DATA-QUALITY.md` (RIR-6 and import semantics), `WEB-UI.md` (plan
  editing and role picker removed), `USER-GUIDE.md` and `ROADMAP.md`.
- The canonical algorithm and selection reference is `RESOLVER-ALGORITHM.md`, rewritten in WP9
  with the formulas, code map and worked examples. `DWELL-AND-ROTATION.md` remains the dwell detail
  linked from it; superseded forward plans are archived or reduced to pointers. `AGENTS.md`, the
  docs index, agent prompts and the manifest link only the canonical set, so an agent does not
  load retired documents.
- Shared contracts and plans updated before implementation: R7 (plan payload, tri-state override,
  execution view, today header), R8 (plan edits retired; closed record preserved with a
  superseding note), watch (D3, D12, §10 revision/conflict rules, §21 relay now planned, execution
  view, phone start), the [iOS client plan](IOS-CLIENT-PLAN.md) (R8 note), the
  [training-intelligence contract](../contracts/TRAINING-INTELLIGENCE-CONTRACT.md) (new fact
  methods) and the contract index.
- iPhone and Watch implementation, build and physical-device acceptance remain in the client
  repository.
- This plan is the canonical cross-repository statement; status changes only with evidence.

## 11. Cutover

- Server, iPhone and Watch ship together; no dual protocol, no capability negotiation.
- Finish or abandon in-flight workouts before the cutover; a plan started under the old shape is
  read by list order and is never edited.
- One additive migration `0073`: a nullable `substitutes_plan_item_index` on `workout_set` and
  on `clean_set`, copied during materialisation, plus one unique index on the client change
  identity in `workout_event`. No destructive change, no backfill.
- Plan-edit routes and role inputs are removed in the same cutover; legacy role columns stay
  read-only provenance and are not used for matching or decisions.
- Profiles without an explicit intent take the default `off`, preserving the previous effective
  behaviour; explicit `ask` reads as `off` and `on` as `required`.
