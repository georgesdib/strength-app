# Strength App portfolio — agent instructions

This workspace is the portfolio repository. It contains two application
repositories as Git submodules:

- `strength-training-app/` — Python strength-coach server.
- `StrengthApp/` — SwiftUI iOS client.

The portfolio repository is the canonical source of truth for shared project-wide documentation: cross-repository roadmaps/plans, specifications, architecture, server/client contracts, multi-component decisions, shared acceptance/operations policy, and agent routing. Application code and implementation-coupled documentation remain in their owning component repository. See `docs/README.md` and `docs/DOCUMENTATION.md`.

## Task routing

Before doing substantive work, classify the task:

1. **Server-only** — changes only `strength-training-app/`.
2. **iOS-only** — changes only `StrengthApp/`.
3. **Cross-repo** — changes the server/iOS API contract, shared schema,
   authentication, client/server behaviour, or both repositories.

Read `docs/agent/TASK-ROUTING.md` before choosing an execution prompt.

Use the matching prompt file:

| Task type | Prompt file |
|---|---|
| Default / unclear | `docs/agent/PROMPT-DEFAULT.md` |
| Server-only | `docs/agent/PROMPT-SERVER-ONLY.md` |
| iOS-only | `docs/agent/PROMPT-IOS-ONLY.md` |
| Cross-repo | `docs/agent/PROMPT-CROSS-REPO.md` |

Do not load a prompt file that does not match the task.

## Documentation placement

Documentation has one canonical home. Before adding, moving, or updating shared documentation, read
`docs/DOCUMENTATION.md` and the relevant index/plan/contract. Use this summary:

| Content | Repository |
|---|---|
| Cross-repository plans/specifications, shared architecture, server/client contracts, shared policy/acceptance/operations and agent workflows | this repository (`docs/plans/`, `docs/contracts/`, `docs/agent/`) |
| Python architecture, API implementation, schema/migrations, backend-only tests, server UI and backend operational procedures | `strength-training-app/` |
| Swift/Xcode architecture, client UI, build/test/live-test guidance and Apple device acceptance | `StrengthApp/` |

Python remains authoritative for training decisions and server behavior; the portfolio owns canonical cross-repository contract documents, while server implementation and API reference remain in the backend. The shared iOS client phase plan lives in portfolio `docs/plans/`; client-specific procedures remain in `StrengthApp/`. Components use short pointers/links, not duplicate shared documents.

## Non-negotiable rules

- Python remains authoritative for readiness, prescriptions, loads, sets, and
  training decisions.
- The iOS client may display, capture, cache, and replay data, but must not
  define training policy or compute training decisions.
- Preserve append-only records, migration compatibility, and existing test
  conventions.
- Never commit or transmit `data/`, `private/`, credentials, API keys, pairing
  tokens, personal health data, or real training exports.
- Never run destructive database, Git, filesystem, or deployment commands without
  explicit approval.
- Do not expose the server publicly; it is intended for the trusted home network.


If task classification is ambiguous, or the change could affect migrations,
append-only history, authentication, data deletion, deployment, or the
server/iOS contract, stop and ask one concise clarifying question before
reading further or editing.

## Output discipline

Never paste full test, build, install, log, database, or command output into
context.

On failure, return only:

1. Pass/fail summary.
2. Failing test or command.
3. Assertion/error message.
4. Relevant traceback or log excerpt, maximum 40 lines.
5. Most likely cause.
6. Minimal next diagnostic command.

Use targeted searches and small file excerpts. Do not read `ROADMAP.md`,
`CHANGELOG.md`, large documentation, logs, exports, lockfiles, build artefacts,
or SQLite databases unless essential.

## Session boundaries

- Prefer one coherent task per session.
- Do not begin an unrelated task in the same session.
- Before implementation of a migration, API contract change, security-sensitive
  change, or architectural refactor, produce a plan and wait for approval.
- Before completion, run only the appropriate final verification command.

## Machine-specific instructions

This repository supports two development environments:

- **iMac** — persistent remote coding-agent environment. Load
  `docs/agent/PROMPT-IMAC.md`.
- **MacBook** — local Apple development and physical-device acceptance environment. Load
  `docs/agent/PROMPT-MACBOOK.md`.

The deployed server is an ODROID-C4 and is the host used for benchmarking. It is the server
host, not the coding host; do not confuse it with the iMac. Server documentation may refer to
the ODROID-C4 without implying that agents run there.

At the start of a task, load the machine-specific instructions if available:

- `AGENTS.machine.md` at the repository root.

This file is intentionally local, uncommitted, and ignored by Git. It
supplements but does not override this committed `AGENTS.md`.

If the local file is absent, follow the shared instructions, the machine prompt above and the
appropriate task-routing prompt.

Machine-specific instructions may define:

- Local tooling and available hardware.
- Machine-specific build and test commands.
- Git handoff procedures.
- Local acceptance responsibilities.

They must not override:

- Repository security requirements.
- Architecture and data invariants.
- Required CI checks.
- Approval requirements for migrations, contracts, or architectural changes.

## Git and submodule boundaries

The portfolio repository contains the server and iOS repositories as Git
submodules.

- Code changes must be committed in the relevant submodule repository.
- Never assume a submodule commit is published merely because it exists locally.
- Never automatically update the portfolio repository's submodule pointers
  as part of ordinary feature implementation.
- Update submodule pointers only when explicitly requested as a portfolio
  consolidation task.
- Never discard submodule changes or reset a submodule without approval.

## Development handoff

Use GitHub as the source of truth for handoff between development machines.

- Push task branches and commits before handing work to another machine.
- Identify the repository, branch, and commit SHA in every handoff.
- Never hand off uncommitted work as if it were available remotely.
- Before modifying a task branch, fetch and inspect its latest remote state.
- Do not force-push or overwrite commits from another machine.
- Report tests performed and tests still outstanding.
- Follow `docs/agent/MACHINE-HANDOFF.md` for machine transitions.


## Shared documentation change management

- Read shared plans/specifications/contracts in this portfolio before cross-repository implementation. Use the portfolio docs index even when the submodules are uninitialized or the task starts from a component checkout.
- Shared documentation changes are committed in the portfolio repository. Backend/iOS implementation details remain in the component repository; a cross-repo change may require separate commits and coordinated PRs in all affected repositories.
- Do not create parallel roadmaps or copies of shared plans/contracts. Use a short pointer only when an existing local path must remain for a manifest, viewer, script, test or compatibility.
- When implementation invalidates a shared requirement or contract, update its portfolio canonical document and all component links. For a purely local implementation change, update only the owning component documentation.
- Preserve active/completed/superseded/historical/unknown status, phase numbering, dependencies, acceptance evidence and caveats. Never claim completion without evidence.
- Keep backend `ROADMAP.md` as the backend live implementation-status authority because its docs viewer and consistency tests consume it; portfolio plans link to it without duplicating its status.
- Shared docs are committed only on an explicit task branch; fetch and inspect remotes first, never force-push, and do not change submodule pointers unless explicitly required.
