"""Tokenizer fix (step 1 of Hayden's 4-step plan, 2026-10-19). Shared by every train / dev / eval / inference path.

Approach (see PLAN_TOKFIX.md):
 (a) normalize_atf(): deterministic Unicode-ATF -> CDLI-ASCII ATF (the corpus's dominant convention):
     š->sz ṣ->s, ṭ->t, ḫ->h ŋ/ĝ->j ś->s' ʾʿ->' , accented vowels -> index digits (ú->u2, ù->u3, É->E2 ...),
     subscript digits -> digits, half brackets ⸢x⸣ -> x# , 〈 〉 -> < >.  (atfutil.to_cdli_ascii + small extras)
 (b) new vocabulary pieces appended to the Unigram model (ids 32100+, inside the SentencePiece model, so whitespace
     handling and decoding stay exact; HF "added tokens" broke spacing): { } < << >> \\ , the top determinatives as
     whole pieces ({d} {m} {1} {ki} {lu2} ...), and the diacritic letters that remain in English targets and in
     normalized Akkadian (š Š ā ī ū ē â ê î û ṣ ṭ ḫ ...).
 (c) anything the new tokenizer still cannot round-trip is escaped with the old reversible atfcodec escapes (&u2014 ...),
     so the unk rate is exactly 0 and decode() is the old codec decode (production-compatible)."""
import os, sys, json, re, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser('~/cursor/unread-db/lib')); sys.path.insert(0, os.path.expanduser('~/cursor/atf-mix/mix'))
from atfutil import to_cdli_ascii
import atfcodec
from atfcodec import decode  # unchanged inverse of the escapes
TOKDIR = os.path.join(HERE, 'tokenizer')
PREFIX = 'translate Akkadian to English: '
EXTRA = str.maketrans({'〈': '<', '〉': '>', 'ĝ': 'j', 'Ĝ': 'J', '₍': '(', '₎': ')'})
# ORACC / eBL / CDLI inline language-protocol tags. These are edition
# markup, not Sumerian or Akkadian to be translated. Leaving them in
# model input is the cause of `Subtotal:` / `surplus:` / `%sú` /
# `(Sum)`/`(Akk)` / "es priest" hallucinations (see
# runs/loop-pilot/ob-lit-v1/LITERARY_SIDE_BY_SIDE.md and
# data/na/tokfix/test_lang_tags.py). Longest codes first. Applied after
# to_cdli_ascii so `%šu` has already become `%szu`.
_LANG_TAG_RE = re.compile(
    r"""(?ix)
    (?<!\w)
    %
    (?:
        sux(?:-x-[\w]+)?
      | akk(?:-x-[\w]+)?
      | szu                  # CDLI-ASCII form of %šu
      | nshu
      | elx | arc | qpc | qcu | qeb
      | hit | hur | uga | peo | grc
      | es | sb | su
      | n                    # eBL normalized-reading marker, e.g. %n <(...)>
      | e | a                # short Akkadian / Emesal
    )
    \b
    """
)


def strip_oracc_lang_tags(s: str) -> str:
    """Remove ATF language-protocol tags; keep the rest of the line.

    `%sux lugal-an-dil2` -> `lugal-an-dil2`
    `%sux foo & %akk bar` -> `foo & bar`
    `dub3 = %a 5(disz)` -> `dub3 = 5(disz)`
    Idempotent. Does not touch `%` that is not a protocol tag.
    """
    if not s:
        return s or ""
    s = _LANG_TAG_RE.sub(" ", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r" *& *", " & ", s)
    s = re.sub(r" += +", " = ", s)
    return s.strip()


def lang_tag_strip_enabled() -> bool:
    """Off/on switch for protocol-tag stripping. Default ON.

    Official eval (adopted 2026-11-24) is TOKFIX_STRIP_LANG_TAGS=1;
    official ctrl baseline on the 965-line gate is 34.32. See
    docs/EVAL_PROTOCOL.md. TOKFIX_STRIP_LANG_TAGS=0/false/off/no
    disables it (reproduces the previous published 34.02). The model
    prefix `translate Akkadian to English: ` is never changed.
    """
    v = os.environ.get("TOKFIX_STRIP_LANG_TAGS", "1").strip().lower()
    return v not in {"0", "false", "off", "no"}


def normalize_atf(s):
    if not s: return s or ''
    s = unicodedata.normalize('NFC', s).translate(EXTRA)
    s = to_cdli_ascii(s)
    if lang_tag_strip_enabled():
        s = strip_oracc_lang_tags(s)
    return s
_SPEC = None
def spec():
    global _SPEC
    if _SPEC is None: _SPEC = json.load(open(os.path.join(TOKDIR, 'tokfix_spec.json')))
    return _SPEC
_SAFE = None
def _escape(s):
    global _SAFE
    if _SAFE is None: _SAFE = set(spec()['safe_chars'])
    out = []
    for ch in s:
        if ch == '&': out.append('&&')
        elif ch in _SAFE: out.append(ch)
        elif ch in '\n\t\r': out.append(' ')
        else:
            e = atfcodec._esc(ch); out.append(e if e != ch else '&u%04x' % ord(ch))
    return ''.join(out)
def encode_tgt(s):
    """English side (targets, and English gloss hints inside inputs)."""
    return _escape(unicodedata.normalize('NFC', s or ''))
def encode_atf(s):
    """A pure ATF string (current line and its =P= / =N= neighbours)."""
    return _escape(normalize_atf(s))
def encode_input(inp):
    """Full model input as built by abl_common.make_input: '<atf> [=P= <atf> =N= <atf>] [=G= <english glosses>]'."""
    inp = inp or ''
    if ' =G= ' in inp:
        a, g = inp.split(' =G= ', 1); return encode_atf(a) + ' =G= ' + encode_tgt(g)
    return encode_atf(inp)
def model_input(inp): return PREFIX + encode_input(inp)
def load_tokenizer(path=TOKDIR):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(path)
def extend_model(model, old_tok, new_tok, old_encode=lambda p: atfcodec.encode(p, atf=True)):
    """Resize the (tied) embeddings for the new pieces; each new row = mean of the old embeddings of the pieces the OLD
    pipeline produced for that string (old codec escapes + old tokenizer), leading '▁' dropped. Returns {piece: old pieces}."""
    import torch
    n_old = len(old_tok); n_new = len(new_tok); emb = model.get_input_embeddings()
    if emb.weight.shape[0] < n_new: model.resize_token_embeddings(n_new, pad_to_multiple_of=64)
    emb = model.get_input_embeddings(); W = emb.weight.data; info = {}
    with torch.no_grad():
        for i in range(n_old, n_new):
            p = new_tok.convert_ids_to_tokens(i)
            ids = old_tok(old_encode(p), add_special_tokens=False).input_ids
            if len(ids) > 1 and ids[0] == 3: ids = ids[1:]
            ids = [x for x in ids if x != old_tok.unk_token_id] or [3]
            W[i] = W[ids].mean(0); info[p] = old_tok.convert_ids_to_tokens(ids)
    if not model.config.tie_word_embeddings:  # T5 v1 is tied; kept for safety
        model.get_output_embeddings().weight.data[n_old:n_new] = W[n_old:n_new]
    return info
