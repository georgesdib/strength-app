
# Cross-repo DSH task prompt

This is a cross-repo contract change.

Server repository: `strength-training-app/`
iOS client repository: `StrengthApp/`

## Before implementation

1. Identify the authoritative side: server or client.
2. Read and update the canonical shared plan/contracts in the portfolio `docs/plans/` and `docs/contracts/`; keep API implementation, data-model implementation, migrations and code-specific detail in `strength-training-app/`, and Apple implementation/acceptance detail in `StrengthApp/`. Link across repositories with absolute GitHub URLs.
3. Read the relevant server contract document and iOS contract/document.
4. Identify every affected route, request/response field, error code,
   authentication rule, client model, decoder, and test.
5. Produce a compatibility matrix before editing.
6. For migrations, API/schema contracts, security-sensitive changes or architectural
   refactors, wait for approval before editing. Otherwise proceed after the plan.

## Compatibility matrix

| Area | Server change | iOS change | Compatibility | Tests |
|---|---|---|---|---|
| Route |  |  |  |  |
| Request schema |  |  |  |  |
| Response schema |  |  |  |  |
| Error contract |  |  |  |  |
| Authentication |  |  |  |  |
| Offline replay |  |  |  |  |

## Token rules

- Read only the contract documents and directly affected files.
- Do not read `ROADMAP.md`, `CHANGELOG.md`, logs, exports, databases, build
  outputs, or unrelated documentation.
- Do not paste full test, build, or log output into context.
- Use focused tests first.
- Summarise failures rather than returning raw output.

## Invariants

- Python remains authoritative for readiness, prescriptions, loads, sets, and
  training decisions.
- The iOS client must not define training policy or compute training decisions.
- Preserve bearer authentication, idempotency keys, offline journal/replay
  semantics, and server-origin restrictions.
- Preserve append-only records and migration compatibility.

## Completion format

- Server files changed
- iOS files changed
- Tests run and concise results
- Compatibility assessment
- Documentation updates required
- Deployment/rollback considerations
- Suggested commit messages for each repository

## Shared documentation architecture (required)

Before implementing a task that touches shared requirements or crosses repositories, read the canonical portfolio index at https://github.com/georgesdib/strength-app/blob/main/docs/README.md and ownership rules at https://github.com/georgesdib/strength-app/blob/main/docs/DOCUMENTATION.md. Locate cross-repository phase plans under `docs/plans/` and contracts under `docs/contracts/`; do not rely on a duplicated plan inside a submodule or on a portfolio submodule being initialized.

Classify work as backend-only, iOS/watchOS-only, or cross-repository. Commit implementation-specific changes only in the owning component repository. Commit shared plans/specifications/contracts/architecture/decisions and project-wide agent instructions only in the portfolio repository. For a cross-repository task, update the canonical portfolio document plus affected component docs/references in separate coordinated branches and link to the canonical source; do not update submodule pointers unless explicitly required. Keep local compatibility pointers short and non-authoritative. Preserve completed/historical status and never infer phase completion.
