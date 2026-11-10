# Default DSH task prompt

Use this when the task type is unclear or spans an unknown part of the portfolio.

## Before implementation

1. Identify whether the task is server-only, iOS-only, or cross-repo.
2. Put documentation in the owning repository (`docs/DOCUMENTATION.md`); do not duplicate it.
3. Identify the smallest set of files and directories required.
4. Read the relevant repository `AGENTS.md` and any directly relevant contract.
5. Return a concise plan before editing.
6. For migrations, API/schema contracts, security-sensitive changes or architectural
   refactors, wait for approval before editing. Otherwise proceed after the plan.

## Plan format

- Task classification
- Relevant files and directories
- Existing constraints and invariants
- Proposed implementation
- Exact test commands, narrowest first
- Risks and assumptions
- Files that will not be changed

## Token rules

- Do not read `ROADMAP.md`, `CHANGELOG.md`, full documentation, logs, exports,
  lockfiles, build artefacts, or databases unless essential.
- Use targeted searches and small excerpts.
- Do not paste full command, test, build, install, or log output into context.
- Run the narrowest relevant test command first.
- On failure, report a concise diagnosis, not raw output.

## Implementation rules

- Make the smallest coherent change.
- Preserve existing architecture, naming, tests, and documentation conventions.
- Add or update tests for new behaviour.
- Do not add dependencies without justification.
- Do not commit secrets, personal data, or generated artefacts.

## Completion format

- Changed files
- Test commands and concise results
- Assumptions and decisions
- Documentation updates required
- Residual risks
- Suggested commit message

## Shared documentation architecture (required)

Before implementing a task that touches shared requirements or crosses repositories, read the canonical portfolio index at https://github.com/georgesdib/strength-app/blob/main/docs/README.md and ownership rules at https://github.com/georgesdib/strength-app/blob/main/docs/DOCUMENTATION.md. Locate cross-repository phase plans under `docs/plans/` and contracts under `docs/contracts/`; do not rely on a duplicated plan inside a submodule or on a portfolio submodule being initialized.

Classify work as backend-only, iOS/watchOS-only, or cross-repository. Commit implementation-specific changes only in the owning component repository. Commit shared plans/specifications/contracts/architecture/decisions and project-wide agent instructions only in the portfolio repository. For a cross-repository task, update the canonical portfolio document plus affected component docs/references in separate coordinated branches and link to the canonical source; do not update submodule pointers unless explicitly required. Keep local compatibility pointers short and non-authoritative. Preserve completed/historical status and never infer phase completion.
