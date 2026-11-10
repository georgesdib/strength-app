# Machine handoff protocol

## Source of truth

GitHub is the source of truth for shared development work.

The handoff unit is:

- Repository.
- Task branch.
- Commit SHA.
- Acceptance or implementation report.

The iMac is the coding host. The ODROID-C4 is the deployed server and benchmarking host; it is
not a handoff endpoint and it is not where agents run.

Uncommitted work is not a valid remote handoff.

## iMac to MacBook

The iMac agent must:

1. Finish the current coherent implementation.
2. Run relevant local tests and quality checks.
3. Commit and push the task branch.
4. Confirm the remote branch contains the handoff commit.
5. Identify the exact commit requiring acceptance.
6. Report the acceptance instructions and outstanding checks.

The MacBook must:

1. Fetch the remote branch.
2. Verify the handoff commit.
3. Inspect the changes and relevant implementation.
4. Build/test in Xcode as applicable.
5. Perform requested simulator or physical-device acceptance.
6. Report results against the exact commit.

## MacBook to iMac

The MacBook must:

1. Push any fixes or acceptance findings that are committed.
2. Identify the latest remote commit.
3. Report any uncommitted work explicitly.
4. State whether acceptance passed, failed, or remains incomplete.

The iMac must:

1. Fetch the task branch.
2. Inspect changes since its last known commit.
3. Confirm the working tree is safe before editing.
4. Continue implementation or resolve acceptance findings.
5. Re-run affected tests and update the PR.

## Handoff report

Use this format:

### Handoff

- Repository:
- Branch:
- Commit SHA:
- Direction: iMac → MacBook / MacBook → iMac
- Task:

### Changes

- Summary:
- Relevant files:

### Validation

- Tests performed:
- CI status:
- Simulator/device acceptance:
- Outstanding checks:

### Next action

- Requested action:
- Known issues:
- Additional context:

## Branch and PR lifecycle

- Use one task branch per coherent task.
- Keep task branches in the relevant code repository.
- Do not merge directly to protected development branches.
- Use the repository's configured PR requirements.
- Do not merge while mandatory acceptance or CI checks are failing.
- Delete task branches only after the task is merged and no machine
  depends on them.

## Cross-repository changes

For backend/client contract changes:

- Keep implementation changes in their respective component repositories; keep shared plan/contract/policy updates in the portfolio repository.
- Record the portfolio, server and client branches/SHAs in the handoff when all are affected.
- Identify compatibility requirements and deployment order.
- Do not assume merging one repository automatically merges the other.
- When component branches link to newly introduced portfolio canonical paths, merge the portfolio PR first; then merge component pointer/reference PRs.
- Follow `docs/agent/PROMPT-CROSS-REPO.md`.

## Shared documentation architecture (required)

Before implementing a task that touches shared requirements or crosses repositories, read the canonical portfolio index at https://github.com/georgesdib/strength-app/blob/main/docs/README.md and ownership rules at https://github.com/georgesdib/strength-app/blob/main/docs/DOCUMENTATION.md. Locate cross-repository phase plans under `docs/plans/` and contracts under `docs/contracts/`; do not rely on a duplicated plan inside a submodule or on a portfolio submodule being initialized.

Classify work as backend-only, iOS/watchOS-only, or cross-repository. Commit implementation-specific changes only in the owning component repository. Commit shared plans/specifications/contracts/architecture/decisions and project-wide agent instructions only in the portfolio repository. For a cross-repository task, update the canonical portfolio document plus affected component docs/references in separate coordinated branches and link to the canonical source; do not update submodule pointers unless explicitly required. Keep local compatibility pointers short and non-authoritative. Preserve completed/historical status and never infer phase completion.
