# Longevity assessment — aerobic adequacy, fitness and strength context

**Status:** closed 2026-11-18; released in 1.7.0 and corrected in 1.7.1 (correctness, privacy
and integration hardening; no product-decision change). Implemented as one
`adequacy()` function, the `assessment` block on `GET /api/cardio/summary` and the phone route, the
golden fixtures, and the `get_longevity_assessment` capability behind MCP tool 11, the iOS
intelligence route and the chat dossier. The iOS Today section, the health-consent toggle, the time-in-zone panel and the web panel are
implemented (web prose is on demand, not automatic). This plan supersedes the v1.6.x cardio-impulse
deliverable (ROADMAP §4.13a A2/A3).

**One sentence:** three questions get one deterministic answer each, one consent switch guards the
sensitive part, and a model may say what to do about it without the app ever prescribing.

| # | Question | Answer surface |
|---|---|---|
| 1 | Am I doing enough aerobic exercise? | moderate-equivalent minutes against the WHO reference |
| 2 | Is my cardiorespiratory fitness appropriate? | latest VO₂max, its date, and whether it can be read at all |
| 3 | Am I keeping my strength? | per-pattern volume headroom and comparable-exposure context, advisory only |

## 1. Product rules

1. **The assessment is context; the advice is advisory.** The 150–300 minute band is reported, not
   scored. No pass/fail, no streak, no daily target.
2. **Advice may be warm and directive and is never wired to anything.** It reaches no prescription,
   no load, no set count, no rule and no stored decision. Ignoring it costs nothing.
3. **The facts never depend on a model.** Every number is computed by Python and rendered even when
   the model is unavailable. Only the prose degrades.
4. **No new monitoring obligation.** Nothing here notifies, chases or scores the athlete.
5. **Missing is unknown, never zero.** An incomplete assessment says so; unclassified minutes are
   reported as unclassified.

## 2. Decisions

### DEC-LONGEVITY-01 — the WHO band is context, advice is advisory

The weekly adequacy figure is compared with the WHO 150–300 minute reference band and described as
below, within (150–300), above or unknown. The API key for the within state is `inside`; clients
render it as "within". Above 300 is contextual, never a maximum safe dose or a warning. It is not a
target with a verdict, and no advice it generates is consumed by any other subsystem. Reversal costs
a decision record, not a refactor.

### DEC-LONGEVITY-02 — health measurements are their own consent class

The intelligence contract's `health` class applies to cardio minutes, time-in-zone and VO₂max. When
the configured model is off-device (DeepSeek), the iOS client sends those fields only with a
separate, explicit, default-off consent toggle that names the fields and the recipient. The web
narration route enforces the same boundary server-side: a health-class envelope requires an explicit
`health_consent` flag, and the browser discloses the configured provider/model before setting it.
Plan and prescription data keep their existing separate consent. On-device generation needs no
consent.

### DEC-LONGEVITY-03 — the cardio impulse is retired, not deferred

TRIMP, sRPE-impulse, acute:chronic ratios, cardio readiness scores and unified fatigue scores are
closed as product direction. §4.13a A2/A3 is superseded. Time-in-zone classification of stored heart
rate samples is **not** an impulse: it adds no load model, no cumulative score and no time constant,
and it is the only cardio computation this plan adds.

### DEC-LONGEVITY-04 — no VO₂max reference category

No age/sex band, no percentile, no new profile field. The athlete's age and sex are not stored and
will not be added for this. Apple Health already bands Cardio Fitness by age and sex; reproducing it
would be the duplication this plan exists to avoid. The app reports the value, its date, its source
and whether it is current, stale or absent.

### DEC-LONGEVITY-05 — the model restates arithmetic, it never performs it

Per-pattern headroom comes from `prescribe/volume_budget.py` and the weekly ledger. The model
receives the numbers; it may not derive, rank or substitute. It may not reorder, add or replace an
exercise. That keeps one planner in the system.

## 3. The three time frames

| Frame | Content | Judgement |
|---|---|---|
| Last completed week | minutes, moderate/vigorous, moderate-equivalents, relation to the reference band | the only place the relation is stated |
| Current week | minutes so far, days and sessions remaining | progress only, never "below" |
| Coming week | advice: aerobic suggestion plus per-pattern volume headroom | advisory |

A completed week is required for the relation because a week-to-date reading would report "below"
every Monday. The advice is told the weekday and the sessions remaining, so it can be forward-looking
without scolding.

## 4. Where each part lives

| Layer | Responsibility |
|---|---|
| `features/cardio_metrics.py` | one pure `adequacy(...)` over an already-built summary: three frames, measured/estimated/unclassified and resistance splits, time-in-zone block with coverage, VO₂max block with `current`/`stale`/`absent`, per-pattern headroom. No DB reads, no cache rebuild |
| `GET /api/cardio/summary` | one additive `assessment` block. No new endpoint, no migration |
| Intelligence `longevity` capability | the same facts in an envelope (`ok`/`no_data`/`insufficient`, `as_of`, `coverage`, `limitations`, privacy `health`). Facts only — no prose |
| iOS | Today section = facts + prose from the configured model (on-device or DeepSeek); health-tool execution is limited to the consent-aware allowlist; time-in-zone panel on the Cardio screen |
| Web | Longevity panel reads the same canonical `assessment` block (no second adequacy calculation), requests time-in-zone and headroom deliberately, and gates prose from the configured model behind a health-data disclosure naming the provider/model |

Before 1.7.0, `time_in_zone` was only reachable through `tools/cardio_report.py`. This plan wired
it into the product. The 1.7.1 corrective release replaced its equal-per-sample allocation with
elapsed-time integration, clipping and explicit coverage (see §6.1); the block and the continuity gate
are otherwise the same.

## 5. Prose rules

- The model states the computed relation, names what is missing, and may recommend activity. It may
  mention the programme's remaining volume, which it receives.
- It may not generate numbers, turn context into a target, claim causation, or diagnose.
- Advice may be ignored; nothing downstream reads it.
- If the model is unavailable, a configured-but-keyless DeepSeek path, or the consent is off, the
  durable fallback is a deterministic sentence built from the same facts and labelled as such.

## 6. Methodology and limits

- **Aerobic reference:** WHO 150–300 min moderate or 75–150 min vigorous per week, combined by the
  conventional 1 vigorous = 2 moderate equivalence. A convention, not a validated conversion.
- **Classification:** Apple METs first, then average heart rate as a share of the effective
  settings-profile maximum heart rate (`cardio.max_hr_bpm`, default 200 bpm, 120–250, effective-dated),
  then unclassified. Changing it reclassifies cached history on the next summary read and
  recomputes time-in-zone on the next request (`CARDIO-STAGE.md`, `DEC-CARDIO-05` post-completion
  amendment). The fallback mean uses only `association = 'workout'` samples inside the workout's
  own interval; the ten-minute recovery tail is retained in the corpus but is never exercise
  intensity. Whole-workout classification is an estimate: a lifting session's average heart rate
  can read moderate or vigorous without sustained aerobic work, and an interval session's rests
  dilute it.
- **Time-in-zone:** only continuity-eligible workouts, never merged into the weekly total. Zone
  time is the elapsed time between adjacent workout samples, clipped to the workout. The sample at
  *t* describes *[t, next_t)*; the final sample closes no interval; unobserved time (before the
  first sample, after the last, or across a gap wider than 120 s) is not extrapolated into a zone.
  Covered, workout and unobserved minutes are reported separately, and continuity eligibility is
  reported separately from temporal coverage. This is not a clinical zone-duration measurement.
- **VO₂max:** a consumer estimate, not a measurement; material error, and generated only during
  outdoor walking, running and hiking, so its presence tracks modality more than fitness. Absence is
  not evidence of poor fitness.
- **Strength context:** headroom is the configured volume budget, not a measurement of adaptation.
  The plan does not claim cardio caused a strength change, and nothing here is a strength verdict.

### 6.1 Corrective release 1.7.1

Verified against the 1.7.0 code and corrected without reopening the product decisions:

| Finding | Correction | Evidence |
|---|---|---|
| Health consent was advertisement-only in the off-device chat | The dispatcher builds an explicit per-request allowlist from the advertised tools and rejects unadvertised health/plan tools before their provider is called | `DeepSeekChatTests` health/plan/unknown-tool cases |
| Recovery-tail samples could influence intensity | Classification and time-in-zone read only `association = 'workout'` samples inside the workout interval; tails remain in the corpus | `test_cardio_metrics.py` tail/interval cases |
| Time-in-zone spread workout duration equally over samples | Elapsed-time integration, workout clipping, no allocation across gaps > 120 s or for the final sample, explicit covered/workout/unobserved coverage | uniform/uneven/partial/large-gap/boundary cases |
| A week above 300 minutes read as "inside" | `relation` gains `above`, and both clients describe the upper bound as context, not a maximum safe dose | 150/300/149.9/300.1 cases in backend and iOS |
| New HR samples did not invalidate the classification cache | Ingestion drops a cheap state marker; an identical re-import is a no-op | cache-invalidation test |
| Web panel mixed a four-week average with the weekly WHO band | The panel consumes only `/api/cardio/summary` `assessment`, shows last-week/current-week separately, and requests optional blocks deliberately | static + Node panel tests, shared fixture |
| VO₂max provenance was incomplete | Value, unit, date, source/method and `current`/`stale`/`absent` are presented on both clients; missing is not poor fitness | iOS and web presentation tests |
| Remote narration had no web privacy boundary | Health-class capabilities require an explicit `health_consent` flag and a browser disclosure naming the configured provider/model | `test_web_narrate.py` consent cases |

Limitations that remain: sample coverage is reported, not imputed, so a sparse recording yields
less zone time rather than a clinically precise estimate; whole-workout classification is still an
estimate; VO₂max remains a consumer estimate with no age/sex category.

## 7. Acceptance

1. Golden fixtures for the arithmetic: moderate only, vigorous only, combined at the 2:1 rule, the
   150 boundary, unclassified-dominated, resistance-heavy, and a stale and an absent VO₂max.
2. iPhone and web render identical numbers from the same payload block.
3. The current-week frame contains no relation word; only a completed week is compared.
4. With the health consent off and DeepSeek selected, the facts render without narration, and a
   health tool returned by the model is rejected without a provider call. The deterministic facts do
   not depend on the model.
5. Nothing in this plan writes a prescription, a rule or a stored decision.
6. Recovery-tail samples do not change workout classification or time-in-zone.
7. Time-in-zone zone totals never exceed the elapsed time actually represented by valid samples.
8. Adequacy is below, within or above the band at 150, 300 and immediately outside it; "above" is
   not described as excessive or harmful.
9. New heart-rate samples for an imported workout invalidate the classification cache; identical
   re-imports do not.
10. Web and iOS decode the same assessment fixture (byte-identical in both repositories) and the
    web panel does not compute adequacy or compare a four-week average with the weekly band.

## 8. Not in scope

TRIMP and TRIMP-like load · acute:chronic ratios · cardio readiness or unified fatigue scores ·
HRV-based readiness changes · automatic modification of strength or cardio prescription ·
generic trend charts duplicating Apple Health · Watch changes · notifications · strength
deterioration verdicts · VO₂max categories · age/sex storage · new tables or migrations.

## 9. Rollback

Remove the `assessment` block and the iOS/web sections; the capability and tool are additive and can
be unregistered. No schema, no migration, no stored data to unwind.

## 10. Open items

- Resting-heart-rate findings are **not** in this plan. The baseline machinery exists
  (`features/readiness_baseline.py`); a sustained-deviation finding would be a separate decision, and
  it sits on the readiness surface frozen by Phase 5A until 2027-01-22.
- A strength-preservation verdict needs numeric gates and the Phase 5A gate first (LIM-61).
- No open longevity product question remains: `Q14` closed with `DEC-LONGEVITY-03`; the Phase 5A
  evidence gate (`Q30`) is tracked in the monitoring register, not in this plan.
