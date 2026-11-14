#!/usr/bin/env python3
"""Build one PDF from the documentation in all three Strength App repositories.

The portfolio checkout (this repository) contains three documentation sets:

* the portfolio repository itself (plans, contracts, decisions and agent policy);
* the Python server repository in 'strength-training-app/';
* the iOS/watchOS client repository in 'StrengthApp/'.

By default the bundle contains each repository's conventional top-level guides,
every Markdown file below its 'docs/' directory, and, when present, every
Markdown file below its local 'private/docs/' directory. Documents are grouped
by repository in the PDF: each repository gets a full-page divider, its own
contents group, a source badge and a running page header. Links between bundled
documents become internal PDF links.

Run from the portfolio repository root:

    python3 scripts/docs_pdf.py                  # write the default PDF
    python3 scripts/docs_pdf.py --help           # show every option and example
    python3 scripts/docs_pdf.py --list           # show what will be included
    python3 scripts/docs_pdf.py --repo server --repo ios
    python3 scripts/docs_pdf.py -o build/strength-app-docs.pdf
    python3 scripts/docs_pdf.py --no-private

Install the optional rendering dependencies once (a virtual environment is best):

    python3 -m venv .venv
    .venv/bin/pip install -r scripts/requirements-docs.txt

Privacy: private/docs/ trees are local, git-ignored notes. They are included by
default, so the generated PDF may contain personal material. The default output
lives below 'dist/', which is git-ignored. Use --no-private to omit private
notes. The PDF is generated locally; nothing is uploaded.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "strength-app-docs.pdf"
DEFAULT_TITLE = "Strength App documentation"

# Fenced blocks must not be scanned for links: a documentation example may contain Markdown.
FENCE_RE = re.compile(r"(^\x60{3}.*?^\x60{3}[ \t]*$)", re.MULTILINE | re.DOTALL)
LINK_RE = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
HEADING_ID_RE = re.compile(r'(<h[1-6]\b[^>]*\bid=")([^"]+)(")')
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


@dataclass(frozen=True)
class Repo:
    """One documentation repository included in the PDF bundle."""

    key: str
    label: str
    short_label: str
    path: Path
    description: str
    root_documents: tuple[str, ...]


def default_repos(root: Path = ROOT) -> tuple[Repo, ...]:
    """Return the portfolio, server and iOS repository definitions below *root*."""
    root = Path(root).resolve()
    return (
        Repo(
            key="portfolio",
            label="Portfolio (strength-app)",
            short_label="Portfolio",
            path=root,
            description=(
                "Cross-repository plans, contracts, decisions, architecture, agent routing "
                "and documentation policy."
            ),
            root_documents=("README.md", "AGENTS.md"),
        ),
        Repo(
            key="server",
            label="Server (strength-training-app)",
            short_label="Server",
            path=root / "strength-training-app",
            description=(
                "Python strength-coaching server: training rules, API, data model, "
                "migrations, backend operations and live implementation status."
            ),
            root_documents=(
                "README.md",
                "USER-GUIDE.md",
                "ROADMAP.md",
                "AGENTS.md",
                "CHANGELOG.md",
            ),
        ),
        Repo(
            key="ios",
            label="iOS client (StrengthApp)",
            short_label="iOS",
            path=root / "StrengthApp",
            description=(
                "SwiftUI iPhone and watchOS client: architecture, build and live-test "
                "procedures, user guide and Apple device acceptance records."
            ),
            root_documents=(
                "README.md",
                "USER-GUIDE.md",
                "DEVICE-ACCEPTANCE.md",
                "WATCH-ACCEPTANCE.md",
                "AGENTS.md",
            ),
        ),
    )


@dataclass(frozen=True)
class Document:
    """A Markdown document, its owning repository and its workspace root."""

    path: Path
    relative: str
    title: str
    repo: Repo
    workspace: Path

    @property
    def slug(self) -> str:
        """Return a bundle-wide unique HTML id fragment for this document."""
        stem = self.relative.removesuffix(".md").lower()
        return re.sub(r"[^a-z0-9]+", "-", f"{self.repo.key}-{stem}").strip("-")

    @property
    def section_id(self) -> str:
        """Return the HTML id used for the document's PDF anchor."""
        return f"doc-{self.slug}"

    @property
    def display_path(self) -> str:
        """Return the repository-labelled path shown in the PDF and contents list."""
        return f"{self.repo.path.name}/{self.relative}"


def _plain_title(text: str) -> str:
    """Turn the first heading's inline Markdown into a plain TOC label."""
    text = LINK_RE.sub(lambda match: match.group(1), text)
    text = re.sub(r"[\x60*_~]", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split())


def title_for(path: Path) -> str:
    """Return the first level-one heading for *path*, or its filename stem."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            return _plain_title(line[2:].strip()) or path.stem
    return path.stem


def _repo_for_path(repos: tuple[Repo, ...], path: Path) -> Repo | None:
    """Return the most specific selected repository that contains *path*."""
    resolved = path.resolve()
    matches = [
        repo
        for repo in repos
        if resolved == repo.path or repo.path in resolved.parents
    ]
    if not matches:
        return None
    return max(matches, key=lambda repo: len(repo.path.parts))


def _default_paths(repo: Repo, include_private: bool) -> list[Path]:
    """Return the conventional Markdown paths for one repository."""
    paths: list[Path] = []
    for name in repo.root_documents:
        path = repo.path / name
        if path.is_file():
            paths.append(path)

    docs_dir = repo.path / "docs"
    if docs_dir.is_dir():
        paths.extend(sorted(docs_dir.rglob("*.md")))

    if include_private:
        private_dir = repo.path / "private" / "docs"
        if private_dir.is_dir():
            paths.extend(sorted(private_dir.rglob("*.md")))
    return paths


def collect_documents(
    root: Path = ROOT,
    repos: tuple[Repo, ...] | list[Repo] | None = None,
    include: list[str] | tuple[str, ...] = (),
    include_private: bool = True,
) -> list[Document]:
    """Collect the documents for the selected repositories.

    'root' is the portfolio checkout. 'repos' defaults to all three
    repositories; pass a subset (usually from default_repos) to render only the
    portfolio, server or iOS documentation. 'include' adds Markdown paths
    relative to 'root' and is repeatable. Private private/docs/ notes are
    included unless 'include_private' is false. Duplicate paths are rendered
    once, in repository order.
    """
    workspace = Path(root).resolve()
    selected = tuple(repos) if repos is not None else default_repos(workspace)
    pending: list[tuple[Path, Repo]] = []

    for repo in selected:
        if not repo.path.is_dir():
            raise FileNotFoundError(
                f"repository not found: {repo.path}; expected the {repo.key} checkout "
                "below the portfolio root"
            )
        pending.extend((path, repo) for path in _default_paths(repo, include_private))

    for item in include:
        path = Path(item)
        if not path.is_absolute():
            path = workspace / path
        repo = _repo_for_path(selected, path)
        if repo is None:
            raise ValueError(
                f"included document is outside the selected repositories: {path}"
            )
        pending.append((path, repo))

    seen: set[Path] = set()
    documents: list[Document] = []
    for path, repo in pending:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not resolved.is_file():
            raise FileNotFoundError(f"document not found: {path}")
        try:
            relative = resolved.relative_to(repo.path).as_posix()
        except ValueError:
            relative = resolved.name
        documents.append(
            Document(resolved, relative, title_for(resolved), repo, workspace)
        )
    return documents


def _route_document(
    source: Document, doc_path: str, by_path: dict[Path, Document]
) -> Document | None:
    """Resolve a docs-viewer route target to a bundled document, if possible."""
    for base in (source.repo.path, source.workspace):
        candidate = (base / doc_path).resolve()
        destination = by_path.get(candidate)
        if destination is not None:
            return destination
    return None


def _rewrite_link(match: re.Match[str], source: Document, by_path: dict[Path, Document]) -> str:
    """Rewrite one Markdown link for the bundled PDF."""
    label, target = match.group(1), match.group(2)
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if not target or target == "#":
        return label
    if target.startswith("#docs?"):
        # Web-app routes such as #docs?doc=docs/WEB-UI.md&anchor=pages become real PDF links
        # when the target is bundled; otherwise the label is more useful than a dead anchor.
        route = urlsplit(target).fragment.partition("?")[2]
        params = parse_qs(route)
        doc_path = (params.get("doc") or [None])[0]
        if doc_path:
            destination = _route_document(source, doc_path, by_path)
            if destination is not None:
                anchor = (params.get("anchor") or [None])[0]
                if anchor:
                    return f"[{label}](#{destination.slug}-{anchor})"
                return f"[{label}](#{destination.section_id})"
        return label
    if target.startswith("#"):
        return f"[{label}](#{source.slug}-{target[1:]})"
    if target.startswith("//") or SCHEME_RE.match(target):
        return match.group(0)

    parsed = urlsplit(target)
    path_part = unquote(parsed.path)
    if not path_part:
        fragment = parsed.fragment
        return f"[{label}](#{source.slug}-{fragment})" if fragment else match.group(0)

    candidates = [(source.path.parent / path_part).resolve()]
    if path_part.startswith("/"):
        candidates.append((source.repo.path / path_part.lstrip("/")).resolve())
    else:
        candidates.append((source.repo.path / path_part).resolve())
    destination = next(
        (by_path[candidate] for candidate in candidates if candidate in by_path), None
    )
    if destination is None:
        # A config/code path cannot be a useful link inside a PDF; keep its readable label.
        return label
    if parsed.fragment:
        return f"[{label}](#{destination.slug}-{parsed.fragment})"
    return f"[{label}](#{destination.section_id})"


def rewrite_links(text: str, source: Document, documents: list[Document]) -> str:
    """Point links between bundled documents at their internal PDF anchors.

    Links to code, configuration, personal paths or other unbundled files stay as
    readable labels; external URLs are left alone.
    """
    by_path = {document.path: document for document in documents}
    parts = FENCE_RE.split(text)
    out: list[str] = []
    for index, part in enumerate(parts):
        if index % 2 == 1:  # fenced code block: leave example Markdown untouched
            out.append(part)
        else:
            out.append(
                LINK_RE.sub(lambda match: _rewrite_link(match, source, by_path), part)
            )
    return "".join(out)


def _prefix_heading_ids(body: str, slug: str) -> str:
    """Keep heading ids unique across the bundle so links cannot collide."""
    return HEADING_ID_RE.sub(
        lambda match: f"{match.group(1)}{slug}-{match.group(2)}{match.group(3)}", body
    )


def _markdown_to_html(text: str) -> str:
    """Convert Markdown to HTML using the optional 'markdown' dependency."""
    try:
        import markdown
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "PDF generation needs the optional docs dependencies; run "
            "'python3 -m pip install -r scripts/requirements-docs.txt'"
        ) from exc

    editor = markdown.Markdown(
        extensions=["extra", "toc", "sane_lists"],
        extension_configs={"toc": {"permalink": False}},
        output_format="html5",
    )
    return editor.convert(text)


def _repo_css_class(key: str) -> str:
    """Return a CSS-safe repository class suffix."""
    return re.sub(r"[^a-z0-9-]+", "-", key.lower()).strip("-")


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    """Return the singular or plural label for *count*."""
    return singular if count == 1 else (plural or f"{singular}s")


def _repo_divider(repo: Repo, index: int, total: int, count: int) -> str:
    """Build the full-page divider that introduces one repository's documents."""
    key = _repo_css_class(repo.key)
    return f"""
    <section class="repo-divider repo-{key}" id="repo-{key}">
      <div class="repo-index"><span class="repo-short">{html.escape(repo.short_label)}</span>
      · Repository {index} of {total}</div>
      <h1 class="repo-name">{html.escape(repo.label)}</h1>
      <p class="repo-description">{html.escape(repo.description)}</p>
      <p class="repo-meta">{count} {_plural(count, 'document')} · {html.escape(repo.path.name)}</p>
    </section>
    """


def build_html(documents: list[Document], title: str = DEFAULT_TITLE) -> str:
    """Build one self-contained HTML document, ready for WeasyPrint.

    Documents are grouped by repository. Each group gets a divider page, a
    contents heading and a source badge so the three repositories are visually
    distinct in the rendered PDF.
    """
    grouped: dict[str, list[Document]] = {}
    for document in documents:
        grouped.setdefault(document.repo.key, []).append(document)
    repo_order = [docs[0].repo for docs in grouped.values()]

    toc_groups: list[str] = []
    for repo in repo_order:
        docs = grouped[repo.key]
        key = _repo_css_class(repo.key)
        entries = "".join(
            f'<li><a href="#{document.section_id}">'
            f'<span class="toc-title">{html.escape(document.title)}</span>'
            f'<span class="toc-path">{html.escape(document.display_path)}</span></a></li>'
            for document in docs
        )
        toc_groups.append(
            f'<div class="toc-group toc-group-{key}">'
            f'<h3 class="toc-repo"><a href="#repo-{key}">{html.escape(repo.label)}</a>'
            f'<span class="toc-count">{len(docs)} {_plural(len(docs), "document")}</span></h3>'
            f'<ol class="toc-list">{entries}</ol></div>'
        )

    sections: list[str] = []
    for index, repo in enumerate(repo_order, start=1):
        docs = grouped[repo.key]
        key = _repo_css_class(repo.key)
        sections.append(_repo_divider(repo, index, len(repo_order), len(docs)))
        for document in docs:
            source = document.path.read_text(encoding="utf-8")
            body = _prefix_heading_ids(
                _markdown_to_html(rewrite_links(source, document, documents)),
                document.slug,
            )
            sections.append(
                f'<section class="doc repo-{key}" id="{document.section_id}">'
                f'<div class="source">'
                f'<span class="source-repo">{html.escape(repo.label)}</span>'
                f'<span class="source-path">{html.escape(document.display_path)}</span>'
                f"</div>{body}</section>"
            )

    badges = "".join(
        f'<span class="cover-repo repo-{_repo_css_class(repo.key)}">'
        f"{html.escape(repo.label)}"
        f"<small>{len(grouped[repo.key])} {_plural(len(grouped[repo.key]), 'document')}</small>"
        f"</span>"
        for repo in repo_order
    )
    cover = f"""
    <section class="cover">
      <div class="cover-kicker">Documentation bundle</div>
      <h1>{html.escape(title)}</h1>
      <p class="cover-copy">One searchable PDF drawn from the portfolio, Python server and iOS
      client repositories. Each repository has its own divider, contents group and page header.</p>
      <div class="cover-repos">{badges}</div>
      <p class="cover-meta">{len(documents)} {_plural(len(documents), 'document')} across
      {len(repo_order)} {_plural(len(repo_order), 'repository', 'repositories')} · generated
      {date.today().isoformat()}</p>
    </section>
    """
    contents = f"""
    <section class="toc">
      <h2>Contents</h2>
      <p class="toc-note">Documents are grouped by the repository that owns them.</p>
      {''.join(toc_groups)}
    </section>
    """
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
{cover}
{contents}
{''.join(sections)}
</body>
</html>
"""


CSS = """
@page {
  size: A4;
  margin: 19mm 16mm 18mm 16mm;
  @top-left {
    content: "Strength App documentation · " string(repo);
    color: #6b7280;
    font-size: 7.5pt;
  }
  @top-right {
    content: string(doctitle);
    color: #6b7280;
    font-size: 7.5pt;
  }
  @bottom-center {
    content: counter(page);
    color: #6b7280;
    font-size: 8pt;
  }
}
@page cover {
  margin: 0;
  @top-left { content: none; }
  @top-right { content: none; }
  @bottom-center { content: none; }
}
@page repo-divider {
  margin: 0;
  @top-left { content: none; }
  @top-right { content: none; }
  @bottom-center { content: none; }
}
html { font-size: 9.5pt; }
body {
  margin: 0;
  color: #1f2933;
  font-family: "DejaVu Sans", "Liberation Sans", sans-serif;
  line-height: 1.45;
}
.cover {
  page: cover;
  height: 297mm;
  padding: 42mm 28mm 28mm;
  box-sizing: border-box;
  background: #123047;
  color: #f8fafc;
}
.cover-kicker {
  color: #9cc3dd;
  font-size: 10pt;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.cover h1 {
  margin: 14mm 0 8mm;
  font-size: 28pt;
  line-height: 1.15;
  bookmark-level: none;
}
.cover-copy { max-width: 125mm; font-size: 12pt; color: #d7e6f0; }
.cover-repos { margin-top: 12mm; }
.cover-repo {
  display: inline-block;
  margin: 0 2mm 2.5mm 0;
  padding: 2.5mm 4mm;
  border-left: 2mm solid #9cc3dd;
  border-radius: 1.5mm;
  background: rgba(255, 255, 255, 0.10);
  font-size: 9.5pt;
  font-weight: bold;
}
.cover-repo small {
  display: block;
  margin-top: 0.7mm;
  color: #d7e6f0;
  font-size: 7.5pt;
  font-weight: normal;
}
.cover-repo.repo-server { border-left-color: #7dd3a8; }
.cover-repo.repo-ios { border-left-color: #f6ad55; }
.cover-meta { margin-top: 35mm; font-size: 9pt; color: #9cc3dd; }
.toc { break-before: page; }
.toc h2 { font-size: 20pt; margin: 0 0 3mm; bookmark-level: 1; bookmark-label: "Contents"; }
.toc-note { color: #6b7280; margin-bottom: 8mm; }
.toc-group { margin: 0 0 7mm; break-inside: avoid; }
.toc-repo {
  margin: 0 0 2mm;
  padding: 0 0 1.5mm;
  border-bottom: 1.5pt solid #123047;
  color: #123047;
  font-size: 12pt;
  bookmark-level: 2;
}
.toc-group-server .toc-repo { border-bottom-color: #1f6f43; color: #1f6f43; }
.toc-group-ios .toc-repo { border-bottom-color: #b45309; color: #b45309; }
.toc-repo a { color: inherit; text-decoration: none; }
.toc-count { float: right; color: #6b7280; font-size: 8pt; font-weight: normal; }
.toc-list { margin: 0; padding: 0; list-style: none; }
.toc li { border-bottom: 0.5pt solid #d9dee5; padding: 2.2mm 0; }
.toc a { color: inherit; text-decoration: none; }
.toc-title { font-weight: bold; }
.toc-path { float: right; color: #6b7280; font-family: "DejaVu Sans Mono", monospace; font-size: 7.5pt; }
.toc-list a::after { content: target-counter(attr(href), page); float: right; margin-left: 4mm; color: #374151; }
.repo-divider {
  page: repo-divider;
  break-before: page;
  height: 297mm;
  padding: 55mm 28mm 28mm;
  box-sizing: border-box;
  border-top: 14mm solid #123047;
  background: #f8fafc;
}
.repo-divider.repo-server { border-top-color: #1f6f43; }
.repo-divider.repo-ios { border-top-color: #b45309; }
.repo-index { font-size: 9pt; letter-spacing: 0.14em; text-transform: uppercase; color: #6b7280; }
.repo-short { string-set: repo content(); }
.repo-name {
  margin: 10mm 0 6mm;
  color: #123047;
  font-size: 30pt;
  line-height: 1.15;
  bookmark-level: 1;
}
.repo-divider.repo-server .repo-name { color: #1f6f43; }
.repo-divider.repo-ios .repo-name { color: #b45309; }
.repo-description { max-width: 125mm; font-size: 11pt; color: #374151; }
.repo-meta { margin-top: 35mm; font-size: 9pt; color: #6b7280; }
section.doc { break-before: page; }
section.doc h1 { string-set: doctitle content(); }
section.doc.repo-server h1 { color: #1f6f43; }
section.doc.repo-ios h1 { color: #b45309; }
.source { margin-bottom: 3mm; color: #6b7280; font-size: 7.5pt; }
.source-repo {
  display: inline-block;
  margin-right: 2mm;
  padding: 0.6mm 1.6mm;
  border-radius: 1pt;
  background: #eaf0f4;
  color: #123047;
  font-family: "DejaVu Sans", sans-serif;
  font-weight: bold;
}
.doc.repo-server .source-repo { background: #e7f4ec; color: #1f6f43; }
.doc.repo-ios .source-repo { background: #fdf0df; color: #9a3412; }
.source-path { font-family: "DejaVu Sans Mono", monospace; }
h1, h2, h3, h4, h5, h6 { color: #123047; line-height: 1.25; bookmark-level: auto; }
h1 { font-size: 20pt; margin: 0 0 5mm; bookmark-level: 1; }
h2 { font-size: 14pt; margin: 7mm 0 3mm; bookmark-level: 2; }
h3 { font-size: 11.5pt; margin: 5mm 0 2mm; bookmark-level: 3; }
h4 { font-size: 10pt; margin: 4mm 0 1.5mm; bookmark-level: 4; }
p { margin: 0 0 2.4mm; }
ul, ol { margin: 0 0 2.8mm; padding-left: 6mm; }
li { margin: 0.5mm 0; }
blockquote { margin: 3mm 0; padding: 2mm 4mm; border-left: 2.5pt solid #9cc3dd; color: #374151; }
a { color: #155e91; text-decoration: none; }
code {
  font-family: "DejaVu Sans Mono", monospace;
  font-size: 8.2pt;
  background: #f1f5f9;
  padding: 0 0.6mm;
  border-radius: 1pt;
}
pre {
  background: #f4f6f8;
  border: 0.5pt solid #d9dee5;
  border-radius: 2pt;
  padding: 2.5mm 3mm;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 8pt;
  line-height: 1.35;
  margin: 2.5mm 0 3.5mm;
}
pre code { background: none; padding: 0; font-size: 7.8pt; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 2.5mm 0 4mm;
  font-size: 7.8pt;
  line-height: 1.3;
}
th, td { border: 0.5pt solid #c9d0d8; padding: 1.3mm 1.6mm; vertical-align: top; text-align: left; }
th { background: #eaf0f4; color: #123047; }
tr { break-inside: avoid; }
hr { border: none; border-top: 0.7pt solid #c9d0d8; margin: 5mm 0; }
img { max-width: 100%; }
"""


def render_pdf(
    documents: list[Document],
    output: Path = DEFAULT_OUTPUT,
    title: str = DEFAULT_TITLE,
    base_url: Path | None = None,
) -> int:
    """Render the bundle and return its page count.

    'output' defaults to dist/strength-app-docs.pdf under the portfolio root.
    'base_url' is the directory used to resolve relative asset paths; it
    defaults to the workspace recorded on the first document.
    """
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:  # pragma: no cover - optional dependencies
        raise RuntimeError(
            "PDF generation needs the optional docs dependencies and WeasyPrint's "
            "native libraries; run "
            "'python3 -m pip install -r scripts/requirements-docs.txt' and see "
            "https://doc.courtbouillon.org/weasyprint/stable/first_steps.html"
        ) from exc

    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if base_url is None:
        base_url = documents[0].workspace if documents else ROOT
    document = HTML(
        string=build_html(documents, title), base_url=str(Path(base_url).resolve())
    ).render()
    document.write_pdf(str(output))
    return len(document.pages)


def _print_list(documents: list[Document]) -> None:
    """Print the document list grouped by repository, for --list."""
    grouped: dict[str, list[Document]] = {}
    for document in documents:
        grouped.setdefault(document.repo.key, []).append(document)

    for docs in grouped.values():
        repo = docs[0].repo
        print(
            f"== {repo.label} ({repo.path.name}) - {len(docs)} "
            f"{_plural(len(docs), 'document')} =="
        )
        for document in docs:
            print(f"  {document.relative}\t{document.title}")
    print(
        f"{len(documents)} {_plural(len(documents), 'document')} across "
        f"{len(grouped)} {_plural(len(grouped), 'repository', 'repositories')}"
    )


EPILOG = """examples (run from the portfolio repository root):
  python3 scripts/docs_pdf.py
      Write dist/strength-app-docs.pdf from all three repositories:
      portfolio (strength-app), server (strength-training-app) and iOS (StrengthApp).
  python3 scripts/docs_pdf.py --list
      Print each repository's included documents and titles without rendering.
  python3 scripts/docs_pdf.py --repo server --repo ios
      Include only the server and iOS repositories (portfolio is omitted).
  python3 scripts/docs_pdf.py --no-private
      Exclude local private/docs notes from the bundle.
  python3 scripts/docs_pdf.py -o build/strength-app-docs.pdf --title "Strength App docs"
      Choose the output path and the cover/PDF title.
  python3 scripts/docs_pdf.py --include strength-training-app/private/docs/notes.md
      Add a Markdown file that is not under the default document paths.
  python3 scripts/docs_pdf.py --root /path/to/strength-app
      Use a different portfolio checkout root.
  python3 scripts/docs_pdf.py --help
      Show this help text again.

Install the optional rendering dependencies once:
  python3 -m venv .venv
  .venv/bin/pip install -r scripts/requirements-docs.txt

The PDF is generated locally; nothing is uploaded. The default output is ignored
by Git. Private notes are included when present, so do not share the PDF unless
you intend to share those notes too.
"""


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, collect documents and render the combined PDF.

    Run 'python3 scripts/docs_pdf.py --help' for the full option list and usage
    examples. Returns a process exit code: 0 on success, 1 on a collection or
    rendering error.
    """
    parser = argparse.ArgumentParser(
        prog="scripts/docs_pdf.py",
        description=(
            "Build one PDF from the documentation in the portfolio, Python server "
            "and iOS client repositories."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        metavar="PATH",
        help="portfolio checkout root containing both submodules (default: repository root)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        metavar="PATH",
        help="PDF path (default: <root>/dist/strength-app-docs.pdf)",
    )
    parser.add_argument("--title", default=DEFAULT_TITLE, help="cover and PDF title")
    parser.add_argument(
        "--repo",
        action="append",
        choices=("portfolio", "server", "ios"),
        metavar="KEY",
        help="include only this repository; repeatable (default: all three)",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="PATH",
        help="additional Markdown file below the root (repeatable)",
    )
    parser.add_argument(
        "--no-private",
        action="store_true",
        help="exclude local private/docs notes",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the repository-grouped document list and exit",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    all_repos = default_repos(root)
    selected = tuple(
        repo for repo in all_repos if args.repo is None or repo.key in args.repo
    )
    output = args.output if args.output is not None else root / "dist" / "strength-app-docs.pdf"

    try:
        documents = collect_documents(
            root=root,
            repos=selected,
            include=args.include,
            include_private=not args.no_private,
        )
        if args.list:
            _print_list(documents)
            return 0
        if not documents:
            raise RuntimeError("no Markdown documents found for the selected repositories")
        pages = render_pdf(documents, output, args.title, base_url=root)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    repo_count = len({document.repo.key for document in documents})
    print(
        f"wrote {Path(output).resolve()} "
        f"({len(documents)} documents across {repo_count} "
        f"{_plural(repo_count, 'repository', 'repositories')}, {pages} pages)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

