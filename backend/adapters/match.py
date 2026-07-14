"""Shared product-name canonicalization + fuzzy-match scoring.

Used by every distributor adapter so that the same product query matches the
same SKU regardless of pack/unit/special-char variations.

Rules:
  1. Lowercase; replace any non-alphanumeric with a space.
  2. Strip trailing units from mixed tokens: 25mg -> 25, 100ml -> 100, 25tabs -> 25.
  3. Drop pack tokens (standalone `\\d+s` like 10s, 15s, 20s, 100s).
  4. Drop pure unit words (mg, ml, tab, cap, tablet, capsule, syrup, etc.).
  5. KEEP alphabetic modifiers (xl, sr, xr, dt, am, plus, beta, forte, ...).

Match rule (see `score`):
  +50  canonical exact match
  +30  candidate has trailing alphabetic modifier(s) after query prefix
  +5   token-set overlap (weak fallback)
  -50  candidate has a different STRENGTH number right after the query prefix
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
}
UNIT_SUFFIX_RE = re.compile(
    r"^(\d+(?:\.\d+)?)(mg|mcg|ml|iu|gm|g|tab|tabs|cap|caps|tablet|tablets|capsule|capsules)$"
)
PACK_RE = re.compile(r"^\d+s$")  # 10s, 15s, 20s, 100s


def canon(text: str) -> List[str]:
    """Return canonical tokens for a product name string."""
    raw = re.findall(r"[a-z0-9]+", (text or "").lower())
    out: List[str] = []
    for tok in raw:
        if tok in UNIT_WORDS:
            continue
        if PACK_RE.match(tok):
            continue
        m = UNIT_SUFFIX_RE.match(tok)
        if m:
            out.append(m.group(1))
            continue
        out.append(tok)
    return out


def score(query_canon: List[str], candidate_text: str) -> int:
    """Score how well a candidate suggestion matches the query."""
    cand = canon(candidate_text)
    n = len(query_canon)
    if n == 0 or len(cand) < n:
        return -100
    if cand[:n] != query_canon:
        # Weak fallback: all query tokens somewhere in candidate
        if all(t in cand for t in query_canon):
            return 5
        return -100
    extras = cand[n:]
    if not extras:
        return 50
    nxt = extras[0]
    if nxt.isdigit() or re.match(r"^\d+(?:\.\d+)?$", nxt):
        # Different strength (25 vs 50) — reject
        return -50
    return 30 - 5 * len(extras)


# Threshold used by all adapters: accept 30 (prefix + 1 modifier) and above.
# Reject 5 (weak fallback) and -50 (wrong strength).
ACCEPT_THRESHOLD = 25
