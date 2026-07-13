import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Search, Database, Clock } from 'lucide-react';

const NAV = [
  { to: '/search', label: 'SEARCH', Icon: Search },
  { to: '/portals', label: 'PORTALS', Icon: Database },
  { to: '/history', label: 'HISTORY', Icon: Clock },
];

const Layout = ({ children }) => {
  const location = useLocation();
  const titles = {
    '/search': { title: 'PHARMASCRAPE', subtitle: 'DISTRIBUTOR AVAILABILITY LOOKUP' },
    '/portals': { title: 'PORTALS', subtitle: 'CONNECTED DISTRIBUTOR ENDPOINTS' },
    '/history': { title: 'HISTORY', subtitle: 'PREVIOUS EXTRACTION RUNS' },
  };
  const meta = titles[location.pathname] || titles['/search'];

  return (
    <div className="min-h-screen w-full flex flex-col bg-white text-neutral-950">
      <div className="mx-auto w-full max-w-3xl flex-1 flex flex-col">
        {/* Header */}
        <header className="px-6 pt-8 pb-5 border-b border-neutral-200">
          <h1 className="text-[28px] sm:text-[32px] font-extrabold mono-track leading-none">
            {meta.title}
          </h1>
          <p className="mt-2 text-[11px] sm:text-xs text-neutral-500 mono-track-wide font-medium">
            {meta.subtitle}
          </p>
        </header>

        {/* Content */}
        <main className="flex-1 px-4 sm:px-6 pb-40 pt-4">{children}</main>
      </div>

      {/* Bottom Nav */}
      <nav className="fixed bottom-0 inset-x-0 border-t border-neutral-200 bg-white/95 backdrop-blur z-40">
        <div className="mx-auto max-w-3xl grid grid-cols-3">
          {NAV.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center gap-1.5 py-3.5 press ${
                  isActive ? 'text-neutral-950' : 'text-neutral-400 hover:text-neutral-700'
                }`
              }
            >
              <Icon className="w-[22px] h-[22px]" strokeWidth={1.8} />
              <span className="text-[11px] font-semibold mono-track-wide">{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
};

export default Layout;
