#!/usr/bin/env python3
"""Unit tests for filter_v3, drawn from v3-r1 SPOTCHECK.md examples.

Run:  ~/cursor/atf-translate-test/.venv/bin/python -m unittest \
        runs/loop-pilot/design-v3/test_filter_v3.py
"""
from __future__ import annotations

import os
import sys
import unittest

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)

import filter_v3 as f3  # noqa: E402


def fails(atf, en, genre=None, paraphrase="lenient", **kw):
    # Default lenient so hard-reject tests are not conflated with the gloss switch.
    return f3.check(atf, en, genre=genre, paraphrase=paraphrase, **kw)["fails"]


def ok(atf, en, genre=None, paraphrase="lenient", **kw):
    return f3.check(atf, en, genre=genre, paraphrase=paraphrase, **kw)["ok"]


def gloss(atf, en, genre=None, paraphrase="lenient", **kw):
    return f3.check(atf, en, genre=genre, paraphrase=paraphrase, **kw)["flags"]["gloss"]


class AccountingInvented(unittest.TestCase):
    def test_subtotal_on_nanna_kam_rejected(self):
        # fair:0230 ctrl
        atf = "%sux 0.0.1 {d}nanna-kam"
        en = "Subtotal: 0;01, of Nanna."
        self.assertTrue(any(f.startswith("invented:subtotal") for f in fails(atf, en)))

    def test_sexagesimal_notation_alone_kept(self):
        # 0;01 is notation for ATF 0.0.1 — not a hard fail
        atf = "%sux 0.0.1 {d}nanna-kam"
        en = "0;01 Nanna-kam"
        fs = fails(atf, en)
        self.assertFalse(any("invented:" in f or "artifact:" in f for f in fs), fs)
        self.assertTrue(ok(atf, en), fs)

    def test_substitute_stewed_lamb_rejected(self):
        # fair:0243 ctrl
        atf = "%sux ½ sila3 inda3 ½ sila3 tu7"
        en = "substitute: one lamb, one stewed lamb,"
        fs = fails(atf, en)
        self.assertTrue(any(f.startswith("invented:substitute") for f in fs), fs)

    def test_subtracted_without_la2_rejected(self):
        # fair:0070 ctrl — a2-je6-ba-a has no la2/minus sign
        atf = "%sux a2-je6-ba-a u4 20-kam"
        en = "subtracted from the wages, 20th day,"
        self.assertTrue(any(f.startswith("invented:subtracted") for f in fails(atf, en)))

    def test_minus_without_la2_rejected(self):
        atf = "%sux 0.0.1 {d}nanna-kam"
        en = "minus 0;01 Nanna-kam"
        self.assertTrue(any(f.startswith("invented:minus") for f in fails(atf, en)))

    def test_minus_licensed_by_la2(self):
        atf = "5(u) la2 2(disz) sze gur"
        en = "50 minus 2 gur of barley"
        fs = fails(atf, en)
        self.assertFalse(any(f.startswith("invented:minus") for f in fs), fs)

    def test_ditto_without_min_rejected(self):
        # fair:0143 — month name, no MIN
        atf = "%sux iti izim-{d}szu-{d}zuen u4 11 | ba-zal"
        en = "Ditto. Month: “Izim-Šuzun,” day 11, passed."
        self.assertTrue(any(f.startswith("invented:ditto") for f in fails(atf, en)))

    def test_percent_ditto_without_min_rejected(self):
        atf = "%sux 0.1.2 5 sila3 sze-ba# [x]"
        en = "% ditto: 0;01 2 sila3 barley rations ...;"
        self.assertTrue(any(f.startswith("invented:ditto") for f in fails(atf, en)))

    def test_ditto_licensed_by_disz_min(self):
        atf = "_{u2}ab2-duh disz-min hi-hi_ [...]"
        en = "abduh-plant, ditto, mix ..."
        fs = fails(atf, en, genre="Medical")
        self.assertFalse(any(f.startswith("invented:ditto") for f in fs), fs)

    def test_ditto_licensed_by_bracketed_min(self):
        atf = "ugula disz me-at {<[MIN(a-kil)>} ...]"
        en = "foreman: Meat, ditto (as before, ...); "
        fs = fails(atf, en, genre="Lexical")
        self.assertFalse(any(f.startswith("invented:ditto") for f in fs), fs)

    def test_ditto_licensed_by_min(self):
        atf = "ge19> ge-e PESZ2 MIN<(nam-ma-szu-u2)>"
        en = "Oh, oh, ditto(?)"
        fs = fails(atf, en)
        self.assertFalse(any(f.startswith("invented:ditto") for f in fs), fs)

    def test_subtotal_licensed_by_szunigin(self):
        atf = "szunigin 5(disz) sila3 tu7"
        en = "Subtotal: 5 sila of soup"
        fs = fails(atf, en)
        self.assertFalse(any(f.startswith("invented:subtotal") for f in fs), fs)


class ArtifactSymbols(unittest.TestCase):
    def test_empty_set_prefix_rejected(self):
        # fair:0230 / fair:0040 v4e
        atf = "%sux 0.0.1 {d}nanna-kam"
        en = "Ø 0;01 Nanna-kam"
        self.assertTrue(any(f == "artifact:Ø" for f in fails(atf, en)))

    def test_pilcrow_rejected(self):
        # fair:0023
        atf = "%sux 1 ur-nijar[{jar}]"
        en = "¶ Ur-niŋar"
        self.assertTrue(any(f == "artifact:¶" for f in fails(atf, en)))

    def test_section_sign_rejected(self):
        atf = "%sux 1 tarah a na8-na8 [x]"
        en = "§ 1: a tarah-vessel to drink water"
        self.assertTrue(any(f == "artifact:§" for f in fails(atf, en)))

    def test_sexagesimal_semicolon_is_not_artifact(self):
        atf = "%sux 0.0.1 {d}nanna-kam"
        en = "0;01 Nanna-kam"
        fs = fails(atf, en)
        self.assertFalse(any(f.startswith("artifact:") for f in fs), fs)


class LanguageTagLeaks(unittest.TestCase):
    def test_percent_shu_leak_rejected(self):
        # fair:0148 ctrl
        atf = "%sux ummux 6"
        en = "%šu-ummu 6"
        fs = fails(atf, en, genre="ARCHIVAL > Administrative > Receipts")
        self.assertTrue(any(f.startswith("langtag:") for f in fs), fs)

    def test_sum_akk_on_monolingual_rejected(self):
        atf = "[...] x isz-te-en la i-x [...]"
        en = "(Sum) ... (Akk) One does not ..."
        fs = fails(atf, en, genre="Literary")
        self.assertTrue(any(f.startswith("langtag:") for f in fs), fs)

    def test_sum_akk_on_bilingual_lexical_kept(self):
        # fair:1221-style lexical equation
        atf = "ki-tusz > ... KI-TUSZ ... tu-usz-sza2-ku szub-tum"
        en = "(Sum) My residence ... (Akk) You reside ..."
        fs = fails(atf, en, genre="Lexicography")
        self.assertFalse(any(f.startswith("langtag:") for f in fs), fs)


class CopyThrough(unittest.TestCase):
    def test_gigur_innuda_rejected(self):
        # fair:0534 ctrl
        atf = "gi-gur in-nu-da gi-gur pisag"
        en = "Gigur innuda, gigur pisag,"
        fs = fails(atf, en, genre="Lexical")
        self.assertTrue(any(f.startswith("copy_through:") for f in fs), fs)

    def test_angurum_stem_rejected(self):
        # fair:0850 ctrl
        atf = "[...]-an-gurum2"
        en = "-angurum"
        fs = fails(atf, en, genre="Literary")
        self.assertTrue(any(f.startswith("copy_through:") for f in fs), fs)

    def test_translated_basket_kept(self):
        atf = "gi-gur in-nu-da gi-gur pisag"
        en = "reed basket for straw"
        fs = fails(atf, en, genre="Lexical")
        self.assertFalse(any(f.startswith("copy_through:") for f in fs), fs)


    def test_buqaqum_name_not_copy_through(self):
        atf = "{disz}bu-qa-qum ki-a-am isz#-pu-[ra]-am#"
        en = "Buqaqum wrote to me thus:"
        fs = fails(atf, en, genre="Letter")
        self.assertFalse(any(f.startswith("copy_through:") for f in fs), fs)

    def test_ceremonial_transcription_not_copy_through(self):
        atf = "e2-temen-ni2-gur3-ru"
        en = "the Etemenniguru"
        fs = fails(atf, en, genre="Official or display")
        self.assertFalse(any(f.startswith("copy_through:") for f in fs), fs)



    def test_damaged_unmarked_name_atta_ma_kept(self):
        atf = "_ki_ at-ta-ma-x-[...]"
        en = "from Atta-ma-[...]"
        fs = fails(atf, en, genre="Legal")
        self.assertFalse(any(f.startswith("copy_through:") for f in fs), fs)

    def test_unmarked_name_zikanim_kept(self):
        atf = "sza _ARAD_ zi-ka?-nim?"
        en = "of the servant Zikanim(?)"
        fs = fails(atf, en, genre="Administrative")
        self.assertFalse(any(f.startswith("copy_through:") for f in fs), fs)

    def test_month_name_apindua_kept(self):
        atf = "_iti {gesz}apin-du8-a u4 2(u) 9(disz)-kam_"
        en = "Month of Apinduʾa, day 29"
        fs = fails(atf, en, genre="Administrative")
        self.assertFalse(any(f.startswith("copy_through:") for f in fs), fs)

    def test_already_english_palm_tree_kept(self):
        atf = "Palm tree"
        en = "Palm tree"
        fs = fails(atf, en, genre="Royal Inscription")
        self.assertFalse(any(f.startswith("copy_through:") for f in fs), fs)

    def test_already_english_stylized_tree_kept(self):
        atf = "Stylized tree"
        en = "Stylized tree"
        fs = fails(atf, en, genre="Royal Inscription")
        self.assertFalse(any(f.startswith("copy_through:") for f in fs), fs)


class OmenTemplate(unittest.TestCase):
    def test_if_stub_on_lexical_rejected(self):
        # fair:0409 ctrl
        atf = "gu > (disz) ... GU qu-u2"
        en = "(If) ... ."
        fs = fails(atf, en, genre="Lexicography")
        self.assertTrue("omen_template" in fs, fs)

    def test_tukum_bi_if_is_not_omen(self):
        atf = "tukum#-[bi]"
        en = "If"
        fs = fails(atf, en, genre="Letter")
        self.assertFalse("omen_template" in fs, fs)

    def test_diagnostic_if_kept(self):
        # fair:0591
        atf = "DISZ# sz[a]p-ti-szu a-na e-le-nu u2-ha-an-na-as, BA.USZ2"
        en = "If he pulls his lip upward: He will die."
        genre = "CANONICAL > Technical > Medicine > Diagnostic and Prognostic"
        fs = fails(atf, en, genre=genre)
        self.assertFalse("omen_template" in fs, fs)


class CommonNounAsPN(unittest.TestCase):
    def test_meluletum_rejected(self):
        # fair:0473
        atf = "me-lu-le-tum"
        en = "Meluletum"
        fs = fails(atf, en, genre="Royal Inscription")
        self.assertTrue(any(f.startswith("common_noun_as_pn:") for f in fs), fs)

    def test_games_gloss_kept(self):
        atf = "me-lu-le-tum"
        en = "games"
        fs = fails(atf, en, genre="Royal Inscription")
        self.assertFalse(any(f.startswith("common_noun_as_pn:") for f in fs), fs)


class CeremonialNameAndChrF(unittest.TestCase):
    def test_etemenniguru_expansion_not_hard_dropped(self):
        # fair:1327 ctrl — ceremonial-name expansion must not be a hard fail
        atf = "e2-temen-ni2-gur3-ru"
        en = "the House With a Foundation Clad in Fearsomeness,"
        r = f3.check(atf, en, genre="Official or display")
        self.assertTrue(r["ok"], r["fails"])

    def test_etemenniguru_name_kept(self):
        atf = "e2-temen-ni2-gur3-ru"
        en = "the Etemenniguru"
        self.assertTrue(ok(atf, en, genre="Official or display"))

    def test_chrf_is_not_a_keep_drop_key(self):
        atf = "e2-temen-ni2-gur3-ru"
        en = "the House With a Foundation Clad in Fearsomeness,"
        r = f3.check(atf, en, genre="Official or display")
        # no chrF in fails, flags, or as a drop criterion
        self.assertFalse(any("chrf" in f.lower() for f in r["fails"]))
        self.assertFalse("chrf" in r["flags"])


class GlossFlag(unittest.TestCase):
    def test_stewed_lamb_is_flagged(self):
        # fair:0243 — "lamb" / "stewed" are not glosses of inda3 / tu7
        atf = "%sux ½ sila3 inda3 ½ sila3 tu7"
        en = "substitute: one lamb, one stewed lamb,"
        g = gloss(atf, en)
        words = {w.lower() for w in g["unlicensed"]}
        self.assertTrue(
            any(w in words for w in ("lamb", "stewed", "stew")),
            g,
        )
        self.assertGreaterEqual(g["n_unlicensed"], 1)

    def test_bread_and_soup_not_flagged(self):
        atf = "%sux ½ sila3 inda3 ½ sila3 tu7"
        en = "½ sila of bread and ½ sila of soup"
        g = gloss(atf, en)
        words = {w.lower() for w in g["unlicensed"]}
        self.assertFalse("bread" in words or "soup" in words, g)

    def test_gloss_flag_is_not_a_hard_drop_for_expansion(self):
        atf = "e2-temen-ni2-gur3-ru"
        en = "the House With a Foundation Clad in Fearsomeness,"
        r = f3.check(atf, en, genre="Official or display")
        self.assertTrue(r["ok"], r["fails"])
        # Flag may or may not fire on 'Clad' / 'Fearsomeness'; it must not drop.
        self.assertIn("gloss", r["flags"])

    def test_sennacherib_name_not_gloss_flagged(self):
        atf = "{[m]}{d#}EN.ZU-SZESZ.MESZ-SU LUGAL# [GAL-u2]"
        en = "[S]ennacherib, [great] king,"
        g = gloss(atf, en, genre="Royal Inscription")
        words = {w.lower() for w in g["unlicensed"]}
        self.assertFalse(any("ennacherib" in w or "sennacherib" in w for w in words), g)

    def test_ordinals_are_atf_backed_numbers(self):
        atf = "_u4 1(u) 3(disz)-kam_"
        en = "13th day,"
        g = gloss(atf, en)
        words = {w.lower() for w in g["unlicensed"]}
        self.assertFalse(any("13th" in w or w.endswith("th") for w in words), g)
        r = f3.check(atf, en, paraphrase="strict")
        self.assertFalse("gloss_unlicensed" in r["fails"], r)

    def test_names_and_numbers_exempt(self):
        atf = "%sux 0.0.1 {d}nanna-kam"
        en = "0;01 Nanna-kam"
        g = gloss(atf, en)
        words = {w.lower() for w in g["unlicensed"]}
        self.assertFalse(any("nanna" in w or "0;01" in w or w.isdigit() for w in words), g)


class ParaphraseMode(unittest.TestCase):
    """strict (chrF phase): gloss threshold is a reject; lenient: flag only."""

    def test_etemenniguru_kept_in_both_modes(self):
        atf = "e2-temen-ni2-gur3-ru"
        en = "the House With a Foundation Clad in Fearsomeness,"
        for mode in ("strict", "lenient"):
            r = f3.check(atf, en, genre="Official or display", paraphrase=mode)
            self.assertTrue(r["ok"], (mode, r["fails"]))
            self.assertFalse(r["flags"]["gloss_over_threshold"], r["flags"]["gloss"])

    def test_silversmiths_flag_only_when_lenient(self):
        # fair:0262 — good paraphrase of ku3-dim2 "goldsmiths"
        atf = "%sux ku3-dim2-me-esz2"
        en = "the silversmiths"
        r = f3.check(atf, en, genre="ARCHIVAL > Administrative", paraphrase="lenient")
        self.assertTrue(r["flags"]["gloss_over_threshold"], r["flags"]["gloss"])
        self.assertTrue(r["ok"], r["fails"])
        self.assertFalse(any(f == "gloss_unlicensed" for f in r["fails"]))

    def test_silversmiths_rejected_when_strict(self):
        atf = "%sux ku3-dim2-me-esz2"
        en = "the silversmiths"
        r = f3.check(atf, en, genre="ARCHIVAL > Administrative", paraphrase="strict")
        self.assertTrue(r["flags"]["gloss_over_threshold"], r["flags"]["gloss"])
        self.assertIn("gloss_unlicensed", r["fails"])
        self.assertFalse(r["ok"])

    def test_stewed_lamb_rejected_in_both_modes(self):
        atf = "%sux ½ sila3 inda3 ½ sila3 tu7"
        en = "substitute: one lamb, one stewed lamb,"
        for mode in ("strict", "lenient"):
            r = f3.check(atf, en, paraphrase=mode)
            self.assertTrue(any(f.startswith("invented:substitute") for f in r["fails"]), (mode, r["fails"]))
            self.assertTrue(r["flags"]["gloss"]["n_unlicensed"] >= 1, r["flags"]["gloss"])
            if mode == "strict":
                self.assertIn("gloss_unlicensed", r["fails"])

    def test_default_is_strict(self):
        atf = "%sux ku3-dim2-me-esz2"
        en = "the silversmiths"
        r = f3.check(atf, en, genre="ARCHIVAL > Administrative")
        self.assertEqual(r["flags"]["paraphrase"], "strict")
        self.assertIn("gloss_unlicensed", r["fails"])



if __name__ == "__main__":
    unittest.main()
