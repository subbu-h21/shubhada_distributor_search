import React, { useMemo, useState } from 'react';
import { PackageCheck, TrendingDown, MapPin, X } from 'lucide-react';

/** Extract a "location" hint from an exploded result. */
const locationOf = (r) => {
  const it = (r.items || [])[0] || {};
  // 1. seller name "Foo Pharma, Hubballi" → Hubballi
  const s = (it.seller || '').trim();
  if (s.includes(',')) {
    const parts = s.split(',');
    const tail = parts[parts.length - 1].trim();
    if (tail.length > 1 && tail.length < 40) return tail;
  }
  // 2. distributor.location field (SUNSHOP etc.)
  if (r.location) return r.location;
  // 3. Target name suffix (rare)
  return null;
};

/** Parse a numeric PTR (handles commas, ₹, spaces). null if not present. */
const ptrOf = (r) => {
  const it = (r.items || [])[0] || {};
  const raw = (it.ptr || '').toString().replace(/[^\d.]/g, '');
  const n = raw ? parseFloat(raw) : NaN;
  return Number.isFinite(n) && n > 0 ? n : null;
};

const isInStock = (r) => {
  const it = (r.items || [])[0] || {};
  const q = it.available_qty;
  if (q === undefined || q === null || q === '') return false;
  if (typeof q === 'number') return q > 0;
  const s = String(q).toLowerCase();
  if (s === 'yes' || s === 'in-stock' || s === 'available' || s === 'partial') return true;
  const n = parseInt(String(q).replace(/[^\d]/g, ''), 10);
  return Number.isFinite(n) && n > 0;
};

/**
 * Renders the filter chip row and returns the filtered+sorted results via
 * children render-prop.
 *
 * <ResultFilters results={exploded}>
 *   {(shown) => shown.map(r => <ResultCard ... />)}
 * </ResultFilters>
 */
const ResultFilters = ({ results, children }) => {
  const [inStock, setInStock] = useState(false);
  const [byPtr, setByPtr] = useState(false);
  const [loc, setLoc] = useState('');

  const locations = useMemo(() => {
    const set = new Set();
    for (const r of results) {
      const l = locationOf(r);
      if (l) set.add(l);
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [results]);

  const filtered = useMemo(() => {
    let out = results.slice();
    if (inStock) out = out.filter(isInStock);
    if (loc) out = out.filter((r) => (locationOf(r) || '').toLowerCase() === loc.toLowerCase());
    if (byPtr) {
      out.sort((a, b) => {
        const pa = ptrOf(a); const pb = ptrOf(b);
        if (pa === null && pb === null) return 0;
        if (pa === null) return 1;
        if (pb === null) return -1;
        return pa - pb;
      });
    }
    return out;
  }, [results, inStock, byPtr, loc]);

  const total = results.length;
  const shown = filtered.length;
  const anyActive = inStock || byPtr || loc;

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          onClick={() => setInStock((v) => !v)}
          data-testid="chip-in-stock"
          className={`h-7 px-2.5 rounded-full inline-flex items-center gap-1 text-[10px] mono-track-wide font-bold border transition-colors ${
            inStock ? 'bg-emerald-600 border-emerald-600 text-white' : 'bg-white border-neutral-300 text-neutral-700 hover:border-emerald-600'
          }`}
        >
          <PackageCheck className="w-3 h-3" /> IN-STOCK
        </button>

        <button
          type="button"
          onClick={() => setByPtr((v) => !v)}
          data-testid="chip-lowest-ptr"
          className={`h-7 px-2.5 rounded-full inline-flex items-center gap-1 text-[10px] mono-track-wide font-bold border transition-colors ${
            byPtr ? 'bg-emerald-600 border-emerald-600 text-white' : 'bg-white border-neutral-300 text-neutral-700 hover:border-emerald-600'
          }`}
        >
          <TrendingDown className="w-3 h-3" /> LOWEST PTR
        </button>

        {locations.length > 0 && (
          <div className="relative inline-flex items-center">
            <MapPin className="w-3 h-3 absolute left-2 pointer-events-none text-neutral-500" />
            <select
              value={loc}
              onChange={(e) => setLoc(e.target.value)}
              data-testid="chip-location-select"
              className={`h-7 pl-6 pr-2 rounded-full text-[10px] mono-track-wide font-bold border cursor-pointer transition-colors appearance-none ${
                loc ? 'bg-emerald-600 border-emerald-600 text-white' : 'bg-white border-neutral-300 text-neutral-700 hover:border-emerald-600'
              }`}
            >
              <option value="">LOCATION</option>
              {locations.map((l) => (
                <option key={l} value={l} className="text-neutral-900 bg-white">{l.toUpperCase()}</option>
              ))}
            </select>
          </div>
        )}

        {anyActive && (
          <button
            type="button"
            onClick={() => { setInStock(false); setByPtr(false); setLoc(''); }}
            data-testid="chip-clear"
            className="h-7 px-2.5 rounded-full inline-flex items-center gap-1 text-[10px] mono-track-wide font-bold border border-red-300 text-red-600 hover:bg-red-50"
          >
            <X className="w-3 h-3" /> CLEAR
          </button>
        )}

        <span className="ml-auto text-[10px] mono-track-wide text-neutral-500 font-semibold">
          {anyActive ? `${shown} / ${total}` : `${total} SELLERS`}
        </span>
      </div>

      {typeof children === 'function' ? children(filtered) : null}
    </div>
  );
};

export default ResultFilters;
