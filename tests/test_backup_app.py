#!/usr/bin/env python3
"""Tests for the whole-portfolio backup tool.

Run from the portfolio repository root:

    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import sqlite3
import stat
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backup_app.py"
SPEC = importlib.util.spec_from_file_location("backup_app", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
backup_app = importlib.util.module_from_spec(SPEC)
sys.modules["backup_app"] = backup_app
SPEC.loader.exec_module(backup_app)

GITMODULES = """[submodule "strength-training-app"]
	path = strength-training-app
	url = git@github.com:georgesdib/strength-training-app.git
[submodule "StrengthApp"]
	path = StrengthApp
	url = git@github.com:georgesdib/StrengthApp.git
"""


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _sqlite(path: Path, *values: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE probe (value TEXT)")
        connection.executemany(
            "INSERT INTO probe (value) VALUES (?)", [(value,) for value in values]
        )
        connection.commit()


class BackupAppTests(unittest.TestCase):
    """Exercise the whole-portfolio copy rules, snapshots and CLI guards."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)
        self.root = self._build_portfolio()

    def _build_portfolio(self) -> Path:
        root = self.workspace / "strength-app"
        _write(root / ".gitmodules", GITMODULES)
        _write(root / "README.md", "# Portfolio\n")
        _write(root / "AGENTS.md", "# Agents\n")
        _write(root / "private" / "notes.md", "portfolio private\n")
        _write(root / "scripts" / "backup_app.py", "#!/usr/bin/env python3\n")

        server = root / "strength-training-app"
        _write(server / ".git", "gitdir: ../.git/modules/strength-training-app\n")
        _write(server / "config" / "volume.v1.yaml", "base: true\n")
        _write(server / "config" / "volume.local.yaml", "local: true\n")
        _write(server / "config" / "exercises" / "demands.local.yaml", "ratings: {}\n")
        _write(server / "config" / "llm.local.toml", "api_key = 'secret'\n")
        _write(server / ".env", "SECRET=1\n")
        _write(server / "private" / "docs" / "EVIDENCE.md", "private\n")
        _write(server / ".venv" / "lib" / "cached.py", "cached\n")
        _write(server / "data" / "README.md", "# data\n")
        _write(server / "data" / "raw" / "training_log.csv", "date,set\n")
        _write(server / "data" / "coach.db.bak-pre-0052", "stale\n")
        _sqlite(server / "data" / "coach.db", "x")
        _sqlite(server / "data" / "knowledge-index.sqlite", "index")

        ios = root / "StrengthApp"
        _write(ios / ".git", "gitdir: ../.git/modules/StrengthApp\n")
        _write(ios / "Sources" / "App.swift", "import SwiftUI\n")
        _write(ios / "private" / "notes.md", "ios private\n")
        _write(ios / ".env", "SECRET=1\n")
        _write(ios / "DerivedData" / "build.db", "junk\n")
        _write(ios / ".build" / "index-build" / "build.db", "junk\n")
        _write(ios / "App.xcodeproj" / "xcuserdata" / "me.xcuserdatad" / "state", "junk\n")
        return root

    def _run(self, destination: Path, *args: str) -> Path:
        with mock.patch.object(backup_app, "ROOT", self.root):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(backup_app.main([str(destination), *args]), 0)
        archives = list(destination.glob("*.tar.gz"))
        self.assertEqual(len(archives), 1)
        return archives[0]

    def _members(self, archive: Path) -> set[str]:
        with tarfile.open(archive, "r:gz") as tar:
            return {name for name in tar.getnames() if not name.endswith("/")}

    def test_full_backup_spans_every_repository(self) -> None:
        archive = self._run(self.workspace / "backups")
        members = self._members(archive)

        for expected in (
            "strength-app/README.md",
            "strength-app/strength-training-app/.git",
            "strength-app/strength-training-app/config/volume.v1.yaml",
            "strength-app/strength-training-app/config/volume.local.yaml",
            "strength-app/strength-training-app/config/exercises/demands.local.yaml",
            "strength-app/strength-training-app/data/coach.db",
            "strength-app/strength-training-app/data/knowledge-index.sqlite",
            "strength-app/strength-training-app/data/raw/training_log.csv",
            "strength-app/strength-training-app/private/docs/EVIDENCE.md",
            "strength-app/StrengthApp/.git",
            "strength-app/StrengthApp/Sources/App.swift",
            "strength-app/StrengthApp/private/notes.md",
            "strength-app/private/notes.md",
        ):
            self.assertIn(expected, members)

        for excluded in (
            "strength-app/strength-training-app/.env",
            "strength-app/strength-training-app/config/llm.local.toml",
            "strength-app/strength-training-app/.venv/lib/cached.py",
            "strength-app/strength-training-app/data/coach.db.bak-pre-0052",
            "strength-app/StrengthApp/.env",
            "strength-app/StrengthApp/DerivedData/build.db",
            "strength-app/StrengthApp/.build/index-build/build.db",
            "strength-app/StrengthApp/App.xcodeproj/xcuserdata/me.xcuserdatad/state",
        ):
            self.assertNotIn(excluded, members)

    def test_full_backup_snapshots_the_live_database(self) -> None:
        archive = self._run(self.workspace / "backups")

        with tarfile.open(archive, "r:gz") as tar:
            handle = tar.extractfile("strength-app/strength-training-app/data/coach.db")
            self.assertIsNotNone(handle)
            payload = handle.read()

        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "coach.db"
            snapshot.write_bytes(payload)
            with contextlib.closing(sqlite3.connect(snapshot)) as connection:
                rows = connection.execute("SELECT value FROM probe ORDER BY value").fetchall()
        self.assertEqual(rows, [("x",)])

    def test_archive_and_checksum_are_private(self) -> None:
        archive = self._run(self.workspace / "backups")
        checksum = archive.with_suffix(archive.suffix + ".sha256")

        self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(checksum.stat().st_mode), 0o600)
        digest, name = checksum.read_text(encoding="utf-8").split()
        self.assertEqual(name, archive.name)
        self.assertEqual(digest, hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_source_only_excludes_data_private_and_local_config(self) -> None:
        archive = self._run(self.workspace / "backups", "--source-only")
        members = self._members(archive)

        for expected in (
            "strength-app/README.md",
            "strength-app/strength-training-app/config/volume.v1.yaml",
            "strength-app/strength-training-app/.git",
            "strength-app/StrengthApp/Sources/App.swift",
        ):
            self.assertIn(expected, members)

        for excluded in (
            "strength-app/strength-training-app/data/coach.db",
            "strength-app/strength-training-app/data/knowledge-index.sqlite",
            "strength-app/strength-training-app/data/raw/training_log.csv",
            "strength-app/strength-training-app/private/docs/EVIDENCE.md",
            "strength-app/StrengthApp/private/notes.md",
            "strength-app/private/notes.md",
            "strength-app/strength-training-app/config/volume.local.yaml",
            "strength-app/strength-training-app/config/exercises/demands.local.yaml",
            "strength-app/strength-training-app/.env",
        ):
            self.assertNotIn(excluded, members)

    def test_default_destination_is_a_sibling_directory(self) -> None:
        with mock.patch.object(backup_app, "ROOT", self.root):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(backup_app.main([]), 0)
        archives = list((self.workspace / "strength-app-backups").glob("*.tar.gz"))
        self.assertEqual(len(archives), 1)

    def test_refuses_filled_in_live_acceptance_config(self) -> None:
        _write(
            self.root / "StrengthApp" / "StrengthAppUITests" / "LiveConfig.swift",
            'enum LiveConfig {\n'
            '    static let enabled = true\n'
            '    static let serverURL = "http://192.168.1.5:8000"\n'
            '    static let pairingCode = "123456"\n'
            '}\n',
        )
        stderr = io.StringIO()
        with mock.patch.object(backup_app, "ROOT", self.root):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(backup_app.main([str(self.workspace / "backups")]), 2)
        self.assertIn("holds live acceptance values", stderr.getvalue())
        self.assertFalse((self.workspace / "backups").exists())

    def test_committed_live_config_defaults_are_backed_up(self) -> None:
        _write(
            self.root / "StrengthApp" / "StrengthAppUITests" / "LiveConfig.swift",
            'enum LiveConfig {\n'
            '    static let enabled = false\n'
            '    static let serverURL = ""\n'
            '    static let pairingCode = ""\n'
            '}\n',
        )
        archive = self._run(self.workspace / "backups")
        self.assertIn(
            "strength-app/StrengthApp/StrengthAppUITests/LiveConfig.swift",
            self._members(archive),
        )

    def test_refuses_destination_inside_the_repository(self) -> None:
        destination = self.root / "backups"
        stderr = io.StringIO()
        with mock.patch.object(backup_app, "ROOT", self.root):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(backup_app.main([str(destination)]), 2)
        self.assertIn("Refusing destination inside the repository", stderr.getvalue())
        self.assertFalse(destination.exists())

    def test_refuses_uninitialized_submodule(self) -> None:
        (self.root / "StrengthApp" / ".git").unlink()
        stderr = io.StringIO()
        with mock.patch.object(backup_app, "ROOT", self.root):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(backup_app.main([str(self.workspace / "backups")]), 2)
        self.assertIn("submodule 'StrengthApp' is not initialized", stderr.getvalue())
        self.assertFalse((self.workspace / "backups").exists())


if __name__ == "__main__":
    unittest.main()
