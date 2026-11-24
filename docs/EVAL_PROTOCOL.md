# Official eval protocol (clean CC BY-SA ATF→English)

Last updated 2026-11-24, America/New_York. Adopted by Hayden 2026-11-24 3:32 PM ET (widget t1327s4750).

## Referee

- Official gate: the 965-line `runs/fair-eval-v1` split (60/40, seed 20261121), tablet-clustered paired bootstrap B=1000 seed 2.
- Family decode: beams 4, no_repeat_ngram 3, repetition_penalty 1.2, max_new 256, `tokfix.decode`.
- Confirm (635) is scored only after a PASS against the official ctrl baseline with a fully positive paired CI. `test_site_final` is never opened or scored.
- Do not commit `runs/fair-eval-v1/pairs.json` or `runs/loop-pilot/ob-lit-v1/analysis.json`.

## Language-tag strip (official, default ON)

`TOKFIX_STRIP_LANG_TAGS=1` is the official eval setting. `tokfix.normalize_atf` strips ORACC/eBL/CDLI protocol tags (`%sux`, `%akk`, `%a`, `%es`, `%sb`, `%n`, `%šu`→`%szu` after CDLI-ASCII, …) before the model sees the line. Set `TOKFIX_STRIP_LANG_TAGS=0`/`false`/`off`/`no` only to reproduce the old strip-off numbers.

The model prefix `translate Akkadian to English: ` is never changed.

## Official ctrl baseline

Champion weights remain `models/clean-bysa-best` = `models/clean-bysa-loop-v3-r1-ctrl/best-chrf` (not a new checkpoint).

| protocol | official 965 chrF | literary (126) | eBL | Ur III | c1438 dedup |
|---|---:|---:|---:|---:|---:|
| strip-off (previous published) | **34.02** | 30.39 | 27.20 | 32.00 | 49.53 |
| **strip-on (official as of 2026-11-24)** | **34.32** | 30.89 | 27.86 | 32.87 | 49.53 |

Ctrl strip-on vs the previous published 34.02: **Δ +0.30 [0.06, 0.56]** (preprocessing win on the same weights). Source: `runs/loop-pilot/ob-lit-v1/STRIP_RESCORE.md`. Also recorded in `models/CLEAN_BEST.json` under `eval_protocol`.

The v3-r1 promotion record vs v4e (ctrl 34.02 vs v4e 33.42, +0.60 [0.14, 1.07]) is historical and unchanged; that comparison was run strip-off.

## Arms not promoted

ob-lit-v1 A3000 / B1000 / B5000 were rescored strip-on and did **not** beat 34.02 with a positive CI (best was B5000 at 33.96, −0.06 [−0.59, 0.52]). Confirm was not scored. Those arms are not promoted.

## Output backstop

After decode, `runs/loop-pilot/ob-lit-v1/output_backstop.py` peels residual `(Sum)`/`(Akk)` labels (keeping the rest of the translation) and drops leak artifacts (`Subtotal:` / `surplus:` / `substitute:` / `%sú` / “es priest”) when the ATF has no genuine šunigin / `szu+nigen2` cue. Genuine totals are left alone.
