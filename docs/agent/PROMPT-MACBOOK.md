# MacBook development and acceptance workflow

This prompt applies when operating in the local MacBook environment.

## Environment

- The MacBook is the Apple development workstation.
- Xcode, iOS simulators, and physical Apple devices may be available.
- The iMac is the persistent remote coding environment.
- The ODROID-C4 hosts both the backend development server and backend main server and is used for
  benchmarking. It is not the Apple/Xcode workstation; verify which server context a task targets.
- Load the local `AGENTS.machine.md` if available.

## Operating model

1. Start from the portfolio root.
2. Classify the task using `docs/agent/TASK-ROUTING.md`.
3. Read the matching task prompt and repository instructions.
4. Inspect Git status and submodule state before editing.
5. Fetch and inspect the task branch from GitHub before accepting a handoff.
6. Never overwrite local changes or another machine's commits.
7. Use the appropriate submodule repository for code changes.

## Apple development

For iOS/watchOS work:

- Use Xcode for builds and simulator testing.
- Run focused tests before broader validation.
- Use physical iPhone/Apple Watch testing for acceptance scenarios that
  cannot be adequately validated in a simulator.
- Capture failures with concise reproduction steps and relevant diagnostics.
- Verify the exact commit being tested.
- Report acceptance results against the branch and commit SHA.

## Handoff back to iMac

When acceptance finds an issue:

- Prefer a concise reproduction report and let the iMac agent implement
  the correction.
- If fixing locally is more efficient, commit the fix to the same task
  branch and push it.
- Never leave a fix only on the MacBook if the iMac agent must continue.
- Report the new commit SHA and validation results.
- Do not merge a PR or declare acceptance complete unless the applicable
  checks and acceptance criteria are satisfied.

## Git safety

- Never force-push.
- Fetch before modifying remote branches.
- Do not reset or discard another machine's work.
- Do not update portfolio submodule pointers during ordinary feature work.
- Do not commit credentials, pairing tokens, private data, or generated
  build artefacts.

## Completion report

Return:

- Repository and branch.
- Exact commit tested.
- Xcode scheme and configuration.
- Simulator/device and OS version where relevant.
- Tests and acceptance scenarios performed.
- Pass/fail results and reproducible failures.
- Fixes committed and pushed.
- Outstanding acceptance items.

## Shared documentation architecture (required)

Before implementing a task that touches shared requirements or crosses repositories, read the canonical portfolio index at https://github.com/georgesdib/strength-app/blob/main/docs/README.md and ownership rules at https://github.com/georgesdib/strength-app/blob/main/docs/DOCUMENTATION.md. Locate cross-repository phase plans under `docs/plans/` and contracts under `docs/contracts/`; do not rely on a duplicated plan inside a submodule or on a portfolio submodule being initialized.

Classify work as backend-only, iOS/watchOS-only, or cross-repository. Commit implementation-specific changes only in the owning component repository. Commit shared plans/specifications/contracts/architecture/decisions and project-wide agent instructions only in the portfolio repository. For a cross-repository task, update the canonical portfolio document plus affected component docs/references in separate coordinated branches and link to the canonical source; do not update submodule pointers unless explicitly required. Keep local compatibility pointers short and non-authoritative. Preserve completed/historical status and never infer phase completion.
