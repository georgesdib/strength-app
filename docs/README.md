# Strength App portfolio documentation

The portfolio repository is the canonical home for shared project documentation across the backend and iOS/watchOS repositories. Start here, then open the authoritative shared plan or contract; implementation-specific instructions remain in their component repository.

## Project plans and roadmap

- [Plans and roadmap navigation](plans/README.md) — authoritative entry point; identifies the active shared plan and links to the backend implementation-status roadmap without duplicating it.
- [Canonical iOS client phase plan](plans/IOS-CLIENT-PLAN.md) — phases, architecture, dependencies, acceptance, rollback gates and retained completion history.
- [Athlete Feedback & Coaching (AFC) plan](plans/AFC.md) — canonical cross-repository plan for post-workout evaluation and feedback: evidence contract, AFC-2 (completed), AFC-2i native report, AFC-3 observations, AFC-4 nudges and the gated AFC-5.
- [Training Intelligence plan](plans/TRAINING-INTELLIGENCE.md) — canonical cross-repository plan for the read-only intelligence capability layer, the standalone MCP server, the iOS Foundation Models adapters and phases INT-1 to INT-8. It **supersedes the forward-planning content** of the backend LLM integration plan and the Apple Intelligence/PCC items in the iOS client plan; the retained constraints are listed in its §16. Its [implementation audit](plans/TRAINING-INTELLIGENCE-AUDIT.md) records the verified starting state.

## Contracts and specifications

- [Server/client contract index](contracts/README.md) — canonical iOS phase/R7/R8/watchOS contracts and the Training Intelligence MCP/envelope contract. Backend implementation is in `strength-training-app`; client implementation and Apple acceptance are in `StrengthApp`.
- [Training Intelligence contract](contracts/TRAINING-INTELLIGENCE-CONTRACT.md) — response envelope, evidence rules, MCP tool/resource catalogue, error semantics, limits and the iOS native adapter contract.
- [Training Intelligence architecture decision records](decisions/TRAINING-INTELLIGENCE-ADR.md) — cross-repository decisions ADR-INT-001 to ADR-INT-013 with alternatives and unresolved questions.
- Project-wide architecture/decision/specification/operations categories should be added here only when a canonical document is established; do not create a competing copy of component-coupled implementation docs.

## Agent instructions

- [Portfolio `AGENTS.md`](../AGENTS.md) — entry point for project-wide and cross-repository work.
- [Documentation architecture and ownership](DOCUMENTATION.md) — canonical ownership, change rules, and link conventions.
- [Agent documentation index](agent/README.md) — task routing, execution prompts and machine-specific workflows.
- [Task routing](agent/TASK-ROUTING.md) — classify server-only, iOS-only, cross-repository and documentation-only tasks.
- [Machine handoff](agent/MACHINE-HANDOFF.md) — branch, commit and acceptance handoff rules.

## Component implementation documentation

- [Backend documentation index](https://github.com/georgesdib/strength-training-app/blob/development/docs/README.md) — backend implementation docs and its manifest-backed viewer. Its `ROADMAP.md` remains the backend implementation status authority.
- [iOS/watchOS documentation index](https://github.com/georgesdib/StrengthApp/blob/development/docs/README.md) — client-specific build, test, UI and Apple acceptance documentation.

## Documentation tooling

- [Combined documentation PDF](DOCUMENTATION-PDF.md) — build one repository-labelled PDF from the portfolio, backend and iOS documentation.
- [`scripts/docs_pdf.py`](../scripts/docs_pdf.py) — canonical cross-repository PDF builder; supports `--list`, repository filters, private-note inclusion and a configurable output path.

## Status labels and history

Shared plans identify active, completed, superseded, historical and unknown material. Completed phases remain linked as historical evidence. Component implementation status must be read from its authoritative component roadmap/acceptance record; this index deliberately does not reproduce changing status tables.
