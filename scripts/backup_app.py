#!/usr/bin/env python3
"""Create one restorable archive of the whole Strength App portfolio.

The portfolio checkout is the cross-repository home of the project. It contains both
application repositories as Git submodules: the Python server in
'strength-training-app/' and the iOS/watchOS client in 'StrengthApp/'. This tool
replaces the server-only 'tools/backup_app.py' and backs up all repositories
together.

A full backup contains every repository's source, documentation, configuration,
scripts and tests, its Git history (including '.git/modules' submodule history),
non-secret local configuration overlays, a consistent SQLite snapshot of each live
database directly below a repository's 'data/' directory, raw exports and local
'private/' data. It excludes virtualenvs, caches, build output, logs, stale
database copies and local secrets. The archive contains health data and private
local state; it is written mode 600 but this script does not encrypt it.

Use --source-only for a code, documentation and configuration backup that also
excludes databases, raw exports, 'private/' data, local configuration overlays,
local secrets and local SQLite indexes.
"""

from __future__ import annotations

import argparse
import configparser
import contextlib
import hashlib
import os
import re
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_NAMES = {
    ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    "node_modules", "backups", "dist", "build", "DerivedData", "xcuserdata",
    ".build", ".swiftpm", ".worktrees", ".tmp-build",
}
SKIP_SUFFIXES = (".pyc", ".pyo", ".log", ".tmp", ".swp", ".xcresult", ".DS_Store")
DATABASE_SUFFIXES = (".db", ".sqlite", ".sqlite3")
SAFE_ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template"}
LIVE_CONFIG = Path("StrengthApp/StrengthAppUITests/LiveConfig.swift")

HELP_TEXT = """Full backup of the portfolio and both application repositories (source, docs, config,
Git history, consistent SQLite snapshots, raw exports, private/ data):
  python3 scripts/backup_app.py

Choose the backup directory:
  python3 scripts/backup_app.py /path/to/backups

Source-only backup (no databases, raw exports, private data, local config overlays
or local secrets):
  python3 scripts/backup_app.py --source-only /path/to/backups

Default destination: ../<checkout-name>-backups (outside the repository).
Output: <checkout-name>-YYYYmmdd-HHMMSS.tar.gz plus .sha256, both mode 600.

Restore outline:
  mkdir -p ~/restore
  tar -xzf <checkout-name>-*.tar.gz -C ~/restore
  cd ~/restore/<checkout-name>
  git submodule status
  cd strength-training-app
  python3 -m venv .venv && .venv/bin/pip install -e .

Full archives contain health data and private local state and are NOT encrypted by
this script. Local secrets are excluded; store the archive encrypted and restrict
access.
"""


def submodule_paths(root: Path = ROOT) -> tuple[Path, ...]:
    """Return the submodule paths declared in *root*/.gitmodules, if any."""
    modules = Path(root) / ".gitmodules"
    if not modules.is_file():
        return ()
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(modules, encoding="utf-8")
    except configparser.Error:
        return ()
    paths: list[Path] = []
    for section in parser.sections():
        if not section.startswith("submodule "):
            continue
        value = parser[section].get("path", "").strip().strip('"')
        if value:
            paths.append(Path(value))
    return tuple(paths)


def repository_roots(root: Path = ROOT) -> tuple[Path, ...]:
    """Return the portfolio root plus each initialized repository below it."""
    root = Path(root)
    roots = {root}
    for relative in submodule_paths(root):
        candidate = root / relative
        if (candidate / ".git").exists():
            roots.add(candidate)
    for child in root.iterdir():
        if child.is_dir() and (child / ".git").exists():
            roots.add(child)
    return tuple(sorted(roots, key=lambda path: len(path.parts)))


def _owning_repository(directory: Path, roots: tuple[Path, ...]) -> Path:
    """Return the deepest repository root that contains *directory*."""
    owning = roots[0]
    for root in roots:
        try:
            directory.relative_to(root)
        except ValueError:
            continue
        if len(root.parts) > len(owning.parts):
            owning = root
    return owning


def _is_local_secret(name: str) -> bool:
    """Return whether *name* is a local secret or signing credential."""
    if name == ".env":
        return True
    if name.startswith(".env.") and name not in SAFE_ENV_TEMPLATES:
        return True
    if name == "llm.local.toml":
        return True
    return name.endswith((".p8", ".p12"))


def _is_local_config(name: str) -> bool:
    """Return whether *name* is a machine-local configuration overlay."""
    return ".local." in name


def _is_database_artifact(name: str) -> bool:
    """Return whether *name* below data/ is a live database, stale copy or sidecar."""
    return ".db" in name or ".sqlite" in name


def _active_live_config(root: Path = ROOT) -> Path | None:
    """Return the iOS live-config file when it holds acceptance-run values."""
    path = Path(root) / LIVE_CONFIG
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    if "static let enabled = true" in text:
        return path
    for key in ("serverURL", "pairingCode"):
        match = re.search(rf'static let {key}\s*=\s*"([^"]*)"', text)
        if match and match.group(1):
            return path
    return None


def _ignore(source_only: bool, roots: tuple[Path, ...]):
    """Build the copytree ignore function for the repositories below ROOT."""

    def ignore(directory: str, names: list[str]) -> set[str]:
        current = Path(directory)
        repository = _owning_repository(current, roots)
        relative = current.relative_to(repository)
        skipped: set[str] = set()
        for name in names:
            if name in SKIP_NAMES or name.endswith(".egg-info") or name.endswith(SKIP_SUFFIXES):
                skipped.add(name)
                continue
            # Secrets and signing credentials are excluded in both modes.
            if _is_local_secret(name):
                skipped.add(name)
                continue
            # Non-secret local overlays are local state: full mode keeps them, source-only does not.
            if source_only and _is_local_config(name):
                skipped.add(name)
                continue
            # private/ trees hold local notes and personal data in every repository.
            if source_only and name == "private":
                skipped.add(name)
                continue
            if relative == Path("."):
                if source_only and name == "data":
                    skipped.add(name)
                elif name == "backups":
                    skipped.add(name)
            elif relative == Path("data"):
                # Live databases are snapshotted separately; stale copies and sidecars are
                # not copied.
                if _is_database_artifact(name):
                    skipped.add(name)
                elif source_only and name in {"raw", "export", "exports"}:
                    skipped.add(name)
        return skipped

    return ignore


def _snapshot_databases(
    staging: Path, source_only: bool, roots: tuple[Path, ...]
) -> tuple[Path, ...]:
    """Snapshot each live SQLite database below a repository's data/ directory."""
    if source_only:
        return ()
    snapshots: list[Path] = []
    for repository in roots:
        data = repository / "data"
        if not data.is_dir():
            continue
        for source in sorted(data.iterdir()):
            if not source.is_file() or not source.name.endswith(DATABASE_SUFFIXES):
                continue
            relative = source.relative_to(ROOT)
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                with (
                    contextlib.closing(
                        sqlite3.connect(f"file:{source}?mode=ro", uri=True)
                    ) as reader,
                    contextlib.closing(sqlite3.connect(destination)) as writer,
                ):
                    reader.backup(writer)
            except sqlite3.Error as error:
                raise RuntimeError(f"could not snapshot {relative}: {error}") from error
            snapshots.append(relative)
    return tuple(snapshots)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a restorable whole-portfolio Strength App archive.",
        epilog=HELP_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "destination",
        nargs="?",
        help="Backup directory (default: sibling directory outside the repository)",
    )
    parser.add_argument(
        "--source-only",
        action="store_true",
        help=(
            "Exclude databases, raw exports, private data, local config overlays, local "
            "secrets and local SQLite indexes"
        ),
    )
    args = parser.parse_args(argv)

    destination = (
        Path(args.destination).expanduser().resolve()
        if args.destination
        else ROOT.parent / f"{ROOT.name}-backups"
    )
    try:
        destination.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        print(f"Refusing destination inside the repository: {destination}", file=sys.stderr)
        return 2

    active_config = _active_live_config(ROOT)
    if active_config is not None:
        print(
            f"error: {active_config.relative_to(ROOT)} holds live acceptance values (server URL "
            "or pairing code); revert it with 'git -C StrengthApp checkout -- "
            "StrengthAppUITests/LiveConfig.swift' before backing up",
            file=sys.stderr,
        )
        return 2

    for relative in submodule_paths(ROOT):
        if not (ROOT / relative / ".git").exists():
            print(
                f"error: submodule '{relative}' is not initialized; run "
                "'git submodule update --init --recursive' before backing up the portfolio",
                file=sys.stderr,
            )
            return 2

    roots = repository_roots(ROOT)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    archive = destination / f"{ROOT.name}-{stamp}.tar.gz"
    checksum = archive.with_suffix(archive.suffix + ".sha256")

    try:
        with tempfile.TemporaryDirectory(prefix="strength-app-backup-") as temporary:
            staging = Path(temporary) / ROOT.name
            shutil.copytree(
                ROOT,
                staging,
                symlinks=True,
                ignore=_ignore(args.source_only, roots),
            )
            snapshots = _snapshot_databases(staging, args.source_only, roots)
            # Write the archive beside the staging copy first so a failed run never leaves a
            # partial archive in the backup directory.
            written = Path(temporary) / archive.name
            with tarfile.open(written, "w:gz") as tar:
                tar.add(staging, arcname=ROOT.name)
            shutil.move(written, archive)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    os.chmod(archive, 0o600)
    digest = _sha256(archive)
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    os.chmod(checksum, 0o600)

    size_mb = archive.stat().st_size / (1024 * 1024)
    print(f"Scope:    {', '.join(repository.name for repository in roots)}")
    print(f"Archive:  {archive}")
    print(f"Size:     {size_mb:.1f} MiB")
    print(f"SHA256:   {digest}")
    print(f"Checksum: {checksum}")
    if snapshots:
        print(f"Snapshots: {', '.join(str(snapshot) for snapshot in snapshots)}")
    if args.source_only:
        print(
            "Mode:     source only (no databases, raw exports, private data, local config "
            "overlays or local secrets)"
        )
    else:
        print(
            "Mode:     full (contains health data and private local state; local secrets "
            "excluded; store encrypted)"
        )
        if not snapshots:
            print("Note:     no live SQLite database was found below data/; snapshot skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
