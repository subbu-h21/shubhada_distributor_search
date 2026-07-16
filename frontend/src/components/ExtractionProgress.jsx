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
      {/* Anjaneya banner — high-detail cinematic image of Hanumanji flying
          with Sanjeevini Parvat. Generated once via Nano Banana; served
          statically from /public. */}
      <div className="relative h-56 sm:h-72 overflow-hidden bg-black">
        <img
          src="/hanuman-sanjeevini.png"
          alt="Lord Hanuman carrying the Sanjeevini Parvat"
          className="absolute inset-0 w-full h-full object-cover animate-hero-float"
          data-testid="hero-hanuman-image"
        />

        {/* Sparkle overlay — small twinkling dots layered on top for kinetic feel */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 800 300" preserveAspectRatio="xMidYMid slice" aria-hidden>
          {[...Array(22)].map((_, i) => {
            const x = (i * 173) % 800;
            const y = (i * 47) % 300;
            const r = (i % 3) * 0.4 + 0.5;
            const dur = 1.4 + (i % 5) * 0.5;
            return (
              <circle key={i} cx={x} cy={y} r={r} fill="#FFF6C0" opacity="0.9">
                <animate attributeName="opacity" values="0.15;1;0.15" dur={`${dur}s`} repeatCount="indefinite" />
              </circle>
            );
          })}
        </svg>

        {/* Bottom gradient scrim so overlay text stays legible */}
        <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-black/80 via-black/40 to-transparent pointer-events-none" />

        {/* Text overlay */}
        <div className="relative z-10 h-full flex flex-col items-center justify-end pb-3 text-white px-4">
          <div className="text-[10px] mono-track-wide tracking-widest text-yellow-200 drop-shadow-lg">॥ जय बजरंग बली ॥ · JAI BAJRANG BALI</div>
          <h2 className="mt-1 text-xl sm:text-2xl font-black tracking-tight drop-shadow-[0_2px_6px_rgba(0,0,0,0.9)]">FETCHING SANJEEVINI STOCK</h2>
          <p className="mt-0.5 text-[11px] sm:text-[12px] max-w-md text-center leading-tight opacity-95 drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">
            Just as Anjaneya carried the Sanjeevini parvat to save Lakshmana,
            we're pulling every distributor's stock at once for
            <span className="font-bold uppercase"> {product}</span>
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
