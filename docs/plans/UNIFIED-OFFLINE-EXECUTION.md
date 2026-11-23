# Unified offline workout execution

**Status:** draft for owner review, 2026-11-23. **No implementation has started.**
**Gate:** this is the WP0 document required by `AGENTS.md` before an architectural refactor. Work packages start only after owner approval of this document and of the contract amendments in §13.
**Owner decisions are recorded in §4.** Anything marked *proposed* has not been applied to a canonical document.

## 1. Purpose

Redesign workout execution so the iPhone and Apple Watch can each start, execute and complete an
issued workout with no internet connection and no connection to the other device, while keeping
one logical history, never losing or duplicating a set, and reconciling deterministically when the
devices next meet. Python remains the downstream authority for prescription, resolver output,
analytics and training intelligence.

"Offline" here means: after the plan has been issued and downloaded, nothing in execution requires
the home server or the other device. It does not mean offline plan generation.

## 2. Relationship to existing documents

- **Supersedes** [RESOLVER-PRESCRIPTION-STRUCTURE.md](RESOLVER-PRESCRIPTION-STRUCTURE.md) §5.8
  ("Phone gateway and offline watch execution"). That section's D10 limitation — the watch is
  offline-capable only while the phone is online — is the thing this plan removes.
- **Amends** [IOS-WATCH-CONTRACT.md](../contracts/IOS-WATCH-CONTRACT.md) §8 (start gate), §9
  (ownership), §10.4 (mismatch policy), §14 (server API), §21 (deferred). Amendment text is in
  §13; it is not applied until approved.
- **Amends** [IOS-CLIENT-PLAN.md](IOS-CLIENT-PLAN.md) §5 (offline behaviour table), which still
  says a start requires server connectivity.
- **Keeps** the technique-throttle modifier (MOD-TECH-001) and the execution-change model
  (DEC-RESOLVER-23) as the basis for offline plan changes.

## 3. Baseline verified on 2026-11-23

Read from the code, not inferred:

- The server rejects writes from a non-owner device: `409 not_owner` (contract §9). Ownership is
  set at start and transferred by `POST .../takeover`.
- A performed set is identified by `(exercise_id, set_index)`; an omitted index is allocated as
  `MAX(set_index) + 1` per exercise, and a reused index with any different field is rejected as
  `set_index_conflict` (`workout.py` `add_set`). A full field match is treated as a replay.
- A completed workout rejects new sets (`workout.py`, `add_set` status guard).
- Substitution/add prefill is solved by the server at arrival through
  `prescribe_engine.resolve_replacement`; the client cannot send a load and an offline author gets
  `prefill_load_kg: null` with `prefill_reason: authored_offline` (`workout.py` `_change_prefill`).
- `resolve_replacement` builds the item but skips the session-level back-flare effort and dose
  modifiers, so a substitute in a flare session currently receives an unmodified load.
- The iOS prescription settings schema is closed: `session_type`, `minimum_session`,
  `minimum_target_minutes`, `top_set_intent` (`server.py` `_ios_request_settings`). The web
  prescription path already accepts `technique_throttle` and `technique_throttle_pattern`.
- The watch today relays execution writes through the phone, or reaches the server directly when
  it can. It keeps a durable local operation queue, stamps time from a server-derived clock offset,
  and has a stored server execution view with a watermark.
- The phone has a durable pending-mutation journal (capped at 16 entries, 28-day replay window) and
  a separate offline capture store. Both are queue semantics, not ledger semantics.

## 4. Decisions

| ID | Decision | Why |
|---|---|---|
| D1 | Execution identity is minted per start, not per plan: the first starter claims it; the web UI mints on start as today; the phone adopts the ID it holds in the issued plan, and an offline start binds at first sync. A web start warns when an outstanding issued plan exists for today. The single in-progress invariant is relaxed so a synced offline session can be created even when another session exists (WP1 B1). | Removes the offline hole in `409 workout_active` without blocking the web UI or killing plans on a timer. |
| D2 | `(exercise_id, set_index)` stays the server's set identity. The watch's offline sets are provisional and carry only a local ID; the phone assigns indexes at merge. | No schema change, no second identity domain, and one writer keeps the index unambiguous. |
| D3 | The phone is the only committer to Python for execution writes. The watch holds an optimistic local view. | One idempotency domain, one merge implementation, one place to resolve conflicts. |
| D4 | Merge never rejects a set. A collision is renumbered after the current maximum, in capture order, with device provenance retained. | A rejection on the merge path is a lost set. |
| D5 | Clock use is relaxed: `performed_at` orders events when both carry an offset derived from the same server epoch; otherwise `(device_id, device_seq)`. Timestamps within ±2 s are unordered. Timestamps never establish identity or dedupe. | Both devices derive time from the same server, so residual skew is small; the failure mode is a stale offset, not drift. |
| D6 | Rest timer state is device-local and derived from the last set event. It is never merged. | Two devices running independent timers would otherwise need a conflict rule for a UI convenience. |
| D7 | Conflicts auto-resolve; only *edit versus remove of the same set* asks the athlete. A set logged against a slot the phone substituted keeps its performed exercise and plan-slot provenance. | A dialog per set is not usable in a gym; silent reinterpretation is not acceptable either. |
| D8 | Late events are accepted on a completed session for **7 days**, recorded in the event stream, with derived metrics recomputed. After the window, events are preserved as rejected-late, never deleted. | Completion must not discard unreceived work; the bound keeps old sessions from changing under analytics. |
| D9 | Offline substitution load comes from a **server-built load catalogue** shipped with the plan. The client applies only `round_down(base / (1 + (reps + rir)/30), increment)`; Python verifies it from the snapshot it issued and never re-solves. | Keeps the training decision on the server while allowing modification with no connection. |
| D10 | `owner_device_id` becomes provenance only. Authorization becomes: any non-revoked device of the pairing; revocation is enforced. | Ownership was doing correctness work (set-index uniqueness); that work moves to D2–D4. |
| D11 | HealthKit duplicates are accepted. The watch writes a workout whenever it executed the session; the phone writes when it finishes one. Both may write, and the user deletes the duplicate in Health. No deferral, no pending-write state, no workout identity in the merge. | A missing workout is worse than a duplicate, and the user can delete one in seconds. Every deferral scheme needed cross-device state that the rest of the design does not otherwise require. An import-side overlap guard stays a contingency. |
| D12 | The watch's direct-to-server *execution writes* are retired; it keeps its device credential for read-only surfaces. | D3 has one committer; a second write path would reintroduce dual authority. |
| D13 | A plan binds to an execution when the local start falls inside `created_at…expires_at` and `for_date` is today or yesterday. | A 23:50 start synced at 00:10, or a start after the four-hour window, is the athlete's real session rather than an expired plan (WP1 B2). |
| D14 | `OfflineCapture` version 2 decodes and migrates version 1 in place. | An app update mid-workout must not make the in-progress capture unreadable (WP1 B3). |

**Execution is not prescription.** A substitution, an added set, or a corrected set is an
execution fact recorded with provenance. A client-applied load is a shipped suggestion the athlete
acted on, never a change to the prescription and never a re-solve. When performed work differs from
prescribed work, the record says so plainly: the workout did not do what was prescribed. The frozen
prescription is never rewritten, and no later read may imply that it was.

## 5. Execution identity (D1)

- `ios_issued_plan` gains `execution_id` (UUID), generated at issue. The plan payload carries it.
- `POST /api/ios/v1/workouts` accepts `execution_id` alongside `issued_plan_id` and binds it as the
  workout ID. Repeated calls with the same pair return the same workout (existing retry semantics).
- An offline phone start writes a local session under that ID; the first sync performs the same
  binding. Nothing else is stored while offline.
- A web start mints as today. Before minting, the server checks for an unexpired issued plan for
  today and returns `409 plan_pending_for_phone` unless the caller confirms
  (`start_anyway: true`); the UI shows the warning rather than a hard block.
- A phone opening a web-started workout adopts the server's workout ID (existing recovery path).
- If both exist anyway, they stay two sessions. Nothing is auto-merged, and the phone shows a
  "two sessions today" state. This requires the single in-progress invariant to be relaxed: today
  `workout.start` refuses to create any second in-progress session.
- Binding is judged by the athlete's start, not by the sync: a plan binds when the recorded local
  start falls inside `created_at…expires_at` and `for_date` is today or yesterday (D13).
- **WP5 implemented 2026-11-23:** the two-minute elapsed-time heuristic is gone. A start is decided
  by identity and state — the same execution id returns the running session, a different one may
  start beside an open session — so a delayed offline sync is never distinguished by how old its
  timestamp looks.

## 6. The ledger, and what it does not replace

The append-only ledger is **client-side**. It records intent, is written before the UI acknowledges
the action, and is replayed in order. It does not replace or duplicate server tables.

- Server canonical record stays `workout_set` (performed sets) plus the append-only `workout_event`
  stream (mutations, audit, execution changes and telemetry).
- Device ledger entries map to existing server writes: `start`, `add_set`, `execution_events`,
  `execution_change`, `complete`. Two markers are new: `late_reconciliation` and
  `reconciliation_closed`, both plain `workout_event` rows.
- Ledger entries are never aged out or capped before acknowledgement. The existing 16-entry journal
  and 28-day replay window are queue semantics and must not be inherited.
- The materialised device state is the existing session snapshot extended with the catalogue
  version, the plan's execution ID, and per-device reconciliation status. It is rebuilt from the
  ledger on launch.

## 7. Merge rules (D2–D7)

**Ack-before-commit.** When the phone is reachable, the watch sends the set and waits for the
phone's acknowledgement before it treats the set as indexed. No acknowledgement within 3 s means
the watch proceeds as offline. This is what makes "if both are logging, they are connected" true.

**At merge the phone:**

1. Reads its own committed sets for the workout.
2. Orders the watch's provisional sets by device sequence.
3. Performed-exercise first: for each `(exercise_id, plan slot)`, assigns the next free indexes
   after the current maximum, ascending.
4. Writes each set with its original `performed_at`, load, reps, RIR, velocity, source device and
   plan-slot provenance, under the same idempotent request shape used today.
5. Keeps a `local_set_id → set_id` mapping per device, so a later edit or removal from either
   device addresses the right row.
6. Uploads, then persists the merged state.

**Conflict classes and resolution:**

| Case | Resolution |
|---|---|
| Same event ID delivered twice | Deduplicated by identity |
| Two devices log the same exercise independently | Both kept, indexes assigned at merge (D2/D4) |
| Both edit the same set | Later edit by D5 ordering wins on value; both edits retained in the event stream |
| One removes, the other edits | Removed state wins; the edit is retained and surfaced as a note |
| Phone substitutes a slot the watch already performed | Set keeps its performed exercise and slot provenance; the slot shows substituted; no reassignment |
| Both modify the plan | Substitution is phone-only; additions merge in capture order |
| Both complete | Earliest `ended_at` is the completion; both events retained |
| Completion before the watch's events arrive | D8 late reconciliation, not a conflict |

**Ordering.** Causal order first (a set before its edit or removal; a plan revision before sets that
reference it). Then D5. Display order and accounting order are separate concerns: the index is
accounting, `performed_at` is display.

## 8. Late reconciliation (D8)

**Server implemented 2026-11-23** (`strength_coach/reconciliation.py`); the client half is C2.

- A phone that cannot reach the watch after finishing uploads with a `late_reconciliation` event
  carrying `pending_devices` and `closes_at = ended_at + 7 days`. It does not ask the athlete to
  choose between waiting and losing data; nothing is lost.
- The summary payload carries `reconciliation: {state, pending_devices, closes_at}`, and
  `pending_devices` lists only what is still outstanding. The phone shows "Apple Watch data
  pending" and refreshes when the watch syncs.
- A device that has nothing left to send is recorded through
  `POST /workouts/{id}/reconciliation {device_id}`, which settles the window as soon as nothing
  remains. Without it a synced watch would leave the session "pending" for the full week.
- Late sets are appended through the same add-set path with the original timestamps. Derived
  metrics (volume, e1RM inputs, VBT aggregation, calibration) recompute on read; the server does not
  store a second summary.
- After the window, a late arrival is preserved as a `late_rejected` event with its payload and the
  response says `reconciliation_window_closed`. It is visible in the event stream and excluded from
  aggregates.
- The UI must not show a completed session as final while reconciliation is open.
- **WP2a implemented 2026-11-23:** a late form rating is written to both the draft and the durable
  `session_form_rating` inside the window; execution telemetry stays observational and is bounded
  by the session's own timestamps, so a completed session accepts it without a window; and a
  rejected late set now preserves its per-rep velocities with the rest of its payload, so refusal
  never discards sensor data.
- **WP2b implemented 2026-11-23:** late removals are accepted inside the window and append a
  `clean_set` tombstone (a successor row that supersedes the old one and is itself voided), which
  is the same append-only mechanism a history edit already uses; the session totals are recomputed
  from live rows. A late correction of a removed set is refused with `409 late_event_rejected` and
  preserved — it never resurrects the set. The first completion still stands, so a later finish
  records the earlier instant without rewriting `ended_at`.
- `clean_set` is append-only in both directions (update and delete are blocked by triggers), which
  is why repair is expressed as supersession rather than mutation.

## 9. Load catalogue (D9)

### 9.1 Shape

One entry per exercise, shipped inside the issued plan:

```json
{
  "catalogue_version": "load-catalogue/v1",
  "as_of": "2026-11-23",
  "exercises": {
    "competition_squat": {
      "load_source": "e1rm",
      "base_load_kg": 163.3,
      "accessory_load_kg": 140.0,
      "increment_kg": 0.5,
      "bodyweight": false,
      "power": false
    }
  }
}
```

`base_load_kg` is already decayed and calibrated by the server. The client multiplies nothing.

### 9.2 Client application

```
power or bodyweight     -> 0, or null with reason
essential slot, base    -> round_down(base_load_kg / (1 + (reps + rir) / 30), increment_kg)
accessory slot, held    -> round_down(accessory_load_kg, increment_kg)
neither                 -> null, reason: no_catalogue_base
```

Rounding uses decimal arithmetic from the decimal string, matching `loads.round_down`. No
`Double` intermediate. Missing `rir` falls back to plain Epley (`reps / 30`), mirroring
`estimate_e1rm`; this case must be tested because `load_for_reps` itself has no fallback.

### 9.3 Generation and parity

- **Implemented 2026-11-23 in `prescribe/catalogue.py`, with a stronger guarantee than the
  extraction originally proposed:** each entry is produced by calling `engine.build_item` itself,
  so there is no second implementation to drift. The earlier plan to extract a `load_recipe`
  module was dropped for that reason.
- One `RuleContext` and one calibration pass are shared across the taxonomy; exercises with no
  stored history emit a null entry without a build, and the accessory load reuses the resolver's
  own `_last_working_set`. Measured on the test account: 144 entries, **20.5 KB**, **0.64 s**.
- **Parity gate (implemented):** the shipped base plus the client formula must equal
  `build_item`'s load across exercises and (reps, RIR) pairs. This test is the contract; if it
  fails, the catalogue is wrong.
- Swift tests still need the same fixtures replayed, including boundary cases that land exactly on
  an increment.

### 9.4 Recording

- `ExecutionChangeRequest` gains `prefill_load_kg`, `prefill_catalogue_version` and
  `prefill_as_of`. **Implemented 2026-11-23**; `prefill_requested` is retained as the documented
  legacy path for one release and can be removed once the phone always sends a value.
- The server recomputes from the snapshot it issued and stores `prefill_verified`,
  `prefill_expected_load_kg` and, on disagreement, `prefill_mismatch_reason`. A mismatch records
  both values and never blocks the change: the number the athlete saw is kept.
- A substitution outside the catalogue, or one with no base, records a reason such as
  `no_catalogue_base`. It is never retro-solved and never falls back to the original exercise's
  load.
- **The event carries the replacement's own prescription** (2026-11-23): `sets`,
  `prefill_source`, `set_groups` (the slot's structure re-solved for the substitute, so a top set
  plus back-offs stays one), `top_set {status, reason_code}` and `resolved_by`.
- **Shape is preserved; top-set eligibility is not re-decided.** The slot's group structure belongs
  to what the athlete is training, so the loads move and the shape stays. Eligibility depends on
  the resolver's gates and the substitute's own history, so a substitute records
  `top_set: not_applicable, reason_code: substituted` rather than inheriting the original lift's
  decision. Warm-up ramps are not carried: a mid-session substitute is defined by load, sets, reps,
  RIR, groups and VBT.
- **VBT targets are shipped** in the catalogue for lifts with a trustworthy calibration, and come
  from the resolver on the server path, so a substitute has the same velocity target online and
  offline. Entries without a calibration carry no target, never a reconstructed one.
- **Online and offline may differ in provenance, never in kind.** A server solve is authoritative
  and stores what it produced; a catalogue prefill stores what the phone applied and is verified
  against the issued snapshot. `resolved_by` says which, and an offline record is never
  retro-upgraded later.
- **Back-flare alignment implemented 2026-11-23:** `resolve_replacement` now applies the per-item
  effort hold and erector dose before attaching warm-ups, so a replacement performed during a flare
  gets the same treatment as a planned item.

### 9.5 Back-flare alignment

`resolve_replacement` currently skips the per-item back-flare effort and dose modifiers. The fix is
small — they act only on `item.flare` — but it must reorder the path to
`build_item → flare effort → flare dose → warmup.attach → VBT`, because the effort hold re-solves
the load and ramps must be rebuilt after it. Readiness-level modifiers stay out of scope and the
asymmetry is recorded.

## 10. Ownership and authorization (D10)

- `owner_device_id` is retained as provenance and reported, not enforced as a gate.
- Authorization: a write is accepted from any non-revoked device belonging to the session's pairing;
  a revoked device is refused immediately, whatever it holds locally.
- Slice S5 removes `409 not_owner`, the takeover endpoint and phone mirror mode, updates the tests
  that assert them, and removes the user-visible "Logging on Apple Watch" state. This is a
  user-visible removal and needs its own approval point and documentation update.

## 11. HealthKit (D11)

- `sessionUUID` is the key. The watch writes when it executed any part of the session; the phone
  writes only when the watch took no part.
- A phone that must finish before reconciliation cannot yet know: it writes with `sessionUUID` in
  the workout metadata, and the import reconciles on that key instead of creating a second workout.
- Exact behaviour at the boundary is settled in WP4 with a device test, not in this document.

## 12. Technique throttle

- Server already implements MOD-TECH-001 (bounded load cap, RIR floor, compared against modifiers
  already applied rather than stacked).
- Add `technique_throttle` (boolean, main-work scope only) to the closed iOS settings schema and
  pass it into the resolver call, matching the web path. No pattern picker on the phone.
- The issued plan must make the modifier visible (rationale ref `MOD-TECH-001`) so lighter loads are
  explained to the athlete.
- No ledger or offline impact: the throttle is frozen into the plan at issue. Changing it
  mid-workout is out of scope.

## 13. Contract amendments (proposed, not applied)

**IOS-WATCH-CONTRACT §8** — replace the start gate bullets with: a plan carries `execution_id`; the
watch may start offline from its cached plan and binds the ID at first sync; start no longer requires
the home server, the phone, or a relay.

**IOS-WATCH-CONTRACT §9** — replace ownership transfer with provenance plus device-scope
authorization; remove the mirror-mode and takeover paragraphs; state that any non-revoked paired
device may log.

**IOS-WATCH-CONTRACT §10.4** — mark superseded: DEC-RESOLVER-23 already retired
`409 plan_item_mismatch`; a stale `plan_item_index` is extra work with preserved provenance. The
document is currently stale relative to that decision and should be corrected in the same edit.

**IOS-WATCH-CONTRACT §14** — add `technique_throttle` to iOS prescription settings; add
`execution_id` to start; add `prefill_load_kg`/`prefill_catalogue_version`/`prefill_as_of` to the
execution-change request; add `409 plan_pending_for_phone`; add the reconciliation block to the
summary.

**IOS-WATCH-CONTRACT §21** — remove the deferred pending-session shell; it is being built.

**IOS-CLIENT-PLAN §5** — the offline table's "start still requires connectivity" row changes to
"start requires a downloaded plan, not a connection".

## 14. Work packages and slices

**WP0 — this document and the amendments.** Gate: owner approval. No code.

**S0 — technique throttle** (independent, no dependency on the rest). Server field + pass-through,
client toggle, plan display. Shippable on its own.

**S1 — identity, ledger, watch-only reap.** Prerequisites from WP1: the bind rule (D13), the
capture-version migration (D14), and the relaxed in-progress invariant (D1). Then: execution ID at
issue; adopt path; device ledger and rebuild; watch executes a full session offline with sets and
finish; phone merges and uploads.
Proves the pipeline end to end. No substitutions, no concurrent logging.

**S2 — concurrent and never-reject merge.** Ack-before-commit; provisional sets; renumbering;
provenance UI; conflict classes and the single edit-vs-remove prompt.

**S3 — offline plan changes.** Load catalogue, parity gate, client arithmetic, phone substitution,
additions on either device, back-flare alignment.

**S4 — lifecycle.** Offline start, late reconciliation (D8), HealthKit boundary, termination and
reboot recovery, upgrade mid-workout (adopt existing queues), device-restart acceptance.

**S5 — ownership removal and the visible simplification.** The authorization change and the UX
change land together, because the second depends on the first:

1. Remove the `409 not_owner` gate; `owner_device_id` stays as provenance (D10).
2. Remove `execution_target`, `target_device_id` and `409 wrong_execution_target` from start; the
   plan is targeted at the **pairing**, and the live-plan uniqueness becomes one row per pairing
   instead of one per target device.
3. **Remove the iPhone/watch execution-target picker from the request screen.** It exists only
   because a plan currently names its executor; once the plan is pairing-scoped, the device that
   presses Start is simply the device that starts. This is a product change, not a side effect,
   and it must be reviewed as one.
4. Remove mirror mode: the "Logging on Apple Watch" banner, the disabled controls and
   `isMirroringWatchSession` guards. The phone is editable whenever a session is open.
5. Retire `POST /workouts/{id}/takeover` and its `MutationKind.takeover` journal entry.
6. Retire the WP8 "Send to iPhone" relay and the watch's direct execution writes (D12); the watch
   keeps its credential for read-only surfaces only.
7. Update every test that asserts these behaviours — the server ownership suite, `WatchMirrorTests`,
   the takeover case in `Phase2ClientTests`, and the `not_owner` case in
   `WatchExecutionEngineTests`.

Until item 2 lands, the picker must stay: the current start gate still refuses a non-target device,
so removing it earlier would break watch start rather than simplify it.

Each slice: own branch, its own acceptance, and a rollback that returns to the previous behaviour
without data loss.

## 15. WP1 audit checklist (before S1)

**Complete 2026-11-23.** Findings, severity and the three decisions required before S1 are in
[UNIFIED-OFFLINE-EXECUTION-WP1-AUDIT.md](UNIFIED-OFFLINE-EXECUTION-WP1-AUDIT.md).

1. Confirm the start path can bind a supplied `execution_id` without breaking idempotency receipts.
2. Establish what the watch's cached plan actually contains, and whether plan + catalogue fit the
   WatchConnectivity delivery path (the application context is reserved for the credential
   handshake; plan and catalogue may need file transfer).
3. List every test asserting `not_owner`, mirror mode and takeover, so S5's removal is explicit.
4. Confirm `build_item`'s load branch extracts cleanly (it depends on `_resolve_flare_policy`,
   `context.entity`, `thresholds`, `_last_working_set`).
5. Confirm the migration path for the existing pending journal and offline capture queue on update,
   or gate the release on queue-empty.
6. Measure catalogue size on a real account and the resulting plan payload.

**B5 settled 2026-11-23.** A measured plan is 12.9–13.7 KB for 6–7 items; a catalogue entry is
274 B, so the 144-entity library is ≈39.5 KB. Worst case ≈53 KB against a 65,536-byte
WatchConnectivity ceiling. **Decision: plan and catalogue travel by `transferFile`, not by
application context or `transferUserInfo`.** A trimmed entry (~180 B, dropping the provenance ref)
brings the library to ≈26 KB if a message transport is ever preferred, but file transfer removes
both the ceiling and the size coupling.

## 16. Acceptance matrix (physical devices)

**Server-side walking skeleton implemented 2026-11-23:** one HTTP conversation covers adopt → log →
finish with a pending device → late set with its original instant → totals recomputed → device
resolved → window closed (`tests/test_ios_workflow.py::test_the_whole_offline_flow_reconciles_end_to_end`).
It is the reference the Swift work is written against; the matrix below still needs physical devices.

Simulator success is not acceptance (`StrengthApp/AGENTS.md`). Required:

1. Phone-only, airplane mode, full workout start → finish → sync.
2. Watch-only, phone powered off, full workout start → finish → later sync.
3. Both logging concurrently while connected, then reconnect.
4. Both logging concurrently while partitioned, then reconcile.
5. Terminate each app mid-set; relaunch; state restored exactly once.
6. Watch reboot mid-workout.
7. Phone finishes while the watch is unreachable; late sets arrive within the window; summary updates.
8. Late set after the window is rejected-late and preserved.
9. Offline substitution on the phone; watch continues on the old slot; merge keeps both.
10. Technique throttle on: loads lower and explained.
11. Phone lost or wiped with unreconciled watch data: the watch session survives locally.

## 17. Risks and non-goals

**Risks:** WatchConnectivity suspension delays (mitigated by explicit triggers and a visible pending
state); catalogue staleness on a plan issued days earlier (bounded by `as_of` and the 4-hour plan
window); stale clock offsets after a watch reboot (D5 fallback); two sessions on the same day in the
web-start edge (D1 soft check, no merge); HealthKit duplication before reconciliation (D11 key);
device storage growth from an uncapped ledger (bounded by acknowledgement, not age).

**Non-goals:** a Swift resolver; server-side event sourcing or a database migration; a generic sync
framework; resurrecting plan editing; watch-authored substitutions (D9 of the resolver plan stands);
mid-workout technique-throttle changes.

## 18. MacBook handout — Swift work

Everything below is client work for the MacBook, because this checkout has no Xcode and device
acceptance is a MacBook responsibility. Branch `offline-execution` in `StrengthApp`, PR into
`development`, and report test status per item; never commit `LiveConfig.swift`, and never claim a
device result from a simulator run.

**Constraints that do not change:**

- No resolver, no load calculation beyond the §9 formula, no training policy.
- Do not remove the ownership gate, mirror mode or the takeover endpoint; that is S5 and needs its
  own approval point.
- Do not add a second write path to the server for the watch.

**C1 — S0 client (small, unblocked).**

1. Add the `technique_throttle` toggle (main work only) to the prescription request and send it in
   `settings`. The server half is implemented; see the contract §14 row.
2. Show on the issued plan that MOD-TECH-001 is in force, so lighter loads are explained. The item's
   rationale refs carry it.
3. Decode `execution_id` from `POST /prescriptions` and `GET /plans/current`, store it with the
   cached plan, and send it with `POST /workouts`; send `started_at` when the start came from a
   cached plan rather than a live request.
4. Substitution and addition requests send `prefill_load_kg` computed from the shipped
   catalogue — `round_down(base/(1+(reps+rir)/30), increment)` for an essential slot, the
   accessory value otherwise — with `prefill_catalogue_version`. A `prefill_verified: false`
   response is a diagnostic for the logs, not something to correct silently in front of the athlete.
5. Tests: settings encoding, `execution_id` round-trip, start body shape, the catalogue prefill
   formula against the server's fixtures, and the "plan changed" banner path.

**C2 — S1 client (after C1).**

1. `OfflineCapture` version 2: decode and migrate version 1 in place (D14). A mid-workout update
   must not make the capture unreadable. Test with a real version-1 fixture.
2. Ledger entries: `entry_id`, `workout_id`, `device_id`, `device_seq`, `kind`, `payload`,
   `created_at_local`, `clock_offset_s`, `plan_watermark`, `ack_state`; no age-out before ack.
3. Plan-only cache on the watch (B4) delivered by `transferFile` (B5), so a start needs nothing but
   the cached plan and the execution id.
4. Offline start on either device under the plan's `execution_id`.
5. Ack-before-commit: when the phone is reachable, a watch set is provisional until acknowledged;
   after 3 s without an acknowledgement it proceeds as offline.
6. Merge: the phone renumbers colliding `(exercise, set_index)` after the current maximum in capture
   order, preserves warm-up indexes ≥1000, keeps device provenance, and never rejects a set.
7. Edit/remove translation through the per-device `local_set_id → set_id` map.

**Acceptance for C2** (physical devices, from §16): watch-only with the phone powered off; both
logging while partitioned then reconciled; terminate each app mid-set; and a version-1 capture
upgraded mid-workout.

**C1/C2 additions from the audit close-out (2026-11-23):**

1. An execution change now returns `resolved_by`, `set_groups` and `top_set`. Render the groups
   as the substitute's prescription — a top set plus back-offs stays one — and show
   `top_set: not_applicable` rather than the original lift's top-set numbers.
2. A substitute may carry `vbt_target` (catalogue path) or `vbt` (server path); show the velocity
   target when present, never invent one.
3. There is no `prefill_requested` flag. Send `prefill_load_kg` when you applied the catalogue;
   send `prefill_catalogue_version` with no value to record a catalogue miss; send neither and the
   server solves.
4. A late removal is accepted inside the window; a late correction of a removed set returns
   `409 late_event_rejected` — keep it unsent and show it, don't retry.
5. The server no longer mints an execution id for a plan issued before the column existed; a plan
   without one answers `409 plan_not_bindable`, and the fix is to request a fresh plan.

**C3 — HealthKit writer policy (WP6, this is the audit's one client task).**

D11 is now four lines and needs no cross-device machinery:

- The watch saves one HealthKit workout whenever it ran the session, through the existing
  per-device finaliser keyed by `sessionUUID`. That mechanism is unchanged.
- The phone saves one when it finishes a session.
- If both finish, both save, and the user deletes one in Health. The app must not delete, merge or
  "fix" HealthKit records automatically.
- No deferral, no pending-write state, no HealthKit identity in the merge, no timeout.

Acceptance: a watch-only session produces one workout; a phone-only session produces one; a
session finished on both produces two, and the athlete can delete either without breaking the
server record (the training data comes from `workout_set`, not HealthKit).

**C2 additions for late reconciliation (server ready):**

1. On finish, send `pending_devices` naming the devices whose events have not arrived (the phone
   knows: it is the one that could not reach the watch). An empty list opens no window.
2. Do not present the finished session as final while `reconciliation.state` is `open`; show
   "Apple Watch data pending" and refresh the summary when the watch syncs.
3. When a late set is refused with `409 reconciliation_window_closed`, keep the device's own copy
   and show it as unsent — the server has preserved it, but only for audit.

## 19. Review dispositions (2026-11-23)

The external review raised five work packages. Recorded here so a later reader does not re-raise
what was decided.

**Accepted and implemented (server):** WP1's parity test against `resolve_replacement`; the
erector-dose divergence; carrying the replacement's prescription (narrowed — see below); WP2's gap
for late events; WP2.3's preservation of a rejected event's payload, including per-rep velocities;
WP5's removal of the elapsed-time heuristic.

**Rejected, with reasons:**

- **WP2.2** — device sequence numbers and stable UUIDs for every server event. The per-device
  idempotency receipt already makes retries safe, and per-event device provenance is a migration
  with no consumer today.
- **WP2.4** — the five-state reconciliation machine. You rejected it; the window is time-bounded
  (D8) and a device is settled explicitly or by elapsed time, not by a richer state graph.
- **WP1.2 as written** — carrying warm-up runs and full VBT provenance inside every execution event.
  Narrowed to the fields the athlete acts on plus the shipped VBT target, because the performed set
  is the durable record (DEC-RESOLVER-23) and the event is a view hint.

**Deferred to S5:** `execution_target`, ownership, takeover, mirror mode, the WP8 relay and the
iPhone/watch picker — one removal, gated on the client ledger.

**Recorded, not code:** WP6's writer policy (D11) is a client decision; the server has no HealthKit
involvement.

## 20. Status and change control

This document is the canonical cross-repository statement for offline execution. Component
implementation detail belongs in `strength-training-app/docs/` and `StrengthApp/docs/`; the
contracts stay canonical here. Status changes only with evidence: code merged, tests green, and the
§16 device acceptance recorded. No submodule pointer is advanced as part of this work unless
explicitly requested.
