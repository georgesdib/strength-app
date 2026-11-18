# Project plans and roadmap navigation

This is the portfolio-level entry point for shared project plans. The portfolio owns cross-repository phase plans and the canonical shared contracts; component repositories own code-coupled implementation guides and component-specific operational status.

## Canonical shared plans

- [iOS client phase plan](IOS-CLIENT-PLAN.md) — cross-repository milestones, scope, dependencies, acceptance criteria, architecture boundaries, and historical completion records. It reflects the Phase 6 closure: 6.0–6.7 complete, with 6.7 owner-confirmed 2026-11-14.
- [Athlete Feedback & Coaching (AFC) plan](AFC.md) — composition rules over the backend adherence/VBT/feedback services, the shared evidence contract, and phases AFC-2 (completed), AFC-2i (implemented native report), AFC-3, AFC-4 and the separate AFC-5. Backend code paths stay authoritative in `strength-training-app`; this plan is the canonical cross-repository statement.
- [Training Intelligence plan](TRAINING-INTELLIGENCE.md) — read-only intelligence capability layer, standalone MCP server, iOS Foundation Models adapters and phases INT-1 to INT-13. **Supersedes** the forward-planning content of [`strength-training-app/docs/LLM-INTEGRATION-PLAN.md`](https://github.com/georgesdib/strength-training-app/blob/development/docs/LLM-INTEGRATION-PLAN.md) and the Apple Intelligence/PCC items in the iOS client plan; §16 records what remains in force and what was withdrawn. Status: delivered 2026-11-15, extended 2026-11-16 — INT-1 to INT-8 closed, INT-7b/7c closed, INT-10 (local daily reminder nudge) implemented with physical-device acceptance outstanding, INT-11 (Explain the System) implemented and closed with documented limitations and its device/release items owner-closed 2026-11-17, INT-12 (web search/RAG) deferred, INT-13 (Today summary card) owner-closed 2026-11-17, INT-4c parked, and INT-9 deferred until iOS 27.3. The verified starting state is in the [implementation audit](TRAINING-INTELLIGENCE-AUDIT.md).
- [C0 audit](CARDIO-C0-AUDIT.md) — measured HealthKit inventory, coverage, volume and session
  matchability from the owner's 2026-11-17 export, plus the intensity concordance and cascade
  coverage; corrects several decisions in the plan. Status: measured 2026-11-17.
- [Cardio policy](CARDIO-C1-POLICY.md) — the versioned import, retention, quality-gate and link values
  the cardio implementation reads; changes only by version bump. Status: active (`cardio-policy/v4`),
  2026-11-17.
- [Cardio stage plan](CARDIO-STAGE.md) — HealthKit-first ingestion, backend-owned canonical cardio data, overlap-based strength reconciliation, cardiovascular and longevity monitoring. **Delivers** the ROADMAP §4.13a A0/A1 evidence (data audit, capture) and **defers** A2/A3 (impulse, shadow load) to v1.6 proper, which remains open. Status: **completed 2026-11-18** — deployed at backend release 1.6.0, owner device acceptance recorded. Deferred items (deletion detection, test debt) are listed in its §14.
- [Server/client contract index](../contracts/README.md) — canonical contracts and ownership of their implementation.

## Component roadmap and active status

- [Backend implementation roadmap](https://github.com/georgesdib/strength-training-app/blob/development/ROADMAP.md) remains the authoritative live status, next actions, and resume checklist for backend implementation. It is intentionally not copied here: the backend documentation viewer and status/consistency tests consume its exact local path and content. Do not create a competing copy; when its scope is cross-repository, update this index and the relevant canonical portfolio plan/contract in the same task.
- iOS-specific build, UI, live-test and device-acceptance records remain in [StrengthApp documentation](https://github.com/georgesdib/StrengthApp/tree/development/docs); shared iOS phases are governed by the canonical plan above.

## Status and change control

The plan records current status plus historical completion evidence. Do not infer completion from branch existence or code alone; reconcile against implementation, acceptance record and owner decision before changing status. Physical Apple Watch acceptance was owner-confirmed 2026-11-14 (W1–W12 and R). Completed phase records remain historical evidence and are not deleted. Superseded documents must point to their replacement.
