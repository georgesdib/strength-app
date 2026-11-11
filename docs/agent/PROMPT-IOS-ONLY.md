
# iOS-only DSH task prompt

For iOS/watchOS code or client-implementation-doc work, work only within `StrengthApp/`. If the task changes a shared plan, contract, policy or cross-repository agent instruction, reclassify it as cross-repo and make that shared-doc change in a separate portfolio task branch.

Do not inspect or modify `strength-training-app/` unless explicitly instructed.

## Before implementation

1. Read the relevant sections of the iOS `AGENTS.md`.
2. The shared iOS phase plan and server/client contracts are canonical in the portfolio docs. Keep client build, UI, live-test, user-guide and device-acceptance docs here; link to the portfolio plan/contracts and do not duplicate them. Read the portfolio `docs/DOCUMENTATION.md` when ownership is unclear.
3. Identify affected Swift files, views, models, networking, storage, and tests.
4. Identify any server contract assumptions that need verification.
5. Return a concise plan before editing.
6. For migrations, API/schema contracts, security-sensitive changes or architectural
   refactors, wait for approval before editing. Otherwise proceed after the plan.

## Plan format

- Relevant files and modules
- Existing behaviour and constraints
- Proposed implementation
- Exact build/test commands, narrowest first
- Contract assumptions requiring verification
- Files that will not be changed

## Token rules

- Do not read full Xcode build logs, DerivedData, simulator logs, device logs,
  lockfiles, or generated files unless essential.
- Use targeted searches and small excerpts.
- Do not paste full `xcodebuild` output into context.
- Run a focused test target or individual test first.
- On failure, report only failing tests, assertion messages, and relevant
  stack traces.

## Invariants

- The server is authoritative for readiness, prescriptions, loads, sets, and
  training decisions.
- Do not introduce client-side training policy or computation.
- Preserve Keychain token handling, idempotency keys, offline journal semantics,
  bounded retries, and server-origin restrictions.
- Do not commit pairing codes, tokens, live server URLs, or personal data.

## Test strategy

Start with a focused test target or individual test:

```bash
xcodebuild test \
  -project StrengthApp.xcodeproj \
  -scheme StrengthApp \
  -destination 'platform=iOS Simulator,id=<simulator-id>' \
  -only-testing:StrengthAppTests/RELEVANT_TEST_CLASS \
  2>&1 | tail -100
```

See StrengthApp/docs/AGENT-WORKFLOWS.md and AGENT-LIVE-TESTS.md for the
DEVELOPER_DIR, pseudo-terminal and disposable-server setup.

## Shared documentation architecture (required)

Before implementing a task that touches shared requirements or crosses repositories, read the canonical portfolio index at https://github.com/georgesdib/strength-app/blob/main/docs/README.md and ownership rules at https://github.com/georgesdib/strength-app/blob/main/docs/DOCUMENTATION.md. Locate cross-repository phase plans under `docs/plans/` and contracts under `docs/contracts/`; do not rely on a duplicated plan inside a submodule or on a portfolio submodule being initialized.

Classify work as backend-only, iOS/watchOS-only, or cross-repository. Commit implementation-specific changes only in the owning component repository. Commit shared plans/specifications/contracts/architecture/decisions and project-wide agent instructions only in the portfolio repository. For a cross-repository task, update the canonical portfolio document plus affected component docs/references in separate coordinated branches and link to the canonical source; do not update submodule pointers unless explicitly required. Keep local compatibility pointers short and non-authoritative. Preserve completed/historical status and never infer phase completion.
