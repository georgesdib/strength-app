# WP1 audit — unified offline execution

**Status:** audit complete 2026-11-23. Read-only: no implementation file was changed.
**Scope:** `strength-training-app` execution, start and plan-issue paths; `StrengthApp` phone and
watch execution, queue and connectivity paths.
**Reads against:** [UNIFIED-OFFLINE-EXECUTION.md](UNIFIED-OFFLINE-EXECUTION.md) (WP0).

## 1. How execution works today

### Server

| Concern | Where | Behaviour |
|---|---|---|
| Session | `workout_session` | One row per session; `status` in progress/completed/abandoned; `plan_json` is the frozen snapshot; `owner_device_id` (0058), `plan_revision`, `last_activity_at` |
| Sets | `workout_set` | Base rows with `UNIQUE(workout_id, exercise_id, set_index)` |
| Corrections | `workout_event` | Append-only (database triggers block update and delete). `update_set`, `remove_set`, `restore_set` carry `target_set_id` |
| Materialised sets | `workout._sets` | Replays the event stream over the base rows on every read |
| Plan issue | `ios_issued_plan` | Frozen `plan_json` + `readiness_json`, TTL, `consumed_at`, `workout_id`, `target_device_id`, `execution_target`; one live plan per target device |
| Idempotency | `ios_operation_receipt` | `(device_id, operation_id)` → `request_hash`, response, expiry |
| Execution changes | `workout.record_execution_change` | Append `substitution`/`addition` `workout_event`; unique index on `payload_json.client_event_id` |
| Telemetry | `workout_execution.record_events` | Observational, capped batch, `local_set_id`; creates nothing |

### Phone

- Starts, logs, edits and finishes through server calls; pending bodies are kept in
  `MutationJournal` (cap 16, 28-day replay) and, separately, in `OfflineCapture` (cap 128).
- Mirror mode gates eight view sites and six `AppModel` guards on `isMirroringWatchSession`.
- Plan edits push `RemoteExecutionPayload` over `transferUserInfo` only when the workout is active
  and has a plan revision.

### Watch

- Start is a server call (`client.startWorkout`) with a derived idempotency key; there is no local
  start path.
- `OfflineCapture` holds `activeWorkout` (full `WorkoutDetail` including plan), the ordered
  operation queue, and `WatchSessionRecord` (session UUID, plan revision, clock offset, rest,
  finish intent, active set, execution view).
- `nextSetIndex` allocates at log time from acknowledged + queued sets, per performed exercise;
  warm-ups use indexes from 1000 upward. It is a provisional index, but a concrete one.
- Writes go through the relay (phone) or directly to the server with the watch credential.
- `restore()` rebuilds from the capture file without contacting the server.

## 2. Reusable components

1. **`_sets` replay** already gives the server a materialised view derived from an append-only
   stream, including removals. The ledger's server side largely exists; no new table is needed.
2. **Append-only triggers** make `workout_event` trustworthy as the audit stream.
3. **`ios_operation_receipt`** is a working idempotency domain keyed by device and operation.
4. **`ios_issued_plan.consumed_at`/`workout_id`** already bind plan to workout; adoption is half
   built, and a retried start already returns the existing in-progress workout.
5. **`OfflineCapture`** is an ordered, durable, atomic queue with `validateOperation`; the ledger
   can be its next version rather than a new subsystem.
6. **`WatchSessionRecord`** already owns the clock domain, rest interval and finish intent.
7. **`ExecutionView` watermark** already merges server-authored plan changes idempotently.
8. **`build_item`'s load branch** is contiguous and extractable into `load_recipe` (see §10).

## 3. Online dependencies today

| Action | Phone | Watch |
|---|---|---|
| Start | server | server or phone relay |
| Fetch plan | server | server or phone relay |
| Add / edit / remove set | server or queue | server or relay, queued |
| Substitution / addition | server (phone-only) | not permitted |
| Finish | server or queue | server or relay, queued |
| Summary | server | server |
| Clock offset | server bootstrap | server bootstrap or workout start |
| HealthKit save | local | local |

## 4. Duplicated or competing state

1. **Two phone queues.** `MutationJournal` (every mutation, cap 16) and `OfflineCapture` (offline
   capture, cap 128) both hold unsent writes. Which one owns a given write is decided at the call
   site. S1 must nominate one; keeping both is a second reconciliation path.
2. **Four watch representations** of "what has been done": `activeWorkout.sets`,
   `operations` (queued), `session` (local record) and `session.execution` (server view). They are
   reconciled by hand in derived properties (`pendingCount`, `completedSetCount`).
3. **Three server representations**: `workout_set` base rows, `workout_event` corrections, and
   `workout_execution` telemetry. The first two are correctly layered; telemetry duplicates some set
   facts for analytics and must not be treated as a ledger.

## 5. Gap analysis against the target

| Target | Today | Gap |
|---|---|---|
| Start offline | Server call required on both devices | New local start path; plan cache before start |
| Complete offline | Finish is a queued server call; local UI state exists | Finish intent is already durable; reconciliation is not |
| Either device independently | Watch needs the phone or server to start; writes relay | Remove start dependency; single committer merge |
| Never reject a set | `set_index_conflict` rejects on index reuse; `UNIQUE` constraint enforces it | Merge-side renumbering before write |
| One history | One server session; per-device local views | Ledger + merge |
| Late events | Completed sessions reject sets | Reconciliation window |
| Offline substitution | Server-solved prefill or null | Load catalogue |
| No ownership transfer | Ownership gate, takeover, mirror mode | D10 removal |

## 6. Blocking findings

**B1 — the single in-progress invariant is enforced in code, not just the API.**
`workout.active_workout()` is global (no device, no date filter) and `workout.start()` raises when
any session is in progress. D1's soft check reduces the chance of two sessions, but when it does
happen the phone's offline session **cannot be created at all** — the upload would be refused and the
data stranded. Options: relax `start`/`active_workout` to allow more than one in-progress row (the
schema has no constraint) and make the web UI choose; or define a hard conflict. **Needs an owner
decision before S1.**

**B2 — date and TTL binding.** `_ios_start` rejects a plan whose `for_date` is not today and whose
`expires_at` has passed. An offline session started at 23:50 and synced at 00:10, or started after
the four-hour window, would be refused. The rule adopted in WP0 ("the plan the athlete saw is the
plan they executed") is not implemented. Needs an explicit bind rule: accept a plan for today or
yesterday when the local start time falls inside the plan window.

**B3 — the capture file refuses an unknown version.** `OfflineCaptureStore.loadUnlocked` throws
`unsupportedVersion` when `version != currentVersion`. Bumping the version on an app update while a
workout is in progress makes the in-progress capture **unreadable**. The ledger must decode version 1
and migrate, or the release must be gated on an empty queue.

**B4 — no pre-start plan cache on the watch.** The watch holds a full `WorkoutDetail` only after a
session exists. `RemoteExecutionPayload` is pushed only for an active workout with a plan revision.
Offline start therefore has nothing to start from until a plan-only cache and push path exist.

**B5 — payload size is unmeasured and probably over the transport limit.** No plan fixture exists to
measure. A six-item plan with warm-ups is plausibly 10–20 KB; a ~150-entry load catalogue is roughly
40 KB. WatchConnectivity application context and `transferUserInfo` are both bounded around 65 KB, so
plan + catalogue must be assumed to exceed it. Measure from a real issued plan and plan on file
transfer, not context update.

**B6 — the watch's provisional index is concrete, not absent.** `nextSetIndex` produces a working
index from its local view, so a partition produces two concrete claims on the same index. This
confirms D2/D4 rather than contradicting them, and means renumbering acts on an existing number;
the merge must also preserve the warm-up convention (≥1000).

## 7. Event schema deltas

Confirmed against code: no new server table is required.

- Client ledger entry: `entry_id`, `workout_id`, `device_id`, `device_seq`, `kind`, `payload`,
  `created_at_local`, `clock_offset_s`, `plan_watermark`, `ack_state`.
- Server mapping: `start` → `workout.start`; `add_set` → `workout.add_set`; `update_set`/`remove_set`
  → existing events; `execution_change` → `record_execution_change`; `finish` → finish.
- New event types: `late_reconciliation`, `reconciliation_closed`, `late_rejected`, and
  `plan_adopted` (records that an offline execution bound to a plan).
- `ios_issued_plan.execution_id` is an additive column; the existing live-plan index is unchanged.

## 8. Conflict resolution against the code

- Replay of an identical add-set request is already a no-op by full field comparison; a distinct set
  at the same index is a rejection. D4 converts the rejection into renumbering at the merge layer,
  before the write, so the `UNIQUE` constraint is never violated.
- Edit and remove are already events ordered by `event_id`; a later edit does not resurrect a
  removed set (`_sets` keeps the removal). That matches D7's "removed wins, edit retained".
- `restore_set` exists and is unused by the iOS client; the merge must not emit it accidentally.
- Warm-up indexes and working indexes are separated by convention, not schema; the merge must keep
  that convention or warm-ups will collide with working sets.

## 9. Migration strategy

Additive only, no data migration:

1. `ALTER TABLE ios_issued_plan ADD COLUMN execution_id TEXT` (nullable; filled at issue).
2. Client ledger introduced as `OfflineCapture` version 2, with a version-1 decode-and-migrate path
   (B3). Existing queued operations replay unchanged.
3. `MutationJournal` retired for execution writes once the ledger owns them; read paths and receipts
   unchanged.
4. No submodule pointer or database backup changes beyond the usual release gate.

## 10. WP1 checklist answers

1. **Can start bind a supplied execution id?** Not today: `workout.start` mints `uuid4`. The change is
   small — accept an optional `workout_id`, validate it, and add the field to `_ios_closed_fields`.
   A retried start already returns the existing in-progress workout, so adoption is half built.
2. **What does the watch cache?** The full `WorkoutDetail` for an **active** session only; no
   pre-start plan cache (B4). Plan and catalogue will not fit the context transport (B5).
3. **Tests asserting ownership or mirror mode.** Server: `tests/test_ios_watch_ownership.py` (four
   tests: owner and revision at start, takeover, stale index as extra work, watch cannot author a
   change). iOS: `WatchMirrorTests`, `Phase2ClientTests` (takeover and `isMirroringWatchSession`),
   `WatchExecutionEngineTests` (`not_owner` conflict), plus the `AppModel` guards.
4. **Does `build_item`'s load branch extract cleanly?** Yes, with care: it is contiguous, but it
   writes roughly a dozen locals later consumed by the item (basis, reason, e1RM provenance, decay,
   refs). Extract a `LoadSolution` record and have `build_item` consume it; the parity test then
   compares the record, not the item.
5. **Upgrade mid-workout.** See B3: the version guard is the hazard, not the schema.
6. **Catalogue size.** Unmeasured; estimate ~40 KB for the library plus plan size (B5).

## 11. Decisions needed before S1

1. **B1** — relax the single in-progress invariant, or define a hard conflict. Recommended: relax
   `active_workout` to prefer the newest row and let the web UI show both; the schema already permits
   it.
2. **B2** — the exact bind rule for date and TTL after an offline start. Recommended: accept when the
   local start falls inside `created_at…expires_at`, and `for_date` is today or yesterday.
3. **B3** — version-1 migration (recommended) or gated release.

## 12. Consequences for the WP0 plan

- WP0 §6 is confirmed and can be simplified: the ledger is a client concern and `workout_event` is
  already the server's append-only record. No server event-sourcing work package.
- S1 gains two prerequisites: the bind rule (B2) and the capture-version migration (B3).
- S4 gains the plan-only watch cache and the transport decision (B4, B5) — move B4 from S4 to S1 if
  offline start is to be demonstrated early.
- D1's soft check alone is not sufficient; B1 needs a decision first.
