# CARDIO POLICY v1 — WHAT IS IMPORTED, KEPT, CLASSIFIED AND SHOWN

**Version:** `cardio-policy/v1`, 2026-11-17. Supersedes nothing.
**Status:** active policy for C2–C5. Nothing is implemented yet; this document is the specification the
implementation reads.
**Owner:** the athlete. Every number here is derived from [the C0 audit](CARDIO-C0-AUDIT.md); changes
require a version bump under §9, not an edit in place.

The rule this document exists to enforce: **nothing is decided in code that is not written here.**

## 1. What enters the backend

| Item | Treatment |
|---|---|
| Every HealthKit workout, all activity types | Imported, stored, displayed in activity history |
| Workout statistics (active energy, distance, HR average/min/max) | Imported where present |
| Heart-rate series inside workout windows | Imported for analytics modalities only (§4) |
| Heart rate outside workout windows | **Not imported**, except a 10-minute tail after each workout end (§4) |
| Routes (`HKWorkoutRoute`) | Deferred (810 files, 211 MB); no v1 metric needs them |
| Standalone metrics (resting HR, HRV, VO₂max, body mass, exercise minutes) | Imported as observations (§5) |

Measured basis: 1,431 workouts, 546,283 HR samples inside workout windows, ≈65 MB canonical at
~120 B/row.

## 2. Modality whitelist

**Analytics modalities** — classified, counted in WHO-equivalent minutes, eligible for time-in-zone:

| Modality | In store | Treatment |
|---|---|---|
| Walking | 558 | analytics |
| Running | 175 | analytics |
| Cycling | 118 | analytics |
| Swimming | 79 | analytics |
| Hiking | 5 | analytics |
| High-intensity interval training | 5 | analytics |
| Mixed cardio | 8 | analytics |
| Tennis / pickleball / badminton / squash | 12 | analytics (intermittent; see §6 floor) |
| Rowing, elliptical, stair climbing | 0 | analytics — whitelisted ahead of data, same rules |

**Import-only** — stored and displayed, never intensity-classified, never counted as aerobic minutes:
golf, fitness gaming, snowboarding, diving, cooldown, core training, kickboxing, mind and body, yoga,
flexibility, other, and every type not listed above. Unknown types default here, not to analytics.

**Resistance domain:** traditional and functional strength training are imported and reconciled
(`DEC-CARDIO-02`) and may produce aerobic minutes under `DEC-CARDIO-05`, but they never enter strength
volume, tonnage or set counts.

Promotion from import-only to analytics is a policy version bump, never a runtime setting.

## 3. Measurement classification

| Measurement | Class | Rule |
|---|---|---|
| Workout UUID, activity type, start, end, duration | **Mandatory** | Row is rejected without them |
| Source name, bundle id, model, device, creation date, timezone | **Mandatory** | Provenance (`DEC-CARDIO-14`) |
| `HKAverageMETs` | **Mandatory when present** | Tier 1 of `DEC-CARDIO-05`; authoritative, never recomputed |
| Active energy, distance, HR average/min/max statistics | **Mandatory when present** | Absence is recorded as absence, never zero |
| HR series inside the workout | **Optional** | Retail per §4 |
| Elevation, cadence, power, speed, stroke count, weather | **Optional** | Stored where present, unused by v1 metrics |
| Workout effort score, workout segments/activities | **Deferred** | Revisit when the app records them routinely |
| Sleep, clinical records, background HR | **Ignored** | Out of scope for this stage |

## 4. Heart-rate retention

- **Kept:** samples whose timestamp falls inside a non-resistance workout of an analytics modality, or
  inside any workout of the resistance domain (cheap, and enrichment needs them).
- **Kept, too:** a **10-minute tail after every workout end**, for heart-rate recovery. Measured:
  52,466 samples (≈6 MB) — cheap enough that dropping them would be arbitrary.
- **Dropped:** everything else — ≈502 k background samples. Background HR supports no v1 metric, and
  resting HR is a separate series HealthKit already aggregates.
- **Resolution:** full, as recorded. No downsampling at v1 — running and cycling arrive at ~55–60
  samples/min and the total is ≈65 MB. Revisit only if the canonical store exceeds 250 MB, and then by
  policy bump.
- **Quality:** a workout's series counts as usable for time-in-zone at ≥ 1 sample/min of duration.
  Measured medians: running 59.5, cycling 54.7, swimming 19.5, walking 1.8, **strength 0.1** — so lifting
  never produces a zone distribution, by data rather than by exception.

## 5. Standalone metrics

| Metric | Source rule | Minimum for display |
|---|---|---|
| Resting HR | Apple Watch only | ≥ 3 samples in the window |
| HRV (SDNN) | Apple Watch only | ≥ 3 samples in the window |
| VO₂max | Apple Watch only in the primary trend; other sources stored and labelled | ≥ 2 samples in 28 days |
| Body mass | Any source, labelled | ≥ 1 sample |
| Apple exercise minutes | Apple only; post-2021 series | ≥ 1 day of data in the window |

Third-party estimates are never merged into an Apple trend line; Athlytic's 25 VO₂max samples appear as
a separate, labelled series (`DEC-CARDIO-14`).

## 6. Data-quality thresholds per metric

| Metric | Gate |
|---|---|
| WHO-equivalent minutes | duration ≥ 5 min **and** a classification tier (METs or HR) |
| Moderate/vigorous split | as above; tier recorded per minute |
| Time in zone | HR series at ≥ 1 sample/min |
| Session frequency / modality mix | any imported workout |
| Pace at comparable HR | running/cycling, distance ≥ 1 km, ≥ 5 HR samples |
| Power at comparable HR | cycling, power present, ≥ 5 HR samples |
| Heart-rate recovery | peak sample within 60 s before the end **and** a post-workout sample within ±20 s of +60 s. Measured: 1,003 workouts (70 %). HRR at +120 s is the fallback; a negative drop is real (HR rose) and is never clamped to zero |
| Strength enrichment | matched workout with HR statistics or ≥ 1 HR sample |

The 5-minute floor removes 44 micro-workouts (3 %) from activity totals while leaving their record in
the history.

## 7. Import range, order and resumability

- **Range:** all available history, 2016-06-21 onwards. Nothing is truncated and nothing is back-filled
  beyond what HealthKit holds.
- **Shape:** one-time manual backfill, month by month, newest first; then anchored incremental sync on
  app foreground.
- **Resumability:** per-month checkpoint, idempotent on the HealthKit UUID, safe to re-run from any
  month without duplicating.
- **Expected volume:** 1,431 workouts and ≈546 k HR samples today — a backfill measured in minutes, not
  hours, on a home LAN.
- **Failure:** a failed month is retried, never skipped silently; a record absent from a later query
  becomes a status event (`DEC-CARDIO-04`), never a delete.

## 8. Link policy (numeric, as implemented)

| Case | Outcome |
|---|---|
| Interval overlap ≥ 0.90, one candidate | auto-link, `method = interval_overlap` |
| Interval overlap 0.60–0.90 | queue, `method = interval_overlap` |
| Interval overlap < 0.60 | no link |
| No interval; one session and one workout on the day | auto-link, `method = day_containment` |
| No interval; 2+ candidates on either side | queue |
| Workout already linked | queue |

Band version `link_v1`. Every link stores method, band version and inputs; unlink is an event.

## 9. Change control

1. A policy change is a version bump (`cardio-policy/v2`) with the audit evidence that forced it.
2. A change to a *calculation* is a `method_version` bump in the derived layer
   (`DEC-CARDIO-12`), independent of this policy.
3. Nothing in this policy may change a load, a set, a prescription or a schedule (`DEC-CARDIO-01`).
4. Values here are the inputs the implementation reads; a number that exists only in code is a defect.

## 10. Deliberately absent

Training-load impulse (TRIMP, sRPE × duration), combined fatigue scores, HR zones defined by anything
other than what `DEC-CARDIO-05` produces, VO₂max estimation, route analysis, sleep, clinical records,
and any per-athlete threshold learned from data. Each would need its own decision and its own evidence.

**Corrected 2026-11-17:** heart-rate recovery was listed here as not computable. It is computable for
70 % of workouts from the post-workout tail, and §4 and §6 were amended the same day. The original
claim was an assumption about sample density, not a measurement — the kind of thing this audit exists
to catch.
