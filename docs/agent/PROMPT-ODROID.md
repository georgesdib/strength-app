# ODROID backend development and server workflow

This prompt applies when operating in the persistent ODROID environment.

## Environment

- The ODROID-C4 hosts both the backend development server and the backend main server; it is also the hardware used for backend benchmarking.
- Treat development and main-server contexts as distinct targets even though they share the ODROID host. Verify the endpoint, configuration and data context before running checks or commands.
- The server role does not, by itself, determine where an agent session runs. Follow the active session and local machine instructions rather than inferring the coding host from the server role.
- The ODROID is not the Apple development workstation. Do not assume Xcode, iOS simulators or physical Apple devices are available.
- The MacBook may be offline or asleep.

Load the local `AGENTS.machine.md` if available. It contains machine-specific tooling and session instructions.

## Operating model

1. Work from the portfolio root unless a repository-specific task requires otherwise.
2. Classify the task using `docs/agent/TASK-ROUTING.md`.
3. Read only the matching task prompt and relevant repository instructions.
4. Inspect Git status and submodule state before editing.
5. Work in the relevant submodule repository for component implementation; make shared plans/contracts/policies in a separate portfolio branch.
6. Confirm whether a command targets the development server or backend main server. Do not run destructive tests, migrations, resets, or experiments against main-server data unless explicitly authorized.
7. Implement the smallest coherent change.
8. Run focused local tests and available quality checks.
9. Report the commit SHA, CI state, and outstanding acceptance requirements.

## Validation

- Backend: run focused Python tests and relevant quality checks against a development environment; do not treat a result against the main server as a disposable test.
- iOS: run available Swift package tests and other non-Xcode checks.
- Cross-repository: verify both sides of the relevant contract.
- Treat GitHub Actions as the authoritative automated validation.
- Never claim an iOS/watchOS simulator or physical-device test passed if it was not actually performed.

## Apple acceptance

When a change requires Xcode, simulator, iPhone, or Apple Watch testing:

- Complete all available implementation and automated validation first.
- Identify the exact branch and commit requiring acceptance.
- Specify the relevant scheme, test, or acceptance scenario.
- Do not mark device acceptance complete until results are reported.

## Git safety

- Never overwrite another machine's unpushed work.
- Fetch before modifying an existing remote task branch.
- Do not force-push.
- Do not commit credentials, private data, databases, exports, or generated build artefacts.
- Do not update portfolio submodule pointers during ordinary implementation.
- Do not edit deployed files or alter main-server configuration as a substitute for a reviewed source change.

## Deployment paths (verified 2026-11-17)

The service runs from a checkout at `/home/dsh/strength-app/strength-training-app` with its
virtualenv at `.venv/` inside it — **not** `/home/dsh/strength-training-app/`, which appears in
older unit comments and does not exist. Working directories, unit `ExecStart` lines and any
`systemctl` troubleshooting must use the real path or fail with `status=203/EXEC`.

| Item | Value |
|---|---|
| Portfolio checkout | `/home/dsh/strength-app` |
| Backend checkout | `/home/dsh/strength-app/strength-training-app` |
| Virtualenv | `/home/dsh/strength-app/strength-training-app/.venv/bin/python` |
| Database | `/home/dsh/strength-app/strength-training-app/data/coach.db` |
| Web unit | `strength-coach-web.service` (port 8000, home LAN only) |
| Cardio linker | `strength-cardio-link.timer`, every 10 min, `SuccessExitStatus=1` |

Run git and `systemctl` as `dsh` (`runuser -u dsh --`): the checkout is owned by that user, and git
refuses it as `root` with "dubious ownership".

## Completion report

Return:

- Repository and branch.
- Commit SHA.
- Changed files.
- Tests and quality checks performed.
- CI status or link if available.
- Device acceptance required or completed.
- Next action, if any.
