#!/usr/bin/env python3
"""Filter v3: stricter hard rejects on top of filter v2, plus a gloss FLAG.

This is a versioned module for loop pseudo-label selection. It wraps filter v2
(numbers, names, invented content, lemma coverage, idioms, doubled gloss,
sense clash) and adds hard rejects taken from v3-r1 SPOTCHECK.md:

  - invented Subtotal / subtracted / substitute / minus / ditto when the ATF
    has no matching sign
  - artifact symbols Ø, ¶, and § (not sexagesimal 0;01)
  - language-tag leaks such as (Sum)/(Akk) or %sux/%šu on non-bilingual lines
  - almost-untranslated ATF copy-through
  - omen templates on non-omen lines
  - common nouns read as personal names (Meluletum for "games")

Exceptions (not hard fails):
  - 0;01-style sexagesimal notation when the ATF has 0.0.1
  - ceremonial-name expansions (Etemenniguru → "House With a Foundation...")
  - chrF is never a keep/drop criterion

Gloss checks (clean ORACC/ePSD-style glossaries + clean CC BY-SA training
pairs only; no ETCSL, eBL, NC, or B2c material):

  - Forward per-sign: content words not in the official (plus synonym /
    WordNet / mined) gloss list for the line's ATF signs, after lemmatizing.
  - Flat corpus vocab: content words not attested in clean human translations.
  - Reverse: a content word that maps to known signs, none of which appear
    in the ATF (e.g. lamb: expected sila4|udu). Unmapped words get no judgment.

Names and ATF-backed numbers are exempt. In paraphrase='lenient' all three
stay FLAGS. In paraphrase='strict', gloss_tier (per_sign / corpus_vocab /
reverse) chooses which FLAG becomes a hard reject.

check() returns {ok, fails, flags, info}. ok is False iff fails is non-empty.
flags["gloss"] is the forward per-sign score (backward compatible).
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

DIR = os.path.dirname(os.path.abspath(__file__))
V2F = os.path.join(DIR, "v2filter")
sys.path.insert(0, V2F)
import filter_v2 as fv  # noqa: E402
import lemma_support as ls  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-reject lexicons
# ---------------------------------------------------------------------------

ACCOUNTING_WORDS = {
    "subtotal": "subtotal",
    "subtotals": "subtotal",
    "subtracted": "subtracted",
    "subtract": "subtracted",
    "subtracting": "subtracted",
    "subtraction": "subtracted",
    "substitute": "substitute",
    "substituted": "substitute",
    "substitutes": "substitute",
    "substitution": "substitute",
    "minus": "minus",
    "ditto": "ditto",
}

# Artifact glyphs that appear in hyps and never in refs. Do not confuse with 0;
ARTIFACT_CHARS = {
    "Ø": "artifact:Ø",
    "¶": "artifact:¶",
    "§": "artifact:§",
}

# Language-tag leaks in English.
_LANG_TAG_RE = re.compile(
    r"\(\s*(?:Sum|Akk|Sumerian|Akkadian|sux|akk)(?:\s*\.)?\s*\)"
    r"|%\s*(?:sux|akk|šu|szu|su)\b"
    r"|(?<![A-Za-z])(?:Sum|Akk)\.(?![A-Za-z])",
    re.I,
)

_OMEN_GENRE = (
    "omen", "diagnostic", "prognostic", "extispic", "physiognom",
    "divination", "medicine", "medical", "hemero", "astrolog",
)

# Genre families that are almost never omen protases.
_NON_OMEN_GENRE = (
    "lexical", "lexicography", "administrative", "letter", "receipt",
    "expenditure", "inventory", "legal", "mathematical", "school",
    "business",
)

_OMEN_EN_START = re.compile(r"^\s*[\(\[]?\s*If\b", re.I)
_OMEN_STUB = re.compile(
    r"^\s*[\(\[]?\s*If\b[\s\.…\-\[\]\(\)]*$",
    re.I,
)

# Sexagesimal / number-like English tokens (exempt from gloss flag when ATF-backed).
_NUM_EN = re.compile(
    r"^(?:"
    r"\d+(?:[;:.,]\d+)*|"          # 0;01  1,000  0.0.1
    r"\d+/\d+|"                    # 1/2
    r"[½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]|"
    r"n"
    r")$",
    re.I,
)

# Function words only for the gloss flag. Do NOT reuse fv.STOP_EN: that list
# includes content nouns (year, gold, silver, house, wall, man, day, father)
# which must stay checkable and includable in official allowed sets.
_GLOSS_STOP = set(ls.GENERIC_GLOSS) | {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "thus",
    "of", "in", "on", "to", "for", "from", "with", "by", "as", "at",
    "into", "onto", "upon", "over", "under", "after", "before", "between",
    "among", "through", "during", "without", "within", "about", "against",
    "he", "she", "it", "i", "we", "you", "they", "him", "her", "them",
    "his", "its", "their", "my", "your", "our", "me", "us",
    "this", "that", "these", "those", "who", "which", "what", "whom",
    "whose", "where", "when", "why", "how",
    "not", "no", "nor", "yes", "there", "here",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "do", "does", "did", "done", "doing",
    "has", "have", "had", "having",
    "will", "would", "shall", "should", "may", "might", "must", "can",
    "could",
    "one", "ones", "another", "other", "others", "each", "every", "all",
    "both", "some", "any", "such", "same", "own",
    "also", "very", "just", "only", "even", "still", "already",
    "than", "then", "once", "again", "ever", "never",
    "up", "down", "out", "off", "away", "back", "well",
    "mr", "mrs", "ms",
    "var", "means",  # lexical glue
}

# Irregular / handy lemmas for the gloss flag (no NLTK dependency).
_IRREG = {
    "men": "man", "women": "woman", "children": "child", "mice": "mouse",
    "geese": "goose", "oxen": "ox", "feet": "foot", "teeth": "tooth",
    "leaves": "leaf", "lives": "life", "loaves": "loaf",
    "clothed": "clothe", "clad": "clothe", "cladding": "clothe",
    "better": "good", "best": "good", "worse": "bad", "worst": "bad",
    "said": "say", "went": "go", "gone": "go", "been": "be",
    "was": "be", "were": "be", "is": "be", "are": "be", "am": "be",
    "has": "have", "had": "have", "did": "do", "done": "do",
    "made": "make", "ate": "eat", "eaten": "eat",
    "gave": "give", "given": "give", "took": "take", "taken": "take",
    "came": "come", "saw": "see", "seen": "see", "knew": "know",
    "known": "know", "built": "build", "written": "write", "wrote": "write",
    "stewed": "stew", "fearsomeness": "fear", "fearfulness": "fear",
    "awesome": "awe", "awesomeness": "awe",
    "rations": "ration", "allotments": "allotment",
    "baskets": "basket", "temples": "temple", "foundations": "foundation",
}

# Bidirectional synonym groups layered on official glosses (not a hard lexicon
# of invented words). Keep these conservative: soup≠lamb.
_SYN_GROUPS = [
    {"house", "temple", "shrine", "chapel", "sanctuary", "building", "palace"},
    {"foundation", "platform", "base", "podium", "temen"},
    {"fear", "awe", "fearsomeness", "awesome", "awful", "terrible", "terror",
     "dread", "awe-inspiring", "frightening", "fearsome"},
    {"clothe", "clad", "cover", "covered", "heaped", "heap", "piled", "pile",
     "thick", "dress", "clothed"},
    {"soup", "broth", "porridge"},
    {"bread", "loaf", "loaves", "biscuit"},
    {"lamb", "sheep", "ewe", "ram", "ewe-lamb"},
    {"basket", "container", "vessel", "bin"},
    {"reed", "cane", "rush"},
    {"straw", "chaff", "fodder"},
    {"game", "games", "play", "sport"},
    {"king", "lord", "ruler", "master", "sovereign"},
    {"father", "dad", "sire"},
    {"son", "child", "offspring"},
    {"woman", "lady", "female"},
    {"man", "male", "person", "people"},
    {"say", "speak", "talk", "utter"},
    {"go", "walk", "come"},
    {"give", "grant", "bestow"},
    {"great", "grand", "mighty", "large", "big"},
    {"good", "fine", "quality", "first-class"},
    {"grain-fed", "fattened", "barley-fed"},
    {"total", "sum", "subtotal"},
    {"month", "iti"},
    {"day", "date"},
    {"god", "deity", "divine"},
    {"name", "called"},
    {"city", "town"},
    {"land", "country"},
    {"water", "river"},
    {"silver", "money"},
    {"barley", "grain", "corn"},
    # Expansion (clean, conservative). Do not equate strong≈erect or
    # banquet≈village / eat.
    {"smear", "anoint", "rub", "daub"},
    {"restore", "return", "reestablish", "reinstate"},
    {"determine", "decree", "destine", "decide"},
    {"build", "construct", "make"},
    {"barge", "boat", "ship"},
    {"boatman", "bargeman", "sailor", "boat-man", "barge-man"},
    {"smith", "goldsmith", "silversmith"},
    {"fate", "destiny"},
    {"year", "years"},
]

_SYN = {}
for _g in _SYN_GROUPS:
    for _w in _g:
        _SYN.setdefault(_w, set()).update(_g)


# Folded exonyms → ATF writings for the gloss name exemption.
_GLOSS_NAME_EXONYMS = {
    "sennacherib": (
        "sinahheeriba", "sinahheriba", "enzusesmessu", "enzuszeszmessu", "enzuszeszmeszsu", "enzuszeszmesu",
        "enzuszeszmessu", "szennacherib",
    ),
}


def typo_fold(s: str) -> str:
    s = ls.typo(s or "")
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode()
    return s


def fold_alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", typo_fold(s).lower())


def atf_surface_tokens(atf: str):
    """Damage- and underscore-stripped ATF tokens (no language tags).

    Determinatives are removed *before* punctuation so `{na4}ur5` becomes
    `ur5` (not `na4ur5`) and `{gesz}ma2` becomes `ma2`. MIN and muszen
    wrapped in braces are kept as signs (ditto / bird).
    """
    out = []
    for t in ls.atf_tokens(atf or ""):
        if re.search(r"(?<![A-Za-z])MIN(?![A-Za-z])", t):
            out.append("MIN")
        if re.search(r"\{[^}]*muszen[^}]*\}", t, re.I):
            out.append("muszen")
        # Strip determinatives first; otherwise `{` / `}` in the punctuation
        # class glue the det onto the sign ({na4}ur5 → na4ur5).
        bare = re.sub(r"\{[^}]*\}", "", t)
        bare = re.sub(r"[\[\]#?!*<>|_={}]", "", bare)
        bare = bare.replace("_", "")
        bare = re.sub(r",+$", "", bare)
        if not bare or bare.startswith("%") or bare in {"//", "...", "…", "x", "X"}:
            continue
        out.append(bare)
    return out


_CASE_ENDINGS = {
    "im", "um", "am", "ia", "szu", "szu2", "szun", "ka", "ki", "su",
    "ni", "tim", "tum", "tam", "ma",
}


# Readings of common determinatives, used to license "wooden boat" for {gesz}ma2 etc.
_DET_EN = {
    "gesz": {"wood", "wooden", "tree", "timber"},
    "gisz": {"wood", "wooden", "tree", "timber"},
    "jesz": {"wood", "wooden", "tree", "timber"},
    "na4": {"stone"},
    "szim": {"aromatic", "resin", "spice"},
    "u2": {"plant", "herb"},
    "muszen": {"bird"},
    "tug2": {"textile", "garment", "cloth"},
    "ku6": {"fish"},
    "uruda": {"copper"},
    "kusz": {"leather", "hide"},
}


def determinative_lemmas(atf: str):
    """English licensed by determinatives present in the ATF."""
    out = set()
    for raw in re.findall(r"\{([^}]+)\}", atf or ""):
        key = re.sub(r"[^a-z0-9]+", "", typo_fold(raw).lower())
        if not key:
            continue
        for det, words in _DET_EN.items():
            if key == det or key.startswith(det):
                out.update(_lemmatize_en(w) for w in words)
    return out



def atf_lookup_keys(atf: str):
    """ATF forms worth glossary lookup, including hyphen pieces and 2/3-grams.

    `[...]-du3-en` → du3, en, du3-en; `mu-an-na_-ti` → mu-an-na; `ku3-dim2-me-esz2`
    → ku3-dim2. Digit-stripped homographs are not added as keys (sila3 stays
    sila3). `lookup_forms_relaxed` still applies `_filter_index_mismatch`.
    """
    keys = []
    seen = set()

    def add(x):
        x = (x or "").strip("-. ")
        if not x or x in seen or x.startswith("%"):
            return
        # skip lone case/phonetic endings and ellipsis leftovers
        if x in {".", "..", "...", "x", "n"}:
            return
        seen.add(x)
        keys.append(x)

    for tok in atf_surface_tokens(atf):
        add(tok)
        parts = [p for p in re.split(r"[-./+]", tok) if p and p not in {"x", "n", "..."}]
        for p in parts:
            add(p)
        for n in (2, 3):
            for i in range(0, max(0, len(parts) - n + 1)):
                add("-".join(parts[i:i + n]))
        # Akkadian noun genitive kap-ri-im → kapru (citation-form guess)
        if len(parts) >= 2 and typo_fold(parts[-1]) in _CASE_ENDINGS:
            stem = "-".join(parts[:-1])
            add(stem)
            fs = fold_alnum(stem)
            if fs.endswith(("i", "a", "e", "u")) and len(fs) >= 4:
                add(fs[:-1] + "u")
                add(fs[:-1] + "um")
    return keys


def atf_content_lookup_keys(atf: str):
    """Subset of atf_lookup_keys used for official-gloss lookup.

    Always includes full tokens, hyphen 2/3-grams, and citation-form guesses.
    Single hyphen pieces are included only when they carry a phonetic index
    (du3, gi4, ku3) or have fold length >= 3 (nam, tar, sila). This stops
    grammatical bits (a, en, pa, as, bi, im) from flooding the allowed set.
    """
    out = []
    seen = set()

    def add(x):
        x = (x or "").strip("-. ")
        if not x or x in seen or x.startswith("%"):
            return
        seen.add(x)
        out.append(x)

    for tok in atf_surface_tokens(atf):
        add(tok)
        parts = [p for p in re.split(r"[-./+]", tok) if p and p not in {"x", "n", "..."}]
        has_index = any(re.search(r"\d", p) for p in parts)
        # 3-grams always (mu-an-na). 2-grams only when a part has a sign index
        # (ku3-dim2) — skip syllabic 2-grams like tap-pa.
        ngram_ns = (2, 3) if has_index or len(parts) <= 2 else (3,)
        for n in ngram_ns:
            for i in range(0, max(0, len(parts) - n + 1)):
                add("-".join(parts[i:i + n]))
        if len(parts) >= 2 and typo_fold(parts[-1]) in _CASE_ENDINGS:
            stem = "-".join(parts[:-1])
            add(stem)
            fs = fold_alnum(stem)
            if fs.endswith(("i", "a", "e", "u")) and len(fs) >= 4:
                add(fs[:-1] + "u")
                add(fs[:-1] + "um")
        # Single pieces: indexed signs (du3, gi4) or, on indexed tokens, length >= 3 (nam, tar).
        for p in parts:
            fk = fold_alnum(p)
            if re.search(r"\d", p) or (has_index and len(fk) >= 3):
                add(p)
    return out


def _atf_token_forms(atf: str):
    """Folded forms of each ATF token, with trailing phonetic digits stripped."""
    out = []
    for t in ls.atf_tokens(atf or ""):
        bare = re.sub(r"[\[\]#?!*<>|_={}]", "", t)
        bare = re.sub(r"\{[^}]*\}", "", bare)
        if re.match(r"^%", bare):
            continue
        f = fold_alnum(bare)
        if not f:
            continue
        out.append(f)
        stripped = re.sub(r"\d+$", "", f)
        if stripped and stripped != f:
            out.append(stripped)
    return out


def _atf_blob(atf: str) -> str:
    return "".join(_atf_token_forms(atf))


def _first_content_atf_token(atf: str) -> str:
    for t in ls.atf_tokens(atf or ""):
        bare = re.sub(r"[\[\]#?!*<>|_={}]", "", t).strip()
        if not bare or re.match(r"^%", bare):
            continue
        return bare
    return ""


# ---------------------------------------------------------------------------
# Accounting invented words
# ---------------------------------------------------------------------------

_TOTAL_ATF = re.compile(
    r"szunigin|szu-?nigin|shu-?nigin|su-?nigin|"
    r"\|?szu\+nigin\|?|gu2-?an-?sze3",
    re.I,
)
_MINUS_TOKEN = re.compile(r"^(?:_?)(?:la2|lal2|lal)(?:-ia3)?(?:_?)$", re.I)
_SUBSTITUTE_ATF = re.compile(
    r"pu-?u[h2h]|puhu|pu-?u2-?hu|ku-?um(?!-)",
    re.I,
)
_DITTO_ATF = re.compile(
    r"(?:^|[\s<|(])(?:min|MIN|ki-min|KI\.MIN|%ditto|ditto)(?:$|[\s>)|\]])",
)


def _has_total_sign(atf: str) -> bool:
    if _TOTAL_ATF.search(atf or ""):
        return True
    # standalone PAP "total" (not a name like pap-pap inside a longer token)
    for t in ls.atf_tokens(atf or ""):
        bare = re.sub(r"[\[\]#?!*<>|_={}]", "", t)
        if fold_alnum(bare) == "pap":
            return True
    return False


def _has_minus_sign(atf: str) -> bool:
    if re.search(r"la2-ia3|lal2-ia3", atf or "", re.I):
        return True
    for t in ls.atf_tokens(atf or ""):
        bare = re.sub(r"[\[\]#?!*<>|_={}]", "", t)
        if _MINUS_TOKEN.match(bare):
            return True
    return False


def _has_substitute_sign(atf: str) -> bool:
    return bool(_SUBSTITUTE_ATF.search(atf or ""))


def _has_ditto_sign(atf: str) -> bool:
    a = atf or ""
    # MIN / min as a sign, KI.MIN, damaged [MIN(...)] , DISZ-MIN ("ditto").
    if re.search(r"(?:disz-min|DISZ-MIN|ki-min|KI\.MIN|%ditto)", a, re.I):
        return True
    if re.search(r"(?<![A-Za-z])(?:MIN|min|ditto)(?![A-Za-z])", a):
        return True
    if _DITTO_ATF.search(a):
        return True
    for t in ls.atf_tokens(a):
        bare = re.sub(r"[\[\]#?!*<>|_={}]", "", t)
        if fold_alnum(bare) in {"min", "kimin", "ditto", "diszmin"}:
            return True
        if re.search(r"MIN|min", t) and re.search(r"[<(]", t):
            return True
    return False


_WORD_RE = re.compile(r"[A-Za-zŠšṢṣṬṭḪḫØ¶§%0-9'’\-ʾʿʼʽʹ′`]+")
_NAME_DET_RE = re.compile(r"\{[^}\s]*[mdfMD1I][^}\s]*\}")
# Capacity / measure words are licensed logograms, not copy-through.
_UNIT_WORDS = {
    "sila", "sila3", "gur", "ban", "ban2", "barig", "bariga", "iku", "gan",
    "mana", "ma-na", "gin", "gin2", "shekel", "mina", "talent", "gun", "gun2",
    "ninda", "nindan", "sar", "sila3",
}


def _en_words(english: str):
    # Strip damage/optional brackets so [S]ennacherib stays one token.
    s = re.sub(r"[\[\]#?!<>]", "", english or "")
    return _WORD_RE.findall(s)


def check_accounting_invented(atf: str, english: str):
    """Hard-drop invented accounting lead-ins when the ATF has no matching sign."""
    fails = []
    seen = set()
    for w in _en_words(english):
        key = typo_fold(w).lower().lstrip("%").strip("[]()<>")
        key = key.replace("’", "'")
        kind = ACCOUNTING_WORDS.get(key)
        if not kind or kind in seen:
            continue
        if kind == "subtotal" and _has_total_sign(atf):
            continue
        if kind in {"subtracted", "minus"} and _has_minus_sign(atf):
            continue
        if kind == "substitute" and _has_substitute_sign(atf):
            continue
        if kind == "ditto" and _has_ditto_sign(atf):
            continue
        seen.add(kind)
        fails.append(f"invented:{kind}")
    return fails


def check_artifact_symbols(english: str):
    fails = []
    en = english or ""
    for ch, label in ARTIFACT_CHARS.items():
        if ch in en:
            fails.append(label)
    return fails


# ---------------------------------------------------------------------------
# Language-tag leaks
# ---------------------------------------------------------------------------

def is_bilingual_atf(atf: str) -> bool:
    """True when this line looks like a bilingual edition or lexical equation."""
    a = atf or ""
    al = a.lower()
    has_sux = bool(re.search(r"%sux\b|%su\b", al))
    has_akk = bool(re.search(r"%akk\b|%a\b", al))
    if has_sux and has_akk:
        return True
    if re.search(r"=\s*%(?:a|akk|e)\b", al):
        return True
    # DCCLT-style "sux > akk" (or "sux > (disz) akk") lexical equations.
    if ">" in a:
        return True
    return False


def check_language_tag_leak(atf: str, english: str):
    tags = _LANG_TAG_RE.findall(english or "")
    if not tags:
        # also catch glued leaks like %šu-ummu
        if re.search(r"%\s*(?:sux|akk|šu|szu|su)(?:-|\b)", english or "", re.I):
            if not is_bilingual_atf(atf):
                return ["langtag:leaked"]
        return []
    if is_bilingual_atf(atf):
        return []
    # Dedup a readable label from the first tag.
    lab = re.sub(r"\s+", "", tags[0])
    return [f"langtag:{lab}"]


# ---------------------------------------------------------------------------
# Copy-through
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Relaxed glossary lookup (broken spellings: me-lu-le-tum ≈ me-lul-tum)
# ---------------------------------------------------------------------------

_FOLD_INDEX = None


def _fold_index():
    """Map hyphen-stripped folded form → glossary keys. Built once."""
    global _FOLD_INDEX
    if _FOLD_INDEX is None:
        g = ls.build_glossary()
        idx = {}
        for k in g:
            fk = fold_alnum(k)
            if len(fk) >= 5:
                idx.setdefault(fk, []).append(k)
        _FOLD_INDEX = idx
    return _FOLD_INDEX


def _form_index_digits(form: str):
    m = re.search(r"(\d+)$", typo_fold(form or ""))
    return m.group(1) if m else None


def _filter_index_mismatch(form: str, hits):
    """sila3 (unit) must not inherit sila4 ('lamb') senses."""
    n = _form_index_digits(form)
    if not n or not hits:
        return hits
    kept = []
    for item in hits:
        cf = item.get("cf") or ""
        cn = _form_index_digits(cf)
        if cn and cn != n:
            continue
        kept.append(item)
    return kept or hits


def lookup_forms_relaxed(form: str):
    """lookup_form plus hyphen-stripped / one-vowel-dropped neighbours."""
    hits = _filter_index_mismatch(form, ls.lookup_form(form))
    if hits:
        return hits
    g = ls.build_glossary()
    idx = _fold_index()
    f = fold_alnum(form)
    if len(f) < 5:
        return []
    cands = {f}
    for i, ch in enumerate(f):
        if ch in "aeiou" and 0 < i < len(f) - 1:
            cands.add(f[:i] + f[i + 1:])
    out, seen = [], set()
    for c in cands:
        if abs(len(c) - len(f)) > 2:
            continue
        for key in idx.get(c) or []:
            for item in g.get(key) or []:
                rec = (item.get("cf"), item.get("gw"), item.get("sense"), item.get("pos"))
                if rec in seen:
                    continue
                seen.add(rec)
                out.append(item)
    return _filter_index_mismatch(form, out)


# ---------------------------------------------------------------------------
# Sexagesimal 0;01 ↔ dotted ATF capacity 0.0.1 (notation, not a new number)
# ---------------------------------------------------------------------------

_DOT_CAP_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+){1,3})(?![\d.])")
_SEMI_RE = re.compile(r"(?<![\d;])(\d+;\d+)(?![\d;])")


def atf_dotted_capacities(atf: str):
    return [m.group(1) for m in _DOT_CAP_RE.finditer(atf or "")]


def dotted_to_semi_forms(s: str):
    """0.0.1 → 0;01; 0.1.2 → 0;12 (digit-place transcription used in this repo)."""
    parts = [int(x) for x in s.split(".")]
    if len(parts) < 2:
        return set()
    head, rest = parts[0], parts[1:]
    out = set()
    if len(rest) == 1:
        n = rest[0]
        out.update({f"{head};{n:02d}", f"{head};{n}"})
    else:
        b, n = rest[0], rest[1]
        packed = 10 * b + n
        out.update({f"{head};{packed:02d}", f"{head};{packed}"})
    return out


def licensed_sexagesimal_tokens(atf: str, english: str):
    """English 0;01 tokens that are notation for an ATF dotted capacity."""
    licensed_forms = set()
    for d in atf_dotted_capacities(atf):
        licensed_forms.update(dotted_to_semi_forms(d))
    tokens = set()
    for s in _SEMI_RE.findall(english or ""):
        if s in licensed_forms:
            a, b = s.split(";")
            tokens.update({s, a, b})
            if b.isdigit():
                tokens.add(str(int(b)))
            if a.isdigit():
                tokens.add(str(int(a)))
    return tokens


def suppress_sexagesimal_number_fails(fails, atf, english):
    licensed = licensed_sexagesimal_tokens(atf, english)
    if not licensed:
        return fails
    out = []
    for f in fails:
        if f.startswith("numbers:"):
            payload = f.split(":", 1)[1]
            parts = [p.strip() for p in payload.split(",") if p.strip()]
            keep = [p for p in parts if p not in licensed]
            if not keep:
                continue
            f = "numbers:" + ",".join(keep)
        out.append(f)
    return out


# ---------------------------------------------------------------------------
# Gloss-licensed ceremonial / title-case expansions (not hard drops)
# ---------------------------------------------------------------------------

def _gloss_words_from_sense(text: str):
    """Words from a guide-word / sense, preferring quoted translations."""
    words = []
    s = text or ""
    quotes = re.findall(r"[\"'‘’]([^\"'‘’]+)[\"'‘’]", s)
    use = quotes if quotes else [re.split(r"\b(?:probably|at)\b", s, 1, flags=re.I)[0]]
    for chunk in use:
        for w in re.findall(r"[A-Za-z]+", typo_fold(chunk)):
            if w.lower() in _GLOSS_STOP or len(w) < 3:
                continue
            words.append(w)
    return words


def official_gloss_lemmas(atf: str, toks=None, include_mined=True, include_wordnet=False):
    """Lemmatized official English gloss tokens for this line (clean ORACC + expansions)."""
    allowed = set()

    def add_word(w):
        if not w:
            return
        if typo_fold(w).lower() in _GLOSS_STOP and _lemmatize_en(w) in _GLOSS_STOP:
            return
        allowed.add(_lemmatize_en(w))
        allowed.update(_syns(w, use_wordnet=False))

    def add_item(cf, gw, sense, pos, form=None):
        for w in _gloss_words_from_sense(gw or "") + _gloss_words_from_sense(sense or ""):
            add_word(w)
        # Multi-word official senses: "gold or silver smith" → silversmith, goldsmith
        blob = typo_fold(" ".join([gw or "", sense or ""])).lower()
        if "smith" in blob and "silver" in blob:
            add_word("silversmith")
        if "smith" in blob and "gold" in blob:
            add_word("goldsmith")
        key_cf = typo_fold(cf or "").replace("-", "")
        key_gw = typo_fold(gw or "").replace("-", "")
        for key in (key_cf, key_gw, typo_fold(form or "").replace("-", "")):
            for w in ls.EXTRA_SYNONYMS.get(key, []) or []:
                add_word(w)

    if toks:
        for tok in toks:
            form, cf, gw, sense, pos = (list(tok) + [""] * 5)[:5]
            add_item(cf, gw, sense, pos, form=form)
    for form in atf_content_lookup_keys(atf or ""):
        for item in lookup_forms_relaxed(form)[:8]:
            add_item(item.get("cf"), item.get("gw"), item.get("sense"),
                     item.get("pos"), form=form)
        # Logograms: use the form as written, not a digit-stripped homograph
        # (sila3 must not inherit sila4).
        typ = ls.typo(form)
        key_full = re.sub(r"[^a-z0-9]", "", typ)
        key_nodig = re.sub(r"[^a-z]", "", typ)
        for w in fv.LOGOGRAMS.get(key_full) or []:
            add_word(w)
        # only fall back to digit-stripped if this form has no phonetic index
        if not re.search(r"\d", typ):
            for w in fv.LOGOGRAMS.get(key_nodig) or []:
                add_word(w)

    # Idioms that live on co-present signs (not a single official gw).
    folded = {fold_alnum(k) for k in atf_lookup_keys(atf or "")}
    if "nam" in folded and ("tar" in folded or "namtar" in folded):
        for w in ("determine", "decree", "destine", "fate", "destiny"):
            add_word(w)
    if "gi4" in folded or "gi" in folded:
        # gi4 "return" already added from the glossary; "restore" comes via _SYN
        pass

    allowed.update(determinative_lemmas(atf))

    if include_mined:
        allowed.update(mined_gloss_for_atf(atf))

    if include_wordnet:
        extra = set()
        for w in list(allowed):
            extra.update(wordnet_syns(w))
        allowed.update(extra)

    if "smith" in allowed and ({"silver", "gold"} & allowed):
        allowed.update({"silversmith", "goldsmith"})

    return {x for x in allowed if x and x not in _GLOSS_STOP}


def suppress_gloss_licensed_name_fails(fails, atf, english, toks=None):
    """Do not hard-drop ceremonial-name expansions or title-cased official glosses."""
    allowed = official_gloss_lemmas(atf, toks=toks)
    if not allowed:
        return fails
    out = []
    for f in fails:
        kind, _, payload = f.partition(":")
        if kind not in {"names", "invented"}:
            out.append(f)
            continue
        parts = [p.strip() for p in payload.split(",") if p.strip()]
        keep = []
        for p in parts:
            lem = _lemmatize_en(p)
            cands = _syns(p) | {lem, fold_alnum(p)}
            if cands & allowed:
                continue
            keep.append(p)
        if not keep:
            continue
        out.append(kind + ":" + ",".join(keep))
    return out



# ---------------------------------------------------------------------------
# Already-English ATF (image labels like "Palm tree") and month-name helpers
# ---------------------------------------------------------------------------

_EN_DICT = None
_EN_DICT_FALLBACK = {
    "palm", "tree", "stylized", "stylised", "plant", "leaf", "flower",
    "king", "queen", "lord", "lady", "month", "day", "year", "city",
    "temple", "gate", "tablet", "stele", "relief", "scene", "figure",
    "standing", "seated", "winged", "bull", "lion", "bird", "fish",
    "water", "river", "mountain", "star", "sun", "moon", "house",
    "from", "the", "and", "of", "for", "with",
}


def _english_dict():
    """Cached lowercase English lexicon. /usr/share/dict/words plus a fallback."""
    global _EN_DICT
    if _EN_DICT is None:
        words = set(_EN_DICT_FALLBACK)
        path = "/usr/share/dict/words"
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    w = line.strip().lower()
                    if w.isalpha() and len(w) >= 3:
                        words.add(w)
        _EN_DICT = words
    return _EN_DICT


def _plain_alpha(tok: str) -> str:
    bare = re.sub(r"[\[\]#?!*<>|_={}]", "", tok or "")
    bare = re.sub(r"\{[^}]*\}", "", bare)
    return bare.strip()


def _token_is_english_word(tok: str) -> bool:
    """Unhyphenated, undigited alphabetic token in the English lexicon."""
    bare = _plain_alpha(tok)
    if not bare or re.search(r"[-\d]", bare):
        return False
    f = fold_alnum(bare)
    return bool(f) and f.isalpha() and len(f) >= 3 and f in _english_dict()


def atf_already_english(atf: str) -> bool:
    """True when the ATF line is already English (e.g. 'Palm tree', 'Stylized tree')."""
    toks = []
    for t in ls.atf_tokens(atf or ""):
        bare = _plain_alpha(t)
        if not bare or re.match(r"^%", bare) or bare in {"$", "blank", "space"}:
            continue
        if fold_alnum(bare):
            toks.append(bare)
    if not toks:
        return False
    n = sum(1 for tok in toks if _token_is_english_word(tok))
    return n == len(toks) and n >= 1


def _is_capitalized_en(original: str) -> bool:
    sig = re.sub(r"^[^A-Za-zŠšṢṣṬṭḪḫ]+", "", original or "")
    return bool(sig) and sig[0].isupper()


def _month_line(atf: str) -> bool:
    return bool(re.search(r"(?:^|[\s_])iti(?:[\s_\-]|$)|(?<![A-Za-z])itud(?![A-Za-z])", atf or "", re.I))


def check_copy_through(atf: str, english: str, toks=None):
    """Almost-untranslated ATF copied into the English.

    Hyphenated or folded ATF forms that make up most of the English content.
    Exemptions: name lemmas (PN/DN/TN/MN/...), ceremonial e2- compounds,
    damaged or unmarked names that are capitalized and ATF-backed, month
    names on an iti-line, and ATF that is already English (image labels).
    name_licensed() is not used on its own, because it also matches
    common-noun stems (Gigur, -angurum).
    """
    if atf_already_english(atf):
        return []
    words = _en_words(english)
    if not words:
        return []
    forms = set(_atf_token_forms(atf))
    blob = _atf_blob(atf)
    copies = []
    content = []
    is_month = _month_line(atf)

    def _is_name_lemma(word: str, original: str) -> bool:
        fw = fold_alnum(word)
        stripped = re.sub(r"\d+$", "", fw)
        # Determinatives {d}, {disz}, {m}, {f} mark the matching ATF token as a name.
        for tok in ls.atf_tokens(atf or ""):
            if not _NAME_DET_RE.search(tok):
                continue
            bare = re.sub(r"[\[\]#?!*<>|_={}]", "", tok)
            bare = re.sub(r"\{[^}]*\}", "", bare)
            ff = fold_alnum(bare)
            ff2 = re.sub(r"\d+$", "", ff)
            if fw in {ff, ff2} or stripped in {ff, ff2} or (len(fw) >= 5 and (fw in ff or ff in fw)):
                return True
        rows = []
        if toks:
            for tok in toks:
                form, cf, gw, sense, pos = (list(tok) + [""] * 5)[:5]
                rows.append({"form": form, "cf": cf, "pos": pos})
        for form in ls.atf_tokens(atf or ""):
            for item in lookup_forms_relaxed(form)[:4]:
                rows.append({"form": form, "cf": item.get("cf"), "pos": item.get("pos")})
        for r in rows:
            ff = fold_alnum(r.get("form") or "")
            cf = fold_alnum(r.get("cf") or "")
            ff2 = re.sub(r"\d+$", "", ff)
            close = (
                fw in {ff, ff2, cf} or stripped in {ff, ff2, cf}
                or (len(fw) >= 6 and fw == blob)
                or (len(fw) >= 5 and cf and (fw.startswith(cf) or cf.startswith(fw))
                    and abs(len(fw) - len(cf)) <= 3)
            )
            if not close:
                continue
            pos = r.get("pos") or ""
            if ls.NAME_POS.match(pos):
                return True
            if re.match(r"^e2-", r.get("form") or "", re.I) and (r.get("form") or "").count("-") >= 2:
                return True
        # Month names: iti-line plus a capitalized ATF-backed token (Apinduʾa).
        if is_month and _is_capitalized_en(original):
            for form in ls.atf_tokens(atf or ""):
                ff = re.sub(r"\d+$", "", fold_alnum(form))
                # strip wood det from {gesz}apin-du8-a → apindua
                ff = re.sub(r"^(gesz|gisz|gi)", "", ff)
                if len(fw) >= 4 and (fw == ff or fw.startswith(ff) or ff.startswith(fw)):
                    return True
                for item in lookup_forms_relaxed(form)[:4]:
                    if (item.get("pos") or "") == "MN":
                        cf = fold_alnum(item.get("cf") or "")
                        if cf and (fw == cf or fw.startswith(cf) or cf.startswith(fw)):
                            return True
        # Capitalization is taken from the *original* English token, not typo_fold
        # (which lowercases and used to drop Zikanim / Atta-ma- / Apinduʾa).
        if _is_capitalized_en(original):
            if not check_common_noun_as_pn(atf, original, toks=toks):
                if fv.name_licensed(original, atf, toks=toks) or fv.name_licensed(word, atf, toks=toks):
                    return True
            # Damaged unmarked names: Atta-ma-[...] ↔ at-ta-ma-x
            for form in ls.atf_tokens(atf or ""):
                ff = fold_alnum(re.sub(r"[xX]+$", "", _plain_alpha(form)))
                ff = re.sub(r"x", "", ff)
                if len(fw) >= 4 and ff and (fw == ff or fw.startswith(ff) or ff.startswith(fw)):
                    if not check_common_noun_as_pn(atf, original, toks=toks):
                        return True
        return False

    for w in words:
        bare = typo_fold(w).lstrip("%-").strip("[]()<>")
        if not bare:
            continue
        low = bare.lower()
        if low in _GLOSS_STOP or _NUM_EN.match(bare) or low in ACCOUNTING_WORDS:
            continue
        if fold_alnum(bare) in {fold_alnum(u) for u in _UNIT_WORDS} or low in _UNIT_WORDS:
            continue
        # Copied already-English ATF tokens (Palm, tree) are not copy-through.
        if _token_is_english_word(w) and _token_is_english_word(bare):
            # only skip if the ATF actually contains this English word as a token
            if fold_alnum(bare) in forms or any(_token_is_english_word(f) and fold_alnum(f) == fold_alnum(bare)
                                                 for f in ls.atf_tokens(atf or "")):
                continue
        fw = fold_alnum(bare)
        if len(fw) < 4:
            continue
        content.append(w)
        stripped = re.sub(r"\d+$", "", fw)
        hit = (fw in forms or stripped in forms or
               (len(fw) >= 6 and fw in blob) or
               (len(stripped) >= 6 and stripped in blob))
        if not hit and "-" in w and (fw in blob or stripped in blob):
            hit = True
        if not hit:
            continue
        if _is_name_lemma(bare, w):
            continue
        copies.append(w)
    if not copies:
        return []
    n_content = max(len(content), 1)
    if len(copies) >= 2 and len(copies) / n_content >= 0.5:
        return ["copy_through:" + ",".join(copies[:4])]
    if len(copies) == 1 and len(content) <= 2 and len(fold_alnum(copies[0])) >= 6:
        return ["copy_through:" + copies[0]]
    return []



# ---------------------------------------------------------------------------
# Omen templates
# ---------------------------------------------------------------------------

_DISZ_HEAD = re.compile(
    r"^(?:DISZ|disz|diš|DIŠ|BE|szum-ma|šum-ma|szumma|šumma)\b",
    re.I,
)


def _atf_is_omen_protasis(atf: str) -> bool:
    head = _first_content_atf_token(atf)
    if not head:
        return False
    bare = re.sub(r"[\[\]#?!*<>|_={}]", "", head)
    bare = re.sub(r"\{[^}]*\}", "", bare)
    return bool(_DISZ_HEAD.match(bare))


def _genre_is_omen(genre: str) -> bool:
    g = (genre or "").lower()
    return any(k in g for k in _OMEN_GENRE)


def _genre_is_non_omen(genre: str) -> bool:
    g = (genre or "").lower()
    return any(k in g for k in _NON_OMEN_GENRE)


def check_omen_template(atf: str, english: str, genre: str = None):
    en = (english or "").strip()
    if not en or not _OMEN_EN_START.match(en):
        return []
    # tukum-bi / šumma in letters and contracts is just "if", not an omen protasis.
    if re.search(r"tukum-?bi|\btukum\b|szum-ma|šum-ma|szumma|šumma", atf or "", re.I):
        return []
    if _atf_is_omen_protasis(atf) or _genre_is_omen(genre):
        return []
    # Always drop the empty "(If) ... ." stub on a non-omen line.
    compact = re.sub(r"[\s\.…\-\[\]\(\)]+", " ", en).strip()
    if _OMEN_STUB.match(en) or compact.lower() in {"if", "(if)", "[if]"}:
        return ["omen_template"]
    if _genre_is_non_omen(genre):
        return ["omen_template"]
    # Unknown genre: only the stub is a hard drop; a full "If ..." sentence
    # may be literary and is left to the gloss flag / other checks.
    return []


# ---------------------------------------------------------------------------
# Common noun read as a personal name
# ---------------------------------------------------------------------------

def check_common_noun_as_pn(atf: str, english: str, toks=None):
    """Drop when English capitalizes a common-noun ATF form as if it were a PN.

    Ceremonial-name expansions and actual PN/DN/RN/GN/TN lemmas are exempt.
    """
    fails = []
    names = fv.extract_english_names(english or "")
    if not names:
        return fails
    rows = []
    if toks:
        for tok in toks:
            form, cf, gw, sense, pos = (list(tok) + [""] * 5)[:5]
            rows.append({"form": form, "cf": cf, "gw": gw, "sense": sense, "pos": pos})
    if not rows:
        for form in ls.atf_tokens(atf or ""):
            for item in lookup_forms_relaxed(form)[:6]:
                rows.append({
                    "form": form,
                    "cf": item.get("cf") or "",
                    "gw": item.get("gw") or "",
                    "sense": item.get("sense") or "",
                    "pos": item.get("pos") or "",
                })
    for name in names:
        fn = fold_alnum(name)
        if len(fn) < 5:
            continue
        matched = []
        for row in rows:
            ff = fold_alnum(row.get("form") or "")
            cf = fold_alnum(row.get("cf") or "")
            ff2 = re.sub(r"\d+$", "", ff)
            close = (
                fn in {ff, ff2, cf}
                or (len(fn) >= 6 and fn == ff2)
                or (len(fn) >= 6 and (fn.startswith(ff2) or ff2.startswith(fn) or cf.startswith(fn) or fn.startswith(cf))
                    and min(abs(len(fn) - len(ff2 or cf)), abs(len(fn) - len(cf))) <= 2)
            )
            # broken spelling: meluletum ≈ melultum (cf mēlultu → melultu)
            if not close and len(fn) >= 6:
                for cand in (ff, ff2, cf):
                    if not cand:
                        continue
                    if abs(len(fn) - len(cand)) <= 2 and (fn in cand or cand in fn or
                            re.sub(r"[aeiou]", "", fn) == re.sub(r"[aeiou]", "", cand)):
                        close = True
                        break
            if close:
                matched.append(row)
        if not matched:
            continue
        if any(ls.NAME_POS.match(r.get("pos") or "") for r in matched):
            continue
        forms = [r.get("form") or "" for r in matched]
        if any(re.match(r"^e2-", f, re.I) and f.count("-") >= 2 for f in forms):
            continue
        nounish = []
        for r in matched:
            pos = r.get("pos") or ""
            if (pos.startswith("N") and pos != "NU") or pos in {"V", "AJ", "AV", "J", "V/i", "V/t"} or not pos:
                gw = (r.get("gw") or r.get("sense") or "").strip()
                if gw and fold_alnum(gw) != fn:
                    nounish.append(r)
        if not nounish:
            continue
        fails.append("common_noun_as_pn:" + name)
    return fails


# ---------------------------------------------------------------------------
# Clean-source gloss expansion (WordNet, mined per-sign English, flat vocab,
# reverse index). Cache is written by mine_clean_gloss.py from clean BY-SA
# pairs only.
# ---------------------------------------------------------------------------

_MINE_CACHE_PATH = os.path.join(DIR, "cache", "clean_gloss_mine.json.gz")
_MINE = None  # lazy

_WN_CACHE = {}
_WN_DENY = {
    "entity", "unit", "attribute", "abstraction", "act", "action", "activity",
    "state", "object", "thing", "person", "someone", "somebody", "artifact",
    "whole", "part", "cause", "get", "set", "take", "make", "go", "come",
    "be", "have", "do", "change", "move", "work", "use", "become", "put",
    "give", "see", "find", "want", "try", "keep", "let", "begin", "seem",
    "show", "play", "run", "hold", "call", "ask", "need", "feel", "leave",
    "being", "existence", "quality", "property", "event", "process", "group",
    "system", "form", "kind", "type", "way", "time", "place", "matter",
    "stuff", "something", "anything", "everything", "nothing",
}


def wordnet_syns(w: str):
    """Conservative same-POS WordNet synonyms. No hypernyms."""
    k = _lemmatize_en(w)
    if not k or k in _WN_DENY:
        return set()
    if k in _WN_CACHE:
        return _WN_CACHE[k]
    out = set()
    try:
        from nltk.corpus import wordnet as wn
    except Exception:
        _WN_CACHE[k] = out
        return out
    try:
        for pos in (wn.VERB, wn.NOUN, wn.ADJ):
            for syn in wn.synsets(k, pos=pos)[:3]:
                sname = syn.name().split(".")[0].replace("_", "")
                if sname in _WN_DENY:
                    continue
                for lem in syn.lemmas()[:6]:
                    n = lem.name().replace("_", "-").lower()
                    if n in _WN_DENY or len(n) < 3:
                        continue
                    if re.search(r"[^a-z\-]", typo_fold(n)):
                        continue
                    out.add(_lemmatize_en(n))
                    out.add(typo_fold(n).lower().replace("-", ""))
        out.discard("")
        out.discard(k)
        if len(out) > 10:
            out = set(sorted(out)[:10])
    except Exception:
        out = set()
    _WN_CACHE[k] = out
    return out


def _is_compact_sign(form: str) -> bool:
    """Keep logograms / short writings, drop long conjugated spellings."""
    f = typo_fold(form or "").strip()
    if not f or f[0] in "+-|*./@":
        return False
    fa = fold_alnum(f)
    if not fa or len(fa) < 2 or len(fa) > 14:
        return False
    if re.search(r"[^a-z0-9\-]", typo_fold(f).replace(",", "")) and len(fa) > 10:
        return False
    return len(fa) <= 10 or bool(re.search(r"\d", f))


def _shortest_forms(forms, n=80):
    return sorted(forms, key=lambda s: (len(fold_alnum(s)), s.lower()))[:n]


def _build_official_reverse():
    """word → signs/cfs from the clean ORACC glossary (no training-pair mine)."""
    g = ls.build_glossary()
    word_signs = defaultdict(set)
    word_cfs = defaultdict(set)

    def add_en(word, form, cf):
        lem = _lemmatize_en(word)
        if not lem or lem in _GLOSS_STOP or len(lem) < 3:
            return
        if form and _is_compact_sign(form):
            word_signs[lem].add(form)
        if cf:
            c = re.sub(r"[^a-z0-9]+", "", typo_fold(cf).replace("-", ""))
            if c and len(c) >= 3:
                word_cfs[lem].add(c)
            # compact typo-folded cf also usable as a sign key
            if _is_compact_sign(cf):
                word_signs[lem].add(ls.norm_form(cf) or typo_fold(cf))

    for form, items in g.items():
        short = form if _is_compact_sign(form) else None
        for it in items:
            cf = it.get("cf") or ""
            gw = it.get("gw") or ""
            sense = it.get("sense") or ""
            for w in _gloss_words_from_sense(gw) + _gloss_words_from_sense(sense):
                add_en(w, short, cf)
            key_cf = typo_fold(cf).replace("-", "")
            key_gw = typo_fold(gw).replace("-", "")
            for key in (key_cf, key_gw, typo_fold(form).replace("-", "")):
                for w in ls.EXTRA_SYNONYMS.get(key, []) or []:
                    add_en(w, short, cf)
    return ({w: _shortest_forms(s, 80) for w, s in word_signs.items() if s},
            {w: _shortest_forms(c, 24) for w, c in word_cfs.items() if c})


def load_mine_cache(force=False):
    """Load mined per-sign English, reverse index, and flat vocab. Lazy."""
    global _MINE
    if _MINE is not None and not force:
        return _MINE
    path = _MINE_CACHE_PATH
    if os.path.exists(path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            _MINE = json.load(f)
    else:
        _MINE = {
            "meta": {"missing_cache": True},
            "vocab": {},
            "sign_words": {},
            "word_signs_mined": {},
            "official_word_signs": {},
            "official_word_cfs": {},
        }
    if not _MINE.get("official_word_signs"):
        signs, cfs = _build_official_reverse()
        _MINE["official_word_signs"] = signs
        _MINE["official_word_cfs"] = cfs
    return _MINE


def mined_gloss_for_atf(atf: str):
    """English lemmas mined as per-sign cooccurrence (high PMI) for this ATF."""
    cache = load_mine_cache()
    sign_words = cache.get("sign_words") or {}
    if not sign_words:
        return set()
    out = set()
    for k in atf_lookup_keys(atf or ""):
        fk = fold_alnum(k)
        rec = sign_words.get(fk) or sign_words.get(k)
        if not rec:
            continue
        for w in rec:
            if w and w not in _GLOSS_STOP:
                out.add(_lemmatize_en(w))
    return out


def corpus_vocab():
    cache = load_mine_cache()
    return cache.get("vocab") or {}


def reverse_index_for_word(word: str):
    """Signs/cfs whose clean gloss includes this (lemmatized) word.

    Official glossary first, then high-PMI mined pairs. Returns
    (signs_sorted, cfs_sorted). Empty means no mapping (no judgment).
    """
    lem = _lemmatize_en(word)
    if not lem:
        return [], []
    cache = load_mine_cache()
    signs = set()
    cfs = set()
    for s in (cache.get("official_word_signs") or {}).get(lem) or []:
        if s:
            signs.add(s)
    for c in (cache.get("official_word_cfs") or {}).get(lem) or []:
        if c:
            cfs.add(c)
    mined = (cache.get("word_signs_mined") or {}).get(lem) or {}
    # mined values may be {sign: {c,pmi}} or a list
    if isinstance(mined, dict):
        items = sorted(mined.items(), key=lambda kv: -float((kv[1] or {}).get("pmi") or 0))
        for s, _st in items[:12]:
            if s:
                signs.add(s)
    elif isinstance(mined, list):
        for s in mined[:12]:
            if s:
                signs.add(s)
    # also look at synonym keys (smear ↔ anoint) so a mapped synonym's signs apply
    for syn in list(_syns(lem, use_wordnet=False))[:8]:
        if syn == lem:
            continue
        for s in (cache.get("official_word_signs") or {}).get(syn) or []:
            if s:
                signs.add(s)
        for c in (cache.get("official_word_cfs") or {}).get(syn) or []:
            if c:
                cfs.add(c)
    def _pref(s):
        fa = fold_alnum(s)
        return (0 if re.search(r"\d", s) else 1, len(fa), typo_fold(s))
    return sorted(signs, key=_pref), sorted(cfs, key=_pref)


def _atf_keys_folded(atf: str):
    keys = atf_lookup_keys(atf or "")
    folded = set()
    for k in keys:
        fk = fold_alnum(k)
        if fk:
            folded.add(fk)
        nf = ""
        try:
            nf = fold_alnum(ls.norm_form(k))
        except Exception:
            nf = ""
        if nf:
            folded.add(nf)
    return keys, folded


def reverse_word_supported(word: str, atf: str, signs=None, cfs=None) -> bool:
    """True if at least one expected sign is present in the ATF line.

    Sign forms are matched against ATF keys (indices kept: sila4 ≠ sila3).
    A form also counts if its official (index-filtered) guide-word/sense
    includes this English word. Bare citation-form matching is not used:
    sila3 (unit) and sila4 (lamb) share the citation 'sila'.
    """
    if signs is None or cfs is None:
        signs, cfs = reverse_index_for_word(word)
    if not signs and not cfs:
        return True  # no mapping: no judgment (caller should skip)
    _keys, folded = _atf_keys_folded(atf)
    det_lems = determinative_lemmas(atf)
    if det_lems and (_lemmatize_en(word) in det_lems or (_syns(word, use_wordnet=False) & det_lems)):
        return True
    for s in signs:
        fs = fold_alnum(s)
        if fs and fs in folded:
            return True
    lem = _lemmatize_en(word)
    cands = _syns(word, use_wordnet=False) | {lem}
    for k in atf_content_lookup_keys(atf):
        for item in lookup_forms_relaxed(k)[:8]:
            lemmas = set()
            for w in _gloss_words_from_sense(item.get("gw") or "") + _gloss_words_from_sense(item.get("sense") or ""):
                lemmas.add(_lemmatize_en(w))
            if cands & {x for x in lemmas if x}:
                return True
    return False


def _lemmatize_en(w: str) -> str:
    w = typo_fold(w).lower().replace("’", "'")
    w = re.sub(r"[^a-z0-9]+", "", w)
    if not w:
        return w
    if w in _IRREG:
        return _IRREG[w]
    # NLTK WordNet lemmatizer (verb then noun) so years/year, built/build,
    # determines/determine, restored/restore agree on both sides.
    try:
        from nltk.stem import WordNetLemmatizer
        wnl = getattr(_lemmatize_en, "_wnl", None)
        if wnl is None:
            wnl = WordNetLemmatizer()
            _lemmatize_en._wnl = wnl
        for pos in ("v", "n", "a"):
            lw = wnl.lemmatize(w, pos)
            if lw and lw != w:
                return lw
    except Exception:
        pass
    for suf, replen, min_stem in (
        ("iness", "", 4),
        ("ness", "", 4),
        ("ously", "", 4),
        ("edly", "", 4),
        ("ing", "", 3),
        ("ers", "", 3),
        ("ies", "y", 3),
        ("ied", "y", 3),
        ("es", "", 3),
        ("ed", "", 3),
        ("ly", "", 3),
        ("er", "", 3),
        ("est", "", 3),
        ("ments", "", 4),
        ("ment", "", 4),
        ("tions", "", 4),
        ("tion", "", 4),
        ("s", "", 3),
    ):
        if w.endswith(suf) and len(w) - len(suf) + len(replen) >= min_stem:
            return w[: len(w) - len(suf)] + replen
    return w


def _syns(w: str, use_wordnet=True):
    k = _lemmatize_en(w)
    raw = typo_fold(w).lower()
    out = {k, raw, re.sub(r"[^a-z0-9]+", "", raw)}
    out.update(_SYN.get(k, ()))
    out.update(_SYN.get(raw, ()))
    out.update(_SYN.get(re.sub(r"[^a-z0-9]+", "", raw), ()))
    if "-" in raw or " " in raw:
        for part in re.split(r"[- ]+", raw):
            if part:
                out.add(_lemmatize_en(part))
                out.add(part)
        out.add(re.sub(r"[^a-z0-9]+", "", raw))
    if use_wordnet:
        out.update(wordnet_syns(w))
        out.update(wordnet_syns(k))
    return {re.sub(r"[^a-z0-9]+", "", typo_fold(x).lower()) for x in out if x}



def _allowed_gloss_lemmas(atf: str, toks=None):
    """English gloss tokens licensed by the clean ORACC glossary.

    Uses guide-words, senses, and per-lemma EXTRA_SYNONYMS only — not raw ATF
    surface forms (those would hide copy-through) and not digit-stripped
    homographs (sila3 must not inherit sila4 'lamb').
    """
    return official_gloss_lemmas(atf, toks=toks)


def _atf_has_name_det(atf: str) -> bool:
    """True if the ATF has a (possibly damaged) PN/DN determinative."""
    return bool(_NAME_DET_RE.search(atf or ""))


def _is_atf_backed_name(word: str, atf: str, toks=None, original=None) -> bool:
    if fv.name_licensed(word, atf, toks=toks):
        return True
    if original and fv.name_licensed(original, atf, toks=toks):
        return True
    fn = fold_alnum(word)
    if toks:
        for tok in toks:
            form, cf, gw, sense, pos = (list(tok) + [""] * 5)[:5]
            if ls.NAME_POS.match(pos or "") and fold_alnum(form) == fn or fold_alnum(cf) == fn:
                return True
    # Short conventional transcription of the whole ATF line (Etemenniguru).
    blob = _atf_blob(atf)
    if len(fn) >= 6 and fn == blob:
        return True
    if len(fn) >= 8 and (fn in blob or blob in fn) and abs(len(fn) - len(blob)) <= 3:
        return True
    # Conventional exonyms (Sennacherib = Sîn-ahhē-erība = EN.ZU-SZESZ.MESZ-SU).
    blob_a = fold_alnum(blob) + fold_alnum(atf or "")
    blob_s = blob_a.replace("sz", "s")
    for stem in _GLOSS_NAME_EXONYMS.get(fn, ()):
        st = fold_alnum(stem)
        if not st or len(st) < 6:
            continue
        if st in blob_a or st.replace("sz", "s") in blob_s:
            return True
    return False


def _is_atf_backed_number(word: str, atf: str, num_info=None) -> bool:
    bare = typo_fold(word).replace(",", "")
    # Ordinals (13th, 29th, 1st) are numbers, not content words, when the ATF
    # has number signs / -kam.
    if re.match(r"^\d+(?:st|nd|rd|th)$", bare, re.I):
        if re.search(r"\d|-kam\b", atf or "", re.I):
            return True
    if not _NUM_EN.match(bare) and not re.match(r"^\d+$", bare):
        return False
    # Sexagesimal 0;01 vs ATF 0.0.1 is notation, treat as backed if any
    # number signs exist or the ATF itself has a dotted capacity.
    if re.search(r"\d", atf or ""):
        return True
    if num_info and (num_info.get("licensed") or num_info.get("values")):
        return True
    # Try filter v2 parser: if *any* ATF number is present, accept notation.
    try:
        licensed, _units, _notes = fv.parse_atf_numbers(atf or "")
        if licensed:
            return True
    except Exception:
        pass
    return bool(re.search(r"\d", atf or ""))


def _is_atf_backed_loan(word: str, atf: str) -> bool:
    """Hyphenated or borrowed English that repeats an ATF surface (qutru-plant)."""
    raw = typo_fold(word).lower()
    parts = [p for p in re.split(r"[- ]+", raw) if len(fold_alnum(p)) >= 4]
    if not parts:
        # a single token of length >= 5 that is an ATF key (loan)
        fw = fold_alnum(word)
        if len(fw) < 5:
            return False
        parts = [word]
    _keys, folded = _atf_keys_folded(atf)
    for p in parts:
        fp = fold_alnum(p)
        if not fp or fp in _GLOSS_STOP:
            continue
        if fp in folded:
            return True
        for fk in folded:
            if abs(len(fk) - len(fp)) <= 1 and len(fp) >= 4:
                # one-char typo / vowel difference (qutru vs qutri)
                if sum(a != b for a, b in zip(fp.ljust(len(fk)), fk.ljust(len(fp)))) <= 1:
                    return True
    return False


def iter_content_words(atf, english, toks=None, num_info=None):
    """Yield original surface forms of content words (names/numbers/stops skipped)."""
    for w in _en_words(english):
        bare = typo_fold(w).lstrip("%").strip("[]()<>")
        if not bare:
            continue
        low = bare.lower()
        if low in _GLOSS_STOP:
            continue
        if _is_atf_backed_number(bare, atf, num_info=num_info):
            continue
        if _is_atf_backed_name(bare, atf, toks=toks, original=w):
            continue
        if _is_atf_backed_loan(bare, atf):
            continue
        if any(ch in w for ch in ARTIFACT_CHARS):
            continue
        if _LANG_TAG_RE.search(w) or re.match(r"^%(?:sux|akk|šu|szu|su)", w, re.I):
            continue
        fw = fold_alnum(bare)
        if len(fw) < 3:
            continue
        yield bare


def _parts_licensed(bare: str, allowed: set) -> bool:
    raw = typo_fold(bare).lower()
    parts = [p for p in re.split(r"[- ]+", raw) if p]
    if len(parts) < 2:
        return False
    for p in parts:
        if p in _GLOSS_STOP or len(fold_alnum(p)) < 2:
            continue
        cands = _syns(p) | {_lemmatize_en(p), fold_alnum(p), p}
        if not (cands & allowed):
            return False
    return True


def gloss_flag(atf: str, english: str, toks=None, num_info=None):
    """FLAG/score: content words with no official/mined per-sign gloss match.

    Returns a dict:
      n_content, n_unlicensed, unlicensed, ratio, score, allowed_n
    score == ratio (unlicensed / content, 0 if no content words).
    Never a hard drop by itself.
    """
    allowed = _allowed_gloss_lemmas(atf, toks=toks)
    unlicensed = []
    content = []
    for bare in iter_content_words(atf, english, toks=toks, num_info=num_info):
        content.append(bare)
        lem = _lemmatize_en(bare)
        fw = fold_alnum(bare)
        cands = _syns(bare) | {lem, fw}
        if cands & allowed:
            continue
        if _parts_licensed(bare, allowed):
            continue
        unlicensed.append(bare)
    n_c = len(content)
    n_u = len(unlicensed)
    ratio = (n_u / n_c) if n_c else 0.0
    return {
        "n_content": n_c,
        "n_unlicensed": n_u,
        "unlicensed": unlicensed,
        "ratio": round(ratio, 4),
        "score": round(ratio, 4),
        "allowed_n": len(allowed),
        "tier": "per_sign",
    }


def gloss_flag_corpus(atf: str, english: str, toks=None, num_info=None):
    """FLAG: content words not attested in the clean human-translation vocab."""
    vocab = corpus_vocab()
    vocab_set = set(vocab) if vocab else set()
    unlicensed = []
    content = []
    for bare in iter_content_words(atf, english, toks=toks, num_info=num_info):
        content.append(bare)
        lem = _lemmatize_en(bare)
        fw = fold_alnum(bare)
        cands = _syns(bare, use_wordnet=False) | {lem, fw, typo_fold(bare).lower()}
        if vocab_set and (cands & vocab_set):
            continue
        if not vocab_set:
            # no cache: do not judge
            continue
        unlicensed.append(bare)
    n_c = len(content)
    n_u = len(unlicensed)
    ratio = (n_u / n_c) if n_c else 0.0
    return {
        "n_content": n_c,
        "n_unlicensed": n_u,
        "unlicensed": unlicensed,
        "ratio": round(ratio, 4),
        "score": round(ratio, 4),
        "allowed_n": len(vocab_set),
        "tier": "corpus_vocab",
    }


def gloss_flag_reverse(atf: str, english: str, toks=None, num_info=None):
    """FLAG: content words whose known signs are all absent from the ATF.

    Words with no sign mapping get no judgment. unlicensed entries look like
    'lamb: expected sila4|udu'.
    """
    unlicensed = []
    unlicensed_words = []
    expected = {}
    unmapped = []
    content = []
    for bare in iter_content_words(atf, english, toks=toks, num_info=num_info):
        content.append(bare)
        signs, cfs = reverse_index_for_word(bare)
        raw = typo_fold(bare).lower()
        parts = [p for p in re.split(r"[- ]+", raw) if p and p not in _GLOSS_STOP and len(fold_alnum(p)) >= 3]
        if not signs and not cfs and len(parts) >= 2:
            # barge-man: judge the parts (barge, man)
            part_flags = []
            any_map = False
            for p in parts:
                ps, pc = reverse_index_for_word(p)
                if not ps and not pc:
                    continue
                any_map = True
                if not reverse_word_supported(p, atf, signs=ps, cfs=pc):
                    part_flags.append((p, ps, pc))
            if any_map and not part_flags:
                continue
            if any_map and part_flags:
                # flag the first unsupported part but label the compound
                p, ps, pc = part_flags[0]
                signs, cfs = ps, pc
            elif not any_map:
                unmapped.append(bare)
                continue
        elif not signs and not cfs:
            unmapped.append(bare)
            continue
        elif reverse_word_supported(bare, atf, signs=signs, cfs=cfs):
            continue
        elif len(parts) >= 2 and all(
            (not reverse_index_for_word(p)[0] and not reverse_index_for_word(p)[1])
            or reverse_word_supported(p, atf)
            for p in parts
        ):
            continue
        show = []
        for s in signs:
            if s not in show:
                show.append(s)
            if len(show) >= 6:
                break
        label = f"{bare}: expected " + ("|".join(show) if show else "|".join(cfs[:6]))
        unlicensed.append(label)
        unlicensed_words.append(bare)
        expected[_lemmatize_en(bare) or bare] = show or list(cfs[:6])
    n_c = len(content)
    n_u = len(unlicensed)
    # ratio is over content words (unmapped count as not-flagged, not unlicensed)
    ratio = (n_u / n_c) if n_c else 0.0
    return {
        "n_content": n_c,
        "n_unlicensed": n_u,
        "unlicensed": unlicensed,
        "unlicensed_words": unlicensed_words,
        "expected": expected,
        "unmapped": unmapped,
        "n_unmapped": len(unmapped),
        "ratio": round(ratio, 4),
        "score": round(ratio, 4),
        "tier": "reverse",
    }


# Suggested operating points (chosen after the v3-r1 offline run; see FILTER_V3.md).
# Not applied as a hard drop here.
SUGGESTED_GLOSS_RATIO = 0.40
SUGGESTED_GLOSS_COUNT = 2
# Reverse check is positive evidence of a wrong lexical choice, so a single
# mapped-but-absent word is enough to flag / (in strict reverse) reject.
REVERSE_GLOSS_COUNT = 1
REVERSE_GLOSS_RATIO = 0.40


def gloss_over_threshold(flag: dict, ratio=SUGGESTED_GLOSS_RATIO, count=SUGGESTED_GLOSS_COUNT,
                         min_content=0):
    """True if the flag meets the suggested (ratio OR count) threshold.

    If min_content > 0, the ratio limb only fires when n_content >= min_content
    (the count limb is unchanged). Used to measure the short-line ratio effect.
    """
    if not flag:
        return False
    n_u = flag.get("n_unlicensed", 0)
    n_c = flag.get("n_content", 0)
    if n_u >= count:
        return True
    if flag.get("ratio", 0) >= ratio and n_c >= min_content:
        return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

GLOSS_TIERS = ("per_sign", "corpus_vocab", "reverse")


def normalize_paraphrase(mode) -> str:
    """'strict' (chrF-phase default) or 'lenient' (flag-only paraphrases)."""
    m = (mode or "strict").strip().lower()
    if m not in {"strict", "lenient"}:
        raise ValueError(f"paraphrase must be 'strict' or 'lenient', got {mode!r}")
    return m


def normalize_gloss_tier(tier) -> str:
    t = (tier or "per_sign").strip().lower().replace("-", "_")
    aliases = {"forward": "per_sign", "mined": "per_sign", "vocab": "corpus_vocab",
               "corpus": "corpus_vocab", "flat": "corpus_vocab"}
    t = aliases.get(t, t)
    if t not in GLOSS_TIERS:
        raise ValueError(f"gloss_tier must be one of {GLOSS_TIERS}, got {tier!r}")
    return t


def check(atf, english, qwen=None, tablet=None, line_no=None, cands=None,
          genre=None, period=None, paraphrase="strict", gloss_tier="per_sign",
          ratio_min_content=0, **_):
    """Return {ok, fails, flags, info}. fails = hard drops; flags = scores.

    paraphrase='strict' (default, chrF phase): the selected gloss_tier FLAG
    becomes a hard reject ('gloss_unlicensed') when it meets its threshold.
    paraphrase='lenient': all gloss checks stay FLAGS only, keeping paraphrases.

    gloss_tier='per_sign' (default): forward official+synonym+mined list,
      threshold n_unlicensed >= 2 or ratio >= 0.40.
    gloss_tier='corpus_vocab': word not in the clean human-translation vocab,
      same 2 / 0.40 threshold.
    gloss_tier='reverse': a content word maps to known signs and none appear
      in the ATF; threshold n_unlicensed >= 1 (or ratio >= 0.40).

    ratio_min_content: if > 0, the ratio limb of the forward/corpus threshold
    only applies when n_content >= that value (count limb unchanged).
    All three flags are always computed and returned.
    """
    paraphrase = normalize_paraphrase(paraphrase)
    gloss_tier = normalize_gloss_tier(gloss_tier)
    v2 = fv.check(atf, english, qwen=qwen, tablet=tablet, line_no=line_no,
                  cands=cands)
    english_s = fv.strip_draft_labels(english or "")
    fails = list(v2.get("fails") or [])
    info = dict(v2.get("info") or {})
    toks = None
    if tablet:
        try:
            toks, _meta = ls.align_line(tablet, atf, line_no=line_no)
        except Exception:
            toks = None

    # v2 exceptions required by the v3 brief
    fails = suppress_sexagesimal_number_fails(fails, atf, english_s)
    fails = suppress_gloss_licensed_name_fails(fails, atf, english_s, toks=toks)

    extra = []
    extra.extend(check_accounting_invented(atf, english_s))
    extra.extend(check_artifact_symbols(english_s))
    extra.extend(check_language_tag_leak(atf, english_s))
    extra.extend(check_copy_through(atf, english_s, toks=toks))
    extra.extend(check_omen_template(atf, english_s, genre=genre))
    extra.extend(check_common_noun_as_pn(atf, english_s, toks=toks))

    seen = set(fails)
    for f in extra:
        if f not in seen:
            fails.append(f)
            seen.add(f)

    nums = info.get("numbers")
    flag = gloss_flag(atf, english_s, toks=toks, num_info=nums)
    flag_corpus = gloss_flag_corpus(atf, english_s, toks=toks, num_info=nums)
    flag_rev = gloss_flag_reverse(atf, english_s, toks=toks, num_info=nums)
    over = gloss_over_threshold(flag, min_content=ratio_min_content)
    over_corpus = gloss_over_threshold(flag_corpus, min_content=ratio_min_content)
    over_rev = gloss_over_threshold(
        flag_rev, ratio=REVERSE_GLOSS_RATIO, count=REVERSE_GLOSS_COUNT,
    )
    if gloss_tier == "per_sign":
        selected_over = over
    elif gloss_tier == "corpus_vocab":
        selected_over = over_corpus
    else:
        selected_over = over_rev
    if paraphrase == "strict" and selected_over:
        extra.append("gloss_unlicensed")
        if "gloss_unlicensed" not in seen:
            fails.append("gloss_unlicensed")
            seen.add("gloss_unlicensed")
    flags = {
        "gloss": flag,
        "gloss_over_threshold": over,
        "gloss_corpus": flag_corpus,
        "gloss_corpus_over_threshold": over_corpus,
        "gloss_reverse": flag_rev,
        "gloss_reverse_over_threshold": over_rev,
        "paraphrase": paraphrase,
        "gloss_tier": gloss_tier,
        "selected_over_threshold": selected_over,
    }
    info["genre"] = genre
    info["period"] = period
    info["v3_extra"] = extra
    info["paraphrase"] = paraphrase
    info["gloss_tier"] = gloss_tier
    return {"ok": not fails, "fails": fails, "flags": flags, "info": info}


if __name__ == "__main__":
    # Tiny smoke; the real suite is test_filter_v3.py.
    import argparse
    ap = argparse.ArgumentParser(description="Filter v3 smoke (see test_filter_v3.py)")
    ap.add_argument("--paraphrase", choices=("strict", "lenient"), default="strict",
                    help="strict (chrF phase): gloss threshold is a reject; "
                         "lenient: gloss stays a flag only")
    args = ap.parse_args()
    cases = [
        ("%sux 0.0.1 {d}nanna-kam", "0;01 Nanna-kam", None),
        ("%sux 0.0.1 {d}nanna-kam", "Subtotal: 0;01, of Nanna.", None),
        ("%sux ½ sila3 inda3 ½ sila3 tu7", "substitute: one lamb, one stewed lamb,", None),
        ("e2-temen-ni2-gur3-ru", "the House With a Foundation Clad in Fearsomeness,",
         "Official or display"),
    ]
    for atf, en, g in cases:
        r = check(atf, en, genre=g, paraphrase=args.paraphrase)
        print(atf, "=>", r["fails"], r["flags"]["gloss"], args.paraphrase)
