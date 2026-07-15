import React, { useState } from 'react';
import { CheckCircle2, XCircle, AlertOctagon, KeyRound, ChevronDown, ChevronUp, Image as ImageIcon, ExternalLink, MousePointerClick, Loader2, ShoppingCart } from 'lucide-react';
import { screenshotUrl, ExtractAPI } from '../lib/api';
import AddToOrderSheet from './AddToOrderSheet';
import { toast } from 'sonner';

const STATUS_META = {
  SUCCESS:      { label: 'SUCCESS',      Icon: CheckCircle2,  tone: 'bg-emerald-600 text-white border-emerald-600' },
  NOT_FOUND:    { label: 'NOT FOUND',    Icon: XCircle,        tone: 'bg-white text-neutral-950 border-emerald-600' },
  LOGIN_FAILED: { label: 'LOGIN FAILED', Icon: KeyRound,       tone: 'bg-white text-neutral-500 border-neutral-400' },
  ERROR:        { label: 'ERROR',        Icon: AlertOctagon,   tone: 'bg-white text-neutral-500 border-neutral-400' },
};

/**
 * Displays one distributor's result: status pill, per-item table (MRP/PTR/Qty/Scheme/Batch/Expiry),
 * expandable screenshot preview, and (on NOT_FOUND) a "Manual pick" panel where the user
 * can force-select any candidate that the distributor's autocomplete surfaced.
 */
const ResultCard = ({ result: initialResult, requestedQty, historyId, onUpdate }) => {
  const [result, setResult] = useState(initialResult);
  const [showShots, setShowShots] = useState(false);
  const [picking, setPicking] = useState(null); // candidate name currently being force-picked
  const [addOpen, setAddOpen] = useState(false);
  const meta = STATUS_META[result.status] || STATUS_META.ERROR;
  const { Icon } = meta;

  // The first item (post-explode there's exactly one seller per card)
  const firstItem = (result.items || [])[0] || {};
  // Can add to order if we matched something in-stock (or partial)
  const canAddToOrder = result.status === 'SUCCESS' && firstItem.matched_name;
  // Supplier defaults: use seller if exploded, else the target name (SUNSHOP/CHETHANA row)
  const orderDefaults = {
    product: firstItem.matched_name || result.product,
    supplier: firstItem.seller || (result.targetName || '').split(' — ')[0] || '',
    qty: requestedQty || 1,
  };

  const candidates = (result.debug && result.debug.candidates) || [];
  const normCandidates = Array.isArray(candidates) && candidates.length > 0 && typeof candidates[0] === 'object'
    ? candidates.map((c) => (c.name ? c.name : String(c)))
    : candidates;
  const showManualPick = result.status === 'NOT_FOUND' && normCandidates.length > 0 && historyId;

  const doManualPick = async (candName) => {
    if (!historyId) return;
    setPicking(candName);
    try {
      const r = await ExtractAPI.manualPick(historyId, result.targetId, candName);
      const newResult = r.result || r;
      setResult(newResult);
      onUpdate && onUpdate(newResult);
      if (newResult.status === 'SUCCESS') {
        toast.success(`Picked "${candName}"`);
      } else {
        toast.error(`Still ${newResult.status}: ${newResult.detail || ''}`);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Manual pick failed');
    } finally {
      setPicking(null);
    }
  };

  const shots = [
    { tag: 'LOGIN', file: result.loginScreenshot },
    { tag: 'SEARCH', file: result.searchScreenshot },
    ...(((result.debug || {}).stageScreenshots) || []).map((f, i) => ({ tag: `STAGE ${i + 1}`, file: f })),
    { tag: 'RESULTS', file: result.resultsScreenshot },
  ].filter((s) => !!s.file);

  return (
    <div className="border border-neutral-300 rounded-sm">
      {/* Header */}
      <div className="px-3 py-3 flex items-start gap-3 border-b border-neutral-200">
        <div className="w-8 h-8 shrink-0 border border-emerald-600 rounded-sm flex items-center justify-center">
          <Icon className="w-4 h-4" strokeWidth={2} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[13px] font-extrabold mono-track-tight uppercase truncate">{result.targetName}</span>
            <span className="text-[9px] mono-track-wide font-semibold border border-neutral-300 rounded-sm px-1.5 py-0.5 text-neutral-500">{result.portal}</span>
            <span className={`text-[9px] mono-track-wide font-semibold rounded-sm px-1.5 py-0.5 border ${meta.tone}`}>{meta.label}</span>
            {result.canFulfill === true && (
              <span className="text-[9px] mono-track-wide font-semibold rounded-sm px-1.5 py-0.5 bg-emerald-600 text-white">CAN FULFILL QTY {requestedQty}</span>
            )}
            {result.canFulfill === false && (
              <span className="text-[9px] mono-track-wide font-semibold rounded-sm px-1.5 py-0.5 border border-neutral-400 text-neutral-500">SHORT OF QTY {requestedQty}</span>
            )}
          </div>
          {result.detail && (
            <div className="mt-1 text-[11px] mono-track-tight text-neutral-500">{result.detail}</div>
          )}
        </div>
        {canAddToOrder && (
          <button
            type="button"
            onClick={() => setAddOpen(true)}
            data-testid="add-to-order-btn"
            className="shrink-0 h-8 px-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-sm text-[10px] mono-track-wide font-bold flex items-center gap-1 press"
            title="Place this seller's PO on Shubhada Pharma"
          >
            <ShoppingCart className="w-3.5 h-3.5" />
            ADD TO ORDER
          </button>
        )}
      </div>

      {/* Items table */}
      {result.items && result.items.length > 0 && (
        <div className="px-3 py-3 overflow-x-auto">
          <table className="w-full text-[11px] mono-track-tight">
            <thead>
              <tr className="text-left text-neutral-500">
                {result.items.some((it) => it.seller) && (
                  <th className="py-1.5 pr-3 font-medium">SELLER</th>
                )}
                <th className="py-1.5 pr-3 font-medium">MATCHED</th>
                <th className="py-1.5 pr-3 font-medium">MFR</th>
                <th className="py-1.5 pr-3 font-medium">PACK</th>
                <th className="py-1.5 pr-3 font-medium">MRP</th>
                <th className="py-1.5 pr-3 font-medium">PTR</th>
                <th className="py-1.5 pr-3 font-medium">QTY</th>
                <th className="py-1.5 pr-3 font-medium">SCHEME</th>
                <th className="py-1.5 pr-3 font-medium">BATCH</th>
                <th className="py-1.5 pr-3 font-medium">EXP</th>
              </tr>
            </thead>
            <tbody>
              {result.items.map((it, i) => {
                const qtyNum = it.available_qty && /^\d+$/.test(it.available_qty) ? parseInt(it.available_qty) : null;
                const outOfStock = qtyNum === 0;
                return (
                  <tr key={i} className={`border-t border-neutral-200 ${outOfStock ? 'text-neutral-400' : ''}`}>
                    {result.items.some((x) => x.seller) && (
                      <td className="py-1.5 pr-3 font-semibold uppercase" data-testid={`result-seller-${i}`}>{it.seller || '—'}</td>
                    )}
                    <td className="py-1.5 pr-3 font-semibold uppercase">{it.matched_name || '—'}</td>
                    <td className="py-1.5 pr-3">{it.manufacturer || '—'}</td>
                    <td className="py-1.5 pr-3">{it.pack || '—'}</td>
                    <td className="py-1.5 pr-3 tabular-nums">{it.mrp || '—'}</td>
                    <td className="py-1.5 pr-3 tabular-nums">{it.ptr || '—'}</td>
                    <td className={`py-1.5 pr-3 tabular-nums font-bold ${qtyNum > 0 ? 'text-emerald-700' : ''}`}>{it.available_qty || '—'}</td>
                    <td className="py-1.5 pr-3">{it.scheme || '—'}</td>
                    <td className="py-1.5 pr-3">{it.batch || '—'}</td>
                    <td className="py-1.5 pr-3">{it.expiry || '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Manual pick panel — shown for NOT_FOUND results with candidates */}
      {showManualPick && (
        <div className="px-3 py-3 border-t border-neutral-200 bg-emerald-50/60">
          <div className="text-[10px] mono-track-wide font-semibold text-neutral-500 flex items-center gap-1.5 mb-2">
            <MousePointerClick className="w-3.5 h-3.5" />
            MANUAL PICK — TAP THE CORRECT SKU
          </div>
          <div className="flex flex-wrap gap-1.5">
            {normCandidates.slice(0, 12).map((name, i) => (
              <button
                key={i}
                type="button"
                disabled={!!picking}
                onClick={() => doManualPick(name)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 border rounded-sm text-[11px] mono-track-tight font-semibold press
                  ${picking === name
                    ? 'border-emerald-600 bg-emerald-600 text-white'
                    : 'border-neutral-300 bg-white hover:border-emerald-600 hover:bg-emerald-600 hover:text-white'}`}
                data-testid={`manual-pick-${i}`}>
                {picking === name && <Loader2 className="w-3 h-3 animate-spin" />}
                {name}
              </button>
            ))}
          </div>
          <p className="mt-2 text-[10px] text-neutral-500 mono-track-tight">
            The auto-scorer rejected these variants (different strength / combo). Tap one to force-select it.
          </p>
        </div>
      )}

      {/* Screenshots */}
      {shots.length > 0 && (
        <div className="px-3 py-2 border-t border-neutral-200">
          <button onClick={() => setShowShots((v) => !v)} className="w-full flex items-center justify-between text-[10px] mono-track-wide font-semibold text-neutral-500 hover:text-neutral-950 py-1">
            <span className="flex items-center gap-1.5"><ImageIcon className="w-3.5 h-3.5" /> SCREENSHOTS ({shots.length})</span>
            {showShots ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          {showShots && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pb-2 pt-1">
              {shots.map((s) => (
                <a key={s.file} href={screenshotUrl(s.file)} target="_blank" rel="noreferrer" className="group block border border-neutral-300 hover:border-emerald-600 rounded-sm overflow-hidden">
                  <img src={screenshotUrl(s.file)} alt={s.tag} className="w-full h-24 sm:h-32 object-cover object-top" />
                  <div className="px-2 py-1 flex items-center justify-between border-t border-neutral-200 bg-white">
                    <span className="text-[9px] mono-track-wide font-semibold">{s.tag}</span>
                    <ExternalLink className="w-3 h-3 text-neutral-400 group-hover:text-neutral-950" />
                  </div>
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      <AddToOrderSheet open={addOpen} onOpenChange={setAddOpen} defaults={orderDefaults} />
    </div>
  );
};

export default ResultCard;
