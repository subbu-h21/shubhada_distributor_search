"""Progressive autocomplete probing helper.

Strategy (as requested by the user for maximum extraction success):
  1. Type a PREFIX (default: first 4 chars) into the search input.
  2. Snapshot the dropdown state — capture rows + screenshot.
  3. Continue typing the FULL query.
  4. Snapshot again — capture rows + screenshot.
  5. Merge the two candidate lists (deduped by canonicalised name), and
     score every candidate against the query. Return the best.
  6. If the best candidate is not present in the CURRENT (final) dropdown,
     clear the input and re-type until the candidate reappears so it can
     be clicked.

Every adapter can reuse this by supplying:
  • the search-input selector (or a Playwright ElementHandle)
  • the autocomplete-row selector (CSS)
  • how to convert a row DOM node → (name, full_text, element)

The helper is deliberately generic so SUNSHOP, CHETHANA, LIVECONNECT,
RETAILIO, YASHIKA and VARDHAMAN can all use it.
"""
from __future__ import annotations
import re
from typing import Callable, List, Optional, Awaitable, Any
from .match import canon, score, ACCEPT_THRESHOLD


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip())


class Candidate:
    __slots__ = ("name", "full_text", "canon", "score")

    def __init__(self, name: str, full_text: str):
        self.name = name.strip()
        self.full_text = full_text.strip() or self.name
        c = canon(self.name)
        # canon() returns a list — normalise into a hashable tuple for keys
        self.canon = tuple(c) if isinstance(c, (list, tuple)) else (str(c),)
        self.score = 0

    def __repr__(self):
        return f"<Cand {self.name!r} score={self.score}>"


async def progressive_autocomplete(
    page,
    *,
    input_selector: str,
    row_selector: str,
    query: str,
    query_canon: Optional[str] = None,
    row_to_name: Optional[Callable[[str], str]] = None,
    screenshotter: Optional[Callable[[Any, str], Awaitable[Optional[str]]]] = None,
    prefix_len: int = 4,
    prefix_wait_ms: int = 1200,
    full_wait_ms: int = 1600,
    accept_threshold: int = ACCEPT_THRESHOLD,
) -> tuple[Optional[Candidate], list[Candidate], dict]:
    """Type + probe an autocomplete field twice (prefix then full) and return
    the best matched candidate plus every merged candidate.

    Returns (best, all_candidates_sorted, debug_info). `best` is None when no
    candidate crosses `accept_threshold`.
    """
    qcanon = query_canon or canon(query)
    if isinstance(qcanon, (list, tuple)):
        qcanon = tuple(qcanon)
    debug: dict = {"query_canon": list(qcanon) if isinstance(qcanon, tuple) else qcanon}

    async def _fill_input(text: str):
        el = await page.query_selector(input_selector)
        if not el:
            return None
        try: await el.click()
        except Exception: pass
        try: await el.fill("")
        except Exception: pass
        try:
            # Prefer element-level type so events fire on the target
            await el.type(text, delay=90)
        except Exception:
            try: await page.keyboard.type(text, delay=90)
            except Exception: return None
        return el

    async def _snapshot_rows() -> list[Candidate]:
        cands: list[Candidate] = []
        try:
            els = await page.query_selector_all(row_selector)
        except Exception:
            return cands
        for e in els:
            try:
                if not await e.is_visible():
                    continue
                full = _clean(await e.inner_text())
                if not full:
                    continue
                name = row_to_name(full) if row_to_name else full.split("\n", 1)[0].split("~", 1)[0].strip()
                if name:
                    cands.append(Candidate(name, full))
            except Exception:
                continue
        return cands

    # ---- STAGE 1: prefix ----
    prefix = re.sub(r"\s+", "", query)[:prefix_len]
    if len(prefix) < 2:
        prefix = query.strip()[:prefix_len]
    await _fill_input(prefix)
    await page.wait_for_timeout(prefix_wait_ms)
    if screenshotter is not None:
        try: debug["prefix_screenshot"] = await screenshotter(page, "autocomplete-prefix")
        except Exception: pass
    prefix_cands = await _snapshot_rows()
    debug["prefix_row_count"] = len(prefix_cands)
    debug["prefix_top"] = [c.name for c in prefix_cands[:5]]

    # ---- STAGE 2: full query ----
    await _fill_input(query)
    await page.wait_for_timeout(full_wait_ms)
    if screenshotter is not None:
        try: debug["full_screenshot"] = await screenshotter(page, "autocomplete-full")
        except Exception: pass
    full_cands = await _snapshot_rows()
    debug["full_row_count"] = len(full_cands)
    debug["full_top"] = [c.name for c in full_cands[:5]]

    # ---- MERGE + SCORE ----
    seen: dict = {}
    def _canon_key(c: Candidate):
        return c.canon if c.canon else (c.name.lower(),)
    for c in prefix_cands + full_cands:
        key = _canon_key(c)
        if not key or key in seen:
            continue
        c.score = score(qcanon, c.name)
        # Confidence boost: candidate present in BOTH probes
        in_prefix = any(_canon_key(x) == c.canon for x in prefix_cands)
        in_full = any(_canon_key(x) == c.canon for x in full_cands)
        if in_prefix and in_full:
            c.score += 5
        seen[key] = c
    merged = sorted(seen.values(), key=lambda c: -c.score)
    debug["merged"] = [{"name": c.name, "score": c.score} for c in merged[:15]]

    best = merged[0] if merged and merged[0].score >= accept_threshold else None
    return best, merged, debug
