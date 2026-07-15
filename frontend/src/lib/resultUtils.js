/**
 * Expands aggregator distributor results (LIVECONNECT, RETAILIO) into one
 * row per underlying seller so every seller shows up as its own card in the
 * results screen. SUNSHOP already has one distributor per row (SAROJ, HEGDE,
 * KAPILA PHARMA, KAPILA MEDICAL, CHIRAG PHARMA, CHETHANA PHARMA, YASHIKA
 * etc.) so those results pass through unchanged.
 *
 * Behavior:
 *   - If `result.items` contains 2+ entries where each has a `.seller`
 *     field, we split it into N results — one per (seller × variant).
 *   - Otherwise we pass the original result through unchanged.
 */
export function explodeResults(results) {
  if (!Array.isArray(results)) return [];
  const out = [];
  for (const r of results) {
    const items = Array.isArray(r.items) ? r.items : [];
    const sellerItems = items.filter((it) => it && it.seller);
    if (sellerItems.length >= 2) {
      sellerItems.forEach((it, idx) => {
        const sellerName = it.seller || `Seller ${idx + 1}`;
        const stockNum = it.available_qty && /^\d+$/.test(it.available_qty) ? parseInt(it.available_qty) : null;
        const status = stockNum === null ? r.status : stockNum > 0 ? 'SUCCESS' : 'NOT_FOUND';
        out.push({
          ...r,
          targetId: `${r.targetId}::${idx}`,
          targetName: `${r.targetName} — ${sellerName}`,
          items: [it],
          status,
          detail: stockNum !== null ? `Stock ${stockNum}${it.mrp ? ` · MRP ₹${it.mrp}` : ''}${it.ptr ? ` · PTR ₹${it.ptr}` : ''}` : r.detail,
          // Keep screenshots on the parent aggregator only (first exploded row)
          // to avoid duplicate large images.
          loginScreenshot: idx === 0 ? r.loginScreenshot : null,
          searchScreenshot: idx === 0 ? r.searchScreenshot : null,
          resultsScreenshot: idx === 0 ? r.resultsScreenshot : null,
          debug: idx === 0 ? r.debug : {},
          // The manual-pick fallback lives on the aggregator card only.
          canFulfill: null,
        });
      });
    } else {
      out.push(r);
    }
  }
  return out;
}
