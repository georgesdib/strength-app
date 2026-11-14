# TRAINING INTELLIGENCE — ARCHITECTURE DECISION RECORDS

**Status:** proposed 2026-11-14. Each record is pending owner approval; none is implemented.
**Canonical location:** this file, in the portfolio repository. It records decisions that span the
backend, the iOS client and the MCP surface. Backend-only decisions remain in
[`docs/DECISIONS.md`](https://github.com/georgesdib/strength-training-app/blob/development/docs/DECISIONS.md)
and are cross-referenced, never duplicated.
**Companions:** [plan](../plans/TRAINING-INTELLIGENCE.md), [audit](../plans/TRAINING-INTELLIGENCE-AUDIT.md),
[contract](../contracts/TRAINING-INTELLIGENCE-CONTRACT.md).

Format: context → decision → alternatives → consequences → status and open questions.

## ADR-INT-001 — The MCP server lives in the backend repository as a separate deployable

**Context.** The capability layer must call `strength_coach` functions directly; a separate
repository would need the package published or vendored, duplicating either code or release
coupling. The backend already has one package, one test suite, one lint gate and one deployment
directory. The repository rule is to avoid a fourth repository without a compelling reason.

**Decision.** Implement the capability layer and MCP transport inside
`georgesdib/strength-training-app` as `strength_coach/intelligence/` plus
`strength_coach/intelligence/mcp/`, with an optional dependency group, a new console script
(`strength-intelligence-mcp`), its own config file, bind address, token file and systemd unit. It is
deployed as an independent process that never imports `strength_coach.web`.

**Alternatives considered.**

- *Separate repository.* Cleaner boundary, but creates a fourth repository, requires publishing
  `strength-coach`, and forces cross-repo releases for every metric fix. Rejected.
- *A route inside the existing web server.* Simplest to write, but couples the AI surface to the
  unauthenticated home-LAN UI, makes independent deployment impossible and puts a second auth model
  in the same process. Rejected.
- *A separate process in the same repo but a separate package.* Unnecessary: the package boundary is
  already enforced by an import-direction test, and a second distribution adds packaging work without
  isolation benefit.

**Consequences.** One repository, one CI, one release. The deployable must be kept genuinely
independent: no web imports, read-only database handle, own configuration. A future split remains
possible because the module only depends on `strength_coach` core.

**Status.** Proposed.

## ADR-INT-002 — A provider-neutral intelligence package, not `agents/context.py`

**Context.** `LLM-INTEGRATION-PLAN.md` §4.1 planned `strength_coach/agents/context.py` for the future
context builder. `agents/` is documented as the LLM layer: "prompt assembly, tool calls, prose".
Deterministic fact assembly that MCP, REST and every model path consume must not live inside the
model layer, or the dependency direction inverts and the capability layer becomes model-coupled.

**Decision.** Create `strength_coach/intelligence/` as a new top-level package: `capabilities/`
(deterministic facts), `context.py` (baseline package), `model/` (prompts, providers, validation)
and `mcp/` (transport). The package may import `features`, `queries`, `prescribe`, `store` and
`domain`. It must not be imported by any of them. `agents/` keeps narrative and the existing
proposal path and is imported by `intelligence/model/`, not by `intelligence/capabilities/`.

**Alternatives considered.**

- *Keep `agents/context.py`* as planned. Rejected: the MCP server would import the model layer to
  get facts, and the capability layer would be untestable without it.
- *Put capabilities in `features/`*. Rejected: `features/` owns metrics, not cross-metric
  composition or transport-shaped envelopes; adding envelope/evidence assembly there would make the
  metric layer depend on presentation concerns.

**Consequences.** `LLM-INTEGRATION-PLAN.md` §4.1 and §11 get a pointer to this decision (no rewrite,
headings preserved). The layering table in `ARCHITECTURE.md` gains one row in INT-1. The one-context-
builder rule (`DEC-LLM-08`) is preserved: there is still exactly one builder, in a different place.

**Status.** Proposed. **Open question:** does the owner accept moving the planned path?

## ADR-INT-003 — MCP protocol revision 2026-07-28 with the official Python SDK 2.x

**Context.** The current stable MCP revision is 2026-07-28. It removed protocol-level sessions and the
`initialize` handshake, added `server/discover`, replaced the HTTP GET stream with
`subscriptions/listen`, moved server-to-client requests into multi-round-trip results, and requires
`resultType` on results and `ttlMs`/`cacheScope` on cacheable results. The official Python SDK
2.x speaks that revision and serves legacy clients (≤ 2025-11-25) from the same endpoint. Many MCP
hosts still negotiate a legacy revision.

**Decision.** Use `mcp>=2,<3` (the `MCPServer` API) and the Streamable HTTP transport, targeting
revision 2026-07-28 while accepting legacy clients through the SDK. Pin the dependency in an optional
`intelligence` extra. Do not implement the protocol by hand. Do not use the deprecated HTTP+SSE
transport, sampling, roots or logging.

**Alternatives considered.**

- *Target 2025-11-25 for maximum client compatibility.* Rejected: it is the older era, has in-process
  session state that complicates scaling, and the SDK serves both anyway.
- *A hand-rolled JSON-RPC server.* Rejected: protocol churn is high (three revisions in two years),
  and the SDK is Tier 1.
- *The TypeScript SDK in a separate service.* Rejected: adds a second runtime and language to a Python
  backend.

**Consequences.** New runtime dependency, optional and pinned. Protocol tests must cover both eras.
`json_response=True` for v1 because no tool streams progress. The server is stateless on the modern
path, so deployment does not need sticky routing; legacy clients would.

**Status.** Proposed.

## ADR-INT-004 — Static per-client bearer tokens for MVP; OAuth 2.1 is a later decision

**Context.** The MCP authorization profile expects OAuth 2.1 with RFC 9728 protected-resource
metadata and RFC 8707 resource indicators. This deployment has **no authorization server, no users
and no tenancy**; the only precedent is per-device bearer tokens on `/api/ios/v1/`. The MCP
specification states authorization is optional for the protocol, and requires that if OAuth is
implemented it follows the profile.

**Decision.** For MVP, authenticate with one opaque bearer token per MCP client, stored as a SHA-256
digest in a git-ignored file, validated in constant time by a small ASGI wrapper, over a loopback or
tailnet bind. Return `401` with a bearer challenge. Do **not** publish a protected-resource-metadata
document, because no authorization server exists. Do not accept a tailnet address as authentication.

**Alternatives considered.**

- *Full OAuth 2.1 authorization server.* Correct for a multi-user or hosted deployment; for one owner
  it adds a login UI, consent, token lifetime and revocation infrastructure to protect one athlete's
  own data on their own network. Deferred, not rejected.
- *Client-certificate (mTLS) auth.* Operable but poorly supported by MCP hosts. Rejected.
- *No auth, tailnet only.* Rejected: network reachability is not authorization, and the offline data
  is health-adjacent.
- *Reuse iOS device tokens.* Rejected: conflates device classes and gives a phone token access to a
  different surface.

**Consequences.** Hosted clients that require OAuth discovery cannot connect; this is an accepted,
documented limitation. Moving to OAuth is a contained change at the auth wrapper, and the capability
layer is unaffected. **Open question for the owner:** which MCP host will be used first? That answer
decides whether a static token is sufficient for INT-1 acceptance.

**Status.** Proposed.

## ADR-INT-005 — Tools and resources only; no MCP prompts

**Context.** MCP offers prompts as server-authored templates. The server is meant to expose training
facts; the prompt that frames a conversation belongs to the host (Claude, the app, the CLI), which
also owns model selection and UX.

**Decision.** Advertise `tools` and `resources`. Do not advertise `prompts`, `logging`,
`sampling`, `roots` or subscriptions. Do not implement elicitation or tasks.

**Consequences.** The server stays deterministic and model-agnostic; prompt versioning lives in
`intelligence/model/` or in the app. A host that wants a review prompt writes one; nothing in the
server needs to know.

**Status.** Proposed.

## ADR-INT-006 — MCP tools return facts, never narration

**Context.** `explain_prescription` was a candidate tool. Its output is prose, which is
non-deterministic, costs money per call, cannot be cached safely and cannot be validated by schema
alone. The read-only contract in the spec would be blurred: a "tool" would become a model endpoint.

**Decision.** Every MCP tool returns a deterministic envelope. Narration is a **capability of the
host** (iOS Foundation Models) or of the server-side model layer (INT-5), both of which consume the
same tools/facts. `explain_prescription` is replaced by `get_prescription` plus a model-side
explanation capability.

**Alternatives considered.**

- *An `explain_prescription` tool backed by a server LLM.* Rejected for v1: it makes the MCP server
  depend on a provider, a key and a budget, and introduces a second place where a model output is
  returned as if it were data.
- *A tool that returns prompt text.* Rejected: that is what the prompts capability is, and it is
  declined in ADR-INT-005.

**Consequences.** Hosts that want prose must run a model themselves (which they do). The weekly review
tool returns facts and the app narrates. Server-side narration remains available through INT-5 without
changing the MCP surface.

**Status.** Proposed.

## ADR-INT-007 — The iOS app consumes REST envelopes, not MCP

**Context.** Apple Foundation Models has no MCP client and no Apple framework exposes one. The
official Swift MCP SDK is Tier 3 and adopts protocol revisions on its own schedule. The app already
has an authenticated, versioned REST facade, a shared Swift package and a server-produced report it
renders. Putting MCP in the app would add a network hop, a second auth mechanism and an unmaintained
client, and would not let Foundation Models call tools more easily.

**Decision.** The app consumes the same capability envelopes over
`/api/ios/v1/intelligence/…` and exposes them to Foundation Models as native `Tool`
implementations. `StrengthCore` holds envelope models and the REST adapter only, with no
FoundationModels, SwiftUI, UIKit, HealthKit or WatchKit import. Model-specific code lives in
`StrengthApp/Intelligence/`.

**Alternatives considered.**

- *Embed the Swift MCP SDK.* Rejected per above.
- *Compose existing REST endpoints in Swift.* Rejected: it duplicates assembly and evidence logic in
  the client, violating `DEC-AFC-03` and the no-duplicate-methodology invariant.

**Consequences.** One new additive REST surface (INT-3). A future watch app can reuse the same
envelope models. If Apple ever ships first-party MCP support, the adapter can become another client of
the same capabilities without moving business logic.

**Status.** Proposed.

## ADR-INT-008 — In-process capability calls by default, MCP parity in CI

**Context.** The backend LLM needs the same facts. Calling its own MCP server over HTTP adds a hop, a
token and a second failure mode inside the same process boundary; skipping MCP entirely risks the two
paths drifting.

**Decision.** Define one `IntelligenceClient` protocol with `InProcessClient` (default) and
`MCPClient` (official Python client). Production server-side narration uses in-process. The
conformance and evaluation suites run the same scenarios through both and require identical
envelopes.

**Consequences.** No duplicated logic and no unnecessary network hop; MCP is still exercised on every
CI run and by external hosts. If the MCP server is ever deployed on another machine, the client
choice becomes a configuration flag.

**Status.** Proposed.

## ADR-INT-009 — `get_programme_block_summary` is a derived reporting window

**Context.** `DEC-PROGRAMME-01` states there is no fixed programme block and progression is
continuous; `DEC-W7-01` states there is no planned-session calendar. There is no block table, no
block identity and no block dates beyond the erector-ramp anchor in `athlete_profile.block_start_date`.
The candidate tool name implies a stored entity.

**Decision.** Keep the familiar name for catalogue discoverability, define it as a **reporting window**
of 4, 6 or 8 weeks ending at `as_of`, and require the limitation text in every response. Do not
invent a block id, block dates or a planned-session denominator.

**Alternatives considered.**

- *Rename to `get_programme_window_summary`.* Clearer, but "programme block" is the owner's
  vocabulary and renaming adds churn. The limitation text carries the precision.
- *Introduce a block entity.* Out of scope: a schema change, a new lifecycle and a training-policy
  decision that this workstream must not make.

**Consequences.** The tool answers "how is this stretch of the programme going?" without implying a
stored block. Any future block entity would extend the capability, not invalidate it.

**Status.** Proposed. **Open question:** owner preference on the name.

## ADR-INT-010 — No intelligence cache in INT-1 or INT-2

**Context.** Caching is the usual first optimisation. Here the correctness risk is high: an envelope
that mixes pre- and post-write state would lie about a week, and the invalidation key would need every
table and config revision. The database is local and small, and the heaviest calls are on demand.

**Decision.** No cache. Every call reads the current database inside one transaction, with the
existing `PRAGMA data_version` + `total_changes` stamp recorded in `provenance`. If measured p95
exceeds the agreed threshold (proposed 300 ms for overview, 800 ms for VBT), add an in-process cache
keyed on the full stamp plus capability, validated arguments and builder version — never a
cross-request cache that ignores writes.

**Consequences.** Predictable correctness; latency measured before it is optimised. The envelope
already exposes the revision, so a future cache is auditable.

**Addendum — deployment-host measurement and options (2026-11-14).** The trigger is met. On the
deployment-class host (Linux aarch64, 4 cores, Python 3.13.5, local SQLite) the synthetic baseline
at the real history size measured **p50 3,101.9 ms / p95 3,169.4 ms / max 3,284.2 ms** over 20
runs (377 sessions, 6,786 sets, 6.5 MB), all `status: ok`. The development Mac measured 220 ms
p50 at 200 sessions and 573 ms at 600, so this is host speed, not dataset size.

**Profiling result (2026-11-14, same host; detail in the backend
[`INTELLIGENCE-IMPLEMENTATION.md`](https://github.com/georgesdib/strength-training-app/blob/llm-integration/docs/INTELLIGENCE-IMPLEMENTATION.md) §18).**
The cost is **not** dominated by the performance ratio. Of the 3,110 ms warm request:
`deload.decision` 2,021 ms (65%) — `RuleContext.from_store` 1,349 ms building the whole-history
frame, plus 689 ms evaluating all five rules to read one verdict — and
`progress.dashboard` 1,050 ms (34%), of which `performance_points` is 507 ms (16%) and the
all-history set load 221 ms. The e1RM/ratio rebuild hypothesis is confirmed but secondary.

A broader response is proposed separately: a versioned, rebuildable derived-analytics layer
(per-set, session/exercise and weekly materialisation owned by the existing modules, with
on-demand fallback), documented in the backend
[`DERIVED-ANALYTICS-ARCHITECTURE.md`](https://github.com/georgesdib/strength-training-app/blob/llm-integration/docs/design/DERIVED-ANALYTICS-ARCHITECTURE.md).
It is not an in-process cache, is not implemented, and does not change the decision recorded here.

| Option | What changes | Gains | Costs / risks |
|---|---|---|---|
| **A. Bound the deload context** | Pass a `start` (≈12 weeks) to `RuleContext.from_store` in `reactive_reason` | 1,349 → 209 ms for the context; deload path 1,976 → ~260 ms | **Behavioural**: the verdict's weekly-cost details shrink (109 → 13 weeks); the last-two-week decision is unchanged on the fixture, but this needs an explicit decision and tests |
| **B. Evaluate one rule** — **implemented 2026-11-14** | `evaluate(..., rule_ids=("PRG-SPINE-001",))` in `reactive_reason` | Measured: deload 2,021 → 1,696 ms; request p50 3,102 → **2,730 ms** (−12%); identical verdict details (tests) | None identified; semantics preserved |
| **C. Bounded lookback for the ratio** | Cap the history `performance_points` rebuilds, or materialise per-session e1RM | ~0.5 s | **Metric definition change**; historical comparability, decision record, Phase 5A care |
| **D. In-process cache keyed on the full stamp** | Cache by `data_version` + `total_changes` + capability + args + builder version | Helps repeated reads only | Cold call unchanged; memory; config revisions in the key |
| **E. Do not enable the transport on this host** | Keep web/CLI only | Zero risk | INT-1 cannot ship on the target hardware |

**Recommendation.** **B is done** (measured −12%, no metric change). Next is **A**, which still
needs the behavioural decision on the verdict's weekly-cost details and the history horizon; after
A, re-measure before considering **C** (metric change) and then **D** (cache). Never choose **E**
silently.

**Status.** Proposed, partly implemented: **B implemented 2026-11-14**. Options **A**, **C**, **D**
and **E** are outstanding, and the trigger is still met — 2,730 ms p50 remains above the
one-second gate, so the MCP transport stays disabled on the deployment host.

## ADR-INT-011 — Stable App Intents now; Siri AI Developer Preview excluded

**Context.** iOS 27.3 beta introduces a Siri AI Developer Preview (custom actions and content,
skills, onscreen awareness). Apple states the App Intents API "may change" and that the preview is not
available to external testers or to App Store builds; it is also unavailable in the EU. Stable App
Intents, App Entities, App Schemas, App Shortcuts and Shortcuts actions have existed for years.

**Decision.** Implement read-only App Intents and App Shortcuts for overview, progression and weekly
review (INT-7). Do not adopt the Siri AI Developer Preview, app skills, onscreen entity donation or
conversational Siri. Do not make any shipped path depend on a point-release beta.

**Consequences.** Siri works today through existing App Intents and Shortcuts. When Apple ships the
preview generally, adopting it is additive: the intents already exist and need schema adoption, not a
rewrite.

**Status.** Proposed.

## ADR-INT-012 — Retire the minimal LLM selector before INT-5

**Context.** `DEC-LLM-14` already retires `agents/selection.py` as Phase 1b. INT-5 adds a
second model surface. Leaving the old chooser alive means three model paths (chooser, proposal,
narrative) with different privacy and validation rules.

**Decision.** Run Phase 1b before or alongside INT-5. It is **not** a prerequisite for INT-1 to INT-4,
because those phases add no model call. INT-5 must not begin while the selector is still reachable
from the UI, CLI or API.

**Consequences.** Sequencing only; the selector's deterministic engine and comparability rules remain
untouched. If the owner prefers, INT-5 can be deferred until after Phase 1b without blocking the
read-only workstream.

**Status.** Proposed.

## ADR-INT-013 — This plan supersedes the earlier LLM and Apple Intelligence forward plans

**Context.** Three documents described overlapping future work: `strength-training-app/docs/LLM-INTEGRATION-PLAN.md`
(analyst, explainer, constrained proposer, context builder, MCP as a conditional Iteration-2
candidate), `ROADMAP.md` §4.24 (the same workstream in status form) and
`docs/plans/IOS-CLIENT-PLAN.md` §5 (Apple Intelligence and PCC as unscheduled optional enhancements).
Keeping four forward descriptions means four sets of phases, statuses and acceptance criteria that
drift the moment one changes. Two of the old items are still binding: the outbound-data inventory and
the evaluation gates, plus the minimal-selector retirement.

**Decision.** The Training Intelligence plan is the single forward plan for training intelligence. It
supersedes the forward-planning content listed in its §16.2 — the analyst/explainer boundaries, the
shared context/evidence layer and its `agents/context.py` path, the MCP Iteration-2 candidate, phases
1–3, and the Apple Intelligence/PCC bullets. The superseded documents are **retained, not deleted**, as
historical and requirements records for the items that remain in force (§16.3): `DEC-LLM-01` to
`DEC-LLM-06`, the §8.1 outbound-data inventory, the §9 evaluation gates, the Phase 1b selector
retirement, and the constrained proposer (`DEC-LLM-09`), which is **deferred/unscheduled** rather than
dropped.

**Alternatives considered.**

- *Delete or blank the old plan.* Rejected: it is the requirements record for the proposer, the
  privacy inventory and the evaluation gates, and the repository rule prohibits dropping content from
  a rewrite.
- *Leave everything live and add a cross-reference.* Rejected: that is the current state, and it is
  what causes the drift the owner asked to remove.
- *Fold the constrained proposer into this plan.* Rejected: it is a write capability with its own
  approval gates; mixing it into a read-only plan would weaken both boundaries.

**Consequences.** One plan, one phase list, one status source for intelligence. Any new LLM or
Apple-platform proposal amends this plan and adds an ADR. The proposer is explicitly unscheduled, so
it cannot be started by momentum. The supersession is recorded in the backend Superseded table for
`DEC-LLM-12` and `DEC-LLM-13` (item 7), and as a status banner in the LLM plan itself.

**Status.** Proposed; takes effect on owner approval of this plan. **Open question:** confirm that the
constrained proposer should be deferred/unscheduled rather than kept as a parallel workstream.

## Rejected architectural alternatives (summary)

| Alternative | Why rejected |
|---|---|
| A fourth repository for the MCP server | duplication or release coupling; no compelling reason |
| MCP inside the existing web server | couples the AI surface to the unauthenticated UI; no independent deploy |
| A generic SQL / table / "query the database" tool | violates the read-only fact contract and invites injection and schema coupling |
| Write-capable intelligence tools | out of scope permanently for this workstream |
| Server LLM as an MCP tool | blurs fact and prose; adds cost and non-determinism to the tool layer |
| MCP client inside the iOS app | no Apple support, Tier-3 SDK, duplicate auth, no benefit |
| Vector database / RAG | structured rows, small corpus; exact lookup wins |
| Agent framework / autonomous loop | no demonstrated need; the plan is bounded tool calls |
| New tables for intelligence output | the trace tables suffice; output is an event, not an artifact |
| Confidence scores | the system cannot justify them; gate, n, comparability and coverage are honest |
| Multi-tenancy now | no user model exists; per-user auth is a separate, larger workstream |

## Unresolved questions requiring owner input

1. Which MCP host is the first target? It decides whether static bearer auth (ADR-INT-004) is
   sufficient for INT-1 acceptance.
2. Accept the capability-layer path change from `agents/context.py` to
   `strength_coach/intelligence/` (ADR-INT-002)?
3. Approve `get_programme_block_summary` as a derived window, or prefer a different name
   (ADR-INT-009)?
4. Should the Weekly Review ever appear in the web UI, or stay iPhone + MCP (INT-3 scope)?
5. Approve the additive `/api/ios/v1/intelligence/` routes at INT-3, or require a different facade?
6. Is a server-side narration path (INT-5) wanted at all, given on-device narration (INT-4) may be
   sufficient for one athlete?
7. Should INT-8 (controlled plan review) be closed now rather than left gated?
8. Confirm the deferral of the constrained proposer (`DEC-LLM-09`) that ADR-INT-013 records, or
   keep it as a parallel unscheduled workstream.

## Related

- [Training Intelligence plan](../plans/TRAINING-INTELLIGENCE.md)
- [Implementation audit](../plans/TRAINING-INTELLIGENCE-AUDIT.md)
- [Training Intelligence contract](../contracts/TRAINING-INTELLIGENCE-CONTRACT.md)
- [Backend decisions](https://github.com/georgesdib/strength-training-app/blob/development/docs/DECISIONS.md)
- [Documentation ownership](../DOCUMENTATION.md)
