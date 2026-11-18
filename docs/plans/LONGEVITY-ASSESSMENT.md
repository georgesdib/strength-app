# Longevity assessment — aerobic adequacy, fitness and strength context

**Status:** approved 2026-11-18 by the owner. **Backend implemented 2026-11-18** — one
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
inside, below or unknown. It is not a target with a verdict, and no advice it generates is consumed
by any other subsystem. Reversal costs a decision record, not a refactor.

### DEC-LONGEVITY-02 — health measurements are their own consent class

The intelligence contract's `health` class applies to cardio minutes, time-in-zone and VO₂max. When
the configured model is off-device (DeepSeek), the iOS client sends those fields only with a
separate, explicit, default-off consent toggle that names the fields and the recipient. Plan and
prescription data keep their existing separate consent. On-device generation needs no consent.

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
| `features/cardio_metrics.py` | one pure `adequacy(...)` over an already-built summary: three frames, measured/estimated/unclassified and resistance splits, time-in-zone block with coverage, VO₂max block with `current | stale | absent`, per-pattern headroom. No DB reads, no cache rebuild |
| `GET /api/cardio/summary` | one additive `assessment` block. No new endpoint, no migration |
| Intelligence `longevity` capability | the same facts in an envelope (`ok`/`no_data`/`insufficient`, `as_of`, `coverage`, `limitations`, privacy `health`). Facts only — no prose |
| iOS | Today section = facts + prose from the configured model (on-device or DeepSeek); time-in-zone panel on the Cardio screen |
| Web | Longevity panel gains the same facts, prose from the configured model, and a visible "written by" line |

`time_in_zone` is already computed for continuity-eligible workouts and currently only reachable
through `tools/cardio_report.py`. This plan wires it into the product; it does not rebuild it.

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
- **Classification:** Apple METs first, then average heart rate as a share of a store-observed
  maximum (200 bpm today), then unclassified. Whole-workout classification is an estimate: a lifting
  session's average heart rate can read moderate or vigorous without sustained aerobic work, and an
  interval session's rests dilute it. Time-in-zone is the sample-based view and covers only
  continuity-eligible workouts — never merged into the weekly total.
- **VO₂max:** a consumer estimate, not a measurement; material error, and generated only during
  outdoor walking, running and hiking, so its presence tracks modality more than fitness. Absence is
  not evidence of poor fitness.
- **Strength context:** headroom is the configured volume budget, not a measurement of adaptation.
  The plan does not claim cardio caused a strength change, and nothing here is a strength verdict.

## 7. Acceptance

1. Golden fixtures for the arithmetic: moderate only, vigorous only, combined at the 2:1 rule, the
   150 boundary, unclassified-dominated, resistance-heavy, and a stale and an absent VO₂max.
2. iPhone and web render identical numbers from the same payload block.
3. The current-week frame contains no relation word; only a completed week is compared.
4. With the health consent off and DeepSeek selected, the facts render and the prose is
   deterministic.
5. Nothing in this plan writes a prescription, a rule or a stored decision.

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
