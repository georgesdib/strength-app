# TRAINING INTELLIGENCE — ARCHITECTURE DECISION RECORDS

**Status:** every record is accepted, deferred, withdrawn or superseded as of 2026-11-24. ADR-INT-001
to ADR-INT-021 are implemented, retained, deferred or withdrawn as recorded: ADR-INT-015 (INT-4c) and
ADR-INT-021 (INT-12) were withdrawn on 2026-11-24, and ADR-INT-016 is accepted as recorded.
ADR-INT-011 and ADR-INT-018 are accepted (ADR-INT-011 amended with the refreshed Siri AI preview facts
and the INT-7 readiness requirement; ADR-INT-018 covers the workout lifecycle surfaces and is extended
by decision 16 for the Shortcuts start/finish pair), and ADR-INT-017 is accepted. ADR-INT-019
(INT-10, the local daily reminder nudge) is accepted 2026-11-16, as are ADR-INT-020 (INT-11, Explain the
System) and ADR-INT-022 (INT-13, the Today summary card); ADR-INT-021 (INT-12, web search and RAG) was
**withdrawn on 2026-11-24** at the owner's request. The one open item is INT-9's adoption pass, which
needs a new ADR once iOS 27.3 lands.
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

**Status.** **Accepted 2026-11-15** (plan §13, decision 1); implemented as the separately
deployable `strength-intelligence-mcp` entry point in this repository.

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

**Status.** **Accepted 2026-11-15** (decision 2). The capability layer lives in
`strength_coach/intelligence/`, so the open question is resolved.

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

**Status.** **Accepted 2026-11-15** (decision 3).

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
layer is unaffected. The host question was answered on 2026-11-15: the Python client is the only
MCP host, so the static token is sufficient for INT-1 acceptance.

**Status.** **Accepted 2026-11-15** (decision 4); OAuth remains a later decision if a hosted client
or a non-owner user is added.

## ADR-INT-005 — Tools and resources only; no MCP prompts

**Context.** MCP offers prompts as server-authored templates. The server is meant to expose training
facts; the prompt that frames a conversation belongs to the host (Claude, the app, the CLI), which
also owns model selection and UX.

**Decision.** Advertise `tools` and `resources`. Do not advertise `prompts`, `logging`,
`sampling`, `roots` or subscriptions. Do not implement elicitation or tasks.

**Consequences.** The server stays deterministic and model-agnostic; prompt versioning lives in
`intelligence/model/` or in the app. A host that wants a review prompt writes one; nothing in the
server needs to know.

**Status.** **Accepted 2026-11-15** (decision 5).

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

**Status.** **Accepted 2026-11-15** (decision 6).

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

**Status.** **Accepted 2026-11-15** (decision 7); implemented as INT-3.

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

**Status.** **Accepted 2026-11-15** (decision 8).

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

**Status.** **Accepted 2026-11-15** (decision 9). The name stays
`get_programme_block_summary`; it is a reporting window with the mandatory limitation, so the open
question is resolved.

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
[`INTELLIGENCE-IMPLEMENTATION.md`](https://github.com/georgesdib/strength-training-app/blob/development/docs/INTELLIGENCE-IMPLEMENTATION.md) §18).**
The cost is **not** dominated by the performance ratio. Of the 3,110 ms warm request:
`deload.decision` 2,021 ms (65%) — `RuleContext.from_store` 1,349 ms building the whole-history
frame, plus 689 ms evaluating all five rules to read one verdict — and
`progress.dashboard` 1,050 ms (34%), of which `performance_points` is 507 ms (16%) and the
all-history set load 221 ms. The e1RM/ratio rebuild hypothesis is confirmed but secondary.

A broader response is proposed separately: a versioned, rebuildable derived-analytics layer
(per-set, session/exercise and weekly materialisation owned by the existing modules, with
on-demand fallback), documented in the backend
[`DERIVED-ANALYTICS-ARCHITECTURE.md`](https://github.com/georgesdib/strength-training-app/blob/development/docs/design/DERIVED-ANALYTICS-ARCHITECTURE.md).
It is not an in-process cache and does not change the decision recorded here. **Milestone A**
(revision ledger, build state, coordinator and safe publication) is implemented and audited, and
**Milestone B** (core per-set/session materialisation and progress/strength-trend migration) and
**Milestone C** (weekly spinal exposures; deload, outcomes and monitoring migration) are implemented
2026-11-14. Snapshots remain optional and deferred.

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

**HTTP measurement after the T-3 first pass (2026-11-14).** Real MCP transport on the ODROID
against a fresh production copy, core family ready, 30 requests and 5 warm-ups: HTTP p95 672 ms
(overview), 278 ms (programme), 377 ms (readiness), 5,684 ms (session details), 45-189 ms for the
fast tools. Under the accepted T-1 budget (fast <= 500 ms, slow/very_slow <= 7 s) all tools fit.
**T-3 first pass closed 2026-11-14**; session details remains the one very_slow capability and is
tracked as optional follow-up **T-3a**.

**T-1 decision — accepted latency budget (2026-11-14).** The owner accepts a latency-aware full
catalogue rather than the original blanket one-second gate: fast capabilities target p95 ≤ 500 ms;
slow and very_slow capabilities target p95 ≤ 7 s, are callable without a hard latency rejection,
and carry measured-latency guidance in their tool descriptions. The server tool timeout is 20 s.
Measured p95 values are historical benchmarks, not guarantees. Repeated costly calls are
discouraged in the descriptions; correctness must never be traded for latency. The transport is
enabled on the trusted LAN with the full ten-tool catalogue; T-3 remains the optimisation and
remeasurement work. Option **E** (do not enable) is rejected for now.

**Status.** **Accepted and closed 2026-11-14.** The transport is enabled with a full catalogue
(installed as a systemd unit on the ODROID on 2026-11-15, with host-specific paths). T-3's first pass is
closed; options A, C and D remain future optimisations and T-3a is the optional session-details
follow-up. B and C are implemented.

## ADR-INT-011 — Stable App Intents now; Siri AI Developer Preview excluded

**Context.** iOS 27.3 beta introduces a Siri AI Developer Preview (custom actions and content,
skills, onscreen awareness). Apple states the App Intents API "may change" and that the preview is not
available to external testers or to App Store builds; it is also unavailable in the EU. Stable App
Intents, App Entities, App Schemas, App Shortcuts and Shortcuts actions have existed for years.

**Decision.** Implement read-only App Intents and App Shortcuts for overview, progression and weekly
review (INT-7). Do not adopt the Siri AI Developer Preview, app skills, onscreen entity donation or
conversational Siri. Do not make any shipped path depend on a point-release beta.

**Consequences.** Siri works today through existing App Intents and Shortcuts. When Apple ships the
preview generally, adoption is additive, but **not** by schema adoption: there is no health or fitness
app-schema domain, so the intents stay custom and become tools with `@AppIntent(.tool)`, optionally
guided by a `Skills.skillsbundle`. The metadata, indexing and snippet readiness in plan §7.6 is what
keeps that cheap.

**Status.** **Accepted 2026-11-15** (decisions 11 and 14).

**Amendment 2026-11-15 — access opened to all developers; readiness, not adoption.**

*What changed.* Apple opened the Siri AI Developer Preview to every developer in the iOS/iPadOS/
macOS/visionOS **27.3** betas (developer beta 2026-11-03; Apple news post). Two statements above are
now imprecise and are corrected here:

1. The preview is no longer limited to internal builds. Any developer can build an integration —
   but it still cannot be distributed: not to external TestFlight testers, not to App Store builds,
   with App Store submission opening in spring 2027.
2. Adoption is not "schema adoption". Apple publishes no health or fitness app-schema domain, so a
   strength-training app's actions are custom intents annotated `@AppIntent(.tool)`, with an optional
   one-per-target `Skills.skillsbundle` whose skills are `SKILL.md` files (YAML `name` and
   `description`, then a Markdown body of at most 10,000 characters).

*What did not change.* The preview still "may change" during the beta; it remains unavailable in the
EU on iOS/iPadOS/watchOS; server-side Apple Intelligence features carry daily usage limits and
expanded access will be "for a fee" on unpublished terms; and **iOS 27.3 ships no Foundation Models
API change**, so the model surface in plan §7.2–§7.4 is untouched.

*Decision amended.* Keep the exclusion and add a readiness requirement to INT-7 (plan §7.6): complete
intent, parameter and entity-property `title`/`description` metadata; `IndexedEntity` (and
`IndexedEntityQuery` where needed) so Spotlight can find entities; snippet views that a `CardSnippet`
can later host; side-effect-free `perform()`; and no `Skills` bundle, tool annotation or other preview
symbol in any build before the adoption pass.

*Invariant.* An app skill is guidance to a model, never a specification: Apple states that skills
cannot enforce deterministic behaviour and that Siri does not perform the listed intents in order.
No skill file may therefore state a load, percentage, e1RM, RIR, set count, readiness verdict, gate or
prescription. Those stay server-computed, and any model text quotes the envelope.

*Adoption gate.* A later adoption needs: the preview shipped to customers, the App Store submission
open, Apple's published terms and a fee/quota position, a device spike (unlock behaviour of
`authenticationPolicy` included), and a new ADR that supersedes this amendment.

*Owner decision 2026-11-15 — distribution is not a constraint.* The owner does not ship on the App
Store and upgrades to iOS 27.3 as soon as it ships (about a month from 2026-11-15). Adoption therefore
happens on their own development-signed build at that point, not at App Store availability, and the
spring 2027 submission date is informational. **No compile gate, feature flag or dual code path is
built meanwhile**: INT-7 stays stable-only, and adoption is a single pass — raise the deployment
target to 27.3, or keep 27.0 and wrap the additions in `@available(iOS 27.3, *)`.

## ADR-INT-012 — Retire the minimal LLM selector before INT-5 (implemented 2026-11-15)

**Context.** `DEC-LLM-14` already retires `agents/selection.py` as Phase 1b. INT-5 adds a
second model surface. Leaving the old chooser alive means three model paths (chooser, proposal,
narrative) with different privacy and validation rules.

**Decision.** Run Phase 1b before or alongside INT-5. It is **not** a prerequisite for INT-1 to INT-4,
because those phases add no model call. INT-5 must not begin while the selector is still reachable
from the UI, CLI or API.

**Consequences.** Sequencing only; the selector's deterministic engine and comparability rules remain
untouched. If the owner prefers, INT-5 can be deferred until after Phase 1b without blocking the
read-only workstream.

**Status.** Accepted and implemented 2026-11-15 (Phase 1b).

## ADR-INT-013 — This plan supersedes the earlier LLM and Apple Intelligence forward plans

**Context.** Three documents described overlapping future work: `strength-training-app/docs/LLM-INTEGRATION-PLAN.md`
(analyst, explainer, constrained proposer, context builder, MCP as a conditional Iteration-2
candidate), `ROADMAP.md` §4.24 (the same workstream in status form) and
`docs/plans/IOS-CLIENT-PLAN.md` §5 (Apple Intelligence and PCC, then unscheduled optional enhancements; PCC was later withdrawn on 2026-11-24).
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

**Status.** **Accepted 2026-11-15** (decision 13); in force with this plan. The constrained proposer
was withdrawn on 2026-11-17, so the open question is resolved.

## ADR-INT-014 — Scoped MCP tokens for sensitive readiness (retained, not adopted 2026-11-15)

**Status.** Retained 2026-11-15; not adopted. Raw readiness values stay local-only over MCP and the
deployment switch `allow_sensitive_readiness` remains the only deliberate escape hatch. No
health-scoped token, auth change or contract revision is planned.

**Context.** Every MCP token currently carries the same access. The readiness tool can return raw
subjective fields (sleep, energy, mood, stress, soreness) and measured fields (HRV, RHR, bodyweight,
fat percentage) alongside the canonical score. Once a host has the token it can request them, and
the server cannot see what the host does with the values. A per-call "consent" flag would not be
consent, because the model client sets it.

**Proposal (not adopted).** Give each MCP token a scope set when it is minted:

- `intelligence.read` (default) — every training fact and the readiness score;
- `intelligence.health` — adds raw readiness fields.

The scope is stored beside the token hash, checked in `authenticate_bearer`, carried on the
`Principal`, and enforced at the dispatch boundary before the capability runs. The CLI gains
`--scope`; `allow_sensitive_readiness` is then removed or kept only as a local-development
override. Existing tokens migrate to `intelligence.read`.

**Alternatives.** Keep the deployment-wide switch (coarse: every client gets the same access);
per-call flag (not enforceable as consent); field-tiering (the audit treats subjective fields as
sensitive too, so it does not satisfy the requirement).

**Consequences.** One token-store migration, a contract revision for the readiness `fields` rule,
auth and dispatch tests, and no envelope change. The weekly review is unaffected because it exposes
coverage and direction only.

**Owner decision (2026-11-15).** Keep as is: no health-scoped token; raw readiness stays local-only
permanently unless a new decision reopens it.

## ADR-INT-015 — User-selectable Private Cloud Compute model (withdrawn 2026-11-24)

**Status.** Deferred 2026-11-15; **withdrawn on 2026-11-24 at the owner's request.** PCC will not be
integrated: no entitlement is sought, no picker is added, no Private Cloud path exists, and the
earlier scope is not planned work.

**Context (historical).** INT-4 and INT-4b run entirely on the device. A user choice between
on-device and Apple Private Cloud Compute was considered; the Foundation Models framework exposes
`PrivateCloudComputeLanguageModel` on iOS 27, but Apple requires the managed entitlement
`com.apple.developer.private-cloud-compute` and eligibility approval.

**Decision.** Withdrawn. The app stays on-device (Apple Foundation Models) or, in Chat only, on the
DeepSeek key path (`ADR-INT-016`). No third model, no cloud fallback and no model picker.
Reintroducing PCC needs a new owner request and a new ADR.

## ADR-INT-016 — External chat model via a user API key (DeepSeek, accepted 2026-11-15)

**Context.** PCC is unavailable and was withdrawn on 2026-11-24 (`ADR-INT-015`); it needed a paid
Apple Developer Program membership and the managed entitlement. The owner wants the option to use
another model with their own API key, specifically DeepSeek, and has clarified that it applies to
**Chat only** — the weekly and overview explanations stay on-device. DeepSeek exposes an OpenAI-compatible `/chat/completions` API with tool calls.

**Decision.** Add INT-4d: a Settings **Chat model** choice, On-device (default) or DeepSeek. With
DeepSeek selected, the iPhone calls `https://api.deepseek.com` directly using `deepseek-chat` and
the user's key, stored in the Keychain. The adapter uses a tool loop over the same five read-only
capabilities, non-streaming, with the existing sources line and soft number verification. No backend
proxy; no explanations; no other task.

**Privacy.** One-line disclosure that DeepSeek receives the question and training facts and that the
key is stored on the iPhone. The key is not logged, not in UserDefaults, not in iCloud Keychain and
not in the repository. **No silent fallback** to on-device, because that would change the data
boundary. On-device remains the default and is unaffected.

**Consequences.** An OpenAI-compatible client, a tool-call loop, Keychain storage, key validation,
error mapping (401/429/5xx/transport/malformed) and a mocked-HTTP test suite. No server deployment.
A model id that cannot call tools is refused for chat. The external model cannot be used for
explanations, weekly review, MCP or server narration.

**Status.** Accepted 2026-11-15; implemented as INT-4d and confirmed on the iPhone with a real key.

## ADR-INT-017 — Plan-aware chat and suggestions (accepted 2026-11-15)

**Context.** Chat exposed only the five explanatory capabilities. The owner wants the current
prescription, programme state and adherence available to chat, including on-device, and wants the
model to suggest changes — including medical considerations — with no refusal guard. The backend
capabilities were MCP-only, so three iOS REST routes were added.

**Decision.** INT-4e adds a default-off plan-data toggle to chat and three read-only tools:
@@prescription@@ (date/id/current), @@programme_summary@@ and @@adherence@@. The same tools are
registered for on-device and DeepSeek. The model returns a structured answer plus a separate
@@suggestions@@ list. Suggestions render in a labelled “Suggestion — not applied. Not medical
advice.” block; they are proposals, are exempt from data grounding, and are never applied. The
factual answer keeps soft number verification. No write path exists.

**Capacity.** The device probe reported 8,192 tokens with tool calling and guided generation; eight
tools plus four history messages and 60 fact lines passed. A context overflow still falls back to
the base tools.

**Consequences.** Three additive backend routes, three tools per chat provider, a structured answer
type, suggestion UI, plan-tool tests and a device matrix. The deterministic engine remains the only
source of prescriptions.

**Status.** Accepted 2026-11-15; implemented, device test pending.

## ADR-INT-018 — Workout lifecycle surfaces: Action button, HomeKit scenes and Shortcuts (accepted 2026-11-15)

**Context.** The owner wants local automations around the existing session lifecycle: a HomeKit scene
and a user-defined Shortcut when a workout starts, and another pair when it ends, on either phone or
watch; and Action-button support on Apple Watch Ultra for starting and ending a workout. The plan's §1.2 originally excluded
"workout-execution changes", which would have made this feature look like a boundary violation. On
2026-11-15 the owner **removed that exclusion** rather than accept a carve-out, and replaced it with an
explicit entry-point boundary: lifecycle intents are in scope, but they call the existing operations
and do not redefine them.

**Decision.** Add INT-7b as a local surface layer, not an intelligence capability:

- `StartWorkoutIntent` in the watch app (`title`, `suggestedWorkouts`, `workoutStyle` over an
  `AppEnum`, `displayRepresentation`, `perform()`), which registers the app under
  Settings > Action button > Workout. The system allows 30 seconds to start an `HKWorkoutSession`
  and return success, and the intent must be compiled into the watch app, never an
  `AppIntentsExtension`.
- An end `AppIntent` **donated as the Action button's next action** while the session is active.
  Apple defines no `EndWorkoutIntent` protocol; the next action is a single slot, replaced by each
  new donation, so the donation state must follow the session state.
- Two user-selected HomeKit scenes executed by the device that owns the session through
  `HMHomeManager` and `HMHome.executeActionSet(_:completionHandler:)` (iOS 8+/watchOS 2+), gated by
  the `com.apple.developer.homekit` entitlement and `NSHomeKitUsageDescription`.
- Two optional user-selected **Shortcuts**, one per event, run by the phone via
  `shortcuts://run-shortcut?name=…&input=text&text=…`. Phone-only by construction (`UIApplication` does
  not exist on watchOS), best-effort (the system gives no completion signal), fired **after** the scene
  because it foregrounds the Shortcuts app, and never given training data unless the owner opts in.
- **Boundary.** These intents call the existing start and finish operations. They do not change how a
  session is executed, validated or recorded, compute nothing, and add no server call, MCP tool, model
  call or envelope field.

**Alternatives rejected.** (1) HomeKit's own automation engine: its triggers are accessory-, time- and
people-based, not "a third-party app started a workout". (2) A server-side automation: HomeKit lives on
the phone and watch, the server cannot reach it, and it would put physical-home control behind a
network token. (3) A user-built Shortcut: possible today, but the device token sits in an editable
shortcut and there is no Action-button start. (4) Mapping `PauseWorkoutIntent`/`ResumeWorkoutIntent`
onto the rest timer: a rest timer is not a pause; refused, and the owner confirmed the exclusion on
2026-11-15. (5) `RunSystemShortcutIntent`
(iOS 27): widget-only, and Apple states it provides no functionality in other contexts. (6) Running a
shortcut from app code through App Intents: no such API exists; the supported direction is the user's
shortcut calling the app's intent, not the app pushing into Shortcuts.

**Consequences.** A HomeKit entitlement and usage string; a scene picker and executor; a shortcut-name
field that cannot be validated (no API enumerates shortcuts) plus percent-encoding and a warning that
the app cannot confirm the shortcut ran; a donation state machine; failure isolation so a HomeKit or
Shortcut error never blocks, delays or rolls back the training record; acceptance on phone-only,
watch-only and both, including the rule that exactly one device executes the scenes for a given
session and that the Shortcut channel is unavailable when the watch owns the session. The HomeKit and
Shortcut mappings stay on the device and never enter the repository, the server, the envelopes or a
prompt. A device check is needed for the watch case, where the home must
be reachable through the user's iCloud home sharing.

**Security.** Scenes can unlock doors, so: explicit opt-in, one scene per event, selection only from the
user's HomeKit list, no Siri- or model-supplied scene name, no execution from a stale donation, and no
scene/home/accessory identifier in any log sent off the device. A Shortcut is arbitrary automation run
with the user's own authority: it is opt-in, named by the user, given no training data unless the owner
opts in to a fixed string, and never verified or retried.

**Status.** **Accepted 2026-11-15** (decision 15), after the §1.2 exclusion was removed at the owner's
request. The owner confirmed that `PauseWorkoutIntent`/`ResumeWorkoutIntent` stay excluded and that the
device owning the session executes the scenes exactly once. Delivered and closed in this order after
INT-7: 7b-1 executor and Shortcuts, 7b-2 HomeKit scenes, 7b-3 Action button and watch Siri.

**Extension 2026-11-15 — decision 16, Shortcuts start/finish.** The Shortcuts app gains a
`StartWorkoutShortcutIntent` and a `FinishWorkoutShortcutIntent` on the phone, and reuses the watch's
two Action-button intents. Start behaves exactly like the Action button: a ready plan starts and the app
lands on the active workout; with nothing requested it says so and opens the app. Finish never finishes
anything — it opens the surface where sRPE is recorded (the phone's active workout, the watch's finish
sheet), matching the Action button's second press. No entitlement, server change or new training path;
the §1.2 boundary is unchanged. Closed, owner-confirmed 2026-11-15.

## ADR-INT-019 — Local daily reminder nudge (accepted 2026-11-16)

**Context.** The app only exists when the athlete opens it. The one step that actually gates progress is
readiness entry — without it the server refuses to issue a prescription — so the natural prompt is a
message at a chosen time of day that names something concrete from the training record and asks for
readiness. On 2026-11-16 the owner asked for exactly that and answered the four decisions that shape
it: (a) content computed when the app was last active is acceptable, so no remote push is needed;
(b) on-device only, no external model; (c) silent when the day is already trained; (d) one time of day.
The plan's §1.2 excluded "notification intelligence" wholesale, which would have made this look like a
boundary violation, so the exclusion is narrowed instead of carved around.

**Decision.** Add INT-10 as a local client-side surface, not an intelligence capability and not a
server feature:

- **Precompute, then schedule.** iOS freezes a local notification's content at scheduling time. The app
  therefore renders the message while it is in the foreground and schedules one-shot
  `UNCalendarNotificationTrigger`s (local hour and minute, so DST and time-zone changes follow the
  device) over a bounded horizon, re-arming by cancel-all-then-rebuild on activation, readiness
  submission, workout end, configuration change and pairing change. A repeating trigger is rejected: it
  would freeze one body forever.
- **On-device only.** The message is rendered by a dedicated two-field on-device shape that reuses the
  narrative path's availability handling over facts the app already holds — `TodayResponse` plus the
  issued plan. No capability is fetched for the reminder. The DeepSeek path is unreachable from this
  code path by construction, and the withdrawn PCC path (`ADR-INT-015`) does not exist: the scheduler
  is wired to the on-device generator and offers no provider choice.
- **Numbers are allowed (owner decision, 2026-11-16).** The reminder enforces only length. An
  encouragement is not an explanation, and a numeral in a nudge — "five minutes", "two sets" — is not
  a training claim; the strict `NarrativeValidator` grounding check stays on the weekly review and
  overview surfaces where a number *is* a claim. The first device run showed why the distinction
  matters: readiness facts contain no numbers at all, so a model that wrote "5 minutes" failed
  grounding and the template always shipped.
- **Template is a first-class outcome.** When the model is unavailable, Apple Intelligence is off, the
  device is ineligible or validation fails, a deterministic fact-derived message ships instead. This is
  the opposite of a silent cloud fallback: there is nowhere to fall back to.
- **Silence.** A day whose session is already recorded gets no nudge, and the pending request is dropped
  at workout end. Known residual gap: a watch-only session the phone never observes cannot suppress the
  same day, because suppressing at delivery time requires remote push.
- **Tap routing.** The notification opens the app on Today, or presents the readiness form when readiness
  is missing, and offers one action that logs readiness directly.

**Alternatives rejected.** (1) APNs push from the home server at the configured time: fresher content
and correct suppression, but it needs an Apple push key, a device-token registry, a scheduler and a
running home server at delivery time — a new service and new personal data for a reminder. (2)
`BGAppRefreshTask` to render shortly before the time: opportunistic by contract, so it can silently
fail, and the fallback would be the same precomputed text anyway. (3) A Notification Service Extension:
only runs for a push, so it presupposes (1). (4) A server-side scheduler without push: cannot deliver
anything. (5) A repeating daily trigger with a fixed body: one string forever, which defeats the point
of naming a fact. (6) A second model surface with provider choice: the reminder is unattended, so
sending training data to a third party while the owner is not looking is a different consent posture
from the interactive chat; refused.

**Consequences.** A scheduler, a settings section, a shared notification-authorization helper with the
existing rest-end notifications, a small nudge context in `StrengthCore`, one new `@Generable` output
shape and a deterministic template, plus tab-selection and pending-route plumbing for the tap. No
server change, no contract field, no schema change, no entitlement. Staleness is bounded by "since the
app was last opened", which is acceptable because that is when the facts were true; if the app is never
opened again, the horizon's final message is intentionally generic rather than a stale specific claim.

**Security.** No credential, endpoint or egress path is added. The rendered body may name a movement, a
load or a readiness fact the athlete already sees in the app, and never a symptom, a note, a clinical
detail or a verdict, because it is written for a Lock Screen. The configured time and the message stay
on the device and never enter the repository, the server, an envelope or a prompt contract.

**Status.** **Accepted 2026-11-16** (decision 17), at the owner's request, after §1.2 was narrowed from
"notification/Live-Activity intelligence" to Live Activities only. Implemented 2026-11-16 on the iOS
client (`StrengthApp`, development branch) with automated tests passing. The remaining physical-device
checks were waived by the owner on 2026-11-18, so the item is closed; it shipped in StrengthApp v1.2
on 2026-11-18. iOS-only, no backend or contract change. No question from this decision remains
open.

## ADR-INT-020 — Explain the System: local knowledge retrieval (accepted 2026-11-16)

**Status.** Accepted 2026-11-16 at the owner's request for personal use; implemented and closed
2026-11-16 with documented limitations. The allowlist, chunker, incremental FTS5 index, knowledge CLI,
retrieval, citation check, explain/status endpoints, background startup indexing and web/iOS tabs are
in place. Hardening followed the audit: raw questions are not stored, rejected files are purged,
citations are repository-qualified, sources are marked untrusted, and every source is reported by
status.

**Context.** The shipped chat answers from a fixed training-data dossier. The owner wants questions
about how the system works — readiness calculation, injury-deload evidence, code behaviour — answered
from the project's docs and source. The corpus is local and versioned; internet access is explicitly
out of scope. The owner accepts stale docs/code, imperfect retrieval and best-effort citations, and
permits private personal notes and data as long as secrets are excluded. The external DeepSeek model will see the
retrieved snippets.

**Decision.** Add a separate Explain surface, web and iOS, backed by:

- a local SQLite FTS5 index over an explicit named allowlist with regex rules;
- portfolio docs, plans, ADRs, contracts, rules and both source trees, including test source unless
  removed by a separate test exclusion list (tests are not individually allowlisted); fixtures,
  snapshots, generated output and test data are always excluded;
- all non-secret private notes and personal data under private/, including reviews, baselines,
  evidence and athlete-state files; private/eval/ test data is excluded; credential/key/token
  patterns and known secret files are denied;
- path normalisation, traversal and symlink-escape rejection;
- incremental indexing on server start using path, size, mtime, SHA-256 and a commit stamp, with a
  background build and an index-readiness state;
- one read-only explanation endpoint, top chunks plus bounded query expansion, and a PROJECT SOURCES
  prompt block; test-derived claims are labelled as test expectations, distinct from implementation
  facts;
- path:line or section citations opened in the system browser: docs through the existing docs viewer,
  code through the GitHub blob at the indexed commit with a line anchor; if unavailable, copyable
  path:line text and no navigation;
- a minimal citation sanity check: path exists and is allowlisted, line range is inside the file, and
  a quoted snippet roughly overlaps the cited lines; failures are surfaced as unverified, not silently
  passed;
- no web search, arbitrary URL fetch, vector embeddings, model-run shell commands, code execution or
  writes.

**Consequences.** No training rule, envelope, MCP tool or existing API contract changes. The index is
local, untracked and owner-readable only. iOS needs the paired server and is offline otherwise.
Private permitted text, including personal details, is sent to DeepSeek; secrets filtering is
best-effort and reviewed by the allowlist. INT-11 is single-question; session-only follow-up context
was withdrawn with INT-12. Retrieval quality, substantive citation accuracy and staleness are
accepted as personal-use risks, not release gates; only the structural citation sanity check above is
enforced.

**Rejected alternatives.** Web search/browsing now (separate, higher-risk proposal); unrestricted
filesystem access (secrets and traversal); vector RAG before keyword retrieval is measured; bundling
the docs in the iOS app (size, staleness, secret risk); strict citation validation as a release gate
(owner accepts best-effort).

## ADR-INT-021 — Web search and RAG (withdrawn 2026-11-24)

**Status.** Deferred 2026-11-16; **withdrawn on 2026-11-24 at the owner's request.** Not approved,
not implemented, not scheduled and no longer planned. The provider, quota, privacy, SSRF, query
retention, page-fetch and citation-evaluation questions are closed with it.

**Context (historical).** INT-11 provides single-question local docs/code explanation. A later step
for web search, session-only follow-up context and retrieval-augmented generation was considered and
deferred on 2026-11-16; the owner has since declined that direction entirely.

**Decision.** No web search, browsing, URL fetch, web citation or retrieval-augmented generation is
approved or planned. The MCP server stays transport and facts-only, INT-11 stays a local keyword/FTS5
explainer, and no component reads external content. Reintroducing any of it needs a new owner request
and a new ADR.

**Consequences.** No code, provider key, endpoint, network policy, MCP tool or contract change was
ever made, and none is expected.

## ADR-INT-022 — Today summary card (accepted 2026-11-16)

**Context.** The owner asked for a short block at the top of Today: one informative passage summarising
where they stand and one motivational passage, written by the configured agent — on the device or
DeepSeek. INT-4d had limited DeepSeek to Chat and the reasoning surfaces had stayed on-device, so this
needed a decision rather than a quiet extension. The first device run of INT-10 had also shown how much
the wording depends on the fact package, which argued for one explicit card with a visible source
instead of another silent surface.

**Decision.** Add INT-13 as a client-side presentation surface:

- **Facts:** the Today payload (readiness), the issued plan, and the server's compact four-week
  overview projection when reachable. No new endpoint, capability or schema field; offline the card is
  written from local facts.
- **One generation, two passages,** validated for length and emptiness only. Numbers are allowed,
  consistent with decision 17: this is encouragement over facts, not an explanation, and the strict
  number-grounding check stays on the weekly review and overview surfaces.
- **The model is the chat model choice.** No separate picker, no silent fallback: a DeepSeek selection
  without a key reports that, and an unavailable on-device model reports why. The footer names the
  model, so the athlete can see when the wording came from off the device.
- **Consent:** the DeepSeek path sends readiness and the overview facts on load; plan details are
  included only while the chat "Include plan and prescription data" toggle is on.
- **Cost:** one generation per (day, readiness answer, issued plan, model). A manual **Refresh**
  regenerates, and a Settings toggle removes the block entirely.

**Alternatives rejected.** (1) A second model picker for the card: two choices to keep in sync and two
consent stories. (2) Silent fallback to the on-device model when DeepSeek fails: it would hide that the
words came from a different model than the one chosen. (3) Generating on every Today appearance: a model
call per tab switch on a screen that is opened all day. (4) Folding the summary into the reminder: the
reminder is precomputed and silent-tested, the card is on demand and visible. (5) Sending the plan with
the plan toggle off: that toggle is where plan disclosure was consented.

**Consequences.** One card, one view model, two generators and a Settings toggle. No server, contract or
schema change. The text is displayed and never stored as a prescription, session or measurement. The
cost is one model call per state change; the worst failure is a card that says why it could not be
written.

**Security.** DeepSeek receives readiness and four-week facts only after the athlete selects it for
chat; plan detail additionally requires the plan toggle. The footer is the disclosure. The API key still
comes from the Keychain, and nothing is logged off the device beyond what the provider request itself
carries.

**Status.** **Accepted 2026-11-16** (decision 20) at the owner's request, amending INT-4d's chat-only
boundary for this surface only. Implemented 2026-11-16 on the iOS client. **Closed 2026-11-17** by
owner decision: the physical-device acceptance was waived rather than run. The card shipped in
StrengthApp v1.2 on 2026-11-18.

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
| APNs push for a daily reminder | a push key, token registry, scheduler and a live home server at delivery time — infrastructure for a reminder (ADR-INT-019) |
| Background refresh to render the reminder on time | opportunistic by contract; would silently fail and fall back to the same precomputed text |
| Unrestricted filesystem/RAG-for-everything explainer | secrets, traversal and a much larger index; ADR-INT-020 uses a named local allowlist |
| Web search or RAG in the same slice as INT-11 | different provider, privacy, SSRF and evaluation risks; ADR-INT-021 withdrew them on 2026-11-24 |

## Questions resolved by delivery (2026-11-15)

All of these were answered by the shipped work; none is open.

1. **MCP host:** the Python client only. The static bearer token is sufficient (ADR-INT-004); no OAuth
   server, accounts or tenancy were built.
2. **Capability-layer path:** accepted and delivered as `strength_coach/intelligence/` (ADR-INT-002).
3. **`get_programme_block_summary`:** delivered as the derived reporting window (ADR-INT-009).
4. **Weekly Review on the web UI:** delivered — the web UI has the review panel and the
   `/api/ios/v1/intelligence/weekly-review` route.
5. **Additive intelligence routes:** approved and delivered at INT-3.
6. **Server-side narration:** delivered at INT-5, alongside on-device narration.
7. **INT-8:** closed 2026-11-15 with no scope; read-only explanation is covered by the weekly review,
   overview and INT-5.
8. **Constrained proposer (`DEC-LLM-09`):** deferred/unscheduled, as ADR-INT-013 records; it needs its
   own gated plan.
9. **Siri AI adoption (INT-9):** the only remaining question — it needs a new ADR once iOS 27.3 lands.
   The readiness work is already delivered under ADR-INT-011's amendment.

## Related

- [Training Intelligence plan](../plans/TRAINING-INTELLIGENCE.md)
- [Implementation audit](../plans/TRAINING-INTELLIGENCE-AUDIT.md)
- [Training Intelligence contract](../contracts/TRAINING-INTELLIGENCE-CONTRACT.md)
- [Backend decisions](https://github.com/georgesdib/strength-training-app/blob/development/docs/DECISIONS.md)
- [Documentation ownership](../DOCUMENTATION.md)
