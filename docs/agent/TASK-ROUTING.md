# Task routing

Before choosing a workflow, classify the task.

## Server-only

Use when the change affects only:

- Python server code
- SQLite schema, migrations, repositories, or queries
- CLI commands
- web UI
- server tests
- server documentation

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
