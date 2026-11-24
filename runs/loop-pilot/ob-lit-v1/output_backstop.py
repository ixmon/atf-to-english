#!/usr/bin/env python3
"""Post-decode backstop for language-tag / total-line hallucinations.

Flags (and optionally cleans) a hypothesis that starts with Subtotal:/surplus:
or contains %sú, (Sum)/(Akk), or 'es priest' when the source ATF has no
šunigin / szu+nigin2-style total cue (and no other matching cue).

This is a CPU post-process on already-decoded text. It does not re-run the
model. 'Redeode' here means rewrite the hyp to drop the leak tokens while
keeping the rest of the translation — including cases where the rest might
be a reasonable guess at damaged ATF.

Genuine total lines are left untouched.
"""
from __future__ import annotations

import re
from typing import Any

# šunigin / šu-nigin₂ and common ATF spellings, including szu+nijen2 (eBL).
GENUINE_TOTAL_RE = re.compile(
    r"""(?ix)
    (?:
        szu \s* \+? \s* nije?n [0-9]*
      | szu \s* -? \s* nigin [0-9]*
      | szunigin [0-9]*
      | šu \s* \+? \s* nijen [0-9]*
      | šu \s* -? \s* nigin [0-9]*
      | šunigin [0-9]*
    )
    """
)

# Leading account-header leaks (allow preceding whitespace / quotes).
HEADER_LEAK_RE = re.compile(
    r"""(?ix)
    ^ [\s"'(\[]*
    (?:
        sub [\s\-]* totals?
      | surplus
      | substitute
    )
    \s* :
    \s*
    [)\]]*
    \s*
    """
)

SU_COPY_RE = re.compile(r"(?i)%\s*s[uúùû](?:x)?\b")
SUM_AKK_RE = re.compile(r"\(\s*(?:Sum|Akk)\s*\)")
ES_PRIEST_RE = re.compile(r"(?i)\bes\s+priest\b")

# After dropping a header, also drop a leftover "subtotal" word mid-sentence? No —
# only the leak patterns named in the brief.


def has_genuine_total_cue(atf: str) -> bool:
    return bool(GENUINE_TOTAL_RE.search(atf or ""))


def leak_reasons(hyp: str, atf: str = "") -> list[str]:
    """Return leak labels. Genuine total cues justify a Subtotal/surplus header only."""
    h = hyp or ""
    reasons: list[str] = []
    genuine = has_genuine_total_cue(atf)
    if HEADER_LEAK_RE.search(h) and not genuine:
        # classify which header
        start = HEADER_LEAK_RE.search(h).group(0).lower()
        if "sub" in start and "total" in start.replace(" ", "").replace("-", ""):
            reasons.append("subtotal_header")
        elif "surplus" in start:
            reasons.append("surplus_header")
        elif "substitute" in start:
            reasons.append("substitute_header")
        else:
            reasons.append("subtotal_header")
    if SU_COPY_RE.search(h):
        reasons.append("pct_su")
    if SUM_AKK_RE.search(h):
        reasons.append("sum_akk")
    if ES_PRIEST_RE.search(h):
        reasons.append("es_priest")
    return reasons


def clean_hyp(hyp: str) -> str:
    h = hyp or ""
    h = HEADER_LEAK_RE.sub("", h)
    h = SU_COPY_RE.sub(" ", h)
    h = SUM_AKK_RE.sub(" ", h)
    h = ES_PRIEST_RE.sub(" ", h)
    h = re.sub(r"[ \t]{2,}", " ", h)
    h = re.sub(r"\s+([,.;:])", r"\1", h)
    h = re.sub(r"^[,.;:\s]+", "", h)
    return h.strip()


def apply_backstop(atf: str, hyp: str) -> dict[str, Any]:
    reasons = leak_reasons(hyp, atf)
    if not reasons:
        return {
            "flagged": False,
            "reasons": [],
            "original": hyp,
            "cleaned": hyp,
            "changed": False,
        }
    cleaned = clean_hyp(hyp)
    return {
        "flagged": True,
        "reasons": reasons,
        "original": hyp,
        "cleaned": cleaned,
        "changed": cleaned != (hyp or ""),
    }


def scan(rows, atf_key="atf", hyp_key="hyp") -> dict[str, Any]:
    """Scan a list of {atf, hyp} dicts. Returns counts and flagged rows (no English required)."""
    counts = {
        "n": 0,
        "flagged": 0,
        "changed": 0,
        "subtotal_header": 0,
        "surplus_header": 0,
        "substitute_header": 0,
        "pct_su": 0,
        "sum_akk": 0,
        "es_priest": 0,
        "genuine_total_left_alone": 0,
    }
    flagged = []
    for r in rows:
        counts["n"] += 1
        atf, hyp = r.get(atf_key) or "", r.get(hyp_key) or ""
        if has_genuine_total_cue(atf) and HEADER_LEAK_RE.search(hyp or ""):
            counts["genuine_total_left_alone"] += 1
        rec = apply_backstop(atf, hyp)
        if rec["flagged"]:
            counts["flagged"] += 1
            if rec["changed"]:
                counts["changed"] += 1
            for lab in rec["reasons"]:
                counts[lab] = counts.get(lab, 0) + 1
            item = {
                "id": r.get("id"),
                "tablet": r.get("tablet"),
                "reasons": rec["reasons"],
                "atf": atf,
                "original": rec["original"],
                "cleaned": rec["cleaned"],
            }
            flagged.append(item)
    counts["flagged_rows"] = flagged
    return counts
