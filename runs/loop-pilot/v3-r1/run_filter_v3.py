#!/usr/bin/env python3
"""Offline filter-v3 pass on v3-r1 arm-S pairs and the qwen_improve pool.

Runs both paraphrase modes:
  strict  (chrF-phase default) — gloss threshold is a hard reject
  lenient                       — gloss stays a FLAG, paraphrases kept

Writes FILTER_V3.md and filter_v3_report.json. CPU only. Does not train.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
R = Path("/home/darkstar/cursor/atf-translate-test")
X = R / "runs/loop-pilot/v3-r1"
POOL = R / "runs/loop-pilot/pool-v3/pool_5k.jsonl"
DESIGN = R / "runs/loop-pilot/design-v3"
sys.path.insert(0, str(DESIGN))
sys.path.insert(0, str(DESIGN / "v2filter"))

import sacrebleu  # noqa: E402
import filter_v3 as f3  # noqa: E402

AGREE_CHRF = 85.0
SEED = 42
HARD_GENRE_KEYS = ("literary", "royal", "medical", "medicine")
MODES = ("lenient", "strict")


def fold(s):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode(),
    )


def agrees(x, top):
    if fold(x) == fold(top):
        return True
    if x and top and sacrebleu.CHRF().sentence_score(x, [top]).score >= AGREE_CHRF:
        return True
    return False


def disagreement(cands):
    if not cands:
        return False
    top = cands[0]
    return any(not agrees(x, top) for x in cands[1:])


def word_cap_ok(qen, top):
    qw, tw = (qen or "").split(), (top or "").split()
    return len(qw) <= 1.8 * max(len(tw), 1) + 4


def rec_has_error(d):
    if d.get("error"):
        return True
    prop = d.get("propose") if isinstance(d.get("propose"), dict) else d
    if isinstance(prop, dict) and prop.get("error"):
        return True
    return False


def genre_bucket(g):
    gl = (g or "").lower()
    if "admin" in gl:
        return "Administrative"
    if "letter" in gl:
        return "Letter"
    if "lexical" in gl or "lexicography" in gl:
        return "Lexical"
    if "literary" in gl:
        return "Literary"
    if "medical" in gl or "medicine" in gl or "diagnostic" in gl:
        return "Medical"
    if "royal" in gl or "official or display" in gl or "monumental" in gl:
        return "Royal / official"
    if "legal" in gl:
        return "Legal"
    if "prayer" in gl or "incantation" in gl or "ritual" in gl:
        return "Prayer / incantation"
    if not gl or gl == "?":
        return "(unlabeled)"
    return "Other"


def is_hard_genre(g):
    gl = (g or "").lower()
    return any(k in gl for k in HARD_GENRE_KEYS)


def is_admin(g):
    return "admin" in (g or "").lower()


def load_jsonl(path, key="id"):
    out = {}
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            out[d[key]] = d
    return out


def cheap_keep_v3(atf, qwen, top, cands, tablet=None, line_no=None,
                  genre=None, period=None, paraphrase="strict"):
    reasons = []
    if not disagreement(cands):
        reasons.append("unanimous")
    en = (qwen.get("english") or "").strip()
    if qwen.get("decision") == "reject" and not en:
        reasons.append("rejected")
    if qwen.get("error"):
        reasons.append("qwen_error")
    conf = (qwen.get("confidence") or "").lower()
    if conf not in {"high", "medium"}:
        reasons.append(f"confidence:{conf or 'missing'}")
    if en and not word_cap_ok(en, top):
        reasons.append("word_cap")
    filt = None
    if en:
        filt = f3.check(atf, en, qwen=qwen, tablet=tablet, line_no=line_no,
                        cands=cands, genre=genre, period=period,
                        paraphrase=paraphrase)
        if not filt.get("ok"):
            reasons.append("filter_v3")
    else:
        if "rejected" not in reasons:
            reasons.append("empty_english")
    return (not reasons), reasons, filt


def parse_panel():
    text = (X / "SPOTCHECK.md").read_text()
    rows = []
    for m in re.finditer(
        r"\|\s*(fair:\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|",
        text,
    ):
        cols = [c.strip() for c in m.groups()]
        mm = re.search(r"\*\*([abcd])\*\*", cols[-1])
        if not mm:
            continue
        rows.append({
            "id": cols[0],
            "cat": mm.group(1),
            "note": cols[-1],
            "slice": cols[1],
        })
    return rows


def fmt_pct(n, d):
    if not d:
        return "—"
    return f"{n}/{d} ({100.0 * n / d:.1f}%)"


def fail_tags(fails):
    tags = set()
    for f in fails or []:
        tags.add(f.split(":")[0])
    return tags


def reason_counter(rows):
    c = collections.Counter()
    for r in rows:
        if "filter_v3" in (r.get("reasons") or []):
            tags = fail_tags(r.get("v3_extra") or r.get("fails"))
            if not tags:
                for f in r.get("fails") or []:
                    tags.add("v2:" + f.split(":")[0])
            for t in tags:
                c[t] += 1
        for rs in r.get("reasons") or []:
            if rs != "filter_v3":
                c[rs] += 1
    return c


def md_rate(counter_s, counter_k, n_s, n_k):
    keys = sorted(set(counter_s) | set(counter_k), key=lambda k: (-counter_s[k], k))
    out = ["| slice | v3-r1 arm S (1479) | kept | keep vs S |",
           "|---|---:|---:|---:|"]
    for k in keys:
        vs, vk = counter_s[k], counter_k[k]
        out.append(
            f"| {k} | {vs} ({100 * vs / n_s:.1f}%) | {vk} ({100 * vk / max(n_k, 1):.1f}% of kept) | {fmt_pct(vk, vs)} |"
        )
    out.append(f"| **all** | **{n_s}** | **{n_k}** | **{fmt_pct(n_k, n_s)}** |")
    return "\n".join(out)


def clip(s, n=160):
    s = (s or "").replace("\n", " ")
    return s if len(s) <= n else s[: n - 3] + "..."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paraphrase", choices=("strict", "lenient", "both"), default="both",
                    help="which mode to run (default both, for the report)")
    args = ap.parse_args()
    modes = list(MODES) if args.paraphrase == "both" else [args.paraphrase]

    now = datetime.now(ET)
    print("warming glossary...", flush=True)
    import lemma_support as ls
    ls.build_glossary()
    f3._fold_index()
    f3._english_dict()
    print("loading data...", flush=True)

    pool = load_jsonl(POOL)
    cands = load_jsonl(X / "candidates.jsonl")
    improve = {}
    with open(X / "qwen_improve.jsonl") as f:
        for line in f:
            d = json.loads(line)
            improve[d["id"]] = d
    judges = {}
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

    # Precompute keep-rule inputs once; filter is mode-specific.
    prepared = []
    for i, rec in pool.items():
        cand = cands.get(i) or {}
        cs = cand.get("cands") or cand.get("family_decoded") or []
        top = cs[0] if cs else ""
        qrec = improve.get(i) or {}
        q = dict(qrec.get("propose") or {})
        if rec_has_error(qrec) or rec_has_error(q):
            q["error"] = q.get("error") or qrec.get("error") or True
        prepared.append({
            "id": i,
            "tablet": rec.get("tablet"),
            "atf": rec.get("atf") or qrec.get("atf") or cand.get("atf") or "",
            "english": (q.get("english") or "").strip(),
            "genre": rec.get("genre") or "",
            "period": rec.get("period") or "",
            "bucket": genre_bucket(rec.get("genre")),
            "line_no": rec.get("line_no"),
            "qwen": q,
            "top": top,
            "cands": cs,
            "verdict": (judges.get(i) or {}).get("verdict"),
            "in_arm_s": i in arm_s,
        })
    print(f"prepared {len(prepared)} pool rows", flush=True)

    by_mode = {}
    for mode in modes:
        rows = []
        n_improve_ok = 0
        n_improve = 0
        improve_fail = collections.Counter()
        for j, p in enumerate(prepared, 1):
            ok, reasons, filt = cheap_keep_v3(
                p["atf"], p["qwen"], p["top"], p["cands"],
                tablet=p["tablet"], line_no=p["line_no"],
                genre=p["genre"], period=p["period"], paraphrase=mode,
            )
            keep = bool(ok) and p["verdict"] in {"better", "equivalent"}
            fails = (filt or {}).get("fails") or []
            extra = ((filt or {}).get("info") or {}).get("v3_extra") or []
            rec = {
                **{k: p[k] for k in ("id", "tablet", "atf", "english", "genre",
                                     "period", "bucket", "verdict", "in_arm_s")},
                "keep": keep,
                "reasons": reasons,
                "fails": fails,
                "v3_extra": extra,
                "flags": (filt or {}).get("flags") or {},
                "filter_ok": bool(filt.get("ok")) if filt is not None else False,
            }
            rows.append(rec)
            # qwen_improve pool: every improve record with English, filter only
            if p["english"] and not p["qwen"].get("error"):
                n_improve += 1
                if filt is not None and filt.get("ok"):
                    n_improve_ok += 1
                else:
                    for t in fail_tags(fails):
                        improve_fail[t] += 1
            if j % 1000 == 0:
                print(f"  {mode}: {j}/{len(prepared)}", flush=True)

        kept = [r for r in rows if r["keep"]]
        newly_rejected = [r for r in rows if r["in_arm_s"] and not r["keep"]]
        still_kept = [r for r in rows if r["keep"] and r["in_arm_s"]]
        newly_kept = [r for r in rows if r["keep"] and not r["in_arm_s"]]
        of_s_filter_ok = sum(1 for r in rows if r["in_arm_s"] and r["filter_ok"])

        genre_s = collections.Counter(r["bucket"] for r in rows if r["in_arm_s"])
        genre_k = collections.Counter(r["bucket"] for r in kept)
        period_s = collections.Counter(r["period"] or "unknown" for r in rows if r["in_arm_s"])
        period_k = collections.Counter(r["period"] or "unknown" for r in kept)
        admin_s = sum(1 for r in rows if r["in_arm_s"] and is_admin(r["genre"]))
        admin_k = sum(1 for r in kept if is_admin(r["genre"]))

        by_mode[mode] = {
            "rows": rows,
            "kept": kept,
            "newly_rejected": newly_rejected,
            "still_kept": still_kept,
            "newly_kept": newly_kept,
            "n_kept": len(kept),
            "n_newly_rejected": len(newly_rejected),
            "n_newly_kept": len(newly_kept),
            "of_s_filter_ok": of_s_filter_ok,
            "reason": reason_counter(newly_rejected),
            "genre_s": genre_s, "genre_k": genre_k,
            "period_s": period_s, "period_k": period_k,
            "admin_s": admin_s, "admin_k": admin_k,
            "n_improve": n_improve,
            "n_improve_ok": n_improve_ok,
            "improve_fail": improve_fail,
        }
        print(f"{mode}: kept {len(kept)} newly_rejected {len(newly_rejected)} "
              f"improve_ok {n_improve_ok}/{n_improve}", flush=True)

    # Samples from the post-fix lenient run (copy_through) and strict (gloss)
    rng = random.Random(SEED)
    copy_src = by_mode.get("lenient") or by_mode[modes[0]]
    copy_rejects = [r for r in copy_src["newly_rejected"]
                    if any(str(f).startswith("copy_through:") for f in (r["fails"] or r["v3_extra"]))]
    # also include improve-pool copy_through if we want volume; stick to 1479 newly rejected
    rng.shuffle(copy_rejects)
    copy_sample = copy_rejects[:10]

    strict = by_mode.get("strict") or by_mode[modes[-1]]
    gloss_rejects = [r for r in strict["newly_rejected"]
                     if "gloss_unlicensed" in (r["fails"] or [])
                     and not any(str(f).startswith("copy_through:") for f in (r["fails"] or []))]
    # Prefer gloss-only rejects so the sample is about the new switch
    rng.shuffle(gloss_rejects)
    gloss_sample = gloss_rejects[:10]

    # Spot-check panel in both modes, on ctrl hyps
    panel = parse_panel()
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
        rec = {**p, "atf": g.get("atf"), "ref": g.get("english"),
               "genre": g.get("genre"), "ctrl": g.get("ctrl"), "modes": {}}
        for mode in modes:
            filt = f3.check(g.get("atf") or "", g.get("ctrl") or "",
                            genre=g.get("genre"), period=g.get("period"),
                            tablet=g.get("tablet"), paraphrase=mode)
            rec["modes"][mode] = {
                "ok": filt["ok"],
                "fails": filt["fails"],
                "gloss": filt["flags"]["gloss"],
                "over": filt["flags"]["gloss_over_threshold"],
            }
        panel_rows.append(rec)

    def panel_stats(mode, cat):
        items = [p for p in panel_rows if p["cat"] == cat]
        hard = sum(1 for p in items if not p["modes"][mode]["ok"])
        # "caught" = hard drop (in this mode)
        gloss = sum(1 for p in items if p["modes"][mode]["over"])
        either = sum(1 for p in items if (not p["modes"][mode]["ok"]) or p["modes"][mode]["over"])
        return {"n": len(items), "hard": hard, "gloss": gloss, "either": either, "items": items}

    report = {
        "written": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "n_pool": len(prepared),
        "n_arm_s": 1479,
        "modes": {},
        "copy_through_sample": [
            {"id": r["id"], "genre": r["genre"], "period": r["period"],
             "atf": r["atf"], "english": r["english"], "fails": r["fails"]}
            for r in copy_sample
        ],
        "strict_gloss_sample": [
            {"id": r["id"], "genre": r["genre"], "period": r["period"],
             "atf": r["atf"], "english": r["english"], "fails": r["fails"],
             "gloss": (r.get("flags") or {}).get("gloss")}
            for r in gloss_sample
        ],
        "panel": [
            {
                "id": p["id"], "cat": p["cat"],
                "ctrl": p.get("ctrl"),
                "modes": {m: {k: v[k] for k in ("ok", "fails", "over") if k in v} |
                               {"unlicensed": (v.get("gloss") or {}).get("unlicensed"),
                                "ratio": (v.get("gloss") or {}).get("ratio")}
                          for m, v in p["modes"].items()},
            }
            for p in panel_rows
        ],
    }
    for mode, d in by_mode.items():
        report["modes"][mode] = {
            "n_kept": d["n_kept"],
            "n_newly_rejected": d["n_newly_rejected"],
            "n_newly_kept": d["n_newly_kept"],
            "of_s_filter_ok": d["of_s_filter_ok"],
            "reason": dict(d["reason"]),
            "genre_kept": dict(d["genre_k"]),
            "period_kept": dict(d["period_k"]),
            "admin_s": d["admin_s"], "admin_k": d["admin_k"],
            "n_improve": d["n_improve"],
            "n_improve_ok": d["n_improve_ok"],
            "improve_fail": dict(d["improve_fail"]),
        }

    (X / "filter_v3_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    # --------------- markdown ---------------
    md = []
    md.append("# Filter v3 offline report (v3-r1)")
    md.append("")
    md.append(f"Written {now.strftime('%-I:%M %p')} America/New_York on {now.strftime('%b %-d, %Y')}. "
              "CPU only. Module: `runs/loop-pilot/design-v3/filter_v3.py`. "
              "Tests: `runs/loop-pilot/design-v3/test_filter_v3.py` (47 passing, including tightened "
              "copy-through regressions and paraphrase-mode tests).")
    md.append("")
    md.append("## Paraphrase mode switch")
    md.append("")
    md.append("Filter v3 has `--paraphrase strict|lenient` (`check(..., paraphrase=...)`).")
    md.append("")
    md.append("- **`strict`** (default of `check()`, the chrF-phase default): the gloss FLAG becomes a hard reject when `n_unlicensed >= 2` or `ratio >= 0.40`. Names and ATF-backed numbers stay exempt. Use this while the goal is corpus chrF.")
    md.append("- **`lenient`**: the gloss check stays a FLAG only, so good paraphrases (Etemenniguru, silversmiths/goldsmiths) can be kept. Use this later, when improving quality past what chrF can measure.")
    md.append("")
    md.append("Hard rejects (invented Subtotal/ditto, Ø/¶/§, language-tag leaks, copy-through, omen templates on non-omen lines, common nouns as PNs) apply in both modes. Sexagesimal `0;01` for ATF `0.0.1` and ceremonial-name expansions are not hard fails. chrF is not a keep/drop rule. Glossary: clean ORACC BY-SA via `lemma_support` (ETCSL/eBL excluded).")
    md.append("")
    md.append("Copy-through was tightened so it no longer over-fires on damaged or unmarked names (`Atta-ma-[...]`, `Zikanim`), month names on an `iti`-line (`Apinduʾa`), or ATF that is already English (`Palm tree`, `Stylized tree`). True copy-through (`Gigur innuda`, `-angurum`) and common-noun-as-PN (`Meluletum`) still reject.")
    md.append("")

    md.append("## Keep counts versus the 1,479 arm-S lines")
    md.append("")
    md.append("Replayed the v3-r1 keep rule (disagreement AND confidence high/medium AND word cap ≤ 1.8×+4 AND judge ∈ {better, equivalent}) with filter v3 in each mode.")
    md.append("")
    md.append("| mode | kept | of 1479 | newly rejected from S | newly kept | filter-ok among S |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for mode in modes:
        d = by_mode[mode]
        md.append(
            f"| **{mode}** | {d['n_kept']} | {fmt_pct(d['still_kept'] and d['n_kept'] or d['n_kept'], 1479)} | "
            f"{d['n_newly_rejected']} | {d['n_newly_kept']} | {fmt_pct(d['of_s_filter_ok'], 1479)} |"
        )
    md.append("")

    md.append("## qwen_improve pool (filter only)")
    md.append("")
    md.append("Every improve record with English and no Qwen error, ignoring disagreement / judge / word cap.")
    md.append("")
    md.append("| mode | filter-ok | of improve-ok lines |")
    md.append("|---|---:|---:|")
    for mode in modes:
        d = by_mode[mode]
        md.append(f"| **{mode}** | {d['n_improve_ok']} | {fmt_pct(d['n_improve_ok'], d['n_improve'])} |")
    md.append("")
    for mode in modes:
        d = by_mode[mode]
        md.append(f"### {mode} improve-pool reject tags")
        md.append("")
        md.append("| tag | n |")
        md.append("|---|---:|")
        for k, v in d["improve_fail"].most_common():
            md.append(f"| `{k}` | {v} |")
        md.append("")

    for mode in modes:
        d = by_mode[mode]
        md.append(f"## {mode}: rejects from the 1,479 by reason")
        md.append("")
        md.append("| tag | n |")
        md.append("|---|---:|")
        for k, v in d["reason"].most_common():
            md.append(f"| `{k}` | {v} |")
        md.append("")
        md.append(f"Administrative share of arm S was {fmt_pct(d['admin_s'], 1479)}; "
                  f"of the {mode} keep set it is {fmt_pct(d['admin_k'], d['n_kept'] or 1)}.")
        md.append("")
        md.append(f"### {mode}: genre")
        md.append("")
        md.append(md_rate(d["genre_s"], d["genre_k"], 1479, d["n_kept"] or 1))
        md.append("")
        md.append(f"### {mode}: period")
        md.append("")
        md.append(md_rate(d["period_s"], d["period_k"], 1479, d["n_kept"] or 1))
        md.append("")

    def sample_block(items, title, kind):
        md.append(f"## {title}")
        md.append("")
        if not items:
            md.append("(none)")
            md.append("")
            return
        for i, r in enumerate(items, 1):
            g = (r.get("flags") or {}).get("gloss") or r.get("gloss") or {}
            md.append(f"{i}. `{r['id']}` — {r.get('genre') or '—'} / {r.get('period') or '—'}  ")
            md.append(f"   ATF: `{clip(r['atf'])}`  ")
            md.append(f"   EN: {clip(r['english'])}  ")
            md.append(f"   fails: `{r.get('fails')}`")
            if kind == "gloss" and g:
                md.append(f"   gloss: unlicensed={g.get('unlicensed')} ratio={g.get('ratio')}")
            md.append(f"   judgment: _see FILTER_V3.md after the hand check_")
            md.append("")

    sample_block(copy_sample, "10 random copy_through rejects after the tightening (seed 42, from lenient newly-rejected)", "copy")
    sample_block(gloss_sample, "10 random strict-mode gloss rejects (seed 42, gloss_unlicensed, not also copy_through)", "gloss")

    md.append("## Overlap with the 30-line spot-check panel (ctrl hyps)")
    md.append("")
    md.append("Category (c) = 16 real content errors; (b) = 3 good paraphrases; (a) = 5 formatting.")
    md.append("")
    md.append("| mode | (c) hard-dropped | (c) gloss-over | (c) either | (b) hard-dropped | (b) gloss-over | (a) hard-dropped |")
    md.append("|---|---:|---:|---:|---:|---:|---:|")
    for mode in modes:
        c = panel_stats(mode, "c")
        b = panel_stats(mode, "b")
        a = panel_stats(mode, "a")
        md.append(
            f"| **{mode}** | {fmt_pct(c['hard'], c['n'])} | {fmt_pct(c['gloss'], c['n'])} | "
            f"{fmt_pct(c['either'], c['n'])} | {fmt_pct(b['hard'], b['n'])} | "
            f"{fmt_pct(b['gloss'], b['n'])} | {fmt_pct(a['hard'], a['n'])} |"
        )
    md.append("")

    for mode in modes:
        md.append(f"### Panel detail, {mode}")
        md.append("")
        for p in panel_rows:
            m = p["modes"][mode]
            if p["cat"] not in {"c", "b"} and not (not m["ok"] or m["over"]):
                continue
            if p["cat"] not in {"c", "b"}:
                continue
            mark = []
            if not m["ok"]:
                mark.append("hard:" + ",".join((m["fails"] or [])[:4]))
            if m["over"]:
                mark.append("gloss:" + ",".join((m["gloss"] or {}).get("unlicensed") or [])[:80])
            status = "; ".join(mark) if mark else "kept, not flagged"
            md.append(f"- **{p['id']}** ({p['cat']}): {status}")
        md.append("")

    # flagship
    for pid, label in (("fair:0243", "stewed lamb"), ("fair:1327", "Etemenniguru expansion"),
                       ("fair:0262", "silversmiths / goldsmiths")):
        p = next((x for x in panel_rows if x["id"] == pid), None)
        if not p:
            continue
        md.append(f"**{pid}** ({label}):")
        for mode in modes:
            m = p["modes"][mode]
            md.append(f"- {mode}: ok={m['ok']} fails=`{m['fails']}` "
                      f"unlicensed={m['gloss'].get('unlicensed')} ratio={m['gloss'].get('ratio')}")
        md.append("")

    md.append("## Files")
    md.append("")
    md.append("- `runs/loop-pilot/design-v3/filter_v3.py`")
    md.append("- `runs/loop-pilot/design-v3/test_filter_v3.py`")
    md.append("- `runs/loop-pilot/v3-r1/run_filter_v3.py`")
    md.append("- `runs/loop-pilot/v3-r1/filter_v3_report.json`")
    md.append("")
    md.append("Glossary: `lemma_support.py` / `runs/blindcrack/lexicon/oracc_lines.jsonl.gz` "
              "(ORACC BY-SA; epsd2/literary and eBL excluded). Not ETCSL, not eBL.")
    md.append("")

    (X / "FILTER_V3.md").write_text("\n".join(md))
    print("wrote", X / "FILTER_V3.md")
    # also print samples for the hand check
    print("\n======= COPY_THROUGH SAMPLE =======")
    for i, r in enumerate(copy_sample, 1):
        print(f"{i}. {r['id']} | {r['genre']} | {r['period']}")
        print(f"   ATF: {r['atf']}")
        print(f"   EN:  {r['english']}")
        print(f"   fails: {r['fails']}")
    print("\n======= STRICT GLOSS SAMPLE =======")
    for i, r in enumerate(gloss_sample, 1):
        g = (r.get("flags") or {}).get("gloss") or {}
        print(f"{i}. {r['id']} | {r['genre']} | {r['period']}")
        print(f"   ATF: {r['atf']}")
        print(f"   EN:  {r['english']}")
        print(f"   fails: {r['fails']}")
        print(f"   gloss: {g}")


if __name__ == "__main__":
    main()
