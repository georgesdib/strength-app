# TRAINING INTELLIGENCE — ARCHITECTURE AND IMPLEMENTATION PLAN

**Canonical location:** this file, in the portfolio repository.
**Status:** proposed 2026-11-14 (INT-0, planning only). No runtime, API, schema, dependency,
prompt or training-rule change is implemented by this plan.
**Supersedes:** the forward-planning content of the earlier LLM and Apple Intelligence plans —
`strength-training-app/docs/LLM-INTEGRATION-PLAN.md` (except the items retained in §16.3) and the
Apple Intelligence/PCC items in `docs/plans/IOS-CLIENT-PLAN.md` §5. This plan is the single forward
plan for training intelligence. See §16.
**Owner:** the athlete. INT-1 may not start without explicit approval of the decisions in section 13.
**Roadmap:** phases INT-1 to INT-8, section 12. Backend implementation status stays in
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
- Cardio tracking, workout-execution changes, watch-app intelligence, notification/Live-Activity
  intelligence.
- Depending on beta-only Apple APIs, including the iOS 27.3 Siri AI Developer Preview.
- Storing model output as a training artifact or as a prescription.

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

Design consequences:

- The weekly review narrative is generated in **one session**, with at most three tools, a short
  instruction (1–3 paragraphs), and a compact fact block. If the estimator says the request exceeds
  ~3,200 tokens, the app drops to a smaller projection or skips the narrative.
- Tools are used only where the model must decide what it needs. The review screen already has the
  facts, so the default path is **no tool calling**: facts go into the prompt, and `ToolCallingMode`
  is `.allowed` only for the "ask a follow-up" case.
- The output type is small: a headline, 2–4 observations each with fact references, and one
  limitation line. `GenerationOptions.maximumResponseTokens` is a guard, not the primary budget.

### 7.3 Apple Private Cloud Compute

`PrivateCloudComputeLanguageModel` (iOS 27.0+) provides a **32K** context and reasoning levels, uses
the same `LanguageModelSession` API, needs a network, has a **per-day quota** and requires Apple's
managed entitlement. It is a stable API in a released OS but **gated access**, so it cannot be the
default or a dependency. Its privacy story is Apple-mediated, not owner-mediated, and it must be
presented as server processing with explicit consent and a context preview, per
`IOS-CLIENT-PLAN.md` §5. Quota errors (`.quotaLimitReached`) are a normal state with a clear
message, never a retry loop.

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
| Siri AI Developer Preview (conversational, skills, onscreen awareness) | **iOS 27.3 beta**, internal builds only, "API may change", App Store builds excluded, not available in the EU | **do not adopt**; revisit only if it ships and a new decision approves it |

Nothing in this plan depends on the Siri AI preview. The stable intents are useful without it: they
run from Shortcuts and from Siri's existing App Intents support.

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
| Readiness | `queries.readiness_series()`, `features/readiness_score.py` | coverage and trend; observed only, no fill |
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
(`get_training_overview`). Not implemented: everything in INT-1b, the baseline context package and
any model path. Implementation detail is in the backend
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

**Scope.** The `mcp>=2,<3` optional dependency and console script; `strength_coach/intelligence/mcp/`
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

**Scope.** `get_exercise_progression`, `get_readiness_history`, `get_adherence_analysis`,
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

### INT-5 — Backend LLM narrative and multi-tool integration

**Scope.** `intelligence/model/` orchestration, `NarrativeProvider` with `NullProvider` and the
existing OpenAI-compatible adapter, `IntelligenceClient` (`InProcessClient` / `MCPClient`), JSON
output contract and validator, `run`/`run_event` trace, cost budget, CLI command
(`strength-coach intelligence review --narrate`), and the evaluation harness. No new public
endpoint.

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

### INT-6 — Conversational Training Intelligence

**Scope.** A multi-turn surface over the same five capabilities: follow-up questions within a
review, "why is my bench flat?", "what changed this month?", with an explicit context budget, turn
cap, and a hard rule that the model may only cite facts it retrieved in this conversation. Ship on
iOS (AFM/PCC) first; a web chat panel later.

**Dependencies.** INT-4 (and INT-5 for any server-side conversation). Requires a decision on
transcript retention.

**Files/repos.** iOS `Features/Intelligence/ChatView.swift`, session management, tests; optional web
panel.

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

**Dependencies.** INT-3 (data), INT-4 optional. Independent of INT-5/6.

**Files/repos.** iOS: `StrengthApp/Intents/*`, `StrengthApp/AppShortcuts.swift`, tests.

**Acceptance.** Each intent works from Shortcuts and from Siri's existing App Intents support; no
intent can write; unauthenticated/offline states produce a clear dialog; the intent does not start a
workout.

**Tests.** Intent unit tests with a stub adapter; shortcut phrase validation; a manual device check
recorded in `DEVICE-ACCEPTANCE.md`.

**Security.** No health data in dialogs by default; no onscreen entity donation in MVP.

**Exclusions.** Siri AI Developer Preview, app skills, onscreen awareness, cross-app actions,
conversational Siri. Revisit only after Apple ships it and a new decision approves it.

### INT-8 — Controlled plan review and recommendations (gated, likely deferred)

**Scope.** Evaluate whether a *read-only* "programme review" (what the plan is doing and why, what the
evidence suggests, what to discuss with the deterministic engine) is useful **without any proposal or
write**. If it is, the output is text plus links into the existing prescription flow; the athlete acts
there.

**Dependencies.** INT-3 and INT-5 evaluation green; owner approval; explicit confirmation that
recommendations are discussion, not instructions.

**Acceptance (if pursued).** No tool, route or capability can alter a prescription; every
recommendation is labelled as a discussion point; the deterministic engine remains the only
prescriber.

**Exclusions.** Structured proposals, approval flows and any write are **not** part of this
workstream. If the owner wants a proposer later, it belongs to `DEC-LLM-09` and its own gated plan,
consuming this capability layer as one input.

**Recommendation:** close INT-8 at the INT-3 gate unless the owner identifies a concrete question the
review cannot answer. Read-only explanation is already covered by INT-3/INT-5.

## 12. Dependencies and sequencing

```
INT-1 ──▶ INT-1b ──▶ INT-2 ──▶ INT-3 ──┬──▶ INT-4 ──▶ INT-6
                                      │
                                      ├──▶ INT-5 ──▶ INT-6
                                      └──▶ INT-7
INT-8: gated after INT-3 + INT-5 evaluation; default disposition: deferred
```

- INT-1 (delivered) and INT-2 need no model and no new API route; INT-1b adds the MCP transport only.
- INT-1b is a split of the original INT-1 scope, not a new capability; INT-2 does not depend on it,
  so either order is safe after INT-1.
- INT-3 is the first user-visible feature and the first API change.
- INT-4 (on device) and INT-5 (server) are independent; either can ship first.
- INT-6 needs at least one working narrative path.
- INT-7 is independent of the model work and could run in parallel with INT-4/5.
- INT-8 has no implementation dependency that justifies starting it early.

## 13. Decisions requiring explicit approval

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
| 11 | Siri AI Developer Preview excluded; stable App Intents only | approve | `ADR-INT-011` |
| 12 | Phase 1b (retire the minimal LLM selector) before INT-5 | approve; otherwise two model surfaces coexist | `ADR-INT-012` |
| 13 | This plan supersedes the earlier LLM and Apple Intelligence forward plans; the constrained proposer is deferred/unscheduled | approve; §16 lists exactly what remains in force | `ADR-INT-013` |

Two further points need an owner answer rather than an architecture decision:

- **Which MCP host will be used first** (Claude Desktop/Code, another client, or only the Python
  client)? It determines whether static bearer auth is sufficient for INT-1 acceptance.
- **Whether the weekly review should ever appear on the web UI** or stay iPhone/MCP-only. The plan
  assumes iPhone + MCP for INT-3 and defers a web panel.

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
| Phase 1b selector retirement (`DEC-LLM-14`) | still required before INT-5 so only one model surface exists (`ADR-INT-012`) | backend work item |
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
- [TN3193 — managing the context window](https://developer.apple.com/documentation/technotes/tn3193-managing-the-on-device-foundation-model-s-context-window)
