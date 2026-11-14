# Strength App portfolio

This workspace is the portfolio repository for the Strength App project. It contains
portfolio-wide agent and handoff instructions plus two Git submodules; it does not contain
application code of its own, but it does host project-wide tooling such as the combined
documentation PDF builder.

| Path | Repository | Role |
|---|---|---|
| `strength-training-app/` | [georgesdib/strength-training-app](https://github.com/georgesdib/strength-training-app) | Python strength-coach server, CLI, local web UI, SQLite data and training rules |
| `StrengthApp/` | [georgesdib/StrengthApp](https://github.com/georgesdib/StrengthApp) | SwiftUI iPhone client and its client-side documentation |

## Documentation map

| Repository | Owns |
|---|---|
| This repository | Portfolio overview, agent routing, machine prompts, handoff protocol, documentation-placement policy |
| `strength-training-app/` | Training methodology, readiness, prescriptions, data model, server API, server web UI, migrations and server design contracts (including the iOS API contracts) |
| `StrengthApp/` | iOS client plan, client architecture/UI notes, iPhone user guide, device acceptance and iOS agent guidance |

The authoritative server docs index is
[`strength-training-app/docs/README.md`](https://github.com/georgesdib/strength-training-app/blob/development/docs/README.md).
The authoritative iOS docs index is
[`StrengthApp/docs/README.md`](https://github.com/georgesdib/StrengthApp/blob/development/docs/README.md).

Start with [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md) when adding or moving documentation.
The rule is simple: one canonical copy, in the repository that owns the subject.

## Combined documentation PDF

[`scripts/docs_pdf.py`](scripts/docs_pdf.py) builds one PDF from the portfolio,
server and iOS documentation, grouped and labelled by repository. See
[docs/DOCUMENTATION-PDF.md](docs/DOCUMENTATION-PDF.md) for installation, usage
and privacy notes.

## Start here

- [AGENTS.md](AGENTS.md) — workspace-level instructions for coding agents.
- [docs/agent/README.md](docs/agent/README.md) — routing, execution prompts and machine handoff.
- [docs/agent/TASK-ROUTING.md](docs/agent/TASK-ROUTING.md) — classify a task before choosing a prompt.
- [docs/agent/MACHINE-HANDOFF.md](docs/agent/MACHINE-HANDOFF.md) — how work moves between the
  iMac coding host and the MacBook.
- [docs/README.md](docs/README.md) — index of the portfolio-level documentation.
- `AGENTS.machine.md` — optional local, git-ignored machine instructions (not committed).

## Clone and update

```bash
git clone --recurse-submodules git@github.com:georgesdib/strength-app.git strength-app
cd strength-app

# For an existing clone:
git submodule update --init --recursive
```

Do not commit or push portfolio submodule pointer changes as part of ordinary feature or
documentation work. Commit application changes in the repository that owns them; update the
portfolio pointers only when the owner explicitly asks for a portfolio consolidation.
