# Strength App portfolio — agent instructions

This workspace is the portfolio repository. It contains two application
repositories as Git submodules:

- `strength-training-app/` — Python strength-coach server.
- `StrengthApp/` — SwiftUI iOS client.

The portfolio repository owns cross-repository process documentation only. Application code,
tests and subject-matter documentation are committed in their owning submodule.

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

Documentation has one canonical home. Before adding or moving a document, read
`docs/DOCUMENTATION.md` and use this summary:

| Content | Repository |
|---|---|
| Training methodology, readiness, prescriptions, data model, server API, server web UI, server design contracts | `strength-training-app/` |
| iOS client plan, iPhone user guide, device acceptance, client build/test guidance | `StrengthApp/` |
| Portfolio routing, machine prompts, handoff protocol, documentation policy | this repository |

The server owns the client/server contract because Python is authoritative for training
decisions. iOS documents link to the server contract instead of duplicating it. The iOS client
plan lives in `StrengthApp/`, not in the server docs index.

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
