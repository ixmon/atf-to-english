#!/usr/bin/env python3
"""
Minimal single-script trainer for high-quality ATF -> English translation.

This distills the recipe that produced the strong "stable" model (30k samples, 5 epochs)
and the later v12a tag-free model (large combined data, ~28 epochs, "translate Akkadian to English:").

Two tiers (visible "simplest path"):
  --tier stable   : fast, reliable, already very usable (matches the training-guide "best model" at one point)
  --tier best     : the longer-training tag-free approach that reached near-manual quality on hard texts

Stability was critical — earlier attempts with FP16 collapsed completely.

Usage examples:
  # Quick POC (5k samples, 3 epochs) — proves the pipeline without waiting
  uv run python train.py --data data/ebl_small.json --max-samples 5000 --epochs 3 --output models/poc

  # The reliable "stable" tier (what you should run first on real data)
  uv run python train.py --tier stable --data data/ebl_pairs.json --output models/atf-en-stable-final

  # Closer to the documented best (v12a style). Use more data + more epochs.
  # For the absolute best results people used paragraph-level data too (see README).
  TIER=best EPOCHS=28 uv run python train.py --data data/ebl_pairs.json --output models/atf-en-best-final

  # Long run on exotic hardware (see scripts/run_on_ngc.sh and README)
  TIER=best EPOCHS=50 EARLY_STOPPING_PATIENCE=5 LEARNING_RATE=3e-4 ...

Environment variables (override defaults / CLI):
  TIER, EPOCHS, MAX_SAMPLES, LEARNING_RATE, BATCH_SIZE, MAX_LENGTH, EARLY_STOPPING_PATIENCE
"""

import argparse
import json
import os
from pathlib import Path

from datasets import Dataset
from transformers import (
    T5Tokenizer,
    T5ForConditionalGeneration,
    Trainer,
    TrainingArguments,
    DataCollatorForSeq2Seq,
)
import torch

# --------------------------- Config & Tier Selection ---------------------------

def get_config():
    tier = os.environ.get("TIER", "stable").lower()
    # CLI will override env for the main ones
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=["stable", "best"], default=tier)
    parser.add_argument("--data", default="data/ebl_pairs.json")
    parser.add_argument("--output", default=None)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--tag-free", action="store_true", help="Force the winning tag-free prompt (default for best tier)")
    args, _ = parser.parse_known_args()

    tier = args.tier

    if tier == "stable":
        # The recipe from train_stable.py that "just worked"
        max_samples = args.max_samples or int(os.environ.get("MAX_SAMPLES", 30000))
        epochs = args.epochs or int(os.environ.get("EPOCHS", 5))
        lr = float(os.environ.get("LEARNING_RATE", "1e-4"))
        batch = int(os.environ.get("BATCH_SIZE", 8))
        grad_accum = 4
        max_len = int(os.environ.get("MAX_LENGTH", 256))
        patience = int(os.environ.get("EARLY_STOPPING_PATIENCE", 0))
        prompt_prefix = "translate ATF to English: "
        base_model = "t5-small"
        default_output = "models/atf-translator-stable-final"
    else:
        # v12a / best tag-free style (fresh t5-small, "translate Akkadian...", longer training)
        max_samples = args.max_samples or int(os.environ.get("MAX_SAMPLES", 0))  # 0 = all
        epochs = args.epochs or int(os.environ.get("EPOCHS", 28))
        lr = float(os.environ.get("LEARNING_RATE", "3e-4"))
        batch = int(os.environ.get("BATCH_SIZE", 16))
        grad_accum = 2  # effective batch = 16×2 = 32 (matches original recipe, half the peak memory)
        max_len = int(os.environ.get("MAX_LENGTH", 256))
        patience = int(os.environ.get("EARLY_STOPPING_PATIENCE", 5))
        prompt_prefix = "translate Akkadian to English: "   # the version used in the successful long runs
        base_model = "t5-small"
        default_output = "models/atf-translator-best-final"

    output_dir = args.output or os.environ.get("OUTPUT", default_output)

    return {
        "tier": tier,
        "data_path": args.data,
        "output_dir": output_dir,
        "max_samples": max_samples,
        "epochs": epochs,
        "lr": lr,
        "batch": batch,
        "grad_accum": grad_accum,
        "max_len": max_len,
        "patience": patience,
        "prompt_prefix": prompt_prefix,
        "base_model": base_model,
        "tag_free": True,  # the simplest successful path was tag-free
    }


def load_pairs(path: str, max_samples: int):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Pairs file not found: {path}. Run download_pairs.py first.")

    data = json.loads(p.read_text(encoding="utf-8"))
    pairs = data.get("pairs", data) if isinstance(data, dict) else data

    # Only pairs that have usable English (the signal the models were trained on)
    pairs = [p for p in pairs if p.get("english", "").strip()]
    if max_samples and max_samples > 0:
        pairs = pairs[:max_samples]
    print(f"Using {len(pairs)} pairs with English translations")
    return pairs


def main():
    cfg = get_config()
    print("=" * 70)
    print(f"ATF → English  |  Tier: {cfg['tier'].upper()}  |  Tag-free: {cfg['tag_free']}")
    print(f"Base: {cfg['base_model']}   Epochs: {cfg['epochs']}   LR: {cfg['lr']}")
    print(f"Prompt prefix: {cfg['prompt_prefix']!r}")
    print(f"Data: {cfg['data_path']}")
    print(f"Output: {cfg['output_dir']}")
    print("=" * 70)

    pairs = load_pairs(cfg["data_path"], cfg["max_samples"])

    # Build dataset exactly like the winning runs
    data_dict = {
        "input_text": [cfg["prompt_prefix"] + p["atf"] for p in pairs],
        "target_text": [p["english"] for p in pairs],
    }
    raw_ds = Dataset.from_dict(data_dict)
    split = raw_ds.train_test_split(test_size=0.05, seed=42)
    print(f"Train: {len(split['train'])}  |  Eval: {len(split['test'])}")

    tokenizer = T5Tokenizer.from_pretrained(cfg["base_model"])
    model = T5ForConditionalGeneration.from_pretrained(cfg["base_model"])

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    def preprocess(examples):
        inputs = tokenizer(
            examples["input_text"],
            truncation=True,
            max_length=cfg["max_len"],
        )
        labels = tokenizer(
            examples["target_text"],
            truncation=True,
            max_length=cfg["max_len"],
        )
        inputs["labels"] = labels["input_ids"]
        return inputs

    print("Tokenizing ...")
    tokenized = split.map(preprocess, batched=True, remove_columns=["input_text", "target_text"])

    # The stability recipe that mattered (no FP16 on the hardware that blew up, grad clipping, etc.)
    training_args = TrainingArguments(
        output_dir=cfg["output_dir"],
        num_train_epochs=cfg["epochs"],
        per_device_train_batch_size=cfg["batch"],
        per_device_eval_batch_size=cfg["batch"],
        gradient_accumulation_steps=cfg["grad_accum"],

        learning_rate=cfg["lr"],
        warmup_ratio=0.1,
        weight_decay=0.01,
        max_grad_norm=1.0,           # essential

        fp16=False,                  # CRITICAL — FP16 caused total collapse (NaNs, loss→0, output commas)
        bf16=False,

        logging_steps=50,
        eval_strategy="steps",
        eval_steps=1000,
        save_strategy="steps",
        save_steps=1000,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",
        dataloader_num_workers=0,       # CRITICAL: avoid fork-based memory duplication on unified memory (GB10)
    )

    # Early stopping via the Trainer callback if patience > 0
    callbacks = []
    if cfg["patience"] > 0:
        from transformers import EarlyStoppingCallback
        callbacks.append(EarlyStoppingCallback(early_stopping_patience=cfg["patience"]))

    # Dynamic padding — only pad to the longest sample in each batch, not globally to max_length.
    # This massively reduces memory vs the old padding="max_length" approach.
    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        data_collator=data_collator,
        callbacks=callbacks,
    )

    print("\n=== Starting training ===\n")
    trainer.train()

    # Save the final model (best checkpoint is also available in the output dir)
    final_path = Path(cfg["output_dir"])
    final_path.mkdir(parents=True, exist_ok=True)
    trainer.save_model(final_path)
    tokenizer.save_pretrained(final_path)
    print(f"\nModel saved to {final_path}")

    # Quick smoke tests (same style as the original train_* scripts)
    print("\n=== Quick inference tests ===")
    model.eval()
    model.to(device)

    test_cases = [
        "BAR# 13 AN.KU₁₀ sin 5 ITU",
        "[MU 60+3.KA]M {i#}an# LUGAL#",
        "lugal ki-en-gi-ra",
    ]
    for atf in test_cases:
        inp = cfg["prompt_prefix"] + atf
        inputs = tokenizer(inp, return_tensors="pt", max_length=cfg["max_len"], truncation=True).to(device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=80, num_beams=4, early_stopping=True)
        result = tokenizer.decode(out[0], skip_special_tokens=True)
        print(f"ATF: {atf}")
        print(f"→ {result}\n")

    print("Training complete.")


if __name__ == "__main__":
    main()