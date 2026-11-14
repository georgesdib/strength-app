# Server/client contracts — canonical index

These contracts define cross-repository behavior and are authoritative in this portfolio repository. Server implementation, migrations, executable tests and API reference remain in `georgesdib/strength-training-app`; client implementation and Apple-specific acceptance remain in `georgesdib/StrengthApp`.

| Canonical contract | Scope | Current status | Implementation owner |
|---|---|---|---|
| [iOS Phase 1](IOS-PHASE-1-CONTRACT.md) | Pairing, authenticated read-only facade, acceptance | Completed (as recorded in linked plan) | Backend + iOS |
| [iOS Phase 2](IOS-PHASE-2-CONTRACT.md) | Online strength workflow, readiness, workout lifecycle | Completed; later amendments are cross-linked | Backend + iOS |
| [iOS Phase 3A](IOS-PHASE-3A-CONTRACT.md) | HealthKit readiness import | Completed/owner-accepted per linked plan | Backend + iOS |
| [iOS Phase 4](IOS-PHASE-4-CONTRACT.md) | Offline capture and ordered replay | Completed/owner-accepted per linked plan | Backend + iOS |
| [iOS R7](IOS-R7-CONTRACT.md) | Asynchronous prescription request | Completed per source plan | Backend + iOS |
| [iOS R8](IOS-R8-CONTRACT.md) | Active-workout plan editing | Completed per source plan | Backend + iOS |
| [watchOS Phase 6](IOS-WATCH-CONTRACT.md) | Watch companion contract | Phase 6.7 owner-confirmed 2026-11-14 (W1–W12); only the R rollback dry run remains | Backend + iOS/watchOS |

The iOS client plan is in [`../plans/IOS-CLIENT-PLAN.md`](../plans/IOS-CLIENT-PLAN.md). The backend HTTP API reference, Python architecture, schemas, migrations and implementation details remain backend-owned; this contract index does not replace those documents.
