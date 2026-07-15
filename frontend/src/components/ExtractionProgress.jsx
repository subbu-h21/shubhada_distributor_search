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
      {/* Anjaneya banner — Hanumanji flying with Sanjeevini parvat */}
      <div className="relative h-56 sm:h-72 overflow-hidden bg-gradient-to-b from-indigo-950 via-purple-900 to-orange-700">
        {/* Twinkling stars in the night sky */}
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 800 300" preserveAspectRatio="xMidYMid slice" aria-hidden>
          {[...Array(30)].map((_, i) => {
            const x = (i * 137) % 800;
            const y = (i * 53) % 140;
            const r = (i % 3) * 0.5 + 0.6;
            const dur = 1.8 + (i % 5) * 0.4;
            return (
              <circle key={i} cx={x} cy={y} r={r} fill="#FFF6C0" opacity="0.85">
                <animate attributeName="opacity" values="0.2;1;0.2" dur={`${dur}s`} repeatCount="indefinite" />
              </circle>
            );
          })}
          {/* Full moon behind him */}
          <circle cx="660" cy="70" r="34" fill="#FFF3CC" opacity="0.9" />
          <circle cx="660" cy="70" r="34" fill="url(#moonGlow)" />
          <defs>
            <radialGradient id="moonGlow" cx="50%" cy="50%" r="60%">
              <stop offset="0%" stopColor="#FFFDE7" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#FFFDE7" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="herbGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#8AFF6D" stopOpacity="0.95" />
              <stop offset="100%" stopColor="#8AFF6D" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="mtn" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4A2E1F" />
              <stop offset="60%" stopColor="#7A4A2F" />
              <stop offset="100%" stopColor="#3B1E12" />
            </linearGradient>
            <linearGradient id="body" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#F97316" />
              <stop offset="100%" stopColor="#C2410C" />
            </linearGradient>
            <linearGradient id="dhoti" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FFD54A" />
              <stop offset="100%" stopColor="#E8A020" />
            </linearGradient>
          </defs>

          {/* Motion trails — long streaks behind him */}
          <g opacity="0.6">
            <path d="M 40 190 Q 200 175 340 165" stroke="#FFE082" strokeWidth="2" fill="none" strokeLinecap="round">
              <animate attributeName="opacity" values="0.15;0.7;0.15" dur="1.8s" repeatCount="indefinite" />
            </path>
            <path d="M 20 220 Q 200 200 350 180" stroke="#FFB74D" strokeWidth="1.5" fill="none" strokeLinecap="round">
              <animate attributeName="opacity" values="0.2;0.6;0.2" dur="2.2s" repeatCount="indefinite" />
            </path>
            <path d="M 60 170 Q 210 160 340 155" stroke="#FFD54F" strokeWidth="1" fill="none" strokeLinecap="round">
              <animate attributeName="opacity" values="0.1;0.5;0.1" dur="1.4s" repeatCount="indefinite" />
            </path>
          </g>

          {/* HANUMANJI + SANJEEVINI PARVAT — floating group */}
          <g transform="translate(0, 0)">
            <animateTransform attributeName="transform" type="translate" values="0,0; 0,-6; 0,0" dur="3s" repeatCount="indefinite" />

            {/* Sanjeevini parvat held above with left arm — mountain with glowing herbs */}
            <g transform="translate(340, 40)">
              {/* Mountain body */}
              <path d="M -60 60 L -40 20 L -20 45 L 0 5 L 22 30 L 44 12 L 62 40 L 78 25 L 90 55 L 100 68 L -60 68 Z"
                    fill="url(#mtn)" />
              {/* Snowy peaks */}
              <path d="M -40 20 L -32 30 L -22 22 L -20 45 M 0 5 L 8 22 L 18 15 L 22 30 M 44 12 L 52 25 L 60 18 L 62 40 M 78 25 L 84 38 L 90 55"
                    stroke="#F5F5F5" strokeWidth="3" fill="none" strokeLinecap="round" />
              {/* Glowing sanjeevini herbs on top */}
              {[
                { cx: -25, cy: 25 }, { cx: -5, cy: 12 }, { cx: 12, cy: 18 },
                { cx: 30, cy: 20 }, { cx: 55, cy: 22 }, { cx: 82, cy: 32 },
              ].map((p, idx) => (
                <g key={idx} transform={`translate(${p.cx} ${p.cy})`}>
                  <circle r="10" fill="url(#herbGlow)">
                    <animate attributeName="r" values="8;14;8" dur={`${2 + idx * 0.3}s`} repeatCount="indefinite" />
                  </circle>
                  <path d="M 0 -6 Q 3 -3 2 0 Q -1 3 -2 6 Q -4 2 -3 -2 Z" fill="#A5F58F">
                    <animate attributeName="opacity" values="0.6;1;0.6" dur={`${1.5 + idx * 0.2}s`} repeatCount="indefinite" />
                  </path>
                  <path d="M 0 -3 L 0 5" stroke="#3FA027" strokeWidth="1" />
                </g>
              ))}
            </g>

            {/* Left arm holding the parvat up */}
            <path d="M 390 100 Q 385 90 388 78 Q 390 70 400 68 L 405 78 Q 400 90 402 100 Z"
                  fill="url(#body)" />
            <circle cx="400" cy="70" r="10" fill="url(#body)" />

            {/* Hanumanji body — flying pose, chest forward */}
            <g transform="translate(400, 130)">
              {/* Cape / flowing fabric behind */}
              <path d="M -50 -10 Q -85 5 -110 30 Q -95 20 -70 20 Q -55 15 -50 10 Z"
                    fill="#DC2626">
                <animate attributeName="d"
                         values="M -50 -10 Q -85 5 -110 30 Q -95 20 -70 20 Q -55 15 -50 10 Z;
                                 M -50 -10 Q -90 10 -120 40 Q -100 25 -75 22 Q -55 17 -50 10 Z;
                                 M -50 -10 Q -85 5 -110 30 Q -95 20 -70 20 Q -55 15 -50 10 Z"
                         dur="2.5s" repeatCount="indefinite" />
              </path>

              {/* Torso */}
              <ellipse cx="0" cy="0" rx="22" ry="26" fill="url(#body)" />
              {/* Golden dhoti (waist wrap) */}
              <path d="M -22 12 L 22 12 L 26 32 Q 0 40 -26 32 Z" fill="url(#dhoti)" />
              <path d="M -22 12 L 22 12" stroke="#B8860B" strokeWidth="1.5" />

              {/* Right leg thrust back — flying */}
              <path d="M 10 30 Q 30 40 55 60 Q 62 68 55 74 Q 46 66 30 55 Q 15 45 8 38 Z"
                    fill="url(#body)" />
              {/* Left leg bent under */}
              <path d="M -10 30 Q -6 45 -12 60 Q -18 68 -12 72 Q -2 62 4 45 Z"
                    fill="url(#body)" />

              {/* Right arm extended forward, holding gada (mace) */}
              <path d="M 20 -8 Q 40 -14 60 -16 Q 68 -14 66 -8 Q 45 -4 22 2 Z"
                    fill="url(#body)" />
              {/* Gada (mace) */}
              <rect x="63" y="-24" width="6" height="26" rx="2" fill="#8B4513" transform="rotate(15 66 -11)" />
              <ellipse cx="70" cy="-30" rx="10" ry="12" fill="#D4A017" transform="rotate(15 66 -11)" />
              <ellipse cx="70" cy="-30" rx="6" ry="8" fill="#F5C542" transform="rotate(15 66 -11)" />

              {/* Head with monkey face features */}
              <circle cx="-5" cy="-32" r="16" fill="url(#body)" />
              {/* Ears */}
              <ellipse cx="-19" cy="-33" rx="5" ry="8" fill="#C2410C" />
              <ellipse cx="9" cy="-33" rx="5" ry="8" fill="#C2410C" />
              {/* Crown / mukut — golden */}
              <path d="M -18 -46 L -12 -52 L -6 -46 L 0 -52 L 6 -46 L 12 -52 L 14 -42 L -19 -42 Z"
                    fill="#F5C542" stroke="#B8860B" strokeWidth="1" />
              <circle cx="0" cy="-52" r="3" fill="#DC2626" />
              {/* Face features */}
              <path d="M -12 -30 Q -8 -26 -5 -30" stroke="#4A1010" strokeWidth="1.2" fill="none" />
              <path d="M -2 -30 Q 2 -26 5 -30" stroke="#4A1010" strokeWidth="1.2" fill="none" />
              <circle cx="-10" cy="-30" r="1.5" fill="#000" />
              <circle cx="2" cy="-30" r="1.5" fill="#000" />
              {/* Determined mouth */}
              <path d="M -6 -22 Q -3 -20 0 -22" stroke="#4A1010" strokeWidth="1.5" fill="none" />
              {/* Tilak on forehead */}
              <path d="M -3 -42 L -3 -38 M -1 -42 L -1 -38 M 1 -42 L 1 -38" stroke="#DC2626" strokeWidth="1.2" />

              {/* Long tail curling upward behind */}
              <path d="M -18 20 Q -60 30 -85 0 Q -100 -30 -75 -50 Q -60 -55 -55 -45"
                    fill="none" stroke="url(#body)" strokeWidth="6" strokeLinecap="round" />
              <path d="M -55 -45 Q -50 -40 -55 -35" fill="none" stroke="#F97316" strokeWidth="4" strokeLinecap="round" />
            </g>

            {/* Little glow around Hanuman */}
            <circle cx="400" cy="130" r="90" fill="url(#moonGlow)" opacity="0.4" />
          </g>

          {/* Foreground cloud wisps he's speeding through */}
          <g opacity="0.7">
            <ellipse cx="120" cy="240" rx="70" ry="10" fill="#FFF" opacity="0.4">
              <animate attributeName="cx" values="120;180;120" dur="6s" repeatCount="indefinite" />
            </ellipse>
            <ellipse cx="620" cy="250" rx="90" ry="12" fill="#FFF" opacity="0.35">
              <animate attributeName="cx" values="620;560;620" dur="7s" repeatCount="indefinite" />
            </ellipse>
            <ellipse cx="380" cy="270" rx="120" ry="14" fill="#FFF" opacity="0.3" />
          </g>
        </svg>

        {/* Text overlay */}
        <div className="relative z-10 h-full flex flex-col items-center justify-end pb-3 text-white px-4">
          <div className="text-[10px] mono-track-wide tracking-widest text-yellow-200 drop-shadow">॥ जय बजरंग बली ॥ · JAI BAJRANG BALI</div>
          <h2 className="mt-1 text-xl sm:text-2xl font-black tracking-tight drop-shadow-lg">FETCHING SANJEEVINI STOCK</h2>
          <p className="mt-0.5 text-[11px] sm:text-[12px] max-w-md text-center leading-tight opacity-95 drop-shadow">
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
