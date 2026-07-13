import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ProductsAPI } from '../lib/api';
import { Search, Loader2, ChevronDown, X } from 'lucide-react';

/**
 * Server-side searchable combobox for the product master.
 * Debounces user input (300ms), fetches top 20 matches from /api/products/search,
 * shows a dropdown, and lets the user pick one or type freely.
 */
const ProductCombobox = ({ value, onChange, placeholder = 'enter product name', className = '' }) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value || '');
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [masterEmpty, setMasterEmpty] = useState(false);
  const debounceRef = useRef(null);
  const boxRef = useRef(null);

  // Sync external value changes into input (only when combobox is closed to avoid caret jumps)
  useEffect(() => {
    if (!open && value !== query) setQuery(value || '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // Server search with debounce
  useEffect(() => {
    if (!open) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        setLoading(true);
        const list = await ProductsAPI.search(query, 20);
        setSuggestions(list);
        setHighlight(0);
        setMasterEmpty(query === '' && list.length === 0);
      } catch (e) {
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    }, 260);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [query, open]);

  // Close on outside click
  useEffect(() => {
    const onDoc = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const commit = (name) => {
    setQuery(name);
    onChange(name);
    setOpen(false);
  };

  const onKeyDown = (e) => {
    if (!open) {
      if (e.key === 'ArrowDown') { setOpen(true); return; }
      return;
    }
    if (e.key === 'ArrowDown') { e.preventDefault(); setHighlight((h) => Math.min(h + 1, suggestions.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHighlight((h) => Math.max(h - 1, 0)); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      const chosen = suggestions[highlight];
      if (chosen) commit(chosen.name);
      else { onChange(query); setOpen(false); }
    }
    else if (e.key === 'Escape') { setOpen(false); }
  };

  return (
    <div ref={boxRef} className={`relative ${className}`}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" strokeWidth={2} />
        <input
          value={query}
          onChange={(e) => { setQuery(e.target.value); onChange(e.target.value); if (!open) setOpen(true); }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          className="w-full h-14 pl-10 pr-10 border border-neutral-300 rounded-sm bg-white text-[16px] font-medium tracking-tight focus:outline-none focus:border-emerald-600 placeholder:text-neutral-400"
        />
        <button type="button" onClick={() => setOpen((v) => !v)} className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-neutral-500 hover:text-neutral-900">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronDown className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`} />}
        </button>
      </div>

      {open && (
        <div className="absolute z-40 top-full left-0 right-0 mt-1 bg-white border border-neutral-300 rounded-sm shadow-lg max-h-72 overflow-y-auto">
          {suggestions.length === 0 && !loading && (
            <div className="px-3 py-3 text-[11px] mono-track-tight text-neutral-500">
              {masterEmpty
                ? 'No product master uploaded. Upload one from Portals → PRODUCT MASTER.'
                : query ? `No match for "${query}" — you can still type your own.` : 'Type to search products…'}
            </div>
          )}
          {suggestions.map((s, i) => (
            <button
              key={s.id}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => commit(s.name)}
              className={`w-full text-left px-3 py-2.5 flex items-center justify-between gap-3 border-b border-neutral-100 last:border-b-0 ${i === highlight ? 'bg-emerald-50' : 'hover:bg-emerald-50'}`}
            >
              <span className="text-[13px] font-semibold uppercase truncate">{s.name}</span>
              {s.pack && <span className="shrink-0 text-[10px] mono-track-wide text-neutral-500">{s.pack}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProductCombobox;
