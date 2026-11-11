# Strength App portfolio documentation

The portfolio repository is the canonical home for shared project documentation across the backend and iOS/watchOS repositories. Start here, then open the authoritative shared plan or contract; implementation-specific instructions remain in their component repository.

## Project plans and roadmap

- [Plans and roadmap navigation](plans/README.md) — authoritative entry point; identifies the active shared plan and links to the backend implementation-status roadmap without duplicating it.
- [Canonical iOS client phase plan](plans/IOS-CLIENT-PLAN.md) — phases, architecture, dependencies, acceptance, rollback gates and retained completion history.

## Contracts and specifications

- [Server/client contract index](contracts/README.md) — canonical iOS phase/R7/R8/watchOS contracts. Backend implementation is in `strength-training-app`; client implementation and Apple acceptance are in `StrengthApp`.
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

## Status labels and history

Shared plans identify active, completed, superseded, historical and unknown material. Completed phases remain linked as historical evidence. Component implementation status must be read from its authoritative component roadmap/acceptance record; this index deliberately does not reproduce changing status tables.
