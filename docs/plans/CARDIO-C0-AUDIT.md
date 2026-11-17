# C0 AUDIT — HEALTHKIT EXPORT AND SESSION MATCHABILITY

**Status:** measured 2026-11-17 against the owner's Apple Health export. This is the C0 deliverable of
[the cardio stage plan](CARDIO-STAGE.md); it records numbers, not opinions, and it changes three
decisions in that plan (§7).

**Sources.** `private/export.zip` (126 MB archive, 2.0 GB `export.xml`, 870 entries, exported
2026-11-17 17:56) parsed with a stdlib streaming parser into a throwaway store at
`private/c0/staging.sqlite`; and the production database, read **read-only** over SSH
(`file:…?mode=ro`, schema `0063`), copied into a local read-only snapshot for joins.

**Data handling.** Everything lives under `private/`, which is gitignored. Nothing was written to the
server, no row was amended, and no health data left the machine. Delete `private/c0/` to remove it.

## 1. Inventory

1,431 workouts, 2016-06-21 → 2026-11-14.

| Activity | n | Activity | n |
|---|---|---|---|
| Walking | 558 | Snowboarding | 15 |
| Traditional strength training | 369 | Functional strength training | 12 |
| Running | 175 | Pickleball | 9 |
| Cycling | 118 | Mixed cardio | 8 |
| Swimming | 79 | Underwater diving | 8 |
| Golf | 30 | HIIT | 5 |
| Fitness gaming | 22 | Hiking | 5 |

By year: 2016 19 · 2017 118 · 2018 152 · 2019 20 · 2020 3 · 2021 9 · 2022 227 · 2023 275 ·
2024 263 · 2025 162 · 2026 183.

Records retained by the parser, 3.2 M rows: heart rate 1,100,274 · active energy 922,031 ·
basal energy 499,696 · walking/running distance 332,451 · steps 237,352 · Apple exercise minutes
71,003 · HRV 31,894 · running power 8,247 · cycling distance 2,667 · body mass 2,046 ·
cycling power 1,874 · resting HR 1,719 · **VO₂max 399** · swimming distance 184. Range 2011-08 →
2026-11-17.

## 2. Measurement coverage by modality

| Modality | Workouts | With HR samples | Median HR samples | Median interval | `AverageMETs` | Distance | Active energy |
|---|---|---|---|---|---|---|---|
| Walking | 558 | 100 % | 39 | 5 s | 99 % | 100 % | 100 % |
| Strength (traditional) | 369 | 90 % | 5 | 735 s | 80 % | 9 % | 99 % |
| Running | 175 | 82 % | 1,261 | 1 s | **8 %** | 100 % | 100 % |
| Cycling | 118 | 72 % | 194 | 1 s | **21 %** | 99 % | 100 % |
| Swimming | 79 | 77 % | 163 | 2 s | 25 % | 100 % | 100 % |

Workout-level HR statistics exist for 835 workouts; **288 of 381 strength workouts** carry them
(average HR 74–151, mean 127). Raw strength HR is sparse (median 5 samples) — the summary statistics
are the useful strength signal, not the series.

`AverageMETs` is zero before 2021 and then 73–96 % per year. This kills the intended tier order for
running and cycling: Apple does not supply METs for them (8 % and 21 %), so a pace-derived tier is
their primary classification, not a fallback.

## 3. Volume and retention

- 546,283 of the 1,100,274 HR samples (50 %) fall inside a workout window. The rest are background
  sampling outside any workout.
- Per modality inside windows: running 264,736 · cycling 117,617 · strength 47,630 · swimming 36,200 ·
  walking 35,516.
- Staging store: 1.25 GB for 3.2 M records including indexes and text columns (≈390 B/row).
- Projected canonical footprint for "HR inside workouts only": ≈546 k rows, order **65 MB** at a
  ~120 B/row estimate. Background HR outside workouts is the only decision that can make this large,
  and nothing in the stage needs it.
- 810 route files (`workout-routes/*.gpx`, 211 MB) spanning 2016–2026, 59 of them from 2026.

## 4. Matchability against the session history — the decisive result

Production has 378 sessions: 373 `source=import` and 5 `source=workout`. **373 of them have
`duration_basis='unavailable'` and no start/end timestamp at all** (`session` stores only
`occurred_on`). Only the 5 watch-recorded sessions have a measured interval.

Calendar-day containment between the two corpora:

| Candidates on that day | Sessions | Share |
|---|---|---|
| Exactly 1 strength workout | 320 | 85 % |
| 2 strength workouts | 3 | 1 % |
| None | 55 | 15 % |

Coverage by year: 2021 3/40 · 2022 16/17 · 2023 72/74 · 2024 82/96 · 2025 86/87 · 2026 64/64.

Reverse direction: **55 strength workouts sit on days with no session in the backend** (2018 3,
2022 47, 2024 1, 2025 2, 2026 2) — real training the app never recorded, mostly from before the
import.

Who recorded the strength workouts: Apple Watch 284 · Sheiko Gold 25 · Athlytic 24 · Strongur 19 ·
Strong 11 · Shortcuts 10 · RunGap 3 · JEFIT 2 · **StrengthApp 1** · HeavySet 1 · Bevel 1.

## 5. The exact-identifier question is answered — and it is not what the plan assumed

The export carries external UUIDs under the key `HKExternalUUID` (the raw value of
`HKMetadataKeyExternalUUID`), not `HKMetadataKeyExternalUUID`. **27 workouts have one, and exactly one
is `source_name = "StrengthApp"`** (2026-11-14 20:30 UTC). The other 26 are Golfshot (25) and HeavySet.

So:

- an exact historical link exists for **one** workout, not for history;
- Apple's export does preserve the metadata an earlier draft assumed it might not — the key is
  discoverable, it is simply near-empty;
- the 5 watch-recorded sessions in production are still unmatchable by identifier, because the server
  never stored the watch's `sessionUUID`.

## 6. Standalone physiological metrics

| Metric | Rows | Sources | Range |
|---|---|---|---|
| VO₂max | 399 | Apple Watch 374, **Athlytic 25** | 2022-01 → 2026-11 |
| Apple exercise minutes | 71,003 | Apple Watch 63,956, iPhone 5,948, iPhone 1,099 | 2011-08 → 2026-11 |
| Resting HR | 1,719 | Apple Watch | — |
| HRV (SDNN) | 31,894 | Apple Watch | — |
| Body mass | 2,046 | mixed | — |

Athlytic is a third-party VO₂max estimate with a different algorithm from Apple's. Those 25 samples
must be distinguishable by source class, or they will read as a fitness discontinuity in 2023–2024.

`cardio_log` holds **0 rows**, and `healthkit_readiness` holds 94 rows (2026 only). Manual cardio has
never been used.

## 7. What this changes in the plan

1. **`DEC-CARDIO-02` (matching).** Interval overlap cannot be the primary signal for history: 373 of
   378 sessions have no interval. Overlap stays the rule for every session that has one — today the 5
   watch-recorded sessions and every future one — and calendar-day containment with a single candidate
   is the fallback for the imported corpus, explicitly labelled lower confidence. Two candidates on a
   day never auto-link, regardless of method. *Amended the same day by `DEC-CARDIO-13` at the owner's
   instruction: the per-item confirm step was dropped, because the 378 sessions sit on 378 distinct
   days, so same-day linking is unique on both sides for 320 of them.*
2. **`DEC-CARDIO-05` (intensity).** METs cannot lead for running (8 %) or cycling (21 %). Amended tier
   order: pace-derived METs for running/cycling where distance exists; Apple METs where present
   (walking 99 %, strength 80 %); %HRR with age and resting HR; else `unclassified`.
3. **`DEC-CARDIO-12` (new).** Derived cardio metrics join the existing derived-analytics layer
   (`analytics_revision`, `analytics_build`, `method_version`, disposable rebuildable rows) as a
   family, instead of a second promotion mechanism.
4. **Retention (C1/C3).** Store HR inside workouts only by default; 546 k rows ≈ 65 MB. Background HR is
   out unless a specific metric needs it.
5. **Entity naming.** `health_sample`, not `health_observation`: `observation` already exists and means
   AFC-3 rendered observations.
6. **Strength enrichment is real but different from the framing.** 288/381 strength workouts have HR
   summaries worth attaching; raw series are worthless there (median 5 samples). The value is HR
   average/max, active energy and true duration, not a time series.

## 8. What this audit does not establish

- Whether an import through `HKAnchoredObjectQuery` returns the same record set and metadata as the
  export (the export is the phone's flattened view; the app-side query is not measured here).
- Whether read authorisation covers any of this once re-requested in C2, and how the prompt behaves on
  an existing install.
- Route-to-workout association quality: GPX files are counted, not yet matched to workouts.
- Why 2021 has 40 sessions and 3 HealthKit strength days — the import and the watch disagree there,
  and the cause is not determined by this data.
- Anything about other devices or other people: this is one athlete's store.
