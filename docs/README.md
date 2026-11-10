# Portfolio documentation

Index of documentation that belongs to the portfolio itself, rather than to the server or iOS
client repository.

- [Documentation ownership and placement](DOCUMENTATION.md) — which repository owns which kind
  of document, and the move/cross-link rules.
- [Agent documentation](agent/README.md) — task routing, execution prompts and machine handoff.
- [Task routing](agent/TASK-ROUTING.md) — server-only, iOS-only, cross-repo or default.
- [Machine handoff](agent/MACHINE-HANDOFF.md) — branch/commit handoff between machines.

## Repository documentation

- Server docs index:
  [strength-training-app/docs/README.md](https://github.com/georgesdib/strength-training-app/blob/development/docs/README.md)
- iOS docs index:
  [StrengthApp/docs/README.md](https://github.com/georgesdib/StrengthApp/blob/development/docs/README.md)

## Machine naming

- **iMac** — the persistent remote coding-agent environment.
- **MacBook** — the local Apple development and physical-device acceptance environment.
- **ODROID-C4** — the deployed home server and benchmarking host. It is not the coding host;
  do not confuse it with the iMac. Server-specific references to the ODROID-C4 remain valid in
  the server repository.
