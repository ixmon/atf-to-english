# Paired continuation design (draft only — do not launch)

Drafted 4:14 PM America/New_York on Nov 22, 2026. CPU-only planning. No training, no GPU, no TensorFold start, no HF, no site/API change, no `test_site_final` scoring. Hayden (t1287u) asked to tighten the filter first and design the longer run after, with a switch that can prefer chrF (strict) now and paraphrases (lenient) later.

This is a design, not an approval to train. Every new training run or GPU use still needs an explicit OK.

Updated 3:20 AM EST (America/New_York) on Nov 23, 2026, after the gloss expansion and reverse-check comparison (CPU only; still not a launch).

**Arm B should use the expanded `filter_v3` `--paraphrase strict --gloss-tier per_sign` set (1,302 lines, 88.0% of the old 1,479), not reverse-strict and not lenient.** Reverse stays a FLAG. The flat corpus vocab is not a drop rule. A third arm is not recommended: forward-strict already recovered 203 lines vs the pre-expansion 1,099, matches reverse on the 30-line panel (14/16 real errors, no gloss false flag on the 3 paraphrases), and is less jumpy on conjugations. Same seeds, 5,000 steps, 1,000-step cadence, and ~7.5–8.5 GPU-hour estimate as below. Every GPU run still needs an explicit OK.


## Why this shape

v3-r1 **ctrl** (`models/clean-bysa-best`) passed the 965-line official gate vs v4e (**+0.60 [0.14, 1.07]**, p_le0=0.006) and is the current internal best clean model. Arm S (loop pairs selected with filter v2) did **not** help (S 33.73 vs ctrl 34.02). The pairs will change under filter v3, so the training sweet spot may change too — hence a paired continuation from the same ctrl checkpoint, with and without the new strict-filtered pseudo-labels, before any quality-beyond-chrF (lenient) phase.

## Arms

Both arms start from `models/clean-bysa-best` (= `models/clean-bysa-loop-v3-r1-ctrl/best-chrf`). Do not overwrite v4e, do not change `models/BEST_MODEL.json` / `models/best` (the API/site B4 splice), and do not publish.

| arm | data | purpose |
|---|---|---|
| **A** | Base mix only (the frozen v4e translation order + name-aux, same CAP-2 schedule as the ctrl continuation). No new loop pairs. | Isolates “more steps on clean human/base data.” |
| **B** | Arm A’s mix **plus** strict-filtered v3-r1 pseudo-labels. | Tests whether the tighter pairs now help, in the genres where the gate failed. |

### Arm B pairs

- Source: v3-r1 `qwen_improve` English, kept only if the **strict** filter v3 keep rule holds (disagreement, confidence high/medium, word cap, judge ∈ {better, equivalent}, and filter v3 `--paraphrase strict`).
- Offline count (this draft, after the 2026-11-23 gloss expansion): **1302** lines (88.0% of the old 1479). Under the 5% draw cap at CAP 2, as before.
- **Prefer genres where the v3-r1 ctrl gate did not beat v4e** (point estimate ≤ 0 or clearly trailing): **lexical** (−0.58, n=180), **other** (−0.41, n=60), **OB literary** (−0.08, n=126). In the expanded strict-per-sign keep set those buckets are 130 lexical / 192 literary / 9 Other. Do not drop the rest of the 1099 if that would leave a thin failed-genre-only set (well under ~400). Instead **up-weight** failed-genre rows in the CAP-2 interleave (e.g. draw them twice as often as admin), and keep a cap so admin cannot dominate the added pairs.
- **Skip stub references.** The 5k pool has no human refs, but do not add or train on “No translation possible/warranted” (or “No translation possible”) lines if any appear in a mix or in eval teacher-forcing. The 40/965 gate placeholders stay eval-only and are never training targets.
- Fair-eval tablets stay blocked (existing `fair_blocked_tablets.json`). No ETCSL/eBL in training.

Lenient-mode pairs, and reverse-strict pairs, are **not** in this run. They are for a later quality phase, once chrF gains on the official gate stall.

## Recipe (same seeds and schedule as v3-r1 ctrl)

Carried from `runs/loop-pilot/DESIGN_V3.md` / the ctrl run unless Hayden changes it:

- **5,000** steps, seed **42**, lr **3e-5** `constant_with_warmup` 100, batch 4 × accum 8 (eff 32), bf16, mem-frac **0.17** (coexist with TensorFold if it is already up; do not start or stop it from this plan).
- CAP 2 on the base translation order; name-aux stays ~2%.
- Output dirs: `models/clean-bysa-loop-v3-r2-a/` and `models/clean-bysa-loop-v3-r2-b/`. Fresh optimizer. Do not write into `models/clean-bysa-v4e/` or `models/clean-bysa-loop-v3-r1-ctrl/`.
- Sequential on one GPU, A then B, as in v3-r1.

## Checkpoint cadence and gating

- **Checkpoint every 1,000 steps** (5 official looks: 1000, 2000, 3000, 4000, 5000), `save_total_limit` 2, copy each arm’s best so far to `best-chrf`.
- **At each checkpoint, run the official 965-line fair gate** (not just the 1,438 training hook): family decode (`num_beams=4`, `num_return_sequences=4`, `do_sample=False`, `no_repeat_ngram_size=3`, `repetition_penalty=1.2`, `max_new_tokens=256`, `TF.model_input`, tokfix.decode), then tablet-clustered paired bootstrap **B=1000, seed 2**, vs **v4e** and vs the starting **ctrl**. Same 60/40 split (`design-v3/fair_split.json`). Decision rule unchanged from DESIGN_V3 (pass / borderline / fail).
- The 1,438 / Ur III 251 / name-exact 405 hook may still run as a cheap training-time signal (as in v3-r1, ~2.7 min). It does **not** decide the round.
- **Confirm split (635 lines / 318 tablets) is scored only if a checkpoint PASSes the 965-line gate.** Do not peek at confirm on a fail or a borderline. Score confirm once for the passing arm(s), then stop.
- Never score `test_site_final`. Early-stop hook (optional): three consecutive gate evals that fail to gain **≥ 0.2** official corpus chrF over the arm’s best gate so far.

## GPU-hour estimate (one GPU, sequential)

From the v3-r1 ctrl log: **5,000 steps in 11,360 s ≈ 3.16 h** at ~2.08 s/step, including 1,438 family chrF at the eval hooks (~160 s each).

Add the official 965-line family decode + bootstrap at 5 checkpoints. 965 lines at the same family recipe is on the order of the 1,438 hook (roughly 2–3 minutes generate + score, ~5–8 minutes if we also keep c1438/Ur III/name-eval at the same checkpoint). Budget **~0.5–0.7 h extra per arm**.

| piece | estimate |
|---|---|
| Arm A train + 5× gate | ~3.7–3.9 h |
| Arm B train + 5× gate | ~3.7–3.9 h |
| Confirm (only on a pass, once per passing arm) | ~5–8 min |
| **Total, sequential** | **~7.5–8.5 GPU hours** |

No fourth arm. No 20k scale-up. If arm B’s strict set were ever rebuilt and fell under ~400 rows, stop and show Hayden before training.

## What this run is not

- Not a publish, HF push, or Unread Atlas / API swap.
- Not a lenient-paraphrase quality run. If both arms stall on the official gate, that is the point to discuss loosening `--paraphrase lenient` or revising the ratio limb (see FILTER_V3.md hand check).
- Not launched. Needs Hayden’s explicit GPU OK, and TensorFold only if he/Tank starts it for family decode.

## Ready when approved

Scripts can follow the v3-r1 `train_loop_v2.py` / `score_v3.py` pattern with `CUDA_VISIBLE_DEVICES=0` restored after any `dedup_eval` import, a clean `CURRENT_CLEAN` pointer left unchanged until a later promotion, and backups under `/mnt/alpaca/model-backup/atf-translate-test/` without clobbering v4e or v3-r1-ctrl.
