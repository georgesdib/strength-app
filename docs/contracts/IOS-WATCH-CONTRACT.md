> **Canonical shared contract.** This is the portfolio-owned source for the server/client watch contract. Backend implementation remains in `strength-training-app/`; its old path is a compatibility pointer.

# iOS Phase 6 — watchOS companion contract

**Status:** Phase 6.2 complete and closed 2026-11-10: 6.0 (S1–S4, shared core), 6.1 (server
watch contract), 6.2a (embedded watch target), 6.2b (credential handoff) and 6.2c (read-only
Today). Physical Apple Watch acceptance was owner-confirmed 2026-11-14 (W1–W12 and R all confirmed).
Decisions locked 2026-11-09; design remediation 2026-11-09. Target platforms: **iOS 27.0** and
**watchOS 27.0**.

**Offline execution amendment — in force and closed 2026-11-23.** Device-independent offline
execution replaces the target/ownership gate and the phone relay: a plan belongs to the pair, either
device may start, execution writes are phone-committed, and the watch token is read-only for them.
See §14.1 for the applied amendments and the canonical
[plan](../plans/UNIFIED-OFFLINE-EXECUTION.md). Physical-device user testing was done and owner-confirmed 2026-11-25.

## 2026-11-19 amendment — frozen plan and execution substitutions

The [resolver prescription structure plan](../plans/RESOLVER-PRESCRIPTION-STRUCTURE.md) changes this
contract as follows; where they differ, this block wins.

- Plan editing is removed. A plan is frozen at start; the phone may declare **execution
  substitutions and additions** on the workout (never sets, never plan content), pushed over
  WatchConnectivity and stored as append-only events.
- `plan_revision` is plan identity only and never changes after start. Execution-view updates are
  ordered by an execution watermark returned by `GET .../execution`; the watch applies a payload
  only when that watermark is at least its local one and keeps unconfirmed WatchConnectivity
  events.
- §10.4 `plan_item_mismatch` is retired for new clients: an annotated substitution set is
  accepted; the legacy off-plan fallback remains for replayed old plans.
- Plan fetch and start may be performed by either device of the pairing. The watch can start
  offline from its cached plan; execution writes are committed by the phone, not the watch token.
- §21's phone relay is implemented as the phone-commit transport: the watch's start/set/event/
  finish operations travel to the phone, which commits them with its own credential. Offline start
  is implemented.
- `substitutes_plan_item_index` is added to the set payload; an added exercise is an off-plan set.

## 2026-11-22 note — per-rep motion capture withdrawn

The [watch motion metrics plan](../plans/WATCH-MOTION-METRICS.md) proposed an amendment adding
100 Hz accelerometer, gyroscope and gravity capture per rep. It was approved and implemented on
unmerged branches, then withdrawn when the plan closed as a failed project: rep segmentation could
not be validated without labelled captures. **No motion-capture amendment is in force.** The
proposed payload fields (`lower_ms`, `lift_ms`, `pause_ms`, `rom_m`, `steadiness`,
`confidence`, `method_version`) are not part of this contract, nothing here authorises capture or
upload of raw motion, and this contract is otherwise unchanged by that attempt.

## 1. Purpose

The watch fetches the server-issued plan, starts the workout, logs sets and rest, shows heart
rate, finishes with sRPE, and saves its HealthKit strength workout. The phone keeps readiness and
prescription requests, may declare execution substitutions/additions, and may log, rate and finish
the same pairing session; it commits the watch's execution writes with its own credential. The
phone is not a read-only mirror (S5, 2026-11-23).

## 2. Scope

- A watch app target in the `StrengthApp` repository, sharing a Swift package with the iPhone app.
- Its own paired server device and bearer token, minted by the phone and handed over once.
- ~~A plan carries an explicit execution target (`phone` or `watch`); the server records it and only
  the target device may start it.~~ **Superseded 2026-11-23 (S5):** a plan belongs to the pairing;
  either non-revoked device may start it.
- The watch is pinned to the home server: the phone hands over `homeBaseURL` and a monotonic
  `configVersion`, never the phone's currently active Away route.
- Plan fetch and start from either pairing device, within the existing issued-plan rules. Start is
  available offline from the cached plan; execution writes commit through the phone.
- Set logging with optional mean and per-rep velocity (only when the plan supplies a velocity
  target), rest timer, form rating and finish with sRPE and productivity on the watch.
- Execution telemetry (rest and set events with their original `occurred_at`) so the server
  timeline keeps the times the user acted, not the replay times.
- Offline-first execution: every mutation is persisted locally before the network call and
  replayed in order; partial flushes are normal. The watch starts offline from its cached plan and
  binds the execution at first sync; execution writes are committed through the phone.
- Heart rate during the session and one `traditionalStrengthTraining` HealthKit workout with
  heart rate, active energy and the effort rating derived from sRPE.
- Plan-revision propagation so a substitution made on the phone reaches the watch without
  disturbing a set in progress.
- The phone as a full participant in a watch-started session: execution substitutions/additions,
  set/form/velocity logging and finish are allowed, and it commits the watch's queued operations.
  No mirror mode and no take-over.
- Active-session Set, Session and Plan destinations, with refresh and reconnect reconciliation,
  idle-warning visibility during execution, and explicit completed/abandoned-elsewhere messaging.
- Idle detection and automatic abandonment of forgotten sessions. The 24h hard threshold is
  accepted and unchanged.

## 3. Non-goals

No readiness entry, prescription request, history, progress, settings or exercise library on the
watch. No heart-rate zones, no Shortcuts automation, no Apple Intelligence/PCC, no complications,
no watch-side pairing UI, no cellular or away-server support, and no app-side HealthKit cleanup:
if both devices save a workout, the athlete deletes a duplicate in Health. The watch is a home-gym
device on the same LAN as the server.

The watch sends its queued execution operations to the phone over WatchConnectivity for commit
(phone-commit transport); it does not notify the phone to auto-open the app. The phone discovers
a watch-started session through its normal foreground refresh. WatchConnectivity also carries the
phone→watch credential/config handoff and the plan nudge in section 10.

Offline start is implemented: the watch starts from its cached plan and binds the execution at
first sync. The phone-commit transport lets the phone perform set/event/finish with its own token;
the watch token is read-only for execution. The watch performs no Home/Away switching and never
follows the phone's Away route.

## 4. Locked decisions

| # | Decision |
|---|---|
| D1 | The watch is its own server device (`kind = watch`), with its own token and independent revocation. |
| D2 | Plan fetch requires the server (or a cached plan); start works offline from the cached plan, and logging and finish work offline and replay. Execution writes commit through the phone. |
| D3 | **Amended 2026-11-23.** Both devices of the pairing may log sets, rate form and finish a session, subject to the merge rules; the phone declares execution substitutions/additions. Ownership is provenance only. |
| D4 | iOS and watchOS share a `StrengthCore` Swift package; views stay per-platform. |
| D5 | `issued_plan_ttl_seconds` becomes 14400 (4h). The same-server-date rule is unchanged, so a plan still cannot cross midnight. |
| D6 | Idle warning at 3h without activity; automatic abandonment at 24h. Sets are preserved. |
| D7 | Heart rate is displayed; zones are not. Each device that saves a workout writes it once; duplicates are accepted (D11). |
| D8 | The watch never computes training numbers; it displays server values and sends user input. |
| D9 | Deployment targets: iOS 27.0 and watchOS 27.0; the package declares both. |
| D10 | A watch session requires an `HKWorkoutSession`. The watch saves one HealthKit workout per session it ran, keyed by a stable external UUID; a session with no saved workout is possible only on an unrecoverable HealthKit failure and is reported. The phone may save its own workout for the same session (D11). |
| D11 | Credential handoff is state, not events: one `updateApplicationContext` payload with a server-issued epoch and an acknowledgement. No queued event copying of tokens. |
| D12 | Execution-view updates never overwrite: the watch applies only a watermark at least as new as its own, and a replayed set from a legacy plan edit is preserved as an off-plan set rather than dropped (legacy replay only; a new client sends `substitutes_plan_item_index`). |
| D13 | **Superseded 2026-11-23 by S5.** A plan belongs to the device pairing, not to a target kind: either non-revoked device may start it, and `execution_target`/`wrong_execution_target` no longer exist. See §9 and §14. |
| D14 | The watch is pinned to `homeBaseURL`; config changes carry a monotonic `configVersion` and apply only between sessions with an empty outbox. No Home/Away switching. |
| D15 | Offline-first after start: sets, forms, telemetry, finish and HealthKit are local-first; the network is opportunistic and partially flushed. |
| D16 | **Superseded 2026-11-23.** Post-finish sync is foreground retry plus next-open sync; offline start is implemented from the cached plan and needs no pending-session shell. |
| D17 | **Amended 2026-11-23.** The watch captures optional mean and per-rep velocity per set, one 1–5 form rating per exercise, and session productivity at finish; the phone can log, rate and finish the same pairing session and commits the watch's writes. No take-over path. Correcting a watch-owned set's velocity after acknowledgement is a post-workout History edit on the server (append-only mean and per-rep VBT overrides); the iOS client's report is read-only for now. |

## 5. Platform targets and project shape

- The iPhone app keeps `IPHONEOS_DEPLOYMENT_TARGET = 27.0`; the watch target uses
  `WATCHOS_DEPLOYMENT_TARGET = 27.0`; `StrengthCore` declares `.iOS(.v27), .watchOS(.v27)`.
- One Xcode project (`project.xcproj`, Xcode 27's JSON format), one shared scheme plus a watch
  scheme; the watch app is embedded in the iPhone app.
- No third-party dependencies. The watch app uses the same API base URL and bearer scheme as the
  iPhone.
- CI builds the watch scheme for a watchOS 27.0 simulator; the iPhone suite and the package tests
  remain the test gates.

## 6. StrengthCore extraction

### 6.1 Goal and shape

Move platform-neutral code into a local package without changing iPhone behaviour, then let the
watch consume the same code. One library target (`StrengthCore`) with folder boundaries
(`Models`, `API`, `Session`, `Offline`, `Support`) and one test target. No module-per-type
split and no dependency-injection container.

### 6.2 Boundaries

- Allowed imports: `Foundation`, `Security`. The core has no `SwiftUI`, `UIKit`,
  `WatchKit`, `HealthKit`, `WatchConnectivity`, `UserNotifications`, `AudioToolbox` or
  `Combine`, and no `#if os()`.
- Platform-specific behaviour is injected by the app: rest notifications, HealthKit, Watch
  Connectivity, the credential service/account names and the storage location.
- The API client keeps taking an `IOSSession` (base URL, token, device id); it never reads the
  Keychain itself.
- DTOs stay `Codable` and `Equatable`; request bodies and error mapping do not change.

### 6.3 Staged extraction

Each stage is a separate, reviewable change; the iPhone suite must be green at every stage boundary.

1. **S1 — Models.** `APIModels`, `Phase2Models`, `ExecutionModels`, `JSONValue` and pure
   formatting/validation. Tests move with the code. No behaviour change.
2. **S2 — Networking.** `IOSAPIClient`, the same-origin redirect policy and `APIError` mapping.
   The same requests, headers and retry rules; the existing client tests move and stay green.
3. **S3 — Persistence and credentials.** `MutationJournal`, the offline capture/outbox and
   `KeychainStore` (service and account injected). File formats stay readable by the existing
   data, so an upgrade does not lose a pending operation; the iPhone journal's 16-entry cap and
   conflict behaviour are unchanged.
4. **S4 — Session engine.** Extract the session state machine from the 2,200-line `AppModel` one
   operation at a time, in this order: start, add set, form rating, remove set, finish/abandon,
   plan edit, recovery reconciliation. Each slice introduces a value-type state and an effect enum,
   moves one operation, and changes no view. `AppModel` remains the `ObservableObject` adapter
   that publishes state and executes effects.
5. **S5 — Watch target (moved to 6.2).** Creating the embedded watch app target, scheme,
   deployment target, Info.plist and CI job belongs to 6.2, where credentials and plan fetch give
   it a purpose. It is not part of the 6.0 core extraction.

### 6.4 Acceptance

- Every stage: the existing iPhone unit suite passes with the same test count (tests may move, not
  disappear); the package builds for iOS 27.0 and watchOS 27.0; no view file changes; no API
  payload or header changes; the same server-call order for the same user actions.
- S4 slices additionally prove parity for the moved operation: success, retry, conflict and
  offline paths; if parity cannot be demonstrated, revert that slice only.
- The extraction is complete when the iPhone app no longer owns models, networking, journal or
  session transitions, and the package builds for iOS 27.0 and watchOS 27.0. The watch target
  itself is 6.2.

### 6.5 What not to do

Do not rewrite `AppModel` wholesale, move views into the package, add generic repositories or
use-case layers, change the public surface the views bind to, or change a server contract as part
of the extraction.

## 7. Credential handoff

### 7.1 Device model

- `ios_device` gains `kind` (`phone`/`watch`), `parent_device_id` (the minting phone) and
  `credential_epoch` (server-issued integer, incremented on every mint).
- At most one non-revoked watch per phone, enforced by a partial unique index on
  `(parent_device_id)` where `kind = 'watch' AND revoked_at IS NULL`.

### 7.2 Minting

- The phone calls `POST /api/ios/v1/devices/watch` with `{"label":"Watch"}`. In one
  transaction the server revokes the parent's active watch (if any), inserts the new device with
  `credential_epoch = max(prior epochs for the parent, 0) + 1`, and returns
  `{device_id, label, epoch, token}` once; only the digest is stored.
- **Superseded 2026-11-23 (S5):** replacing a watch no longer retires the pairing's live plan;
  the plan belongs to the pairing and the new watch reads it through its parent phone. There is no
  target column and no "requested for Apple Watch" state. The historical paragraph below is retained
  for the old contract only:
- The same transaction supersedes any live plan whose execution target is the replaced watch. A
  plan is bound to the device id it was issued to and is retired, never re-targeted: `plans/current`
  reports `none` instead of advertising a ready plan the watch can no longer start. Without it the
  phone (which resolves the plan by requester) and the watch (which resolves it by target) could
  disagree about the same row — "requested for Apple Watch" on the phone, "No workout for Apple
  Watch" on the watch, for a workout that already existed.
- Minting is **identity-idempotent**, not receipt-idempotent: a lost response produces a new
  epoch and device, and the previous watch token is revoked. There is never a second active watch
  and no plaintext token is stored for replay. Mint is rate-limited per phone.
- The tracked server config enables minting (`watch_enabled: true`). The code default stays
  `false`, so a missing or malformed config still fails closed.
- The phone mints when no active watch exists, when the watch reports missing credentials, or when
  the owner deliberately taps **Pair Apple Watch** to rotate an active watch. A successful
  acknowledgement stops all further automatic minting.

### 7.3 Delivery and acknowledgement

- The phone sends one `updateApplicationContext` payload under a versioned key:
  `{schema, epoch, configVersion, homeBaseURL, deviceID, token?, issuedAt, status}`.
  `homeBaseURL` is the Home server, never the phone's active Away route.
- `token` is present for a new epoch. A same-epoch, higher-`configVersion` refresh omits it and
  the watch keeps its existing token; this is the only context sent after the token was
  acknowledged. `status` is `ready` or `revoked`.
- `updateApplicationContext` is asynchronous, coalesced to the latest value and may be delayed
  until the counterpart app runs. The design therefore treats it as latest-wins state, not as a
  message queue.
- The watch accepts a payload when `epoch` is greater than its stored epoch, or when the epoch
  is equal and `configVersion` is greater. It validates the schema and base URL, writes a new
  token to its Keychain, then acknowledges with a second `updateApplicationContext`:
  `{schema, ackEpoch, configVersion, deviceID, status: "ready" | "missing" | "revoked",
  homeBaseURL?}`.
- **Epoch lineage rule:** epochs are monotonic within one parent phone's watch history and are
  not globally comparable. Epoch ordering is applied only when the incoming `deviceID` matches
  the stored `deviceID`. A token-bearing credential for a different device starts a new
  credential lineage even if its numeric epoch is lower; this is how a watch moves to another
  iPhone. A tokenless probe can never start a lineage, clear revocation, or replace a valid
  token. A cross-device revocation is ignored.
- A stale or duplicate payload is ignored but acknowledged again with the stored epoch, so a
  delayed delivery cannot roll the watch back. A revoked credential at the same epoch is not
  resurrected.
- A tokenless probe is metadata only. If it names a different device or newer epoch, the watch
  may replace metadata **only when it holds no token**; it adopts the probe as `missing`, clears
  any stale token and acknowledges that adopted identity so the phone can mint. A valid token or a
  revoked credential is never replaced by a tokenless probe.

### 7.4 Retry and foreground recovery

- The phone retries only on a WC activation change, a reachability change, the phone entering the
  foreground, or an explicit `credentialsMissing` request from the watch. At most three attempts
  per foreground session, with 2s/10s/30s backoff; there are no background timers and no tight
  loops.
- On launch/foreground both sides exchange contexts. The phone re-sends when `ackEpoch < epoch`;
  the watch asks again when it has no credentials.
- If the watch reports missing credentials after a send, the phone re-mints (new epoch) rather than
  resending an old token that may never have arrived. The watch accepts the higher epoch.
- If the phone is relaunched after minting but before the acknowledgement, the in-memory token is
  gone. The phone sends a tokenless duplicate context at the stored epoch: a watch that has the
  token re-acks, and a watch without it reports `missing`, which triggers a new mint.
- A different-device acknowledgement is never judged by its epoch. If no token handoff is in
  flight, the phone mints one fresh epoch in its own lineage and sends the token; if a token handoff
  is already in flight, the stale acknowledgement is ignored. A same-device older-epoch
  acknowledgement only triggers a replacement while the current credential is still unacknowledged;
  once paired, a delayed stale acknowledgement is ignored.
- Automatic minting is bounded to two attempts per foreground session, with one mint task at a time,
  so repeated stale acknowledgements cannot create a mint/ack loop. The manual **Pair Apple Watch**
  action remains the escape hatch. A token-bearing new-device lineage, or a newer token in the same
  lineage, is the only way to replace a valid old token or a revoked credential.
- A delivered and acknowledged token is never re-sent.

### 7.5 Missing and revoked credentials

- Any `401`/`403` from the server makes the watch wipe its token, mark credentials missing, stop
  retrying API calls, and show “Open StrengthApp on your iPhone”. It retries only on foreground or
  when a new context arrives.
- The phone, on foreground, reads `GET /api/ios/v1/devices` on the **Home** server: if a
  previously paired watch is absent or revoked it mints; if the watch is active but reports
  missing credentials it mints a new epoch (rotation). A first-run phone with no stored watch
  relationship never mints merely because the app entered the foreground; the owner must tap
  **Pair Apple Watch**.
- Revoking the watch from Settings is deliberate: the server device is revoked, the watch is sent
  a `revoked` context so it wipes its token, and the phone suppresses automatic re-minting until
  **Pair Apple Watch** is tapped again. A revocation context naming a different device is ignored,
  and a stale revocation for the matching device is ignored.
- Revoking a phone also revokes its active child watch in the same transaction; the DELETE response
  includes `revoked_watch_ids` so a legacy stranded watch is visible. This prevents a replaced
  phone from leaving an independently usable watch token behind.
- Revoking a watch, directly or through its phone's cascade, supersedes its live plan in the same
  transaction. A repeat revocation also retires a plan left behind by an older server build.
- Re-pairing the phone itself does not resurrect a watch token; the phone mints a new watch device
  after its own pairing succeeds.

### 7.6 Security

- The token never appears in a log, error description, analytics event, URL, file, UserDefaults
  value, notification or crash report; `Authorization` headers are redacted in diagnostics.
- Credentials travel only in `updateApplicationContext`. They are never sent through
  `transferUserInfo` or `sendMessage`, which could deliver a stale queued copy.
- The watch stores the token in `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`; the phone holds it
  in memory only until the acknowledgement and then clears it. A config-only refresh therefore
  carries no token.
- The payload is accepted only from the paired WC session, with a known schema and the same base
  URL validation used by pairing. No debug or hard-coded token exists outside an explicit
  `#if DEBUG` simulator seam.

### 7.7 Handoff failures

| Situation | Behaviour |
|---|---|
| WC not activated / watch not paired | Watch shows the instruction; phone retries on activation. |
| Phone app not running | Context is delivered when it next runs; no background wake is attempted for credentials beyond the OS's own delivery. |
| Delivery delayed | Latest context wins; the epoch guard prevents a rollback. |
| Acknowledgement lost | Phone resends the same epoch; the watch ignores and re-acks. |
| Token revoked mid-session | Watch wipes on 401, pauses API calls, requests credentials; queued local operations remain. |
| Duplicate mint attempt | Partial unique index plus revoke-on-mint; no second active watch device. |

### 7.8 Home server and config refresh

- The watch is pinned to the phone's Home server for its whole lifetime. The payload carries
  `homeBaseURL`; the Away URL is never sent and the watch never probes or switches routes.
- All watch device operations — mint, device-list reconciliation, revoke and automatic recovery —
  use a dedicated session pinned to `homeBaseURL`, carrying the phone's existing bearer token and
  device id. They never use the phone's active Away route; an unreachable Home fails the watch
  operation instead of minting against Away.
- `configVersion` is a phone-local monotonic integer, independent of `credentialEpoch`. Saving a new
  home address or changing the reachability preference that selects it increments it.
- The acknowledgement carries `homeBaseURL` so the phone can verify that the watch applied the
  desired Home address, not merely a matching version number. If the watch reports a version above
  the phone's desired version, or a different Home URL at the same version, the phone raises its
  desired version above the observed one and sends one config-only context. This re-baselining is
  bounded, never lowers the watch's version, does not change the credential epoch, and does not
  re-send the token.
- The watch accepts a newer `configVersion` only when it has **no active session and an empty
  outbox**. Applying a new base URL while queued operations exist would leave them pointing at the
  old server, where their idempotency receipts live; the watch therefore defers the change.
- If the home URL changes while queued operations target the old URL, the watch flushes them to the
  old URL first. If that is impossible it surfaces a conflict and keeps the old URL; it never
  silently retargets the queue.
- Reachability failures mean **offline**, never “switch server”. Cellular availability does not make
  the home LAN reachable.

## 8. Plan availability and start

- `issued_plan_ttl_seconds` changes from 3600 to 14400 in `config/ios.v1.yaml`; validation
  already allows 60–86400. This is a start window, not a workout lifetime.
- The server-date rule stays: a plan whose `for_date` is not today returns `410 plan_expired`.
  Late-night sessions regenerate rather than extend.
- The plan request carries no target. The plan is scoped to the pairing — the phone that
  requested it, or the phone that minted the requesting watch — and `GET /api/ios/v1/plans/current`
  resolves it for either device of that pairing. Either non-revoked device may start it; there is
  no "plan for the watch" choice to make and no `wrong_execution_target` response.
- The watch reads `GET /api/ios/v1/plans/current` on launch, on foreground and on **Refresh**.
  **Retrieve workout** is Refresh, not a transport.
- `POST /api/ios/v1/workouts` with `issued_plan_id` starts the session and sets
  `owner_device_id` to the calling device. A retried start with the same plan returns the
  existing in-progress workout; the existing `409 workout_active`, `410 plan_expired`,
  `410 plan_consumed` and `409 plan_not_ready` responses keep their meaning.
- The watch starts offline from its cached plan and no longer needs the server or phone to begin.
  The start binds the execution at first sync; execution writes then go through the phone.
- The watch must have HealthKit workout authorisation before it starts (section 11). If it does
  not, it explains why and offers to log on the phone instead.
- The watch derives a clock offset from the server time in `bootstrap`/`today` and stamps
  `performed_at` and `ended_at` with server-adjusted time. The server rejects a timestamp more
  than a minute in the future, so a fast watch clock must not surface as a server error.

## 9. Ownership and phone mirror (superseded by S5)

> **S5 applied 2026-11-23.** `workout_session.owner_device_id` is provenance only. There is no
> `409 not_owner` gate, no take-over endpoint, no mirror mode and no target picker. The watch
> credential is read-only for execution: every execution write answers `403 watch_read_only`, and
> the watch commits through the phone. Abandon stays open to any device. Any
> non-revoked device of the pairing may write, start, finish or abandon a session; plan edits
> remain phone-only. The text below is retained for history only.

- Owner and non-owner both write; the server sets `owner_device_id` at start for audit.
- `POST /api/ios/v1/workouts/{id}/takeover` is removed and returns 404.
- The phone does not disable set, form or finish controls for a watch-started session.
- The watch does not become read-only when the phone owns the session.
- Abandon is allowed from any authenticated device.

## 10. Plan revision and offline conflicts

### 10.1 Revision contract

- Every plan write (swap, add, remove, set-count, move) increments
  `workout_session.plan_revision` in the same transaction and returns the new value.
  `GET .../execution` returns it with the plan.
- The watch stores the revision with its snapshot and never writes plan content.

### 10.2 Propagation

- After an edit the phone, while foreground, sends the new execution payload to the watch over
  WatchConnectivity as a queued `transferUserInfo` nudge; the single-slot application context stays
  reserved for the credential handshake. This is a nudge, not the source of truth: the watch also
  refreshes on foreground, after each set and on demand.
- The payload carries `plan_revision`; the watch applies it only when it is equal to or newer than
  its snapshot, and only at an idle point (10.4).

### 10.3 Reconnect order

When the watch regains connectivity with pending work:

1. Flush pending set/form/telemetry operations in their original order, each with its original
   idempotency key and timestamps.
2. If any flush step fails, stop. Do not fetch or apply a snapshot while the queue still holds
   unacknowledged work; keep the local state and expose retry/error status.
3. Fetch `GET .../execution`.
4. If the fetched revision is newer, replace the local snapshot and its revision.
5. Resume the UI on the new snapshot. A newer plan is never applied before the pending sets are
   flushed. Reconnect and refresh are single-flight, so overlapping requests cannot double-apply.

### 10.4 Mismatch policy

> **Retired for new clients 2026-11-23.** A new client sends `substitutes_plan_item_index` on the
> set, and a stale `plan_item_index` is kept as extra work with its provenance. The `409`
> fallback below applies only to a replayed plan issued before the change.

- A replayed set carries the `exercise_id` actually performed and the `plan_item_index` it was
  logged against. If the phone swapped that item while the watch was offline, the server rejects
  the set with `409 plan_item_mismatch` rather than silently attributing it to the new exercise.
- The client then retries once with `plan_item_index = null` (an off-plan set) keeping the
  original exercise, load, reps, RIR, `performed_at` and idempotency-derived identity. The set
  is preserved, volume still counts by exercise, and the session summary and telemetry record a
  visible “plan changed while offline” note. The original `plan_item_index` is retained in the
  telemetry event as provenance, so the performed plan item is not lost even though the accounting
  link is cleared.
- This is automatic data preservation, not a silent reinterpretation: the user sees the note, and
  the plan is not rewritten to make the set fit.

### 10.5 Stale snapshots and in-progress input

- The watch applies a payload only when its revision is greater than or equal to the cached one;
  an older or delayed payload is ignored. A stale snapshot can never overwrite a newer revision
  because the watch never writes plans.
- A plan update arriving while the user is entering a set is deferred until that entry is
  committed or cancelled; it is not allowed to change the target under the user's fingers.
- If the current item is swapped before any set is captured, the watch updates the label at the
  next idle point. If a set was captured, that set keeps its performed exercise and the mismatch
  policy applies on replay.

### 10.6 Phone edits while the watch is offline

Phone edits remain allowed, subject to the existing rule that an item with a logged set on the
server cannot be swapped. The phone cannot see a set the watch has captured but not yet sent, so
it may swap an item the watch has already performed. That is accepted: the replay preserves the
set as off-plan (§10.4) and the revision guard keeps both devices coherent afterwards. There is no
server-side reservation or locking while the watch is offline.

### 10.7 Offline-first execution and network policy

- **Network states:** `unknown`, `online(home)`, `offline`. “Cellular available” is **not** online:
  the server is on the home LAN. The watch does not switch servers or fall back.
- **Start gate:** the watch starts from its cached plan, including with no server or phone; it
  binds the execution at first sync. Execution writes are phone-committed.
- **Persist first:** after start, every set, form, telemetry event and finish is written to the
  session store before the request. The UI shows captured/pending until acknowledged.
- **Partial flush:** the outbox flushes in order and acknowledges per operation; it stops on the
  first failure and never clears an unacknowledged operation. Reconnecting mid-session and
  flushing a prefix is normal.
- **Retry:** on failure wait 5s, 15s, 60s, then every 5 minutes; reset on success. Automatic
  retries stop after a 15-minute window from the first failure of a burst, with the final wait
  clamped to the window's end; a foreground, a network-path change or an explicit retry starts a
  new burst. Authentication failures are not retried: they clear to "credentials missing" and
  leave the queue intact. No tight polling; the watch is on battery.
- **Finish:** the finish intent and `ended_at` are persisted, HealthKit is saved locally, and the
  server finish is queued. The summary retries while visible; if the app is suspended, the queue
  survives and syncs on next open. There is no guaranteed background sync.
- **Timestamps:** `performed_at` and `ended_at` are captured at action time and replayed unchanged;
  the sync time never replaces them.
- **Config changes** wait until the session is finished, synced and the outbox is empty (7.8).

## 11. Watch execution lifecycle

### 11.1 States

`idle → fetching → ready → starting → active(running/resting) → finishing → finished`, plus
`abandoned` and the recovery states `suspended`, `terminated` and `reconciling`.

### 11.2 HealthKit is the liveness anchor

- The watch starts an `HKWorkoutSession` and `HKLiveWorkoutBuilder` before the active UI is
  shown. This is what keeps the app running when the wrist is lowered or the screen dims.
- In 6.3 the session is started and must report `.running` before the server workout may start;
  a session that never runs is a hard start failure. The builder, heart rate and the exactly-once
  save arrive in 6.5, so a 6.3 session saves no HealthKit workout.
- HealthKit **workout authorisation is required to start a watch session**. Without it the app
  cannot be relied on to stay alive, so the watch refuses to start and explains the choice
  (enable Health access, or log on the phone). Heart-rate read authorisation is optional: without
  it the session runs and simply shows no HR.
- If a session is somehow running without an HK session, the app treats itself as foreground-only:
  every action is persisted, and the UI says logging may stop when the screen locks.

### 11.3 Lifecycle matrix

| Event | Behaviour |
|---|---|
| Wrist lowered / screen dims | HK session keeps the app alive; timers continue; the UI dims; a tap wakes it. Logging needs no continuous screen. |
| App backgrounded (Digital Crown, another app) | Same as above while the HK session is active; state is persisted on every action. |
| System suspension (no active HK session) | The app may suspend; the session store is authoritative; resume on next activation. |
| System termination / low power / reboot | HK session ends; on relaunch the store and server are reconciled (11.5); the HK workout is recovered per section 12. |
| User force-quits the app | Same as system termination; no workout is finalised unless the finish intent was already persisted. |
| Screen lock / Always-On | The dimmed screen shows the current set; no computation depends on it. |
| Network drops mid-session | The set persists; the outbox flushes what it can on reconnect; no blocking error, retry with backoff. |
| Finish while offline | Finish and `ended_at` persist; HealthKit saves locally; the server finish queues; the summary shows “syncing”. |
| App suspended after finish, before sync | The queue survives; sync runs on next open. No background-sync guarantee. |

### 11.4 Set capture

- **Log set** first performs one atomic local write of the operation (set payload, timestamp,
  idempotency key, plan item attribution) and only then updates the UI to “captured, syncing”.
  The network call is asynchronous and may fail without losing the set.
- A captured set is never re-entered because the screen dimmed, the app backgrounded or the
  network failed; duplicate taps are suppressed by a local operation id plus the server's
  idempotency receipt.
- The rest timer's end date is persisted and recomputed on relaunch; it never depends on the UI
  remaining active.
- The same rule applies to form ratings, finish and telemetry: persist first, then send.

### 11.5 Interrupted-session recovery

On launch, the watch reads its session store and `GET .../execution`:

| Local | Server | Behaviour |
|---|---|---|
| active | in_progress | Resume: restore the snapshot, restart the HK session, flush pending operations; `owner_device_id` is provenance only, so there is no read-only case (S5, 2026-11-23). |
| active with pending finish | completed/abandoned | Flush nothing; show the conflict and the preserved summary; do not recreate the workout. |
| active | no active workout | Show explicit “completed elsewhere” / “abandoned elsewhere” wording, keep the local sets and summary, offer clear. |
| finishing | in_progress | Resume finalisation: retry the server finish and the HealthKit save (section 12). |
| finished | completed | Clear the store after the summary is acknowledged. |

### 11.6 Execution telemetry (watch)

The watch emits only what it observes: `set_started`, `set_completed`, `rest_started`,
`rest_completed`, `rest_skipped`, `rest_extended`, `exercise_started` and
`exercise_completed`. It never emits `workout_paused`/`workout_resumed` (the watch has no
pause), or an event for a set or exercise that never started. A rest closes exactly once:
`rest_skipped` when the lifter ends it early — the −15 s control bound for zero is that command,
matching the phone's Skip — or `rest_completed` when it runs out or the next set starts. A skip
is a deliberate end, not a pause: the server derives duration and deviation from the timestamps,
and the time after the skip is outside the interval. `set_completed` gains `set_id` only after the matching add-set is
acknowledged; without a mapping it sends none. Payloads stay minimal: `set_index`,
`prescribed_rest_s`, `added_s`.

### 11.7 Form rating, VBT and productivity (6.6; extended 2026-11-14)

- A watch-owned session records one 1–5 form rating per exercise after **Done with exercise** (or
  at finish) and, when the plan supplies a velocity target, optional mean and per-rep velocity per
  set. Bodyweight or uncalibrated work is not asked for a speed.
- Session productivity (1–5 or **Not recorded**) is captured on the finish screen; it defaults to
  not recorded and matches the phone input.
- All of it is captured local-first in the existing ordered outbox; a rating is never inferred, and
  **Not recorded** is a valid outcome everywhere.
- The watch does not correct a set after acknowledgement; the phone corrects a set with one
  `update-set` call (S5 removed the mirror lock). Post-workout correction still happens in the
  server's History edit (append-only VBT overrides), not on the watch.

## 12. HealthKit idempotency and recovery

### 12.1 One workout per saving device

- At start, generate a `sessionUUID`, persist it **before** starting the HK session, and use it
  as the HK workout metadata external UUID (`HKMetadataKeyExternalUUID`). The workout is
  `traditionalStrengthTraining` with the real start and end dates.
- The watch saves one workout when it ran the session. The phone saves one when it finishes a
  session. Both may save, and the athlete deletes a duplicate in Health. The app never deletes,
  merges or rewrites HealthKit records automatically (D11).

### 12.2 Finish protocol

1. Persist a finish intent: `{endedAt, sRPE, effort, hkState: pending, serverAcked: false}`.
2. End collection at `ended_at` and call `finishWorkout` on the live builder.
3. On success, persist `hkState: saved`. On failure, leave `pending` and retry on the next
   launch/foreground.
4. Independently enqueue the server finish. A server retry never triggers a second HK save.

### 12.3 Crash and relaunch during finalisation

- On relaunch, first query HealthKit for a workout whose external UUID equals `sessionUUID`. If
  one exists, mark `saved` and do not save again.
- If none exists and the builder survived (same process), retry `finishWorkout`.
- If none exists and the builder is gone (relaunch), rebuild a **minimal** workout from the
  persisted intent with the original start/end and effort, no HR samples, and save it once. If
  HealthKit refuses, mark `unsaved`, show the summary and do not retry indefinitely. Never
  create a second workout.
- If the app relaunched mid-session it starts a new HK session for liveness and the resumed
  segment's HR. That segment is **not** saved as its own workout: at finish the resumed builder is
  discarded and the single minimal workout above is saved with the original start. Crash recovery
  therefore trades HR samples for one workout with truthful timestamps; the summary says so. If a
  workout with the external UUID already exists, the resumed segment is discarded too.
- The external UUID plus the persisted `hkState` are the exactly-once mechanism; the server's
  idempotency is separate and cannot create duplicates in HealthKit.

### 12.4 Permissions

- Workout authorisation is required to start (§11.2). HR read denial only removes the HR display.
- If authorisation is revoked mid-session, HR collection stops; the finish save may fail. The app
  reports it once, keeps the server session intact, and does not retry in a loop.
- Abandon ends the HK session without saving a workout; if a workout was already saved (only
  possible after a finish), it is left saved.

## 13. Watch UI contract

An active session exposes three destinations. Set is the main screen; Session and Plan open as
watch-appropriate sheets from the Set or exercise-list header. Opening either sheet must not clear
the selected exercise, active set or execution state, and closing it restores the same context.

1. **Set** — exercise name, “Set n of m”, target load × reps @ RIR, last set, current HR, a large
   **End set** button when running, and the rest countdown when resting.
2. **Session** — elapsed time (from the server's `started_at`), completed and pending set counts,
   tonnage clearly marked provisional while operations are pending, sync/network status and
   actionable errors, **Refresh**, **Retry sync**, **Undo last set** where supported, the next
   exercise when the authoritative plan has one, and **Finish**.
3. **Plan** — the full exercise sequence, read-only, with completed, current and upcoming state and
   a marker when the plan was updated. It offers no way to select, start, log or end an exercise;
   the exercise-navigation lock is unchanged, so the Plan screen cannot be used to bypass it.

- **Rest start.** The rest is anchored at the End-set stamp, not at the moment the RIR/velocity
  entry finishes; that entry time is rest. The set's `performed_at` is the Start-set time.
- **Rest end.** The watch schedules one local notification for the open rest's end (asked once
  at session start) and re-points or cancels it when the interval is extended, shortened or closed;
  the on-screen haptic remains. A denied permission never blocks logging.
- **Idle warning.** The server-derived stale state is advisory and shown on Set, Session and Plan:
  “No activity for 3h — the server may abandon this session.” It never blocks a set, changes the
  workout or terminates anything locally.
- **Ended elsewhere.** A completed or abandoned server session uses explicit wording (“Workout
  completed elsewhere” / “Workout abandoned elsewhere”); the raw status identifier is never shown.
  Locally captured sets stay visible and the clear-record action remains available.
- End flow: summary, sRPE picker (Digital Crown, 1–10), productivity (1–5 or **Not recorded**),
  **Finish**. Productivity defaults to “not recorded” and is a real input, matching the phone.
- Persistent states: offline banner with pending count (“offline · 4 pending”), “Plan updated”,
  plan-expired/regenerate, “credentials missing”, “resume session”,
  “finish saved on watch — syncing”.
- The watch never labels itself online because cellular is available; only a successful home-server
  call does. It never offers a server switch.
- After finish the summary stays visible and retries; if it is dismissed or the app suspends, the
  outbox syncs on next open.
- A captured set shows a distinct confirmation before the server acknowledges; the screen never
  claims “saved” on a failed request.
- No keyboard text entry except an optional short note if it proves necessary; v1 omits notes.
- Always-On dims to the Set screen; no complication.

**Active refresh.** A refresh action is available on Set and Session. It flushes queued operations
first and then fetches the authoritative execution snapshot; it never requires returning to the
exercise list and never bypasses the exercise-navigation lock. A failed flush leaves local state
and the queue intact and does not apply a snapshot.

**Phone during a watch session.** The phone opens the same active-workout view with every control
enabled; S5 removed mirror mode, the disabled controls, the take-over confirmation and the banner.
The phone commits the watch's queued start, set, form and finish operations with its own
credential, either device may log and finish, and abandon is available on both. The watch stays
editable throughout.

## 14. Server API changes

| Route | Change |
|---|---|
| `POST /api/ios/v1/devices/watch` | New. Phone-authenticated; revokes the previous watch, mints a new epoch, returns the token once. |
| `GET /api/ios/v1/devices` | New. Lists devices with kind, label, epoch, created/last-seen/revoked. |
| `DELETE /api/ios/v1/devices/{device_id}` | New. Revokes the watch from phone or itself. Revoking a phone also revokes its active child watch and returns `revoked_watch_ids`. |
| `POST /api/ios/v1/prescriptions` | No execution target. Issues one plan for the pairing (the phone and its active watch); a request from either device supersedes the pairing's previous live plan. |
| `GET /api/ios/v1/plans/current` | Returns `execution_id` and `load_catalogue`; a watch resolves the pairing's plan through its parent phone. No `execution_target`. |
| `POST /api/ios/v1/workouts` | Any non-revoked device of the plan's pairing starts it; no target check. Sets `owner_device_id` (provenance), `plan_revision = 0` and `last_activity_at`; response includes them. |
| `GET /api/ios/v1/workouts/{id}/execution` | Adds `owner_device_id`, `plan_revision`, `last_activity_at`, `stale`, the frozen `plan`, and the `execution` block `{workout_id, watermark, substitutions, additions}`. |
| `POST /api/ios/v1/workouts/{id}/execution` | New, phone token only (`403 not_phone` from a watch): appends one `substitution` or `addition`; the server solves the prefill or records `prefilled_load_kg: null` with `prefill_reason`, and the response is the same `execution` block. Idempotent by the body `event_id`. |
| Existing set/form/finish routes | No owner check; any pairing device writes. A set may carry `substitutes_plan_item_index`. A stale `plan_item_index` is kept as extra work instead of returning `409 plan_item_mismatch`, which is retired for new clients. |
| Plan-edit routes | Removed. All five R8 routes return `404`; a substitution or addition is the only mid-session change. |
| `POST /api/ios/v1/workouts/{id}/takeover` | Removed. Returns 404. |
| Existing abandon route | Allowed by any device; records the device. |
| `POST /api/ios/v1/prescriptions` settings | Adds `technique_throttle` (boolean, main-work scope): MOD-TECH-001 is applied when the plan is built and frozen into it. Omitted by a client that does not send it. **Implemented 2026-11-23.** |
| `POST /api/ios/v1/workouts` | Binds the plan's `execution_id` as the workout id (minted at issue, migration `0076`); accepts the athlete's `started_at` and binds by the plan's issue window with `for_date` today or yesterday; identity and state decide a start, never elapsed time — the same `execution_id` returns the existing session even after another pairing device completed it, without reopening it, so a replayed offline start can continue into late reconciliation; a different execution may run beside an open one; a different `execution_id` for the same plan is `409 execution_id_mismatch`. **Implemented 2026-11-23.** |
| `POST /api/workout/start` (web UI) | `409 plan_pending_for_phone` when an unexpired phone plan is outstanding for today; `start_anyway: true` proceeds. **Implemented 2026-11-23.** |
| `GET /api/ios/v1/plans/current` | Adds `load_catalogue` (`load-catalogue/v1`): one entry per taxonomy exercise, built by the resolver (`engine.build_item`) with `base_load_kg`, `accessory_load_kg`, `increment_kg`, flags, the live `dose_load_kg`/`dose_sets_cap` override and `vbt_target`, so a substitution can be prefilled offline with the same decision the server would make. Null on a plan built before the column existed. **Implemented 2026-11-23.** |
| `POST /api/ios/v1/workouts/{id}/execution` | Accepts `prefill_load_kg`, `prefill_catalogue_version` and `prefill_as_of`; verifies the value against the snapshot the plan shipped and records `prefill_verified`, `prefill_expected_load_kg`, `prefill_source`, `sets` (the replacement's own count, capped by a live erector dose), `set_groups` (the slot's structure re-solved for the substitute), `top_set {status, reason_code}` (always `not_applicable`/`substituted`) and `resolved_by` (`server` or `catalogue`), plus a mismatch reason, without rejecting the change. There is no legacy flag: a value means the phone applied the catalogue, a version with no value records a catalogue miss, and neither means the server solves. **Implemented 2026-11-23.** |
| `POST /api/ios/v1/workouts/{id}/complete` | Accepts `pending_devices`; a non-empty list opens a `reconciliation_window_days` (default 7) window recorded as a `late_reconciliation` event with the deadline. A completion whose `ended_at` is earlier than the recorded completion appends a `late_finish` event with that instant and the device, and never rewrites `ended_at`. **Implemented 2026-11-23.** |
| `POST /api/ios/v1/workouts/{id}/form` | A rating may arrive after completion inside the open window and is written to both the draft and `session_form_rating`. **Implemented 2026-11-23.** |
| `POST /api/ios/v1/workouts/{id}/update-set` | One correction event on the same `set_id`, so a correction keeps the set's identity instead of a remove-and-re-add; a late correction inside the window appends a superseding `clean_set` row, and one after a removal is `409 late_event_rejected`. **Implemented 2026-11-23.** |
| `POST /api/ios/v1/workouts/{id}/remove-set` | A removal may arrive after completion inside the open window; it appends a `clean_set` tombstone (supersedes the row, itself voided) and refreshes the totals. A late correction of a removed set is `409 late_event_rejected`, preserved and never resurrected. **Implemented 2026-11-23.** |
| `POST /api/ios/v1/workouts/{id}/execution-events` | Telemetry stays observational and timestamp-bounded, so a completed session accepts it without the reconciliation window applying. **Implemented 2026-11-23.** |
| `POST /api/ios/v1/workouts/{id}/sets` | A set may arrive after completion inside the open window: it is applied with its original timestamp, written into `clean_set` and the session totals are recomputed, with a `late_set` event. Carries optional `origin_device_id`; the server validates it belongs to the workout's pairing and persists it separately from the committing phone, without changing the set key. After the window the arrival is preserved as a `late_rejected` event and the response is `409 reconciliation_window_closed`. **Implemented 2026-11-23.** |
| `GET /api/ios/v1/workouts/{id}/summary` | Gains `reconciliation: {state: none|open|closed, pending_devices, closes_at}`; `pending_devices` reports only the devices still outstanding. **Implemented 2026-11-23.** |
| `POST /api/ios/v1/workouts/{id}/reconciliation` | `{device_id}` records that an expected device has nothing left to send, so a synced watch settles the window early instead of leaving it open for seven days. Idempotent; unknown device is a no-op. **Implemented 2026-11-23.** |

### 14.1 Offline execution amendments (in force 2026-11-23)

These amendments are **in force** and implemented on both sides. Physical acceptance was closed by
owner decision on 2026-11-23. Canonical statement:
[Unified offline workout execution](../plans/UNIFIED-OFFLINE-EXECUTION.md).

- **S5 — complete 2026-11-23.** §9's ownership gate, take-over and mirror mode are removed;
  `execution_target` and the per-target live-plan rule are removed so a plan belongs to the
  pairing, and the target picker goes with them. `owner_device_id` is provenance only; migration
  `0078` scopes one live plan per pairing and either non-revoked device may start. Execution
  writes are phone-only: a watch token gets `403 watch_read_only`, and the watch's writes travel
  through the phone. Migrations `0079`/`0080` drop the legacy target columns and add durable set
  origin. §21's pending-session deferral is removed now that offline start lands.

`config/ios.v1.yaml` gains `idle_warn_seconds` (10800), `idle_abandon_seconds` (86400) and
`watch_enabled` (tracked `true`; the code default remains `false` so a missing or malformed config fails closed; gates device minting), and
`issued_plan_ttl_seconds` becomes 14400. All are validated with closed ranges and fail-closed
parsing, like the existing TTLs.

## 15. Data model

Migration `0058_watch_companion.sql` (additive, no data rewrite):

- `ios_device.kind TEXT NOT NULL DEFAULT 'phone' CHECK (kind IN ('phone','watch'))`
- `ios_device.parent_device_id TEXT` (nullable; the phone that minted a watch)
- `ios_device.credential_epoch INTEGER NOT NULL DEFAULT 0`
- Partial unique index: one active watch per parent
  (`(parent_device_id) WHERE kind = 'watch' AND revoked_at IS NULL`)
- `ios_issued_plan.target_device_id TEXT REFERENCES ios_device(device_id)` (backfilled to `device_id`)
- `ios_issued_plan.pairing_device_id TEXT` — the plan's live scope (migration `0078`). Migration
  `0079` drops the legacy `target_device_id` and `execution_target` columns after all rows are
  backfilled.
- Target-scoped live index on
  `(COALESCE(target_device_id, device_id)) WHERE consumed_at IS NULL AND superseded_at IS NULL`
- `workout_session.owner_device_id TEXT` (nullable; NULL keeps legacy permissive behaviour)
- `workout_session.plan_revision INTEGER NOT NULL DEFAULT 0`
- `workout_session.last_activity_at TEXT` (backfilled from `started_at`)

The `sessionUUID`, `hkState` and the outbox live only in the watch app's local store; the
server stores no HealthKit data. Rollback drops the added columns and indexes; existing rows and
every other table are untouched.

Ownership is enforced after the idempotency receipt lookup, so a retry whose response was lost
replays its stored response instead of failing on the completed/abandoned state. Idle abandonment
runs lazily on start, today and execution reads and preserves every set.

## 16. Failure and recovery matrix

| Situation | Behaviour |
|---|---|
| No watch credentials | “Open StrengthApp on your iPhone”; retry on foreground; phone re-mints if needed. |
| Credential delivery delayed | Latest context wins; epoch guard; ack retried. |
| Token revoked | 401 wipes the watch token, pauses API calls, shows the instruction; queued local ops stay. |
| Plan not ready | Show status and retry; no local plan generation. |
| Plan expired / wrong date | “Generate a new plan on the phone.” |
| Workout already active | Show recovery: resume, or abandon then start. |
| Set write fails offline | Queued; pending badge; retry with the same key. |
| Finish fails offline | Queued; server still shows in-progress until replay. |
| Phone opens mid-session | Editable; both devices may log and the sets merge (S5 removed mirror mode). |
| Phone closed when the watch starts | Nothing is signalled; the phone shows the session on its next foreground refresh. |
| Phone substitutes an item offline | An execution event; the replayed set carries `substitutes_plan_item_index`, and a stale `plan_item_index` is kept as extra work (mismatch retired for new clients). |
| Watch relaunch with pending ops | Store reload, ordered replay, HK recovery; UI shows pending until acked. |
| HealthKit save fails at finish | Retry on launch; if the builder is gone, save the minimal persisted workout once; else report unsaved. |
| Watch stolen/lost | Any device of the pairing may finish or abandon; revoke the watch device. |
| Phone substitutes the current exercise | Allowed only before any set; watch applies at the next idle point. |
| Server unreachable at start | Blocking message; retry within the plan TTL; no fabricated session. |
| Plan belongs to another pairing | `404 plan_not_found`; no state change; the device must request its own plan. |
| Network drops mid-set | Set persists; partial flush on reconnect; no blocking error; backoff retry. |
| Home URL changes mid-session | Config change deferred until the session is finished, synced and the outbox empty; old-URL operations flush first. |
| Finish while offline | Finish and `ended_at` persist; HealthKit saves locally; server finish queues; summary shows “syncing”. |
| App suspended after finish | Queue survives; sync on next open; no background guarantee. |

## 17. Tests and acceptance

Server (pytest, default suite): TTL 4h boundary, same-date rejection, idle warning and 24h lazy
abandon (idempotent, sets preserved), pairing-scoped plan resolution and a start from either device
of the pairing, device mint/replace/revoke with one active watch and monotonic epochs, credential
epoch in device responses, idempotency replay, the late-reconciliation window and its late events,
and rollback of `watch_enabled`.

`StrengthCore` tests: outbox ordering, bounded retry, revision rejection, finish-after-sets,
relaunch recovery, and one parity test per extracted session operation.

Client: the existing iPhone suite stays green throughout 6.0; the watch scheme builds for a
watchOS 27.0 simulator in CI; a simulator UI smoke test covers fetch → start → log → finish.

Required scenario tests (unit/integration where possible, physical where not):

1. **Delayed or failed credential delivery:** context delayed past the first UI render, a lost
   acknowledgement, a stale epoch, and a revoked token; the watch ends ready once, with one active
   device and no duplicate mint.
2. **Relaunch with pending offline mutations:** three queued sets before relaunch, replay in
   order after relaunch, no duplicates, the pending badge clears only after acknowledgement.
3. **Backgrounding and returning during an active workout:** background for several minutes with
   the HK session active, return, log a set, and confirm the rest timer and elapsed time are
   correct.
4. **Phone plan modification while the watch is offline:** swap an unstarted item; on reconnect
   the pending set flushes first, the newer revision then applies, and the watch does not
   interrupt an in-progress entry. If the swap hits the item the offline set was logged against,
   the set is preserved off-plan and its original index is recorded in telemetry.
5. **Stale plan revision rejection:** a delayed R4 payload cannot overwrite a cached R5; an R6
   payload applies.
6. **Interchangeable logging:** the phone and the watch both log into the same pairing session,
   with no take-over, no read-only state and no `not_owner` response; a set logged on either device
   survives the merge.
7. **HealthKit finish retry without duplication:** simulate a failed `finishWorkout`, a crash
   before the save and a relaunch; exactly one workout with the session's external UUID exists,
   with the real start/end, and the resumed segment is not saved separately.
8. **Clock skew and timestamps:** a watch clock +5 minutes still logs and finishes; an offline set
   captured at T and synced later is stored at T in both the session and the telemetry timeline.
9. **watchOS 27.0 deployment and CI:** `xcodebuild -showBuildSettings` reports
   `WATCHOS_DEPLOYMENT_TARGET = 27.0` for the watch target and
   `IPHONEOS_DEPLOYMENT_TARGET = 27.0` for the app; the CI watch scheme builds on a watchOS 27.0
   simulator.
10. **Pairing scope:** the phone and its watch each resolve the same live plan from
    `plans/current`, either may start it, and a start under the same `execution_id` is one
    workout. A plan from another pairing is `404 plan_not_found`.
11. **Patchy Wi-Fi:** drop the network several times mid-session; each drop queues, each return
    partially flushes, and no operation is cleared before acknowledgement. Finish offline, reconnect
    two minutes later, and confirm the server matches the watch: same sets, same timestamps, one
    finish, no duplicates.
12. **Home config refresh:** change the home URL while no session is active and the outbox is empty;
    the watch applies the new `configVersion` and keeps its token. With an active session or
    queued operations, the change is deferred and the old-URL queue flushes first. The watch never
    follows the phone's Away route.
13. **Active-session corrections:** open Plan during a running set; the selected exercise, active
    set and row statuses are unchanged and Plan cannot select another exercise. Refresh flushes
    before it fetches; a failed flush leaves the queue and snapshot untouched and does not fetch;
    reconnect performs flush then reconciliation; the stale warning is visible on Set, Session and
    Plan; an abandoned session says “Workout abandoned elsewhere” without the raw status; the
    Session screen shows the next exercise; and phone mirror form controls are disabled with a
    phone form mutation rejected before any offline queueing.

Physical acceptance on the Ultra 4: phone plan (watch target) → phone app closed → watch fetch →
start → sets (one with mean velocity) → form rating after an exercise → phone substitution → watch
update → finish with sRPE → server completed → exactly one HealthKit workout with HR and effort. Repeat with the network dropped repeatedly during the
session and re-enabled only after finish: the session must sync, timestamps must stay at the times
the sets were logged, and a suspended app must sync on next open. Open Plan during a running set
and return to the same set. Refresh from Set and Session. Force a reconnect and confirm the flush
happens before the snapshot. Exercise the idle warning with a lowered test threshold or a seeded
`last_activity_at` (a real 3h wait is not an acceptance step); abandon the session from the phone
and confirm the watch says “Workout abandoned elsewhere” while keeping its local set count; check
the phone mirror form section is disabled.

**Historical record (Phase 6.7, 2026-11-14).** The mirror, take-over and legacy-mismatch clauses
in scenario 4, scenario 13 and the physical script above describe the pre-S5 contract; they are
retained as the Phase 6.7 acceptance record. Current offline execution acceptance is the
[unified plan §16](../plans/UNIFIED-OFFLINE-EXECUTION.md).

## 18. CI and distribution

- Add a watch scheme to the existing `ios-ci` workflow: build the watch app for a watchOS 27.0
  simulator, resolving a UDID the same way the iPhone job does, and keep unit tests on the iPhone
  target and the package.
- Assert the deployment targets in CI with `xcodebuild -showBuildSettings` so a future target
  bump cannot silently break the 27.0 baseline.
- Watch UI tests are not a CI gate in v1. The watch app ships embedded in the iPhone app; both
  need signing, and the existing personal-team 7-day signing applies.

## 19. Risks

- WatchConnectivity handoff latency and the absence of any guaranteed background wake; the epoch
  and ack design tolerates delay but not a phone that is never opened.
- LAN-only networking: the watch must be on the same Wi-Fi; cellular cannot reach the server and
  is not treated as online.
- watchOS suspension: logging depends on the HK session; persistence covers crashes but not user
  force-quits during finalisation. After finish, sync needs the app to run again; queued writes
  wait for the phone and the next active connection.
- Offline start is implemented from the cached plan; the watch binds the execution at first sync.
- Target enforcement is removed: a plan belongs to the pairing, so either device may start and the
  phone may commit the watch's writes.
- HealthKit finalisation across a crash: the backdated minimal-workout fallback needs a spike
  (§22) and may be the only path to exactly one workout.
- `AppModel` extraction is the largest refactor; a slice that cannot prove parity is reverted
  rather than forced through.
- Offline plan mismatch is accepted data loss of *plan attribution*, never of the set itself.
- Project format: `project.xcproj` is Xcode 27's JSON format; adding a watch target and scheme is
  Xcode-driven and CI grows accordingly.

## 20. Rollback

- Set `watch_enabled: false` and stop minting watch devices; the watch app becomes unusable and
  the phone is unaffected. Revert `issued_plan_ttl_seconds` and the idle keys.
- Drop migration 0058 with its paired rollback row if the feature is abandoned before data depends
  on it. Ownership enforcement is inert for rows with `owner_device_id IS NULL`.
- Each `StrengthCore` stage is independently revertible; reverting S1–S4 restores the app to its
  current structure without touching server data.

## 21. Historical deferrals (closed or superseded)

**Offline start — implemented 2026-11-23.** The watch starts from the cached issued plan under
the plan's `execution_id` and binds it at first sync; no pending-session shell or new table is
needed. The completed-start replay returns the same workout so queued sets can use late
reconciliation.

**Phone relay — superseded by the phone-commit transport on 2026-11-23.** The watch sends its
queued start/set/event/finish operations over WatchConnectivity; the phone commits them with its
own credential, and the watch operation id remains the idempotency key. The server refuses
execution writes from a watch token, so the old watch-token replay is retired. Offline start is
implemented separately: the watch starts from its cached plan and binds the execution at first
sync. Physical-device user testing was done and owner-confirmed 2026-11-25; see
`StrengthApp/docs/WATCH-GATEWAY.md` for the historical WP8 record.

**iOS post-workout correction.** The server already corrects a completed session from History →
Edit session, including mean and per-rep VBT overrides, with an append-only audit. The iOS client
exposes that history read-only; adding an edit screen would reuse the existing service and is not
part of this contract.

Recovery of an offline session that outlives the abandonment window; heart-rate zones; Shortcuts
automation; complications;
away-server/cellular support and watch-side Home/Away switching; watch-side readiness or history;
Apple Intelligence. Each needs a separate decision.

## 22. Validation spikes before implementation

These are technical proofs, not open design decisions; they run before the corresponding work
package and do not change the decisions above. The owner skipped the separate WP8 spike on
2026-11-20; the documented `sendMessage` relay is implemented directly, with physical acceptance
still required.

1. **WatchConnectivity (before 6.2):** measure `updateApplicationContext` delivery when the
   counterpart is backgrounded, killed and relaunched; confirm the epoch/ack loop converges, that
   no duplicate watch device is minted across a lost response, and that a `configVersion` change
   arriving mid-session is deferred rather than applied to a non-empty outbox.
2. **HealthKit (before 6.5):** confirm a minimal workout can be saved after relaunch with the
   original start date (backdated `beginCollection`), that a metadata UUID can be queried, and
   that a failed `finishWorkout` followed by a retry yields exactly one workout.
3. **Toolchain (before 6.2):** confirm the GitHub `xcode-27` image builds a watchOS 27.0
  simulator target and reports the deployment targets through `showBuildSettings`.
