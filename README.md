# ATF → English Translation — Minimal Reproduction

**Repository:** https://github.com/ixmon/atf-to-english

This is a clean, minimal, self-contained reproduction focused **only** on ATF (Akkadian Transliteration Format) → English translation using T5. It was extracted from a larger research project on full cuneiform tablet translation (image → ATF → English).

**Goal**: The smallest possible, self-contained set of code + instructions that lets you reproduce the high-quality ATF-to-English translation models that reached "almost perfect" / "arguably on par with manual translations" on hard real-world tablets (Gilgamesh Flood Tablet, royal inscriptions, medical texts).

This is the distilled "simplest path" extracted from a much larger research repository. The original success used T5-small, careful stability fixes, and (for the very best results) long training on a large combined dataset.

## Two Tiers (the "simplest path" is visible)

| Tier   | Data                  | Epochs | Speed     | Quality                          | When to use |
|--------|-----------------------|--------|-----------|----------------------------------|-------------|
| stable | ~30k eBL pairs        | 5      | minutes   | Already very good & reliable     | Default / first thing you run |
| best   | Larger (eBL + paragraphs recommended) | 25-30+ | hours     | The documented near-manual result (v12a style) | When you want the highest quality |

The **stable** tier is the one that "just worked" after earlier FP16 disasters. The **best** tier is the long-training tag-free approach that finally matched or exceeded previous hand-crafted baselines on the hardest genres.

## Quick Start (Stable Tier — Recommended First)

uv.lock is committed for reproducible installs (highly recommended for consistent training results across machines).

```bash
# 1. Clone + set up environment (uses the committed lockfile)
git clone https://github.com/ixmon/atf-to-english.git
cd atf-to-english
uv sync   # creates .venv + installs *exact* versions pinned in uv.lock

# Fallbacks
# uv pip install -r pyproject.toml
# pip install -r requirements.txt   # for plain pip or the NGC container below

# 2. Get data (the exact source used for the original good models)
uv run python download_pairs.py --small   # fast POC (~200 pairs)
# or
uv run python download_pairs.py           # real ~ number of pairs with English

# 3. Train the reliable stable model
uv run python train.py --tier stable --data data/ebl_pairs.json --output models/atf-en-stable-final

# 4. Use it
uv run python infer.py --model models/atf-en-stable-final --atf "BAR# 13 AN.KU₁₀ sin 5 ITU"
# Expected style: "The 13th, moonrise to sunrise: 5°." (or very close)
```

## The Best-Tier Recipe (v12a-style near-manual quality)

For the results that were manually judged "almost perfect" on royal, literary, and medical texts:

- Use the **tag-free** prompt that matched the winning external baseline: `translate Akkadian to English: {atf}`
- Fresh `t5-small` (not continued fine-tune for the tag-free case).
- Same **stability settings** that prevented collapse: `fp16=False`, `max_grad_norm=1.0`, modest LR, gradient accumulation.
- 25–30+ epochs (one famous run used early stopping with patience=5 and max=50; best checkpoint was often epoch 27 on ~131k pairs).
- Larger data helps a lot for royal epithets and long literary passages (eBL inline translations + paragraph-level pairs from other CDLI sources).

You can drive the long run with environment variables:

```bash
TIER=best \
EPOCHS=28 \
EARLY_STOPPING_PATIENCE=5 \
LEARNING_RATE=3e-4 \
BATCH_SIZE=32 \
uv run python train.py --data data/ebl_pairs.json --output models/atf-en-best-final
```

On machines where normal PyTorch wheels don't have good CUDA (certain ARM64/Blackwell setups), use the NGC container path (see below).

## Hardware Notes & the NGC Container (what actually worked)

On normal x86 + recent CUDA you can usually just `uv run` (after `uv sync`).

On the hardware where many of the stability lessons were learned (NVIDIA Grace-Blackwell etc.), stock PyPI torch lacked proper wheels. The reliable invocation was:

```bash
docker run --rm --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  -v $(pwd):/workspace -w /workspace \
  nvcr.io/nvidia/pytorch:25.01-py3 \
  bash -c "pip install -q datasets sentencepiece accelerate transformers && python train.py ..."
```

**Note**: The NGC path uses direct `pip install` (see `scripts/run_on_ngc.sh`). It intentionally bypasses `uv.lock` because that container image manages its own Python environment.

See `scripts/run_on_ngc.sh` for the exact flags + env passthrough used for the long 28-epoch run.

**Critical stability lesson**: `fp16=True` (or mixed precision) caused total model collapse (NaN loss/grads, output became only commas or garbage). Always `fp16=False` + gradient clipping.

## Verification — Did You Get the Good Result?

The original "best" model was manually evaluated on three particularly difficult tablets:

- **P346140** — Gilgamesh Flood Tablet (literary, long narrative)
- **P467316** — Tiglath-Pileser royal inscription (complex epithets, formulaic royal language — previously a weak point)
- **P285298** — "Evil Hand Syndrome" medical tablet

Representative ATF is in `data/key_test_cases.json`. After training a "best" model, run:

```bash
python infer.py --model models/atf-en-best-final --atf "u4 ri-a u4 su3-u4 ri-a"
# (and the other lines from the key cases)
```

Qualitative bar for success (from the original manual review):
- Handles royal epithets and complex syntax well.
- Produces coherent narrative on literary texts.
- Reasonable specialized terminology on medical/diagnostic texts.
- "Almost perfect" or "on par with manual translations" on the hardest examples.

The training signal for the 28-epoch run was that validation loss was *still improving* through epoch 27 (best eval loss ~0.128).

## Files in This Minimal Project

- `download_pairs.py` — fetches from the eBL API and extracts the exact inline `#tr.en:` pairs used originally.
- `train.py` — one script with `--tier stable|best`, full stability recipe, env var control for long runs, built-in quick tests.
- `infer.py` — clean tag-free inference (the path that won on manual eval).
- `scripts/run_on_ngc.sh` — the container command that actually produced the record long-training result.
- `data/key_test_cases.json` — the three hard tablets + examples for verification.
- `uv.lock` — committed for exact, reproducible dependency installs across machines (used by `uv sync`).

Everything else (multiple historical train_* scripts, giant checkpoint dirs, logs, vendored platforms, vision OCR experiments) has been stripped away.

## Next Steps After You Have a Working Model

- Add paragraph-level data (see the original `extract_paragraph_pairs.py` style) + retrain the "best" tier for further gains on royal/literary material.
- Try `t5-base` (the original plan after t5-small was proven stable with long training).
- Publish the final model + this README as a model card on Hugging Face.

This directory is intentionally small, clean, and focused on **understanding and reproducing the simplest path that actually delivered excellent results**.

(If you came from the larger research tree: the hero model there was `models/atf-translator-v12a-tagfree-final` and the stable reference was `atf-translator-stable-final`.)
