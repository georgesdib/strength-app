
# iOS-only DSH task prompt

Work only within `StrengthApp/`.

Do not inspect or modify `strength-training-app/` unless explicitly instructed.

## Before implementation

1. Read the relevant sections of the iOS `AGENTS.md`.
2. Identify affected Swift files, views, models, networking, storage, and tests.
3. Identify any server contract assumptions that need verification.
4. Return a concise plan before editing.
5. For migrations, API/schema contracts, security-sensitive changes or architectural
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
