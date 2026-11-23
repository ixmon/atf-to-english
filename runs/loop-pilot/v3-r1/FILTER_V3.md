# Filter v3 offline report (v3-r1)

Written 4:09 PM America/New_York on Nov 22, 2026. CPU only. Module: `runs/loop-pilot/design-v3/filter_v3.py`. Tests: `runs/loop-pilot/design-v3/test_filter_v3.py` (**62 passing**, including copy-through, paraphrase-mode, gloss-expansion, reverse-check, and determinative regressions).



## 2026-11-23 update: expanded gloss, reverse check, flat vocab

Written 3:20 AM EST (America/New_York) on Nov 23, 2026. CPU only. No GPU, no training, no TensorFold. Full tables and the 10-line samples: `FILTER_V3_TIERS.md` and `filter_v3_tiers_report.json`.

### Gloss list size (clean sources only)

Clean ORACC/ePSD-style glossary via `lemma_support` (ETCSL/eBL already excluded) plus `runs/clean-bysa-v4e/train.json` human pairs. Miner: `runs/loop-pilot/design-v3/mine_clean_gloss.py`. Cache: `design-v3/cache/clean_gloss_mine.json.gz`.

From 400,253 train records, **334,966** clean human pairs were used. Excluded: synth 44,308; ETCSL-tagged 11,170 (not mined, even if they appeared in the mix file); empty keys/words 9,809. No eBL, NC, or B2c rows entered the mine.

| list | unique English lemmas |
|---|---:|
| Official ORACC/ePSD-style (function words dropped) | **9,670** |
| After curated synonyms + WordNet on those lemmas | **21,287** |
| After mined per-sign English (count ≥ 5, PMI ≥ 2.0, official-conflict filter) | **30,684** |
| Flat clean-human vocab (lemmatized content words) | **49,004** |

Lemmatization uses NLTK WordNetLemmatizer plus the existing irregular map (`built`→`build`, `years`→`year`). Synonyms are curated groups (smear≈anoint/rub, restore≈return, barge-man≈boatman, silversmith≈goldsmith, nam+tar → determine fate) plus conservative same-POS WordNet on the *hypothesis* side. WordNet is **not** used to inflate the allowed set. Per-sign mining does not attach a word to a sign if that word already has a different official home (`sila3` does not inherit `lamb` from `sila4`).

Other filter fixes in this pass: hyphen-split ATF lookup (`du3-en` → `du3`), stop-list no longer uses `fv.STOP_EN` (so `year`/`silver`/`gold` stay content words), determinatives are stripped *before* punctuation (`{na4}ur5` → `ur5`, `{gesz}ma2` → `ma2`), and `{gesz}` licenses “wooden”.

### Three gloss tiers, side by side

`check(..., paraphrase, gloss_tier)` always computes all three flags. In `strict` mode, `gloss_tier` chooses which one becomes `gloss_unlicensed`:

- **`per_sign`** (default): forward official + synonyms + mined list; reject if `n_unlicensed ≥ 2` or `ratio ≥ 0.40`.
- **`corpus_vocab`**: word not in the flat clean-human vocab; same 2 / 0.40 threshold.
- **`reverse`**: a content word maps to known signs and *none* of them appear in the ATF (e.g. `lamb: expected u8|si6|…`; words with no mapping get no judgment). Threshold **n ≥ 1**.

Keep rule on arm S is the same as before (disagreement, confidence, word cap, judge ∈ {better, equivalent}) plus the named filter.

| policy | kept of 1,479 | improve-pool filter-ok |
|---|---:|---:|
| lenient (hard rejects only) | **1448 (97.9%)** | 3279/4925 (66.6%) |
| strict forward per-sign | **1302 (88.0%)** | 3012/4925 (61.2%) |
| strict forward, ratio limb only if n_content ≥ 3 | 1440 (97.4%) | 3260/4925 (66.2%) |
| strict corpus vocab | 1440 (97.4%) | 3258/4925 (66.2%) |
| strict reverse (n ≥ 1) | **1238 (83.7%)** | 2802/4925 (56.9%) |

Before this expansion, strict forward kept 1,099 / 1,479 (74.3%). The expanded list recovered **203** arm-S lines.

Forward strict genre keep vs arm S: Administrative 425/461 (92.2%), Royal 186/214 (86.9%), Literary 192/211 (91.0%), Letter 157/188 (83.5%), Lexical 130/165 (78.8%), Medical 133/144 (92.4%), Other 9/10 (90.0%). Admin share of kept: 425/1302 (32.6%). Arm-S filter rejects: gloss_unlicensed 146, copy_through 19, common_noun_as_pn 11, invented 3.

Reverse is harsher in medical (119/144, 82.6%) and letters (148/188, 78.7%). Corpus vocab rejects only 8 extra arm-S lines — too loose to use as a drop.

### 30-line SPOTCHECK panel (ctrl hyps)

Caught = hard reject OR the named gloss threshold. Cat (c) = 16 real errors; (b) = 3 good paraphrases; (a) = 5 formatting.

| check | real errors (c) | paraphrases (b) flagged | formatting (a) |
|---|---|---|---|
| hard rejects only | 12/16 | 1/3 | 1/5 |
| hard + forward per-sign | **14/16** | 1/3 | 1/5 |
| hard + forward, ratio min 3 | 12/16 | 1/3 | 1/5 |
| hard + corpus vocab | 12/16 | 1/3 | 1/5 |
| hard + reverse n≥1 | **14/16** | 1/3 | 1/5 |

The one flagged paraphrase (`fair:0460`) is a pre-existing **hard** `lemma_missing` drop, not a gloss false flag. `fair:0262` (silversmiths) and `fair:1327` (Etemenniguru) are clean on every gloss tier.

`fair:0243` (“stewed lamb” on a sila3 / bread / soup line) is a hard reject *and* both forward (`lamb`, `stewed`) and reverse (`lamb: expected u8|si6|…`; sila3 is not treated as a lamb sign). `fair:0230` (“Subtotal” on `0.0.1 {d}nanna-kam`) is a hard `invented:subtotal` *and* is reverse-flagged. The two extra real-error catches vs hard-only are `fair:0883` and `fair:0849` (short-line forward/reverse). A minimum content length of 3 on the ratio limb drops those two catches and is **not** recommended as the default strict rule.

### Hand check (seed 20261123)

10 random arm-S lines kept under lenient but rejected by **strict forward** (pool n=146):

| # | id | judgment |
|---|---|---|
| 1 | P270691:9 `a2 mu-a-sze3` “labor of that year” | **WRONG** — a2 is labor/wages |
| 2 | P247855:307 “a type of grass” | **BORDERLINE** — “type” is lexical metalanguage |
| 3 | P333149:130 “gag (is a synonym of): weapon” | **BORDERLINE** — “synonym” is list apparatus |
| 4 | P270782:5 `nig2-ar3-ra` “niŋaru-allocation” | **BORDERLINE** — ATF-backed loan, split poorly |
| 5 | P393923:414 `ka-mu-szu-nu` “offerings” | **BORDERLINE** — kamû is not clearly “offerings” |
| 6 | P263166:79 `nig2-mu10-us2-sa2` “marriage gift” | **WRONG** — this is the marriage-gift term |
| 7 | P248028:15 `u2-sze-lu-u2` “clear (a field)” | **BORDERLINE** |
| 8 | P358363:18 `i-sze2-ep` “pay the silver” | **BORDERLINE** |
| 9 | P270790:7 `szu ti-a` / `{lu2}azlag2` “received, fullers” | **WRONG** — both readings are standard |
| 10 | P481834:29 `at,-ru-du-szu` “cursed him” | **RIGHT** — ṭarādum is “to send,” not “curse” |

About 3/10 clearly wrong, 1 clearly right, the rest borderline. Residual false rejects are mostly short-line ratio fires and official-list gaps (`a2` “labor”, níg-mu10-us2-sa2, šu ti-a / azlag2).

10 random **strict reverse** rejects (pool n=210): more false flags on unlisted conjugations (`az-za-ki` “I stand”), already-English ATF paraphrases (podium ~ pedestal), and names (`ʿAmmi`). Reverse is the right *detector* for lamb / Subtotal / strong / banquet, but too jumpy as the only strict drop.

The six previously wrong rejects from the Nov 22 hand check: **built, barge-man, years, determine fate, restore** are now kept in both modes; **smear** (`tu-tap-pa-[as]`) is still rejected (the damaged conjugation is not in the official glossary or the mine). The two correct rejects, **strong** vs raṣāpu and **banquet** vs kapru, still reject under forward and under reverse.

### Recommendation

Use **expanded forward per-sign** as the strict-mode reject (chrF phase / Arm B). Record reverse as a FLAG only (do not drop on it yet). Do not use the flat vocab as a reject. Do not add a third training arm. `ratio_min_content=3` is too loose for the official panel.


## Paraphrase mode switch

Filter v3 has `--paraphrase strict|lenient` (`check(..., paraphrase=...)`).

- **`strict`** (default of `check()`, the chrF-phase default): the gloss FLAG becomes a hard reject when `n_unlicensed >= 2` or `ratio >= 0.40`. Names and ATF-backed numbers (including 13th / 29th ordinals) stay exempt. Use this while the goal is corpus chrF.
- **`lenient`**: the gloss check stays a FLAG only, so good paraphrases (Etemenniguru, silversmiths/goldsmiths) can be kept. Use this later, when improving quality past what chrF can measure.

Hard rejects (invented Subtotal/ditto, Ø/¶/§, language-tag leaks, copy-through, omen templates on non-omen lines, common nouns as PNs) apply in both modes. Sexagesimal `0;01` for ATF `0.0.1` and ceremonial-name expansions are not hard fails. chrF is not a keep/drop rule. Glossary: clean ORACC BY-SA via `lemma_support` (ETCSL/eBL excluded).

Copy-through was tightened so it no longer over-fires on damaged or unmarked names (`Atta-ma-[...]`, `Zikanim`), month names on an `iti`-line (`Apinduʾa`), or ATF that is already English (`Palm tree`, `Stylized tree`). True copy-through (`Gigur innuda`, `-angurum`) and common-noun-as-PN (`Meluletum`) still reject.

## Keep counts versus the 1,479 arm-S lines

Replayed the v3-r1 keep rule (disagreement AND confidence high/medium AND word cap ≤ 1.8×+4 AND judge ∈ {better, equivalent}) with filter v3 in each mode.

| mode | kept | of 1479 | newly rejected from S | newly kept | filter-ok among S |
|---|---:|---:|---:|---:|---:|
| **lenient** | 1444 | 1444/1479 (97.6%) | 35 | 0 | 1444/1479 (97.6%) |
| **strict** | 1099 | 1099/1479 (74.3%) | 380 | 0 | 1099/1479 (74.3%) |

## qwen_improve pool (filter only)

Every improve record with English and no Qwen error, ignoring disagreement / judge / word cap.

| mode | filter-ok | of improve-ok lines |
|---|---:|---:|
| **lenient** | 3134 | 3134/4925 (63.6%) |
| **strict** | 2460 | 2460/4925 (49.9%) |

### lenient improve-pool reject tags

| tag | n |
|---|---:|
| `lemma_missing` | 925 |
| `invented` | 548 |
| `names` | 339 |
| `numbers` | 222 |
| `copy_through` | 85 |
| `common_noun_as_pn` | 57 |
| `doubled_gloss` | 13 |
| `units` | 10 |
| `titulary` | 6 |
| `omen_template` | 2 |
| `langtag` | 1 |
| `idiom` | 1 |

### strict improve-pool reject tags

| tag | n |
|---|---:|
| `gloss_unlicensed` | 1636 |
| `lemma_missing` | 925 |
| `invented` | 548 |
| `names` | 339 |
| `numbers` | 222 |
| `copy_through` | 85 |
| `common_noun_as_pn` | 57 |
| `doubled_gloss` | 13 |
| `units` | 10 |
| `titulary` | 6 |
| `omen_template` | 2 |
| `langtag` | 1 |
| `idiom` | 1 |

## lenient: rejects from the 1,479 by reason

| tag | n |
|---|---:|
| `copy_through` | 24 |
| `common_noun_as_pn` | 11 |
| `invented` | 3 |

Administrative share of arm S was 461/1479 (31.2%); of the lenient keep set it is 451/1444 (31.2%).

### lenient: genre

| slice | v3-r1 arm S (1479) | kept | keep vs S |
|---|---:|---:|---:|
| Administrative | 461 (31.2%) | 451 (31.2% of kept) | 451/461 (97.8%) |
| Royal / official | 214 (14.5%) | 212 (14.7% of kept) | 212/214 (99.1%) |
| Literary | 211 (14.3%) | 207 (14.3% of kept) | 207/211 (98.1%) |
| Letter | 188 (12.7%) | 187 (13.0% of kept) | 187/188 (99.5%) |
| Lexical | 165 (11.2%) | 147 (10.2% of kept) | 147/165 (89.1%) |
| Medical | 144 (9.7%) | 144 (10.0% of kept) | 144/144 (100.0%) |
| (unlabeled) | 37 (2.5%) | 37 (2.6% of kept) | 37/37 (100.0%) |
| Prayer / incantation | 25 (1.7%) | 25 (1.7% of kept) | 25/25 (100.0%) |
| Legal | 24 (1.6%) | 24 (1.7% of kept) | 24/24 (100.0%) |
| Other | 10 (0.7%) | 10 (0.7% of kept) | 10/10 (100.0%) |
| **all** | **1479** | **1444** | **1444/1479 (97.6%)** |

### lenient: period

| slice | v3-r1 arm S (1479) | kept | keep vs S |
|---|---:|---:|---:|
| Old Babylonian | 791 (53.5%) | 771 (53.4% of kept) | 771/791 (97.5%) |
| Neo-Assyrian | 236 (16.0%) | 232 (16.1% of kept) | 232/236 (98.3%) |
| Ur III | 184 (12.4%) | 180 (12.5% of kept) | 180/184 (97.8%) |
| unknown | 51 (3.4%) | 51 (3.5% of kept) | 51/51 (100.0%) |
| Old Assyrian | 40 (2.7%) | 39 (2.7% of kept) | 39/40 (97.5%) |
| Old Akkadian | 37 (2.5%) | 36 (2.5% of kept) | 36/37 (97.3%) |
| Neo-Babylonian | 36 (2.4%) | 32 (2.2% of kept) | 32/36 (88.9%) |
| Middle Babylonian | 29 (2.0%) | 29 (2.0% of kept) | 29/29 (100.0%) |
| Early Old Babylonian | 27 (1.8%) | 27 (1.9% of kept) | 27/27 (100.0%) |
| Lagash II | 16 (1.1%) | 16 (1.1% of kept) | 16/16 (100.0%) |
| Middle Assyrian | 13 (0.9%) | 13 (0.9% of kept) | 13/13 (100.0%) |
| Achaemenid | 10 (0.7%) | 9 (0.6% of kept) | 9/10 (90.0%) |
| ED IIIb | 8 (0.5%) | 8 (0.6% of kept) | 8/8 (100.0%) |
| ED I-II | 1 (0.1%) | 1 (0.1% of kept) | 1/1 (100.0%) |
| **all** | **1479** | **1444** | **1444/1479 (97.6%)** |

## strict: rejects from the 1,479 by reason

| tag | n |
|---|---:|
| `gloss_unlicensed` | 353 |
| `copy_through` | 24 |
| `common_noun_as_pn` | 11 |
| `invented` | 3 |

Administrative share of arm S was 461/1479 (31.2%); of the strict keep set it is 383/1099 (34.8%).

### strict: genre

| slice | v3-r1 arm S (1479) | kept | keep vs S |
|---|---:|---:|---:|
| Administrative | 461 (31.2%) | 383 (34.8% of kept) | 383/461 (83.1%) |
| Royal / official | 214 (14.5%) | 158 (14.4% of kept) | 158/214 (73.8%) |
| Literary | 211 (14.3%) | 161 (14.6% of kept) | 161/211 (76.3%) |
| Letter | 188 (12.7%) | 130 (11.8% of kept) | 130/188 (69.1%) |
| Lexical | 165 (11.2%) | 109 (9.9% of kept) | 109/165 (66.1%) |
| Medical | 144 (9.7%) | 88 (8.0% of kept) | 88/144 (61.1%) |
| (unlabeled) | 37 (2.5%) | 26 (2.4% of kept) | 26/37 (70.3%) |
| Prayer / incantation | 25 (1.7%) | 15 (1.4% of kept) | 15/25 (60.0%) |
| Legal | 24 (1.6%) | 20 (1.8% of kept) | 20/24 (83.3%) |
| Other | 10 (0.7%) | 9 (0.8% of kept) | 9/10 (90.0%) |
| **all** | **1479** | **1099** | **1099/1479 (74.3%)** |

### strict: period

| slice | v3-r1 arm S (1479) | kept | keep vs S |
|---|---:|---:|---:|
| Old Babylonian | 791 (53.5%) | 607 (55.2% of kept) | 607/791 (76.7%) |
| Neo-Assyrian | 236 (16.0%) | 160 (14.6% of kept) | 160/236 (67.8%) |
| Ur III | 184 (12.4%) | 140 (12.7% of kept) | 140/184 (76.1%) |
| unknown | 51 (3.4%) | 34 (3.1% of kept) | 34/51 (66.7%) |
| Old Assyrian | 40 (2.7%) | 21 (1.9% of kept) | 21/40 (52.5%) |
| Old Akkadian | 37 (2.5%) | 31 (2.8% of kept) | 31/37 (83.8%) |
| Neo-Babylonian | 36 (2.4%) | 28 (2.5% of kept) | 28/36 (77.8%) |
| Middle Babylonian | 29 (2.0%) | 24 (2.2% of kept) | 24/29 (82.8%) |
| Early Old Babylonian | 27 (1.8%) | 21 (1.9% of kept) | 21/27 (77.8%) |
| Lagash II | 16 (1.1%) | 12 (1.1% of kept) | 12/16 (75.0%) |
| Middle Assyrian | 13 (0.9%) | 7 (0.6% of kept) | 7/13 (53.8%) |
| Achaemenid | 10 (0.7%) | 7 (0.6% of kept) | 7/10 (70.0%) |
| ED IIIb | 8 (0.5%) | 7 (0.6% of kept) | 7/8 (87.5%) |
| ED I-II | 1 (0.1%) | 0 (0.0% of kept) | 0/1 (0.0%) |
| **all** | **1479** | **1099** | **1099/1479 (74.3%)** |

## 10 random copy_through rejects after the tightening (seed 42, from lenient newly-rejected)

1. `P333144:2` — Lexical / Old Babylonian  
   ATF: `birbirx(NE) bi-ir-bi-ir NE# [...]`  
   EN: birbir (tree)  
   fails: `['copy_through:birbir']`
   judgment: **RIGHT** — untranslated lexical stem; “tree” is only a partial gloss.

2. `P128501:1` — Administrative / Ur III  
   ATF: `2(ban2) kasz dida sag10 szar3`  
   EN: 2 ban2 of fine-quality dida beer, šar3  
   fails: `['copy_through:dida,šar3']`
   judgment: **MOSTLY RIGHT** — leftover šar3 is untranslated; dida is a conventional beer loanword, so the reject is slightly harsh but justified by šar3.

3. `P228500:9` — Lexical / Old Babylonian  
   ATF: `[...] szinig#-dili`  
   EN: ... a single šinigdili  
   fails: `['copy_through:šinigdili']`
   judgment: **RIGHT** — šinig (tamarisk) + dili (single) left as a copied compound, even though “single” already renders dili.

4. `P480793:10` — Official or display / Achaemenid  
   ATF: `sz#-i-y-a#-t : v-i-n-a-h-y : a-d-t-i-y : a-z-d-a : b-v-`  
   EN: šiyat (means): vinahyu. adtiy (means): azda.  
   fails: `['copy_through:šiyat,adtiy,azda']`
   judgment: **RIGHT** — Old Persian forms copied through with “means,” not translated.

5. `P227886:58` — Lexical / Old Babylonian  
   ATF: `i3-du8-en-nu-uj3#-ja2`  
   EN: i3-du8-en-nu-uŋ3  
   fails: `['copy_through:i3-du8-en-nu-u']`
   judgment: **RIGHT** — almost-untranslated ATF.

6. `P279013:15` — Literary / Old Babylonian  
   ATF: `[mu]-szid-bi 1(gesz2) 2(u)-am3`  
   EN: its mušid: 80;  
   fails: `['copy_through:mušid']`
   judgment: **RIGHT** — mu-šid “its count” left untranslated; 80 is fine.

7. `P357555:18` — Letter / Old Assyrian  
   ATF: `e-ru-ba-tum`  
   EN: Erubatum,  
   fails: `['copy_through:Erubatum', 'common_noun_as_pn:Erubatum']`
   judgment: **RIGHT as common-noun-as-PN** — e-ru-ba-tum is the festival erubatum, capitalized as if a personal name.

8. `P229800:8` — Lexical / Old Babylonian  
   ATF: `gesz nimbar-al#-[...]-ga`  
   EN: The nimbar tree of ...  
   fails: `['copy_through:nimbar']`
   judgment: **RIGHT** — gišnimbar (date palm) left as nimbar next to “tree.”

9. `P365385:31` — lexical / Neo-Assyrian  
   ATF: `sa sumugx(UM) e-ri-im-mu`  
   EN: sa-sumug (means) erimmu.  
   fails: `['copy_through:sa-sumug']`
   judgment: **RIGHT** — lexical copy-through of the Sumerian form (and the Akkadian erimmu).

10. `P270740:11` — Administrative / Old Babylonian  
   ATF: `_4(disz) sila3 szuku_ 4(disz) sza-ki-ki`  
   EN: 4 sila3 ration, 4 šakiki  
   fails: `['copy_through:šakiki']`
   judgment: **BORDERLINE** — could be an unmarked PN (same family as Zikanim) or an untranslated commodity; relaxed glossary also has sakīku “silt,” which the hyphenated form missed. Remaining false-positive risk if it is a name.

## 10 random strict-mode gloss rejects (seed 42, gloss_unlicensed, not also copy_through)

1. `P357284:2` — Literary / Old Babylonian  
   ATF: `[...]-du3-en // [...]`  
   EN: ... I built ...  
   fails: `['gloss_unlicensed']`
   gloss: unlicensed=['built'] ratio=1.0
   judgment: **WRONG** — du3 is “to build”; “I built” is the right verb. allowed_n=0 (damaged form, no glossary hit). The ratio limb fires on a one-content-word line.

2. `P285129:5` — Medical / unknown  
   ATF: `tu-tap-pa-[as, ...]`  
   EN: you will smear  
   fails: `['gloss_unlicensed']`
   gloss: unlicensed=['smear'] ratio=1.0
   judgment: **WRONG** — tu-tap-pa-[aṣ] is the medical verb “you smear.” Same allowed_n=0 / short-line ratio issue.

3. `P393923:519` — Official or display / Middle Assyrian  
   ATF: `u3 _bad3_-szu la-a ra-s,a-pi i-na muh-hi`  
   EN: and its wall is not strong on top of it  
   fails: `['gloss_unlicensed']`
   gloss: unlicensed=['strong'] ratio=0.5
   judgment: **RIGHT** — bad3 “wall” is fine, but raṣāpu is “to erect/build,” not “strong.”

4. `P338786:16` — Letter / Old Babylonian  
   ATF: `a#-ka-al _u4 5(disz)-kam_ i-na kap-ri-im sza-ti`  
   EN: I will eat on the fifth day at that banquet.  
   fails: `['gloss_unlicensed']`
   gloss: unlicensed=['banquet'] ratio=0.5
   judgment: **RIGHT** — kapru is “village,” not “banquet.”

5. `P270738:9` — Administrative / Old Babylonian  
   ATF: `_{gesz}ma2_ sza-li-im#-ta-[am]`  
   EN: a boat of peace  
   fails: `['gloss_unlicensed']`
   gloss: unlicensed=['peace'] ratio=0.5
   judgment: **BORDERLINE** — šalimtam is “intact / safe / complete”; “peace” is related but not the usual sense. Fair as a strict-mode flag.

6. `P247799:5` — Lexical / Old Babylonian  
   ATF: `lu2 ma2-u5`  
   EN: the barge-man  
   fails: `['gloss_unlicensed']`
   gloss: unlicensed=['barge-man'] ratio=1.0
   judgment: **WRONG** — lu2 ma2-u5 is “barge-man / boatman.” A good compound gloss, rejected because the hyphenated English is not in the official list.

7. `P270698:5` — — / unknown  
   ATF: `_5(disz) mu-an-na_-ti a-bi-a`  
   EN: 5 years, my father  
   fails: `['gloss_unlicensed']`
   gloss: unlicensed=['years'] ratio=1.0
   judgment: **WRONG** — mu-an-na is “year.” “5 years, my father” is exact; the gloss list missed the underscored writing.

8. `P285191:8` — Medical / unknown  
   ATF: `[...] _numun_ {u2}qut-ri _numun gada_`  
   EN: ... seed of qutru-plant, seed of linen  
   fails: `['gloss_unlicensed']`
   gloss: unlicensed=['qutru-plant'] ratio=0.5
   judgment: **BORDERLINE** — {u2}qut-ri is on the ATF; keeping qutru-plant as a loan is reasonable. linen for gada is good.

9. `P268989:50` — Official or display / Early Old Babylonian  
   ATF: `en nam tar-re-gin7`  
   EN: like the lord who determines fate,  
   fails: `['gloss_unlicensed']`
   gloss: unlicensed=['determines'] ratio=0.5
   judgment: **WRONG** — nam tar is “to determine fate.” “the lord who determines fate” is the standard rendering.

10. `Q002042:18` — Royal Inscription / Old Babylonian  
   ATF: `ki-bi bi2-in-gi4-a`  
   EN: he restored it there  
   fails: `['gloss_unlicensed']`
   gloss: unlicensed=['restored'] ratio=1.0
   judgment: **WRONG** — ki-bi … gi4 is the idiom “to restore (to its place).” A standard translation, rejected by the ratio limb on a short line.

## Overlap with the 30-line spot-check panel (ctrl hyps)

Category (c) = 16 real content errors; (b) = 3 good paraphrases; (a) = 5 formatting.

| mode | (c) hard-dropped | (c) gloss-over | (c) either | (b) hard-dropped | (b) gloss-over | (a) hard-dropped |
|---|---:|---:|---:|---:|---:|---:|
| **lenient** | 12/16 (75.0%) | 9/16 (56.2%) | 13/16 (81.2%) | 1/3 (33.3%) | 2/3 (66.7%) | 1/5 (20.0%) |
| **strict** | 13/16 (81.2%) | 9/16 (56.2%) | 13/16 (81.2%) | 2/3 (66.7%) | 2/3 (66.7%) | 1/5 (20.0%) |

### Panel detail, lenient

- **fair:0591** (c): hard:invented:speech,continually,aches,lemma_missing:lip; gloss:speech,continually,aches
- **fair:0883** (c): kept, not flagged
- **fair:0850** (c): hard:copy_through:-angurum
- **fair:0849** (c): gloss:destroyed
- **fair:0473** (c): hard:copy_through:Meluletum,common_noun_as_pn:Meluletum
- **fair:1327** (b): kept, not flagged
- **fair:0409** (c): hard:lemma_missing:cord,flax,omen_template
- **fair:1049** (c): hard:invented:coarse,flour; gloss:coarse,flour
- **fair:1028** (c): kept, not flagged
- **fair:0230** (c): hard:names:Subtotal,invented:subtotal; gloss:subtotal
- **fair:0243** (c): hard:numbers:one,units:missing:sila3,invented:substitute,stewed,lemma_missing:bread,soup; gloss:substitute,lamb,stewed,lamb
- **fair:0239** (c): hard:numbers:1,numbers:0,numbers:01,numbers:05; gloss:ditto,double-hour
- **fair:0262** (b): gloss:silversmiths
- **fair:0265** (c): hard:invented:subtotal; gloss:subtotal,a-laborers
- **fair:0576** (c): hard:lemma_missing:boxwood; gloss:tamarisk
- **fair:0534** (c): hard:names:Gigur,copy_through:Gigur,innuda,gigur,pisag,common_noun_as_pn:Gigur
- **fair:0377** (c): hard:names:Abzu,lemma_missing:father; gloss:abzu
- **fair:0460** (b): hard:lemma_missing:food,basin; gloss:possessions
- **fair:0949** (c): kept, not flagged

### Panel detail, strict

- **fair:0591** (c): hard:invented:speech,continually,aches,lemma_missing:lip,gloss_unlicensed; gloss:speech,continually,aches
- **fair:0883** (c): kept, not flagged
- **fair:0850** (c): hard:copy_through:-angurum
- **fair:0849** (c): hard:gloss_unlicensed; gloss:destroyed
- **fair:0473** (c): hard:copy_through:Meluletum,common_noun_as_pn:Meluletum
- **fair:1327** (b): kept, not flagged
- **fair:0409** (c): hard:lemma_missing:cord,flax,omen_template
- **fair:1049** (c): hard:invented:coarse,flour,gloss_unlicensed; gloss:coarse,flour
- **fair:1028** (c): kept, not flagged
- **fair:0230** (c): hard:names:Subtotal,invented:subtotal,gloss_unlicensed; gloss:subtotal
- **fair:0243** (c): hard:numbers:one,units:missing:sila3,invented:substitute,stewed,lemma_missing:bread,soup; gloss:substitute,lamb,stewed,lamb
- **fair:0239** (c): hard:numbers:1,numbers:0,numbers:01,numbers:05; gloss:ditto,double-hour
- **fair:0262** (b): hard:gloss_unlicensed; gloss:silversmiths
- **fair:0265** (c): hard:invented:subtotal,gloss_unlicensed; gloss:subtotal,a-laborers
- **fair:0576** (c): hard:lemma_missing:boxwood,gloss_unlicensed; gloss:tamarisk
- **fair:0534** (c): hard:names:Gigur,copy_through:Gigur,innuda,gigur,pisag,common_noun_as_pn:Gigur
- **fair:0377** (c): hard:names:Abzu,lemma_missing:father,gloss_unlicensed; gloss:abzu
- **fair:0460** (b): hard:lemma_missing:food,basin,gloss_unlicensed; gloss:possessions
- **fair:0949** (c): kept, not flagged

**fair:0243** (stewed lamb):
- lenient: ok=False fails=`['numbers:one', 'units:missing:sila3', 'invented:substitute,stewed', 'lemma_missing:bread,soup', 'invented:substitute']` unlicensed=['substitute', 'lamb', 'stewed', 'lamb'] ratio=1.0
- strict: ok=False fails=`['numbers:one', 'units:missing:sila3', 'invented:substitute,stewed', 'lemma_missing:bread,soup', 'invented:substitute', 'gloss_unlicensed']` unlicensed=['substitute', 'lamb', 'stewed', 'lamb'] ratio=1.0

**fair:1327** (Etemenniguru expansion):
- lenient: ok=True fails=`[]` unlicensed=[] ratio=0.0
- strict: ok=True fails=`[]` unlicensed=[] ratio=0.0

**fair:0262** (silversmiths / goldsmiths):
- lenient: ok=True fails=`[]` unlicensed=['silversmiths'] ratio=1.0
- strict: ok=False fails=`['gloss_unlicensed']` unlicensed=['silversmiths'] ratio=1.0


## Hand-check summary

Of the 10 random post-fix copy_through rejects: **7 right**, **1 mostly right** (dida/šar3), **1 right as common-noun-as-PN** (Erubatum = festival), **1 borderline** (šakiki, possible unmarked name). The tightening removed the earlier name/month/English-ATF false positives; remaining copy_through flags are mostly real leftovers, with some residual risk on unmarked names.

Of the 10 random strict-mode gloss rejects: **2 right** (strong ≠ raṣāpu; banquet ≠ kapru), **2 borderline**, **6 wrong**. The wrong ones are mostly good short translations (build, smear, barge-man, years, determine fate, restore) where the official gloss was missed or `allowed_n=0` on a damaged line, and the **ratio ≥ 0.40** limb then rejects a single content word. Strict mode is doing what it was asked to do for chrF — it is harsher on paraphrases — but the ratio limb on 1–2-word lines is noisy. Worth revisiting (e.g. require `n_unlicensed >= 2`, or do not apply the ratio limb when `n_content <= 2` or `allowed_n == 0`) before promoting strict mode to a large training cut.

Strict mode also **raises** the administrative share (451/1444 = 31.2% lenient → 383/1099 = 34.8% strict) because literary, medical, and lexical lines drop harder.

## Files

- `runs/loop-pilot/design-v3/filter_v3.py`
- `runs/loop-pilot/design-v3/test_filter_v3.py`
- `runs/loop-pilot/v3-r1/run_filter_v3.py`
- `runs/loop-pilot/v3-r1/filter_v3_report.json`

Glossary: `lemma_support.py` / `runs/blindcrack/lexicon/oracc_lines.jsonl.gz` (ORACC BY-SA; epsd2/literary and eBL excluded). Not ETCSL, not eBL.
