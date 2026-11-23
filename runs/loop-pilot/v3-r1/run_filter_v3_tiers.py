#!/usr/bin/env python3
"""One-pass filter_v3 comparison of gloss tiers on arm-S and qwen_improve.

Policies (applied after the existing cheap-keep / judge rule):
  lenient            — hard rejects only (gloss is a FLAG)
  strict_per_sign    — + forward per-sign threshold (n>=2 or ratio>=0.40)
  strict_per_sign_min3 — same, but ratio limb requires n_content >= 3
  strict_corpus      — + flat clean-human vocab threshold (n>=2 or ratio>=0.40)
  strict_reverse     — + reverse check (n>=1 mapped word with no ATF sign)

CPU only. Writes filter_v3_tiers_report.json and FILTER_V3_TIERS.md.
Never writes pairs.json. Does not train.
"""
from __future__ import annotations

import collections
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Reuse helpers and data loading from the existing runner.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_filter_v3 as base  # noqa: E402
import filter_v3 as f3  # noqa: E402

ET = base.ET
X = base.X
SEED_HAND = 20261123
POLICIES = (
    "lenient",
    "strict_per_sign",
    "strict_per_sign_min3",
    "strict_corpus",
    "strict_reverse",
)


def policy_over(flags, name):
    if name == "lenient":
        return False
    if name == "strict_per_sign":
        return bool(flags.get("gloss_over_threshold"))
    if name == "strict_per_sign_min3":
        return f3.gloss_over_threshold(flags.get("gloss") or {}, min_content=3)
    if name == "strict_corpus":
        return bool(flags.get("gloss_corpus_over_threshold"))
    if name == "strict_reverse":
        return bool(flags.get("gloss_reverse_over_threshold"))
    raise ValueError(name)


def fmt_pct(n, d):
    return base.fmt_pct(n, d)


def rate_table(counter_s, counter_k, n_s):
    keys = sorted(counter_s.keys(), key=lambda k: -counter_s[k])
    lines = ["| slice | arm S | kept | keep vs S |", "|---|---:|---:|---|"]
    for k in keys:
        s = counter_s[k]
        ke = counter_k[k]
        lines.append(f"| {k} | {s} | {ke} | {fmt_pct(ke, s)} |")
    return "\n".join(lines)


def main():
    now = datetime.now(ET)
    print("warming glossary + mine cache...", flush=True)
    import lemma_support as ls
    ls.build_glossary()
    f3._fold_index()
    f3._english_dict()
    f3.load_mine_cache()
    meta = (f3._MINE or {}).get("meta") or {}
    print("cache meta official_en", meta.get("official_en_lemmas_before"),
          "vocab", meta.get("vocab_size"), flush=True)

    print("loading data...", flush=True)
    pool = base.load_jsonl(base.POOL)
    cands = base.load_jsonl(X / "candidates.jsonl")
    improve, judges = {}, {}
    with open(X / "qwen_improve.jsonl") as f:
        for line in f:
            d = json.loads(line)
            improve[d["id"]] = d
    if (X / "qwen_judge.jsonl").exists():
        with open(X / "qwen_judge.jsonl") as f:
            for line in f:
                d = json.loads(line)
                judges[d["id"]] = d
    arm_s_ids = []
    with open(X / "loop_pairs_armS.jsonl") as f:
        for line in f:
            d = json.loads(line)
            arm_s_ids.append(d["prov"]["line_id"])
    arm_s = set(arm_s_ids)
    assert len(arm_s) == 1479, len(arm_s)

    prepared = []
    for i, rec in pool.items():
        cand = cands.get(i) or {}
        cs = cand.get("cands") or cand.get("family_decoded") or []
        top = cs[0] if cs else ""
        qrec = improve.get(i) or {}
        q = dict(qrec.get("propose") or {})
        if base.rec_has_error(qrec) or base.rec_has_error(q):
            q["error"] = q.get("error") or qrec.get("error") or True
        prepared.append({
            "id": i,
            "tablet": rec.get("tablet"),
            "atf": rec.get("atf") or qrec.get("atf") or cand.get("atf") or "",
            "english": (q.get("english") or "").strip(),
            "genre": rec.get("genre") or "",
            "period": rec.get("period") or "",
            "bucket": base.genre_bucket(rec.get("genre")),
            "line_no": rec.get("line_no"),
            "qwen": q,
            "top": top,
            "cands": cs,
            "verdict": (judges.get(i) or {}).get("verdict"),
            "in_arm_s": i in arm_s,
        })
    print(f"prepared {len(prepared)}; scoring once...", flush=True)

    rows = []
    for j, p in enumerate(prepared, 1):
        # Filter once, lenient, so flags are complete and ok = hard rejects only.
        ok, reasons, filt = base.cheap_keep_v3(
            p["atf"], p["qwen"], p["top"], p["cands"],
            tablet=p["tablet"], line_no=p["line_no"],
            genre=p["genre"], period=p["period"], paraphrase="lenient",
        )
        flags = (filt or {}).get("flags") or {}
        fails = (filt or {}).get("fails") or []
        hard_ok = bool(filt.get("ok")) if filt is not None else False
        base_ok = bool(ok) and p["verdict"] in {"better", "equivalent"}
        rec = {
            **{k: p[k] for k in ("id", "tablet", "atf", "english", "genre",
                                 "period", "bucket", "verdict", "in_arm_s")},
            "reasons": reasons,
            "fails": fails,
            "flags": flags,
            "hard_ok": hard_ok,
            "base_ok": base_ok,
            "policies": {},
        }
        for pol in POLICIES:
            over = policy_over(flags, pol)
            # arm-S style keep: cheap rule + judge + this policy's gloss reject
            rec["policies"][pol] = {
                "over": over,
                "filter_ok": hard_ok and not over,
                "keep": base_ok and not over,
            }
        rows.append(rec)
        if j % 1000 == 0:
            print(f"  {j}/{len(prepared)}", flush=True)

    def summarize(pol):
        s_rows = [r for r in rows if r["in_arm_s"]]
        kept = [r for r in s_rows if r["policies"][pol]["keep"]]
        rejected = [r for r in s_rows if not r["policies"][pol]["keep"]]
        filter_ok = sum(1 for r in s_rows if r["policies"][pol]["filter_ok"])
        gloss_only = [r for r in rejected
                      if "filter_v3" in (r["reasons"] or [])
                      or not r["policies"][pol]["filter_ok"]]
        # reject tags on arm S
        tags = collections.Counter()
        for r in s_rows:
            if r["policies"][pol]["filter_ok"]:
                continue
            if pol != "lenient" and r["hard_ok"] and r["policies"][pol]["over"]:
                tags["gloss_unlicensed"] += 1
            for t in base.fail_tags(r["fails"]):
                tags[t] += 1
        genre_s = collections.Counter(r["bucket"] for r in s_rows)
        genre_k = collections.Counter(r["bucket"] for r in kept)
        period_s = collections.Counter(r["period"] or "unknown" for r in s_rows)
        period_k = collections.Counter(r["period"] or "unknown" for r in kept)
        # improve pool: filter only
        n_imp = n_imp_ok = 0
        imp_fail = collections.Counter()
        for r, p in zip(rows, prepared):
            if not (p["english"] and not p["qwen"].get("error")):
                continue
            n_imp += 1
            if r["policies"][pol]["filter_ok"]:
                n_imp_ok += 1
            else:
                if pol != "lenient" and r["hard_ok"] and r["policies"][pol]["over"]:
                    imp_fail["gloss_unlicensed"] += 1
                for t in base.fail_tags(r["fails"]):
                    imp_fail[t] += 1
        admin_s = sum(1 for r in s_rows if base.is_admin(r["genre"]))
        admin_k = sum(1 for r in kept if base.is_admin(r["genre"]))
        return {
            "n_kept_arm_s": len(kept),
            "n_rejected_arm_s": len(rejected),
            "of_s_filter_ok": filter_ok,
            "tags": tags,
            "genre_s": genre_s, "genre_k": genre_k,
            "period_s": period_s, "period_k": period_k,
            "admin_s": admin_s, "admin_k": admin_k,
            "n_improve": n_imp,
            "n_improve_ok": n_imp_ok,
            "improve_fail": imp_fail,
            "kept_ids": [r["id"] for r in kept],
        }

    by = {pol: summarize(pol) for pol in POLICIES}
    for pol, d in by.items():
        print(f"{pol}: armS kept {d['n_kept_arm_s']}/1479  "
              f"filter_ok {d['of_s_filter_ok']}  "
              f"improve {d['n_improve_ok']}/{d['n_improve']}", flush=True)

    # Hand-check samples (new seed), from arm-S rows that lenient-keep but
    # the policy rejects (pure gloss rejects).
    rng = random.Random(SEED_HAND)

    def sample_gloss(pol, n=10):
        src = [r for r in rows if r["in_arm_s"]
               and r["policies"]["lenient"]["keep"]
               and not r["policies"][pol]["keep"]]
        rng_l = random.Random(SEED_HAND)
        rng_l.shuffle(src)
        out = []
        for r in src[:n]:
            g = (r["flags"] or {}).get("gloss") or {}
            rv = (r["flags"] or {}).get("gloss_reverse") or {}
            cv = (r["flags"] or {}).get("gloss_corpus") or {}
            out.append({
                "id": r["id"], "genre": r["genre"], "period": r["period"],
                "bucket": r["bucket"],
                "atf": r["atf"], "english": r["english"],
                "fails": r["fails"],
                "fwd_unlic": g.get("unlicensed"), "fwd_ratio": g.get("ratio"),
                "fwd_n": g.get("n_content"),
                "rev_unlic": rv.get("unlicensed"), "rev_unmapped": rv.get("unmapped"),
                "corp_unlic": cv.get("unlicensed"),
            })
        return out, len(src)

    samples = {}
    for pol in ("strict_per_sign", "strict_reverse", "strict_corpus",
                "strict_per_sign_min3"):
        samples[pol], samples[pol + "_n"] = sample_gloss(pol, 10)

    # 30-line panel
    panel = base.parse_panel()
    gate = {}
    with open(X / "spotcheck_gate_lines.jsonl") as f:
        for line in f:
            d = json.loads(line)
            gate[d["id"]] = d
    panel_rows = []
    for p in panel:
        g = gate.get(p["id"])
        if not g:
            continue
        filt = f3.check(g.get("atf") or "", g.get("ctrl") or "",
                        genre=g.get("genre"), period=g.get("period"),
                        tablet=g.get("tablet"), paraphrase="lenient")
        flags = filt["flags"]
        rec = {
            **p, "atf": g.get("atf"), "ref": g.get("english"),
            "genre": g.get("genre"), "ctrl": g.get("ctrl"),
            "hard_ok": filt["ok"], "fails": filt["fails"],
            "fwd": flags.get("gloss"), "fwd_over": flags.get("gloss_over_threshold"),
            "fwd_min3": f3.gloss_over_threshold(flags.get("gloss") or {}, min_content=3),
            "corpus": flags.get("gloss_corpus"),
            "corpus_over": flags.get("gloss_corpus_over_threshold"),
            "reverse": flags.get("gloss_reverse"),
            "reverse_over": flags.get("gloss_reverse_over_threshold"),
        }
        panel_rows.append(rec)

    def pstats(cat, pred):
        items = [x for x in panel_rows if x["cat"] == cat]
        n = sum(1 for x in items if pred(x))
        return {"n": len(items), "caught": n, "ids": [x["id"] for x in items if pred(x)]}

    panel_summary = {}
    for cat, label in (("c", "real_errors"), ("b", "paraphrases"), ("a", "formatting")):
        panel_summary[cat] = {
            "label": label,
            "hard": pstats(cat, lambda x: not x["hard_ok"]),
            "fwd": pstats(cat, lambda x: (not x["hard_ok"]) or x["fwd_over"]),
            "fwd_min3": pstats(cat, lambda x: (not x["hard_ok"]) or x["fwd_min3"]),
            "corpus": pstats(cat, lambda x: (not x["hard_ok"]) or x["corpus_over"]),
            "reverse": pstats(cat, lambda x: (not x["hard_ok"]) or x["reverse_over"]),
        }

    report = {
        "written": now.strftime("%Y-%m-%d %H:%M %Z"),
        "n_pool": len(prepared),
        "n_arm_s": 1479,
        "mine_meta": {k: meta.get(k) for k in (
            "source_train", "license_note", "official_en_lemmas_before",
            "official_plus_syn_wordnet", "after_plus_mined_lemmas", "vocab_size",
            "n_used", "n_seen", "excluded", "n_mined_sign_word",
            "n_mined_sign_word_post", "n_conflict_skip", "min_count", "min_pmi",
        )},
        "policies": {pol: {k: (dict(v) if isinstance(v, collections.Counter) else v)
                           for k, v in d.items() if k != "kept_ids"}
                     for pol, d in by.items()},
        "policy_keep_ids_counts": {pol: d["n_kept_arm_s"] for pol, d in by.items()},
        "samples": {k: v for k, v in samples.items() if not k.endswith("_n")},
        "sample_sizes": {k: samples[k] for k in samples if k.endswith("_n")},
        "panel": panel_rows,
        "panel_summary": panel_summary,
        "hand_seed": SEED_HAND,
    }
    # serialize counters
    def conv(o):
        if isinstance(o, collections.Counter):
            return dict(o)
        if isinstance(o, dict):
            return {k: conv(v) for k, v in o.items()}
        if isinstance(o, list):
            return [conv(x) for x in o]
        return o
    report = conv(report)
    (X / "filter_v3_tiers_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("wrote", X / "filter_v3_tiers_report.json", flush=True)

    # Markdown
    md = []
    md.append("# Filter v3 gloss expansion and reverse check")
    md.append("")
    md.append(f"Written {report['written']}. CPU only. Clean sources only.")
    md.append("")
    md.append("## Gloss list size (clean sources)")
    m = report["mine_meta"]
    md.append("")
    md.append(f"- Official ORACC/ePSD-style English lemmas (function words dropped): "
              f"**{m.get('official_en_lemmas_before')}**")
    md.append(f"- After curated synonyms + WordNet on those lemmas: "
              f"**{m.get('official_plus_syn_wordnet')}**")
    md.append(f"- After mined per-sign English from clean BY-SA pairs "
              f"(count≥{m.get('min_count')}, PMI≥{m.get('min_pmi')}): "
              f"**{m.get('after_plus_mined_lemmas')}** unique lemmas")
    md.append(f"- Flat clean-human vocab (lemmatized content words): "
              f"**{m.get('vocab_size')}**")
    md.append(f"- Pairs used: **{m.get('n_used')}** / {m.get('n_seen')} "
              f"(excluded {m.get('excluded')})")
    md.append("")
    md.append("## Keep counts on the 1,479 arm-S lines")
    md.append("")
    md.append("| policy | kept of 1479 | filter-ok of 1479 | improve-pool filter-ok |")
    md.append("|---|---:|---:|---:|")
    for pol in POLICIES:
        d = by[pol]
        md.append(f"| `{pol}` | {d['n_kept_arm_s']} "
                  f"({100.0*d['n_kept_arm_s']/1479:.1f}%) | "
                  f"{fmt_pct(d['of_s_filter_ok'], 1479)} | "
                  f"{fmt_pct(d['n_improve_ok'], d['n_improve'])} |")
    md.append("")
    for pol in POLICIES:
        d = by[pol]
        md.append(f"### {pol}: genre keep rate (arm S)")
        md.append("")
        md.append(rate_table(d["genre_s"], d["genre_k"], 1479))
        md.append("")
        md.append(f"### {pol}: period keep rate (arm S)")
        md.append("")
        md.append(rate_table(d["period_s"], d["period_k"], 1479))
        md.append("")
        md.append(f"Administrative share of kept: "
                  f"{fmt_pct(d['admin_k'], d['n_kept_arm_s'])} "
                  f"(arm S admin {fmt_pct(d['admin_s'], 1479)}).")
        md.append("")
        md.append("Reject tags (arm S, not filter-ok):")
        for k, v in collections.Counter(d["tags"]).most_common():
            md.append(f"- `{k}`: {v}")
        md.append("")

    md.append("## 30-line SPOTCHECK panel (ctrl hyps)")
    md.append("")
    md.append("Caught = hard reject OR the named gloss threshold. "
              "Cat (c) = 16 real errors; (b) = 3 good paraphrases; (a) = 5 formatting.")
    md.append("")
    md.append("| check | real errors (c) | paraphrases (b) flagged | formatting (a) |")
    md.append("|---|---|---|---|")
    for key, label in (("hard", "hard rejects only"),
                       ("fwd", "hard + forward per-sign"),
                       ("fwd_min3", "hard + forward, ratio min 3"),
                       ("corpus", "hard + corpus vocab"),
                       ("reverse", "hard + reverse n≥1")):
        row = [label]
        for cat in ("c", "b", "a"):
            s = panel_summary[cat][key]
            row.append(f"{s['caught']}/{s['n']}")
        md.append("| " + " | ".join(row) + " |")
    md.append("")
    md.append("Panel detail:")
    md.append("")
    for rec in panel_rows:
        md.append(f"- `{rec['id']}` ({rec['cat']}) hard_ok={rec['hard_ok']} "
                  f"fails={rec['fails']}")
        g = rec.get("fwd") or {}
        rv = rec.get("reverse") or {}
        cv = rec.get("corpus") or {}
        md.append(f"  fwd unlic={g.get('unlicensed')} over={rec['fwd_over']} "
                  f"min3={rec['fwd_min3']}; "
                  f"rev unlic={rv.get('unlicensed')} over={rec['reverse_over']}; "
                  f"corpus unlic={cv.get('unlicensed')} over={rec['corpus_over']}")
        if rec["id"] in {"fair:0243", "fair:0230"}:
            md.append(f"  ATF: `{rec.get('atf')}`")
            md.append(f"  ctrl: {rec.get('ctrl')}")
    md.append("")

    def samp(pol, title):
        md.append(f"## {title} (seed {SEED_HAND})")
        md.append("")
        md.append(f"Arm-S lines kept under lenient but rejected by `{pol}` "
                  f"(n={samples[pol+'_n']}).")
        md.append("")
        for i, r in enumerate(samples[pol], 1):
            md.append(f"{i}. `{r['id']}` — {r.get('genre') or '—'} / {r.get('period') or '—'}")
            md.append(f"   ATF: `{r['atf']}`")
            md.append(f"   EN: {r['english']}")
            md.append(f"   fwd: unlic={r['fwd_unlic']} ratio={r['fwd_ratio']} n={r['fwd_n']}")
            md.append(f"   rev: {r['rev_unlic']} unmapped={r['rev_unmapped']}")
            md.append(f"   corpus: {r['corp_unlic']}")
            md.append("")

    samp("strict_per_sign", "10 random strict forward (per-sign) gloss rejects")
    samp("strict_reverse", "10 random strict reverse gloss rejects")

    (X / "FILTER_V3_TIERS.md").write_text("\n".join(md) + "\n")
    print("wrote", X / "FILTER_V3_TIERS.md", flush=True)


if __name__ == "__main__":
    main()
