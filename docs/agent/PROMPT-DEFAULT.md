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
