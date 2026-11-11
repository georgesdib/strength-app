# Task routing

Before choosing a workflow, classify the task. For documentation-only work, decide the owning
repository with `docs/DOCUMENTATION.md`; a change that spans repositories follows the cross-repo
prompt for link and manifest verification even when no code changes.

## Shared documentation-only

Use when the task changes only cross-repository plans, specifications, architecture, contracts, project-wide policies, agent routing or documentation ownership. Work in the portfolio repository, read `docs/DOCUMENTATION.md`, preserve component implementation details in place, and update only the pointers/references genuinely affected. If implementation or tests change, use the server-only, iOS-only or cross-repo path as well.

## Server-only

Use when the change affects only:

- Python server code
- SQLite schema, migrations, repositories, or queries
- CLI commands
- web UI
- server tests
- backend-specific implementation documentation

Read and follow `docs/agent/PROMPT-SERVER-ONLY.md`.

Do not inspect `StrengthApp/` unless the task explicitly requires verifying a
client-facing contract.

## iOS-only

Use when the change affects only:

- SwiftUI views or navigation
- iOS models, decoding, networking, or local storage
- HealthKit integration
- iOS unit or UI tests
- iOS documentation

Read and follow `docs/agent/PROMPT-IOS-ONLY.md`.

Do not inspect `strength-training-app/` unless the task explicitly requires
verifying a server contract.

## Cross-repo

Use when the change affects:

- A server API route, request/response schema, error contract, authentication
  rule, or client-facing behaviour
- The iOS client’s models, decoding, requests, offline journal, or sync/replay
  behaviour
- Both repositories
- A shared contract document

Read and follow `docs/agent/PROMPT-CROSS-REPO.md`.

## Default

If the task is ambiguous, incomplete, or could affect either repository, read and
follow `docs/agent/PROMPT-DEFAULT.md`.

Do not guess. Ask one concise clarifying question if the distinction materially
changes the implementation.
