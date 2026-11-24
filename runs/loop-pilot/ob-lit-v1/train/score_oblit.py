#!/usr/bin/env python3
"""ob-lit-v1 official scoring (adapted from v3-r2). Family decode + tokfix
+ tablet-clustered paired bootstrap (B=1000, seed 2) vs v4e and vs ctrl.

Confirm is scored only if a checkpoint beats official ctrl on the 965-line
gate with a positive paired CI (CI lower bound > 0). Official ctrl is
34.32 with TOKFIX_STRIP_LANG_TAGS=1 (adopted 2026-11-24; previous
published strip-off baseline was 34.02). Never opens
test_site_final. No promotion.

Modes:
  --mode gate-ckpts --arm {a,b}
      Score every checkpoint-* (and best-chrf if its step is new) on the
      official 965-line fair gate. Confirm is scored once per arm, only if
      a checkpoint PASSes, on the passing ckpt with the highest official
      corpus chrF. Never opens test_site_final.
  --mode finalize
      Write RESULTS.md and PIPELINE_DONE from the per-arm gate/confirm files.

CUDA_VISIBLE_DEVICES is forced to 0 after any import that may blank it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

R = Path("/home/darkstar/cursor/atf-translate-test")
X = Path(os.environ.get("LOOP_X", str(R / "runs/loop-pilot/ob-lit-v1/train")))
V3R1 = R / "runs/loop-pilot/v3-r1"
PY = str(R / ".venv/bin/python")
sys.path.insert(0, str(R / "evaltools"))
sys.path.insert(0, str(R / "runs/chunk-sweep"))
sys.path.insert(0, str(R / "data/na/tokfix"))
import dedup_eval as DE  # noqa: E402
import score_chunks as SC  # noqa: E402
import tokfix as TF  # noqa: E402
AE = SC.AE
# dedup_eval blanks CUDA_VISIBLE_DEVICES as a CPU guard. Empty string counts
# as set, so setdefault is not enough. Restore explicitly.
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

ET = ZoneInfo("America/New_York")
B = 1000
BOOT_SEED = 2
PARENT = "v4e"
START = "ctrl"
ARMS = ["a", "b"]
ARM_LABEL = {"a": "A", "b": "B", "v4e": "v4e", "ctrl": "ctrl (start)"}
MODEL_DIR = {
    "a": R / "models/clean-bysa-loop-ob-lit-v1-a",
    "b": R / "models/clean-bysa-loop-ob-lit-v1-b",
}
CTRL_OFFICIAL = 34.32  # strip-on official (was 34.02 strip-off)
CTRL_LIT = 30.89  # strip-on literary slice (was 30.39)
CTRL_C1438_DEDUP = 49.53
GATED_SLICES = ["all", "cdli", "oracc", "ebl", "no_ebl", "ur3", "neo_assyrian",
                "ob_literary", "names", "royal"]
WATCH_SLICES = ["lexical"]
# Parent / starting-ctrl family preds from v3-r1 (same models, reuse).
CTRL_FAIR = V3R1 / "preds_ctrl_fair_family.json"
CTRL_C1438 = V3R1 / "preds_ctrl_c1438_family.json"


def now():
    return datetime.now(ET).strftime("%Y-%m-%d %I:%M:%S %p") + " America/New_York"


def log(msg):
    line = f"{now()} [score] {msg}"
    print(line, flush=True)
    open(X / "progress.log", "a").write(line + "\n")


def run_infer(model_dir: Path, out: Path, pairs=None, eval_pack=None, mem_frac=0.17):
    if out.exists() and out.stat().st_size > 100:
        log(f"reuse {out}")
        return
    cmd = [PY, str(Path(__file__).resolve().parent / "infer_family_v3.py"), "--model", str(model_dir),
           "--out", str(out), "--mem-frac", str(mem_frac)]
    if eval_pack:
        cmd += ["--eval-pack", str(eval_pack), "--pairs", str(eval_pack)]
    else:
        cmd += ["--pairs", str(pairs)]
    log("RUN " + " ".join(cmd))
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"
    r = subprocess.run(cmd, cwd=str(R), env=env)
    if r.returncode != 0:
        raise SystemExit(f"infer failed rc={r.returncode} out={out}")


def load_fair_pairs():
    return json.load(open(R / "runs/fair-eval-v1/pairs.json"))["pairs"]


def load_split():
    fs = json.load(open(R / "runs/loop-pilot/design-v3/fair_split.json"))
    s = fs["splits"][fs.get("recommended") or "60_40"]
    return set(s["gate_ids"]), set(s["confirm_ids"])


def parent_fair_hyps_raw():
    nf = load_fair_pairs()
    wf = json.load(open(R / "runs/fair-eval-v1/pairs_with_formulae.json"))["pairs"]
    key = {(p["tablet"], p["atf"]): p["id"] for p in wf}
    pred = {p["id"]: p["hyp"] for p in json.load(open(R / "runs/fair-eval-v1/preds_v4e_beam4_family.json"))}
    out = {}
    miss = 0
    for p in nf:
        wid = key.get((p["tablet"], p["atf"]))
        if wid and wid in pred:
            out[p["id"]] = pred[wid]
        else:
            miss += 1
    if miss:
        log(f"WARN parent fair hyp miss {miss}/{len(nf)}")
    return out


def preds_to_id_map(path):
    rows = json.load(open(path))
    return {r["id"]: r["hyp"] for r in rows}


def decoded_by_index(pairs, id_to_raw):
    H = {}
    for i, p in enumerate(pairs):
        raw = id_to_raw.get(p["id"])
        if raw is not None:
            H[i] = TF.decode(raw)
    return H


def slice_groups(pairs, idx):
    g = defaultdict(list)
    for i in idx:
        p = pairs[i]
        g["all"].append(i)
        src = (p.get("source") or "").lower()
        if src == "cdli":
            g["cdli"].append(i)
        if src == "oracc":
            g["oracc"].append(i)
        if src != "ebl":
            g["no_ebl"].append(i)
        if src == "ebl":
            g["ebl"].append(i)
        lic = (p.get("license") or "").lower()
        if "nc" in lic or "noncommercial" in lic or "non-commercial" in lic:
            g["nc"].append(i)
        for s in p.get("slices") or []:
            g[s].append(i)
    return g


def boot(HA, HB, idx, val, tablets):
    return DE.paired_bootstrap(HA, HB, idx, val, B=B, seed=BOOT_SEED,
                               cluster=[tablets[i] for i in idx if i in HA and i in HB])


def score_set(tag, pairs, idx, models, tablets):
    val = [{"english": p["english"]} for p in pairs]
    groups = slice_groups(pairs, idx)
    out = {"n": len(idx), "n_tablets": len({tablets[i] for i in idx}), "models": {}, "slices": {}, "gaps": {}}
    for lab, H in models.items():
        out["models"][lab] = DE.score_hyps(H, idx, val)
    labs = list(models)

    def gap(a, b, ix, name):
        if a not in models or b not in models:
            return
        common = [i for i in ix if i in models[a] and i in models[b]]
        if len(common) < 10:
            return
        out["gaps"][name] = boot(models[a], models[b], common, val, tablets)

    if PARENT in models:
        for lab in labs:
            if lab == PARENT:
                continue
            gap(lab, PARENT, idx, f"{lab}_vs_{PARENT}")
    if START in models:
        for lab in labs:
            if lab in {PARENT, START}:
                continue
            gap(lab, START, idx, f"{lab}_vs_{START}")
    for gname, ix in groups.items():
        rec = {"n": len(ix)}
        for lab, H in models.items():
            rec[lab] = DE.score_hyps(H, ix, val)["chrf"]
        if PARENT in models:
            for lab in labs:
                if lab == PARENT or len(ix) < 40:
                    continue
                common = [i for i in ix if i in models[lab] and i in models[PARENT]]
                if len(common) < 40:
                    continue
                rec[f"{lab}_vs_{PARENT}"] = boot(models[lab], models[PARENT], common, val, tablets)
        if START in models:
            for lab in labs:
                if lab in {PARENT, START} or len(ix) < 40:
                    continue
                common = [i for i in ix if i in models[lab] and i in models[START]]
                if len(common) < 40:
                    continue
                rec[f"{lab}_vs_{START}"] = boot(models[lab], models[START], common, val, tablets)
        out["slices"][gname] = rec
    return out


def score_1438(arm, H_arm, H_parent, H_ctrl, pack, val):
    ded = json.load(open(R / "runs/eval-dedup/c1438_dedup.json"))["i"]
    strict = json.load(open(R / "runs/eval-dedup/c1438_strict.json"))["i"]
    ur3 = pack["ur3_251_indices"]
    name_by_i = {x["i"]: x for x in pack["name_405"]}
    H = {PARENT: H_parent, START: H_ctrl, arm: H_arm}
    out = {"dedup": {}, "strict": {}, "ur3_251": {}, "name_exact": {}, "gaps": {}}
    for lab, Hh in H.items():
        out["dedup"][lab] = DE.score_hyps(Hh, ded, val)
        out["strict"][lab] = DE.score_hyps(Hh, strict, val)
        out["ur3_251"][lab] = DE.score_hyps(Hh, ur3, val)
        hits = tot = 0
        for i, rec in name_by_i.items():
            if i not in Hh:
                continue
            for pn in rec.get("pns") or []:
                en = pn.get("en") or ""
                if en:
                    tot += 1
                    hits += int(AE.name_exact_in_hyp(en, Hh[i]))
        out["name_exact"][lab] = {"hits": hits, "n": tot, "pct": round(100 * hits / tot, 1) if tot else None}
    for cut, idx in (("dedup", ded), ("strict", strict)):
        out["gaps"][cut] = {}
        for other in (arm, START):
            out["gaps"][cut][other] = DE.paired_bootstrap(
                H[other], H[PARENT], idx, val, B=B, seed=BOOT_SEED,
                cluster=[val[i]["tablet"] for i in idx if i in H[other] and i in H[PARENT]],
            )
        out["gaps"][cut][f"{arm}_vs_{START}"] = DE.paired_bootstrap(
            H[arm], H[START], idx, val, B=B, seed=BOOT_SEED,
            cluster=[val[i]["tablet"] for i in idx if i in H[arm] and i in H[START]],
        )
    return out


def judge_one(arm, gate, c1438):
    """DESIGN_V3 pass/fail/borderline for one arm (decision vs v4e)."""
    rec = {"arm": arm, "pass": False, "borderline": False, "fails": [], "notes": []}
    gap = (gate.get("gaps") or {}).get(f"{arm}_vs_{PARENT}") or {}
    rec["gate_vs_v4e"] = gap
    rec["gate_vs_ctrl"] = (gate.get("gaps") or {}).get(f"{arm}_vs_{START}") or {}
    if not gap:
        rec["fails"].append("missing_gate_gap")
        return rec
    lb, ub = gap["ci95"]
    delta, p = gap["delta"], gap.get("p_le0")
    if lb > 0:
        rec["notes"].append(f"gate CI LB {lb} > 0 (delta {delta})")
    elif delta > 0 and (p is not None and p <= 0.10) and lb <= 0:
        rec["borderline"] = True
        rec["fails"].append(f"borderline: delta {delta} p_le0 {p} CI {gap['ci95']}")
    else:
        rec["fails"].append(f"gate CI LB {lb} <= 0 (delta {delta}, p_le0 {p})")
    for sl in GATED_SLICES:
        if sl == "all":
            continue
        info = (gate.get("slices") or {}).get(sl) or {}
        g = info.get(f"{arm}_vs_{PARENT}")
        if not g or info.get("n", 0) < 100:
            continue
        if g["ci95"][1] < 0:
            rec["fails"].append(f"slice {sl} n={info['n']} CI UB {g['ci95'][1]} < 0 (delta {g['delta']})")
    lex = (gate.get("slices") or {}).get("lexical") or {}
    if lex.get("n", 0) >= 100 and lex.get(f"{arm}_vs_{PARENT}"):
        rec["notes"].append(f"lexical watch: {lex[f'{arm}_vs_{PARENT}']}")
    for cut in ("dedup", "strict"):
        g = ((c1438.get("gaps") or {}).get(cut) or {}).get(arm)
        if not g:
            rec["fails"].append(f"missing c1438_{cut}")
            continue
        rec[f"c1438_{cut}_vs_v4e"] = g
        if g["ci95"][1] < 0:
            rec["fails"].append(f"c1438_{cut} significant regression CI UB {g['ci95'][1]} < 0 (delta {g['delta']})")
    u_arm = ((c1438.get("ur3_251") or {}).get(arm) or {}).get("chrf")
    u_par = ((c1438.get("ur3_251") or {}).get(PARENT) or {}).get("chrf")
    if u_arm is not None and u_par is not None:
        rec["ur3_251"] = {"arm": u_arm, "v4e": u_par, "delta": round(u_arm - u_par, 2)}
        if (u_par - u_arm) > 1.0:
            rec["fails"].append(f"Ur III 251 drop {u_par-u_arm:.2f} > 1.0")
    n_arm = ((c1438.get("name_exact") or {}).get(arm) or {}).get("pct")
    n_par = ((c1438.get("name_exact") or {}).get(PARENT) or {}).get("pct")
    if n_arm is not None and n_par is not None:
        rec["name_exact"] = {"arm": n_arm, "v4e": n_par, "delta": round(n_arm - n_par, 1)}
        if (n_par - n_arm) > 2.0:
            rec["fails"].append(f"name-exact drop {n_par-n_arm:.1f} > 2 points")
    rec["pass_v3r2_style"] = (not rec["fails"]) and (not rec["borderline"])
    # Official confirm trigger: beat official ctrl 34.32 (strip-on) with CI LB > 0.
    gctrl = rec.get("gate_vs_ctrl") or {}
    ci = gctrl.get("ci95") or [None, None]
    chrf = None
    rec["beats_ctrl_positive_ci"] = bool(
        ci[0] is not None and ci[0] > 0 and (gctrl.get("delta") or 0) > 0
    )
    rec["pass"] = bool(rec["beats_ctrl_positive_ci"])
    rec["notes"].append(
        f"confirm trigger vs official ctrl {CTRL_OFFICIAL}: beats_ctrl_positive_ci={rec['pass']} "
        f"delta={gctrl.get('delta')} CI={ci}"
    )
    return rec


def list_ckpts(model_dir: Path, snapshot_dir: Path | None = None):
    """Return (step, path) sorted by step. Prefer checkpoint-N in model_dir; fall back to snapshots."""
    found = {}
    roots = [model_dir]
    if snapshot_dir is not None:
        roots.append(snapshot_dir)
    for root in roots:
        if not root.exists():
            continue
        for pth in root.glob("checkpoint-*"):
            m = re.search(r"checkpoint-(\d+)$", pth.name)
            if not m:
                continue
            step = int(m.group(1))
            if step in found:
                continue
            if (pth / "model.safetensors").exists() or (pth / "config.json").exists():
                found[step] = pth
    best = model_dir / "best-chrf"
    best_step = None
    if (best / "model.safetensors").exists() or (best / "config.json").exists():
        bm = best / "best_metrics.json"
        if bm.exists():
            try:
                best_step = int(json.load(open(bm)).get("step") or 0) or None
            except Exception:
                best_step = None
        if best_step and best_step not in found:
            found[best_step] = best
        elif not found:
            found[best_step or 0] = best
    return sorted(found.items())


def load_fixed_hyps(pairs):
    H_parent = decoded_by_index(pairs, parent_fair_hyps_raw())
    H_ctrl = decoded_by_index(pairs, preds_to_id_map(CTRL_FAIR))
    pack = json.load(open(R / "runs/clean-bysa-v4e/eval_1438.json"))
    val = DE.load_val()
    bare = json.load(open(R / "runs/v4e-beam4/bare_1438_beam4_family.json"))
    Hp = {}
    for row in bare:
        i = int(row["i"])
        Hp[i] = TF.decode(row["hyp"])
    Hc = {}
    for row in json.load(open(CTRL_C1438)):
        i = int(row["i"])
        Hc[i] = TF.decode(row["hyp"])
    return H_parent, H_ctrl, pack, val, Hp, Hc



def count_hallucination_tics(pairs, id_to_raw):
    """Count Subtotal / late royal names / ATF copy-through in decoded hyps."""
    late = re.compile(r"\b(Cyrus|Seleucus|Darius|Xerxes|Cambyses|Heliopolis)\b", re.I)
    sub = re.compile(r"\bsub[\s\-]*totals?:", re.I)
    counts = {"n": 0, "subtotal": 0, "cyrus": 0, "seleucus": 0, "darius": 0,
              "xerxes": 0, "cambyses": 0, "heliopolis": 0, "copy_through": 0,
              "examples": []}
    for p in pairs:
        raw = id_to_raw.get(p["id"])
        if raw is None:
            continue
        hyp = TF.decode(raw)
        counts["n"] += 1
        hit = []
        if sub.search(hyp):
            counts["subtotal"] += 1
            hit.append("subtotal")
        for name, key in (("Cyrus", "cyrus"), ("Seleucus", "seleucus"),
                          ("Darius", "darius"), ("Xerxes", "xerxes"),
                          ("Cambyses", "cambyses"), ("Heliopolis", "heliopolis")):
            if re.search(r"\b" + name + r"\b", hyp, re.I):
                counts[key] += 1
                hit.append(key)
        # crude copy-through: two or more hyphenated ATF tokens from the source
        atf_toks = set(re.findall(r"[A-Za-z][A-Za-z0-9]*-[A-Za-z0-9\-]+", p.get("atf") or ""))
        hyp_toks = set(re.findall(r"[A-Za-z][A-Za-z0-9]*-[A-Za-z0-9\-]+", hyp or ""))
        overlap = {t for t in (atf_toks & hyp_toks) if len(t) >= 5}
        if len(overlap) >= 2:
            counts["copy_through"] += 1
            hit.append("copy_through")
        if hit and len(counts["examples"]) < 8:
            counts["examples"].append({"id": p.get("id"), "tablet": p.get("tablet"),
                                       "hits": hit, "hyp": hyp[:200]})
    return counts


def official_chrf(gate, arm):
    m = (gate.get("models") or {}).get(arm) or {}
    return m.get("chrf")


def gate_one_ckpt(arm, step, ckpt, pairs, gate_idx, tablets,
                  H_parent, H_ctrl, pack, val, Hp, Hc):
    tag = f"{arm}_step{step}"
    fair_out = X / f"preds_{arm}_step{step}_fair_family.json"
    c1438_out = X / f"preds_{arm}_step{step}_c1438_family.json"
    run_infer(ckpt, fair_out, pairs=R / "runs/fair-eval-v1/pairs.json")
    H_arm_fair = decoded_by_index(pairs, preds_to_id_map(fair_out))
    log(f"fair hyps {tag}: {len(H_arm_fair)}/{len(pairs)} from {ckpt}")
    models = {PARENT: H_parent, START: H_ctrl, arm: H_arm_fair}
    gate = score_set("gate", pairs, gate_idx, models, tablets)
    gate["arm"] = arm
    gate["step"] = step
    gate["ckpt"] = str(ckpt)
    json.dump(gate, open(X / f"scores_gate_{tag}.json", "w"), indent=2)

    run_infer(ckpt, c1438_out, eval_pack=R / "runs/clean-bysa-v4e/eval_1438.json")
    Ha = {}
    for row in json.load(open(c1438_out)):
        i = int(row["i"])
        Ha[i] = TF.decode(row["hyp"])
    log(f"c1438 hyps {tag}: {len(Ha)}")
    c1438 = score_1438(arm, Ha, Hp, Hc, pack, val)
    c1438["arm"] = arm
    c1438["step"] = step
    c1438["ckpt"] = str(ckpt)
    json.dump(c1438, open(X / f"scores_c1438_{tag}.json", "w"), indent=2)

    verd = judge_one(arm, gate, c1438)
    verd["step"] = step
    verd["ckpt"] = str(ckpt)
    verd["official_chrf"] = official_chrf(gate, arm)
    try:
        raw_map = preds_to_id_map(fair_out)
        verd["hallucination_tics"] = count_hallucination_tics(pairs, raw_map)
    except Exception as e:
        verd["hallucination_tics"] = {"error": str(e)[:200]}
    json.dump(verd, open(X / f"verdict_{tag}.json", "w"), indent=2)
    status = "PASS" if verd["pass"] else ("BORDERLINE" if verd["borderline"] else "FAIL")
    log(f"verdict {tag}: {status} official_chrf={verd['official_chrf']} vs v4e {verd.get('gate_vs_v4e')}")

    return verd, H_arm_fair


def mode_gate_ckpts(arm):
    assert arm in ARMS, arm
    pairs = load_fair_pairs()
    gate_ids, confirm_ids = load_split()
    gate_idx = [i for i, p in enumerate(pairs) if p["id"] in gate_ids]
    confirm_idx = [i for i, p in enumerate(pairs) if p["id"] in confirm_ids]
    assert len(gate_idx) == 965 and len(confirm_idx) == 635, (len(gate_idx), len(confirm_idx))
    tablets = [p.get("tablet") for p in pairs]
    log(f"gate-ckpts arm={arm} pairs={len(pairs)} gate={len(gate_idx)} confirm={len(confirm_idx)} "
        f"CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES')!r}")
    if not CTRL_FAIR.exists() or not CTRL_C1438.exists():
        raise SystemExit(f"missing starting-ctrl preds: {CTRL_FAIR} or {CTRL_C1438}")
    H_parent, H_ctrl, pack, val, Hp, Hc = load_fixed_hyps(pairs)
    md = MODEL_DIR[arm]
    ckpts = list_ckpts(md, snapshot_dir=X / "ckpts" / arm)
    if not ckpts:
        raise SystemExit(f"no checkpoints in {md}")
    log(f"checkpoints for {arm}: " + ", ".join(f"{s}:{p}" for s, p in ckpts))

    summary = {"arm": arm, "ckpts": [], "confirm_step": None, "best_official": None}
    best_official = None
    official_hist = []
    early_note = None
    bad_streak = 0
    best_so_far = None
    hyps_by_step = {}
    for step, ckpt in ckpts:
        verd, H_arm_fair = gate_one_ckpt(
            arm, step, ckpt, pairs, gate_idx, tablets,
            H_parent, H_ctrl, pack, val, Hp, Hc,
        )
        hyps_by_step[step] = H_arm_fair
        ch = verd.get("official_chrf")
        official_hist.append({"step": step, "chrf": ch, "pass": verd["pass"],
                              "borderline": verd["borderline"], "fails": verd["fails"]})
        if ch is not None and (best_official is None or ch > best_official[0]):
            best_official = (ch, step, str(ckpt), verd["pass"])
        gained = ch is not None and (best_so_far is None or (ch - best_so_far) >= 0.2)
        if ch is not None and (best_so_far is None or ch > best_so_far):
            best_so_far = ch
        if gained:
            bad_streak = 0
        else:
            bad_streak += 1
            if bad_streak >= 3 and early_note is None:
                early_note = f"three consecutive official evals failed to gain >= 0.2 after step {step}"
                log("official early-stop note: " + early_note + " (scoring remaining saved ckpts)")
        summary["ckpts"].append({
            "step": step, "ckpt": str(ckpt), "official_chrf": ch,
            "pass": verd["pass"], "borderline": verd["borderline"],
            "fails": verd["fails"], "notes": verd["notes"],
            "vs_v4e": verd.get("gate_vs_v4e"), "vs_ctrl": verd.get("gate_vs_ctrl"),
        })
    # Confirm once, only on a PASS, on the passing checkpoint with the highest official 965 chrF.
    passing = [c for c in summary["ckpts"] if c.get("pass") and c.get("official_chrf") is not None]
    if passing and not (X / f"scores_confirm_{arm}.json").exists():
        best_pass = max(passing, key=lambda c: (c["official_chrf"], c["step"]))
        step = best_pass["step"]
        H_arm_fair = hyps_by_step[step]
        conf_models = {PARENT: H_parent, START: H_ctrl, arm: H_arm_fair}
        confirm = score_set("confirm", pairs, confirm_idx, conf_models, tablets)
        confirm["arm"] = arm
        confirm["step"] = step
        confirm["ckpt"] = best_pass["ckpt"]
        json.dump(confirm, open(X / f"scores_confirm_{arm}.json", "w"), indent=2)
        (X / f"confirm_done_{arm}.flag").write_text(
            f"{now()}\narm={arm} step={step} ckpt={best_pass['ckpt']}\n"
        )
        summary["confirm_step"] = step
        log(f"wrote scores_confirm_{arm}.json for best passing {arm}_step{step} chrF={best_pass['official_chrf']}")
    elif not passing:
        log(f"no checkpoint passed the official gate for arm {arm}; confirm not scored")
    else:
        log(f"confirm already present for arm {arm}; not re-scored")
        try:
            summary["confirm_step"] = json.load(open(X / f"scores_confirm_{arm}.json")).get("step")
        except Exception:
            pass
    summary["best_official"] = (
        {"chrf": best_official[0], "step": best_official[1], "ckpt": best_official[2],
         "pass": best_official[3]}
        if best_official else None
    )
    summary["official_early_stop_note"] = early_note
    summary["confirm_scored"] = (X / f"scores_confirm_{arm}.json").exists()
    json.dump(summary, open(X / f"gate_summary_{arm}.json", "w"), indent=2)
    (X / f"gate_done_{arm}.flag").write_text(f"{now()}\narm={arm}\n")
    log(f"gate-ckpts done for arm {arm}")
    return 0


def _fmt_ci(g):
    if not g:
        return "—"
    ci = g.get("ci95") or [None, None]
    return f"{g.get('delta')} [{ci[0]}, {ci[1]}]"


def write_results():
    lines = []
    A = lines.append
    A("# Loop ob-lit-v1 results (v4e parent, two arms)")
    A("")
    A(f"Written {now()}.")
    A("")
    A("Two-arm continuation from `models/clean-bysa-v4e/best-chrf` (v4e). "
      "Arm A: v4e-scrubbed replay + 262 gold N-to-N lines (20× upsample). "
      "Arm B: same gold + 3,466 kept N-to-N literary pseudo-label spans (10% literary draws). "
      "lr 1e-5, 5k steps, Ur III floor preserved at the v4e 160k-prefix share (10.34%).")
    A("Referee: `runs/fair-eval-v1/pairs.json`, 60/40 split seed 20261121. Official 965-line gate "
      "with tablet-clustered bootstrap B=1000 seed 2, scored at every 1,000-step checkpoint, vs v4e and vs starting ctrl. "
      "Confirm scored only if a checkpoint beats official ctrl (34.32 strip-on) with a positive paired CI. "
      "`test_site_final` was not opened or scored. No promotion, publish, or deploy.")
    A("")
    for arm in ARMS:
        path = X / f"gate_summary_{arm}.json"
        A(f"## Arm {ARM_LABEL[arm]}")
        A("")
        if not path.exists():
            A(f"No gate summary yet (`{path.name}` missing).")
            A("")
            continue
        s = json.load(open(path))
        A("| step | official 965 chrF | Δ vs v4e | Δ vs ctrl 34.02 | beats ctrl +CI |")
        A("|---:|---:|---|---|---|")
        for c in s.get("ckpts") or []:
            v4 = _fmt_ci(c.get("vs_v4e"))
            vc = _fmt_ci(c.get("vs_ctrl"))
            st = "YES" if c.get("pass") else "no"
            A(f"| {c.get('step')} | {c.get('official_chrf')} | {v4} | {vc} | {st} |")
        A("")
        # Per-step slices from scores_gate / scores_c1438 / verdict
        A("| step | literary vs 30.39 | Ur III | NA | royal | CDLI | eBL | c1438 dedup vs 49.53 | Subtotal | Cyrus | copy-through |")
        A("|---:|---|---|---|---|---|---|---|---:|---:|---:|")
        for c in s.get("ckpts") or []:
            step = c.get("step")
            gate = {}
            c1438 = {}
            verd = {}
            gp = X / f"scores_gate_{arm}_step{step}.json"
            cp = X / f"scores_c1438_{arm}_step{step}.json"
            vp = X / f"verdict_{arm}_step{step}.json"
            if gp.exists():
                gate = json.load(open(gp))
            if cp.exists():
                c1438 = json.load(open(cp))
            if vp.exists():
                verd = json.load(open(vp))
            sl = gate.get("slices") or {}
            def slv(name, ctrl=None):
                rec = sl.get(name) or {}
                ch = rec.get(arm)
                if ch is None:
                    return "—"
                extra = ""
                if ctrl is not None:
                    extra = f" ({ch-ctrl:+.2f})"
                return f"{ch}{extra}"
            lit = slv("ob_literary", CTRL_LIT)
            ur3 = slv("ur3")
            na = slv("neo_assyrian")
            royal = slv("royal")
            cdli = slv("cdli")
            ebl = slv("ebl")
            ded = ((c1438.get("dedup") or {}).get(arm) or {}).get("chrf")
            ded_s = "—" if ded is None else f"{ded} ({ded-CTRL_C1438_DEDUP:+.2f})"
            tics = verd.get("hallucination_tics") or {}
            A(f"| {step} | {lit} | {ur3} | {na} | {royal} | {cdli} | {ebl} | {ded_s} | "
              f"{tics.get('subtotal', '—')} | {tics.get('cyrus', '—')} | {tics.get('copy_through', '—')} |")
        A("")
        bo = s.get("best_official") or {}
        if bo:
            A(f"Best official 965 chrF: **{bo.get('chrf')}** at step {bo.get('step')} "
              f"({ 'PASS' if bo.get('pass') else 'not a pass' }).")
        if s.get("official_early_stop_note"):
            A(f"Official early-stop note: {s['official_early_stop_note']}")
        if s.get("confirm_scored"):
            A(f"Confirm was scored once, on the passing checkpoint with the highest official 965 chrF (step {s.get('confirm_step')}).")
        else:
            A("Confirm was not scored (no checkpoint passed the official gate).")
        A("")
        for c in s.get("ckpts") or []:
            fails = c.get("fails") or []
            notes = c.get("notes") or []
            if not fails and not notes:
                continue
            A(f"### Arm {ARM_LABEL[arm]} step {c.get('step')} notes")
            for f in fails:
                A(f"- FAIL: {f}")
            for n in notes:
                A(f"- Note: {n}")
            A("")
        conf_p = X / f"scores_confirm_{arm}.json"
        if conf_p.exists():
            conf = json.load(open(conf_p))
            A(f"### Confirm (arm {ARM_LABEL[arm]}, step {conf.get('step')}; not used to pick)")
            A("")
            A("| model | n | chrF | Δ vs v4e | Δ vs ctrl |")
            A("|---|---:|---:|---|---|")
            m = (conf.get("models") or {})
            gaps = conf.get("gaps") or {}
            A(f"| v4e | {conf.get('n')} | {(m.get(PARENT) or {}).get('chrf')} | — | — |")
            A(f"| ctrl (start) | {conf.get('n')} | {(m.get(START) or {}).get('chrf')} | {_fmt_ci(gaps.get(f'{START}_vs_{PARENT}'))} | — |")
            A(f"| {ARM_LABEL[arm]} | {conf.get('n')} | {(m.get(arm) or {}).get('chrf')} | {_fmt_ci(gaps.get(f'{arm}_vs_{PARENT}'))} | {_fmt_ci(gaps.get(f'{arm}_vs_{START}'))} |")
            A("")
    # arms stats if present
    st = X / "arms_stats.json"
    if st.exists():
        stats = json.load(open(st))
        A("## Data")
        A("")
        A(f"- Arm B keep rows: {stats.get('armB_rows')} (filter_v3 strict / per_sign).")
        A(f"- Buckets: {stats.get('armB_buckets')}")
        A(f"- Orders: {stats.get('orders')}")
        A(f"- Stubs dropped: {stats.get('stubs_dropped')}")
        A("")
    A("## Pickup markers")
    A("")
    A("- `runs/loop-pilot/ob-lit-v1/train/PIPELINE_DONE` — written when both arms are scored and this file is complete.")
    A("- `runs/loop-pilot/ob-lit-v1/train/RESULTS.md` — this report.")
    A("- `runs/loop-pilot/ob-lit-v1/train/gate_done_{a,b}.flag` — official gates finished for that arm.")
    A("- `runs/loop-pilot/ob-lit-v1/train/confirm_done_{a,b}.flag` — confirm scored for a passing arm.")
    A("- `models/clean-bysa-loop-ob-lit-v1-{a,b}/mix_train.json` — training finished for that arm.")
    A("")
    A("No promotion. `models/BEST_MODEL.json`, `models/best`, `models/clean-bysa-best`, and the Unread Atlas site/API were not changed.")
    A("")
    text = "\n".join(lines)
    (X / "RESULTS.md").write_text(text)
    log(f"wrote {X / 'RESULTS.md'}")
    passing = []
    for arm in ARMS:
        p = X / f"gate_summary_{arm}.json"
        if not p.exists():
            continue
        s = json.load(open(p))
        for c in s.get("ckpts") or []:
            if c.get("pass"):
                passing.append(f"{arm}@step{c.get('step')}")
    (X / "PIPELINE_DONE").write_text(f"{now()}\npassing={passing}\n")
    log(f"wrote PIPELINE_DONE passing={passing}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("gate-ckpts", "finalize"), required=True)
    ap.add_argument("--arm", choices=ARMS, default=None)
    a = ap.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    X.mkdir(parents=True, exist_ok=True)
    if a.mode == "gate-ckpts":
        if not a.arm:
            raise SystemExit("--arm is required for gate-ckpts")
        return mode_gate_ckpts(a.arm)
    return write_results()


if __name__ == "__main__":
    sys.exit(main() or 0)
