import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Eye, EyeOff, LogIn, Loader2, Zap } from 'lucide-react';

const LoginPage = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password) { setError('Enter username and password'); return; }
    try {
      setLoading(true);
      await login(username.trim().toLowerCase(), password);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Login failed');
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center bg-white px-6">
      <div className="fixed top-0 left-0 right-0 h-1 bg-emerald-600" />

      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-11 h-11 rounded-sm bg-emerald-600 flex items-center justify-center text-white">
            <Zap className="w-5 h-5 fill-white" strokeWidth={2} />
          </div>
          <div>
            <div className="text-[13px] font-extrabold mono-track-tight uppercase leading-none text-neutral-950">SHUBHADA PHARMA SIRSI</div>
            <div className="mt-1 text-[10px] mono-track-wide text-emerald-700 font-semibold">AI SEARCH</div>
          </div>
        </div>

        <h1 className="text-[24px] font-extrabold mono-track leading-tight text-neutral-950">SIGN IN</h1>
        <p className="mt-1 text-[12px] mono-track-tight text-neutral-500">Enter your credentials to continue</p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="block text-[11px] text-neutral-500 mono-track-wide font-medium mb-2">USERNAME</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. shubhada" autoComplete="username" autoCapitalize="none"
              className="w-full h-12 px-4 border border-neutral-300 rounded-sm focus:outline-none focus:border-emerald-600 text-[15px]" />
          </div>

          <div>
            <label className="block text-[11px] text-neutral-500 mono-track-wide font-medium mb-2">PASSWORD</label>
            <div className="relative">
              <input value={password} onChange={(e) => setPassword(e.target.value)} type={showPassword ? 'text' : 'password'} placeholder="••••" autoComplete="current-password"
                className="w-full h-12 px-4 pr-11 border border-neutral-300 rounded-sm focus:outline-none focus:border-emerald-600 text-[15px] font-mono" />
              <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-neutral-500 hover:text-neutral-900">
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {error && (
            <div className="text-[11px] mono-track-tight text-red-700 bg-red-50 border border-red-200 rounded-sm px-3 py-2">
              {error}
            </div>
          )}

          <button type="submit" disabled={loading}
            className="w-full h-14 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-70 text-white rounded-sm flex items-center justify-center gap-2 text-[13px] mono-track-wide font-bold press">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogIn className="w-4 h-4" />}
            {loading ? 'SIGNING IN…' : 'SIGN IN'}
          </button>
        </form>

        <p className="mt-8 text-[10px] mono-track-wide text-neutral-400 text-center">
          SESSION LASTS 30 DAYS · 4 SEATS · SHUBHADA / MANJU / ABHISHEK / NARENDRA
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
