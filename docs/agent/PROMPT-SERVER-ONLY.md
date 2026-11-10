# Server-only DSH task prompt

For server-code or backend-implementation-doc work, work only within `strength-training-app/`. If the task changes a shared plan, contract, policy or cross-repository agent instruction, reclassify it as cross-repo and make that shared-doc change in a separate portfolio task branch.

Do not inspect or modify `StrengthApp/` unless explicitly instructed.

## Before implementation

1. Read the relevant sections of the server `AGENTS.md`.
2. Cross-repository plans and iOS server/client contracts are canonical in the portfolio docs; backend API implementation, schema, migrations and tests stay in this repository. Do not maintain duplicate shared plans/contracts here. Keep backend-specific implementation docs local.
3. Identify affected modules, tests, documentation, and configuration.
4. Identify whether the change affects SQLite migrations, append-only records,
   data quality, prescriptions, readiness, web API, or web UI.
5. Return a concise plan before editing.
6. For migrations, API/schema contracts, security-sensitive changes or architectural
   refactors, wait for approval before editing. Otherwise proceed after the plan.

## Plan format

- Relevant modules and files
- Existing behaviour and invariants
- Proposed implementation
- Exact test commands, narrowest first
- Migration, data-quality, privacy, or documentation implications
- Files that will not be changed

## Token rules

- Do not read `ROADMAP.md`, `CHANGELOG.md`, full documentation, logs, exports,
  lockfiles, build artefacts, or SQLite databases unless essential.
- Use targeted searches and small excerpts.
- Do not paste full test, install, build, or log output into context.
- Run focused tests first; run the full suite only as final verification.

## Invariants

- Python computes; the LLM explains and never computes training decisions.
- Preserve append-only records and migration compatibility.
- Do not deduplicate repeated training sets.
- Preserve documented sentinel semantics for zero values.
- Preserve exercise identity, RIR, load, readiness, and rule-engine semantics
  unless explicitly authorised.
- Never commit `data/`, `private/`, credentials, or personal health data.

## Test strategy

Start with the narrowest relevant test command, for example:

```bash
.venv/bin/python -m pytest tests/test_prescribe.py tests/test_rules_policy.py -q
```

## Shared documentation architecture (required)

Before implementing a task that touches shared requirements or crosses repositories, read the canonical portfolio index at https://github.com/georgesdib/strength-app/blob/main/docs/README.md and ownership rules at https://github.com/georgesdib/strength-app/blob/main/docs/DOCUMENTATION.md. Locate cross-repository phase plans under `docs/plans/` and contracts under `docs/contracts/`; do not rely on a duplicated plan inside a submodule or on a portfolio submodule being initialized.

Classify work as backend-only, iOS/watchOS-only, or cross-repository. Commit implementation-specific changes only in the owning component repository. Commit shared plans/specifications/contracts/architecture/decisions and project-wide agent instructions only in the portfolio repository. For a cross-repository task, update the canonical portfolio document plus affected component docs/references in separate coordinated branches and link to the canonical source; do not update submodule pointers unless explicitly required. Keep local compatibility pointers short and non-authoritative. Preserve completed/historical status and never infer phase completion.
