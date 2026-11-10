# Strength App portfolio — agent instructions

This workspace contains two related repositories:

- `strength-training-app/` — Python strength-coach server.
- `StrengthApp/` — SwiftUI iOS client.

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
