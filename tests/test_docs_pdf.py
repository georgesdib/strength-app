#!/usr/bin/env python3
"""Tests for the cross-repository documentation PDF builder.

Run from the portfolio repository root:

    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "docs_pdf.py"
SPEC = importlib.util.spec_from_file_location("docs_pdf", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
docs_pdf = importlib.util.module_from_spec(SPEC)
sys.modules["docs_pdf"] = docs_pdf
SPEC.loader.exec_module(docs_pdf)


def _pdf_dependencies_available() -> bool:
    """Return whether Markdown and a loadable WeasyPrint are installed."""
    try:
        import markdown  # noqa: F401
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


PDF_DEPENDENCIES_AVAILABLE = _pdf_dependencies_available()


class DocsPdfTests(unittest.TestCase):
    """Exercise collection, grouping, link rewriting and the CLI."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

        self.write("README.md", "# Portfolio\n")
        self.write("AGENTS.md", "# Portfolio agents\n")
        self.write("docs/README.md", "# Portfolio docs\n")
        self.write("private/docs/portfolio-notes.md", "# Portfolio notes\n")

        self.write("strength-training-app/README.md", "# Server\n")
        self.write("strength-training-app/USER-GUIDE.md", "# Server guide\n")
        self.write("strength-training-app/ROADMAP.md", "# Server roadmap\n")
        self.write("strength-training-app/AGENTS.md", "# Server agents\n")
        self.write("strength-training-app/CHANGELOG.md", "# Server changelog\n")
        self.write("strength-training-app/docs/README.md", "# Server docs\n")
        self.write("strength-training-app/docs/API.md", "# HTTP API\n")
        self.write("strength-training-app/private/docs/server-notes.md", "# Server notes\n")

        self.write("StrengthApp/README.md", "# iOS\n")
        self.write("StrengthApp/USER-GUIDE.md", "# iOS guide\n")
        self.write("StrengthApp/DEVICE-ACCEPTANCE.md", "# Device acceptance\n")
        self.write("StrengthApp/WATCH-ACCEPTANCE.md", "# Watch acceptance\n")
        self.write("StrengthApp/AGENTS.md", "# iOS agents\n")
        self.write("StrengthApp/docs/README.md", "# iOS docs\n")
        self.write("StrengthApp/private/docs/ios-notes.md", "# iOS notes\n")

    def write(self, relative: str, body: str) -> Path:
        """Create a Markdown fixture below the temporary workspace root."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def collect(self, **kwargs: object) -> list[object]:
        """Collect documents with all three test repositories."""
        return docs_pdf.collect_documents(root=self.root, **kwargs)

    def test_collects_all_three_repositories_and_private_notes(self) -> None:
        documents = self.collect()
        counts = Counter(document.repo.key for document in documents)

        self.assertEqual(counts, {"portfolio": 4, "server": 8, "ios": 7})
        self.assertEqual(
            list(dict.fromkeys(document.repo.key for document in documents)),
            ["portfolio", "server", "ios"],
        )
        relative_paths = {document.relative for document in documents}
        self.assertIn("private/docs/portfolio-notes.md", relative_paths)
        self.assertIn("private/docs/server-notes.md", relative_paths)
        self.assertIn("private/docs/ios-notes.md", relative_paths)
        self.assertEqual(len({document.section_id for document in documents}), 19)

    def test_private_notes_can_be_excluded(self) -> None:
        documents = self.collect(include_private=False)

        self.assertFalse(
            any(document.relative.startswith("private/") for document in documents)
        )
        self.assertEqual(
            Counter(document.repo.key for document in documents),
            {"portfolio": 3, "server": 7, "ios": 6},
        )

    def test_repository_slugs_are_distinct_for_same_relative_path(self) -> None:
        documents = self.collect()
        readmes = [document for document in documents if document.relative == "README.md"]

        self.assertEqual(len(readmes), 3)
        self.assertEqual(len({document.slug for document in readmes}), 3)
        self.assertTrue(all(document.repo.key in document.slug for document in readmes))

    def test_repo_filter_and_explicit_include(self) -> None:
        repos = [repo for repo in docs_pdf.default_repos(self.root) if repo.key == "ios"]
        self.write("StrengthApp/private/docs/extra.md", "# Extra iOS notes\n")

        documents = docs_pdf.collect_documents(
            root=self.root,
            repos=repos,
            include=["StrengthApp/private/docs/extra.md"],
            include_private=False,
        )
        self.assertEqual({document.repo.key for document in documents}, {"ios"})
        self.assertIn("private/docs/extra.md", {document.relative for document in documents})

    def test_include_outside_selected_repositories_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / "external.md"
            path.write_text("# External\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside the selected repositories"):
                docs_pdf.collect_documents(root=self.root, include=[str(path)])

    def test_rewrite_links_between_repositories(self) -> None:
        self.write(
            "docs/README.md",
            "# Portfolio docs\n\n"
            "[Server API](../strength-training-app/docs/API.md)\n\n"
            "[iOS docs](../StrengthApp/docs/README.md)\n\n"
            "[Same doc](#details)\n\n"
            "[Code](../strength-training-app/strength_coach/cli.py)\n",
        )
        documents = self.collect()
        source = next(
            document
            for document in documents
            if document.repo.key == "portfolio" and document.relative == "docs/README.md"
        )
        server_api = next(
            document
            for document in documents
            if document.display_path == "strength-training-app/docs/API.md"
        )
        ios_readme = next(
            document
            for document in documents
            if document.display_path == "StrengthApp/docs/README.md"
        )

        rewritten = docs_pdf.rewrite_links(
            source.path.read_text(encoding="utf-8"), source, documents
        )

        self.assertIn(f"(#{server_api.section_id})", rewritten)
        self.assertIn(f"(#{ios_readme.section_id})", rewritten)
        self.assertIn(f"(#{source.slug}-details)", rewritten)
        self.assertIn("Code", rewritten)
        self.assertNotIn("strength_coach/cli.py", rewritten)

    def test_build_html_groups_and_labels_the_three_repositories(self) -> None:
        original = docs_pdf._markdown_to_html
        docs_pdf._markdown_to_html = lambda text: "<h1>Document</h1>"
        self.addCleanup(setattr, docs_pdf, "_markdown_to_html", original)
        documents = self.collect()

        output = docs_pdf.build_html(documents, "Test documentation")

        self.assertEqual(output.count('class="repo-divider'), 3)
        for key in ("portfolio", "server", "ios"):
            self.assertIn(f'id="repo-{key}"', output)
            self.assertIn(f'class="doc repo-{key}"', output)
        self.assertIn("Portfolio (strength-app)", output)
        self.assertIn("Server (strength-training-app)", output)
        self.assertIn("iOS client (StrengthApp)", output)
        self.assertIn("strength-training-app/docs/API.md", output)
        self.assertIn("StrengthApp/docs/README.md", output)
        self.assertIn("Documents are grouped by the repository that owns them", output)

    def test_help_explains_how_to_run_and_lists_all_repositories(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            docs_pdf.main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        help_text = output.getvalue()
        for token in (
            "python3 scripts/docs_pdf.py",
            "portfolio",
            "strength-training-app",
            "StrengthApp",
            "--repo",
            "--no-private",
            "--list",
            "requirements-docs.txt",
        ):
            self.assertIn(token, help_text)

    def test_list_groups_documents_by_repository(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = docs_pdf.main(["--root", str(self.root), "--list"])

        self.assertEqual(result, 0)
        text = output.getvalue()
        self.assertIn("== Portfolio (strength-app)", text)
        self.assertIn("== Server (strength-training-app)", text)
        self.assertIn("== iOS client (StrengthApp)", text)
        self.assertIn("19 documents across 3 repositories", text)

    def test_missing_repository_is_reported_as_an_error(self) -> None:
        empty = self.root / "empty"
        empty.mkdir()
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            result = docs_pdf.main(["--root", str(empty), "--list"])

        self.assertEqual(result, 1)
        self.assertIn("repository not found", errors.getvalue())

    @unittest.skipUnless(
        PDF_DEPENDENCIES_AVAILABLE,
        "optional documentation PDF dependencies are not installed",
    )
    def test_render_pdf_writes_a_pdf(self) -> None:
        output = self.root / "dist" / "docs.pdf"
        with contextlib.redirect_stdout(io.StringIO()):
            result = docs_pdf.main(
                ["--root", str(self.root), "--no-private", "-o", str(output)]
            )

        self.assertEqual(result, 0)
        self.assertTrue(output.read_bytes().startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

