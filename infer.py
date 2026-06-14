#!/usr/bin/env python3
"""
Minimal tag-free ATF → English inference (the path that delivered the best manual quality).

Usage:
  uv run python infer.py --atf "BAR# 13 AN.KU₁₀ sin 5 ITU"
  uv run python infer.py --interactive
  uv run python infer.py --model models/atf-translator-best-final --atf "..."

This uses the exact training prompt style ("translate Akkadian to English: " or the ATF variant).
Beam search (num_beams=4) matches what was used for the reported results.
"""

import argparse
import torch
from transformers import T5Tokenizer, T5ForConditionalGeneration
from pathlib import Path


def load_model(model_path: str):
    print(f"Loading model from {model_path} ...")
    model = T5ForConditionalGeneration.from_pretrained(model_path)
    try:
        tokenizer = T5Tokenizer.from_pretrained(model_path)
    except Exception:
        tokenizer = T5Tokenizer.from_pretrained("t5-small")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    model.eval()
    print(f"Device: {device}")
    return model, tokenizer, device


def translate(model, tokenizer, device, atf: str, prompt_prefix: str = "translate Akkadian to English: ",
              num_beams: int = 4, max_new_tokens: int = 100) -> str:
    text = prompt_prefix + atf
    inputs = tokenizer(text, return_tensors="pt", max_length=256, truncation=True).to(device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            num_beams=num_beams,
            early_stopping=True,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", "-m", default="models/atf-translator-stable-final")
    parser.add_argument("--atf", "-a")
    parser.add_argument("--interactive", "-i", action="store_true")
    parser.add_argument("--beams", type=int, default=4)
    parser.add_argument("--prompt", default=None, help="Override prompt prefix (rarely needed)")
    args = parser.parse_args()

    model, tokenizer, device = load_model(args.model)

    prompt = args.prompt or "translate Akkadian to English: "

    if args.interactive:
        print("Interactive mode. Type ATF (empty line to quit).")
        while True:
            try:
                atf = input("ATF> ").strip()
            except EOFError:
                break
            if not atf:
                break
            out = translate(model, tokenizer, device, atf, prompt, args.beams)
            print("→", out, "\n")
        return

    if args.atf:
        out = translate(model, tokenizer, device, args.atf, prompt, args.beams)
        print("ATF :", args.atf)
        print("→  ", out)
    else:
        # Default demo (one of the examples used in the original stable training tests)
        demo = "BAR# 13 AN.KU₁₀ sin 5 ITU"
        out = translate(model, tokenizer, device, demo, prompt, args.beams)
        print("Demo ATF:", demo)
        print("→", out)


if __name__ == "__main__":
    main()