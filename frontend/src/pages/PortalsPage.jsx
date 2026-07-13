import React, { useEffect, useState } from 'react';
import { PortalsAPI, ProductsAPI } from '../lib/api';
import { Circle, ExternalLink, Loader2, FileSpreadsheet, ChevronRight } from 'lucide-react';
import ProductMasterSheet from '../components/ProductMasterSheet';

const PortalsPage = () => {
  const [portals, setPortals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pmOpen, setPmOpen] = useState(false);
  const [pmCount, setPmCount] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const [portals, pc] = await Promise.all([
          PortalsAPI.list(),
          ProductsAPI.count().catch(() => ({ count: 0 })),
        ]);
        setPortals(portals);
        setPmCount(pc.count || 0);
      } catch (e) {
        setError('Failed to load portals');
      } finally {
        setLoading(false);
      }
    })();
  }, [pmOpen]); // refresh count after upload sheet closes

  if (loading) {
    return (
      <div className="pt-10 flex items-center justify-center text-neutral-500">
        <Loader2 className="w-4 h-4 animate-spin mr-2" />
        <span className="text-[11px] mono-track-wide">LOADING PORTALS</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pt-10 text-center text-[12px] mono-track-wide text-neutral-500">{error}</div>
    );
  }

  return (
    <div className="pt-3">
      {/* Product Master card */}
      <button type="button" onClick={() => setPmOpen(true)}
        className="w-full border border-emerald-600 bg-emerald-50 hover:bg-emerald-100 rounded-sm px-4 py-4 mb-5 flex items-center gap-3 press">
        <div className="w-10 h-10 shrink-0 rounded-sm bg-white border border-emerald-600 flex items-center justify-center text-emerald-700">
          <FileSpreadsheet className="w-5 h-5" strokeWidth={1.8} />
        </div>
        <div className="min-w-0 flex-1 text-left">
          <div className="text-[14px] font-extrabold uppercase mono-track-tight text-emerald-800">PRODUCT MASTER</div>
          <div className="text-[11px] mono-track-tight text-emerald-700 mt-0.5">
            {pmCount > 0 ? `${pmCount.toLocaleString()} products loaded \u00b7 tap to manage` : 'No master uploaded \u00b7 tap to upload Excel/CSV'}
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-emerald-700" />
      </button>

      <p className="text-[12px] text-neutral-500 mono-track-tight mb-4">
        Portals are shared crawl engines used to reach individual distributor targets.
      </p>

      <ul className="space-y-2.5">
        {portals.map((p) => {
          const isActive = p.status === 'ACTIVE';
          return (
            <li
              key={p.id}
              className="border border-neutral-300 rounded-sm px-4 py-4 card-hover bg-white"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Circle
                      className={`w-2.5 h-2.5 ${isActive ? 'fill-neutral-950 text-neutral-950' : 'fill-neutral-300 text-neutral-300'}`}
                    />
                    <h3 className="text-[16px] font-extrabold mono-track-tight uppercase">{p.name}</h3>
                  </div>
                  <p className="mt-2 text-[12px] text-neutral-500">{p.description}</p>
                  <div className="mt-2 flex items-center gap-1 text-[11px] text-neutral-500">
                    <ExternalLink className="w-3 h-3" strokeWidth={1.8} />
                    <span className="font-mono truncate">{p.baseUrl}</span>
                  </div>
                </div>
                <span
                  className={`shrink-0 text-[10px] mono-track-wide font-semibold rounded-sm px-2.5 py-1.5 ${
                    isActive
                      ? 'bg-emerald-600 text-white'
                      : 'bg-white text-neutral-400 border border-neutral-300'
                  }`}
                >
                  {p.status}
                </span>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="mt-8 border border-dashed border-neutral-300 rounded-sm px-4 py-6 text-center">
        <p className="text-[11px] mono-track-wide text-neutral-500">
          NEW PORTAL INTEGRATIONS ARRIVE MONTHLY
        </p>
      </div>

      <ProductMasterSheet open={pmOpen} onOpenChange={setPmOpen} />
    </div>
  );
};

export default PortalsPage;
