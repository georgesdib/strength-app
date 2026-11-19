> **Canonical shared contract.** Relocated from `georgesdib/strength-training-app/docs/design/IOS-R8-CONTRACT.md`. Contract substance and acceptance requirements are preserved; backend implementation remains in the backend repository.

# iOS R8 — Active-workout plan editing (add, swap, remove, move, set count)

**Status:** **implemented and closed 2026-11-08; extended 2026-11-17.** The authenticated
catalogue, five plan-edit routes, shared service guards, iPhone menus, web conflict handling and
tests are on `development`. The 2026-11-17 amendment solves the load for an added exercise and
adds a move/reorder operation (`DEC-IOS-08`, `DEC-IOS-09`). No migration is required.

> **Superseded in part 2026-11-19.** The plan-edit routes and client menus in this contract are
> retired by the [resolver prescription structure plan](../plans/RESOLVER-PRESCRIPTION-STRUCTURE.md).
> Plans are frozen at start; substitutions and additions are execution events, not plan edits. The
> closed record below is preserved for history and must not be implemented.

**Why R8 exists.** The Phase 2 contract deliberately excluded plan editing: "No plan edits, exercise
swap, set-count change, set update/remove, or load/reps overrides. Those remain web/CLI"
([`IOS-PHASE-2-CONTRACT.md`](https://github.com/georgesdib/strength-app/blob/main/docs/contracts/IOS-PHASE-2-CONTRACT.md) §9). In practice the owner trains with the
phone in hand, and the web UI already exposes these edits on a live workout through
`strength_coach/workout.py`. R8 brings that existing capability to the phone without giving the
phone any new authority: every edit still runs through the same Python services.

## 1. Scope

In scope, on an **in-progress** workout only:

- **Swap** a plan item's exercise.
- **Add** an exercise to the plan.
- **Remove** an exercise from the plan.
- **Change the set count** of a plan item.
- **Move** a plan item to a different display position (added 2026-11-17).

Out of scope: editing a prescription that has not been started, editing a completed/abandoned
workout, editing loads by hand (see §3), set-level correction or removal (Phase 4), editing a plan
from the web-synchronised "plan override" surface beyond these five operations, and any new rubric
or scoring behaviour.

## 2. Existing server capability being reused

The edit services live in `workout.py`; swap and add reuse the prescription engine's single-slot
solve, and move is a list permutation with no training-policy meaning:

| Operation | Service | Behaviour |
|---|---|---|
| Swap | `workout.swap_exercise` | Replaces the item's `exercise_id`, records `substitution_for`, **re-solves the replacement** with `resolve_replacement` (its own load, warm-up ramp and VBT target from its own history), and discards `set_groups` |
| Add | `workout.add_exercise` | Rejects a duplicate exercise, clamps `sets` 1–20 and reps 1–50, **solves the added slot** the same way when no explicit load is supplied, and appends with `added_during_workout: true` |
| Remove | `workout.remove_exercise` | Drops the item at `item_index`; later items shift position but keep their identities |
| Sets | `workout.change_sets` | Clamps to 1–20, resizes `set_groups` |
| Move | `workout.move_exercise` | Re-inserts the item at `to_index` (its final position); identities and logged-set attributions travel with it |

All five require `status = 'in_progress'` (they raise unless `_editable`), all five go through
`_write_plan`, which validates the resulting items and then:

1. rewrites `workout_session.plan_modified_json`, and
2. appends a `workout_event` row (`swap_exercise`, `add_exercise`, `remove_exercise`,
   `change_sets`, `move_exercise`).

`workout_event` is append-only by trigger, so the audit trail of edits is the event log;
`plan_modified_json` is the current editable state.

## 3. The load rule (the one real policy decision)

The phone may **not** supply a load for an added or swapped exercise. A load is a training decision
and Python owns it, so the server solves both edits itself (`DEC-IOS-08`):

- **Swap:** the replacement is solved with `prescribe_engine.resolve_replacement`. It keeps the
  item's sets/reps/RIR shape but gets its **own** load, warm-up ramp and VBT target from its own
  history and calibration; the old lift's load is never carried across. The phone sends only
  `exercise_id`.
- **Add:** the request accepts `exercise_id`, `sets`, `reps_low`, `reps_high`, `rir_target`
  and nothing else. `load_kg` is **not accepted** (`400 unknown_field`). The server builds the
  same single-slot solve with the requested shape and an `essential: false` slot, so the added item
  carries `load_kg`, `load_basis`, `warmup`, `e1rm_*` and any VBT target exactly as an issued
  item would.
- **Unsolved is still a valid edit.** When the solver has no history (or cannot answer), the item is
  added with `load_kg: null` and the solver's `unknown_load_reason`, so a mid-workout addition is
  never blocked and the reason stays visible. A client-supplied load remains rejected in every case.
- The owner enters the actual load when logging the set, which is where a performed load belongs.
  Nothing on the phone invents a prescription load.

The explicit `load_kg` argument survives for the **web** add form only, where it is a manual
override; the iOS route never passes it.

## 4. API surface

> **Retired 2026-11-19.** The five routes in this section are removed from the facade; see the
> amendment at the top of this contract.

All routes are under `/api/ios/v1/` and require the bearer token. Mutating routes also require an
`Idempotency-Key` and return the full `workout.get` payload so the client never has to predict the
new plan. The request schemas are closed.

```text
GET  /api/ios/v1/exercises                                      -> {"exercises": [{"id", "display", "pattern"}]}
POST /api/ios/v1/workouts/{id}/plan/items/{item_index}/swap     {"exercise_id": "…", "expected_exercise_id": "…"}
POST /api/ios/v1/workouts/{id}/plan/items/{item_index}/remove   {"expected_exercise_id": "…"}
POST /api/ios/v1/workouts/{id}/plan/items/{item_index}/sets     {"delta": -1, "expected_exercise_id": "…"}
POST /api/ios/v1/workouts/{id}/plan/items/{item_index}/move     {"to_index": 0, "expected_exercise_id": "…"}
POST /api/ios/v1/workouts/{id}/plan/exercises                   {"exercise_id": "…", "sets"?, "reps_low"?, "reps_high"?, "rir_target"?}
```

Rules:

- `item_index` is positional and shifts after a removal, so every mutating request also carries the
  exercise the client believes is at that index: `{"expected_exercise_id": "…"}`. The server
  compares it with the current item and returns `409 plan_changed` on mismatch, with the fresh
  workout in the body. Without this, two clients (phone plus web) can silently edit the wrong lift.
- `swap` rejects a target exercise that is already in the plan (`409 exercise_already_present`).
  The check is in the shared service so the web and the phone share one rule.
- `swap` is rejected after any set is logged for the target item (`409 sets_already_logged`). An
  unattributed set for the same exercise is treated as ambiguous and also blocks the swap.
- `remove` is allowed even when sets are already logged for that exercise. Those sets are
  append-only and stay; they simply no longer match a plan item, and the comparison will report the
  item missing. The client must warn before sending: "Remove <lift>? Logged sets are kept."
- `remove` is rejected when it would leave no plan items (`409 last_plan_item`).
- `sets` takes a non-zero delta; the iPhone uses `-1`/`+1`, and the service clamps to 1–20. A
  delta that would put the target below the logged-set count is rejected (`409 sets_below_logged`);
  an unattributed set for the same exercise blocks any decrease until that ambiguity is resolved.
- `move` takes the item's **final position** after removal (`to_index`), so moving the first
  item of a three-item plan to the end sends `2`. The list length it must fit is the current plan
  length; an out-of-range `to_index` returns `409 plan_changed` with the fresh workout. A move to
  the item's current position is a no-op and appends no event.
- `add` defaults to 3 sets, 8–12 reps and RIR 2 when the optional shape fields are omitted; the
  shared service clamps and solves the load.
- Unknown workout → `404 workout_not_found`. Not in progress → `409 workout_not_active`. Unknown
  exercise → `400 validation_failed` (taxonomy lookup), never silently dropped.
- Idempotency uses the existing receipt table: a replayed key returns the stored workout and does
  not apply the edit twice. A different body with the same key is `409 idempotency_conflict`.

## 5. Data effects

- `workout_session.plan_modified_json` — updated in place (the current editable plan).
- `workout_event` — one appended row per edit, with the before/after payload.
- `ios_issued_plan.plan_json` — **never modified**. It remains the server-issued plan the workout
  started from, so "what was prescribed" and "what was performed" stay separately reconstructible.
- No new table, no new column, no migration.

### 5.1 Stable plan-item identity

- Within a workout, each plan item's `order_index` is its **stable identity**. Removal preserves
  the remaining items' `order_index` values (leaving gaps); swap preserves the item's identity;
  add assigns `max(order_index) + 1`; move reorders the list without touching any identity, so
  logged sets keep pointing at the same lift. Nothing in R8 renumbers an existing identity.
- `workout_set.prescription_item_index` stores that stable identity for new rows. It is **not** the
  item's current display position. The comparison response carries both `plan_item_index` (stable
  identity, used for attribution) and `display_index` (current order, for rendering).
- The set-writing API accepts the stable identity in `plan_item_index`. For backward compatibility,
  an old client's display position is accepted only when it names an item of the same exercise;
  ambiguous or stale values are not guessed into an item.
- Existing rows written before this fix remain readable. Resolution prefers an exact stable
  identity, then falls back to the same-exercise display position for legacy rows. Unresolved rows
  stay visible as stale/unavailable, and unattributed rows remain conservatively ambiguous.
- No historical event or set is rewritten and no migration is required. The item identity is
  carried in the existing plan JSON and `prescription_item_index` column.

## 6. Client behaviour

- The active-workout screen gains a per-item menu: **Swap exercise**, **Remove**, **Move up**,
  **Move down**, **Sets −/+**, and a plan-level **Add exercise**. The move actions are disabled at
  the ends of the list; like the other edits they are allowed while the watch mirrors the session,
  and the new revision is pushed at its next idle point.
- Exercise choice uses an authenticated read-only catalogue route (`GET /api/ios/v1/exercises`)
  rather than a typed-name-only picker. The phone loads it while online; the catalogue is not a
  promise of offline editing. The server still validates every exercise id.
- If the catalogue request fails, the menu reports the error and does not guess an exercise. A
  typed fallback is not required for the first implementation.
- The app is online-only for R8 edits. The R1 journal makes an attempted edit retry-safe; it is not
  an offline queue and does not permit an edit without the server response.
- Every edit shows a busy state and applies only when the 2xx workout payload returns; on failure the
  previous plan stays on screen with the server's message. No optimistic local plan edits.
- After any edit the client re-renders from the response, which fixes index shifting for free.
- Logged sets are never removed by an edit; the UI states this explicitly on remove.
- An edit is a mutation and therefore uses the R1 journal: an unresolved edit blocks the next
  mutation and replays with the same key.

## 7. Invariants that still hold

- Python remains authoritative for exercises, loads, sets, reps, RIR and validation.
- The phone never sends a replacement plan, a prescription, a load or a plan item array.
- Edits are append-only events plus a mutable working plan; the issued plan is never rewritten.
- The prescription snapshot the workout started from is unchanged, so the rubric and comparison keep
  their meaning.
- No edit can convert a completed session back to in-progress, and no completed session row is
  ever touched.

## 8. Tests

- Server (`tests/test_workout.py`, `tests/test_ios_workflow.py`, `tests/test_vbt_wiring.py`):
  swap records `substitution_for` and discards `set_groups`; add with history solves its own load
  and basis, add without history stays unsolved with the solver's reason, and an iOS `load_kg` is
  `400 unknown_field`; move changes display order while identities and logged-set attribution stay
  put, a same-position move appends no event, an out-of-range `to_index` is `409 plan_changed`;
  remove keeps logged sets; last-item and logged-set guards return 409; set count clamps and cannot
  drop below logged sets; ambiguous sets block edits; `expected_exercise_id` mismatch → 409
  `plan_changed`; duplicate swap target → 409; unknown exercise → 400; not in progress → 409;
  idempotent replay applies once; `plan_json` unchanged; one `workout_event` per edit. A dedicated
  regression logs later-item sets, removes an earlier item, then checks reload-time attribution and
  the set-count guard against the still-correct logged count. A web regression removes an earlier
  item and applies a set-count edit to the correct shifted display item.
- Client: catalogue decodes; the picker sends only the exercise id for add; the move request carries
  `to_index` and the expected item; response re-render after an edit keeps the correct item;
  journaling covers `.planEdit`; no load field is ever sent. The live simulator workflow adds an
  exercise through the authenticated picker.
- Existing workout, comparison, history and Phase 2 tests stay green.

## 9. Acceptance

1. On an active workout the owner can swap, add, remove, move and change set counts from the phone.
2. A swapped or added exercise carries a **server-solved** load when history exists, and no invented
   load ever; when it cannot be solved, the reason is visible in the workout payload.
3. Removing an item with logged sets keeps the sets and warns first; moving an item never detaches
   its logged sets.
4. A concurrent web edit produces `plan_changed` rather than an edit to the wrong lift.
5. The issued plan JSON is unchanged after editing; the event log shows every edit.
6. Default suite, docs tests and `ruff` pass; the web UI shares the same guards and returns 409
   for rejected edits.

## 10. Rollback

- Remove the five routes and the client menu; the server services and the web UI keep their existing
  behaviour.
- No schema change to undo. Workouts edited during the period keep their events and their modified
  plan, which is the intended record.
- No prescription, session or readiness row is touched by enabling or removing R8.

## 11. Decisions taken

Settled by the owner on 2026-11-08:

1. **Swap to a duplicate exercise:** the `409 exercise_already_present` check goes in the shared
   service, so the web and the phone agree. This is a deliberate web behaviour change: two clients
   disagreeing about whether a lift is on the plan is worse than one extra validation. Recorded as
   `DEC-IOS-05`.
2. **R8 stays a separate item from R7**, because it is a new write surface on a live workout rather
   than a reliability change.

Owner-approved decisions on 2026-11-08:

3. **Authenticated exercise catalogue:** add `GET /api/ios/v1/exercises` for the picker. The phone
   loads it online. No local taxonomy validation beyond the server response.
4. **Online-only edits:** R8 does not add an offline queue. R1 journaling covers attempted edits.
5. **No client-supplied load:** the phone never supplies a load for add/swap. The server solves
   the edit itself (amended 2026-11-17, `DEC-IOS-08`); the original decision was "no solved load
   mid-session", now superseded.
6. **Order:** R8 follows R7. R7 is closed (2026-11-08), so R8 may start once this contract is
   confirmed.
7. **Reordering:** originally out of scope; **added 2026-11-17** as a fifth operation
   (`DEC-IOS-09`) once the identity design made it safe.

Amended 2026-11-17:

8. **The server solves an added exercise, not the athlete.** `add_exercise` runs the same
   single-slot `resolve_replacement` path swap uses, with an `essential: false` slot built from
   the requested shape; an unsolvable exercise is added with a null load and the solver's reason
   rather than blocked. `DEC-IOS-08`.
9. **Move is a display-position edit with no renumbering.** `to_index` is the final position after
   removal; identities, `set_groups` and logged-set attribution travel with the item; a
   same-position move is a no-op. `DEC-IOS-09`.

Nothing in R8 remains deferred: the two former deferrals (a solved load on add, and reordering) are
implemented above.
