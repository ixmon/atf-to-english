# Promote clean-bysa-loop-v3-r1-ctrl (internal best clean model)

Promoted **2026-11-22 2:13 PM America/New_York**. Hayden approved this local promotion at 2:05 PM ET on Nov 22, 2026. CPU only: no training, no GPU, nothing published, no HF.

## What changed

- Registry: `models/CLEAN_BEST.json` now points at `models/clean-bysa-loop-v3-r1-ctrl/best-chrf`.
- Symlink: `models/clean-bysa-best` → `clean-bysa-loop-v3-r1-ctrl/best-chrf` (same relative-symlink convention as `models/best`).
- Alpaca backup: `/mnt/alpaca/model-backup/atf-translate-test/clean-bysa-loop-v3-r1-ctrl/` already held the step-5000 weights (`model.safetensors` sha256 `36b4ab0f59c94cdc…`, cmp-identical to the local `best-chrf`). The backup's stale `best_metrics.json` (step 2000, chrF 50.2) was updated to the current sidecar (step 5000, chrF 50.3).

## What did not change

- `models/BEST_MODEL.json` and `models/best` still point at `t5large-B4-splice-v3-10k/checkpoint-10000` (the Unread Atlas / API model). Not touched.
- `models/clean-bysa-v4e/` and its alpaca backup are intact. Previous clean best is recorded as `previous_best`.
- No HF push, no site or API swap (`not_done` is explicit in the registry).

## Recorded scores (official corpus chrF, tablet-clustered paired bootstrap, B=1000, seed 2)

- **Gate** (n=965 / 472 tablets): ctrl 34.02 vs v4e 33.42, **+0.60 [0.14, 1.07]**, p_le0=0.006, PASS.
- **Confirm** (n=635 / 318 tablets): ctrl 33.25 vs v4e 33.09, **+0.16 [-0.27, 0.67]**, p_le0=0.263. Confirm interval includes 0; promotion is on the gate pass, with confirm recorded.
- Trainer sidecar (not the official gate): step 5000, 1,438 chrF 50.3 (v4e was 50.81), Ur III 251 68.84, name-exact 77.6%.

Arm S did not pass the gate; loop pairs were not used in this promotion.

---

**Eval-protocol addendum (2026-11-24, America/New_York).** Hayden adopted `TOKFIX_STRIP_LANG_TAGS=1` as the official eval setting. The official ctrl baseline on the 965-line gate is now **34.32** (same v3-r1 ctrl weights; Δ vs the previous published strip-off 34.02 is +0.30 [0.06, 0.56]). The numbers in this file are the historical strip-off record and are not rewritten. ob-lit-v1 A/B arms were not promoted. See `docs/EVAL_PROTOCOL.md` and `runs/loop-pilot/ob-lit-v1/STRIP_RESCORE.md`.
