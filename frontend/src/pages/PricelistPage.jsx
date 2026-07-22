import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Upload, Search, Trash2, Loader2, CheckCircle2, AlertTriangle, Database, Building2, MapPin, Tag, ShoppingCart, X, ArrowDown } from 'lucide-react';
import { PricelistAPI, DistributorsAPI } from '../lib/api';
import { toast } from 'sonner';
import AddToOrderSheet from '../components/AddToOrderSheet';

/** Additive feature: browse & manage the local Distributor Price-List Vault.
 *  Does NOT touch the live-extraction flow. Two tabs: SEARCH, MANAGE. */

const FIELD_LABELS = {
  product: 'Product Name *',
  company: 'Company / Manufacturer',
  pack:    'Pack',
  mrp:     'MRP',
  ptr:     'PTR / Rate',
  scheme:  'Scheme',
};

const inr = (v) => (typeof v === 'number' && !Number.isNaN(v)) ? `₹${v.toFixed(2)}` : '—';

// -----------------------------------------------------------------
// SEARCH TAB — instant search across all uploaded distributor rows
// -----------------------------------------------------------------
const SearchTab = () => {
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState({ groups: [], count: 0 });
  const [orderDialog, setOrderDialog] = useState(null);

  useEffect(() => {
    let cancelled = false;
    if (!q.trim() || q.trim().length < 2) { setData({ groups: [], count: 0 }); return; }
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const res = await PricelistAPI.search(q.trim());
        if (!cancelled) setData(res);
      } catch (e) {
        toast.error(e?.response?.data?.detail || 'Search failed');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => { cancelled = true; clearTimeout(t); };
  }, [q]);

  return (
    <div className="space-y-4">
      {/* Search input */}
      <div className="flex items-center gap-2 border-2 border-neutral-950 rounded-sm h-12 px-3">
        <Search className="w-4 h-4 text-neutral-500 shrink-0" />
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search product across all uploaded price lists..."
          className="flex-1 outline-none text-[14px] font-semibold placeholder:font-normal placeholder:text-neutral-400"
          data-testid="pricelist-search-input"
          autoFocus
        />
        {loading && <Loader2 className="w-4 h-4 text-emerald-600 animate-spin" />}
        {q && !loading && (
          <button onClick={() => setQ('')} className="text-neutral-400 hover:text-neutral-900" data-testid="pricelist-clear">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Result groups */}
      {q.length >= 2 && !loading && data.count === 0 && (
        <div className="text-center py-16 text-neutral-500 text-[12px] mono-track-wide">
          NO MATCHES · TRY A DIFFERENT SPELLING OR UPLOAD MORE PRICE LISTS
        </div>
      )}

      <div className="space-y-3" data-testid="pricelist-results">
        {data.groups.map((g) => (
          <div key={g.product_norm} className="border border-neutral-200 rounded-sm overflow-hidden bg-white">
            {/* Group header */}
            <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-200 flex items-start gap-3">
              <Tag className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-[14px] font-bold uppercase tracking-tight text-neutral-950">{g.product}</div>
                {g.company && (
                  <div className="text-[10px] mono-track-wide text-neutral-500 mt-0.5 flex items-center gap-1">
                    <Building2 className="w-3 h-3" /> {g.company}
                  </div>
                )}
              </div>
              {g.cheapest_ptr != null && (
                <div className="text-right">
                  <div className="text-[9px] mono-track-wide text-emerald-700 font-bold">CHEAPEST PTR</div>
                  <div className="text-[16px] font-black text-emerald-700 mono-track">{inr(g.cheapest_ptr)}</div>
                </div>
              )}
            </div>

            {/* Distributor rows */}
            <ul className="divide-y divide-neutral-100">
              {g.distributors.map((d, i) => {
                const isCheapest = d.ptr != null && d.ptr === g.cheapest_ptr;
                return (
                  <li key={i} className={`px-4 py-2.5 flex items-center gap-3 ${isCheapest ? 'bg-emerald-50/50' : ''}`}
                      data-testid={`pl-row-${g.product_norm}-${i}`}>
                    <div className="min-w-0 flex-1">
                      <div className="text-[12px] font-bold text-neutral-950 flex items-center gap-1.5">
                        {isCheapest && <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500"></span>}
                        {d.distributor_name}
                      </div>
                      <div className="text-[10px] mono-track-tight text-neutral-500 mt-0.5">
                        {d.pack ? `${d.pack} · ` : ''}
                        {d.scheme ? `SCH ${d.scheme} · ` : ''}
                        MRP {inr(d.mrp)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[9px] mono-track-wide text-neutral-500">PTR</div>
                      <div className={`text-[14px] font-black mono-track ${isCheapest ? 'text-emerald-700' : 'text-neutral-950'}`}>
                        {inr(d.ptr)}
                      </div>
                    </div>
                    <button
                      className="h-9 px-3 border border-neutral-300 rounded-sm text-[10px] mono-track-wide font-bold hover:border-emerald-600 hover:text-emerald-700 press flex items-center gap-1"
                      onClick={() => setOrderDialog({ product: g.product, supplier: d.distributor_name, qty: 1 })}
                      data-testid={`pl-order-${g.product_norm}-${i}`}
                    >
                      <ShoppingCart className="w-3 h-3" /> ORDER
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>

      <AddToOrderSheet
        open={!!orderDialog}
        onOpenChange={(v) => { if (!v) setOrderDialog(null); }}
        defaults={orderDialog || {}}
      />
    </div>
  );
};


// -----------------------------------------------------------------
// MANAGE TAB — upload new price lists, view what's in the vault
// -----------------------------------------------------------------
const ManageTab = () => {
  const [summary, setSummary] = useState({ total_rows: 0, distributors: [] });
  const [distributors, setDistributors] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);   // 0-100 during transfer
  const [uploadStage, setUploadStage] = useState(''); // 'transfer' | 'parse'
  const [uploadResp, setUploadResp] = useState(null);
  const [chosenDistId, setChosenDistId] = useState('');
  const [mapping, setMapping] = useState({});
  const [confirming, setConfirming] = useState(false);
  const mappingRef = useRef(null);

  const refresh = async () => {
    const [s, d] = await Promise.all([PricelistAPI.summary(), DistributorsAPI.list()]);
    setSummary(s);
    setDistributors(d);
  };
  useEffect(() => { refresh().catch(() => {}); }, []);

  const onFile = async (file) => {
    if (!file) return;
    const okExt = /\.(xlsx|xls|csv|pdf)$/i.test(file.name);
    if (!okExt) { toast.error('Please pick a .xlsx, .xls, .csv, or .pdf file'); return; }
    setUploading(true); setUploadResp(null); setUploadPct(0); setUploadStage('transfer');
    try {
      const r = await PricelistAPI.upload(file, ({ percent }) => {
        setUploadPct(percent);
        if (percent >= 100) setUploadStage('parse');
      });
      setUploadResp(r);
      setMapping(r.mapping_saved || r.mapping_suggested || {});
      setChosenDistId(r.detected_distributor?.id || '');
      if (!r.detected_distributor) {
        toast.info(`Parsed ${r.rows} rows. Please pick the distributor below.`);
      } else {
        toast.success(`${r.rows} rows parsed · ${r.detected_distributor.name} · scroll down & click SAVE`);
      }
      setTimeout(() => {
        try { mappingRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (_) {}
      }, 150);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e?.message || 'Upload failed');
    } finally {
      setUploading(false); setUploadStage(''); setUploadPct(0);
    }
  };

  const onConfirm = async () => {
    if (!chosenDistId) { toast.error('Please pick a distributor'); return; }
    if (!mapping.product) { toast.error('Please map the Product column'); return; }
    setConfirming(true);
    try {
      const r = await PricelistAPI.confirm({
        token: uploadResp.token,
        distributor_id: chosenDistId,
        mapping,
        save_mapping: true,
      });
      toast.success(`Saved ${r.rows_inserted} rows for ${r.distributor}`);
      setUploadResp(null); setMapping({}); setChosenDistId('');
      await refresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Confirm failed');
    } finally {
      setConfirming(false);
    }
  };

  const onClearDist = async (distId, distName) => {
    if (!window.confirm(`Wipe all price-list rows for ${distName}?`)) return;
    try {
      await PricelistAPI.clear(distId);
      toast.success(`Cleared ${distName}`);
      await refresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Clear failed');
    }
  };

  const [dragOver, setDragOver] = useState(false);
  const distributorOptions = useMemo(() => distributors.filter((d) => !!d.name), [distributors]);

  return (
    <div className="space-y-5">
      {/* Upload dropzone */}
      {!uploadResp && (
        <label
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files?.[0]; if (f) onFile(f); }}
          className={`flex flex-col items-center justify-center py-8 px-4 border-2 border-dashed rounded-sm cursor-pointer transition-colors ${dragOver ? 'border-emerald-600 bg-emerald-50' : 'border-neutral-300 hover:border-emerald-500'}`}
          data-testid="pricelist-dropzone"
        >
          {uploading ? (
            <div className="w-full max-w-xs flex flex-col items-center">
              <Loader2 className="w-6 h-6 text-emerald-600 animate-spin mb-2" />
              <div className="text-[12px] mono-track-wide font-bold text-emerald-700">
                {uploadStage === 'transfer' && `UPLOADING ${uploadPct}%`}
                {uploadStage === 'parse' && 'PARSING FILE ON SERVER…'}
                {!uploadStage && 'PREPARING…'}
              </div>
              {uploadStage === 'transfer' && (
                <div className="w-full h-1.5 bg-neutral-200 rounded-full mt-2 overflow-hidden">
                  <div className="h-full bg-emerald-600 transition-all" style={{ width: `${uploadPct}%` }} />
                </div>
              )}
              {uploadStage === 'parse' && (
                <div className="text-[10px] mono-track-tight text-neutral-500 mt-1 text-center">
                  Large files may take a minute · Please don't close this tab
                </div>
              )}
            </div>
          ) : (
            <>
              <Upload className="w-6 h-6 text-emerald-600 mb-2" />
              <div className="text-[12px] font-bold mono-track-wide">DROP OR CLICK TO UPLOAD PRICE LIST</div>
              <div className="text-[10px] text-neutral-500 mt-1 mono-track-tight">.XLSX · .XLS · .CSV · NATIVE PDF · UP TO 100K ROWS</div>
            </>
          )}
          <input
            type="file"
            accept=".xlsx,.xls,.csv,.pdf"
            className="hidden"
            disabled={uploading}
            onChange={(e) => onFile(e.target.files?.[0])}
            data-testid="pricelist-file-input"
          />
        </label>
      )}

      {/* Mapping wizard */}
      {uploadResp && (
        <div ref={mappingRef} className="border-2 border-emerald-600 rounded-sm bg-white shadow-lg" data-testid="pricelist-mapping-panel">
          {/* Step indicator banner */}
          <div className="bg-emerald-600 text-white px-4 py-2 flex items-center gap-2">
            <ArrowDown className="w-4 h-4 animate-bounce" />
            <div className="text-[11px] mono-track-wide font-bold flex-1">STEP 2 OF 2 · REVIEW & SAVE TO VAULT</div>
          </div>
          <div className="px-4 py-3 border-b border-emerald-200 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="text-[13px] font-bold mono-track-wide">CONFIRM COLUMN MAPPING</div>
              <div className="text-[10px] text-neutral-500 mono-track-tight mt-0.5 truncate">
                {uploadResp.filename} · {uploadResp.rows} rows
              </div>
            </div>
            <button onClick={() => { setUploadResp(null); setMapping({}); setChosenDistId(''); }}
                    className="text-neutral-500 hover:text-neutral-900" data-testid="pricelist-cancel">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-4 space-y-3">
            {/* Distributor picker */}
            <div>
              <label className="text-[10px] mono-track-wide text-neutral-500 font-semibold">DISTRIBUTOR</label>
              <select
                value={chosenDistId}
                onChange={(e) => setChosenDistId(e.target.value)}
                className="w-full h-11 mt-1 border border-neutral-300 rounded-sm text-[13px] font-semibold px-2 bg-white focus:border-emerald-600 outline-none"
                data-testid="pricelist-distributor-select"
              >
                <option value="">— pick distributor —</option>
                {distributorOptions.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}{d.location ? ` (${d.location})` : ''}</option>
                ))}
              </select>
              {uploadResp.detected_distributor && (
                <div className="text-[10px] text-emerald-700 mono-track-tight mt-1">
                  ▸ Auto-detected: <b>{uploadResp.detected_distributor.name}</b>
                </div>
              )}
            </div>

            {/* Column mapping grid */}
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(FIELD_LABELS).map(([field, label]) => (
                <div key={field}>
                  <label className="text-[10px] mono-track-wide text-neutral-500 font-semibold">{label}</label>
                  <select
                    value={mapping[field] || ''}
                    onChange={(e) => setMapping({ ...mapping, [field]: e.target.value || null })}
                    className="w-full h-10 mt-1 border border-neutral-300 rounded-sm text-[12px] font-semibold px-2 bg-white focus:border-emerald-600 outline-none"
                    data-testid={`pricelist-map-${field}`}
                  >
                    <option value="">— skip —</option>
                    {uploadResp.headers.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            {/* Preview */}
            {uploadResp.preview?.length > 0 && (
              <div className="mt-2">
                <div className="text-[10px] mono-track-wide text-neutral-500 font-semibold mb-1">PREVIEW (FIRST 5 ROWS)</div>
                <div className="border border-neutral-200 rounded-sm overflow-x-auto">
                  <table className="w-full text-[10px]">
                    <thead className="bg-neutral-50">
                      <tr>
                        {uploadResp.headers.map((h) => (
                          <th key={h} className="px-2 py-1.5 text-left font-bold uppercase tracking-tight border-b border-neutral-200 whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {uploadResp.preview.map((r, i) => (
                        <tr key={i} className="odd:bg-white even:bg-neutral-50">
                          {uploadResp.headers.map((h) => (
                            <td key={h} className="px-2 py-1 truncate max-w-[140px]">{r[h]}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <button
              onClick={onConfirm}
              disabled={confirming || !chosenDistId || !mapping.product}
              className="w-full h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[12px] mono-track-wide rounded-sm press flex items-center justify-center gap-2 disabled:opacity-50"
              data-testid="pricelist-confirm-btn"
            >
              {confirming ? <><Loader2 className="w-4 h-4 animate-spin" /> SAVING…</> : <>REPLACE & SAVE {uploadResp.rows} ROWS</>}
            </button>
            <div className="text-[9.5px] mono-track-tight text-neutral-500 text-center">
              This will WIPE all existing rows for this distributor and replace with fresh data.
            </div>
          </div>
        </div>
      )}

      {/* Vault summary */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Database className="w-4 h-4 text-emerald-600" />
          <div className="text-[12px] mono-track-wide font-bold">VAULT · {summary.total_rows.toLocaleString()} PRODUCTS ACROSS {summary.distributors.length} DISTRIBUTORS</div>
        </div>
        {summary.distributors.length === 0 && (
          <div className="text-center py-6 text-[11px] mono-track-tight text-neutral-500">
            No price lists uploaded yet. Drop your first file above.
          </div>
        )}
        <ul className="space-y-1">
          {summary.distributors.map((d) => (
            <li key={d.distributor_id} className="flex items-center gap-3 px-3 py-2 border border-neutral-200 rounded-sm bg-white"
                data-testid={`vault-dist-${d.distributor_id}`}>
              <MapPin className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-[12px] font-bold text-neutral-950 truncate">{d.distributor_name}</div>
                <div className="text-[9.5px] mono-track-tight text-neutral-500">
                  {d.row_count.toLocaleString()} rows · updated {new Date(d.last_upload).toLocaleDateString()}
                </div>
              </div>
              <button onClick={() => onClearDist(d.distributor_id, d.distributor_name)}
                      className="text-neutral-400 hover:text-red-600 press"
                      data-testid={`vault-clear-${d.distributor_id}`}
                      aria-label="Clear this distributor's rows">
                <Trash2 className="w-4 h-4" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};


// -----------------------------------------------------------------
// Page shell — 2 tabs
// -----------------------------------------------------------------
const PricelistPage = () => {
  const [tab, setTab] = useState('search'); // 'search' | 'manage'
  return (
    <div className="px-4 sm:px-6 py-4 space-y-4" data-testid="pricelist-page">
      {/* Tab switcher */}
      <div className="inline-flex border border-neutral-300 rounded-sm p-0.5 bg-neutral-50">
        <button
          onClick={() => setTab('search')}
          className={`px-4 h-9 text-[11px] mono-track-wide font-bold rounded-sm ${tab === 'search' ? 'bg-neutral-950 text-white' : 'text-neutral-600 hover:text-neutral-900'}`}
          data-testid="pricelist-tab-search"
        >
          <Search className="w-3 h-3 inline mr-1.5 -mt-0.5" /> SEARCH
        </button>
        <button
          onClick={() => setTab('manage')}
          className={`px-4 h-9 text-[11px] mono-track-wide font-bold rounded-sm ${tab === 'manage' ? 'bg-neutral-950 text-white' : 'text-neutral-600 hover:text-neutral-900'}`}
          data-testid="pricelist-tab-manage"
        >
          <Upload className="w-3 h-3 inline mr-1.5 -mt-0.5" /> MANAGE UPLOADS
        </button>
      </div>

      {tab === 'search' ? <SearchTab /> : <ManageTab />}
    </div>
  );
};

export default PricelistPage;
