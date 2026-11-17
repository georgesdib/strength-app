# CARDIO POLICY v1 — WHAT IS IMPORTED, KEPT, CLASSIFIED AND SHOWN

**Version:** `cardio-policy/v4`, 2026-11-17. Supersedes `cardio-policy/v3` (same day): the continuity
test is `and`, not `or` (§4), because coverage alone admitted sparse series. v3 split the timeline
between the export and HealthKit; v2 moved golf to analytics and replaced the samples-per-minute gate.
See §10.
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
| Standalone metrics | Resting HR, HRV and body weight into `healthkit_readiness`; VO₂max into `measurement` (§5) |

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
| Golf | 30 | analytics — intermittent, and Apple's METs include cart and pause time, so its minutes are weaker evidence than a walk of the same length |

**Import-only** — stored and displayed, never intensity-classified, never counted as aerobic minutes:
fitness gaming, snowboarding, diving, cooldown, core training, kickboxing, mind and body, yoga,
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
- **Sync:** heart-rate samples carry their own anchor. A workout and its recovery tail may arrive in
  separate syncs, and a tail that has not arrived is **pending**, never an absence (`DEC-CARDIO-04`).
- **Quality — continuity, not rate.** A series is usable for time-in-zone when its median inter-sample
  gap is ≤ 30 s, **and** no internal gap exceeds 120 s, **and** samples cover ≥ 50 % of the workout's
  duration. Each condition alone lies. Coverage alone admits three samples across two hours; the
  median alone admits a cluster of samples at the start and one hours later, which is exactly what a
  strength session looks like. Measured on the real corpus, the first two versions admitted 336 of 381
  strength workouts to time-in-zone; the widest-gap condition reduces that to zero and leaves 275
  eligible workouts overall. A samples-per-minute threshold is
  rejected because it measures the recording mode rather than the data: density is bimodal across the
  history (chest strap 2016–2018 and live recording 2026 sit at 55–60 samples/min; wrist background
  sampling 2019–2025 sits at 0.1–0.7), so a fixed rate would admit some years and reject others for the
  same physiological evidence. Under the continuity test, lifting still produces no zone distribution —
  its median gap is minutes, not seconds — but for a reason the data states rather than a rate someone
  chose.

## 5. Standalone metrics

| Metric | Store | Source rule | Minimum for display |
|---|---|---|---|
| Resting HR | `healthkit_readiness` | Apple Watch only | ≥ 3 samples in the window |
| HRV (SDNN) | `healthkit_readiness` | Apple Watch only | ≥ 3 samples in the window |
| Body weight | `healthkit_readiness` | Any source, labelled | ≥ 1 sample |
| VO₂max | `measurement`, `metric_key = 'vo2max'` | Apple in the primary trend; other sources stored with their own `method` label | ≥ 2 samples in 28 days |
| Apple exercise minutes | cardio corpus, daily series (C5) | Apple only; post-2021 series | ≥ 1 day of data in the window |

No new metric table is introduced: the backend already separates state (`healthkit_readiness`) from
outcome (`measurement`), and VO₂max is an outcome. A re-import is idempotent on `measurement.external_id`.

Third-party estimates are never merged into an Apple trend line; Athlytic's 25 VO₂max samples appear as
a separate, labelled series (`DEC-CARDIO-14`).

## 6. Data-quality thresholds per metric

| Metric | Gate |
|---|---|
| WHO-equivalent minutes | duration ≥ 5 min **and** a classification tier (METs or HR) |
| Moderate/vigorous split | as above; tier recorded per minute |
| Time in zone | continuity: median gap ≤ 30 s **and** widest gap ≤ 120 s **and** ≥ 50 % of duration covered |
| Session frequency / modality mix | any imported workout |
| Pace at comparable HR | running/cycling, distance ≥ 1 km, ≥ 5 HR samples |
| Power at comparable HR | cycling, power present, ≥ 5 HR samples |
| Heart-rate recovery | peak sample within 60 s before the end **and** a post-workout sample within ±20 s of +60 s. Measured: 1,003 workouts (70 %). HRR at +120 s is the fallback; a negative drop is real (HR rose) and is never clamped to zero |
| Strength enrichment | matched workout with HR statistics or ≥ 1 HR sample |

The 5-minute floor removes 44 micro-workouts (3 %) from activity totals while leaving their record in
the history.

## 7. Import range, split and resumability

The timeline is split, and the split is by construction rather than by scheduling
(`DEC-CARDIO-18`).

**History — from the file.** Everything from 2016-06-21 up to `history_cutoff` is promoted offline
from `export.xml`: one time, CLI only, re-runnable, never through the app and never exposed as an
endpoint. `history_cutoff` is the maximum sample timestamp in the file, recorded by the promotion — not
a date chosen in advance.

**New data — through the app.** Anchored queries with `start > history_cutoff` and a **7-day lookback**,
on app foreground. Workouts and heart-rate samples are anchored **separately**: a recovery tail can
arrive after the workout that owns it, and a tail that has not arrived is pending, never an absence.

**Identity.** One column, two sources (`DEC-CARDIO-09`): the HealthKit UUID for rows from the app, a
`sha256` content key for rows from the export. They never meet, because nothing before
`history_cutoff` is ever uploaded by the app.

**Volume.** 1,431 workouts, ≈546 k in-workout and tail samples. The promotion is minutes; the
incremental path carries a handful of sessions a week.

**Failure and deletion.** A failed sync is retried, never skipped silently. Absence from a later query
becomes a status event (`DEC-CARDIO-04`), never a delete. **Deletion inside the history is
undetectable** — a static file has no tombstones — and a gap needs a fresh export rather than a backfill
re-run.

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

1. A policy change is a version bump (`cardio-policy/v4` next) with the audit evidence that forced it.
2. A change to a *calculation* is a `method_version` bump in the derived layer
   (`DEC-CARDIO-12`), independent of this policy.
3. Nothing in this policy may change a load, a set, a prescription or a schedule (`DEC-CARDIO-01`).
4. Values here are the inputs the implementation reads; a number that exists only in code is a defect.

## 10. Change log

| Version | Date | Change | Evidence |
|---|---|---|---|
| v1 | 2026-11-17 | First policy | [C0 audit](CARDIO-C0-AUDIT.md) |
| v2 | 2026-11-17 | Golf moved to analytics; time-in-zone gate replaced by a continuity test; recovery retention and sync rules made explicit | Density is bimodal by recording mode (2016–2018 and 2026 at 55–60 samples/min, 2019–2025 at 0.1–0.7), and 70 % of workouts carry a computable HRR |
| v3 | 2026-11-17 | Timeline split: history promoted from the export, new data through the app; `history_cutoff` and the 7-day lookback defined; content-key identity for file rows | `DEC-CARDIO-18`; the export carries no sample UUIDs |
| v4 | 2026-11-17 | Continuity needs density, no long internal gap, and span | Coverage alone admitted sparse series; the median alone admitted strength sessions (a sample cluster plus one hours later). 336 of 381 strength workouts passed the first two versions |

## 11. Deliberately absent

Training-load impulse (TRIMP, sRPE × duration), combined fatigue scores, HR zones defined by anything
other than what `DEC-CARDIO-05` produces, VO₂max estimation, route analysis, sleep, clinical records,
and any per-athlete threshold learned from data. Each would need its own decision and its own evidence.

**Corrected 2026-11-17:** heart-rate recovery was listed here as not computable. It is computable for
70 % of workouts from the post-workout tail, and §4 and §6 were amended the same day. The original
claim was an assumption about sample density, not a measurement — the kind of thing this audit exists
to catch.
