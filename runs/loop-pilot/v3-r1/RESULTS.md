# Loop v3-r1 RESULTS

Scored: 2026-11-22 01:40:54 PM America/New_York

Official metric: corpus chrF, family decode + `tokfix.decode`, tablet-clustered paired bootstrap (B=1000, seed 2).
Referee: `runs/fair-eval-v1/pairs.json`, 60/40 split seed 20261121. Confirm scored only after a gate pass, once. `test_site_final` was not opened or scored.

## Gate overall

| arm | n | chrF | Δ vs v4e | CI 95 | p_le0 | pass |
|---|---:|---:|---:|---|---:|---|
| v4e (parent) | 965 | 33.42 | — | — | — | — |
| S | 965 | 33.73 | 0.32 | [-0.2, 0.85] | 0.098 | BORDERLINE |
| S-raw | 965 | 33.42 | -0.0 | [-0.54, 0.59] | 0.496 | FAIL |
| ctrl | 965 | 34.02 | 0.6 | [0.14, 1.07] | 0.006 | PASS |

## Gate slices (chrF / Δ vs v4e CI)

| slice | n | v4e | S | S-raw | ctrl |
|---|---:|---:|---:|---:|---:|
| cdli | 332 | 36.0 | 36.68 (Δ 0.68 [-0.38, 1.66]) | 35.84 (Δ -0.15 [-1.05, 0.77]) | 36.7 (Δ 0.71 [-0.21, 1.69]) |
| oracc | 364 | 34.85 | 35.15 (Δ 0.31 [-0.37, 1.09]) | 35.25 (Δ 0.4 [-0.39, 1.48]) | 35.48 (Δ 0.64 [-0.07, 1.42]) |
| no_ebl | 696 | 35.2 | 35.63 (Δ 0.43 [-0.14, 1.04]) | 35.43 (Δ 0.23 [-0.41, 0.97]) | 35.86 (Δ 0.66 [0.1, 1.24]) |
| ur3 | 184 | 31.33 | 31.55 (Δ 0.22 [-0.85, 1.23]) | 30.54 (Δ -0.79 [-1.86, 0.27]) | 32.0 (Δ 0.67 [-0.25, 1.62]) |
| neo_assyrian | 259 | 38.34 | 38.76 (Δ 0.42 [-0.33, 1.28]) | 38.61 (Δ 0.27 [-0.69, 1.41]) | 39.19 (Δ 0.85 [0.13, 1.67]) |
| ob_literary | 126 | 30.48 | 30.18 (Δ -0.3 [-1.76, 1.01]) | 30.27 (Δ -0.21 [-1.51, 0.82]) | 30.39 (Δ -0.08 [-1.29, 0.88]) |
| names | 185 | 34.16 | 34.26 (Δ 0.11 [-0.73, 0.98]) | 33.88 (Δ -0.28 [-1.32, 0.77]) | 34.85 (Δ 0.7 [-0.27, 1.55]) |
| royal | 182 | 42.27 | 43.16 (Δ 0.88 [-0.03, 2.12]) | 42.96 (Δ 0.68 [-0.35, 2.1]) | 43.31 (Δ 1.04 [0.16, 2.12]) |
| lexical (watch) | 180 | 20.77 | 21.06 (Δ 0.3 [-1.03, 1.7]) | 20.99 (Δ 0.23 [-1.51, 2.18]) | 20.18 (Δ -0.58 [-2.37, 1.03]) |
| ebl (report only) | 269 | 26.8 | 26.72 (Δ -0.08 [-0.89, 0.71]) | 25.94 (Δ -0.86 [-1.71, -0.15]) | 27.2 (Δ 0.4 [-0.29, 1.14]) |

## Secondary diagnostics (c1438, Ur III 251, name-exact)

| cut | v4e | S | S-raw | ctrl |
|---|---:|---:|---:|---:|
| c1438_dedup | 49.98 | 49.53 (Δ -0.45 [-1.08, 0.14]) | 49.47 (Δ -0.51 [-1.16, 0.11]) | 49.53 (Δ -0.46 [-1.07, 0.15]) |
| c1438_strict | 48.48 | 47.98 (Δ -0.5 [-1.23, 0.19]) | 47.91 (Δ -0.57 [-1.18, 0.05]) | 47.95 (Δ -0.53 [-1.19, 0.11]) |
| Ur III 251 chrF | 69.05 | 69.44 | 69.31 | 69.82 |
| name-exact % | 79.5 | 80.1 | 77.9 | 79.2 |

## Confirm (scored once after a gate pass; not used to pick an arm)

| arm | n | chrF | Δ vs v4e | CI 95 | p_le0 |
|---|---:|---:|---:|---|---:|
| v4e (parent) | 635 | 33.09 | — | — | — |
| ctrl | 635 | 33.25 | 0.16 | [-0.27, 0.67] | 0.263 |

## Verdicts

### Arm S: BORDERLINE — report and wait

- FAIL: borderline: delta 0.32 p_le0 0.098 CI [-0.2, 0.85]
- FAIL: S does not beat ctrl (delta -0.28); loop data did not help
- Note: lexical watch: {'n': 180, 'delta': np.float64(0.3), 'ci95': [-1.03, 1.7], 'p_le0': 0.329, 'n_boot': 1000, 'cluster': 'tablet'}

### Arm S-raw: FAIL

- FAIL: gate CI LB -0.54 <= 0 (delta -0.0, p_le0 0.496)
- Note: lexical watch: {'n': 180, 'delta': np.float64(0.23), 'ci95': [-1.51, 2.18], 'p_le0': 0.407, 'n_boot': 1000, 'cluster': 'tablet'}

### Arm ctrl: PASS

- Note: gate CI LB 0.14 > 0 (delta 0.6)
- Note: lexical watch: {'n': 180, 'delta': np.float64(-0.58), 'ci95': [-2.37, 1.03], 'p_le0': 0.751, 'n_boot': 1000, 'cluster': 'tablet'}

No further round was started. Fair-eval stays uncommitted.

---

**Eval-protocol addendum (2026-11-24, America/New_York).** Hayden adopted `TOKFIX_STRIP_LANG_TAGS=1` as the official eval setting. The official ctrl baseline on the 965-line gate is now **34.32** (same v3-r1 ctrl weights; Δ vs the previous published strip-off 34.02 is +0.30 [0.06, 0.56]). The numbers in this file are the historical strip-off record and are not rewritten. ob-lit-v1 A/B arms were not promoted. See `docs/EVAL_PROTOCOL.md` and `runs/loop-pilot/ob-lit-v1/STRIP_RESCORE.md`.
