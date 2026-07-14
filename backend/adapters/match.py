"""Shared product-name canonicalization + fuzzy-match scoring.

Used by every distributor adapter so that the same product query matches the
same SKU regardless of pack/unit/special-char variations, AND handles
combination drugs (e.g. ECOSPRIN AV 75/10, TELMIKIND AM 40/5).

Rules:
  1. Lowercase; replace any non-alphanumeric with a space.
  2. Strip trailing units from mixed tokens: 25mg -> 25, 100ml -> 100, 25tabs -> 25.
  3. Drop pack tokens (standalone `\\d+s` like 10s, 15s, 20s, 100s).
  4. Drop pure unit / packaging words (mg, ml, tab, cap, tablet, capsule,
     syrup, pack, kit, strip, ...).
  5. KEEP alphabetic modifiers (xl, sr, xr, dt, am, plus, beta, forte, ...).
  6. **Merge consecutive numeric tokens into a combo strength**: after step 4,
     if two adjacent tokens are both plain digits (<=4 chars), merge them as
     `X/Y`. This makes these forms all identical:
         "ECOSPRIN AV 75/10"
         "ECOSPRIN AV 75 10"
         "ECOSPRIN AV 75-10"
     -> canonical = ['ecosprin', 'av', '75/10'].

Match rule (see `score`):
  +50  canonical exact match
  +45  candidate is a *combo variant* whose last-position token is `Q/Y`
       where Q is the query's last strength (e.g., query "ECOSPRIN AV 75"
       matches candidate "ECOSPRIN AV 75/10").
  +40  candidate is a combo variant with extra tokens beyond the combo.
  +30  candidate has an alphabetic modifier after the query prefix
       (e.g., BETA, PLUS).
  +5   token-set overlap (weak fallback).
  -50  candidate begins with a different strength number in the last position
       (e.g., 25 vs 50).
  -100 unrelated.
"""
from __future__ import annotations
import re
from typing import List

UNIT_WORDS = {
    "mg", "mcg", "ml", "iu", "g", "gm", "kg",
    "tab", "tabs", "tablet", "tablets",
    "cap", "caps", "capsule", "capsules",
    "syp", "syrup", "susp", "suspension",
    "drop", "drops", "ointment", "cream", "gel",
    "inj", "injection", "sol", "solution", "lotion",
    "sachet", "sachets", "powder", "spray", "lozenge", "lozenges",
    "pack", "packs", "strip", "strips", "kit", "kits", "bottle", "bottles",
    "amp", "ampoule", "ampoules", "vial", "vials",
}
UNIT_SUFFIX_RE = re.compile(
    r"^(\d+(?:\.\d+)?)(mg|mcg|ml|iu|gm|g|tab|tabs|cap|caps|tablet|tablets|capsule|capsules)$"
)
PACK_RE = re.compile(r"^\d+s$")  # 10s, 15s, 20s, 100s
PURE_NUM_RE = re.compile(r"^\d{1,4}(?:\.\d+)?$")


def canon(text: str) -> List[str]:
    """Return canonical tokens for a product name string."""
    raw = re.findall(r"[a-z0-9]+", (text or "").lower())
    stripped: List[str] = []
    for tok in raw:
        if tok in UNIT_WORDS:
            continue
        if PACK_RE.match(tok):
            continue
        m = UNIT_SUFFIX_RE.match(tok)
        if m:
            stripped.append(m.group(1))
            continue
        stripped.append(tok)

    # Merge consecutive numeric tokens into combo strengths:
    #   ['ecosprin','av','75','10']  -> ['ecosprin','av','75/10']
    #   ['telmikind','am','40','5']  -> ['telmikind','am','40/5']
    merged: List[str] = []
    for tok in stripped:
        if merged and PURE_NUM_RE.match(tok) and PURE_NUM_RE.match(merged[-1].split("/")[-1] or ""):
            merged[-1] = f"{merged[-1]}/{tok}"
        else:
            merged.append(tok)
    return merged


def _num_prefix(token: str) -> str:
    """Return the leading numeric segment of a token (before any '/')."""
    return token.split("/", 1)[0] if token else ""


def score(query_canon: List[str], candidate_text: str) -> int:
    """Score how well a candidate suggestion matches the query."""
    cand = canon(candidate_text)
    n = len(query_canon)
    if n == 0 or len(cand) < n:
        return -100

    # Match all positions except the last exactly
    for i in range(n - 1):
        if cand[i] != query_canon[i]:
            # Weak fallback: all query tokens present anywhere
            if all(t in cand for t in query_canon):
                return 5
            return -100

    last_q, last_c = query_canon[-1], cand[n - 1]
    extras = cand[n:]

    # 1. Exact match at last position
    if last_c == last_q:
        if not extras:
            return 50
        nxt = extras[0]
        # After canonicalization, a bare digit as first extra means an ADDITIONAL
        # strength that wasn't combined into the canonical (rare). Reject.
        if PURE_NUM_RE.match(nxt):
            return -50
        return 30 - 5 * len(extras)

    # 2. Combo variant: query says "75", candidate says "75/10".
    #    This means the user typed the primary strength and the distributor
    #    stocks a combination product with that primary strength — MATCH.
    if last_q.isdigit() and last_c.startswith(f"{last_q}/"):
        return 45 if not extras else 40 - 5 * len(extras)

    # 3. Reverse combo: query is a combo, candidate is single. Unlikely but
    #    allow it as a mild positive.
    if last_c.isdigit() and last_q.startswith(f"{last_c}/"):
        return 35 if not extras else 30 - 5 * len(extras)

    # 4. Same numeric prefix but different combo (e.g., query "75/10" vs cand
    #    "75/20"). Different combination → different SKU.
    q_num, c_num = _num_prefix(last_q), _num_prefix(last_c)
    if q_num and c_num and q_num == c_num and (q_num != last_q or c_num != last_c):
        # Same primary strength, different secondary combo
        return -30

    # 5. Not a prefix match at last position — weak fallback
    if all(t in cand for t in query_canon):
        return 5
    return -100


# Threshold used by all adapters: accept 25 (prefix + 1 modifier) and above.
ACCEPT_THRESHOLD = 25
