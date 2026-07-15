import React, { useMemo } from 'react';
import { Loader2, CheckCircle2, XCircle, AlertOctagon, KeyRound, MapPin } from 'lucide-react';

/**
 * Anjaneya-themed extraction progress overlay.
 * Shows a beautiful roster of all distributors grouped by city, with a live
 * per-distributor status indicator (spinner while running, then icon for
 * SUCCESS / NOT_FOUND / LOGIN_FAILED / ERROR). The centerpiece is an image of
 * Anjaneya (Hanuman) carrying Sanjeevini Parvat — Shubhada Pharma's spiritual
 * mascot, connecting the pharmacist's mission (fast, life-saving medicine
 * lookup) with the parvat-carrying deity.
 */

const STATUS_ICON = {
  RUNNING: { Icon: Loader2, cls: 'text-emerald-600 animate-spin', label: 'FETCHING' },
  SUCCESS: { Icon: CheckCircle2, cls: 'text-emerald-600', label: 'FOUND' },
  NOT_FOUND: { Icon: XCircle, cls: 'text-neutral-500', label: 'NO STOCK' },
  LOGIN_FAILED: { Icon: KeyRound, cls: 'text-amber-600', label: 'AUTH' },
  ERROR: { Icon: AlertOctagon, cls: 'text-red-600', label: 'ERROR' },
};

const groupByCity = (distributors) => {
  const groups = {};
  for (const d of distributors) {
    const city = (d.location || 'Other').trim();
    if (!groups[city]) groups[city] = [];
    groups[city].push(d);
  }
  // Sort cities alphabetically; put "Karnataka (…)" and "Other" last
  const keys = Object.keys(groups).sort((a, b) => {
    const aRank = a.startsWith('Karnataka') || a === 'Other' ? 1 : 0;
    const bRank = b.startsWith('Karnataka') || b === 'Other' ? 1 : 0;
    if (aRank !== bRank) return aRank - bRank;
    return a.localeCompare(b);
  });
  return keys.map((k) => ({ city: k, list: groups[k] }));
};

const ExtractionProgress = ({ distributors, resultsByTargetId, product, quantity }) => {
  const grouped = useMemo(() => groupByCity(distributors), [distributors]);
  const total = distributors.length;
  const completed = distributors.filter((d) => resultsByTargetId[d.id]).length;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="relative overflow-hidden">
      {/* Anjaneya banner */}
      <div className="relative h-40 sm:h-52 overflow-hidden bg-gradient-to-r from-emerald-700 via-emerald-600 to-emerald-800">
        {/* Hanuman/Sanjeevini SVG art — inline so it works offline and stays sharp on retina */}
        <svg viewBox="0 0 800 200" className="absolute inset-0 w-full h-full opacity-25" preserveAspectRatio="xMidYMid slice" aria-hidden>
          {/* Silhouette of Anjaneya flying with a mountain overhead */}
          <defs>
            <radialGradient id="glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#fff" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#fff" stopOpacity="0" />
            </radialGradient>
          </defs>
          <circle cx="400" cy="80" r="70" fill="url(#glow)" />
          {/* Mountain */}
          <path d="M 300 60 L 340 20 L 380 45 L 420 15 L 460 50 L 500 25 L 540 55 L 300 60 Z"
                fill="#fff" opacity="0.85" />
          <path d="M 300 60 Q 340 40 380 50 Q 420 45 460 55 Q 500 45 540 55 L 540 70 L 300 70 Z"
                fill="#fff" opacity="0.55" />
          {/* Hanuman body silhouette below (highly stylised) */}
          <g transform="translate(390, 90)" fill="#fff" opacity="0.9">
            <ellipse cx="0" cy="10" rx="26" ry="15" />
            <circle cx="0" cy="-14" r="14" />
            {/* Mace/gada in one hand */}
            <rect x="-45" y="0" width="18" height="4" transform="rotate(-15 -30 2)" rx="1" />
            <circle cx="-48" cy="-2" r="6" />
            {/* Tail curl */}
            <path d="M 20 20 Q 55 25 55 -5 Q 55 -25 30 -22"
                  fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" />
            {/* Wings/movement lines */}
            <path d="M -55 -20 L -80 -30 M -55 -10 L -85 -15 M -55 0 L -85 0"
                  stroke="#fff" strokeWidth="2" strokeLinecap="round" fill="none" />
          </g>
          {/* Stars / motion trail */}
          <circle cx="120" cy="40" r="2" fill="#fff" />
          <circle cx="80"  cy="80" r="2" fill="#fff" />
          <circle cx="180" cy="120" r="1.5" fill="#fff" />
          <circle cx="650" cy="60" r="2" fill="#fff" />
          <circle cx="700" cy="130" r="1.5" fill="#fff" />
        </svg>

        <div className="relative z-10 h-full flex flex-col items-center justify-center text-white px-4">
          <div className="text-[10px] mono-track-wide tracking-widest opacity-90">॥ जय हनुमान ॥ · SANJEEVINI HERBS · JAY HANUMAN</div>
          <h2 className="mt-1.5 text-2xl sm:text-3xl font-black tracking-tight">FETCHING LIFE-SAVING STOCK</h2>
          <p className="mt-1 text-[12px] sm:text-[13px] opacity-95 max-w-md text-center leading-tight">
            Just as Anjaneya carried the entire Sanjeevini parvat to save Lakshmana,
            we are pulling every distributor's stock at once for <span className="font-bold uppercase">{product}</span>
            {quantity ? <> · qty <span className="font-bold">{quantity}</span></> : null}.
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-4 py-2.5 border-b border-neutral-200 flex items-center gap-3">
        <div className="flex-1 h-2 bg-neutral-100 rounded-full overflow-hidden">
          <div className="h-full bg-emerald-600 transition-[width] duration-500" style={{ width: `${pct}%` }} data-testid="progress-fill" />
        </div>
        <div className="text-[11px] mono-track-wide font-bold text-emerald-700 tabular-nums" data-testid="progress-count">
          {completed}/{total}
        </div>
      </div>

      {/* Distributor roster, grouped by city */}
      <div className="px-4 py-3 max-h-[45vh] overflow-y-auto">
        {grouped.map(({ city, list }) => (
          <div key={city} className="mb-3 last:mb-0">
            <div className="flex items-center gap-1.5 mb-1.5">
              <MapPin className="w-3 h-3 text-emerald-600" />
              <div className="text-[10px] mono-track-wide font-semibold text-neutral-500 uppercase tracking-wider">{city}</div>
              <div className="flex-1 h-px bg-neutral-200"></div>
              <div className="text-[10px] mono-track-tight font-semibold text-neutral-400">{list.length}</div>
            </div>
            <ul className="space-y-1">
              {list.map((d) => {
                const res = resultsByTargetId[d.id];
                const status = res ? res.status : 'RUNNING';
                const meta = STATUS_ICON[status] || STATUS_ICON.RUNNING;
                const { Icon } = meta;
                const inStock = res?.items?.reduce((s, it) => s + (Number(it.available_qty) || 0), 0) || 0;
                return (
                  <li key={d.id} className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-sm bg-white border border-neutral-100 hover:border-emerald-200"
                      data-testid={`extraction-progress-${d.id}`}>
                    <Icon className={`w-4 h-4 shrink-0 ${meta.cls}`} />
                    <div className="min-w-0 flex-1">
                      <div className="text-[12px] font-semibold truncate">{d.name}</div>
                      <div className="text-[9.5px] mono-track-wide text-neutral-400 uppercase">
                        {d.portal || d.portalType || 'PORTAL'}
                      </div>
                    </div>
                    <div className={`text-[10px] mono-track-wide font-bold tabular-nums ${status === 'SUCCESS' ? 'text-emerald-700' : 'text-neutral-500'}`}>
                      {status === 'RUNNING' ? '···' : (status === 'SUCCESS' && inStock ? `${inStock}u` : meta.label)}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ExtractionProgress;
