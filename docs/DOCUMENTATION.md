# Documentation architecture and ownership

The portfolio repository (`georgesdib/strength-app`) is the canonical source of truth for documentation whose requirements, plans, decisions or contracts span repositories. The backend (`georgesdib/strength-training-app`) and iOS/watchOS client (`georgesdib/StrengthApp`) remain the canonical homes for implementation-coupled documentation and operational details belonging only to that component.

## Repository responsibilities

| Content | Canonical owner | Examples |
|---|---|---|
| Overall cross-repository plans, phase roadmaps, shared feature specifications, project architecture, decisions affecting multiple components, server/client contracts, integration requirements, shared acceptance rules, shared operational/data-management policies, agent task routing and handoff | Portfolio | `docs/plans/`, `docs/contracts/`, `docs/decisions/`, `docs/specifications/`, `docs/operations/`, `docs/agent/`, this policy |
| Python implementation architecture, backend API reference, schemas and migration details, config formats, backend-only tests, server operations and code-coupled user guides | Backend | `AGENTS.md`, `ROADMAP.md` for live backend implementation status, `docs/API.md`, `docs/DATA-MODEL.md`, `docs/design/` implementation materials, manifest/viewer docs |
| Swift architecture, Xcode/build/test procedures, UI implementation, live-test setup, Apple platform details and physical-device acceptance evidence | iOS/watchOS | `AGENTS.md`, `README.md`, `docs/AGENT-*.md`, `USER-GUIDE.md`, `DEVICE-ACCEPTANCE.md`, watch-specific implementation docs |

## Canonical shared sources

- [`docs/README.md`](README.md) is the navigation index.
- [`docs/plans/README.md`](plans/README.md) is the portfolio-level plan and roadmap locator. It links the backend implementation roadmap without duplicating it because that file is consumed by backend tests and the docs viewer.
- [`docs/plans/IOS-CLIENT-PLAN.md`](plans/IOS-CLIENT-PLAN.md) is the canonical cross-repository iOS phase plan.
- [`docs/contracts/README.md`](contracts/README.md) indexes the canonical server/client phase contracts.
- `docs/agent/` is the source for shared task routing, prompts and machine handoff. Machine-only private instructions remain untracked and local.

A component roadmap may remain local only when it is specifically the component's implementation-status authority and is coupled to that component's code, tests or tools. The backend `ROADMAP.md` is such an exception; it is not a second cross-repository roadmap. Portfolio documents must link to it rather than restating its active phase status.

## Documentation change rules

1. Every shared project plan, shared specification and cross-repository contract has one canonical file in the portfolio repository. Component repositories may retain short compatibility pointers, never a second full copy.
2. Backend-specific implementation documentation, Python architecture, API implementation detail, schema/migration detail, backend-only testing and operational procedures stay in the backend repository.
3. iOS/watchOS implementation documentation, Swift architecture, Xcode instructions, Apple testing and device acceptance remain in the client repository.
4. Do not copy shared documents between repositories or create parallel roadmaps/plans. Link to the canonical document; use a pointer only where a stable old path is needed by a manifest, viewer, script, test or historical external link.
5. If implementation invalidates a shared plan, contract, acceptance criterion or cross-repository requirement, update the canonical portfolio document. Update component-specific docs when only local implementation changes.
6. Cross-repository tasks review relevant portfolio plans/contracts before implementation and update all affected repositories' references. Shared-doc changes are committed in the portfolio branch; implementation changes are committed in their owning component branches.
7. Keep active, completed, superseded, historical and unknown status explicit. Preserve phase numbers, dependencies, acceptance criteria, caveats and completion evidence. Never infer completion from source code or branch existence alone.
8. A superseded document must name and link its replacement. A compatibility pointer must say it is not authoritative and must not repeat substantive content.
9. Update links in Markdown, READMEs, agent prompts, manifests, tests, source comments, scripts and workflows when a path changes. Do not change application behavior or CI behavior merely to accommodate documentation.
10. Keep submodule boundaries and Git safety: inspect status, fetch before branch changes, use separate task branches, do not force-push, and do not update portfolio submodule pointers unless the task explicitly requires it.
11. Never publish private machine notes, credentials, health data, training exports, databases, generated artifacts or ignored local files.

## Link and status conventions

- Relative Markdown links are for files inside the same repository only.
- Cross-repository documentation links must use absolute GitHub URLs to the canonical path and the intended stable integration branch. The PR sequence must merge the portfolio canonical docs before component pointers that refer to them.
- In the current backend docs viewer, local pointer paths and manifest entries remain where needed for compatibility. They resolve to a concise link to the portfolio canonical source.
- The plan/index page is not a second roadmap: it locates authoritative status sources and must not restate their changing status tables.
