
# Cross-repo DSH task prompt

This is a cross-repo contract change.

Server repository: `strength-training-app/`
iOS client repository: `StrengthApp/`

## Before implementation

1. Identify the authoritative side: server or client.
2. Read the relevant server contract document and iOS contract/document.
3. Identify every affected route, request/response field, error code,
   authentication rule, client model, decoder, and test.
4. Produce a compatibility matrix before editing.
5. For migrations, API/schema contracts, security-sensitive changes or architectural
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
