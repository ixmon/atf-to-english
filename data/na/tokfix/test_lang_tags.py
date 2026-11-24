#!/usr/bin/env python3
"""Tests for ORACC/eBL language-tag stripping in tokfix.normalize_atf.

Uncommitted follow-up to ob-lit-v1: eBL `%sux` / `%akk` / `%a` / `%es`
reaching model input causes Subtotal: / surplus: / %sú leaks.
Run:  .venv/bin/python data/na/tokfix/test_lang_tags.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tokfix as TF  # noqa: E402


CASES = [
    # line-initial eBL Sumerian tag (the Subtotal trigger)
    ("%sux lugal-an-dil2", "lugal-an-dil2"),
    ("%sux u4 2-a-kam", "u4 2-a-kam"),
    ("%sux 1 ur-nijar[{jar}]", "1 ur-nijar[{jar}]"),
    ("%sux szu+nijen2 9.2.0 sze gur", "szu+nijen2 9.2.0 sze gur"),
    ("%SUX e2-gal an ku3-ge tud-da-a", "e2-gal an ku3-ge tud-da-a"),
    # Emesal
    ("%es {a}akkil{ki} x ku3-ga im-gi4-gi4", "{a}akkil{ki} x ku3-ga im-gi4-gi4"),
    # bilingual eBL lexical
    ("%sux [i3]-dub [sze] & %akk [isz-pi-ki sze-im]",
     "[i3]-dub [sze] & [isz-pi-ki sze-im]"),
    ("%sux [{jesz}ka-ra-an jesztin & %sb til]-la#-tu4# & [...]",
     "[{jesz}ka-ra-an jesztin & til]-la#-tu4# & [...]"),
    # eBL %n note
    ("%sux [{jesz.szim}mar-g]u-zum# & %sb SZU %n <(margūs,u)> %sb & la-d[u-nu]",
     "[{jesz.szim}mar-g]u-zum# & SZU <(margūs,u)> & la-d[u-nu]"),
    # CDLI lexical `%a` Akkadian column
    ("dub3 [gurum] = %a 5(disz)", "dub3 [gurum] = 5(disz)"),
    ("i3-hul# = %a nap-t,um", "i3-hul# = nap-t,um"),
    # subtype
    ("%sux-x-emesal ama ugu-gu10", "ama ugu-gu10"),
    ("%akk-x-oldbab a-na LUGAL", "a-na LUGAL"),
    # Unicode šu tag, after CDLI-ASCII fold
    ("%šu an-dil2", "an-dil2"),
    # already clean: unchanged
    ("lugal-an-dil2", "lugal-an-dil2"),
    ("{d}en-lil2-la2 e2-a-ni", "{d}en-lil2-la2 e2-a-ni"),
    ("silim bi2-tag-ga", "silim bi2-tag-ga"),
    # do not eat non-tag percent forms
    ("a 50% sila3", "a 50% sila3"),
    ("x %unknown-foo y", "x %unknown-foo y"),
]


def test_strip_cases():
    fail = 0
    for src, want in CASES:
        got = TF.normalize_atf(src)
        if got != want:
            print(f"FAIL normalize_atf({src!r}) -> {got!r} want {want!r}")
            fail += 1
        again = TF.normalize_atf(got)
        if again != got:
            print(f"FAIL not idempotent: {src!r} -> {got!r} -> {again!r}")
            fail += 1
    return fail


def test_model_input_drops_tag():
    fail = 0
    raw = "%sux lugal-an-dil2"
    mi = TF.model_input(raw)
    if "%sux" in mi.lower() or "%su" in mi.lower():
        print("FAIL model_input still contains a language tag:", mi)
        fail += 1
    if "lugal-an-dil2" not in mi:
        print("FAIL model_input lost the ATF:", mi)
        fail += 1
    if not mi.startswith(TF.PREFIX):
        print("FAIL model_input missing prefix:", mi)
        fail += 1
    # Emesal should not leave a token that becomes "es priest"
    mi2 = TF.model_input("%es {a}akkil{ki} im-gi4-gi4")
    # after strip the line should not start with "es " as a leftover code
    body = mi2[len(TF.PREFIX):]
    if body.lower().startswith("es "):
        print("FAIL leftover es code in model_input:", mi2)
        fail += 1
    return fail


def test_untagged_roundtrip_stable():
    """Untagged CDLI-ASCII ATF must be unchanged by the new step."""
    samples = [
        "1(disz) {d}nanna-kam",
        "mu us2-sa ki-masz{ki} ba-hulu",
        "nibru{ki} lu2 NE [...]",
        "szu+nijen2 9.2.0 sze gur",
    ]
    fail = 0
    for s in samples:
        got = TF.normalize_atf(s)
        if got != s:
            print(f"FAIL untagged changed: {s!r} -> {got!r}")
            fail += 1
    return fail


def test_off_switch():
    import os, importlib
    fail = 0
    os.environ["TOKFIX_STRIP_LANG_TAGS"] = "0"
    importlib.reload(TF)
    got = TF.normalize_atf("%sux lugal-an-dil2")
    if got != "%sux lugal-an-dil2":
        print(f"FAIL off-switch still stripped: {got!r}")
        fail += 1
    if "translate Akkadian to English: " not in TF.model_input("%sux lugal-an-dil2"):
        print("FAIL prefix changed")
        fail += 1
    # restore default ON and reload so later imports see the patch
    os.environ["TOKFIX_STRIP_LANG_TAGS"] = "1"
    importlib.reload(TF)
    got = TF.normalize_atf("%sux lugal-an-dil2")
    if got != "lugal-an-dil2":
        print(f"FAIL on-switch did not strip: {got!r}")
        fail += 1
    if TF.PREFIX != "translate Akkadian to English: ":
        print("FAIL PREFIX constant changed:", TF.PREFIX)
        fail += 1
    return fail


if __name__ == "__main__":
    fail = 0
    fail += test_strip_cases()
    fail += test_model_input_drops_tag()
    fail += test_untagged_roundtrip_stable()
    fail += test_off_switch()
    n = len(CASES) + 2 + 4
    print(f"{'PASS' if fail==0 else 'FAIL'}: {fail} failure(s)")
    sys.exit(1 if fail else 0)
