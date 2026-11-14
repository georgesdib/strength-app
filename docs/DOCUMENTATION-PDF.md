# Combined documentation PDF

The portfolio owns the tool that renders all three documentation sets:
[scripts/docs_pdf.py](../scripts/docs_pdf.py). It builds one searchable PDF
from the portfolio repository, the Python server repository
(`strength-training-app/`) and the iOS/watchOS repository
(`StrengthApp/`).

The previous server-only tool lived at
`strength-training-app/tools/docs_pdf.py`. It moved to the portfolio
because the bundle now spans repositories; do not duplicate it in a component
repository.

## Included documents

| Repository | Default root documents | Additional Markdown |
|---|---|---|
| Portfolio (strength-app) | `README.md`, `AGENTS.md` | every file below `docs/`, plus `private/docs/` when present |
| Server (strength-training-app) | `README.md`, `USER-GUIDE.md`, `ROADMAP.md`, `AGENTS.md`, `CHANGELOG.md` | every file below `docs/`, plus `private/docs/` when present |
| iOS client (StrengthApp) | `README.md`, `USER-GUIDE.md`, `DEVICE-ACCEPTANCE.md`, `WATCH-ACCEPTANCE.md`, `AGENTS.md` | every file below `docs/`, plus `private/docs/` when present |

Use `--list` to print the exact set without rendering, or
`--include PATH` to add another Markdown file below the checkout root.
`--repo portfolio`, `--repo server` and
`--repo ios` can be repeated to render a subset.

## Install dependencies

Run from the portfolio repository root. The dependencies are optional; the
server and iOS applications do not need them.

~~~bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements-docs.txt
~~~

`Markdown` converts the source files and `WeasyPrint`
renders the HTML to PDF. WeasyPrint also needs its native Pango, HarfBuzz and
font libraries; if the import fails, follow its first-steps installation guide.
The requirements file is the canonical Python dependency list for this tool.

## Run

~~~bash
# Default PDF: dist/strength-app-docs.pdf
python3 scripts/docs_pdf.py

# Full option list and examples
python3 scripts/docs_pdf.py --help

# Inspect what would be included
python3 scripts/docs_pdf.py --list

# Render only the server and iOS documentation
python3 scripts/docs_pdf.py --repo server --repo ios

# Exclude local private notes
python3 scripts/docs_pdf.py --no-private

# Choose an output path and title
python3 scripts/docs_pdf.py -o build/strength-app-docs.pdf --title "Strength App docs"
~~~

The script accepts these options:

| Option | Purpose |
|---|---|
| `--root PATH` | Use a different portfolio checkout root. |
| `--output PATH`, `-o PATH` | Write the PDF to this path. |
| `--title TEXT` | Set the cover and PDF title. |
| `--repo KEY` | Include only `portfolio`, `server` or `ios`; repeatable. |
| `--include PATH` | Add a Markdown file below the root; repeatable. |
| `--no-private` | Exclude `private/docs/` notes. |
| `--list` | Print the repository-grouped document list and exit. |
| `--help` | Show usage, examples and dependency instructions. |

## What the PDF contains

- A cover listing the three source repositories and their document counts.
- A contents page grouped by repository, with each document's repository-labelled
  path and its page number.
- A full-page divider for each repository, numbered (for example,
  "Repository 2 of 3") and colour-coded.
- A repository badge and source path above every document.
- A running page header that names the owning repository, so a page remains
  identifiable when printed or copied out of context.
- Internal PDF links between bundled documents. Links to code, configuration or
  unbundled files remain readable labels instead of becoming dead links.

## Privacy and generated files

`private/docs/` trees are local, git-ignored notes. They are included
by default, so the generated PDF may contain personal material. Do not commit,
upload or share the PDF unless you intend to share those notes. The default
output lives below `dist/`, which is git-ignored; the tool never
uploads anything.

## Tests

~~~bash
python3 -m unittest discover -s tests -v
~~~

The tests use temporary fixtures and standard-library `unittest`, so
they run without the PDF dependencies. The end-to-end PDF smoke test is skipped
unless `Markdown` and `WeasyPrint` are installed.

## Submodules

The tool reads the current working trees of all three repositories. Initialize
the submodules first if the checkout does not have them:

~~~bash
git submodule update --init --recursive
~~~

If a selected repository directory is missing, the tool stops with a clear
"repository not found" error rather than producing a partial PDF.

## Ownership

The portfolio repository is the canonical home for this cross-repository
tooling. Update this page, the root `README.md`, the docs index and
the tests when the tool's behaviour changes. Keep component-specific
documentation in its owning repository.

