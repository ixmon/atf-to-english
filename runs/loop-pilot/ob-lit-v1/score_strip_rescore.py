#!/usr/bin/env python3
"""Score strip-off vs strip-on official 965-line gate (+ c1438).

Never opens test_site_final. Never scores the confirm split.
Family hyps are tokfix.decode'd. Bootstrap B=1000 seed 2, tablet-clustered.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path("/home/darkstar/cursor/atf-translate-test")
X = R / "runs/loop-pilot/ob-lit-v1/strip-rescore"
sys.path.insert(0, str(R / "evaltools"))
sys.path.insert(0, str(R / "runs/chunk-sweep"))
sys.path.insert(0, str(R / "data/na/tokfix"))
sys.path.insert(0, str(R / "runs/loop-pilot/ob-lit-v1"))
import dedup_eval as DE  # noqa: E402
import tokfix as TF  # noqa: E402
import output_backstop as OB  # noqa: E402

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

ET = ZoneInfo("America/New_York")
B = 1000
BOOT_SEED = 2
# This script compares strip-off vs strip-on against the then-published
# strip-off official ctrl 34.02. After 2026-11-24 the official protocol is
# TOKFIX_STRIP_LANG_TAGS=1 and ctrl 34.32; do not rewrite this experiment's target.
CTRL_OFFICIAL = 34.02
CTRL_LIT = 30.39
CTRL_C1438_DEDUP = 49.53

OFF_FAIR = {
    "ctrl": R / "runs/loop-pilot/v3-r1/preds_ctrl_fair_family.json",
    "A3000": R / "runs/loop-pilot/ob-lit-v1/train/preds_a_step3000_fair_family.json",
    "B1000": R / "runs/loop-pilot/ob-lit-v1/train/preds_b_step1000_fair_family.json",
    "B5000": R / "runs/loop-pilot/ob-lit-v1/train/preds_b_step5000_fair_family.json",
}
OFF_C1438 = {
    "ctrl": R / "runs/loop-pilot/v3-r1/preds_ctrl_c1438_family.json",
    "A3000": R / "runs/loop-pilot/ob-lit-v1/train/preds_a_step3000_c1438_family.json",
    "B1000": R / "runs/loop-pilot/ob-lit-v1/train/preds_b_step1000_c1438_family.json",
    "B5000": R / "runs/loop-pilot/ob-lit-v1/train/preds_b_step5000_c1438_family.json",
}
ON_FAIR = {k: X / f"preds_{k}_fair_family_strip_on.json" for k in OFF_FAIR}
ON_C1438 = {k: X / f"preds_{k}_c1438_family_strip_on.json" for k in OFF_C1438}
MODELS = ["ctrl", "A3000", "B1000", "B5000"]


def now():
    return datetime.now(ET).strftime("%Y-%m-%d %I:%M:%S %p") + " America/New_York"


def log(msg):
    line = f"{now()} [strip-score] {msg}"
    print(line, flush=True)
    (X / "score.log").open("a").write(line + "\n")


def load_gate():
    pairs = json.load(open(R / "runs/fair-eval-v1/pairs.json"))["pairs"]
    fs = json.load(open(R / "runs/loop-pilot/design-v3/fair_split.json"))
    s = fs["splits"][fs.get("recommended") or "60_40"]
    gate_ids, confirm_ids = set(s["gate_ids"]), set(s["confirm_ids"])
    assert not (gate_ids & confirm_ids)
    gate = [p for p in pairs if p["id"] in gate_ids]
    assert len(gate) == 965, len(gate)
    return gate


def load_hyps(path: Path) -> dict:
    rows = json.load(open(path))
    return {r["id"]: r["hyp"] for r in rows}


def decoded_map(pairs, raw):
    H = {}
    for i, p in enumerate(pairs):
        if p["id"] in raw:
            H[i] = TF.decode(raw[p["id"]])
    return H


def slice_idx(pairs):
    g = defaultdict(list)
    for i, p in enumerate(pairs):
        g["all"].append(i)
        src = (p.get("source") or "").lower()
        g[src].append(i)
        if src != "ebl":
            g["no_ebl"].append(i)
        for s in p.get("slices") or []:
            g[s].append(i)
    return g


def boot(HA, HB, idx, val, tablets):
    return DE.paired_bootstrap(
        HA, HB, idx, val, B=B, seed=BOOT_SEED,
        cluster=[tablets[i] for i in idx if i in HA and i in HB],
    )


def leak_counts(pairs, H):
    """Pattern leaks on decoded hyps (gate). Also run the backstop."""
    rows = []
    for i, p in enumerate(pairs):
        if i not in H:
            continue
        rows.append({"id": p["id"], "tablet": p.get("tablet"), "atf": p["atf"], "hyp": H[i]})
    # raw pattern counts (including genuine totals if they say Subtotal)
    raw = {"subtotal": 0, "surplus": 0, "substitute": 0, "pct_su": 0, "sum_akk": 0, "es_priest": 0}
    import re
    pats = {
        "subtotal": re.compile(r"(?i)\bsub[\s\-]*totals?:"),
        "surplus": re.compile(r"(?i)\bsurplus\s*:"),
        "substitute": re.compile(r"(?i)\bsubstitute\s*:"),
        "pct_su": re.compile(r"(?i)%\s*s[uúùû](?:x)?\b"),
        "sum_akk": re.compile(r"\(\s*(?:Sum|Akk)\s*\)"),
        "es_priest": re.compile(r"(?i)\bes\s+priest\b"),
    }
    any_n = 0
    for r in rows:
        hit = False
        for k, pat in pats.items():
            if pat.search(r["hyp"]):
                raw[k] += 1
                hit = True
        if hit:
            any_n += 1
    raw["any"] = any_n
    bs = OB.scan(rows)
    flagged = bs.pop("flagged_rows")
    return {"raw": raw, "backstop": {k: bs[k] for k in bs}, "n_flagged_examples": len(flagged),
            "flagged_examples": flagged[:12]}


def fmt_ci(g):
    if not g:
        return "—"
    d = g.get("delta")
    ci = g.get("ci95") or [None, None]
    if d is None or ci[0] is None:
        return "—"
    return f"{d:+.2f} [{ci[0]}, {ci[1]}]"


def score_fair(pairs, models_H, H_ctrl_off):
    val = [{"english": p["english"]} for p in pairs]
    tablets = [p.get("tablet") or "" for p in pairs]
    idx = list(range(len(pairs)))
    groups = slice_idx(pairs)
    want = ["all", "ebl", "ob_literary", "ur3"]
    out = {}
    for name, H in models_H.items():
        rec = {"n": sum(1 for i in idx if i in H)}
        rec["official_chrf"] = DE.score_hyps(H, idx, val)["chrf"]
        rec["vs_ctrl_off"] = boot(H, H_ctrl_off, idx, val, tablets)
        rec["beats_ctrl_positive_ci"] = bool(
            rec["vs_ctrl_off"]
            and rec["vs_ctrl_off"].get("ci95")
            and rec["vs_ctrl_off"]["ci95"][0] is not None
            and rec["vs_ctrl_off"]["ci95"][0] > 0
            and (rec["vs_ctrl_off"].get("delta") or 0) > 0
        )
        rec["slices"] = {}
        for gname in want:
            ix = groups[gname]
            rec["slices"][gname] = {
                "n": len(ix),
                "chrf": DE.score_hyps(H, ix, val)["chrf"],
            }
            rec["slices"][gname]["vs_ctrl_off"] = boot(H, H_ctrl_off, ix, val, tablets)
        rec["leaks"] = leak_counts(pairs, H)
        out[name] = rec
    return out


def load_c1438_maps(path: Path, pack_n: int):
    """Map pack index i -> raw hyp. Accepts {i, hyp} or {id, hyp}."""
    rows = json.load(open(path))
    out = {}
    for r in rows:
        if "i" in r:
            i = int(r["i"])
        else:
            i = int(r["id"])
        out[i] = r["hyp"]
    return out


def score_c1438(on_off_raw):
    # Official c1438 indices are into val_site (0..2006), not 0..1437.
    # DE.load_val() is the same index space used by the official hook.
    # It is not test_site_final.
    val = DE.load_val()
    ded = json.load(open(R / "runs/eval-dedup/c1438_dedup.json"))["i"]

    def H_of(raw):
        return {int(i): TF.decode(h) for i, h in raw.items()}

    href = H_of(on_off_raw[("ctrl", "off")])
    out = {}
    for (name, kind), raw in on_off_raw.items():
        H = H_of(raw)
        rec = {"dedup_chrf": DE.score_hyps(H, ded, val)["chrf"], "n_dedup": len(ded)}
        rec["vs_ctrl_off"] = DE.paired_bootstrap(
            H, href, ded, val, B=B, seed=BOOT_SEED,
            cluster=[val[i].get("tablet") or "" for i in ded if i in H and i in href],
        )
        out[f"{name}_{kind}"] = rec
    return out


def write_md(fair, c1438):
    L = []
    A = L.append
    A("# Strip-on official rescore (eval only)")
    A("")
    A(f"Written {now()}.")
    A("")
    A("Eval only: family decode + `tokfix.decode`, language tags stripped at `tokfix.normalize_atf` (`TOKFIX_STRIP_LANG_TAGS=1`). Model prefix `translate Akkadian to English: ` is unchanged. Official 965-line gate only (confirm not scored; `test_site_final` not opened). Bootstrap B=1000 seed 2, tablet-clustered. No promotion, no training, no commit.")
    A("")
    A("Strip-off numbers are the already-saved official predictions, re-scored with the same script so the comparison is exact. `ctrl` strip-off official chrF should match **34.02**.")
    A("")
    A("## Official 965-line gate")
    A("")
    A("| model | strip | official chrF | Δ vs ctrl 34.02 (paired CI) | beats ctrl +CI | literary | eBL | Ur III |")
    A("|---|---|---:|---|---|---:|---:|---:|")
    beats = []
    for name in MODELS:
        for kind in ("off", "on"):
            rec = fair.get(f"{name}_{kind}")
            if not rec:
                A(f"| {name} | {kind} | — | — | — | — | — | — |")
                continue
            sl = rec["slices"]
            lit = sl["ob_literary"]["chrf"]
            ebl = sl["ebl"]["chrf"]
            ur3 = sl["ur3"]["chrf"]
            flag = "YES" if rec["beats_ctrl_positive_ci"] and name != "ctrl" else ("yes (ctrl+strip vs 34.02)" if rec["beats_ctrl_positive_ci"] else "no")
            if rec["beats_ctrl_positive_ci"] and name != "ctrl":
                beats.append(f"{name} strip-{kind}")
            A(f"| {name} | {kind} | {rec['official_chrf']} | {fmt_ci(rec['vs_ctrl_off'])} | {flag} | {lit} | {ebl} | {ur3} |")
    A("")
    A(f"Literary ctrl strip-off official slice target is **{CTRL_LIT}**. Ur III and eBL have no fixed published headline besides the numbers in this table.")
    A("")
    A("## Leak counts on the 965-line gate (decoded hyps)")
    A("")
    A("`raw` counts every pattern hit, including a genuine šunigin line that correctly says Subtotal. `backstop` counts only residual *false* leaks (no šunigin / szu+nigin2 cue in the ATF).")
    A("")
    A("| model | strip | Subtotal | surplus | substitute | %sú | (Sum)/(Akk) | es priest | any raw | backstop flagged |")
    A("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name in MODELS:
        for kind in ("off", "on"):
            rec = fair.get(f"{name}_{kind}")
            if not rec:
                continue
            raw = rec["leaks"]["raw"]
            bs = rec["leaks"]["backstop"]
            A(f"| {name} | {kind} | {raw['subtotal']} | {raw['surplus']} | {raw['substitute']} | {raw['pct_su']} | {raw['sum_akk']} | {raw['es_priest']} | {raw['any']} | {bs['flagged']} |")
    A("")
    A("## c1438 dedup")
    A("")
    A(f"Ctrl strip-off official dedup headline is **{CTRL_C1438_DEDUP}**.")
    A("")
    A("| model | strip | c1438 dedup chrF | Δ vs ctrl strip-off (paired CI) |")
    A("|---|---|---:|---|")
    for name in MODELS:
        for kind in ("off", "on"):
            rec = c1438.get(f"{name}_{kind}")
            if not rec:
                continue
            A(f"| {name} | {kind} | {rec['dedup_chrf']} | {fmt_ci(rec['vs_ctrl_off'])} |")
    A("")
    if beats:
        A("## Pass against ctrl 34.02")
        A("")
        A("The following arm(s) beat official ctrl 34.02 with a positive paired CI: **" + ", ".join(beats) + "**. Confirm was **not** scored, per the brief. No promotion.")
        A("")
    else:
        A("No arm beat official ctrl 34.02 with a positive paired CI. Confirm was not scored. No promotion.")
        A("")
    A("## Recommendation")
    A("")
    A("(filled by the driver after scoring, or see the accompanying report)")
    A("")
    path = R / "runs/loop-pilot/ob-lit-v1/STRIP_RESCORE.md"
    path.write_text("\n".join(L) + "\n")
    return path, beats


def main():
    X.mkdir(parents=True, exist_ok=True)
    pairs = load_gate()
    log(f"gate n={len(pairs)}")

    # strip-off ctrl is the official reference
    raw_ctrl_off = load_hyps(OFF_FAIR["ctrl"])
    H_ctrl_off = decoded_map(pairs, raw_ctrl_off)
    assert len(H_ctrl_off) == 965, len(H_ctrl_off)

    models_H = {}
    fair = {}
    for name in MODELS:
        for kind, catalog in (("off", OFF_FAIR), ("on", ON_FAIR)):
            path = catalog[name]
            if not path.exists() or path.stat().st_size < 100:
                log(f"missing {kind} fair preds for {name}: {path}")
                continue
            raw = load_hyps(path)
            H = decoded_map(pairs, raw)
            log(f"loaded {name} strip-{kind} fair n={len(H)}")
            models_H[f"{name}_{kind}"] = H

    fair = score_fair(pairs, models_H, H_ctrl_off)
    for name, rec in fair.items():
        log(f"{name} official={rec['official_chrf']} vs_ctrl={fmt_ci(rec['vs_ctrl_off'])} "
            f"beats={rec['beats_ctrl_positive_ci']} leaks_raw={rec['leaks']['raw']} "
            f"backstop={rec['leaks']['backstop']['flagged']}")

    # c1438
    c_raw = {}
    for name in MODELS:
        for kind, catalog in (("off", OFF_C1438), ("on", ON_C1438)):
            path = catalog[name]
            if not path.exists() or path.stat().st_size < 100:
                continue
            pack_n = 1438
            c_raw[(name, kind)] = load_c1438_maps(path, pack_n)
            log(f"loaded {name} strip-{kind} c1438 n={len(c_raw[(name, kind)])}")
    c1438 = score_c1438(c_raw) if ("ctrl", "off") in c_raw else {}

    path, beats = write_md(fair, c1438)
    payload = {
        "written": now(),
        "fair": {k: {kk: vv for kk, vv in rec.items() if kk != "leaks"} | {
            "leaks": {"raw": rec["leaks"]["raw"], "backstop": rec["leaks"]["backstop"],
                      "examples": rec["leaks"]["flagged_examples"]}
        } for k, rec in fair.items()},
        "c1438": c1438,
        "beats_ctrl_positive_ci": beats,
    }
    json.dump(payload, open(X / "strip_rescore_scores.json", "w"), indent=2, default=str)
    log(f"wrote {path}")
    print("BEATS", beats)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
