# TRAINING INTELLIGENCE — ARCHITECTURE AND IMPLEMENTATION PLAN

**Canonical location:** this file, in the portfolio repository.
**Status:** delivered 2026-11-15, extended 2026-11-16. INT-1 to INT-8 are delivered (INT-8 closed with
no scope), INT-4c is parked on Apple's PCC entitlement, **INT-9 (the Siri AI adoption pass) is deferred
until iOS 27.3**, and **INT-10 (the local daily reminder nudge) was added on 2026-11-16 and is
implemented on the iOS client**, with physical-device acceptance outstanding. **INT-11 (Explain the
System, local knowledge retrieval) was accepted on 2026-11-16 and is plan-only; INT-12 (web search and
RAG) is deferred.** This plan document itself changes no runtime, API, schema, dependency,
prompt or training rule.

Amended 2026-11-15: §7.2 gained the iOS 27.0 framework facts and the measured context size, §7.5
refreshed the Siri AI preview status, and §7.6 added the readiness design and recorded that MCP is not
a Siri transport. Decisions 11, 14 and 15 were accepted that day. INT-7 delivered the read-only
intents plus the shared `StrengthIntents` module and is closed, owner-confirmed. INT-7b delivered the
workout lifecycle surfaces in four closed slices — Shortcuts automation, HomeKit scenes, Action button
and watch Siri, and the Shortcuts start/finish pair (decisions 15 and 16) — with the watch linked into
the shared intents module in 7b-3.

Amended 2026-11-16: §1.2 narrowed the notification exclusion, §11 gained INT-10 (decision 17,
`ADR-INT-019`), INT-11 (decision 18, `ADR-INT-020`) and INT-12 (decision 19, deferred), and §12
records the phases. INT-10 is a local client-side surface — it adds no server call, endpoint, schema
field, MCP tool or prompt contract, so the backend, the contract and the dependency graph are
unchanged. INT-11 is accepted but plan-only: a local docs/code explainer, not web access or RAG.
INT-12 consolidates the former web-search and RAG candidates into one deferred later step.

**Supersedes:** the forward-planning content of the earlier LLM and Apple Intelligence plans —
`strength-training-app/docs/LLM-INTEGRATION-PLAN.md` (except the items retained in §16.3) and the
Apple Intelligence/PCC items in `docs/plans/IOS-CLIENT-PLAN.md` §5. This plan is the single forward
plan for training intelligence. See §16.
**Owner:** the athlete. Decisions 1–18 are accepted; decision 19 (INT-12) is deferred. The plan is
delivered and further work needs a new decision (INT-9's adoption ADR, INT-12's provider/privacy ADR,
or a new proposal under §16.5).
**Roadmap:** phases INT-1 to INT-12, section 12. Backend implementation status stays in
[`ROADMAP.md`](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md);
this plan does not restate it.
**Companions:** [implementation audit](TRAINING-INTELLIGENCE-AUDIT.md),
[MCP and capability contract](../contracts/TRAINING-INTELLIGENCE-CONTRACT.md),
[architecture decision records](../decisions/TRAINING-INTELLIGENCE-ADR.md).

## 1. Purpose and boundary

Training Intelligence is a **read-only interpretation layer over the training data the server
already computes**. It has one job: turn authoritative numbers into an evidence-linked overview,
progression, review or explanation that a person or a model can read, without ever becoming a second
source of training truth.

It exists in three forms that share one core:

1. a **capability layer** in Python that composes the existing services into versioned,
   evidence-linked fact packages;
2. a **standalone MCP server** that exposes those packages as tools and resources to any MCP host;
3. a set of **native adapters** so the iPhone can use the same packages with Apple Foundation Models,
   Private Cloud Compute, or no model at all.

The core never calls a model, the MCP server never calculates, the app never calculates, and no part
of the system can change a prescription, a readiness score, a load or a training plan.

### 1.1 In scope

- Deterministic composition of existing metrics into a versioned response envelope.
- A separately deployable, read-only, authenticated MCP server with typed tools and resources.
- A compact baseline context and on-demand retrieval instead of whole-database payloads.
- Native iOS adapters, including Apple Foundation Models tool calling.
- Weekly Training Review as the first user-facing feature.
- Provider-agnostic model orchestration for the server and for the app.
- Evaluation, regression and cross-repository contract tests.

### 1.2 Out of scope (permanent for this workstream unless a new decision replaces it)

- Write-capable intelligence tools of any kind: no prescription, workout, readiness, symptom,
  measurement, settings or state mutation.
- Any model computing a load, e1RM, volume, readiness score, gate, adherence ratio or training
  decision.
- Re-opening or changing prescription, readiness, fatigue, volume or selection algorithms.
- A generic SQL, table, document or "query the database" tool.
- Multi-tenancy, user accounts, OAuth provider hosting, or public exposure of the server.
- Cardio tracking and watch-app intelligence.
- Live-Activity intelligence. (Daily reminder notifications are **in scope** as INT-10: local, on-device
  and precomputed, with no server call, no external model and no write. The exclusion applies only to
  the Lock Screen / Dynamic Island surface.)
- Depending on beta-only Apple APIs, including the iOS 27.3 Siri AI Developer Preview.
- Storing model output as a training artifact or as a prescription.

Lifecycle entry points (INT-7b) are therefore in scope: an intent may start or finish a session and run
a user-configured HomeKit scene, but it calls the existing operations and does not redefine them
(`ADR-INT-018`).

## 2. Architectural invariants

These are testable requirements, not aspirations. Each has a named test in section 11.

1. **One owner per metric.** A capability that returns a metric calls the module that owns it. No
   capability re-implements a threshold, window, gate or formula.
2. **One evidence schema.** `features/evidence.py` (`EVIDENCE_VERSION "2.0.0"`) is the only
   evidence envelope. The intelligence layer wraps it; it does not define a rival shape.
3. **Facts, not inference.** Every returned value is either `observed` (read from stored rows) or
   `derived` (computed by a named owner with a version). Interpretation is labelled and never
   presented as a fact.
4. **Unknown is not zero.** Missing, partial, voided or low-`n` data produces `status: "no_data"` or
   `status: "insufficient"` with explicit `missing` and `limitations` entries.
5. **No confidence score.** Gate, `n`, comparability, coverage and quality flags are the whole
   uncertainty vocabulary. Nothing invents a percentage.
6. **Read-only.** The tool registry contains no mutating verb, and a test asserts it.
7. **Transport-neutral core.** The capability layer imports no HTTP, MCP, model-provider or UI code.
8. **Model-neutral core.** The same fact package feeds MCP, REST and every model path.
9. **Data is data.** Retrieved training text is never instruction. No tool returns raw free-text
   notes by default, and the prompt treats every returned string as untrusted.
10. **Small by default.** The baseline context is a few hundred tokens; detail is fetched on demand.
11. **Deterministic byte-for-byte.** The same database state, arguments and builder version produce
    the same envelope and the same `context_hash`.
12. **No beta dependency.** Every shipped path works on a released OS and a released SDK.

## 3. Architecture

### 3.1 The seven layers

| # | Layer | Owns | Must never |
|---|---|---|---|
| 1 | **Authoritative training data** | SQLite schema, append-only writes, `queries`/`features`/`prescribe` metric owners | be duplicated outside layer 1 |
| 2 | **Deterministic analytical capabilities** | `intelligence/capabilities/*`: compose layer 1 into a versioned envelope | compute a metric, call a model, do I/O beyond a read transaction |
| 3 | **Context assembly and retrieval** | `intelligence/context.py`: baseline package, relevance rules, hashing, provenance | decide training policy or hide missingness |
| 4 | **MCP transport and tool exposure** | `intelligence/mcp/*`: auth, tool/resource registry, schema, serialisation, limits, audit | contain business logic, import the web server, write |
| 5 | **iOS-native intelligence adapters** | `StrengthCore/Intelligence` (models, REST client) and `StrengthApp/Intelligence` (FoundationModels tools) | calculate a metric, bypass the server |
| 6 | **Model providers and orchestration** | `intelligence/model/*` (server), iOS model adapters; prompt, validation, retry, cost | see the whole database, invent numbers, persist output as an artifact |
| 7 | **UI and conversational interfaces** | SwiftUI review/chat surfaces, web panel, CLI, Siri dialogs | be required for the deterministic path to work |

```
                 ┌──────────────────────────── layer 7 ────────────────────────────┐
                 │  iOS review / chat / Siri     web panel / CLI                    │
                 └───────────▲──────────────────────────────▲─────────────────────┘
                             │                              │
        ┌────────────────────┴─────┐          ┌─────────────┴──────────────┐
        │ layer 5  iOS adapters    │          │ layer 6  model orchestration│
        │ REST client + AFM tools  │          │ prompt · validate · trace   │
        └────────────▲─────────────┘          └─────────────▲──────────────┘
                     │ REST (envelope)                     │ in-process capability call
        ┌────────────┴──────────────────────────────────────┴────────────┐
        │ layer 4  MCP server        ◀── MCP hosts ──▶   REST adapter     │
        │ auth · tools · resources · limits · audit · schemas            │
        └────────────▲───────────────────────────────────────────────────┘
                     │ calls only
        ┌────────────┴───────────────────────────────────────────────────┐
        │ layer 3  context assembly (baseline package, hash, provenance) │
        │ layer 2  deterministic capabilities (envelope + evidence)      │
        └────────────▲───────────────────────────────────────────────────┘
                     │ calls only
        ┌────────────┴───────────────────────────────────────────────────┐
        │ layer 1  queries · features · prescribe · workout · history    │
        │          SQLite (append-only, single athlete)                  │
        └────────────────────────────────────────────────────────────────┘
```

The arrow that matters: **layers 4, 5 and 6 all sit beside each other and all import layer 2, never
each other.** The MCP server cannot contain logic the REST adapter lacks, and the model layer cannot
bypass the capabilities.

### 3.2 Component responsibilities

| Component | Path (proposed) | Responsibility |
|---|---|---|
| Envelope and errors | `strength_coach/intelligence/envelope.py`, `errors.py` | one response shape, one error taxonomy, canonical JSON and hashing |
| Capabilities | `strength_coach/intelligence/capabilities/*.py` | one module per capability, each returning an envelope |
| Context builder | `strength_coach/intelligence/context.py` | compact baseline package, relevance rules, truncation policy, hash |
| Model orchestration | `strength_coach/intelligence/model/*.py` | prompt ids, provider choice, structured validation, trace, cost |
| MCP server | `strength_coach/intelligence/mcp/*.py` | transport, auth, registry, schemas, limits, logging |
| REST adapter | `strength_coach/web/server.py` + `intelligence/api.py` | the iOS routes, same envelopes |
| iOS models | `StrengthCore/Sources/StrengthCore/Intelligence/` | `Decodable` envelope, client, capability protocol |
| iOS Foundation Models | `StrengthApp/Intelligence/` | `Tool` implementations, `@Generable` output, availability, token budget |
| Evaluation | `tests/intelligence/`, `tools/intelligence_eval.py` | golden facts, grounding, protocol and regression |

### 3.3 Data flow

**MCP host path.** Host → `POST /mcp` → bearer auth → tool lookup → argument validation → capability
→ layer 1 services inside one read transaction → envelope → `structuredContent` + a serialised JSON
text block. Every call writes one audit record (tool, argument hash, row counts, duration, outcome);
never the payload.

**iOS path.** App → `GET /api/ios/v1/intelligence/...` (existing device bearer token) → the same
capability → the same envelope → `StrengthCore` decodes it → the view renders the deterministic
sections. If a model is enabled, its `Tool` implementations call the same REST routes and return
compacted `PromptRepresentable` strings, so the model sees a small projection of the envelope.

```
sequence — on-device narrative
  User      View            Model            Tool            REST            Capability
   │         │               │                │               │                 │
   │ tap ───▶│ availability? │                │               │                 │
   │         │──────────────▶│ session(tools:5)                │                 │
   │         │               │── call tool ──▶│── GET ───────▶│── envelope ────▶│
   │         │               │◀── compact ────│◀── JSON ──────│◀── facts ───────│
   │         │◀── @Generable │                │               │                 │
   │         │  narrative    │                │               │                 │
   │◀── text │  + fact refs  │                │               │                 │
```

## 4. The capability layer

### 4.1 One capability, one function

```python
# strength_coach/intelligence/capabilities/progression.py  (proposed)
def exercise_progression(conn, *, exercise_id: str, window_days: int = 84,
                         include_sessions: bool = False,
                         limit_sessions: int = 5) -> Envelope:
    ...  # calls features.strength_trend / features.exercise_history only
```

Rules:

- The signature takes already-validated primitives. Schema validation lives in the transport
  (MCP/Pydantic, REST) and is repeated in the capability for defence in depth.
- No capability raises a bare exception to the transport; it raises `IntelligenceError` with a
  stable `code` (`invalid_argument`, `not_found`, `unavailable`, `insufficient_data`,
  `internal`) and a message safe to show a model.
- No capability opens its own connection when the transport already supplied one; the server passes
  a read transaction so a multi-query capability is consistent.
- No capability formats prose. Prose is the model layer's job, or a static limitation string.

### 4.2 The response envelope

Full schema in the [contract](../contracts/TRAINING-INTELLIGENCE-CONTRACT.md) §3. The shape is:

```json
{
  "intelligence_version": "1.0.0",
  "capability": "training_overview",
  "schema_version": "intelligence.envelope.v1",
  "status": "ok",
  "as_of": "2026-11-14",
  "period": {"start": "2026-10-18", "end": "2026-11-14", "weeks": 4, "timezone": "Europe/London"},
  "units": {"load": "kg", "velocity": "m/s", "duration": "min"},
  "facts": {
    "attendance": {
      "value": {"completed_sessions": 8, "target_sessions": 12, "ratio": 0.67},
      "basis": "derived",
      "method": "strength_coach.features.attendance.summary",
      "evidence_ids": ["ev:..."]
    }
  },
  "evidence": [{"evidence_id": "ev:...", "evidence_version": "2.0.0", "...": "..."}],
  "observations": [],
  "coverage": {"sessions_considered": 8, "planned_sessions": "not_tracked"},
  "missing": ["no readiness entries in the window"],
  "limitations": ["attendance is target-based; no planned-session calendar exists (DEC-W7-01)"],
  "provenance": {"database": "coach.db", "database_revision": 1234, "config_revision": "..."},
  "generated_at": "2026-11-14T09:12:03Z"
}
```

`facts` is an object of **fact blocks**, never bare scalars, so `basis` and `method` cannot be
lost. A fact block with `basis: "observed"` names a table/repository; `basis: "derived"` names the
owning function and version. Anything interpretive goes in `observations` (AFC-3 only) or
`limitations`.

### 4.3 Baseline context versus on-demand detail

The baseline package (`context.py`) is deliberately small and is **not** appended to every tool
result. It is the package a model receives when it needs orientation before choosing tools:

| Section | Content | Budget |
|---|---|---|
| athlete | goal, priority order, days/week, constraints as structured flags, units, training age band | ≤ 120 tokens |
| programme | sessions/week, current session-type rotation, deload state, volume policy summary | ≤ 150 tokens |
| recent | last 3 completed sessions (date, type, working sets, sRPE presence) | ≤ 200 tokens |
| lifts | per-tracked-lift 28-day and 84-day e1RM median + n + quality flag | ≤ 250 tokens |
| readiness | last 7 days as coverage + trend direction, not raw rows | ≤ 80 tokens |
| signals | at most 2 open AFC-3 observations, with gate and `n` | ≤ 120 tokens |

Rules:

- **Injuries, symptoms, health measurements and free-text notes are excluded by default.** A capability
  that needs them (readiness/symptom context) must opt in explicitly and record it in the envelope's
  `privacy` block. This follows `LLM-INTEGRATION-PLAN.md` §8.1.
- Relevance, not sampling: most recent completed sessions, then the per-lift windows, then anything
  the specific question requires. No random rows.
- Truncation is ordered and recorded: current safety flags and the asked-about lift are never
  truncated; older session detail is.
- `context_hash` is SHA-256 over canonical JSON (reuse `features/evidence.canonical_json`) of the
  package plus `builder_version`, `schema_version` and the database stamp.
- The builder records `token_estimate` (character-based, ~4 chars/token) so the 4,096-token on-device
  budget can be respected before generation.

### 4.4 Caching and versioning

- **No cache in INT-1 or INT-2.** Measure first. The heaviest calls (VBT, 365-day e1RM) are on demand
  and bounded; an incorrect cache is worse than a slow read.
- **Shared derived analytics is a separate, broader design**, not an in-process cache:
  [`DERIVED-ANALYTICS-ARCHITECTURE.md`](https://github.com/georgesdib/strength-training-app/blob/development/docs/design/DERIVED-ANALYTICS-ARCHITECTURE.md)
  (2026-11-14). It proposes versioned, rebuildable per-set, session/exercise and weekly tables owned
  by the existing analytical modules, with on-demand fallback. Phase 0 is approved; **Milestone A**
  (revision ledger, build state, coordinator and safe publication) is implemented and audited, and
  **Milestone B** (core `derived_set`/`derived_session_exercise` materialisation, progress and
  strength-trend migration behind a readiness check) is implemented 2026-11-14 with parity and
  ODROID measurements recorded. **Milestone C** (weekly spinal exposures plus deload, outcomes and
  monitoring migration, with full-dataset parity and measured improvements) is also implemented.
  Snapshots remain optional and deferred; the INT integration review is a follow-up. The remaining
  operational item is follow-up **C-1**: a background maintenance worker that reconciles the derived
  build automatically on startup, periodically and after exercise-writer changes, replacing the
  manual `analytics build` trigger.

  The ODROID HTTP benchmark (2026-11-14) measured p95 6,201 ms for session details, 4,058 ms for
  overview, 3,800 ms for the programme summary and 1,663 ms for readiness. The owner accepted a
  latency-aware budget (T-1): fast ≤ 500 ms p95, slow/very-slow ≤ 7 s p95, no hard rejection, 20 s
  tool timeout; the transport is enabled with the full ten-tool catalogue. The rollout tracks four
  items: **C-1** automatic maintenance
  worker (systemd oneshot + timer sharing the backend checkout/venv, plus a post-restart run;
  installed and active on the ODROID 2026-11-15); **T-1** accepted
  2026-11-14 with ADR-INT-010 amended; **T-2** implemented - full catalogue with measured latency
  metadata in every tool description and no hiding of slow tools; **T-3** closed 2026-11-14 as a
  first pass, remeasured (deload flare lookup bounded, readiness config cached, one summary rule
  context): overview HTTP p95 672 ms, programme 278 ms, readiness 377 ms, session details 5,684 ms
  (still very_slow). **T-3a** is the optional, not-started session-details follow-up; T-3 improves
  performance rather than unlocking basic LLM functionality.

  Operational 2026-11-15: the MCP server runs as a systemd unit on 10.0.0.44:8765 with the full
  ten-tool catalogue and an explicit Host allowlist (address and `odroid.local`). It reads the
  production database read-only; the unit grants `ReadWritePaths` on the data directory because
  SQLite WAL needs `-shm`/`-wal` even for a read-only connection. The migration collision is
  resolved: production 0060 is development's plank-variants migration (applied at 22:17); analytics
  migrations are renumbered 0061-0063 on `development`, and a fresh production copy migrated
  0060-0063 and built ready
  without deleting the recorded row. T-3 profiling and its first remediation pass are recorded; the
  remaining session-details cost is a follow-up within the accepted budget.
- If a cache is added later it keys on `(capability, validated_args, database_stamp, config_revision,
  builder_version)`, where the stamp is the existing `PRAGMA data_version` + `conn.total_changes`
  pair already used by `features/e1rm_calibration.py`, and it lives in process memory.
- Versions are independent and all appear in the envelope: `intelligence_version`,
  `schema_version`, `context.builder_version`, and each `method` string names the owning function.
- A change to a metric definition is a change to the owning module only; the envelope does not
  re-version because a number moved.

## 5. MCP server architecture

### 5.1 Placement — recommendation

**Live in the existing backend repository as a separately deployable module. Do not create a fourth
repository.**

| Criterion | In `strength-training-app` | New repository |
|---|---|---|
| Reuse without duplication | imports `strength_coach` directly | needs the package published or vendored: a second copy or a release coupling |
| Layer-1 changes | same commit, same tests | cross-repo version negotiation for every metric fix |
| Test fixtures and migrations | already available | must be duplicated or fetched |
| Deploy isolation | separate process, separate unit, separate config | same, plus another repo to maintain |
| CI | one workflow, one lint/test gate | a third CI pipeline |
| Repository rule | "do not introduce a fourth repository without a compelling reason" | none found |

The module is a **separate deployable**, not a second application: its own console script, its own
config file, its own bind address, its own token file, its own systemd unit. It does not serve the
web UI, does not import `web`, and does not need the UI to be running.

### 5.2 Runtime and libraries

- **Protocol revision: 2026-07-28** (the current stable revision) with the SDK's built-in
  compatibility for legacy clients (≤ 2025-11-25). The spec revision removed protocol sessions and the
  `initialize` handshake, added `server/discover`, made the modern path stateless, and moved
  server-to-client requests into multi-round-trip results. A modern request is a self-contained POST,
  so horizontal scaling needs no sticky routing; a legacy client does, until it is not used.
- **SDK: the official Python SDK `mcp` 2.x** (`MCPServer`, formerly `FastMCP`). Python 3.11+ is
  already required. Pin `mcp>=2,<3` in a new optional dependency group so the coached runtime and
  existing deployments are unaffected until the extra is installed.
- **Transport: Streamable HTTP**, one `/mcp` endpoint, `json_response=True` for the read-only tool
  path (no progress stream needed, simpler proxying), with SSE available if a future tool needs
  progress. No deprecated HTTP+SSE transport. No stdio in production (stdio is a local debugging
  convenience only, and has no authentication).
- **Tools and resources only. No prompts capability in MVP.** Prompt text belongs to the host that
  owns the conversation; baking prompt engineering into the server would duplicate the model layer
  and make the server model-specific.

### 5.3 Authentication and authorization

Facts: there is no OAuth authorization server, no user store and no multi-tenancy. The MCP spec makes
authorization optional *for the protocol* but requires that any implemented OAuth follows its profile
(RFC 9728 protected-resource metadata, RFC 8707 resource indicators, OAuth 2.1).

Recommendation for MVP, subject to approval (`ADR-INT-004`):

- Bind to loopback and the owner's private tailnet only. Tailscale is reachability, not
  authentication: application auth is still required.
- **One opaque bearer token per MCP client**, stored as a SHA-256 digest in a git-ignored
  `config/intelligence.local.yaml`, never in the repository, never in logs. Tokens are generated by a
  CLI command, shown once, revocable by deleting the entry.
- A thin ASGI auth wrapper (not the SDK's OAuth middleware, because no authorization server exists)
  validates the token in constant time and returns `401` with
  `WWW-Authenticate: Bearer realm="strength-intelligence"`. No OAuth discovery document is published,
  because publishing one without an authorization server would be a lie.
- **Interoperability cost, accepted:** a hosted MCP client that insists on OAuth discovery cannot
  connect. Moving to OAuth 2.1 + a real authorization server is a separate, later decision and the
  only path to a non-owner user.
- **Single-athlete by construction.** No tool accepts an athlete, user or database parameter. A future
  tenant model (ROADMAP §4.19) must thread an authenticated subject through the capability layer; the
  envelope already reserves `subject` for that, and the current value is a fixed
  `{"athlete": "self"}`.

### 5.4 Configuration (proposed `config/intelligence.v1.yaml`)

```yaml
# Domain reason: the MCP endpoint is a separate deployable with its own exposure and limits.
enabled: false                 # off until INT-1 acceptance passes
bind_host: 127.0.0.1           # tailnet address added by the operator, never 0.0.0.0
bind_port: 8765
endpoint_path: /mcp
allowed_hosts: ["127.0.0.1:8765"]   # DNS-rebinding protection must stay on
max_request_body_bytes: 262144
max_window_days: 400
max_concurrent_calls: 4
rate_limit_per_minute: 60
tool_timeout_seconds: 20
read_only: true                # asserted by the registry test; cannot be flipped to false
```

Token hashes live in the git-ignored `config/intelligence.local.yaml`, following the
`config/llm.local.toml` precedent. Every key gets a domain-reason comment (repository rule).

### 5.5 Errors, validation and limits

| Situation | Result |
|---|---|
| Schema-invalid argument | SDK rejects before the handler; model sees an `isError` tool result with the field |
| Unknown exercise/session/workout id | `IntelligenceError("not_found")` → `isError` result with a short message |
| Window out of range, `from > to`, unknown enum | `IntelligenceError("invalid_argument")` → `isError` result |
| No data in the window | **not** an error: `status: "no_data"` with `missing` |
| Thin data (below the owning gate) | `status: "insufficient"`, gate and `n` preserved |
| Provider/DB failure | `internal`, message sanitised, traceback only in the server log |
| Unknown tool | JSON-RPC `-32601` (SDK) |
| Wrong token / revoked | HTTP 401/403 before parsing |
| Unsupported protocol version | JSON-RPC `-32022` (SDK) with supported versions |

Limits: `max_window_days`, `max_sessions` per page, 1 MiB maximum tool result, 20 s timeout, 4
concurrent calls, and a 256 KiB request-body cap (lowered from the SDK's 4 MiB default). A
capability that would exceed a limit truncates deterministically and says so in `coverage`; it never
silently drops rows.

### 5.6 Observability

- One structured log line per call: request id, tool, argument **hash** (not values), duration,
  row counts, response bytes, outcome code, client id.
- Never log payloads, tokens, health values or free text.
- Optional OpenTelemetry trace propagation via `_meta` (`traceparent`) later; the spec documents
  the convention but it is not required for a single-owner deployment.
- `GET /api/intelligence/health`-style liveness is not part of MCP; use the process supervisor's
  health check. MCP has no health RPC.

### 5.7 Deployment

Same host as the backend initially (separate unit), because the SQLite database is local and the
server is a single file. `systemd` unit, dedicated user, read-only bind of the database file,
`sqlite3` opened in read-only mode (`mode=ro`) — a defence-in-depth guarantee that the
intelligence process cannot write even if a bug tried. If the database later moves to a server
engine, the same module deploys elsewhere unchanged.

## 6. iOS-native adapter

Apple Foundation Models has **no MCP client**, and there is no first-party Apple SDK for MCP. The
official Swift SDK is Tier 3 and adopts protocol revisions on its own schedule. Putting MCP in the app
would therefore add an unmaintained client, a second auth surface and a network hop for data the app
already has an authenticated route to.

**Recommendation:** the app consumes the **same capability envelopes over the existing authenticated
REST facade**, and exposes them to Foundation Models as native `Tool` implementations.

```
StrengthCore/Sources/StrengthCore/Intelligence/
  IntelligenceEnvelope.swift      # Decodable mirror of the shared contract, versioned
  IntelligenceCapability.swift    # protocol: the 5 allow-listed capabilities
  RESTIntelligenceAdapter.swift   # IOSAPIClient + envelope decoding, no calculation
StrengthApp/Intelligence/
  IntelligenceAvailability.swift  # model availability, user consent, feature flag
  WeeklyReviewNarrator.swift      # AFM session, instructions, @Generable output
  WeeklyReviewTools.swift         # <=5 Tool implementations -> RESTIntelligenceAdapter
  NarrativeValidator.swift        # numeric grounding + evidence-ref checks
  WeeklyReviewView.swift          # deterministic sections + optional narrative
```

Constraints:

- `StrengthCore` gains **models and transport only**: no FoundationModels, no SwiftUI. This keeps the
  package buildable and testable without a model and usable by watchOS later.
- The app's tool surface is **capped at five** (Apple's guidance is 3–5 tools per request):
  `trainingOverview`, `exerciseProgression`, `weeklyReview`, `sessionDetails`,
  `readinessStatus`. The server's fuller catalogue is not exposed to a 4,096-token model.
- The model receives a **compact projection** written in Swift (a few fields per section), never the
  raw envelope. That projection is presentation, not calculation, and is covered by tests.
- No Swift computes a metric, a gate, an evidence id or a trend. If a number is not in the payload,
  the UI must not show it.
- Deterministic sections render first and never wait for the model. A missing/unavailable model
  degrades to the deterministic review, never to an error.

## 7. Model architecture

### 7.1 Provider-agnostic seam

The seam is the **capability envelope**, not a shared prompt. Each provider gets:

- the same fact packages (via a capability client);
- its own prompt id and version, its own output schema, its own validator;
- its own availability and cost policy;
- its own trace record.

```python
# server side (proposed)
class NarrativeProvider(Protocol):
    id: str
    async def generate(self, request: NarrativeRequest) -> NarrativeResult: ...
# implementations: NullProvider (default), OpenAICompatibleProvider (existing agents.client)
```

```swift
// app side (proposed)
protocol NarrativeGenerating { func narrative(for review: WeeklyReviewEnvelope) async throws -> WeeklyReviewNarrative }
// implementations: FoundationModelsNarrator, PrivateCloudComputeNarrator, None
```

Provider selection is explicit, never automatic on failure: a failed on-device generation shows the
deterministic review and an "unavailable" note. There is **no automatic fallback from on-device to
cloud**, because that would silently change the privacy boundary (`IOS-CLIENT-PLAN.md` §5 stands).

### 7.2 Apple Foundation Models — on device

| Fact | Verified position |
|---|---|
| Availability | `SystemLanguageModel.default.availability`; `.unavailable(.deviceNotEligible)`, `.unavailable(.modelNotReady)` and related causes must each have UI |
| Context | **4,096 tokens per session**, shared by instructions, prompts, tool definitions, tool output, `@Generable` schemas and the response (Apple TN3193) |
| Tools | `Tool` protocol (iOS 26+), `@Generable` arguments, `PromptRepresentable` output; Apple recommends **at most 3–5 tools** |
| Structured output | `@Generable` + `@Guide`; the schema text itself costs tokens |
| Token accounting | `SystemLanguageModel.tokenCount(for:)` and `.contextSize` (iOS 26.4+) |
| Overflow | `LanguageModelSession.GenerationError.exceededContextWindowSize`; recover with a new session from a condensed transcript |
| Offline | Works offline; no network permission needed; **no MCP** |
| Privacy | On-device; no data leaves the phone; no entitlement |
| Model abstraction | `LanguageModel` protocol (iOS 27.0) lets one `LanguageModelSession` host the on-device model, `PrivateCloudComputeLanguageModel` or a custom model behind the same API |
| Multimodal input | `DynamicProfile` (iOS 27.0) plus the Vision tools `OCRTool` and `BarcodeReaderTool` allow one image in a prompt; not used by INT-4, which is text-only |
| Model version | The on-device model changed in iOS 26.4 and again in iOS 27.0; Apple asks apps to re-test prompts per model version |

Design consequences:

- The weekly review narrative is generated in **one session**, with at most three tools, a short
  instruction (1–3 paragraphs), and a compact fact block. If the estimator says the request exceeds
  ~3,200 tokens, the app drops to a smaller projection or skips the narrative.
- Tools are used only where the model must decide what it needs. The review screen already has the
  facts, so the default path is **no tool calling**: facts go into the prompt, and `ToolCallingMode`
  is `.allowed` only for the "ask a follow-up" case.
- The output type is small: a headline, 2–4 observations each with fact references, and one
  limitation line. `GenerationOptions.maximumResponseTokens` is a guard, not the primary budget.

None of the three framework rows above changes INT-4's shape: the weekly review is text-only, runs on
`SystemLanguageModel`, and needs no image, no protocol abstraction and no per-model prompt matrix
beyond re-running the evaluation on each OS release.

The **4,096** in the table is the documented base context. The INT-4b device probe measured **8,192**
tokens with tool calling and guided generation on the current OS (`ADR-INT-017`), so the estimator
reads `contextSize` at runtime rather than hard-coding either number.

### 7.3 Apple Private Cloud Compute

`PrivateCloudComputeLanguageModel` (iOS 27.0+) provides a **32K** context and reasoning levels, uses
the same `LanguageModelSession` API, needs a network, has a **per-day quota** and requires Apple's
managed entitlement. It is a stable API in a released OS but **gated access**, so it cannot be the
default or a dependency. Its privacy story is Apple-mediated, not owner-mediated, and it must be
presented as server processing with a single Settings choice and a one-line disclosure. The owner
waived the earlier context preview and per-request consent flow (2026-11-15). Quota errors
(`.quotaLimitReached`) are a normal state with a clear message, never a retry loop.

### 7.4 Backend LLM

- Server-side inference, existing OpenAI-compatible client and settings (`agents/config.py`,
  `agents/client.py`); provider defaults to null.
- Orchestration: the model receives the capability *catalogue* (not the database), calls 1–8 tools,
  and returns a structured narrative validated against the same grounding rules.
- Retrieval path: a single `IntelligenceClient` protocol with two implementations.
  - `InProcessClient` — default for server-side use: calls the capability functions directly. No
    network, no token, no duplicated logic.
  - `MCPClient` — the official Python client against the deployed `/mcp` endpoint: used by the
    cross-transport conformance test, the evaluation harness, and any external host.
- The conformance test asserts that both clients produce **identical envelopes** for the same
  database snapshot and arguments. That is the mechanism that keeps MCP from drifting away from the
  capability layer.
- Cost/usage: every call records provider, model, token counts and latency in `run`/`run_event`;
  a per-day soft budget stops further calls. No background calls, no automatic retries that change
  the answer.
- Retention: prompts and outputs are **not** stored by default; the trace stores hashes, versions,
  token counts and the validation verdict (`DEC-LLM-01`).

### 7.5 Siri, App Intents and Apple Intelligence

| Capability | Availability | Decision |
|---|---|---|
| App Intents, App Entities, App Shortcuts | stable since iOS 16/17; `AppSchema` since iOS 18 | **adopt** (INT-7) |
| Shortcuts actions, Spotlight/`IntentValueQuery` | stable | **adopt** for read-only review/progression |
| App Intents in Apple Intelligence (schemas, donations) | shipped APIs (AppSchema iOS 18+) | **adopt selectively**; no onscreen entity donation in MVP |
| Siri AI Developer Preview (custom tool intents, app skills, onscreen awareness, cross-app actions, Spotlight semantic index) | **iOS 27.3 beta, open to any developer since 2026-11-03**; "API may change"; no App Store or external-TestFlight distribution; App Store submission opens in spring 2027; unavailable in the EU; daily usage limits, expanded access "for a fee" | **do not adopt**; make adoption additive (§7.6) |

Nothing in this plan depends on the Siri AI preview. The stable intents are useful without it: they
run from Shortcuts and from Siri's existing App Intents support.

The preview did not change the model surface: **iOS 27.3 ships no Foundation Models API change**, so
§7.2 and §7.3 stand as written. What 27.3 changes is access and vocabulary — custom tool intents,
app skills and the Spotlight semantic index are now documented for any developer. §7.6 records those
facts and the readiness INT-7 must carry so that a post-launch adoption adds capability instead of
forcing a rewrite.

### 7.6 Siri AI readiness — stable intents now, preview later

Facts recorded 2026-11-15 from Apple's news post, release notes, framework updates and Siri AI
documentation (links under Related). They update §7.5; they do not reopen §7.2–§7.4.

| Fact (2026-11-15) | Position |
|---|---|
| Access | Any developer may integrate through the iOS/iPadOS/macOS/visionOS **27.3** betas (developer beta 2026-11-03); needs an Apple Intelligence device and a supported language; unavailable in the EU on iOS/iPadOS/watchOS |
| Distribution | Xcode development build or internal TestFlight only — not external testers, not App Store builds; Apple opens App Store submission in spring 2027. The owner does not ship on the App Store, so the binding constraint here is the 27.3 install, not the submission date |
| Stability | Apple: "the App Intents API and Siri functionality may change" during the preview |
| Integration | `@AppIntent(.tool)` turns a custom intent into a `ToolIntent` (`@AppIntent(.tool, schema:)` when a schema is Shortcuts-only); Siri reads the `title` and `description` of the intent, its parameters and its entity properties; entities must be available to Spotlight |
| App skills | One `Skills.skillsbundle` per app target; each skill is `Skills/<skill-name>/SKILL.md` — YAML frontmatter with only `name` and `description`, then a Markdown body of at most 10,000 characters; a subset of the SKILL.md format with no scripts or reference files |
| Skills are advisory | Apple: "you can't use app skills to enforce deterministic behavior… Siri AI doesn't sequentially perform the tool intents that your skill lists" |
| Cost | Server-side Apple Intelligence features are subject to daily usage limits; expanded access will be "for a fee"; Apple has not published the terms |
| Schemas | There is **no health or fitness app-schema domain**, so a strength app cannot adopt a primary domain; its actions are custom tool intents |

**Why MCP is not a Siri transport.** Siri has no MCP client, cannot be pointed at a URL or a
JSON-RPC endpoint, and calls only your app's App Intents or schema actions; a `SKILL.md` is prose
guidance about those intents, not a transport descriptor. The MCP server therefore reaches Siri only
through the app: an intent calls the same envelope that a tool wraps. This is the plan's standing rule
— one capability layer, several projections (MCP tools, REST routes, App Intents) — and it is why no
MCP endpoint, token or tool catalogue is ever exposed to Siri. Consequences for the surfaces: "how
long was my previous workout" is a read-only intent over `history.list_sessions()`, not an MCP call;
it works on stable APIs today, without the preview and without the app knowing that MCP exists.

Design consequences:

- **Determinism stays in Python.** A `SKILL.md` is guidance to a model, not a specification. No
  skill file may state a load, percentage, e1RM, RIR, set count, readiness verdict, gate or
  prescription: those remain server-computed facts, and model text may only quote the envelope.
- **One capability source, one more surface.** Siri AI intents would call the same read-only REST
  envelopes as the app (`ADR-INT-007`). Siri AI is a fourth *surface* over the capability layer, never
  a second capability layer and never a place where training decisions are made.
- **No preview dependency.** Nothing in this plan imports a 27.3-only symbol. Readiness is metadata,
  indexing and view reuse — all stable APIs. The only preview symbols are added at adoption time.
- **Adoption is a decision, not a migration.** It needs a released OS, open App Store submission,
  Apple's published terms, a fee/quota position and a new ADR. It is not an extension of INT-7.

Readiness INT-7 ships now, so the later upgrade is additive:

1. every intent carries a `title`, a `description` and a `description` on each parameter;
2. every entity carries a `title` and a `description` on each `@Property`, and conforms to
   `IndexedEntity` (`IndexedEntityQuery` where lookup by identifier is needed) so Spotlight can find
   it without the app;
3. snippet views are ordinary SwiftUI views that a `CardSnippet` can host later;
4. `perform()` stays side-effect-free for the read-only intents, so turning one into a tool changes
   no behaviour; the only intents allowed a side effect are the INT-7b lifecycle ones, and their
   effect is a user-configured HomeKit scene, never a training mutation;
5. no build contains `@AppIntent(.tool)`, a `Skills.skillsbundle` or any other preview symbol until the adoption pass — App Store distribution is not a constraint for this owner, so this is a timing rule, not a shipping rule.

Deferred to adoption: the tool annotation, the skills bundle and its `SKILL.md` files,
`CardSnippet` presentation, `authenticationPolicy` on sensitive entities (27.3 has a known issue
where it may not force unlock before Siri displays an entity), a Siri Integration Advisor review and a
`SiriEvaluations` suite beside the intent unit tests.

## 8. First user-facing feature — Weekly Training Review

### 8.1 Why this one

It is the smallest feature that exercises the whole architecture (composition, evidence, envelope,
MCP, REST, native rendering, optional model) and it is genuinely useful weekly without becoming a
coaching prescription.

### 8.2 Deterministic content (never model-computed)

| Section | Source | Notes |
|---|---|---|
| Activity and adherence | `adherence_analytics.analytics()`, `attendance.summary()` | target-based attendance; no planned-session calendar |
| Completed sessions | `history.list_sessions()` | count, types, working sets, sRPE presence |
| Progression | `strength_trend.observations/summarize`, `exercise_history.history()` | 28/84-day medians, direction, `n`, breaks |
| Volume | `features/volume.py`, `prescribe/volume_budget.py` | per-pattern vs budget, exemptions, coverage |
| Readiness | `queries.readiness_series()`, `features/readiness_score.py` | coverage and trend (sign of the canonical composite change); observed only, no fill |
| Block/programme observations | `features/deload.py`, `features/regime_change.py`, `features/breaks.py` | events, not a stored block |
| Deviations | `features/observations.py` | at most two, with gate, `n`, evidence id |
| Quality and limitations | `workout.summary()["quality"]`, coverage, live `LIMITATIONS-REGISTER` ids | explicit |

### 8.3 Interpreted by the model (optional, additive)

- A two-to-four sentence headline about the week.
- Two to four "what changed / what to watch" statements, each **citing fact block keys or evidence
  ids**.
- One sentence on what the data cannot say.
- Nothing else. No load, percentage, e1RM, RIR or set count that is not present verbatim in the facts.

### 8.4 Grounding and validation

The narrative validator rejects: unknown fact/evidence references, a numeric token absent from the
fact set (after normalising units and rounding), a claim with `strength: "supported"` and no
reference, a prescription suggestion phrased as an instruction, and any content outside the schema.
Rejection is not silent: the deterministic review is shown and the model section is marked
unavailable with a reason.

### 8.5 Explicitly not in the review

No "you should deload", no load recommendation, no plan change, no injury diagnosis, no comparison to
other athletes, no prediction of results. Those are outside read-only intelligence and, for plan
changes, outside this workstream entirely.

## 9. Security, privacy and safety

| Risk | Control |
|---|---|
| Unauthorised access | tailnet + loopback bind, per-client bearer token (hashed at rest), 401 before parsing, revocable |
| Cross-athlete leakage | single database per deployment; no subject parameter; every query scoped to the configured DB; envelope carries a fixed subject |
| Write through a bug | SQLite opened `mode=ro` in the intelligence process; registry test forbids mutating tool names; no write service is imported |
| Prompt injection via data | free-text notes excluded by default; all strings treated as data; instruction text says so; adversarial fixtures in CI; no tool returns arbitrary user-authored text unless a capability explicitly requires it and labels it `untrusted_text` |
| Model-supplied arguments | schema validation + server-side range/bounds + identifier existence checks; the model cannot widen a window or name a user |
| Health-data minimisation | field-level outbound inventory (reuse `LLM-INTEGRATION-PLAN.md` §8.1) before any model path is enabled; injuries/symptoms/measurements excluded unless the capability needs them, and then listed in `privacy` |
| Local vs server inference | the UI states which model runs where; on-device never silently becomes cloud; PCC requires explicit consent and a context preview |
| Logging and retention | metadata only, no payloads, no tokens, 30-day operational log retention; model transcripts not persisted |
| Rate limiting and resource limits | per-token bucket, concurrency cap, timeout, body cap, window caps, result-size cap |
| Model output validation | schema + grounding + numeric checks + refusal to persist as an artifact |
| Unauthorised training mutation | no write tool exists; the existing prescription/approval path is untouched and remains the only way to change a plan |

The last row is the important one architecturally: the intelligence system has **no path** to a
prescription, not merely a rule against one.

## 10. Testing and operational architecture

| Layer | Requirement | Where |
|---|---|---|
| Deterministic capabilities | golden facts from synthetic fixtures; determinism (same input → same JSON and hash); boundary windows; empty DB; voided sessions; `n=1` and zero-variance series | `tests/intelligence/test_capabilities_*.py` |
| No-duplication guard | monkeypatch the owning feature function and assert the capability delegates; a static test asserts no metric/formula constants in `intelligence/` | `tests/intelligence/test_ownership.py` |
| Envelope contract | JSON Schema validation of every capability output; `basis` on every fact; evidence ids resolvable | `tests/intelligence/test_envelope.py` |
| Tool schemas | snapshot of `tools/list`; deterministic order; names/descriptions; `outputSchema` present; no `$ref` escaping the schema | `tests/intelligence/test_tool_schemas.py` |
| Invocation | official SDK in-memory client for fast tests, HTTP for transport tests; legacy (2025-11-25) and modern (2026-07-28) eras both exercised | `tests/intelligence/test_mcp_protocol.py` |
| Auth and isolation | missing/invalid/revoked token; token not in logs; no tool accepts a subject; 401 before parse | `tests/intelligence/test_auth.py` |
| Invalid arguments | every range and enum boundary; unknown ids; `from > to`; oversized window | `tests/intelligence/test_validation.py` |
| Missing data | unknown ≠ zero; abstention reasons surface; partial readiness never fills | `tests/intelligence/test_missing_data.py` |
| Error mapping | each `IntelligenceError` code → the documented tool result; stack traces never leak | `tests/intelligence/test_errors.py` |
| Transport parity | in-process and MCP clients return identical envelopes for the same snapshot | `tests/intelligence/test_parity.py` |
| iOS adapter | decode the shared fixtures; no metric arithmetic in Swift; the five-tool cap | `StrengthAppTests/Intelligence*` |
| Model grounding | golden fact pack; numeric-invention and evidence-ref tests; injection fixtures; timeout and unavailability | `tests/intelligence/test_narrative_*.py`, iOS unit tests |
| Regression | full existing suite unchanged; golden `prospective` and prescription fixtures untouched (`AFC plan` §5) | existing tests |
| Cross-repo | the contract's synthetic fixtures are checked into both repositories and byte-compared in CI | portfolio contract + both CI jobs |
| Deployment | start/stop the unit, health check, read-only database proof, log format, limit behaviour | INT-1 acceptance record |

**Evaluation of intelligence quality** (not just correctness): a fixed synthetic athlete dataset with
known answers; for each capability, the expected fact values are committed; for each model path, a
scored rubric of (factual grounding, coverage honesty, usefulness, brevity) on a small prompt set,
run manually at each phase gate. No claim of "better coaching" is made from an acceptance rate.

## 11. Implementation roadmap

Dependency-ordered, not date-ordered. Each phase is separately shippable and separately reviewable.
No phase may silently deliver the next phase's capability.

### INT-1 — Intelligence foundation and MCP server skeleton

**Implementation status (2026-11-14): the foundation is delivered; the MCP skeleton moved to
INT-1b.** The owner-directed INT-1 implementation prompt narrowed this phase to the read-only
foundation, so the transport, the second tool and the resources are now INT-1b. Implemented and
tested: the envelope, error taxonomy, capability registry, request validation, execution service,
bearer authentication, configuration bounds, request-context identity and one reference capability
(`get_training_overview`). INT-1b has since delivered the transport, the second tool and the resource
(see below). The baseline context package (INT-2) and the model paths (INT-4/INT-5) followed.
Implementation detail is in the backend
[INTELLIGENCE-IMPLEMENTATION.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/INTELLIGENCE-IMPLEMENTATION.md).

**Scope (as originally written).** The envelope, error taxonomy, capability registry, context builder skeleton, MCP server
with two tools (`get_training_overview`, `get_session_details`) and one resource
(`strength://athlete/profile`), bearer auth, limits, logging, config, systemd unit, and the test
harness (in-memory + HTTP + legacy/modern eras). No model. No new REST route.

**Dependencies.** Owner approval of section 12 decisions; `mcp>=2,<3` allowed as an optional dependency.

**Files/repos.** Backend: `pyproject.toml` (optional extra + console script),
`strength_coach/intelligence/{__init__,envelope,errors,registry,context}.py`,
`strength_coach/intelligence/capabilities/{__init__,overview,session}.py`,
`strength_coach/intelligence/mcp/{__init__,app,auth,tools,resources,run}.py`,
`config/intelligence.v1.yaml`, `deploy/` unit, `tests/intelligence/`. Portfolio: contract status
line only.

**Acceptance.** Server starts as a separate process with the UI stopped; `tools/list` is
deterministic and lists exactly two read-only tools and one resource; both eras connect; every result
validates against the envelope and the tool `outputSchema`; 401 without a token; token absent from
logs; the process opens SQLite read-only and a write attempt fails; `pytest` and `ruff` clean; no
`web` import.

**Tests.** As rows 1–9 of section 10 for the two capabilities plus protocol/auth/deployment.

**Security.** Tailnet/loopback only; hashed tokens; no payload logging; read-only DB; limits live.

**Exclusions.** No progression/VBT/adherence/review tools; no model; no REST route; no schema change;
no change to any existing endpoint.

### INT-1b — MCP transport and the second tool

**Implementation status (2026-11-14): implemented and tested.** Delivered: the `intelligence`
optional extra and `strength-intelligence-mcp`/`strength-coach intelligence serve` entry points;
the Streamable HTTP server on revision 2026-07-28 with legacy clients served by the same app;
dedicated per-client tokens (hash-only, CLI create/list/rotate/revoke) with a bearer guard, Host
allowlist, body cap, rate and concurrency limits; strict tool-argument checking (unknown keys and
type coercion rejected before the SDK); `get_session_details`; the `strength://athlete/profile`
resource; read-only SQLite (`mode=ro`); and a synthetic performance baseline (development machine,
plus the deployment host on 2026-11-14: p50 3.10 s / p95 3.17 s at 377 sessions). Those host
figures exceed the one-second threshold, so ADR-INT-010 adopted a latency-aware budget and option B,
and the transport is enabled there with the full ten-tool catalogue; the measured p95 values are
guidance, not a guarantee, and T-3 remains the optimisation track. No REST route, model provider or
write tool was added.

**Audit remediation (2026-11-14):** token revoke/rotate now take effect without a restart (the
store is re-read per request, atomic writes, fail closed on a malformed file); every tool and
resource emits one structured metadata-only audit record; the MCP adapter enforces a configurable
20-second response deadline and 1 MiB serialized-result cap with typed errors rather than a
truncated envelope; a dedicated systemd unit and deployment guide exist (installed on the ODROID
2026-11-15); and a live HTTP integration test drives both tools and the resource through the
official client. Implementation detail, operation instructions, schemas and the
baseline are in the backend
[INTELLIGENCE-IMPLEMENTATION.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/INTELLIGENCE-IMPLEMENTATION.md).
The contract's profile-resource payload was corrected to the fields that actually exist: goal and
priority columns are retired (DEC-STATE-02), and injury constraints are withheld and only counted.

**Scope (as written).** The `mcp>=2,<3` optional dependency and console script; `strength_coach/intelligence/mcp/`
(Streamable HTTP endpoint, bearer guard, deterministic tool registry, tool/resource schemas,
`json_response`, limits, deployment unit); `get_session_details` (worker `workout_id` path, reusing
`workout.summary()` and its real evidence array); the `strength://athlete/profile` resource; legacy
(2025-11-25) and modern (2026-07-28) protocol tests; the in-process versus MCP parity test.

**Dependencies.** INT-1 (done). No model, no new REST route.

**Acceptance.** The server starts as a separate process with the UI stopped; `tools/list` is
deterministic and lists exactly two read-only tools and one resource; both protocol eras connect;
every result validates against the envelope and the tool `outputSchema`; 401 without a token; token
absent from logs; the process opens SQLite read-only and a write attempt fails; `pytest` and `ruff`
clean; no `web` import.

**Tests.** Protocol compatibility, tool schemas, invocation, auth and isolation, invalid arguments,
missing data, error mapping, parity, and the deployment/read-only checks.

**Security.** Tailnet/loopback only; hashed client tokens (ADR-INT-004) or the existing device token
for the first acceptance; no payload logging; read-only DB; limits live.

**Exclusions.** No model, no REST route, no schema change, no mutation tool, no INT-2 capability.

### INT-2 — Deterministic capabilities and the full read-only catalogue

**Implementation status (2026-11-14): delivered.** Nine read-only capabilities and three resources
are registered and exposed over MCP: the INT-1 tools plus `get_exercise_progression`,
`get_readiness_history`, `get_adherence_analysis`, `get_prescription`, `get_vbt_analysis`,
`get_programme_block_summary` and `compare_training_periods`. Every value comes from its owning
service; the only arithmetic added is the difference between two owner outputs in
`compare_training_periods`. Evidence arrays remain empty where owners do not emit evidence.
`get_weekly_review_data` is not a separate capability: the weekly review package is INT-3, which
composes these (closed 2026-11-15). MCP tool schemas spell date bounds `start`/`end` (`from` is a Python keyword); the
capability API keeps `from`/`to`. Implementation detail, limits and the development-machine timings
are in the backend
[INTELLIGENCE-IMPLEMENTATION.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/INTELLIGENCE-IMPLEMENTATION.md).

**Scope (as written).** `get_exercise_progression`, `get_readiness_history`, `get_adherence_analysis`,
`get_vbt_analysis`, `get_prescription`, `compare_training_periods`,
`get_programme_block_summary`, `get_weekly_review_data`; two more resources
(`strength://programme/current`, `strength://overview/current`); the parity test between in-process
and MCP clients.

**Dependencies.** INT-1. No model.

**Files/repos.** `intelligence/capabilities/*`, `intelligence/context.py` (baseline package used by
overview and review), `tests/intelligence/`. Backend docs: `docs/API.md` gets the MCP surface under
a new section (it is a backend implementation doc); `ROADMAP.md` §4.24 pointer.

**Acceptance.** Every catalogue tool returns an envelope whose fact blocks name their owning module;
each has at least one golden test; ranges and limits enforced; no metric constant in
`intelligence/`; in-process and MCP envelopes are byte-identical; p95 latency recorded for the three
heaviest tools (informational, not a gate).

**Tests.** Ownership guard, golden facts, validation, missing data, parity, protocol.

**Security.** Same as INT-1 plus a per-tool result-size cap and a query-time limit.

**Exclusions.** No narration, no weekly review UI, no REST route, no writes.

### INT-3 — Weekly Training Review (deterministic) and the iOS read surface

**Implementation status: closed 2026-11-15.** `intelligence/reports/weekly_review.py`, the
`get_weekly_review` tool, `GET /api/ios/v1/intelligence/weekly-review`, the `StrengthCore`
envelope model and REST client, the SwiftUI review screen and the Week navigation are implemented
and tested. Acceptance evidence: the completed week matches the golden fixture; an empty week is
`no_data` with the expected inputs; an imported-only week keeps its quality flags; the screen works
with no model and no route beyond the existing REST call; `DEC-AFC-03` holds. The screen shows
status, coverage and limitations, renders no values client-side, and works with no model. No narrative, model or write path was added. The REST entrypoint opens SQLite
read-only; raw readiness values are local-only over MCP (score only unless a deployment opts in),
and the weekly review flags a partial current week explicitly. ADR-INT-014 proposes per-token
scopes as the long-term model. The branch was merged into `development` on 2026-11-15.

**Scope.** `intelligence/reports/weekly_review.py` composing the sections in §8.2;
`get_weekly_review` tool; a new read-only iOS route
`GET /api/ios/v1/intelligence/weekly-review?week_end=YYYY-MM-DD`; `StrengthCore` envelope models and
REST adapter; a SwiftUI review screen with deterministic sections, coverage and limitations; the
Week navigation from Progress.

**Dependencies.** INT-2. **This is the first phase that adds a REST route** (the minimum necessary API
change; it is additive and authenticated).

**Files/repos.** Backend: `intelligence/reports/weekly_review.py`, `intelligence/api.py`,
`web/server.py` route + tests, `docs/API.md`. iOS: `StrengthCore/.../Intelligence/*`,
`StrengthApp/Features/Intelligence/WeeklyReviewView.swift`, `StrengthApp/Core/AppModel.swift`
(load + state), tests. Portfolio: contract fixture, plan status.

**Acceptance.** A completed week renders with sections that match the golden fixture; an empty week
renders "no data" rather than zeros; a week with only imported sessions renders with explicit
quality flags; the screen is useful with no model and no network beyond the existing REST call;
`DEC-AFC-03` (client calculates nothing) holds.

**Tests.** Golden review fixture; Monday/week-boundary; empty/partial; iOS decode and snapshot; no
Swift arithmetic.

**Security.** Existing device bearer auth; no new data classes leave the server.

**Exclusions.** No narrative, no chat, no Siri, no write, no change to Progress/History calculations.

### INT-4 — Apple Foundation Models narrative (on device)

**Implementation status (2026-11-15): delivered.** The on-device
narrative works on the weekly review and the Progress overview: default-off consent, availability
and detail settings, a compact facts projection, a `@Generable` output, a grounding validator that
uses a structured number allow-list, deterministic fallback and no persistence or network. The five
Foundation Models `Tool` adapters from contract §10 are implemented and tested as an adapter
surface, but not registered in the session: their schemas consumed most of the 8,192-token window
and overflowed on the device at the Detailed preset. The budget trims at 1,200 tokens and retries at
600 on overflow before falling back. The owner confirmed the narrative on 2026-11-15 and found two
issues (that overflow, and an over-strict grounding check that rejected percentages, thousands
separators and the digit in `e1RM`); both are fixed. The device run passed and no UI test is
required by owner decision. Conditional tool registration remains a tuning item.
**Scope.** Feature flag (default off), availability UI, consent copy, five `Tool` implementations,
`@Generable` narrative, token budgeting, overflow recovery, grounding validator, cache-free
regeneration, and the deterministic fallback.

**Dependencies.** INT-3; a physical Apple Intelligence device; no backend change.

**Files/repos.** iOS only: `StrengthApp/Intelligence/*`, `StrengthApp/Features/Intelligence/*`,
`StrengthAppTests/Intelligence*`.

**Acceptance.** On an eligible device, enabling the flag produces a narrative whose every number
exists in the facts; disabling it or running on an ineligible device shows the deterministic review
with an accurate reason; a forced context overflow degrades gracefully; no network call from the
model path; no transcript persists; the app's existing flows are unchanged.

**Tests.** Unit tests with a stub generator (the model itself is not unit-tested); validator
adversarial cases; availability matrix; token-budget estimator; UI test on a simulator with a stub.

**Security.** On-device only; explicit opt-in; no health fields in the projection by default;
injection fixtures.

**Exclusions.** No PCC, no cloud fallback, no chat, no Siri, no write.

### INT-4b — On-device training chat (delivered 2026-11-15)

**Status.** **Complete (2026-11-15).** The app has a dedicated Chat screen reached from Progress, a
separate default-off consent toggle, suggested prompts, non-streaming answers, a sources line per
reply and a session-only transcript (leaving the screen clears it). The five tools are registered
for chat with a 5-to-3 fallback on a context overflow; the answer is checked against the envelopes
the tools actually returned: an ungrounded digit gets one corrective retry and, if it survives, a
visible "Unverified numbers" warning. Session details resolve the most recently completed session
when the model has no id. The manual device
matrix passed: weekly review, overview, progression, session details without an id, readiness,
refusal of plan/medical prompts, and transcript clearing. No UI test by owner decision.

**Scope.** A multi-turn chat in the app over the on-device Foundation Models, using the read-only
capability tools and the REST envelopes. The athlete can ask follow-ups about the current week,
the overview, a lift, a session or readiness. The model chooses which facts to fetch; the client
never computes a metric. Suggested questions, a compact context budget and per-answer grounding are
part of the work. The transcript is session-only by default: leaving the screen or force-quitting
the app loses it.

**Dependencies.** INT-4; a physical Apple Intelligence device; no backend change.

**Acceptance.**
- Every digit in an answer is checked against the fetched facts. An ungrounded digit triggers one
  corrective retry; if it survives, the answer is shown with an "Unverified numbers" warning, never
  silently accepted. Number words are prose and are not treated as claims.
- Questions outside the facts (medical advice, plan changes, other athletes) are refused plainly.
- Multi-turn context stays within the model window: tool results are trimmed, old turns are
  trimmed to the most recent ones, and a context overflow is a clear message, never a raw token
  count.
- The five tools are registered only when the context budget allows; the single-shot explanation
  path is unchanged and still does not register them.
- No writes, no prescription, no medical advice, no network from the model path, and no persisted
  transcript by default. Raw readiness may be used on-device only if the app already has it.
- Injection fixtures: instruction-like text inside facts cannot change the answer or widen the
  grounded-number set.

**Tests.** Stub tool provider and generator; grounded and ungrounded answers; tool selection and
result trimming; context-budget trimming; refusal cases; injection fixture. No UI test is required
by the owner.

**Exclusions.** No Siri AI Developer Preview, no PCC/cloud fallback, no server narration, no write,
no new analytical capability, and no INT-5 work.

### INT-4c — User-selectable model: on-device or Private Cloud (parked 2026-11-15)

**Status.** **Parked 2026-11-15; not scheduled.** PCC requires a paid Apple Developer Program
membership plus the managed entitlement `com.apple.developer.private-cloud-compute` and Apple's
eligibility approval. Until that access exists the model is unavailable, so this phase does not
ship and no picker is added. Revisit only if the owner obtains access; the scope below is retained
as the future definition.

**Goal.** One app-wide setting: **On-device (default)** or **Private Cloud Compute**, applied to the
weekly/overview explanations and Chat. Each surface states which model produced the answer.

**Privacy — deliberately simple.** One picker plus one line: “Private Cloud sends your question and
training facts to Apple's private cloud; On-device keeps them on this iPhone.” No per-request
consent modal, no context preview, no audit log, no telemetry. The transcript stays session-only.
The owner waived the earlier context-preview requirement.

**Prerequisite spike (must pass before UI work).** Apply for access and add the entitlement to the
app profile, then on the iPhone verify:
- `PrivateCloudComputeLanguageModel().isAvailable`;
- `.capabilities` contains `.toolCalling` and `.guidedGeneration`;
- `contextSize` (expected 32K);
- `quotaUsage.status`;
- one chat turn and one explanation.
If any check fails, stop and report; do not ship a partial picker.

**Implementation.**
- `NarrativeModelChoice` (`onDevice`, `privateCloud`) persisted in UserDefaults; default on-device.
- A small session factory switches on the choice; both generators take it. Tools, budgets,
  grounding, soft verification and session-only transcripts are unchanged.
- Settings picker with the one-line disclosure. The PCC option appears only when entitled,
  available and capable; otherwise the surface stays on-device with a clear reason.
- Errors: `.networkFailure`, `.quotaLimitReached` and `.serviceUnavailable` map to short
  messages; quota includes the reset date when Apple provides it; no retry loop and **no silent
  fallback**.
- Chat requires `.toolCalling`; explanations require `.guidedGeneration`. If either is missing, that
  surface stays on-device with a clear line.

**Acceptance.**
- Default remains on-device; changing the picker persists and both surfaces use it.
- PCC is offered only when entitled, available and capable; otherwise a clear reason, no dead
  control.
- No silent fallback; a PCC failure stops with a message and leaves the deterministic review intact.
- Grounding/soft verification, sources, refusal behaviour and session-only transcript are identical.
- Quota, network and service errors are differentiated.
- Device matrix on both models: weekly explanation, overview explanation, chat with the five tools,
  refusal, transcript clearing.

**Tests.** Model-choice persistence and factory selection; availability/error mapping; a stub
generator confirms both surfaces pass the choice through. No UI tests (owner). PCC itself is
device-only.

**Out of scope.** No backend/MCP change, no Siri, no streaming, no per-conversation model switch, no
cost dashboard, no cloud fallback.

**Estimate.** Small once access exists (2–3 focused sessions); entitlement and eligibility are the
schedule risk.

### INT-4d — Chat with an external model via API key (DeepSeek; delivered 2026-11-15)

**Status.** **Complete (2026-11-15); manual device acceptance passed.** Direct from the iPhone; no
backend change. Chat only.

**Scope.** **Chat only.** The weekly and overview explanations remain on-device and never use the
external model. A Settings **Chat model** choice offers On-device (default) or DeepSeek. When
DeepSeek is selected, the app calls `https://api.deepseek.com` with model
`deepseek-chat` using an API key stored in the Keychain. The conversation, facts and tool
results are sent directly from the iPhone to DeepSeek. The adapter uses the OpenAI-compatible
`/chat/completions` API with a tool loop over the same five read-only capabilities: at most four
tool rounds, non-streaming, session-only transcript, sources line, and the existing soft number
verification.

**Privacy and key handling.** One-line disclosure: “DeepSeek receives your question and training
facts; the key is stored in this iPhone's Keychain.” No server proxy, no key in UserDefaults, logs,
the repository or iCloud Keychain; device-only accessibility. **No silent fallback** to on-device —
that would change the data boundary. An external failure stops with a message and the user can
switch back. On-device remains the default.

**Settings.** Secure key field with Save/Test/Remove. A minimal validation request proves the key;
401 shows “invalid key”, and the key is never echoed. Model defaults to `deepseek-chat`; a
different model id is allowed only if it supports tool calls, otherwise chat refuses with a clear
message.

**Errors.** 401 invalid key, 429 rate limit, 5xx/transport unavailable, malformed response, tool
execution failure. Short messages, no retry loop, no fallback.

**Acceptance.**
- On-device stays the default; the external model applies to Chat only; explanations are unchanged.
- The key is stored in the Keychain, never logged or persisted elsewhere; Remove works.
- Chat uses the five tools and returns grounded answers with sources; an ungrounded digit gets the
  existing retry and “Unverified numbers” warning.
- No request is made without a key; invalid keys fail clearly.
- The transcript is session-only; prompts, answers and keys are not persisted.
- Device test with the owner's key; simulator tests use a mocked HTTP transport.

**Tests.** Mocked HTTP: request shape, bearer header, tool-call round trip, final answer, 401/429/500,
malformed JSON, four-round cap and history budget. Keychain wrapper test with a test service. No UI
tests (owner).

**Out of scope.** Explanations and the weekly review, backend proxy, PCC, streaming, generic
providers, cost dashboard, cloud fallback, any write.

**Estimate.** Medium: HTTP client, tool loop and key UX; no server work.

**Implementation note.** The client and tool loop are in `DeepSeekAPI.swift` and
`DeepSeekChatGenerator.swift`; the Keychain store and Chat model picker are iOS app code. The
simulator tests cover the HTTP shape, bearer header, tool round-trip, 401/429, malformed JSON, the
retry/warning path and the missing-key state (6 DeepSeek tests; 38 chat-related tests in total).

### INT-4e — Plan-aware chat and suggestions (delivered 2026-11-15)

**Status.** **Complete (2026-11-15).** Backend routes are deployed; the owner confirmed both
providers on the iPhone. A deterministic prescription card, built from the fetched envelope, shows the exact date,
session type and every item, so model prose abbreviation or a confused date no longer hides the
prescription.

**Scope.** A default-off **“Include plan and prescription data”** toggle in Chat adds three
read-only tools: `prescription`, `programme_summary` and `adherence`, alongside the five existing
ones. This applies to on-device and DeepSeek chat. The backend exposes the same capabilities over
three additive iOS routes (`/intelligence/prescription`, `/programme-summary`, `/adherence`).

- Prescription accepts a date (`YYYY-MM-DD`) or a prescription id; empty asks for the current
  prescription.
- Programme summary accepts a date; block weeks default to 4.
- Adherence accepts weeks or a date; default 12 weeks.

**Suggestions.** The model may suggest changes, including medical considerations, with no refusal
guard. Suggestions are a separate structured field, rendered in a labelled block: “Suggestion — not
applied. Not medical advice.” Numeric suggestions are proposals and are exempt from the data-claim
grounding. The factual answer keeps the existing soft verification (digits, one retry, then the
unverified warning). No suggestion is applied; the deterministic engine remains authoritative.

**On-device capacity.** The physical-device probe reported `contextSize=8,192`, tool calling and
guided generation true. The base five, plus prescription, plus all three plan tools passed; eight
tools with four history messages and 60 fact lines also passed. Plan tools use compact projections
so a multi-item prescription or a 12-week adherence payload is not truncated.

**Acceptance.**
- Flag off: chat behaves exactly as before.
- Flag on: chat explains the current or dated prescription, programme state and adherence.
- Suggestions render separately, are clearly proposals, and are never applied.
- Factual digits remain grounded; suggestion digits do not trigger the unverified warning.
- Both providers inject plan facts only on success or partial success; total failure stops with a deterministic message.
- Projections preserve no_data, missing reasons, limitations and truncation, and render absent numbers as n/a.
- A context overflow retries with empty history.
- Prescription answers use a larger output budget so every item can be listed.
- Each answer offers a “Show raw data” disclosure with the exact facts used.
- Tests: plan-tool registration, tool execution, structured suggestion parsing and message carrying,
  grounding separation.

**Tests.** 54 chat-related tests pass, including typed plan failures, no-data projections, natural-
language plan intent, plan-fact injection, today/yesterday resolution, the plan card and raw-output
inspection. The backend route tests pass (12).

**Open.** None blocking. Optional follow-up: shorten the model prose when a prescription card is
shown.

### INT-5 — Backend LLM narrative and multi-tool integration

**Implementation status (2026-11-15): delivered.** The narrate CLI and web view explain any
registered capability through the existing Null/OpenAI-compatible provider, validate the JSON
against the envelope facts with advisory number warnings, and record a run trace. Daily token
budget, a ten-capability evaluation harness, MCP parity and Phase 1b selector retirement are done.
Multi-tool orchestration is deferred beyond INT-5 by owner decision.

**Scope.** `intelligence/model/` orchestration, `NarrativeProvider` with `NullProvider` and the
existing OpenAI-compatible adapter, `IntelligenceClient` (`InProcessClient` / `MCPClient`), JSON
output contract and validator, `run`/`run_event` trace, cost budget, CLI command
(`strength-coach intelligence narrate --capability NAME --payload JSON [--json]`), and the
evaluation harness. No new public endpoint.

**Dependencies.** INT-3; INT-2 parity test; Phase 1b selector retirement recommended first
(`DEC-LLM-14`) so there is exactly one model surface.

**Files/repos.** Backend: `intelligence/model/*`, `cli.py` command, `tests/intelligence/`,
`tools/intelligence_eval.py`; `docs/LLM-INTEGRATION-PLAN.md` pointer; `ROADMAP.md` status.

**Acceptance.** With provider null, the command reports unavailable and exits non-zero; with a
configured provider, the narrative is grounded in the fact pack; the validator rejects invented
numbers and unknown evidence ids; the trace records versions and tokens; a per-day budget stops
calls; no output is stored as a training artifact.

**Tests.** Grounding, injection, provider failure, timeout, malformed JSON, budget, trace fields,
in-process/MCP parity.

**Security.** Field-level outbound inventory completed before enablement; provider disclosure in the
CLI/settings; keys never logged.

**Exclusions.** No autonomous multi-step agent loop, no write, no new endpoint, no prompt stored in
the repository with personal data.

### INT-6 — Conversational Training Intelligence (closed 2026-11-15)

**Implementation status (2026-11-15): closed.** The Programme Intelligence Chat view posts up to 20
session-only turns to `POST /api/intelligence/chat`; the server supplies a fresh six-capability fact
dossier, with advisory number warnings, source capabilities, daily budget and no write. The
recent-ten-message window, 18k dossier cap, separate suggestions block and four-case multi-turn
matrix are delivered. **Model tool calling is deferred/closed**: the provider stalled on it and the
deterministic dossier covers the six core capabilities plus latest duration. Streaming is not planned. Chat tokens are
persisted in `run.llm_tokens` and count against the daily budget.

**Status.** The iOS multi-turn surface is delivered as INT-4b (2026-11-15); the model choice is
INT-4c. This phase covered the server/web conversation only.

**Scope (historical).** A web chat panel over the read-only capabilities, with an explicit context
budget, turn cap, and a hard rule that answers use only facts in the supplied snapshot.

**Dependencies.** INT-5. The iOS surface is INT-4b/4c. Transcript retention is session-only; no
server transcript is stored.

**Files/repos.** Optional web panel; server conversation orchestration. The iOS `ChatView` is no
longer part of this phase.

**Acceptance.** Answers cite fact keys; asking for a prescription change produces a refusal and a
pointer to the existing prescription flow; context stays under budget across 10 turns; no transcript
is uploaded; the surface can be disabled.

**Security.** Prompt injection through prior turns; no tool-result text is treated as instruction;
retention decision recorded.

**Exclusions.** No memory across sessions, no proactive messages, no write.

### INT-7 — Siri, App Intents and Shortcuts (stable APIs only)

**Scope.** Three read-only intents (`TrainingOverviewIntent`, `ExerciseProgressionIntent`,
`WeeklyReviewIntent`) with `AppShortcutsProvider` phrases, entity/parameter types for the exercise
and week, and dialog + snippet presentation. Optionally a fourth intent that opens the existing
review screen.

**Intent set and defaults (2026-11-15).** `TrainingOverviewIntent` also answers the last-workout
question ("how long was my previous workout"); a dedicated `LastWorkoutIntent` is added only if the
overview facts turn out not to carry a per-session duration. Entities indexed for Spotlight are
exercises only; completed sessions are not indexed, so history stays out of system search. Both are
defaults pending an owner override.

**Dependencies.** INT-3 (data), INT-4 optional. Independent of INT-5/6.

**Files/repos.** A new shared package product **`StrengthIntents`** (intent types, entities and the
envelope→entity adapter; no SwiftUI), linked by the **phone target** in INT-7. `AppShortcuts.swift`
and the snippet views stay in the app; tests sit with the module.

**Acceptance.** Each intent works from Shortcuts and from Siri's existing App Intents support; no
read-only intent can write; unauthenticated/offline states produce a clear dialog; a read-only intent
does not start a workout (start and finish live in INT-7b); the §7.6 readiness items 1–2 hold and are
unit-tested (intent, parameter and entity-property metadata, plus Spotlight indexing).

**Tests.** Intent unit tests with a stub adapter; shortcut phrase validation; a manual device check
recorded in `DEVICE-ACCEPTANCE.md`.

**Security.** Dialogs may speak and show any number the envelope carries — the owner removed the
"no health data in dialogs" rule on 2026-11-15 — but a dialog adds no interpretation beyond those
facts, and the snippet shows the same values. No onscreen entity donation in MVP; no preview API symbol
before the adoption pass.

**Forward compatibility (2026-11-15).** INT-7 is the phase that decides how cheap a future Siri AI
adoption is. Build it to §7.6: complete intent, parameter and entity-property metadata, `IndexedEntity`
Spotlight indexing, snippet views that a `CardSnippet` can host, and `perform()` with no side effects.
The preview requirements — `@AppIntent(.tool)`, a `Skills.skillsbundle` of `SKILL.md` files,
`CardSnippet`, `SiriEvaluations` — are added in one pass once iOS 27.3 is installed on the owner's
device: raise the deployment target to 27.3, or keep 27.0 and wrap the additions in
`@available(iOS 27.3, *)`. No compile gate, feature flag or dual code path is built now. Adoption
still re-runs the `ADR-INT-011` gate (terms, fee/quota, device spike).

**Watch rollout (2026-11-15, option B).** The intent code is shared from day one, but the watch target
is **not** linked in INT-7: `StrengthIntents` reaches `StrengthWatch` in 7b-3, together with the
Action-button intents, so both get a single watch acceptance run. The server needs no change — the
intelligence routes authenticate any device principal and carry no watch gate — and the watch surface
is dialog-only (no screens; history and progress stay on the phone).

**Exclusions.** Siri AI Developer Preview, app skills, onscreen awareness, cross-app actions,
conversational Siri, and any fee-bearing Apple-hosted path. The readiness in §7.6 is in scope; the
preview itself is not. Revisit only after it ships to customers, Apple publishes its terms, and a new
ADR approves it.

**Implementation status (2026-11-15): delivered except the device checks** on iOS branch
`feat/int-7-intents`. Shipped in two commits: the shared `StrengthIntents` package product (provider
protocol and registry, `ExerciseEntity` with `IndexedEntity`, four digests, formatters) and the four
intents (`TrainingOverviewIntent`, `LastWorkoutIntent`, `ExerciseProgressionIntent`,
`WeeklyReviewIntent`) declared in the app target as thin shells. Each intent returns a snippet card
and a dialog; the cards are pure value-in SwiftUI views, so a `CardSnippet` can host them after the
27.3 adoption pass. `scripts/check-shortcut-phrases.sh` runs from `scripts/ci.sh` and fails a phrase
that lacks the app-name token. Eleven unit tests pass (digests, entity query, snippet rendering,
metadata presence). Verified: App Intents declared in a package product still emit metadata
(`StrengthIntents.appintents` merges into `StrengthApp.app`), phone and watch builds are clean, and
the package stays SwiftUI-free for the watch in 7b-3. The average-duration intent agreed on
2026-11-15 is delivered too: `AverageSessionDurationIntent` takes `weeks` (1–52, default 4), passes it
to `overview(windowWeeks:)`, and speaks the `attendance.duration` aggregate with its sample size and
the measured subset. Days are not supported: the capability's only window parameter is weeks.
Two literal phrases cover the fixed windows a phrase can match ("... over the last 12 weeks"), because
an App Shortcut phrase cannot carry a free-form number.

**Closed 2026-11-15**, owner-confirmed on the physical iPhone (Release build at `0697889`): every
read-only phrase routes to the app and answers, and the snippets render. Two items are recorded as
deferred rather than passed in `StrengthApp/DEVICE-ACCEPTANCE.md`: **Spotlight** does not surface the
donated exercises on the owner's device (accepted deferral), and the offline/unpaired dialog was not
exercised. An arbitrary "last N weeks" phrase still needs an enum plus
`AppShortcutParameterPresentation`, and a Spotlight tap still needs `URLRepresentableEntity`.

### INT-7b — Workout lifecycle surfaces: Action button, HomeKit scenes and Shortcuts (owner-requested 2026-11-15)

**Scope.** A *local* surface layer around the existing session lifecycle — Action button, HomeKit
scenes and user Shortcuts — on iPhone and watch. It is not an intelligence capability and adds no
training policy. Delivered as three slices, cheapest first.

**Boundary.** These intents are entry points: they **call** the existing start and finish operations and
never redefine them. Session semantics — what counts as started, when a session is finished, sRPE
validation, offline journaling and replay, device ownership and abandonment — stay in the session
engine and the server (`ADR-INT-018`).

**Channels.**

1. `StartWorkoutIntent` in the watch app, so an Apple Watch Ultra Action button
   (**Settings > Action button > Workout > StrengthApp**) starts the workout.
2. An end-workout `AppIntent` **donated as the Action button's next action** while a session is
   active, so a second press ends it. Apple defines no `EndWorkoutIntent` protocol; donating an intent
   sets the next action, only one exists at a time, and re-donating replaces it.
3. Two user-selected **HomeKit scenes** — one on start, one on end — executed by whichever device owns
   the session (phone or watch) through `HMHomeManager` and
   `HMHome.executeActionSet(_:completionHandler:)`.
4. Two user-selected **Shortcuts**, one on start and one on end, run by the phone through the
   documented `shortcuts://run-shortcut` URL. **Phone-only:** `UIApplication` does not exist on
   watchOS and Apple documents no watch-side equivalent, so a watch-owned session has no shortcut
   channel.

**Dependencies.** The Phase 6 watch session engine (start, finish, HealthKit authorization, exactly one
HealthKit save) and the phone's session path. Independent of INT-3, INT-4 and INT-7's read-only intents.

**Files/repos.** iOS/watchOS: `StrengthApp/Intents/`, `StrengthWatch/`, `StrengthApp/Home/`
(scene picker and executor), tests. The Action-button intents are compiled **into the watch app**:
Apple forbids implementing them in an `AppIntentsExtension`.

**Facts (2026-11-15).**

- `StartWorkoutIntent` is a protocol (watchOS 9+, iOS 16+): `title`, `suggestedWorkouts`,
  `workoutStyle` as a `@Parameter` over an `AppEnum`/`AppEntity`, `displayRepresentation` and
  `perform()`; `invalidateSuggestedWorkouts()` refreshes the list. The system allows **30 seconds** to
  start an `HKWorkoutSession` and return success.
- `PauseWorkoutIntent`/`ResumeWorkoutIntent` are the Action + Side button pair; they need a pausable
  session engine, which strength training does not have — **excluded** (decided 2026-11-15).
- `HMHome.executeActionSet` is iOS 8+/watchOS 2+. HomeKit needs the `com.apple.developer.homekit`
  entitlement plus `NSHomeKitUsageDescription` and the user's authorisation. Scenes are `HMActionSet`
  values read from the user's homes; the app never invents one.
- HomeKit's own automations trigger on accessory, time and people events, not on a third-party app
  event, which is why the app executes the scene itself.
- `shortcuts://run-shortcut?name=<name>&input=text&text=<text>` is the only public way to run a
  shortcut from another app; `UIApplication.open` hands it to the system and **foregrounds Shortcuts**.
  No API executes a shortcut programmatically, and `RunSystemShortcutIntent` (iOS 27) is widget-only —
  Apple: it "doesn't provide functionality in other contexts". Success from `open` means the URL was
  accepted, **not** that the shortcut ran: there is no completion signal and no error to report.

**Slices.** Three reviewable slices, in this order. The shared facts above apply to all of them.

**Slice 7b-1 — Automation executor and user Shortcuts (phone).** One `WorkoutAutomation` service that
observes the phone's session start and end transitions, holds the per-event choice (at most one
Shortcut), fires the URL after the transition is committed, dedupes by session id plus event, and
isolates failure. No HomeKit or watch work.

*Owner decisions 2026-11-15.* Both events are wanted (start **and** end). There is **no separate
on/off switch**: a filled-in shortcut name means the channel is on, an empty field means it is off.
**Nothing is passed to the shortcut** — no session data, no duration, no text; the shortcut runs with
no input at all.

*Acceptance.* A configured shortcut fires at most once per event; an empty field does nothing; a
missing or renamed shortcut, and a refused URL, are invisible to the session; no training data is
passed; the service is unit-tested against a URL-open stub.

**Closed 2026-11-15**, owner-confirmed on the physical iPhone. `WorkoutAutomation` holds the
per-event name in `UserDefaults`, dedupes by `sessionID + event` with a bounded fired log, builds
`shortcuts://run-shortcut?name=…` with no input, and swallows every failure. It is called after the
phone commits a start, a finish (online or queued offline) and an abandonment; a refused URL clears the
dedupe entry so a later transition can retry. Settings gained a "Workout automation" section with one
field per event and two test buttons. Six unit tests cover fire-once, separate channels, empty = off,
per-session firing, refusal retry and the URL shape. The physical checks are listed in
`StrengthApp/DEVICE-ACCEPTANCE.md`; the owner confirmed all six physical checks on 2026-11-15, so
the slice is closed.

*Why first.* It is the cheapest real channel and it proves the trigger, ordering, dedupe and failure
isolation that 7b-2 and 7b-3 reuse.

**Slice 7b-2 — HomeKit scenes (phone and watch).** The `com.apple.developer.homekit` entitlement and
`NSHomeKitUsageDescription`, `HMHomeManager` authorisation, a picker limited to the user's homes, and
execution through `executeActionSet` by whichever device owns the session.

*Owner decisions 2026-11-15.* The HomeKit capability is confirmed enableable on **both** App IDs — the iOS app and
the watch app. The watch
does **not** get its own scene picker: it takes the selection **from the phone over WatchConnectivity**
(option b), keeping one place to choose scenes.

*Implementation notes.* Both App IDs need the capability — the iOS app and the watch app — with the
usage string in both Info.plists. The phone pushes `{homeID, startSceneID, endSceneID}` on change and
on watch activation; the watch uses the last-known mapping, and if it has none it runs no scene rather
than guessing. Scene identifiers are `HMHome.uniqueIdentifier` + `HMActionSet.uniqueIdentifier`, kept on
the device and never sent to the server. Ordering is scene first, then the Shortcut (which foregrounds
Shortcuts). A missing home, a deleted scene or denied authorisation skips silently and is logged; the
workout is never blocked.

*Acceptance.* The start scene runs once on the owning device and the end scene once on finish or
abandonment; a HomeKit failure (denied, home removed, scene missing) never blocks the record; scenes
are off by default; only `HMActionSet` values from the user's homes are used; no scene, home or
accessory identifier leaves the device.

*Depends on.* 7b-1's executor interface.

**Implementation status (2026-11-15): phone half delivered.** The HomeKit entitlement and
`NSHomeKitUsageDescription` are in the app and the watch targets; `HomeKitSceneRunner` in
`StrengthCore` lists scenes from the user's homes and executes one through `executeActionSet`, waiting
for the first homes update and failing silently. `WorkoutAutomation` now runs channels in order — scene
first, then the Shortcut — with a separate fired key per channel, so a refused scene does not consume
the Shortcut's turn. Settings gained "Home scenes": one picker per event (`SceneSelection` as JSON in
`UserDefaults`), a test button each, and a reload button. Ten unit tests cover ordering, once-per-event,
retry and the selection codec.
**Watch half delivered 2026-11-15.** The mapping rides in `WatchCredentialContext`
(`startScene`/`endScene` as encoded `SceneSelection`), so the existing credential channel carries it
without a second message type; the phone re-sends the context when a scene changes. The watch stores it
in `WatchSceneAutomation` and runs the scene from `WatchExecutionController` after a successful start,
after a finish that recorded a finish intent, and after a discard — once per session and event, with the
same last-known fallback and silent-skip rules. Phone and watch builds are green and 387 tests pass.
**Closed 2026-11-15**, owner-confirmed on the physical iPhone and Watch; the checks are recorded in
`StrengthApp/DEVICE-ACCEPTANCE.md`.

**Slice 7b-3 — Action button and watch Siri (watch).** `StartWorkoutIntent` compiled into the watch app
with `suggestedWorkouts` and the 30-second start budget, the end intent donated as the button's next
action and re-donated as the session state changes, and `StrengthIntents` linked into the watch target
so watch Siri answers the three read-only questions from INT-7 (dialog-only, no screens).

*Acceptance.* A first press starts the configured workout, a second press during the session ends it,
the donation reflects finish and abandonment, watch Siri answers the three read-only questions, and the
physical-watch checks are recorded in `DEVICE-ACCEPTANCE.md`. The intents are compiled into the watch
app, never an `AppIntentsExtension`.

*Independence.* Does not need 7b-1 or 7b-2; it can run in parallel.

**Tests.** Intent and donation-state unit tests; executor, dedupe and scene-selection tests with stubs;
a device matrix on phone-only, watch-only and both.

**Security.** Scenes can unlock doors, so: explicit opt-in, no execution without a confirmed session
transition, no model- or Siri-supplied scene name, no scene execution from a stale donation, and the
device token stays in the app. The scene mapping lives on the device, not in the repository. A Shortcut
is arbitrary automation and can do anything the user could do by hand, so it is off by default, named
by the user, receives **no training data** unless the owner opts in to a fixed string, and is never
verified or retried.

**Exclusions.** No redefinition of session semantics — the boundary above, not a §1.2 prohibition,
is what bounds this phase. No pause/resume, no accessory-level control beyond a scene, no watch-side
shortcut execution, no arbitrary URL execution, no HomeKit data in the intelligence layer, no server or
MCP involvement.

**Decided (2026-11-15).** `PauseWorkoutIntent`/`ResumeWorkoutIntent` are **excluded**, not mapped: a
rest timer is not a pause, and the session engine has no paused state. The Action + Side pair therefore
does nothing in this app. No open question remains in this phase.

**INT-7c — Shortcuts can start and finish a workout (owner request 2026-11-15).** The Shortcuts app
gets a `StartWorkoutShortcutIntent` and a `FinishWorkoutShortcutIntent` on the phone, and reuses the
watch's two Action-button intents. Start behaves like the Action button: a ready plan starts and the app
lands on the active workout; with nothing requested it says to request one and opens the app. Finish
never finishes anything — it opens the surface where sRPE is recorded (the phone's active workout, the
watch's finish sheet), exactly like the Action button's second press. No new entitlement, no server
change, and the same read-only-to-training-data boundary: these intents only call the existing start
and finish paths. **Closed 2026-11-15**, owner-confirmed on the iPhone and the Watch.

**Closed 2026-11-15**, owner-confirmed on the physical Watch. The watch target links
`StrengthIntents` and registers a watch-side provider over its own device credential.
`ActionButtonStartWorkoutIntent` (one `Strength` style, `suggestedWorkouts`, the 30-second start
budget) starts the plan the phone already requested for the watch and answers "Request a workout on
your iPhone first" when there is none. `ActionButtonOpenFinishIntent` is donated as the button's next
action after a successful start and, per the owner's choice, only brings the session forward — it never
finishes, so sRPE is still entered by hand. Four read-only intents and a watch-local
`AppShortcutsProvider` give watch Siri the same answers as the phone, dialog-only.

### INT-8 — Controlled plan review and recommendations (closed 2026-11-15)

**Owner decision (2026-11-15): closed.** No concrete question justified the phase, and read-only
explanation is already covered by the weekly review, the overview and INT-5. No scope is scheduled,
no code was written, and the phase does not reopen without a new owner request and a named question.

**Historical scope (not pursued).** A read-only "programme review" — what the plan is doing and why,
what the evidence suggests, what to discuss with the deterministic engine — without any proposal or
write. It was gated on the INT-3/INT-5 evaluation and owner approval because it sits close to advice.

**Exclusions retained.** Structured proposals, approval flows and any write remain outside this
workstream; a future proposer belongs to `DEC-LLM-09` and its own gated plan.

### INT-9 — Siri AI adoption pass (deferred; gated on iOS 27.3)

**Status.** Not scheduled. Starts only once iOS 27.3 is installed on the owner's device (about
December 2026), after INT-7, and only with a new ADR that supersedes the `ADR-INT-011` amendment.

**Scope.** Turn the readiness INT-7 builds into the preview surface: `@AppIntent(.tool)` on the
read-only intents (and optionally on the lifecycle intents), a `Skills.skillsbundle` of `SKILL.md`
files, `CardSnippet` wrappers around the existing snippet views, and a `SiriEvaluations` suite beside
the intent unit tests. Either raise the deployment target to 27.3 or wrap the additions in
`@available(iOS 27.3, *)`.

**Why deferred.** The API exists only in the 27.3 SDK, Apple states it may change, and it cannot ship
to App Store builds before spring 2027. Building it earlier is the only real throwaway risk in this
roadmap.

**Acceptance.** The same questions are answered through free-form Siri as through the shortcut phrases;
the skills bundle validates at build time; the evaluation suite passes on a device; the deterministic
path is unchanged; the app still builds and runs where the preview symbols are unavailable.

**Security.** No skill file may state a load, e1RM, readiness verdict, gate or prescription; no onscreen
entity donation; no fee-bearing call without an explicit owner decision.

### INT-10 — Local daily reminder nudge (owner-requested 2026-11-16)

**Scope.** One user-configured time of day at which the app reminds the athlete about the day's
training, in a short encouraging message that names one concrete fact from the read-only packages and
prompts readiness entry. A tap opens the app — Today, or the readiness form when readiness is missing.
The whole feature is client-side: no server call, endpoint, schema field, MCP tool, contract change,
new dependency or training rule. When a model runs at all it is the on-device Foundation Models model.

**Design.** The unit of work is *when the text is computed*: iOS freezes a local notification's content
at scheduling time, so the app precomputes and schedules instead of waking at the configured time.

1. **Fact package.** Assembled in `StrengthCore` from data the app already holds: `TodayResponse`
   (readiness known or not, score, active workout) plus the issued plan — session label, exercise
   count, and the lead lift's sets, reps and load, named from the cached exercise catalogue. Nothing is
   recomputed; the client owns no metric and fetches nothing extra for the reminder.
2. **Message.** On-device generation through the existing `NarrativeGenerating` path, reusing
   `NarrativeValidator`'s number-grounding check (`allowedNumbers`) unchanged: the body may only
   repeat numbers present in the facts. Output is a short title plus one body line, not the review
   shape.
3. **Template.** A deterministic, fact-derived message is a first-class outcome rather than a silent
   fallback: it ships when the model is unavailable, Apple Intelligence is off, validation fails or the
   device is ineligible. No cloud model is reachable from this path by construction.
4. **Scheduling.** One-shot `UNCalendarNotificationTrigger`s at the configured local hour and minute,
   over a bounded horizon, all with their text precomputed, re-armed (cancel-all then rebuild) on app
   activation, readiness submission, workout end, configuration change and pairing change. A repeating
   trigger is not used because it would freeze one body forever.
5. **Silence.** The nudge is suppressed for a day whose session is already recorded, and dropped at
   workout end. Known residual gap: a session executed only on the watch and never observed by the
   phone cannot suppress the same day; closing it would need remote push, which this phase excludes.
6. **Time base.** `DateComponents` hour/minute, so a time-zone change or DST transition moves with the
   device instead of firing at a stale absolute instant.
7. **Privacy.** The body is written for a Lock Screen: it may name a movement, a load or a readiness
   fact the athlete already sees in the app, and never a symptom, a note, a clinical detail or a
   verdict. The notification payload carries no training data beyond the rendered sentence.

**Exclusions.** Remote push (APNs), a server-side scheduler, `BGAppRefreshTask` or any other
background-refresh mode, a Notification Service Extension, Live Activities, watch-app nudges,
snooze/repeat reminders, more than one reminder per day, and any use of the DeepSeek or PCC paths for
this surface.

**Acceptance.** Unit tests: horizon dates across a DST transition, suppression after a recorded
session, cancel-then-rebuild leaving exactly the intended requests, template determinism, an ungrounded
number rejected by the validator, and permission-denied handling. The nudge path has no provider
choice wired into it at all, so the external-model clients are unreachable by construction rather
than by test. Physical iPhone: delivery at the configured time, tap routing
to Today and to the readiness form, the action button logging readiness, silence after a completed
session, and no duplicate after re-arming. Simulator success is not device proof.

**Security.** No new credential, endpoint or data egress. The message is generated on device from data
the app already displays, so nothing crosses the network that did not already. The reminder time and
the message are local settings; they never enter the repository, the server, an envelope or a prompt
contract.

**Status.** **Accepted 2026-11-16** (decision 17, `ADR-INT-019`) at the owner's request.
**Implemented 2026-11-16** on the iOS client: the scheduler, the on-device composer and template, the
settings section, the shared authorisation helper and the tap routing are in place, with 18 automated
tests passing and the iOS scheme building. **Physical-device acceptance is outstanding** — delivery
timing, tap routing and Focus behaviour are not proven by the simulator. iOS-only, with no backend
change.

### INT-11 — Explain the System (local knowledge; accepted 2026-11-16)

**Status.** Accepted 2026-11-16 (decision 18, ADR-INT-020). Plan only; no code is written yet.

**Goal.** Answer questions about how the system works — for example how readiness is calculated or
what evidence supports the injury-deload rule — from the project's own documentation, source code and
named private notes. Answers cite the files they used. This is a personal-use surface; there is no
internet search and no web browsing.

**Corpus and allowlist.** A named allowlist with path and regex rules covers:

- canonical portfolio docs, plans, ADRs, contracts and rules YAML;
- backend Python and iOS Swift source;
- selected test source files, named explicitly in the allowlist;
- explicitly named private notes that the owner permits.

Fixtures, snapshots, generated output and test data are excluded, as are build output, `.git`,
`data/`, credentials, tokens, keys, `.env` and LLM configuration files. Paths are normalised; symlink escapes and traversal are
rejected. The allowlist and denial patterns are reviewable in configuration, and the index is stored
locally with owner-only permissions, never committed.

**Index.** SQLite FTS5 over chunks split by markdown heading, Python function/class and Swift
type/function. Each chunk stores path, line range and the repository commit. The index is built
incrementally on server start: a manifest of path, size, mtime and SHA-256 plus the commit stamp
means unchanged files are skipped, changed files are replaced and removed files are dropped. The
build runs in the background; the Explain surface reports when the index is not ready yet instead of
blocking startup.

**Retrieval and answer.** A read-only endpoint searches the index for the question, applies bounded
deterministic query expansion for concepts (for example readiness/score/composite), and gives the
model the top chunks in a PROJECT SOURCES block. The model must answer only from that block and cite
path and line or document section. If nothing relevant is found it says so. Test-derived claims are
labelled as test expectations and kept distinct from implementation facts; a test assertion is not
presented as runtime behaviour.

A minimal citation sanity check, not a semantic validator: the cited path must exist and be
allowlisted, the line range must be inside the file, and any quoted snippet must overlap roughly with
the cited lines. A failed check is surfaced as a citation warning and the claim is marked unverified;
it does not silently pass. Retrieval and substantive citation accuracy remain best-effort by owner
decision. Code behaviour and documented intent are labelled separately.

**Surfaces.** A separate Explain tab in the web UI and a separate Explain tab in iOS. The iOS tab
calls the paired server and is unavailable offline. Citations open the existing docs/source viewer at
the cited location where possible; otherwise they are copyable path:line text. Reuse the existing
viewer rather than build a second one.

**Privacy.** Retrieved text is sent to the configured external model, DeepSeek. Permitted private
notes therefore leave the server; secrets must still be filtered. The feature is opt-in and does not
query the training capabilities unless the question explicitly mixes system explanation with training
data.

**Exclusions.** Web search, browsing, arbitrary URL fetch, vector embeddings/RAG, model-run shell
commands, code execution, writes and filesystem tools are out of scope. Fixtures, snapshots, generated
output and test data are excluded; only selected test source files are indexed.

**Acceptance.** Retrieval tests for readiness, injury-deload and code-path questions; citation
presence, path/line existence and rough quoted-snippet overlap; test-source labelling and no-answer
behaviour; allowlist, traversal, fixture/snapshot and secret-pattern rejection; incremental rebuild
skipping unchanged files; web and iOS Explain tabs; index-readiness state; iOS offline state; web and
iOS builds. Retrieval and substantive citation accuracy are accepted as best-effort, not a release
gate.

**Dependencies.** INT-5/INT-6 provide the server model client and web chat shell; INT-4b/INT-4d
provide the iOS chat shell. No new entitlement, backend schema or training rule is required.

**MCP.** The existing MCP server stays facts-only and is not used by INT-11: it provides transport,
authentication and a tool boundary, but no local knowledge index or search. Exposing Explain through
MCP would be a later contract change, covered with INT-12's approval rather than this phase.

### INT-12 — Web search and RAG (deferred; later step)

**Status.** Deferred 2026-11-16. Not approved, not implemented, not scheduled. It starts only after
INT-11 is delivered and evaluated. This is the consolidated home for the former separate web-access
and RAG candidates.

**Dependencies.** INT-11 for the local corpus, allowlist, chunking, citation format and evaluation
habits. It needs a new provider decision and ADR before code.

**Web search slice.** Opt-in per question, never automatic. The server calls one fixed search
provider (for example Brave or Google Programmable Search) and returns a bounded set of title/url/
snippet results. The first slice does not fetch arbitrary pages. If page fetch is added later it
needs an explicit allowlist, SSRF protection (no loopback/private/metadata endpoints), redirect and
size limits, content-type checks, timeouts and prompt-injection isolation. Web content is untrusted
data, always cited by URL and access date, and visibly separate from training facts and project
sources. Queries must not carry health details, names or tokens. iOS reaches the same server tool
through the paired server; the on-device model has no network path.

**RAG slice.** Only after the INT-11 FTS5 baseline is measured and found insufficient. Retrieval
would add embeddings/vector search over the same reviewed allowlist, with citation precision/recall,
staleness and unsupported-claim evaluation. It may add sources, never compute or override a training
value, never become a rule or hard constraint, and never open a write path. A deterministic
keyword/BM25 baseline stays the fallback and the stop rule prefers it.

**MCP.** The existing MCP server is useful transport, authentication and tool-boundary reuse, but it
is not a search engine and does not provide web access. Its current contract is facts-only
(ADR-INT-006). Exposing local knowledge search or web research through MCP would need a new ADR and
contract revision; it is not part of this phase. The first web slice remains an internal server tool
used by the web and iOS surfaces.

**Exclusions.** Automatic search on every message, arbitrary model-run URLs or shell commands,
unreviewed page content, scraping Google HTML, vector RAG before the FTS baseline is measured, and
mixing external claims into training rules.

**Acceptance.** Provider failure/no-results handling; URL citations; injection fixtures; blocked
localhost/private endpoints; privacy review; rate/budget caps; iOS opt-in; a pre-registered evaluation
set. RAG additionally needs the INT-11 baseline comparison and citation metrics.

**Owner decisions needed.** Search provider and plan/quota; snippets only or allowlisted page fetch;
whether health-adjacent queries are allowed; retention of queries/results; whether MCP exposure is
wanted at all.

## 12. Dependencies and sequencing

```
INT-1 ──▶ INT-1b ──▶ INT-2 ──▶ INT-3 ──┬──▶ INT-4 ──▶ INT-4b ──▶ INT-6 (iOS)
                                      │
                                      ├──▶ INT-5 ──▶ INT-6 (server/web)
                                      └──▶ INT-7
INT-4d (external chat model): delivered; chat only
INT-4e (plan-aware chat): delivered
INT-4c (PCC model choice): parked — needs paid developer access + entitlement
INT-8: closed 2026-11-15 — no concrete question; read-only explanation covered

INT-7     closed (read-only intents, phone and watch)
INT-7b-1  closed (automation executor + Shortcuts)
INT-7b-2  closed (HomeKit scenes, phone and watch)
INT-7b-3  closed (Action button + watch Siri)
INT-7c    closed (Shortcuts start/finish, phone and watch)
INT-10    implemented 2026-11-16 — local daily reminder nudge (iOS only; device acceptance outstanding)
INT-11    accepted 2026-11-16 — Explain the System, local docs/code retrieval (plan only)
INT-12    deferred — web search and RAG; after INT-11, new provider/ADR
INT-9     deferred — starts only after iOS 27.3 lands
INT-4c    parked — needs paid developer access + the PCC entitlement
```

- INT-1, INT-1b and INT-2 are delivered; INT-3 is closed (2026-11-15). INT-4 is delivered.
- INT-4b (on-device chat) and INT-4d (DeepSeek chat) are delivered. INT-4e (plan-aware chat and
  suggestions) is delivered. INT-4c (PCC model choice) is parked
  until paid developer access and the entitlement exist; INT-5 delivered the server narrative track.
  INT-6 is closed (2026-11-15): its iOS surface is INT-4b and its server/web chat uses the deterministic dossier; tool calling and streaming are deferred.
- INT-1b is a split of the original INT-1 scope, not a new capability; INT-2 does not depend on it,
  so either order is safe after INT-1.
- INT-3 is the first user-visible feature and the first API change.
- INT-4 (on device) and INT-5 (server) are independent; either can ship first.
- INT-6 needs at least one working narrative path.
- **Delivery complete 2026-11-15:** INT-7 → INT-7b-1 → INT-7b-2 → INT-7b-3 → INT-7c all closed and
  owner-confirmed. INT-11 is accepted but not implemented; INT-9 remains gated on iOS 27.3, plus the
  parked INT-4c.
- **Why this order.** INT-7 first: it is the smallest phase, it is what December's adoption annotates,
  and built to §7.6 it leaves nothing behind. 7b-1 next: the cheapest real channel proves the trigger,
  ordering, dedupe and failure isolation that the heavier channels reuse. 7b-2 then adds the HomeKit
  entitlement and picker on top of that executor. 7b-3 last: it is the only slice that needs repeated
  physical-watch acceptance. INT-9 is the single pass that requires iOS 27.3.
- **Throwaway at the 27.3 upgrade: none, if the order holds.** The intents gain one annotation, the
  entities already carry the metadata, the snippet views become `CardSnippet` hosts, and HomeKit,
  Shortcuts and the Action button are stable APIs with no preview equivalent. INT-7 puts the intents in
  a shared module, so 7b-3 links it into the watch instead of moving code. The only real waste would
  be writing preview code before 27.3 (impossible today) or over-engineering dialog strings and phrase
  lists that Siri's own matching later replaces.
- 7b-3 is independent of 7b-1/2 and may run in parallel if the watch is the priority; INT-9 may not start
  before INT-7, and not before 27.3 is installed.
- INT-7 is independent of the model work and could run in parallel with INT-4/5.
- INT-7b is technically independent of INT-7 and of every model phase; the order above is a
  recommendation for sequencing and risk, not a hard dependency, and 7b-3 can be deferred without
  blocking 7b-1/7b-2 (`ADR-INT-018`).
- INT-8 is closed; it does not block or extend the remaining phases.
- **INT-10 is independent of every other phase.** It needs nothing to land first, changes no server
  code or contract, and reuses INT-4's on-device narrative plumbing and the INT-2 capability text the
  client already fetches. It is the only phase whose output is consumed while the app is not in the
  foreground, which is why its text is precomputed rather than produced on demand.
- **INT-11 is independent of training decisions.** It reuses the INT-5/INT-6 model client and chat
  shells, adds only a local read-only index and explanation surfaces, and changes no training rule,
  envelope or MCP contract. INT-12 is the separate, deferred web-search/RAG step; MCP stays
  facts-only until a new ADR.

### Deferred — web access (web UI and iOS)

Consolidated into **INT-12**. No browsing, web search, URL fetch or web citation is approved; the
detailed policy lives there.

### Later-stage candidate — retrieval-augmented generation (not a phase, not scheduled)

Consolidated into **INT-12**. Retrieval remains a later, separately approved step; the detailed
prerequisites live there.

## 13. Decisions (all accepted)

Decision 19 is deferred, not accepted; it is recorded for the later INT-12 step.

| # | Decision | Recommendation | ADR |
|---|---|---|---|
| 1 | MCP server placement: existing backend repository as a separately deployable module | approve; no fourth repository | `ADR-INT-001` |
| 2 | Capability layer location: new provider-neutral `strength_coach/intelligence/` package rather than the planned `agents/context.py` | approve; supersedes the path in `LLM-INTEGRATION-PLAN.md` | `ADR-INT-002` |
| 3 | MCP protocol revision and SDK: `mcp` 2.x, revision 2026-07-28 with legacy-client support | approve; pin `mcp>=2,<3` | `ADR-INT-003` |
| 4 | MCP authentication for MVP: static per-client bearer token over loopback/tailnet, no OAuth server | approve; OAuth 2.1 is a later decision if a hosted client or non-owner user is required | `ADR-INT-004` |
| 5 | MCP exposure: no prompts capability; tools and resources only | approve | `ADR-INT-005` |
| 6 | Model boundary: MCP tools return deterministic facts only; narration is a host/model capability, so `explain_prescription` is not a tool | approve; it prevents a cost-bearing, non-deterministic tool | `ADR-INT-006` |
| 7 | iOS data path: REST envelopes plus native `Tool` adapters, no MCP client in the app | approve | `ADR-INT-007` |
| 8 | Backend LLM retrieval: in-process client by default, with MCP parity tests | approve; saves a hop and still exercises MCP | `ADR-INT-008` |
| 9 | `get_programme_block_summary` as a derived reporting window (no stored block exists) | approve the rename and limitation wording | `ADR-INT-009` |
| 10 | No caching in INT-1/INT-2; revisit only with measured latency | approve | `ADR-INT-010` |
| 11 | Siri AI Developer Preview excluded; stable App Intents only | **accepted 2026-11-15**; adoption on the owner's own device once iOS 27.3 ships | `ADR-INT-011` (accepted) |
| 12 | Phase 1b (retire the minimal LLM selector) before INT-5 | approve; otherwise two model surfaces coexist | `ADR-INT-012` |
| 13 | This plan supersedes the earlier LLM and Apple Intelligence forward plans; the constrained proposer is deferred/unscheduled | approve; §16 lists exactly what remains in force | `ADR-INT-013` |
| 14 | Siri AI readiness without adoption: INT-7 ships tool-ready metadata, Spotlight-indexable entities and snippet-ready views, with no preview symbol before the adoption pass | **accepted 2026-11-15**; makes the December adoption additive rather than a rewrite (§7.6) | `ADR-INT-011` (accepted, amended) |
| 15 | Workout lifecycle surfaces: `StartWorkoutIntent` + a donated end intent for the watch Action button, user-selected HomeKit scenes on start and end (phone and watch), and user-selected Shortcuts on start and end (phone only) | **accepted 2026-11-15**; Pause/Resume excluded; exactly one device executes the scenes per session; the Shortcuts channel is best-effort and phone-only | `ADR-INT-018` (accepted) |
| 16 | Shortcuts start/finish (INT-7c): the Shortcuts app can start the ready workout and open the finish surface on phone and watch; ending never finishes by itself | **accepted 2026-11-15** at the owner's request; it reuses decision 15's boundary and adds no new training path | `ADR-INT-018` (extended) |
| 17 | Daily reminder nudge (INT-10): one user-set time, one local notification per day whose text is precomputed on device from the read-only packages, on-device model or deterministic template only, silent once the day is trained | **accepted 2026-11-16** at the owner's request; the §1.2 "notification intelligence" exclusion is narrowed to Live Activities, and remote push, background refresh and external models stay excluded | `ADR-INT-019` (accepted) |
| 18 | Explain the System (INT-11): local incremental FTS5 index over an explicit docs/source/private allowlist, separate web and iOS tabs, best-effort path:line citations, no web or vector search | **accepted 2026-11-16** at the owner's request for personal use; named allowlist with regex, selected test source included while fixtures/snapshots/test data are excluded, private notes permitted but secrets excluded, index at server start, existing source viewer reused, minimal citation path/line/snippet sanity check; substantive citation/retrieval/staleness risks accepted | `ADR-INT-020` (accepted; implementation pending) |
| 19 | Web search and RAG (INT-12): opt-in fixed-provider search with citations, and embeddings only if the INT-11 FTS baseline is insufficient | **deferred 2026-11-16**; not approved or scheduled; MCP stays facts-only; provider/privacy/SSRF/evaluation decisions are still open | `ADR-INT-021` (deferred) |

Both former open questions are answered (2026-11-15):

- **MCP host: the Python client only.** The static per-client bearer token is sufficient for INT-1
  acceptance; no OAuth 2.1 authorization server, no user accounts and no tenancy are built. Revisit
  only if a hosted MCP host is added (`ADR-INT-004`).
- **Weekly review on the web UI: already delivered.** The server exposes
  `/api/ios/v1/intelligence/weekly-review` and the web UI has a Weekly review panel, so the review is
  available on iPhone, the web UI and MCP. No web panel is deferred.

## 14. Documentation change proposal (deliverable F)

| Action | Repository | Path | Purpose |
|---|---|---|---|
| **create** | portfolio | `docs/plans/TRAINING-INTELLIGENCE.md` | this plan |
| **create** | portfolio | `docs/plans/TRAINING-INTELLIGENCE-AUDIT.md` | audit record (A) |
| **create** | portfolio | `docs/contracts/TRAINING-INTELLIGENCE-CONTRACT.md` | MCP, envelope and adapter contract (C) |
| **create** | portfolio | `docs/decisions/TRAINING-INTELLIGENCE-ADR.md` | ADR-INT-001…012 (E) |
| **update** | portfolio | `docs/README.md` | index the plan, audit, contract and decisions |
| **update** | portfolio | `docs/plans/README.md` | list the plan as a canonical shared plan |
| **update** | portfolio | `docs/contracts/README.md` | add the contract row |
| **update** | portfolio | `docs/DOCUMENTATION.md` | add the plan/contract/decisions as canonical sources |
| **update** | backend | `docs/LLM-INTEGRATION-PLAN.md` | §4.1 builder path pointer; §9.2 MCP status pointer; §11 `mcp/` row |
| **update** | backend | `ROADMAP.md` | a short workstream pointer that links here (status stays in this plan and the backend roadmap) |
| **update** | backend | `docs/ARCHITECTURE.md` | §3.1 pointer to the intelligence layer |
| **update** | iOS | `docs/README.md` | pointer to the plan and contract |
| **update** | iOS | `docs/AGENT-CONTRACTS.md` | note that the intelligence envelopes are additive read-only contracts |
| **no change** | backend | `docs/API.md`, `docs/DATA-MODEL.md`, `docs/DECISIONS.md` | no API or schema change in INT-0; INT-3 adds the route section |

Rules respected: one canonical home per document, no duplicate shared text in component repositories,
links (not copies), no moving of historical documents, headings preserved in edited files, and
`scripts/check-doc-headings.sh` runs before any commit.

## 15. Review for unnecessary complexity

Deliberately **not** built:

- No vector database, embedding pipeline or RAG. The facts are structured rows; the corpus is small and
  exact lookup wins. Retrieval in this architecture means "call the right capability", not semantic
  search.
- No agent framework, planner loop or autonomous multi-step execution.
- No new service layer, repository abstraction or dependency-injection container over the existing
  function modules.
- No new database tables for intelligence output. The trace tables already exist; model output is an
  event, not an artifact (`DEC-LLM-01`).
- No OAuth authorization server, no user accounts, no tenancy.
- No MCP prompts, no MCP sampling, no MCP roots, no subscriptions (read-only, no live updates).
- No caching layer, no message queue, no background workers.
- No duplicate metric code in Swift or in the intelligence package.
- No fourth repository.

The only new runtime dependency is the MCP SDK, and only in an optional extra.

## 16. Supersession and authority

### 16.1 One authority

This plan is the single forward plan for training intelligence across the three repositories. Any new
LLM, MCP, Apple Intelligence or Siri proposal amends this plan and records a new ADR; it does not
create a second plan. The stable-API boundary, the capability layer and the read-only constraint are
described here and nowhere else.

### 16.2 What this plan supersedes

| Superseded document or section | Disposition | Replaced by |
|---|---|---|
| `strength-training-app/docs/LLM-INTEGRATION-PLAN.md` §3 analyst/explainer boundaries | superseded | §4–§6 and the contract |
| §4 shared context and evidence layer, including the `agents/context.py` path | superseded | §4, `intelligence/context.py`, `ADR-INT-002` |
| §5 athlete-analyst reports | superseded | §4, `get_weekly_review`, model capabilities |
| §6 programme explainer | superseded | `get_prescription` plus a model capability (§7.4, `ADR-INT-006`) |
| §9.2 MCP server over Tailscale (Iteration 2 candidate) | superseded | §5, `ADR-INT-003`, `ADR-INT-004` |
| §10 phases 1, 2 and 3 | superseded | INT-1 to INT-5 |
| §11 future areas for context, analyst, explainer and `mcp/` | superseded | §3.2 |
| `docs/plans/IOS-CLIENT-PLAN.md` §5 Apple Intelligence and PCC bullets | superseded | §7.2–§7.3, INT-4/INT-5 |
| `ROADMAP.md` §4.24 phases 1–3 and the Iteration-2 MCP clause; §4.18 forward idea | superseded | §12, INT-1 to INT-8 |
| Any earlier uncommitted Apple Intelligence or MCP scope | superseded | this plan |

The superseded documents remain in place as **historical and requirements records**. They are not
deleted and their headings are not rewritten, because they record decisions that still bind the
retained items in §16.3.

### 16.3 What remains in force

| Item | Why it is not superseded | Owner |
|---|---|---|
| `DEC-LLM-01` to `DEC-LLM-06` | output is an event; structural edits are rebuilt; menus are Python-computed; essential-lift rules | backend `docs/DECISIONS.md` |
| `LLM-INTEGRATION-PLAN.md` §8.1 field-level outbound-data inventory | the privacy precondition for every model path; adopted by reference in §9 | backend, unchanged |
| `LLM-INTEGRATION-PLAN.md` §9 evaluation and rollout gates | gate vocabulary for any narrated or write path; adopted by reference where an INT phase narrates | backend, unchanged |
| Phase 1b selector retirement (`DEC-LLM-14`) | it made INT-5 the only model surface (`ADR-INT-012`); **retired 2026-11-15** and recorded here so it is not reintroduced | backend, done |
| Constrained proposer (`DEC-LLM-09`, LLM plan §7, phases 4–5) | a **write** capability outside this read-only workstream; **reclassified as deferred/unscheduled**, requirements retained, any future work needs a new decision | backend, unscheduled |
| AFC (`docs/plans/AFC.md`) | not an LLM plan; it is the deterministic producer of the evidence consumed here | portfolio |
| iOS phase contracts (Phase 1/2/3A/4/R7/R8/watch) | they exclude AI surfaces and are unchanged | portfolio contracts |
| `docs/ARCHITECTURE.md` §3 boundaries and `PRIVACY.md` §7 | they constrain every model path and remain true | backend docs |

### 16.4 Status changes this supersession makes

- **MCP moves** from a conditional Iteration-2 candidate to the primary AI-facing interface of INT-1
  (`ADR-INT-003`), still read-only and still reusing the existing core.
- **The context and evidence builder moves** from the planned `agents/context.py` to the
  provider-neutral `strength_coach/intelligence/context.py` (`ADR-INT-002`).
- **Apple Intelligence and PCC move** from an unscheduled Phase 5 bullet to a specified, independently
  disableable INT-4/INT-5 scope with no silent cloud fallback (`ADR-INT-007`).
- **The constrained proposer becomes deferred/unscheduled.** It is not dropped: its decision,
  requirements and gates stay recorded, and re-activating it requires a new decision.
- **No completed phase is reopened.** All previously closed work (iOS Phases 0–6, R1–R10,
  AFC-2 to AFC-4) keeps its recorded status.

### 16.5 Change control

- A new LLM or Apple-platform proposal MUST amend this plan and add an ADR; it MUST NOT create a
  parallel plan or extend a superseded document.
- A change that would make any intelligence path write-capable, or that re-introduces a second
  calculation, is a new decision outside this plan.
- If this plan is itself superseded, it MUST name and link its replacement, and the replacement MUST
  carry forward §16.3.

## Related

- [Implementation audit](TRAINING-INTELLIGENCE-AUDIT.md)
- [MCP and capability contract](../contracts/TRAINING-INTELLIGENCE-CONTRACT.md)
- [Architecture decision records](../decisions/TRAINING-INTELLIGENCE-ADR.md)
- [iOS client phase plan](IOS-CLIENT-PLAN.md)
- [AFC plan](AFC.md)
- [Backend LLM integration plan](https://github.com/georgesdib/strength-training-app/blob/development/docs/LLM-INTEGRATION-PLAN.md)
- [Backend roadmap](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md)
- [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)
- [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/)
- [Apple Foundation Models](https://developer.apple.com/documentation/foundationmodels)
- [Siri AI Developer Preview](https://developer.apple.com/documentation/appintents/siri-ai-developer-preview)
- [StartWorkoutIntent](https://developer.apple.com/documentation/appintents/startworkoutintent)
- [Responding to the Action button on Apple Watch Ultra](https://developer.apple.com/documentation/appintents/actionbuttonarticle)
- [HMHome.executeActionSet(_:completionHandler:)](<https://developer.apple.com/documentation/homekit/hmhome/executeactionset(_:completionhandler:)>)
- [Orchestrating complex actions with app skills](https://developer.apple.com/documentation/appintents/orchestrating-complex-actions-with-app-skills)
- [iOS & iPadOS 27.3 beta release notes](https://developer.apple.com/documentation/ios-ipados-release-notes/ios-ipados-27_3-release-notes)
- [Siri AI is now open to all developers (2026-11-03)](https://developer.apple.com/news/?id=gdk2umrf)
- [TN3193 — managing the context window](https://developer.apple.com/documentation/technotes/tn3193-managing-the-on-device-foundation-model-s-context-window)
