# Server-only DSH task prompt

Work only within `strength-training-app/`.

Do not inspect or modify `StrengthApp/` unless explicitly instructed.

## Before implementation

1. Read the relevant sections of the server `AGENTS.md`.
2. Identify affected modules, tests, documentation, and configuration.
3. Identify whether the change affects SQLite migrations, append-only records,
   data quality, prescriptions, readiness, web API, or web UI.
4. Return a concise plan before editing.
5. For migrations, API/schema contracts, security-sensitive changes or architectural
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

