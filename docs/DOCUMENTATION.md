# Documentation ownership and placement

The portfolio has three repositories. Documentation must have one canonical home; the copy in
the owning repository is authoritative and every other repository links to it.

## Ownership table

| Kind of document | Owner | Examples |
|---|---|---|
| Portfolio process, cross-repo agent routing, machine handoff, documentation policy | This repository | `AGENTS.md`, `docs/agent/*`, this file |
| Training methodology, evidence, readiness, prescriptions, loads, sets, progression, scoring | `strength-training-app/` | `docs/METHODOLOGY.md`, `docs/READINESS.md`, `docs/WORKOUT-GENERATION.md` |
| Server architecture, data model, API, migrations, server web UI, server tests | `strength-training-app/` | `docs/ARCHITECTURE.md`, `docs/DATA-MODEL.md`, `docs/API.md`, `docs/WEB-UI.md` |
| Server-side design contracts for the iOS API | `strength-training-app/` | `docs/design/IOS-*-CONTRACT.md` |
| iOS client plan, client UI/UX, iPhone user guide, device acceptance | `StrengthApp/` | `docs/IOS-CLIENT-PLAN.md`, `USER-GUIDE.md`, `DEVICE-ACCEPTANCE.md` |
| iOS build/test/live-test/agent guidance | `StrengthApp/` | `AGENTS.md`, `docs/AGENT-*.md` |

## Decision rules

1. If it defines a training decision or server behaviour, it belongs to the server repository.
2. If it describes how the iPhone app behaves, how it is built, or how it is accepted, it belongs
   to the iOS repository.
3. If it coordinates machines, repositories or agents, it belongs to this portfolio repository.
4. The server owns the client/server contract because Python is authoritative for training
   decisions. iOS docs link to the server contract; they do not mirror it.
5. If a document genuinely serves two owners, keep the authoritative explanation in the owning
   repository and put a short pointer in the other. Never maintain two full copies.

## Cross-repository links

- From one submodule to the other, use an absolute GitHub URL on the `development` branch, for
  example:
  `https://github.com/georgesdib/strength-training-app/blob/development/docs/design/IOS-WATCH-CONTRACT.md`.
- Relative links are correct only within the same repository.
- Do not link a public document to `private/` or to another repository's local filesystem path.
- When a document moves, update every inbound link in both repositories and in the server docs
  manifest/index. The server documentation tests fail on broken relative links and on any
  unclassified Markdown file under `docs/`.

## Plans

- A plan lives with the work it plans. A server implementation plan belongs to the server repo; an
  iPhone client plan belongs to the iOS repo.
- A cross-repo plan stays in the repository that owns the majority of the work, with links to the
  companion plan or contract.
- Completed plans move to the owning repository's archive (where one exists), or stay as history
  with a clear completed status. Do not leave the client plan in the server docs index.

## Moving a document — checklist

1. Decide the owner using the table above.
2. Move the file into the owning repository's docs tree.
3. Update the owning repository's index and, for the server, `docs/manifest.yaml`.
4. Rewrite inbound links in both repositories to the new canonical location.
5. Update tests that assert document paths or manifest coverage.
6. Confirm the old path no longer exists and no duplicate copy remains.
7. Do not commit until the owner asks; local review is expected first.
