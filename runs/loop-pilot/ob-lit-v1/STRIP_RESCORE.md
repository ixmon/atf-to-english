# Strip-on official rescore (eval only)

Written 2026-11-24 02:23:55 PM America/New_York.

Eval only: family decode + `tokfix.decode`, language tags stripped at `tokfix.normalize_atf` (`TOKFIX_STRIP_LANG_TAGS=1`). Model prefix `translate Akkadian to English: ` is unchanged. Official 965-line gate only (confirm not scored; `test_site_final` not opened). Bootstrap B=1000 seed 2, tablet-clustered. No promotion, no training, no commit.

Strip-off numbers are the already-saved official predictions, re-scored with the same script so the comparison is exact. `ctrl` strip-off official chrF should match **34.02**.

## Official 965-line gate

| model | strip | official chrF | Δ vs ctrl 34.02 (paired CI) | beats ctrl +CI | literary | eBL | Ur III |
|---|---|---:|---|---|---:|---:|---:|
| ctrl | off | 34.02 | +0.00 [0.0, 0.0] | no | 30.39 | 27.2 | 32.0 |
| ctrl | on | 34.32 | +0.30 [0.06, 0.56] | yes (ctrl+strip vs 34.02) | 30.89 | 27.86 | 32.87 |
| A3000 | off | 33.7 | -0.32 [-0.84, 0.19] | no | 30.27 | 26.42 | 31.0 |
| A3000 | on | 33.8 | -0.22 [-0.72, 0.35] | no | 30.81 | 27.98 | 33.0 |
| B1000 | off | 33.5 | -0.52 [-1.21, 0.14] | no | 30.63 | 26.22 | 30.94 |
| B1000 | on | 33.74 | -0.28 [-0.9, 0.33] | no | 30.41 | 27.64 | 32.84 |
| B5000 | off | 33.5 | -0.52 [-1.03, 0.02] | no | 30.27 | 26.19 | 30.93 |
| B5000 | on | 33.96 | -0.06 [-0.59, 0.52] | no | 30.6 | 27.88 | 32.97 |

Literary ctrl strip-off official slice target is **30.39**. Ur III and eBL have no fixed published headline besides the numbers in this table.

## Leak counts on the 965-line gate (decoded hyps)

`raw` counts every pattern hit, including a genuine šunigin line that correctly says Subtotal. `backstop` counts only residual *false* leaks (no šunigin / szu+nigin2 cue in the ATF).

| model | strip | Subtotal | surplus | substitute | %sú | (Sum)/(Akk) | es priest | any raw | backstop flagged |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ctrl | off | 19 | 3 | 4 | 1 | 14 | 0 | 41 | 41 |
| ctrl | on | 0 | 0 | 0 | 0 | 12 | 0 | 12 | 12 |
| A3000 | off | 28 | 6 | 0 | 6 | 16 | 1 | 57 | 57 |
| A3000 | on | 0 | 0 | 0 | 0 | 15 | 0 | 15 | 15 |
| B1000 | off | 35 | 4 | 0 | 39 | 11 | 1 | 90 | 90 |
| B1000 | on | 0 | 0 | 0 | 0 | 11 | 0 | 11 | 11 |
| B5000 | off | 28 | 6 | 0 | 17 | 12 | 1 | 64 | 64 |
| B5000 | on | 0 | 0 | 0 | 0 | 12 | 0 | 12 | 12 |

## c1438 dedup

Ctrl strip-off official dedup headline is **49.53**.

| model | strip | c1438 dedup chrF | Δ vs ctrl strip-off (paired CI) |
|---|---|---:|---|
| ctrl | off | 49.53 | +0.00 [0.0, 0.0] |
| ctrl | on | 49.53 | -0.00 [-0.0, 0.0] |
| A3000 | off | 49.54 | +0.02 [-0.57, 0.58] |
| A3000 | on | 49.54 | +0.02 [-0.57, 0.58] |
| B1000 | off | 49.52 | -0.00 [-0.61, 0.58] |
| B1000 | on | 49.52 | -0.01 [-0.61, 0.58] |
| B5000 | off | 49.65 | +0.12 [-0.51, 0.7] |
| B5000 | on | 49.65 | +0.12 [-0.51, 0.7] |

**No trained arm** (A3000, B1000, B5000) beat official ctrl 34.02 with a positive paired CI. Confirm was not scored. No promotion.

The same **ctrl model** with tag-stripping on, however, scores **34.32**, Δ **+0.30 [0.06, 0.56]** vs the published 34.02. That is a preprocessing win on the existing champion, not a new checkpoint. Literary 30.39→30.89, eBL 27.20→27.86, Ur III 32.00→32.87. c1438 dedup is unchanged at 49.53 (this pack is almost all untagged CDLI-style lines).

## Residual leaks and the output backstop

After the input strip, Subtotal / surplus / substitute / `%sú` / “es priest” are **0** on every model. The only remaining pattern is `(Sum)` / `(Akk)` on bilingual or lexical lines (ctrl 12, A3000 15, B1000 11, B5000 12). These are format labels, often on lines that already use `>` or a Sumerian/Akkadian equation; the backstop flags them and drops the labels while keeping the rest of the translation (see Hayden’s note that some filler can be a respectable reading of a bilingual line).

`runs/loop-pilot/ob-lit-v1/output_backstop.py` (tests in `test_output_backstop.py`) is the uncommitted post-decode check. It leaves genuine `szu+nijen2` / `szu-nigin2` Subtotals alone. On strip-on gate hyps it flags exactly those residual 11–15 `(Sum)`/`(Akk)` lines and nothing else.

## Off/on switch

`TOKFIX_STRIP_LANG_TAGS` (default ON) in `data/na/tokfix/tokfix.py`. Set to `0`/`off` to restore the old input. The prefix `translate Akkadian to English: ` is never changed. Tests in `data/na/tokfix/test_lang_tags.py`.

## Recommendation

1. **Adopt tag-stripping in official eval** (and any future train). It is already the default in uncommitted `tokfix.normalize_atf`. The cleanest headline change is to treat **ctrl + strip-on = 34.32** (CI vs old 34.02 entirely positive) as the new official ctrl number, *if Hayden agrees this is an eval-protocol update rather than a new model*. Do not score confirm for that; it is the same ctrl weights.
2. **Do not promote A or B.** Even with strip-on they remain below 34.02 (best is B5000 at 33.96, CI vs ctrl still crosses zero: −0.06 [−0.59, 0.52]). A new training round is not justified by this rescore alone.
3. **Keep the output backstop** for residual `(Sum)`/`(Akk)`. It is a cheap CPU cleanup, not a second decode. Do not use it to rewrite genuine bilingual content beyond dropping the labels.
4. **No GPU training** until Hayden explicitly OKs a round. If one happens, train *and* eval with the strip on, otherwise the model will not see the inputs it is scored on.
5. Names list (first pass, gold literary only, no eval English): `runs/loop-pilot/ob-lit-v1/names/`. 25 determinative-marked forms from KASKAL + ORACC gold; 19 have a unique English guess on the same line. A bigger next step would be the v4e `name_transliteration` training aux, still avoiding the official gate.

Preds live under `runs/loop-pilot/ob-lit-v1/strip-rescore/`.

## Adopted 2026-11-24 3:32 PM America/New_York

Hayden approved the protocol update (widget t1327s4750): official eval is `TOKFIX_STRIP_LANG_TAGS=1`, official ctrl baseline is **34.32** (CI vs old 34.02: +0.30 [0.06, 0.56]). A/B arms are not promoted. Confirm was not scored. See `docs/EVAL_PROTOCOL.md` and `models/CLEAN_BEST.json` (`eval_protocol`).
