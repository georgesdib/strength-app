# Agent documentation

Read [../../AGENTS.md](../../AGENTS.md) first. This directory holds the portfolio-level routing,
execution and handoff instructions; repository-specific instructions live in each submodule's
`AGENTS.md`.

## Choose one execution prompt

| Task | Load |
|---|---|
| Default / unclear | [PROMPT-DEFAULT.md](PROMPT-DEFAULT.md) |
| Server-only | [PROMPT-SERVER-ONLY.md](PROMPT-SERVER-ONLY.md) |
| iOS-only | [PROMPT-IOS-ONLY.md](PROMPT-IOS-ONLY.md) |
| Cross-repo | [PROMPT-CROSS-REPO.md](PROMPT-CROSS-REPO.md) |
| Working on the iMac coding host | [PROMPT-IMAC.md](PROMPT-IMAC.md) |
| Working on the MacBook for Apple acceptance | [PROMPT-MACBOOK.md](PROMPT-MACBOOK.md) |

Do not load a prompt that does not match the task. Use [TASK-ROUTING.md](TASK-ROUTING.md) to
classify the task first.

## Machine-prompt status

- [PROMPT-ODROID.md](PROMPT-ODROID.md) is retained as a **superseded historical pointer**, not a usable coding workflow. ODROID-C4 is the deployed server/benchmarking host.

## Process documents

- [TASK-ROUTING.md](TASK-ROUTING.md) — server-only, iOS-only, cross-repo or default.
- [MACHINE-HANDOFF.md](MACHINE-HANDOFF.md) — branch/commit handoff between the iMac and MacBook.
- [../DOCUMENTATION.md](../DOCUMENTATION.md) — which repository owns which documentation.

## Machine-local instructions

`AGENTS.machine.md` at the portfolio root is optional, local and git-ignored. It supplements
the committed instructions and must not override security, architecture, data invariants, CI or
approval requirements.

## Shared plans and contracts

Use the [portfolio documentation index](../README.md), [plans index](../plans/README.md), and [contract index](../contracts/README.md) as the project-wide sources of truth.
