# Whole-repository backup

The portfolio owns the tool that archives all three repositories:
[scripts/backup_app.py](../scripts/backup_app.py). A full run writes one
restorable archive of the portfolio repository, the Python server repository
(`strength-training-app/`) and the iOS/watchOS repository (`StrengthApp/`).

The previous server-only tool lived at
`strength-training-app/tools/backup_app.py`. It moved to the portfolio because
the backup now spans repositories; do not duplicate it in a component
repository.

## What is backed up

A **full** backup (the default) contains:

- every repository's working tree: source, documentation, configuration,
  scripts, tests, README/AGENTS and Git metadata, including `.git` and
  `.git/modules` submodule history;
- non-secret local configuration overlays such as the server's
  `config/volume.local.yaml` and `config/exercises/demands.local.yaml`;
- a consistent SQLite snapshot of each live database directly below a
  repository's `data/` directory (currently the server's `data/coach.db` and
  `data/knowledge-index.sqlite`), taken through SQLite's backup API so
  committed WAL contents are included;
- raw exports (`data/raw/`, `data/exports/`) and local `private/` trees in
  every repository.

These are excluded in every mode:

- local secrets and signing credentials: `.env`, `.env.*` (except example
  templates), `config/llm.local.toml`, `*.p8` and `*.p12`;
- virtualenvs, caches and build output: `.venv/`, `__pycache__/`,
  `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.build/`, `.swiftpm/`,
  `DerivedData/`, `build/`, `dist/`, `node_modules/`, `xcuserdata/`,
  `.worktrees/` and `.tmp-build/`;
- logs, temporary files, `.DS_Store`, `.pyc` and `.xcresult`;
- stale database copies and SQLite sidecars below `data/` (`.bak`,
  `pre-transfer`, `-wal`, `-shm`) and root-level `backups/` directories.

A filled-in iOS acceptance file, `StrengthApp/StrengthAppUITests/LiveConfig.swift`, carries a
server address and pairing code. The tool stops with a clear error instead of archiving it;
revert the file first with
`git -C StrengthApp checkout -- StrengthAppUITests/LiveConfig.swift`. The committed,
empty-default copy is backed up normally.

A **source-only** backup (`--source-only`) additionally excludes every root
`data/` directory, every `private/` tree and all local configuration
overlays.

The tool only reads the working trees. It never modifies, resets or commits the
repositories.

## Run

Run from the portfolio checkout root:

~~~bash
# Default destination: ../<checkout-name>-backups, outside the repository
python3 scripts/backup_app.py

# Code, documentation and configuration only
python3 scripts/backup_app.py --source-only

# Choose the backup directory
python3 scripts/backup_app.py /path/to/backups
~~~

Output is `<checkout-name>-YYYYmmdd-HHMMSS.tar.gz` plus a matching `.sha256`
file, both mode 600, in the chosen directory. The tool refuses a destination
inside the repository. Every submodule must be initialized; it stops with a
clear error instead of writing a partial archive. Initialize them with:

~~~bash
git submodule update --init --recursive
~~~

## Restore

~~~bash
mkdir -p ~/restore
tar -xzf strength-app-*.tar.gz -C ~/restore
cd ~/restore/strength-app
git submodule status
cd strength-training-app
python3 -m venv .venv && .venv/bin/pip install -e .
~~~

The archive carries the portfolio's `.git` directory, including
`.git/modules`, so submodule histories restore without fetching. The archive
name follows the checkout directory name; the example assumes a `strength-app`
checkout.

## Privacy

Full archives contain health data, training exports, private notes and
non-secret local configuration. They are written mode 600, but this script does
**not** encrypt them. Store archives encrypted, keep them out of Git and off
shared devices. A source-only archive still contains Git history and
configuration, so treat it with the same care.

## Tests

~~~bash
python3 -m unittest discover -s tests -v
~~~

The tests use temporary fixtures and standard-library `unittest`, and cover
repository discovery, full and source-only scope, database snapshots, checksum
and mode, and the CLI guards.

## Ownership

The portfolio repository is the canonical home for this cross-repository
tooling. Update this page, the root `README.md`, the docs index and the tests
when the tool's behaviour changes. Keep component-specific documentation in its
owning repository; components may keep a short pointer, not a copy.
