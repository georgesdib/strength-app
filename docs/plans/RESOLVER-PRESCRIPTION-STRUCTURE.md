# Resolver prescription structure and programme context

**Status:** proposed 2026-11-19 (revised after owner review); not implemented.
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
  set role;
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
| D4 | Groups are identified by order. No role field is required, stored or inferred. Straight sets are emitted as an empty list; a single full-item group is accepted on read. |
| D5 | Top-set intent is one tri-state: `off`, `preferred`, `required`. It lives in the settings profile with an optional per-request override. Default `required`; legacy `ask` reads as `off`, legacy `on` as `required`. |
| D6 | `preferred` builds the structured prescription when the lift is eligible and unblocked, otherwise straight sets with a reason. `required` does the same but marks an unexpected blocker as unsatisfied. Neither evaluates two structures. |
| D7 | The plan is immutable once started. Plan editing is removed; there is no plan swap, add, remove, reorder or set-count edit. |
| D8 | Substitution and addition are execution concepts, not plan edits: an append-only execution event plus a per-set attribution field. The performed set is the durable record. |
| D9 | The watch does not originate substitutions. It renders the phone-authored execution view and logs sets against it. |
| D10 | The watch is offline-capable only while the phone is online. There is no pending-session shell and no start without a reachable phone or server. |
| D11 | Set-role input is removed from every logging surface. Legacy role columns and values remain unread history. |
| D12 | The programme header is a server-computed reporting model reused by Today and intelligence facts; it labels trained week and calendar deload week separately and is not an evaluator input. |
| D13 | Evaluation is a deterministic, role-aware hierarchy, not a composite score, and reuses the existing intensity, exposure, volume, suitability and tie-break definitions. |
| D14 | Candidate ordering is slot-role aware, deterministic and measured before any beam or cap change. |
| D15 | This plan supersedes the "no default programme change" conclusion of the top-set evidence review and the R8 plan-edit surface; both documents are amended with it. |
| D16 | Programme context reaches evaluation through the applied build and its notes, never through the header. |
| D17 | Main, secondary and accessory assignments are ranked by deterministic role-quality classes (specificity, continuity, exposure adequacy, suitability, complementarity, redundancy, coverage, stimulus-to-fatigue). One owner per signal, volume as a gate, no composite, and only with measured evidence. |

## 4. Current state

- `prescribe/resolver.py` runs candidate pools, a bounded beam, full evaluation, integrity
  checks and snapshot provenance. `prescribe/engine.py` remains authoritative for load, reps,
  RIR, readiness, continuity, deload, volume, spinal exposure, top sets, warm-ups and validation.
- `prescribe/top_set.py` produces one top set plus one back-off group for the session primary
  main lift, and sets the item-level `load_kg` to the back-off load.
- The plan payload already contains `set_groups` (roles `top_set`/`back_off`), but the shared
  Swift `PrescriptionItem` does not decode it, so iPhone and Watch show the back-off load only.
- `validate_plan_set_groups` requires a unique role, rejects any other shape, and plan editing
  paths resize groups; there are five core plan-edit functions and matching web/iOS routes.
- `set_role` is an optional input in the web logging path and is used to choose a group target
  in `workout.py`, `adherence.py` and `features/vbt_analysis.py`. The iOS add-set schema does
  not accept it.
- `GET /api/ios/v1/today` returns date, readiness, score, active workout and plan state, but
  not trained week, DUP, deload or competition.
- The watch start gate requires a successful server call; the phone relay is explicitly
  deferred. Idempotency receipts are scoped `(device_id, operation_id)`, and a plan is readable
  by its requester or its execution target.

## 5. Target model

### 5.1 Frozen plan and execution view

A plan is a preview until it is started. Before start, changing parameters means issuing a new
plan request (the R7 supersede path); that is not a plan edit. After start the plan is frozen:
no route mutates `plan_json`, and `plan_revision` stops being a plan-edit counter.

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
- no role is stored or required; the wire accepts 1..N groups and the engine emits only the
  top-set + back-off structure (D3);
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
- validation accepts 1..N groups, enforces the sum invariant and requires numeric loads; role
  is ignored. Legacy rows with roles are read by list order.

Plan-edit resize rules are deleted with the edit paths (D7), so no structure rule has to survive
an edit.

### 5.3 Top-set intent

One tri-state, resolved as: per-request override, else the settings-profile value, else the
registry default `required`.

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
`required`. Profiles that never stored a value take the new default; this is accepted and
recorded as a programme change (D15).

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
- The same structure is one fact block in the existing programme-context intelligence resource,
  with the existing method names, and is available to nudge, weekly-summary and chat dossiers.
  The LLM may explain it; it may not compute or alter it.

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
   competition effects; the level reads their outcome and does not re-score them. Its continuity
   class is exercise-level (dwell and last used, e1RM recency), not a second load adjustment.

   | Role | Ranking criteria | Source |
   |---|---|---|
   | Main | Specificity class (same lift, same family, same pattern, comparable pattern); continuity (dwell and last used, e1RM recency); heavy-exposure adequacy (band plus e1RM confidence, not a point estimate); technical suitability (ratings, technique throttle, form) | taxonomy and lift family, dwell counts, e1RM age and quality, lift readiness, form assessment, suitability |
   | Secondary (support) | Complementarity with the chosen main lift's pattern and primary muscles; usefulness to the volume band; redundancy and fatigue cost | taxonomy patterns and primary muscles, volume ledger, existing redundancy penalty, spinal and fatigue, selection tax |
   | Accessory | Coverage of otherwise uncovered patterns and muscles (counts, not doses); productive volume per unit time; stimulus-to-fatigue | taxonomy, volume ledger, selection tax, time estimate |

   Within a role, order the criteria as listed; across roles, order role priority first (main,
   then secondary, then accessory). Missing data is neutral, never a guess, and power slots are
   excluded from quality ranking because their intent is fixed by the quality stop.
4. **Volume adequacy and distribution** — only within the band: closeness to target, pattern
   balance, and no pattern left badly short. The symmetric volume error is removed.
5. **Recovery and practicality** — session time, fatigue and spinal context, warnings.
6. **Deterministic tie-break** — the existing resolver tie-break, then stable assignment order.
   History continuity is not re-added here; it is owned by role quality and must not also order
   the pool.

Implementation notes:

- one owner per signal: the resolver pool is ordered structurally (pattern coverage, family,
  catalogue) and the evaluator owns specificity, continuity, redundancy and suitability; injury,
  can_do and suitability vetoes remain eligibility filters, not quality points;
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
- no composite score, no per-muscle dose and no second scoring engine.

### 5.6 Actual data and sequence analysis

The athlete records exercise, actual load, reps or seconds, RIR/RPE where available, velocity
where available, and optional feedback. No role is requested, stored or inferred.

Classification and matching use:

- ordered actual sets (`set_index`, `created_at` which carries the client's performed time);
- the frozen plan's ordered groups and the item identity;
- load, reps and RIR, plus any group annotation;
- warm-up rows, identified by RIR 6 or the stored working-set flag, which are excluded from
  group matching.

One matcher is shared by adherence, VBT and the sequence analysis. For each planned group it
reports `matched`, `missing`, `extra`, `ambiguous` or `unknown`, using load tolerance (one
rounding increment), rep range and RIR tolerance. It never infers a top set because the plan had
one. A substituted set is matched to the planned slot through `substitutes_plan_item_index`; an
addition is extra work.

The server may derive a descriptive actual sequence:

- `constant`, `ascending`, `descending`, `ascending_then_descending`, `multiple_heavy`,
  `irregular`, or `insufficient_data`;
- loads within one rounding increment count as equal;
- `multiple_heavy` means two or more working sets at or above the existing heavy intensity band,
  or at RIR 1 or lower when e1RM is unavailable; when neither is available the descriptor is
  `unknown`;
- fewer than two working sets with usable loads is `insufficient_data`.

These are post-workout descriptions. They never rewrite raw sets, working-set volume, e1RM or
fatigue metrics, and they are not a role taxonomy.

### 5.7 Candidate diversity

Retain the bounded beam and full evaluation. The candidate cap stays at its current width until a
measured change justifies otherwise.

- The generator orders each slot's pool deterministically before the beam cap: candidates required
  for movement-pattern coverage first, then the slot's structural family, then catalogue order as
  the final tie-break. History, continuity, readiness and suitability are owned by role quality
  (D17) and must not also order the pool.
- The beam already reserves required-pattern candidates when it truncates; that behaviour is kept.
- Pool order is the beam's rank cost, so reordering changes the search trajectory, not only the
  shortlist. The change is measured on a fixed history before and after.
- Structural family membership is an explicit config rule, not a judgement call; no history or
  recency threshold is added to the pool.

### 5.8 Phone gateway and offline watch execution (later slice)

The watch is offline-capable only while the phone is online (D10). There is no pending-session
shell, no offline start without a reachable phone, and no new server lifecycle state.

- **Plan delivery.** The phone reads the watch-targeted plan (a plan is readable by its requester
  or its execution target) and pushes the full plan payload to the watch over
  WatchConnectivity. The watch caches it as its session snapshot.
- **Start.** The phone performs the start with the watch token, so the server sees the watch as
  the execution device and the existing ownership, target, expiry and consumption checks run
  unchanged. The watch does not call the server.
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
- **Security.** The watch token is handed over per session over WatchConnectivity and is not
  persisted at rest on the phone; the phone can revoke it. Relayed operations are recorded with
  both device identities.
- **No watch-originated substitutions** (D9). The watch renders and logs the phone-authored
  execution view; the phone is the only author of substitutions and additions.

If neither device can reach the server and the watch cannot reach the phone, the session cannot
start. That is the accepted limitation of D10.

## 6. Implementation order

The slices ship together with the apps; there are no compatibility gates or dual protocols.

1. **Groups and frozen plan.** Add ordered groups end to end, fix warm-up and intensity from
   groups, validate 1..N, render and prefill groups on iPhone, Watch and web, remove plan editing
   and role pickers, and add the substitution/addition execution view with the one additive
   `workout_set` annotation column; `plan_modified_json` becomes legacy-only.
2. **Top-set intent.** Add the tri-state, profile default and per-request override, legacy
   normalisation, structure status and reason codes; amend the evidence review and record the
   decision.
3. **Programme header.** Add the header to Today and the intelligence fact block with the two
   week definitions and the deload status rules.
4. **Actual data.** Add order-based matching, substitution attribution and the sequence
   descriptors; stop accepting or writing roles; keep legacy role columns unread.
5. **Evaluation.** Add the role-aware hierarchy, the role-quality criteria, the intensity profile
   and the volume gate and distribution; keep hard feasibility first and remove the symmetric
   volume error. Role quality is enabled only with the fixed-history comparison.
6. **Candidate ordering.** Add the deterministic shortlist ordering and measure it on a fixed
   history before and after.
7. **Gateway (later).** Plan push, relayed start and sync, waiting states and the
   WatchConnectivity spike.

## 7. Acceptance

**Functional**

- A top-set plan displays and prefills two different target rows on iPhone and Watch; a synthetic
  three-group fixture displays three and is not collapsed to the item-level load.
- `off`, `preferred` and `required` take distinct, tested paths; `required` with an unexpected
  blocker returns a startable plan marked `unsatisfied` with a reason; a deload is
  `not_applicable`, not unsatisfied.
- The plan cannot be edited after start; a substitution or addition appears in the watch view and
  is attributed on the performed sets; no plan route mutates the plan.
- Today shows trained week and deload calendar week separately, DUP only when enabled and
  anchored, the correct deload status and a competition countdown only for a future date.
- The same header facts reach the intelligence facts without LLM calculation.
- Role quality is role-specific: a main-lift candidate with better specificity, continuity or
  suitability beats an otherwise comparable candidate; a secondary candidate that complements the
  main lift and adds less redundancy wins; an accessory that covers an uncovered pattern at lower
  fatigue wins; missing data is neutral.
- The volume band is a gate: a candidate outside it ranks below every inside-band candidate, and
  inside-band candidates are decided by role quality, not by set-count closeness.
- The programme header is not an evaluator input: the evaluator reads the applied context from
  the build and its notes.

**Safety and invariants**

- Hard feasibility, assignment preservation, spinal, constraint, injury, unknown and
  executability checks are unchanged.
- The engine remains the only source of loads, reps, RIR, warm-ups, structure and deload.
- No named phases, per-muscle targets, composite score or set-role inference is introduced.
- Role quality never outranks hard feasibility, programme intent or the volume gate.
- Each signal affects the result once: history and continuity order the evaluator, not the pool.
- Raw actual sets are never rewritten; working-set volume and e1RM are unchanged.

**Actual data**

- A skipped planned group is missing, not performed; extra work stays visible; a substitution is
  attributed to its planned slot; ambiguous data remains unknown.
- Missing RIR or e1RM yields unknown or limited output, never a guess.
- Warm-up rows are excluded from group matching.

**Performance**

- A single-structure build per intent: no dual evaluation, no resolver budget increase.
- Today and the programme header stay within the existing read latency target; the header does
  not load history.
- Role quality uses the single build per assignment; it does not add evaluations or a second
  resolver pass.
- Candidate ordering is measured before any beam or cap change.

**Evidence**

- Fixture tests are necessary but not sufficient. Run the current and proposed paths over a fixed
  copy of representative history and have the owner review straight-set, top-set, substitution
  and divergent workouts before the default and the hierarchy are relied on.
- The backend roadmap and this plan record status only with that evidence.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Default `required` changes the programme | Recorded in the decision log; the evidence review is amended; the previous behaviour remains available with `off`. |
| A stale watch renders a structured plan as its back-off load | No compatibility is claimed; apps and server ship together, and the gateway phase keeps the direct path. |
| WatchConnectivity delivery is delayed or the phone is suspended | Waiting state with timeout and retry; the WatchConnectivity spike runs first; the direct watch path remains. |
| Programme header drifts from engine context | One server-side helper, one source of week definitions, reused by Today and intelligence facts. |
| Role quality trades safety, volume or time for specificity | It ranks after feasibility, intent and the volume gate; neutral when data is missing; enabled only with the fixed-history comparison. |
| Role criteria become a second scoring engine | Fixed role table, deterministic classes, one owner per signal, no weighted total. |
| A signal is counted twice (pool order and role quality) | History and continuity order the evaluator only; the pool stays structural. |
| Role quality freezes exercise variety | Continuity is one class among several, not a bonus; the existing dwell policy still bounds repetition; measured. |
| The header becomes a second source of applied context | Reporting only; evaluation reads the build inputs and the built prescription's notes. |
| Sequence descriptors become a role taxonomy | Descriptive only, post-workout, no inference, no metric rewrites. |
| Candidate ordering changes search results | Deterministic rules, explicit thresholds, measured before and after. |
| Substitution events arrive after the sets | The performed set is self-describing and is the durable attribution; the event is a view hint. |
| Legacy plans with role-based groups | Read by list order; no rewrite, no dual write path. |

## 9. Out of scope

- Named phase model or automatic phase transitions; periodisation engine; resolver V2.
- Using the programme header as an evaluator input; a weighted composite role score or a second
  scoring engine.
- Per-muscle volume targets; composite strength-stimulus score.
- Plan editing after start.
- Generalised actual set-role inference; manual role entry.
- Watch-originated substitutions or additions.
- Pending-session shell or a start with neither device online.
- LLM-calculated programme context.
- Destructive migration or historical-row rewrite.

## 10. Documentation and status ownership

- Backend implementation status and phase completion belong in the backend
  [ROADMAP.md](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md).
- Backend decisions, including the tri-state, the frozen plan, the substitution model and the
  default change, are recorded in
  [DECISIONS.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/DECISIONS.md).
- Backend references updated with the implementation: `RESOLVER-ALGORITHM.md`,
  `RESOLVER-MAIN-LIFTS-VS-ACCESSORIES.md`, `TOP-SET-BACKOFF-EVIDENCE.md` (supersede the default
  conclusion), `API.md` (today, workouts, add-set, execution, plan), `DATA-MODEL.md` (the
  annotation column) and `ROADMAP.md`.
- Shared contracts updated before implementation: R7 (plan payload, tri-state override, execution
  view), R8 (plan edits superseded), watch (§10 revision/conflict rules, §21 relay deferral now
  planned, execution view) and the contract index.
- iPhone and Watch implementation, build and physical-device acceptance remain in the client
  repository.
- This plan is the canonical cross-repository statement; status changes only with evidence.

## 11. Cutover

- Server, iPhone and Watch ship together; no dual protocol, no capability negotiation.
- Finish or abandon in-flight workouts before the cutover; a plan started under the old shape is
  read by list order and is never edited.
- One additive migration: a nullable `substitutes_plan_item_index` on `workout_set` (and the
  clean-set materialisation if it carries attribution). No destructive change, no backfill.
- Plan-edit routes and role inputs are removed in the same cutover; legacy columns stay unread.
- Profiles without an explicit intent take the new `required` default; explicit `ask` reads as
  `off` and `on` as `required`.
