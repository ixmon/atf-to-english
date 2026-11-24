# Loop ob-lit-v1 results (v4e parent, two arms)

Written 2026-11-24 11:50:57 AM America/New_York.

Two-arm continuation from `models/clean-bysa-v4e/best-chrf` (v4e). Arm A: v4e-scrubbed replay + 262 gold N-to-N lines (20× upsample). Arm B: same gold + 3,466 kept N-to-N literary pseudo-label spans (10% literary draws). lr 1e-5, 5k steps, Ur III floor preserved at the v4e 160k-prefix share (10.34%).
Referee: `runs/fair-eval-v1/pairs.json`, 60/40 split seed 20261121. Official 965-line gate with tablet-clustered bootstrap B=1000 seed 2, scored at every 1,000-step checkpoint, vs v4e and vs starting ctrl. Confirm scored only if a checkpoint beats ctrl 34.02 with a positive paired CI. `test_site_final` was not opened or scored. No promotion, publish, or deploy.

## Arm A

| step | official 965 chrF | Δ vs v4e | Δ vs ctrl 34.02 | beats ctrl +CI |
|---:|---:|---|---|---|
| 1000 | 33.69 | 0.27 [-0.06, 0.61] | -0.33 [-0.9, 0.22] | no |
| 2000 | 33.34 | -0.08 [-0.46, 0.36] | -0.68 [-1.19, -0.14] | no |
| 3000 | 33.7 | 0.28 [-0.07, 0.69] | -0.32 [-0.84, 0.19] | no |
| 4000 | 33.43 | 0.01 [-0.4, 0.47] | -0.59 [-1.06, -0.08] | no |
| 5000 | 33.69 | 0.27 [-0.14, 0.71] | -0.33 [-0.8, 0.2] | no |

| step | literary vs 30.39 | Ur III | NA | royal | CDLI | eBL | c1438 dedup vs 49.53 | Subtotal | Cyrus | copy-through |
|---:|---|---|---|---|---|---|---|---:|---:|---:|
| 1000 | 29.98 (-0.41) | 31.51 | 38.87 | 43.07 | 35.99 | 26.75 | 49.73 (+0.20) | 36 | 0 | 0 |
| 2000 | 30.45 (+0.06) | 30.75 | 38.38 | 42.35 | 36.26 | 26.33 | 49.53 (+0.00) | 40 | 0 | 0 |
| 3000 | 30.27 (-0.12) | 31.0 | 38.96 | 42.85 | 36.39 | 26.42 | 49.54 (+0.01) | 45 | 0 | 0 |
| 4000 | 30.06 (-0.33) | 31.26 | 38.73 | 42.58 | 36.05 | 26.71 | 49.71 (+0.18) | 52 | 0 | 0 |
| 5000 | 30.29 (-0.10) | 31.42 | 39.01 | 42.97 | 36.01 | 26.9 | 49.64 (+0.11) | 41 | 0 | 0 |

Best official 965 chrF: **33.7** at step 3000 (not a pass).
Official early-stop note: three consecutive official evals failed to gain >= 0.2 after step 4000
Confirm was not scored (no checkpoint passed the official gate).

### Arm A step 1000 notes
- FAIL: borderline: delta 0.27 p_le0 0.056 CI [-0.06, 0.61]
- Note: lexical watch: {'n': 180, 'delta': np.float64(0.69), 'ci95': [-0.37, 2.06], 'p_le0': 0.126, 'n_boot': 1000, 'cluster': 'tablet'}
- Note: confirm trigger vs ctrl 34.02: beats_ctrl_positive_ci=False delta=-0.33 CI=[-0.9, 0.22]

### Arm A step 2000 notes
- FAIL: gate CI LB -0.46 <= 0 (delta -0.08, p_le0 0.598)
- FAIL: name-exact drop 2.3 > 2 points
- Note: lexical watch: {'n': 180, 'delta': np.float64(0.48), 'ci95': [-0.59, 1.69], 'p_le0': 0.184, 'n_boot': 1000, 'cluster': 'tablet'}
- Note: confirm trigger vs ctrl 34.02: beats_ctrl_positive_ci=False delta=-0.68 CI=[-1.19, -0.14]

### Arm A step 3000 notes
- FAIL: borderline: delta 0.28 p_le0 0.066 CI [-0.07, 0.69]
- Note: lexical watch: {'n': 180, 'delta': np.float64(0.43), 'ci95': [-0.53, 1.58], 'p_le0': 0.211, 'n_boot': 1000, 'cluster': 'tablet'}
- Note: confirm trigger vs ctrl 34.02: beats_ctrl_positive_ci=False delta=-0.32 CI=[-0.84, 0.19]

### Arm A step 4000 notes
- FAIL: gate CI LB -0.4 <= 0 (delta 0.01, p_le0 0.468)
- Note: lexical watch: {'n': 180, 'delta': np.float64(0.53), 'ci95': [-0.76, 1.86], 'p_le0': 0.242, 'n_boot': 1000, 'cluster': 'tablet'}
- Note: confirm trigger vs ctrl 34.02: beats_ctrl_positive_ci=False delta=-0.59 CI=[-1.06, -0.08]

### Arm A step 5000 notes
- FAIL: borderline: delta 0.27 p_le0 0.099 CI [-0.14, 0.71]
- Note: lexical watch: {'n': 180, 'delta': np.float64(0.55), 'ci95': [-0.76, 2.17], 'p_le0': 0.229, 'n_boot': 1000, 'cluster': 'tablet'}
- Note: confirm trigger vs ctrl 34.02: beats_ctrl_positive_ci=False delta=-0.33 CI=[-0.8, 0.2]

## Arm B

| step | official 965 chrF | Δ vs v4e | Δ vs ctrl 34.02 | beats ctrl +CI |
|---:|---:|---|---|---|
| 1000 | 33.5 | 0.08 [-0.4, 0.61] | -0.52 [-1.21, 0.14] | no |
| 2000 | 33.38 | -0.04 [-0.44, 0.36] | -0.64 [-1.25, -0.05] | no |
| 3000 | 33.35 | -0.07 [-0.49, 0.3] | -0.67 [-1.25, -0.18] | no |
| 4000 | 33.48 | 0.07 [-0.32, 0.49] | -0.54 [-1.16, 0.08] | no |
| 5000 | 33.5 | 0.08 [-0.29, 0.5] | -0.52 [-1.03, 0.02] | no |

| step | literary vs 30.39 | Ur III | NA | royal | CDLI | eBL | c1438 dedup vs 49.53 | Subtotal | Cyrus | copy-through |
|---:|---|---|---|---|---|---|---|---:|---:|---:|
| 1000 | 30.63 (+0.24) | 30.94 | 38.59 | 42.35 | 36.41 | 26.22 | 49.52 (-0.01) | 59 | 0 | 1 |
| 2000 | 30.17 (-0.22) | 30.61 | 38.55 | 42.42 | 36.17 | 26.06 | 49.39 (-0.14) | 50 | 0 | 0 |
| 3000 | 30.32 (-0.07) | 30.87 | 38.51 | 42.51 | 36.12 | 26.2 | 49.48 (-0.05) | 54 | 0 | 1 |
| 4000 | 30.21 (-0.18) | 31.02 | 38.89 | 42.92 | 36.06 | 26.15 | 49.77 (+0.24) | 48 | 0 | 1 |
| 5000 | 30.27 (-0.12) | 30.93 | 38.79 | 42.58 | 36.09 | 26.19 | 49.65 (+0.12) | 42 | 0 | 1 |

Best official 965 chrF: **33.5** at step 1000 (not a pass).
Official early-stop note: three consecutive official evals failed to gain >= 0.2 after step 4000
Confirm was not scored (no checkpoint passed the official gate).

### Arm B step 1000 notes
- FAIL: gate CI LB -0.4 <= 0 (delta 0.08, p_le0 0.373)
- Note: lexical watch: {'n': 180, 'delta': np.float64(0.29), 'ci95': [-0.72, 1.37], 'p_le0': 0.308, 'n_boot': 1000, 'cluster': 'tablet'}
- Note: confirm trigger vs ctrl 34.02: beats_ctrl_positive_ci=False delta=-0.52 CI=[-1.21, 0.14]

### Arm B step 2000 notes
- FAIL: gate CI LB -0.44 <= 0 (delta -0.04, p_le0 0.592)
- FAIL: c1438_dedup significant regression CI UB -0.05 < 0 (delta -0.59)
- FAIL: c1438_strict significant regression CI UB -0.1 < 0 (delta -0.65)
- Note: lexical watch: {'n': 180, 'delta': np.float64(0.61), 'ci95': [-1.28, 2.64], 'p_le0': 0.271, 'n_boot': 1000, 'cluster': 'tablet'}
- Note: confirm trigger vs ctrl 34.02: beats_ctrl_positive_ci=False delta=-0.64 CI=[-1.25, -0.05]

### Arm B step 3000 notes
- FAIL: gate CI LB -0.49 <= 0 (delta -0.07, p_le0 0.633)
- FAIL: c1438_dedup significant regression CI UB -0.02 < 0 (delta -0.5)
- FAIL: name-exact drop 2.3 > 2 points
- Note: lexical watch: {'n': 180, 'delta': np.float64(-0.5), 'ci95': [-2.37, 1.58], 'p_le0': 0.708, 'n_boot': 1000, 'cluster': 'tablet'}
- Note: confirm trigger vs ctrl 34.02: beats_ctrl_positive_ci=False delta=-0.67 CI=[-1.25, -0.18]

### Arm B step 4000 notes
- FAIL: gate CI LB -0.32 <= 0 (delta 0.07, p_le0 0.396)
- Note: lexical watch: {'n': 180, 'delta': np.float64(-0.71), 'ci95': [-2.3, 1.0], 'p_le0': 0.789, 'n_boot': 1000, 'cluster': 'tablet'}
- Note: confirm trigger vs ctrl 34.02: beats_ctrl_positive_ci=False delta=-0.54 CI=[-1.16, 0.08]

### Arm B step 5000 notes
- FAIL: gate CI LB -0.29 <= 0 (delta 0.08, p_le0 0.35)
- Note: lexical watch: {'n': 180, 'delta': np.float64(-0.18), 'ci95': [-1.89, 1.87], 'p_le0': 0.595, 'n_boot': 1000, 'cluster': 'tablet'}
- Note: confirm trigger vs ctrl 34.02: beats_ctrl_positive_ci=False delta=-0.52 CI=[-1.03, 0.02]

## Data

- Arm B keep rows: None (filter_v3 strict / per_sign).
- Buckets: None
- Orders: {'a': {'draws': 160000, 'gold_draws': 940, 'gold_share_pct': 0.59, 'pseudo_draws': 0, 'pseudo_share_pct': 0.0, 'literary_draws': 940, 'literary_share_pct': 0.59, 'ur3_draws': 16538, 'ur3_share_pct': 10.34, 'name_aux_draws': 3207, 'name_aux_share_pct': 2.0}, 'b': {'draws': 160000, 'gold_draws': 940, 'gold_share_pct': 0.59, 'pseudo_draws': 15060, 'pseudo_share_pct': 9.41, 'literary_draws': 16000, 'literary_share_pct': 10.0, 'ur3_draws': 16538, 'ur3_share_pct': 10.34, 'name_aux_draws': 3207, 'name_aux_share_pct': 2.0}}
- Stubs dropped: None

## Pickup markers

- `runs/loop-pilot/ob-lit-v1/train/PIPELINE_DONE` — written when both arms are scored and this file is complete.
- `runs/loop-pilot/ob-lit-v1/train/RESULTS.md` — this report.
- `runs/loop-pilot/ob-lit-v1/train/gate_done_{a,b}.flag` — official gates finished for that arm.
- `runs/loop-pilot/ob-lit-v1/train/confirm_done_{a,b}.flag` — confirm scored for a passing arm.
- `models/clean-bysa-loop-ob-lit-v1-{a,b}/mix_train.json` — training finished for that arm.

No promotion. `models/BEST_MODEL.json`, `models/best`, `models/clean-bysa-best`, and the Unread Atlas site/API were not changed.

---

**Eval-protocol addendum (2026-11-24, America/New_York).** Hayden adopted `TOKFIX_STRIP_LANG_TAGS=1` as the official eval setting. The official ctrl baseline on the 965-line gate is now **34.32** (same v3-r1 ctrl weights; Δ vs the previous published strip-off 34.02 is +0.30 [0.06, 0.56]). The numbers in this file are the historical strip-off record and are not rewritten. ob-lit-v1 A/B arms were not promoted. See `docs/EVAL_PROTOCOL.md` and `runs/loop-pilot/ob-lit-v1/STRIP_RESCORE.md`.
