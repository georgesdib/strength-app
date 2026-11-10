# iMac coding-agent workflow

This prompt applies when operating in the persistent iMac environment.

## Environment

- The iMac is the always-on remote coding environment.
- It may run a backend development server for implementation checks.
- The deployed server is an ODROID-C4 and is the host used for benchmarking. Do not treat the
  iMac as the deployed host or use iMac timing as evidence about deployed performance.
- It is not the Apple development workstation.
- Do not assume Xcode, iOS simulators, or physical Apple devices are
  available.
- The MacBook may be offline or asleep.

Load the local `AGENTS.machine.md` if available. It contains machine-specific
tooling and session instructions.

## Operating model

1. Work from the portfolio root unless a repository-specific task requires
   otherwise.
2. Classify the task using `docs/agent/TASK-ROUTING.md`.
3. Read only the matching task prompt and relevant repository instructions.
4. Inspect Git status and submodule state before editing.
5. Work in the relevant submodule repository, not in the portfolio repository.
6. Implement the smallest coherent change.
7. Run focused local tests and available quality checks.
8. Report the commit SHA, CI state, and outstanding acceptance requirements.

## Validation

- Backend: run focused Python tests and relevant quality checks.
- iOS: run available Swift package tests and other non-Xcode checks.
- Cross-repository: verify both sides of the relevant contract.
- Treat GitHub Actions as the authoritative automated validation.
- Never claim an iOS/watchOS simulator or physical-device test passed if it
  was not actually performed.

## Apple acceptance

When a change requires Xcode, simulator, iPhone, or Apple Watch testing:

- Complete all available implementation and automated validation first.
- Identify the exact branch and commit requiring acceptance.
- Specify the relevant scheme, test, or acceptance scenario.
- Hand off to the MacBook using `docs/agent/MACHINE-HANDOFF.md`.
- Do not mark device acceptance complete until results are reported.

## Git safety

- Never overwrite another machine's unpushed work.
- Fetch before modifying an existing remote task branch.
- Do not force-push.
- Do not commit credentials, private data, databases, exports, or generated
  build artefacts.
- Do not update portfolio submodule pointers during ordinary implementation.

## Completion report

Return:

- Repository and branch.
- Commit SHA.
- Changed files.
- Tests and quality checks performed.
- CI status or link if available.
- Device acceptance required or completed.
- Next action, if any.