#!/usr/bin/env python3
"""
Minimal ATF-English pair downloader / extractor for the eBL API.

This is the data source that powered the high-quality T5 translation models
(stable 30k and the v12a ~28-epoch "near manual" result).

Usage:
  uv run python download_pairs.py                  # small default batch + extract
  uv run python download_pairs.py --full           # all fragments (slow, ~25k+)
  uv run python download_pairs.py --small --output data/ebl_small.json
  uv run python download_pairs.py --force-fetch    # ignore cache

Output:
  data/ebl_pairs.json (or your --pairs-output) containing
  {"pairs": [{"atf": "...", "english": "..."}, ...]}

The extraction logic looks for inline #tr.en: translations following ATF content lines.
"""

import argparse
import json
import re
from pathlib import Path
import requests

URL = "https://www.ebl.lmu.de/api/fragments/retrieve-all"


def fetch_fragments(url_base: str, skip: int = 0, batch_size: int = 1000, full: bool = False):
    fragments = []
    total = 0
    while True:
        url = f"{url_base}?skip={skip}"
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            print(f"Error {resp.status_code} on {url}")
            break
        data = resp.json()
        batch = data.get("fragments", [])
        fragments.extend(batch)
        total += len(batch)
        print(f"Fetched {len(batch)} (total {total})")
        if not full or len(batch) < batch_size:
            break
        skip += batch_size
    return fragments


def extract_atf_english_pairs(fragments):
    """Reproduces the logic that produced ebl_pairs.json used for the good models."""
    pairs = []
    for frag in fragments:
        atf = frag.get("atf", "") or ""
        lines = atf.split("\n")
        current_atf_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#tr.en"):
                if current_atf_lines:
                    atf_text = " ".join(current_atf_lines)
                    eng = re.sub(r"^#tr\.en[.:]?\s*", "", stripped).strip()
                    if eng:
                        pairs.append({"atf": atf_text, "english": eng})
                current_atf_lines = []
            elif stripped and not stripped.startswith(("@", "$", "&", ">", "#")):
                # Content line (strip leading line numbers like "1. " or "1'. ")
                clean = re.sub(r"^\d+['\".]?\s*", "", stripped)
                if clean:
                    current_atf_lines.append(clean)
        # trailing ATF without translation (rarely useful, skipped)
    return pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Download the entire collection")
    parser.add_argument("--small", action="store_true", help="Force a very small test batch (first ~200)")
    parser.add_argument("--output", default="data/ebl_fragments.json", help="Raw fragments cache")
    parser.add_argument("--pairs-output", default="data/ebl_pairs.json", help="Extracted pairs")
    parser.add_argument("--force-fetch", action="store_true")
    args = parser.parse_args()

    out_path = Path(args.output)
    pairs_path = Path(args.pairs_output)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pairs_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and not args.force_fetch:
        print(f"Loading cached fragments from {out_path}")
        fragments = json.loads(out_path.read_text(encoding="utf-8")).get("fragments", [])
    else:
        print("Fetching from eBL API ...")
        max_skip = 200 if args.small else None
        fragments = fetch_fragments(URL, full=args.full and not args.small)
        if args.small:
            fragments = fragments[:200]
        out_path.write_text(json.dumps({"fragments": fragments}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved raw fragments to {out_path}")

    print("Extracting ATF-English pairs from inline #tr.en ...")
    pairs = extract_atf_english_pairs(fragments)
    pairs_path.write_text(json.dumps({"pairs": pairs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted {len(pairs)} pairs with English translations -> {pairs_path}")

    # Quick stats
    with_english = [p for p in pairs if p.get("english")]
    print(f"Pairs that have non-empty English: {len(with_english)}")


if __name__ == "__main__":
    main()