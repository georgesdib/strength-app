# Documentation consolidation record

**Task branch snapshot:** 2026-11-10. The inventory and migration were performed on separate `docs-consolidation` branches from portfolio `main`, backend `development`, and iOS `development`. No submodule pointers were changed and no application behavior, database, CI configuration or deployment was changed.

## Canonical changes in this PR set

- The full 1,005-line iOS client phase plan from `StrengthApp` development commit `eecfd6fc33ad23c16ac43a8a00533becf7401567` is now at [`docs/plans/IOS-CLIENT-PLAN.md`](plans/IOS-CLIENT-PLAN.md), with substantive phase/history content preserved and cross-repository links qualified.
- Seven iOS server/client phase and watchOS contracts are now in [`docs/contracts/`](contracts/README.md). Backend and iOS former paths remain short pointers where needed; they are not duplicate full documents.
- Portfolio root/agent docs, backend AGENTS/docs index and iOS AGENTS/docs index now explain canonical shared-doc discovery and repository ownership.
- The owner confirmed ODROID-C4 hosts both the backend development server and backend main server. `PROMPT-ODROID.md` remains an active environment workflow; its instructions keep development and main-server contexts distinct and do not infer agent runtime from server role.

## Retained component authority

The backend root `ROADMAP.md` remains the live backend implementation-status source because the backend viewer, manifest and consistency/status tests directly consume that path/content. It is not copied into the portfolio, and portfolio indexes link to it without restating status. Backend API reference, Python/data architecture, migration implementation, backend-only operations, manifest/viewer and archives remain backend-owned. iOS build/test, UI/live-test and device-acceptance records remain iOS-owned. No unrelated archive or obsolete document was moved or deleted; uncertain or historical material remains at its original component path pending explicit review.

## Inventory and unresolved branch evidence

Read-only inventory reports were prepared for the supplied repository snapshots. Backend and iOS `main` are not the selected working bases; the iOS `development` branch already contains the moved client plan and agent docs. The watch contract status in the plan is branch-dependent: the plan snapshot says watch target code was not started, while separate watch branches exist. This PR set preserves the plan's source status and flags it for reconciliation rather than claiming a completion state. The backend public docs corpus contains additional project-wide training/evidence/methodology candidates whose paths feed its manifest, viewer, tests, configs or implementation. They remain in the backend for this migration to avoid breaking those consumers; this is a follow-up candidate inventory, not silently treated as resolved.
