import React from 'react';
import { PORTALS } from '../mock';
import { Circle, ExternalLink } from 'lucide-react';

const PortalsPage = () => {
  return (
    <div className="pt-3">
      <p className="text-[12px] text-neutral-500 mono-track-tight mb-4">
        Portals are shared crawl engines used to reach individual distributor targets.
      </p>

      <ul className="space-y-2.5">
        {PORTALS.map((p) => {
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
                      ? 'bg-neutral-950 text-white'
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
    </div>
  );
};

export default PortalsPage;
