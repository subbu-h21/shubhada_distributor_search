import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Search, Database, Clock, LogOut, User as UserIcon, KeyRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import ChangePasswordSheet from './ChangePasswordSheet';

const NAV = [
  { to: '/search', label: 'SEARCH', Icon: Search },
  { to: '/portals', label: 'PORTALS', Icon: Database },
  { to: '/history', label: 'HISTORY', Icon: Clock },
];

const Layout = ({ children }) => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [cpOpen, setCpOpen] = useState(false);

  const titles = {
    '/search': { title: 'SHUBHADA PHARMA SIRSI', subtitle: 'AI SEARCH \u00b7 DISTRIBUTOR AVAILABILITY' },
    '/portals': { title: 'PORTALS', subtitle: 'CONNECTED DISTRIBUTOR ENDPOINTS' },
    '/history': { title: 'HISTORY', subtitle: 'PREVIOUS EXTRACTION RUNS' },
  };
  const meta = titles[location.pathname] || titles['/search'];

  return (
    <div className="min-h-screen w-full flex flex-col bg-white text-neutral-950">
      {/* Brand accent bar */}
      <div className="h-1 w-full bg-emerald-600" />
      <div className="mx-auto w-full max-w-3xl flex-1 flex flex-col">
        {/* Header */}
        <header className="px-6 pt-7 pb-5 border-b border-neutral-200">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                <div className="w-2 h-6 bg-emerald-600 rounded-sm shrink-0" />
                <h1 className="text-[22px] sm:text-[28px] font-extrabold mono-track leading-none text-neutral-950 break-words">
                  {meta.title}
                </h1>
              </div>
              <p className="mt-2 text-[10px] sm:text-xs text-neutral-500 mono-track-wide font-medium pl-4">
                {meta.subtitle}
              </p>
            </div>

            {/* User menu */}
            <div className="relative shrink-0">
              <button type="button" onClick={() => setMenuOpen((v) => !v)}
                className="flex items-center gap-2 h-10 px-2.5 border border-neutral-300 hover:border-emerald-600 rounded-sm press bg-white">
                <div className="w-6 h-6 rounded-sm bg-emerald-600 text-white flex items-center justify-center text-[11px] font-bold">
                  {(user?.name || user?.username || 'U').slice(0, 1).toUpperCase()}
                </div>
                <span className="text-[11px] mono-track-wide font-semibold uppercase text-neutral-700 hidden sm:block">
                  {user?.username}
                </span>
              </button>
              {menuOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                  <div className="absolute right-0 top-full mt-1 min-w-[190px] z-50 bg-white border border-neutral-300 rounded-sm shadow-lg">
                    <div className="px-3 py-2.5 border-b border-neutral-200 flex items-center gap-2">
                      <UserIcon className="w-3.5 h-3.5 text-neutral-500" />
                      <div>
                        <div className="text-[12px] font-bold uppercase mono-track-tight leading-tight">{user?.name || user?.username}</div>
                        <div className="text-[10px] mono-track-wide text-neutral-500">{user?.username}</div>
                      </div>
                    </div>
                    <button type="button" onClick={() => { setMenuOpen(false); setCpOpen(true); }}
                      className="w-full text-left px-3 py-2.5 flex items-center gap-2 text-[12px] mono-track-tight hover:bg-emerald-50 border-b border-neutral-100">
                      <KeyRound className="w-3.5 h-3.5" /> CHANGE PASSWORD
                    </button>
                    <button type="button" onClick={() => { setMenuOpen(false); logout(); }}
                      className="w-full text-left px-3 py-2.5 flex items-center gap-2 text-[12px] mono-track-tight text-red-700 hover:bg-red-50">
                      <LogOut className="w-3.5 h-3.5" /> SIGN OUT
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
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
                  isActive ? 'text-emerald-700' : 'text-neutral-400 hover:text-emerald-600'
                }`
              }
            >
              <Icon className="w-[22px] h-[22px]" strokeWidth={1.8} />
              <span className="text-[11px] font-semibold mono-track-wide">{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      <ChangePasswordSheet open={cpOpen} onOpenChange={setCpOpen} />
    </div>
  );
};

export default Layout;
