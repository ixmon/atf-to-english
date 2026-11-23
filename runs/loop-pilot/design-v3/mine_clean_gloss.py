#!/usr/bin/env python3
"""Mine per-sign English, a flat corpus vocab, and a reverse gloss index
from clean CC BY-SA training pairs only.

Sources: clean ORACC glossary (lemma_support; ETCSL/eBL already excluded)
and runs/clean-bysa-v4e/train.json human translation pairs.

Excluded from the pairs: ETCSL, eBL, NC, B2c, synth, name-aux / transliterate
tasks. Alignment suffixes (=P= / =N= / =G=) are stripped from ATF.

Writes: runs/loop-pilot/design-v3/cache/clean_gloss_mine.json.gz

CPU only. No GPU, no training.
"""
from __future__ import annotations

import collections
import gzip
import json
import math
import os
import re
import sys
import time

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(DIR, "..", "..", ".."))
if os.path.basename(ROOT) != "atf-translate-test":
    # DIR is .../runs/loop-pilot/design-v3 → repo is three up? 
    # design-v3 is at repo/runs/loop-pilot/design-v3, so 3 ups is repo.
    pass
sys.path.insert(0, DIR)
sys.path.insert(0, os.path.join(DIR, "v2filter"))

import filter_v3 as f3  # noqa: E402
import lemma_support as ls  # noqa: E402

TRAIN = os.path.join(ROOT, "runs", "clean-bysa-v4e", "train.json")
CACHE = os.path.join(DIR, "cache", "clean_gloss_mine.json.gz")

MIN_COUNT = 5
MIN_PMI = 2.0


def training_atf(atf: str) -> str:
    a = atf or ""
    for sep in ("=P=", "=N=", "=G=", "=A=", "=T="):
        if sep in a:
            a = a.split(sep)[0]
    return a.strip()


def is_clean_human_pair(r, excluded):
    atf = r.get("atf") or ""
    en = r.get("english") or r.get("en") or r.get("target") or ""
    if not atf.strip() or not str(en).strip():
        excluded["no_text"] += 1
        return False
    prov = r.get("prov") or {}
    family = str(prov.get("family") or "")
    pool = str(prov.get("from_pool") or "")
    lic = str(prov.get("license") or r.get("license") or "")
    reasons = " ".join(prov.get("reasons") or [])
    project = str(prov.get("project") or r.get("project") or "")
    status = str(prov.get("status") or "")
    task = str(r.get("task") or r.get("prefix") or r.get("input") or "")
    blob = " ".join([family, pool, lic, reasons, project, status,
                     str(r.get("source") or ""), task]).lower()
    if "transliterate" in task.lower() or str(task).startswith("name"):
        excluded["aux"] += 1
        return False
    if "etcsl" in blob or "epsd2/literary" in blob:
        excluded["etcsl"] += 1
        return False
    if re.search(r"\bebl\b", blob) and "ebla" not in blob:
        excluded["ebl"] += 1
        return False
    if re.search(r"\bnc\b|non-?commercial|cc by-nc", blob):
        excluded["nc"] += 1
        return False
    if re.search(r"\bb2c\b", blob):
        excluded["b2c"] += 1
        return False
    if "synth" in pool.lower() or "synth" in family.lower():
        excluded["synth"] += 1
        return False
    return True


def english_content_lemmas(english: str):
    out = []
    seen = set()
    for w in f3._en_words(english):
        bare = f3.typo_fold(w).lstrip("%").strip("[]()<>")
        if not bare:
            continue
        low = bare.lower()
        if low in f3._GLOSS_STOP:
            continue
        if f3._NUM_EN.match(bare) or re.match(r"^\d+$", bare):
            continue
        if any(ch in w for ch in f3.ARTIFACT_CHARS):
            continue
        fw = f3.fold_alnum(bare)
        if len(fw) < 3:
            continue
        lem = f3._lemmatize_en(bare)
        if not lem or lem in f3._GLOSS_STOP or lem in seen:
            continue
        seen.add(lem)
        out.append(lem)
    return out


def official_reverse_and_counts():
    """Build word→signs/cfs from the clean ORACC glossary + EXTRA_SYNONYMS."""
    g = ls.build_glossary()
    word_signs = collections.defaultdict(set)
    word_cfs = collections.defaultdict(set)
    official_lemmas = set()
    n_items = 0

    def add_en(word, form, cf):
        lem = f3._lemmatize_en(word)
        if not lem or lem in f3._GLOSS_STOP or len(lem) < 3:
            return
        official_lemmas.add(lem)
        if form and f3._is_compact_sign(form):
            word_signs[lem].add(form)
        if cf:
            c = f3.typo_fold(cf).replace("-", "")
            c = re.sub(r"[^a-z0-9]+", "", c)
            if c and len(c) >= 3:
                word_cfs[lem].add(c)
            if f3._is_compact_sign(cf):
                word_signs[lem].add(ls.norm_form(cf) or f3.typo_fold(cf))

    for form, items in g.items():
        short_form = form if f3._is_compact_sign(form) else None
        for it in items:
            n_items += 1
            cf = it.get("cf") or ""
            gw = it.get("gw") or ""
            sense = it.get("sense") or ""
            for w in f3._gloss_words_from_sense(gw) + f3._gloss_words_from_sense(sense):
                add_en(w, short_form, cf)
            key_cf = f3.typo_fold(cf).replace("-", "")
            key_gw = f3.typo_fold(gw).replace("-", "")
            for key in (key_cf, key_gw, f3.typo_fold(form).replace("-", "")):
                for w in ls.EXTRA_SYNONYMS.get(key, []) or []:
                    add_en(w, short_form, cf)
    # logograms
    for key, words in (f3.fv.LOGOGRAMS or {}).items():
        for w in words or []:
            add_en(w, key, "")

    w_signs = {w: f3._shortest_forms(s, 80) for w, s in word_signs.items() if s}
    w_cfs = {w: f3._shortest_forms(c, 24) for w, c in word_cfs.items() if c}
    return w_signs, w_cfs, official_lemmas, n_items, len(g)


def official_conflict_signs(official_word_signs):
    """For each English lemma, the official signs that already license it."""
    return official_word_signs


def mine_pairs(official_word_signs):
    excluded = collections.Counter()
    sign_n = collections.Counter()
    word_n = collections.Counter()
    sw = collections.Counter()
    vocab = collections.Counter()
    n_used = 0
    n_seen = 0
    t0 = time.time()
    print(f"loading {TRAIN} ...", flush=True)
    with open(TRAIN) as f:
        data = json.load(f)
    recs = data["pairs"] if isinstance(data, dict) else data
    print(f"n records {len(recs)}", flush=True)
    for r in recs:
        n_seen += 1
        if not is_clean_human_pair(r, excluded):
            continue
        atf = training_atf(r.get("atf") or "")
        en = r.get("english") or r.get("en") or ""
        if not atf or not en:
            excluded["no_text"] += 1
            continue
        keys = []
        seenk = set()
        for k in f3.atf_lookup_keys(atf):
            fk = f3.fold_alnum(k)
            if not fk or len(fk) < 2 or fk in seenk:
                continue
            # keep a stable surface (prefer hyphenated / indexed)
            seenk.add(fk)
            keys.append(k)
        words = english_content_lemmas(en)
        if not keys or not words:
            excluded["empty_keys_or_words"] += 1
            continue
        n_used += 1
        for k in keys:
            fk = f3.fold_alnum(k)
            sign_n[fk] += 1
        for w in words:
            word_n[w] += 1
            vocab[w] += 1
        for k in keys:
            fk = f3.fold_alnum(k)
            for w in words:
                sw[(fk, w)] += 1
        if n_used % 50000 == 0:
            print(f"  used {n_used}/{n_seen}  {time.time()-t0:.1f}s", flush=True)
    N = n_used
    mined_sw = {}
    n_conflict_skip = 0
    for (sk, w), c in sw.items():
        if c < MIN_COUNT:
            continue
        # PMI in bits
        pmi = math.log2((c * N) / (sign_n[sk] * word_n[w]))
        if pmi < MIN_PMI:
            continue
        # official-conflict: do not attach a word to a sign if that word is
        # already an official gloss of a *different* sign (sila3 must not
        # inherit lamb from sila4 cooccurrence on the same account line).
        official_for_w = official_word_signs.get(w) or []
        official_folds = {f3.fold_alnum(s) for s in official_for_w if s}
        official_folds.discard("")
        if official_folds and sk not in official_folds:
            # allow if this sign's *own* official glosses are synonyms of w
            # (checked later at filter load against official_gloss). Skip here
            # when the word has a clear official home elsewhere.
            n_conflict_skip += 1
            continue
        mined_sw.setdefault(sk, {})[w] = {"c": int(c), "pmi": round(pmi, 3)}
    # word → mined signs (only passing pairs)
    word_signs_mined = {}
    for sk, words in mined_sw.items():
        for w, st in words.items():
            word_signs_mined.setdefault(w, {})[sk] = st
    meta_counts = {
        "n_seen": n_seen,
        "n_used": n_used,
        "excluded": dict(excluded),
        "n_sign_types": len(sign_n),
        "n_word_types_in_pairs": len(word_n),
        "n_cooc_raw": len(sw),
        "n_mined_sign_word": sum(len(v) for v in mined_sw.values()),
        "n_signs_with_mined": len(mined_sw),
        "n_conflict_skip": n_conflict_skip,
        "min_count": MIN_COUNT,
        "min_pmi": MIN_PMI,
        "vocab_size": len(vocab),
    }
    return mined_sw, word_signs_mined, vocab, meta_counts


def main():
    t0 = time.time()
    print("building official reverse from clean ORACC glossary ...", flush=True)
    off_signs, off_cfs, official_lemmas, n_items, n_forms = official_reverse_and_counts()
    print(f"  forms={n_forms} items={n_items} official_en_lemmas={len(official_lemmas)} "
          f"reverse_words={len(off_signs)}  {time.time()-t0:.1f}s", flush=True)

    # synonym / wordnet expansion size (allowed-side unique lemmas)
    syn_lemmas = set(official_lemmas)
    for w in list(official_lemmas):
        syn_lemmas.update(x for x in f3._syns(w) if x and x not in f3._GLOSS_STOP and len(x) >= 3)
    print(f"  official+syn+wordnet lemmas={len(syn_lemmas)}", flush=True)

    mined_sw, mined_ws, vocab, mine_meta = mine_pairs(off_signs)
    # after: official + syn + mined words
    after = set(syn_lemmas)
    for sk, words in mined_sw.items():
        after.update(words.keys())
    after = {w for w in after if w and w not in f3._GLOSS_STOP and len(w) >= 3}

    meta = {
        "source_train": os.path.relpath(TRAIN, ROOT),
        "license_note": (
            "Clean CC BY-SA training pairs (runs/clean-bysa-v4e/train.json) "
            "plus clean ORACC/ePSD-style glossary via lemma_support. "
            "Excluded: ETCSL, eBL, NC, B2c, synth, name-aux."
        ),
        "official_forms": n_forms,
        "official_items": n_items,
        "official_en_lemmas_before": len(official_lemmas),
        "official_plus_syn_wordnet": len(syn_lemmas),
        "after_plus_mined_lemmas": len(after),
        "vocab_size": len(vocab),
        **mine_meta,
        "elapsed_s": round(time.time() - t0, 1),
    }
    payload = {
        "meta": meta,
        "vocab": dict(vocab),
        "sign_words": mined_sw,
        "word_signs_mined": mined_ws,
        "official_word_signs": off_signs,
        "official_word_cfs": off_cfs,
    }
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with gzip.open(CACHE, "wt", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    sz = os.path.getsize(CACHE)
    print("wrote", CACHE, f"{sz/1e6:.1f} MB")
    print("META", json.dumps(meta, indent=2))
    # sanity: lamb, build, year, smear, banquet, strong
    for w in ("lamb", "build", "year", "smear", "anoint", "restore", "return",
              "determine", "banquet", "strong", "silversmith", "subtotal", "stew"):
        signs = (off_signs.get(w) or [])[:8]
        mined = list((mined_ws.get(w) or {}).items())[:6]
        print(f"  word={w:14} official_signs={signs} mined={mined}")


if __name__ == "__main__":
    main()
