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

**Full reproduction log, data sources, OOM fixes, training commands, results, and evaluation on the key tablets are in [REPRODUCTION.md](REPRODUCTION.md).**

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

## Data Sources and How the Best (v12a) Training Set Was Built

The minimal `download_pairs.py` only reproduces the **eBL inline `#tr.en:` extraction** (the core ~30k–125k pairs from the Electronic Babylonian Library API). This is sufficient for the "stable" tier and a strong starting point.

The **best-performing v12a-tagfree model** (the one that achieved near-manual quality on the hard test tablets after ~27–28 epochs on a 131k-pair set) was trained on a much richer, combined dataset. The data work happened upstream of the training script.

### Primary Sources (from the original larger repo)

- **eBL inline pairs** (`ebl_pairs.json`, `ebl_fragments.json`)
  - Source: Public eBL API (`https://www.ebl.lmu.de/api/fragments/retrieve-all`)
  - Extraction: Look for ATF content lines followed by `#tr.en:` (or `#tr.en.`) comments. The minimal `download_pairs.py` (and the big repo's `download_ebl.py`) does exactly this.
  - Strength: High-quality, consistent astronomical/omen/medical style translations. ~125k pairs in the full extract (many with usable English after filtering).

- **CDLI / CDLI2 translations** (`cdli_translation_pairs.json`, `cdli2_translation_pairs.json`)
  - Extracted from CDLI publication dumps and the "unknown_pubs.json" (CDLI2) data.
  - Scripts in the original: `extract_cdli_translations.py`, `extract_cdli2_translations.py`.

- **Paragraph-level pairs** (`cdli2_paragraph_pairs.json`) — **key differentiator for best results**
  - Generated by `extract_paragraph_pairs.py` in the original repo.
  - Input: `data/cdli2/unknown_pubs.json`
  - Method:
    - Used existing `paragraphs` fields when present (with English).
    - Also constructed paragraphs by grouping consecutive lines that had English translations (for royal and literary texts that were line-by-line in the source).
    - Filtered for substantial length (roughly 10–200 English words, 5–150 ATF tokens).
    - Focused on Literature + Royal/Monumental genres (and some Middle Assyrian).
  - Why it mattered: Provided multi-line context for complex royal epithets and long literary passages (Gilgamesh-style narrative). The minimal README calls this out as the main thing to add for further gains.

- **Oracc translations** (`oracc_translation_pairs.json`)
  - From Oracc publication dumps.
  - Script: `extract_oracc_translations.py`.

- **CuneiformTranslators pairs** (`cuneiform_translators_pairs.json`)
  - Large external dataset of Akkadian/Sumerian translations (the "CuneiformTranslators" project).
  - Script: `extract_cuneiform_translators_pairs.py`.
  - This was one of the highest-volume sources and a strong baseline for many genres.

- **Synthetic rare + domain-specific data** (`synthetic_rare_pairs.json`)
  - Generated by `generate_synthetic_data.py`.
  - Sources mixed in: Akkadian lexical dictionaries, Grok-generated literary pairs, stock medical/ritual phrases, plants/minerals, idiom patterns, rare vocabulary augmentation.
  - This file ended up with **exactly 131,637 pairs** — matching the dataset size used for the famous long v12a run.

### How They Were Combined for the Best Model

In the original work:
- Individual extractors produced the source pair files above (all with at least `atf` + `english`, often with `period`/`genre`/`source` metadata).
- `generate_synthetic_data.py` (and related steps) merged/augmented them, with emphasis on:
  - Paragraph-level context (from the CDLI2 extractor).
  - Oversampling royal epithets.
  - Synthetic examples for rare terms and specialized domains (medical, ritual, etc.).
- The final set used for the hero v12a-tagfree run was essentially `data/synthetic_rare_pairs.json` (131k pairs).
- This was then fed to `fine_tune_synthetic.py` (in tag-free mode) which:
  - Started from a **fresh** `t5-small` (no continued pretrain for the pure tag-free case).
  - Applied the prompt `"translate Akkadian to English: {atf}"`.
  - Ran long training (the optimal run used early stopping with patience=5, max ~50; best checkpoint at epoch 27).

The current minimal `train.py --tier best` already implements the correct recipe (fresh t5-small + tag-free prompt + stability settings). You just need to point it at a good combined file.

### Reproducing / Using the Best Data in This Repo

After copying the files from the backup (`../deep-cuneiform/data/*.json`):

```bash
# The 131k set that powered the near-manual v12a results
uv run python train.py --tier best \
  --data data/synthetic_rare_pairs.json \
  --epochs 28 \
  --early_stopping_patience 5 \
  --output models/atf-en-v12a-best

# Or fall back to the large eBL extract (still excellent, simpler)
uv run python train.py --tier best --data data/ebl_pairs.json ...
```

Other useful files now present:
- `data/cdli2_paragraph_pairs.json` — pure paragraph data (great for mixing experiments).
- `data/cuneiform_translators_pairs.json`, `data/oracc_translation_pairs.json`, `data/cdli*_translation_pairs.json` — additional volume and genre coverage.
- `data/ebl_fragments.json` — raw eBL cache (not needed for training).

If you want to experiment with custom mixes, you can concatenate the JSON pair lists (they share a compatible schema) and save as a new combined file, then point `train.py` at it. The original work did heavy curation + synthetic augmentation on top of the raw extracts.

## Next Steps After You Have a Working Model

See [REPRODUCTION.md](REPRODUCTION.md) for the complete record of the reproduction effort (including the exact commands used, why training stopped at epoch ~17.5, the inferences on the key cases, and concrete ideas for further improvement).

- Reproduce the v12a long-training result on `synthetic_rare_pairs.json` (or a custom mix including the paragraph data) to confirm the ~131k + 27-epoch recipe.
- Study the original `extract_paragraph_pairs.py` and `generate_synthetic_data.py` (in the backup) for ideas on new augmentation or filtering approaches.
- Try mixing in more paragraph data or different oversampling for royal/literary genres.
- Experiment with t5-base (the planned next step after t5-small was stable).
- Publish the final model + this README as a model card on Hugging Face.

This directory is intentionally small, clean, and focused on **understanding and reproducing the simplest path that actually delivered excellent results**.

(If you came from the larger research tree: the hero model there was `models/atf-translator-v12a-tagfree-final` and the stable reference was `atf-translator-stable-final`.)
