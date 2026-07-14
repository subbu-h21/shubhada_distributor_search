import React, { useState } from 'react';
import { CheckCircle2, XCircle, AlertOctagon, KeyRound, ChevronDown, ChevronUp, Image as ImageIcon, ExternalLink } from 'lucide-react';
import { screenshotUrl } from '../lib/api';

const STATUS_META = {
  SUCCESS:      { label: 'SUCCESS',      Icon: CheckCircle2,  tone: 'bg-emerald-600 text-white border-emerald-600' },
  NOT_FOUND:    { label: 'NOT FOUND',    Icon: XCircle,        tone: 'bg-white text-neutral-950 border-emerald-600' },
  LOGIN_FAILED: { label: 'LOGIN FAILED', Icon: KeyRound,       tone: 'bg-white text-neutral-500 border-neutral-400' },
  ERROR:        { label: 'ERROR',        Icon: AlertOctagon,   tone: 'bg-white text-neutral-500 border-neutral-400' },
};

/**
 * Displays one distributor's result: status pill, per-item table (MRP/PTR/Qty/Scheme/Batch/Expiry),
 * and expandable screenshot preview.
 */
const ResultCard = ({ result, requestedQty }) => {
  const meta = STATUS_META[result.status] || STATUS_META.ERROR;
  const { Icon } = meta;
  const [showShots, setShowShots] = useState(false);

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
    </div>
  );
};

export default ResultCard;
