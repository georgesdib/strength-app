# Project plans and roadmap navigation

This is the portfolio-level entry point for shared project plans. The portfolio owns cross-repository phase plans and the canonical shared contracts; component repositories own code-coupled implementation guides and component-specific operational status.

## Canonical shared plans

- [iOS client phase plan](IOS-CLIENT-PLAN.md) — cross-repository milestones, scope, dependencies, acceptance criteria, architecture boundaries, and historical completion records. It reflects the Phase 6 closure: 6.0–6.7 complete, with 6.7 owner-confirmed 2026-11-14.
- [Athlete Feedback & Coaching (AFC) plan](AFC.md) — composition rules over the backend adherence/VBT/feedback services, the shared evidence contract, and phases AFC-2 (completed), AFC-2i (implemented native report), AFC-3, AFC-4 and the separate AFC-5. Backend code paths stay authoritative in `strength-training-app`; this plan is the canonical cross-repository statement.
- [Server/client contract index](../contracts/README.md) — canonical contracts and ownership of their implementation.

## Component roadmap and active status

- [Backend implementation roadmap](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md) remains the authoritative live status, next actions, and resume checklist for backend implementation. It is intentionally not copied here: the backend documentation viewer and status/consistency tests consume its exact local path and content. Do not create a competing copy; when its scope is cross-repository, update this index and the relevant canonical portfolio plan/contract in the same task.
- iOS-specific build, UI, live-test and device-acceptance records remain in [StrengthApp documentation](https://github.com/georgesdib/StrengthApp/tree/development/docs); shared iOS phases are governed by the canonical plan above.

## Status and change control

The plan records current status plus historical completion evidence. Do not infer completion from branch existence or code alone; reconcile against implementation, acceptance record and owner decision before changing status. Physical Apple Watch acceptance was owner-confirmed 2026-11-14; only the R rollback dry run remains. Completed phase records remain historical evidence and are not deleted. Superseded documents must point to their replacement.
