# Filter v3 gloss expansion and reverse check

Written 2026-11-23 03:15 EST. CPU only. Clean sources only.

## Gloss list size (clean sources)

- Official ORACC/ePSD-style English lemmas (function words dropped): **9670**
- After curated synonyms + WordNet on those lemmas: **21287**
- After mined per-sign English from clean BY-SA pairs (count≥5, PMI≥2.0): **30684** unique lemmas
- Flat clean-human vocab (lemmatized content words): **49004**
- Pairs used: **334966** / 400253 (excluded {'empty_keys_or_words': 9809, 'synth': 44308, 'etcsl': 11170})

## Keep counts on the 1,479 arm-S lines

| policy | kept of 1479 | filter-ok of 1479 | improve-pool filter-ok |
|---|---:|---:|---:|
| `lenient` | 1448 (97.9%) | 1448/1479 (97.9%) | 3279/4925 (66.6%) |
| `strict_per_sign` | 1302 (88.0%) | 1302/1479 (88.0%) | 3012/4925 (61.2%) |
| `strict_per_sign_min3` | 1440 (97.4%) | 1440/1479 (97.4%) | 3260/4925 (66.2%) |
| `strict_corpus` | 1440 (97.4%) | 1440/1479 (97.4%) | 3258/4925 (66.2%) |
| `strict_reverse` | 1238 (83.7%) | 1238/1479 (83.7%) | 2802/4925 (56.9%) |

### lenient: genre keep rate (arm S)

| slice | arm S | kept | keep vs S |
|---|---:|---:|---|
| Administrative | 461 | 451 | 451/461 (97.8%) |
| Royal / official | 214 | 212 | 212/214 (99.1%) |
| Literary | 211 | 207 | 207/211 (98.1%) |
| Letter | 188 | 187 | 187/188 (99.5%) |
| Lexical | 165 | 151 | 151/165 (91.5%) |
| Medical | 144 | 144 | 144/144 (100.0%) |
| (unlabeled) | 37 | 37 | 37/37 (100.0%) |
| Prayer / incantation | 25 | 25 | 25/25 (100.0%) |
| Legal | 24 | 24 | 24/24 (100.0%) |
| Other | 10 | 10 | 10/10 (100.0%) |

### lenient: period keep rate (arm S)

| slice | arm S | kept | keep vs S |
|---|---:|---:|---|
| Old Babylonian | 791 | 772 | 772/791 (97.6%) |
| Neo-Assyrian | 236 | 232 | 232/236 (98.3%) |
| Ur III | 184 | 180 | 180/184 (97.8%) |
| unknown | 51 | 51 | 51/51 (100.0%) |
| Old Assyrian | 40 | 39 | 39/40 (97.5%) |
| Old Akkadian | 37 | 36 | 36/37 (97.3%) |
| Neo-Babylonian | 36 | 35 | 35/36 (97.2%) |
| Middle Babylonian | 29 | 29 | 29/29 (100.0%) |
| Early Old Babylonian | 27 | 27 | 27/27 (100.0%) |
| Lagash II | 16 | 16 | 16/16 (100.0%) |
| Middle Assyrian | 13 | 13 | 13/13 (100.0%) |
| Achaemenid | 10 | 9 | 9/10 (90.0%) |
| ED IIIb | 8 | 8 | 8/8 (100.0%) |
| ED I-II | 1 | 1 | 1/1 (100.0%) |

Administrative share of kept: 451/1448 (31.1%) (arm S admin 461/1479 (31.2%)).

Reject tags (arm S, not filter-ok):
- `copy_through`: 19
- `common_noun_as_pn`: 11
- `invented`: 3

### strict_per_sign: genre keep rate (arm S)

| slice | arm S | kept | keep vs S |
|---|---:|---:|---|
| Administrative | 461 | 425 | 425/461 (92.2%) |
| Royal / official | 214 | 186 | 186/214 (86.9%) |
| Literary | 211 | 192 | 192/211 (91.0%) |
| Letter | 188 | 157 | 157/188 (83.5%) |
| Lexical | 165 | 130 | 130/165 (78.8%) |
| Medical | 144 | 133 | 133/144 (92.4%) |
| (unlabeled) | 37 | 29 | 29/37 (78.4%) |
| Prayer / incantation | 25 | 20 | 20/25 (80.0%) |
| Legal | 24 | 21 | 21/24 (87.5%) |
| Other | 10 | 9 | 9/10 (90.0%) |

### strict_per_sign: period keep rate (arm S)

| slice | arm S | kept | keep vs S |
|---|---:|---:|---|
| Old Babylonian | 791 | 695 | 695/791 (87.9%) |
| Neo-Assyrian | 236 | 216 | 216/236 (91.5%) |
| Ur III | 184 | 163 | 163/184 (88.6%) |
| unknown | 51 | 42 | 42/51 (82.4%) |
| Old Assyrian | 40 | 30 | 30/40 (75.0%) |
| Old Akkadian | 37 | 32 | 32/37 (86.5%) |
| Neo-Babylonian | 36 | 34 | 34/36 (94.4%) |
| Middle Babylonian | 29 | 26 | 26/29 (89.7%) |
| Early Old Babylonian | 27 | 24 | 24/27 (88.9%) |
| Lagash II | 16 | 15 | 15/16 (93.8%) |
| Middle Assyrian | 13 | 10 | 10/13 (76.9%) |
| Achaemenid | 10 | 7 | 7/10 (70.0%) |
| ED IIIb | 8 | 8 | 8/8 (100.0%) |
| ED I-II | 1 | 0 | 0/1 (0.0%) |

Administrative share of kept: 425/1302 (32.6%) (arm S admin 461/1479 (31.2%)).

Reject tags (arm S, not filter-ok):
- `gloss_unlicensed`: 146
- `copy_through`: 19
- `common_noun_as_pn`: 11
- `invented`: 3

### strict_per_sign_min3: genre keep rate (arm S)

| slice | arm S | kept | keep vs S |
|---|---:|---:|---|
| Administrative | 461 | 448 | 448/461 (97.2%) |
| Royal / official | 214 | 211 | 211/214 (98.6%) |
| Literary | 211 | 206 | 206/211 (97.6%) |
| Letter | 188 | 187 | 187/188 (99.5%) |
| Lexical | 165 | 150 | 150/165 (90.9%) |
| Medical | 144 | 143 | 143/144 (99.3%) |
| (unlabeled) | 37 | 36 | 36/37 (97.3%) |
| Prayer / incantation | 25 | 25 | 25/25 (100.0%) |
| Legal | 24 | 24 | 24/24 (100.0%) |
| Other | 10 | 10 | 10/10 (100.0%) |

### strict_per_sign_min3: period keep rate (arm S)

| slice | arm S | kept | keep vs S |
|---|---:|---:|---|
| Old Babylonian | 791 | 768 | 768/791 (97.1%) |
| Neo-Assyrian | 236 | 231 | 231/236 (97.9%) |
| Ur III | 184 | 179 | 179/184 (97.3%) |
| unknown | 51 | 51 | 51/51 (100.0%) |
| Old Assyrian | 40 | 39 | 39/40 (97.5%) |
| Old Akkadian | 37 | 36 | 36/37 (97.3%) |
| Neo-Babylonian | 36 | 35 | 35/36 (97.2%) |
| Middle Babylonian | 29 | 28 | 28/29 (96.6%) |
| Early Old Babylonian | 27 | 26 | 26/27 (96.3%) |
| Lagash II | 16 | 16 | 16/16 (100.0%) |
| Middle Assyrian | 13 | 13 | 13/13 (100.0%) |
| Achaemenid | 10 | 9 | 9/10 (90.0%) |
| ED IIIb | 8 | 8 | 8/8 (100.0%) |
| ED I-II | 1 | 1 | 1/1 (100.0%) |

Administrative share of kept: 448/1440 (31.1%) (arm S admin 461/1479 (31.2%)).

Reject tags (arm S, not filter-ok):
- `copy_through`: 19
- `common_noun_as_pn`: 11
- `gloss_unlicensed`: 8
- `invented`: 3

### strict_corpus: genre keep rate (arm S)

| slice | arm S | kept | keep vs S |
|---|---:|---:|---|
| Administrative | 461 | 450 | 450/461 (97.6%) |
| Royal / official | 214 | 209 | 209/214 (97.7%) |
| Literary | 211 | 207 | 207/211 (98.1%) |
| Letter | 188 | 186 | 186/188 (98.9%) |
| Lexical | 165 | 150 | 150/165 (90.9%) |
| Medical | 144 | 144 | 144/144 (100.0%) |
| (unlabeled) | 37 | 37 | 37/37 (100.0%) |
| Prayer / incantation | 25 | 25 | 25/25 (100.0%) |
| Legal | 24 | 24 | 24/24 (100.0%) |
| Other | 10 | 8 | 8/10 (80.0%) |

### strict_corpus: period keep rate (arm S)

| slice | arm S | kept | keep vs S |
|---|---:|---:|---|
| Old Babylonian | 791 | 768 | 768/791 (97.1%) |
| Neo-Assyrian | 236 | 230 | 230/236 (97.5%) |
| Ur III | 184 | 180 | 180/184 (97.8%) |
| unknown | 51 | 51 | 51/51 (100.0%) |
| Old Assyrian | 40 | 39 | 39/40 (97.5%) |
| Old Akkadian | 37 | 36 | 36/37 (97.3%) |
| Neo-Babylonian | 36 | 35 | 35/36 (97.2%) |
| Middle Babylonian | 29 | 29 | 29/29 (100.0%) |
| Early Old Babylonian | 27 | 27 | 27/27 (100.0%) |
| Lagash II | 16 | 16 | 16/16 (100.0%) |
| Middle Assyrian | 13 | 13 | 13/13 (100.0%) |
| Achaemenid | 10 | 7 | 7/10 (70.0%) |
| ED IIIb | 8 | 8 | 8/8 (100.0%) |
| ED I-II | 1 | 1 | 1/1 (100.0%) |

Administrative share of kept: 450/1440 (31.2%) (arm S admin 461/1479 (31.2%)).

Reject tags (arm S, not filter-ok):
- `copy_through`: 19
- `common_noun_as_pn`: 11
- `gloss_unlicensed`: 8
- `invented`: 3

### strict_reverse: genre keep rate (arm S)

| slice | arm S | kept | keep vs S |
|---|---:|---:|---|
| Administrative | 461 | 409 | 409/461 (88.7%) |
| Royal / official | 214 | 181 | 181/214 (84.6%) |
| Literary | 211 | 175 | 175/211 (82.9%) |
| Letter | 188 | 148 | 148/188 (78.7%) |
| Lexical | 165 | 132 | 132/165 (80.0%) |
| Medical | 144 | 119 | 119/144 (82.6%) |
| (unlabeled) | 37 | 29 | 29/37 (78.4%) |
| Prayer / incantation | 25 | 18 | 18/25 (72.0%) |
| Legal | 24 | 18 | 18/24 (75.0%) |
| Other | 10 | 9 | 9/10 (90.0%) |

### strict_reverse: period keep rate (arm S)

| slice | arm S | kept | keep vs S |
|---|---:|---:|---|
| Old Babylonian | 791 | 661 | 661/791 (83.6%) |
| Neo-Assyrian | 236 | 200 | 200/236 (84.7%) |
| Ur III | 184 | 155 | 155/184 (84.2%) |
| unknown | 51 | 37 | 37/51 (72.5%) |
| Old Assyrian | 40 | 30 | 30/40 (75.0%) |
| Old Akkadian | 37 | 32 | 32/37 (86.5%) |
| Neo-Babylonian | 36 | 32 | 32/36 (88.9%) |
| Middle Babylonian | 29 | 25 | 25/29 (86.2%) |
| Early Old Babylonian | 27 | 24 | 24/27 (88.9%) |
| Lagash II | 16 | 15 | 15/16 (93.8%) |
| Middle Assyrian | 13 | 10 | 10/13 (76.9%) |
| Achaemenid | 10 | 9 | 9/10 (90.0%) |
| ED IIIb | 8 | 8 | 8/8 (100.0%) |
| ED I-II | 1 | 0 | 0/1 (0.0%) |

Administrative share of kept: 409/1238 (33.0%) (arm S admin 461/1479 (31.2%)).

Reject tags (arm S, not filter-ok):
- `gloss_unlicensed`: 210
- `copy_through`: 19
- `common_noun_as_pn`: 11
- `invented`: 3

## 30-line SPOTCHECK panel (ctrl hyps)

Caught = hard reject OR the named gloss threshold. Cat (c) = 16 real errors; (b) = 3 good paraphrases; (a) = 5 formatting.

| check | real errors (c) | paraphrases (b) flagged | formatting (a) |
|---|---|---|---|
| hard rejects only | 12/16 | 1/3 | 1/5 |
| hard + forward per-sign | 14/16 | 1/3 | 1/5 |
| hard + forward, ratio min 3 | 12/16 | 1/3 | 1/5 |
| hard + corpus vocab | 12/16 | 1/3 | 1/5 |
| hard + reverse n≥1 | 14/16 | 1/3 | 1/5 |

Panel detail:

- `fair:0591` (c) hard_ok=False fails=['invented:speech,continually,aches', 'lemma_missing:lip']
  fwd unlic=['speech', 'continually', 'aches'] over=True min3=True; rev unlic=['speech: expected du11|ka-u2|kau2|pu-u2|puu2|at-me2-e', 'continually: expected mu2|mu2-mu2|mu2mu2|e-tam2-da|etam2da|gu3-gu3-a', 'aches: expected adu|buul|szin|ulti|maadu|puran'] over=True; corpus unlic=[] over=False
- `fair:0883` (c) hard_ok=True fails=[]
  fwd unlic=['old'] over=True min3=False; rev unlic=['old: expected mu-1|mu-2|mu-3|mu-4|mu-5|mu-6', 'break: expected zi2|bur3|gir8|gud9|dar|dur'] over=True; corpus unlic=[] over=False
- `fair:0657` (d) hard_ok=False fails=['lemma_missing:house']
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0864` (d) hard_ok=False fails=['lemma_missing:measure']
  fwd unlic=['want'] over=True min3=False; rev unlic=['want: expected ma-ku-u2|makuu2|u2-tar-ri-szu-nu|u2tarriszunu|makû|maku'] over=True; corpus unlic=[] over=False
- `fair:0850` (c) hard_ok=False fails=['copy_through:-angurum']
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0673` (a) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0812` (a) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0823` (a) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0849` (c) hard_ok=True fails=[]
  fwd unlic=['destroyed'] over=True min3=False; rev unlic=['destroyed: expected zah2|zer3|a-pul2|apul2|gul|iph'] over=True; corpus unlic=[] over=False
- `fair:1427` (d) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:1523` (d) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0473` (c) hard_ok=False fails=['copy_through:Meluletum', 'common_noun_as_pn:Meluletum']
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0316` (d) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:1327` (b) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0409` (c) hard_ok=False fails=['lemma_missing:cord,flax', 'omen_template']
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:1204` (d) hard_ok=False fails=['lemma_missing:flour,find']
  fwd unlic=['smite'] over=True min3=False; rev unlic=['smite: expected tu10|tu11|mu-e-tu10|muetu10|u2-ra-sib|u2rasib'] over=True; corpus unlic=[] over=False
- `fair:1049` (c) hard_ok=False fails=['invented:coarse,flour']
  fwd unlic=['coarse', 'flour'] over=True min3=True; rev unlic=['coarse: expected zi3-kum|zi3kum|zid2-gu|zid2gu|za-ri2-in|zari2in', 'flour: expected zi3|esz2|zi3@t|zi3t|zid2|esze2'] over=True; corpus unlic=[] over=False
- `fair:1028` (c) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0230` (c) hard_ok=False fails=['names:Subtotal', 'invented:subtotal']
  fwd unlic=['subtotal'] over=True min3=False; rev unlic=['subtotal: expected kel3|kil3|kin4|nin3|ga-ar3|gaar3'] over=True; corpus unlic=[] over=False
  ATF: `%sux 0.0.1 {d}nanna-kam`
  ctrl: Subtotal: 0;01, of Nanna.
- `fair:0243` (c) hard_ok=False fails=['numbers:one', 'units:missing:sila3', 'invented:substitute,stewed', 'lemma_missing:bread,soup', 'invented:substitute']
  fwd unlic=['substitute', 'lamb', 'stewed', 'lamb'] over=True min3=True; rev unlic=['substitute: expected a2-bal|a2bal|a2-bal-e|a2bale|pu-u2-hi|pu-u2-hu', 'lamb: expected u8|si6|u10|u8-e|u8e|ua2', 'lamb: expected u8|si6|u10|u8-e|u8e|ua2'] over=True; corpus unlic=[] over=False
  ATF: `%sux ½ sila3 inda3 ½ sila3 tu7`
  ctrl: substitute: one lamb, one stewed lamb,
- `fair:0239` (c) hard_ok=False fails=['numbers:1', 'numbers:0', 'numbers:01', 'numbers:05', 'invented:ditto,double-hour', 'invented:ditto']
  fwd unlic=['ditto', 'double-hour'] over=True min3=True; rev unlic=['ditto: expected 02-isz|02isz|min-szu2|minszu2|szu-bi-asz-am3|szubiaszam3', 'double-hour: expected minkila2|mulmesgam3|mulmesgam3a|minane|minqaq|mulmes'] over=True; corpus unlic=[] over=False
- `fair:0262` (b) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0265` (c) hard_ok=False fails=['invented:subtotal']
  fwd unlic=['subtotal', 'a-laborers'] over=True min3=True; rev unlic=['subtotal: expected kel3|kil3|kin4|nin3|ga-ar3|gaar3'] over=True; corpus unlic=[] over=False
- `fair:0148` (a) hard_ok=False fails=['numbers:6', 'langtag:%šu']
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0576` (c) hard_ok=False fails=['lemma_missing:boxwood']
  fwd unlic=['tamarisk'] over=True min3=False; rev unlic=['tamarisk: expected szinig-am3|szinig-am6|szinigam3|szinigam6|szinig-gin7|szinig-sze3'] over=True; corpus unlic=[] over=False
- `fair:0534` (c) hard_ok=False fails=['copy_through:Gigur,innuda,gigur,pisag', 'common_noun_as_pn:Gigur']
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0508` (a) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0377` (c) hard_ok=False fails=['names:Abzu', 'lemma_missing:father']
  fwd unlic=['abzu'] over=True min3=False; rev unlic=['abzu: expected a-kalam|akalam|nam-abzu|namabzu'] over=True; corpus unlic=[] over=False
- `fair:0460` (b) hard_ok=False fails=['lemma_missing:food,basin']
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False
- `fair:0949` (c) hard_ok=True fails=[]
  fwd unlic=[] over=False min3=False; rev unlic=[] over=False; corpus unlic=[] over=False

## 10 random strict forward (per-sign) gloss rejects (seed 20261123)

Arm-S lines kept under lenient but rejected by `strict_per_sign` (n=146).

1. `P270691:9` — Legal / Old Babylonian
   ATF: `_a2 mu-a-sze3_`
   EN: for the labor of that year
   fwd: unlic=['labor'] ratio=1.0 n=1
   rev: ['labor: expected a-il2|ail2|bir3|a2-il2|a2il2|eren2'] unmapped=[]
   corpus: []

2. `P247855:307` — Lexical / Old Babylonian
   ATF: `{u2}|ZI&ZI.LAGAB|`
   EN: a type of grass
   fwd: unlic=['type'] ratio=0.5 n=2
   rev: ['type: expected ze2|dī|gl|lh|nr|t,r'] unmapped=[]
   corpus: []

3. `P333149:130` — Lexical / Old Babylonian
   ATF: `gag <([KAK])> ka-ku`
   EN: gag (is a synonym of): weapon.
   fwd: unlic=['synonym'] ratio=0.5 n=2
   rev: ['synonym: expected ba-a-ru3|baaru3|li-sza2-ni|lisza2ni|kit-tab-ri-szu2|kittabriszu2'] unmapped=[]
   corpus: []

4. `P270782:5` — Administrative / Old Babylonian
   ATF: `[...] _sze nig2-ar3-ra_`
   EN: ... barley of the niŋaru-allocation
   fwd: unlic=['aru-allocation'] ratio=1.0 n=1
   rev: ['aru-allocation: expected asza3|irisi2|irisi2ia|irisi2iu|irisi2ium|irisi2iani'] unmapped=[]
   corpus: []

5. `P393923:414` — Official or display / Middle Assyrian
   ATF: `u3 ka-mu-szu-nu i-na ma-har {d}utu _en_-ia`
   EN: and their offerings before Šamaš, my lord,
   fwd: unlic=['offerings'] ratio=1.0 n=1
   rev: ['offerings: expected e11|a-qi2|aqi2|ki-sig3|kisig3|sa-dug4'] unmapped=[]
   corpus: []

6. `P263166:79` — Official or display / Early Old Babylonian
   ATF: `nig2#-[mu10]-us2#-sa2`
   EN: as a marriage gift
   fwd: unlic=['marriage'] ratio=0.5 n=2
   rev: ['marriage: expected aj2-dam|aj2dam|e-mu-tu2|emutu2|dam-u2-ti|dam-u2-tu'] unmapped=[]
   corpus: []

7. `P248028:15` — Letter / Old Babylonian
   ATF: `_4(bur3) 2(esze3) GAN2_ u2-sze-lu-u2`
   EN: They will clear 4 bur3 2 eše3 of field.
   fwd: unlic=['clear'] ratio=1.0 n=1
   rev: ['clear: expected du8|dan3|dan4|dan6|sug4|du8-ma'] unmapped=[]
   corpus: []

8. `P358363:18` — Letter / Old Assyrian
   ATF: `[... _ku3]-babbar_ i-sze2-ep`
   EN: ... he will pay the silver.
   fwd: unlic=['pay'] ratio=1.0 n=1
   rev: ['pay: expected e3-a|e3a|e-la2|ela2|i3-e3|i3e3'] unmapped=[]
   corpus: []

9. `P270790:7` — Administrative / Old Babylonian
   ATF: `_2(u) 2(disz) szu ti-a 2(disz) {lu2}azlag2_`
   EN: 22 received, 2 fullers;
   fwd: unlic=['received'] ratio=0.5 n=2
   rev: ['received: expected ti-u2|tiu2|li-qe2|liqe2|be|ur', 'fullers: expected sa5|su3|de6-a|de6a|sug4|nij2-bar-sur-ra'] unmapped=[]
   corpus: []

10. `P481834:29` — Letter / Old Babylonian
   ATF: `a-na sza at,-ru-du-szu id-di-in-mas`
   EN: he gave it to the one who cursed him
   fwd: unlic=['cursed'] ratio=1.0 n=1
   rev: ['cursed: expected asz2|asz3|as2-se|as2se|asz2-a|asz2a'] unmapped=[]
   corpus: []

## 10 random strict reverse gloss rejects (seed 20261123)

Arm-S lines kept under lenient but rejected by `strict_reverse` (n=210).

1. `P452606:21` — Prayer / Neo-Assyrian
   ATF: `[...] az#-za-ki ki-ma la#-[ar2-di]`
   EN: [...] I stand like a [...]
   fwd: unlic=['stand'] ratio=1.0 n=1
   rev: ['stand: expected su8|dur2|i3-du|i3du|su8-a|su8a'] unmapped=[]
   corpus: []

2. `P270706:12` — Legal / Old Babylonian
   ATF: `u3 a2-gab2-bu-gin7`
   EN: and like the flank
   fwd: unlic=['flank'] ratio=1.0 n=1
   rev: ['flank: expected a-hi-sza2|ahisza2|ahu|a-hi-sza|ahīsza'] unmapped=[]
   corpus: []

3. `P285210:33` — Medical / Neo-Assyrian
   ATF: `u ma-gal _zi-zi-bi {uzu}bun_-szu he-sa-at`
   EN: and his liver is greatly swollen.
   fwd: unlic=[] ratio=0.0 n=3
   rev: ['liver: expected u5|ba3|ur5|bur3|dun3|gir2', 'swollen: expected bir7|eb-t,u2|ebt,u2|e-be2-t,u|e-eb-t,u2|ul'] unmapped=[]
   corpus: []

4. `P240428:10` — Literary / Neo-Assyrian
   ATF: `[...] ina eri-du10 ri-im-ma-[tu2 ...]`
   EN: ... in Eridu, the rejoicing ...
   fwd: unlic=[] ratio=0.0 n=1
   rev: ['rejoicing: expected hul2|sug4|he2-li|he2li|hul2-a|hul2-e'] unmapped=[]
   corpus: []

5. `P297240:9` — Letter / Old Assyrian
   ATF: `a-szar i-ta-pu-lu-ni`
   EN: where they appealed to me,
   fwd: unlic=['appealed'] ratio=1.0 n=1
   rev: ['appealed: expected hilib2|hi-li|hili|in-bu|inbu|a-ra-zu'] unmapped=[]
   corpus: []

6. `P393923:414` — Official or display / Middle Assyrian
   ATF: `u3 ka-mu-szu-nu i-na ma-har {d}utu _en_-ia`
   EN: and their offerings before Šamaš, my lord,
   fwd: unlic=['offerings'] ratio=1.0 n=1
   rev: ['offerings: expected e11|a-qi2|aqi2|ki-sig3|kisig3|sa-dug4'] unmapped=[]
   corpus: []

7. `Q003344:1` — Royal Inscription / Neo-Assyrian
   ATF: `Horned headdress on podium bearing a relief of a stylized tree`
   EN: Horned headdress on a pedestal bearing a relief of a stylized tree.
   fwd: unlic=['pedestal'] ratio=1.0 n=1
   rev: ['pedestal: expected szu-pa2-al|szupa2al|ki-gal-ju10|ki-gal-sze3|kigalju10|kigalsze3'] unmapped=[]
   corpus: []

8. `P252335:5` — Literary / Old Babylonian
   ATF: `{jesz}bansur# ku3 {d}en-lil2-la2-ka muszen (IGI.DU-)x#`
   EN: The bird (looks at) the pure table of Enlil.
   fwd: unlic=['looks'] ratio=0.25 n=4
   rev: ['looks: expected bu-u2|buu2|a-lu-u2|a-nu-u2|aluu2|anuu2'] unmapped=[]
   corpus: []

9. `P285124:7` — Medical / unknown
   ATF: `ina _mud2 erin_ lu ina _i3 erin# hi-hi za-na du3_-usz`
   EN: You make a preparation with either cedar resin or cedar oil.
   fwd: unlic=['preparation'] ratio=0.2 n=5
   rev: ['preparation: expected dida2|kasz-u2-sa|kaszu2sa|te9-er-si2-ti|te9ersi2ti|sza2-as,-bu-tu2'] unmapped=[]
   corpus: []

10. `P520812:2` — Letter / unknown
   ATF: `'m#n szlm`
   EN: ʿAmmi, it is well.
   fwd: unlic=['ammi'] ratio=1.0 n=1
   rev: ['ammi: expected ir3-ra-i-x|ir3raix|am-mi-s,a-du-qa2|ammis,aduqa2|bi-x|bi-x-x'] unmapped=[]
   corpus: []

