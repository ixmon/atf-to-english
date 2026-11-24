#!/usr/bin/env python3
"""Tests for the post-decode Subtotal / %sú / (Sum) / es-priest backstop."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import output_backstop as OB  # noqa: E402


def check(cond, msg):
    if not cond:
        print("FAIL", msg)
        return 1
    return 0


def main():
    f = 0
    # Genuine šunigin: Subtotal is allowed, not flagged.
    atf = "szu+nijen2 9.2.0 sze gur"
    hyp = "Subtotal: 9 gur 2 barig of barley."
    rec = OB.apply_backstop(atf, hyp)
    f += check(not rec["flagged"], f"genuine szu+nijen2 was flagged: {rec}")
    f += check(rec["cleaned"] == hyp, "genuine hyp was rewritten")

    atf2 = "szu-nigin2 3(disz) udu"
    rec = OB.apply_backstop(atf2, "subtotal: 3 sheep")
    f += check(not rec["flagged"], f"szu-nigin2 was flagged: {rec}")

    # False Subtotal on a name line: flag and drop the header, keep the name.
    rec = OB.apply_backstop("%sux lugal-an-dil2", "subtotal: Lugal-andil;")
    f += check(rec["flagged"] and "subtotal_header" in rec["reasons"], rec)
    f += check(rec["cleaned"] == "Lugal-andil;", f"clean={rec['cleaned']!r}")

    rec = OB.apply_backstop("u4 2-a-kam", "Surplus: 2nd day;")
    f += check("surplus_header" in rec["reasons"], rec)
    f += check(rec["cleaned"] == "2nd day;", f"clean={rec['cleaned']!r}")

    # %sú copy-through
    rec = OB.apply_backstop("%sux a2-sze murgu2", "%sú: barley rations, neck ...;")
    f += check("pct_su" in rec["reasons"], rec)
    f += check("%sú" not in rec["cleaned"].lower() and "barley rations" in rec["cleaned"], rec)

    # (Sum)/(Akk)
    rec = OB.apply_backstop("%sux szen-szen-na", "(Sum) ... (Akk) The ziggurat of ...")
    f += check("sum_akk" in rec["reasons"], rec)
    f += check("(Sum)" not in rec["cleaned"] and "(Akk)" not in rec["cleaned"], rec)
    f += check("ziggurat" in rec["cleaned"], rec)

    # es priest leak
    rec = OB.apply_backstop("%es {a}akkil{ki} ku3-ga im-gi4-gi4",
                           "The es priest of Akkil returned the pure ...")
    f += check("es_priest" in rec["reasons"], rec)
    f += check("es priest" not in rec["cleaned"].lower(), rec)
    f += check("Akkil" in rec["cleaned"], rec)

    # Clean line is left alone
    rec = OB.apply_backstop("ama ugu-gu10", "My birth mother ...")
    f += check(not rec["flagged"] and rec["cleaned"] == "My birth mother ...", rec)

    # nijen inside a name (ISZ-gal-nijen5) is NOT a total cue
    rec = OB.apply_backstop("%sux 1 x#-ne2-ISZ-gal-nijen5", "subtotal: 1 x-ne-ISZgal-niŋen;")
    f += check(rec["flagged"], f"name nijen5 should not count as šunigin: {rec}")

    print("PASS" if f == 0 else f"FAIL: {f} failure(s)")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())

def test_parenthetical_subtotal_label_does_not_leave_a_stray_paren():
    rec = OB.apply_backstop("5(u) 4(disz)", "(Subtotal:) 54 (lines)")
    assert rec["changed"]
    assert rec["cleaned"] == "54 (lines)"
    rec2 = OB.apply_backstop("5(u) 4(disz)", "(subtotal:) 40 (shekels)")
    assert rec2["cleaned"] == "40 (shekels)"

