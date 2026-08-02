import { useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Phone, Lock, Eye, EyeOff, ChevronDown, Search, Loader2 } from 'lucide-react';
import ozzyLogo from '../assets/ozzy-logo.png';
import ozzyHero from '../assets/ozzy-hero.jpg';
import { AFRICA_COUNTRIES, type Country } from '../data/africaCountries';
import api from '../api/client';

export default function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [country, setCountry] = useState<Country>(AFRICA_COUNTRIES[0]); // Uganda default
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register, fetchUserData } = useAuth();
  const navigate = useNavigate();
  const pickerRef = useRef<HTMLDivElement>(null);

  // "Have an invite code?" flow — a Worker joins with a 6-digit code instead of registering.
  const [showInvite, setShowInvite] = useState(false);
  const [inviteStep, setInviteStep] = useState<'code' | 'password'>('code');
  const [inviteCode, setInviteCode] = useState('');
  const [invitePhone, setInvitePhone] = useState('');
  const [invitePassword, setInvitePassword] = useState('');
  const [inviteConfirmPassword, setInviteConfirmPassword] = useState('');
  const [inviteShowPassword, setInviteShowPassword] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteLoading, setInviteLoading] = useState(false);

  // Close the country picker when clicking anywhere outside it
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const filteredCountries = useMemo(() => {
    const q = countrySearch.trim().toLowerCase();
    if (!q) return AFRICA_COUNTRIES;
    return AFRICA_COUNTRIES.filter(
      c => c.name.toLowerCase().includes(q) || c.dial.includes(q),
    );
  }, [countrySearch]);

  // Build the full international phone number: dial code + local number
  // (leading zeros in the local part are removed, e.g. 0770... -> 770...)
  const buildFullPhone = () => {
    const local = phone.replace(/\D/g, '').replace(/^0+/, '');
    return `${country.dial}${local}`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (mode === 'register' && password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    const fullPhone = buildFullPhone();
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(fullPhone, password);
      } else {
        await register(fullPhone, password);
      }
      navigate('/chat', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode(mode === 'login' ? 'register' : 'login');
    setError('');
    setPassword('');
    setConfirmPassword('');
  };

  const resetInvite = () => {
    setShowInvite(false);
    setInviteStep('code');
    setInviteCode('');
    setInvitePhone('');
    setInvitePassword('');
    setInviteConfirmPassword('');
    setInviteError('');
  };

  const handleCheckCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteError('');
    if (!/^\d{6}$/.test(inviteCode.trim())) {
      setInviteError('Enter the 6-digit code exactly as it was given to you.');
      return;
    }
    setInviteLoading(true);
    try {
      const res: any = await (api as any).request('/invites/check', {
        method: 'POST',
        body: JSON.stringify({ code: inviteCode.trim() }),
      });
      setInvitePhone(res?.phone_number || '');
      setInviteStep('password');
    } catch (err: any) {
      setInviteError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setInviteLoading(false);
    }
  };

  const handleRedeem = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteError('');
    if (invitePassword !== inviteConfirmPassword) {
      setInviteError('Passwords do not match');
      return;
    }
    if (invitePassword.length < 6) {
      setInviteError('Password must be at least 6 characters');
      return;
    }
    setInviteLoading(true);
    try {
      const res: any = await (api as any).request('/invites/redeem', {
        method: 'POST',
        body: JSON.stringify({ code: inviteCode.trim(), password: invitePassword }),
      });
      api.setToken(res.access_token);
      await fetchUserData();
      navigate('/chat', { replace: true });
    } catch (err: any) {
      setInviteError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setInviteLoading(false);
    }
  };

  const inputClass =
    'w-full h-[52px] pl-11 pr-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white placeholder:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600 focus:border-[#3F0071] focus:ring-4 focus:ring-[#3F0071]/10 outline-none transition-[border-color,box-shadow] duration-150';

  return (
    <div className="min-h-screen flex">
      {/* ---------- Form panel (left) ---------- */}
      <div className="w-full lg:w-[46%] flex items-center justify-center bg-white dark:bg-gray-950 p-6 sm:p-10">
        <div className="fade-up w-full max-w-[420px]">
          {/* logo */}
          <img src={ozzyLogo} alt="Ozzy for Business" className="h-24 mb-8" />

          {showInvite ? (
            <>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                {inviteStep === 'code' ? 'Enter your invite code' : 'Set your password'}
              </h1>
              <p className="text-gray-500 dark:text-gray-400 mb-8">
                {inviteStep === 'code'
                  ? 'Ask the business owner for the 6-digit code they generated for you.'
                  : invitePhone
                    ? `Joining as ${invitePhone}. Choose a password to finish setting up your account.`
                    : 'Choose a password to finish setting up your account.'}
              </p>

              {inviteError && (
                <div
                  role="alert"
                  className="fade-up bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-900/40 p-3 rounded-xl text-sm mb-5"
                >
                  {inviteError}
                </div>
              )}

              {inviteStep === 'code' ? (
                <form onSubmit={handleCheckCode} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Invite Code</label>
                    <input
                      type="text"
                      inputMode="numeric"
                      maxLength={6}
                      className={`${inputClass} pl-4 text-center tracking-[0.5em] text-lg font-semibold`}
                      placeholder="000000"
                      value={inviteCode}
                      onChange={e => setInviteCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      required
                      autoFocus
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={inviteLoading}
                    className="w-full h-14 bg-[#3F0071] hover:bg-[#2E0054] active:scale-[0.98] text-white font-semibold rounded-xl transition-[background-color,transform] duration-150 ease-out disabled:opacity-60 disabled:active:scale-100 flex items-center justify-center gap-2 shadow-sm shadow-[#3F0071]/20"
                  >
                    {inviteLoading && <Loader2 size={18} className="animate-spin" />}
                    {inviteLoading ? 'Checking…' : 'Continue'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleRedeem} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Password</label>
                    <div className="relative">
                      <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type={inviteShowPassword ? 'text' : 'password'}
                        className={`${inputClass} pr-11`}
                        placeholder="At least 6 characters"
                        value={invitePassword}
                        onChange={e => setInvitePassword(e.target.value)}
                        required
                        minLength={6}
                        autoFocus
                      />
                      <button
                        type="button"
                        onClick={() => setInviteShowPassword(s => !s)}
                        aria-label={inviteShowPassword ? 'Hide password' : 'Show password'}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-150"
                      >
                        {inviteShowPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Confirm Password</label>
                    <div className="relative">
                      <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type={inviteShowPassword ? 'text' : 'password'}
                        className={inputClass}
                        placeholder="Re-enter your password"
                        value={inviteConfirmPassword}
                        onChange={e => setInviteConfirmPassword(e.target.value)}
                        required
                        minLength={6}
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={inviteLoading}
                    className="w-full h-14 bg-[#3F0071] hover:bg-[#2E0054] active:scale-[0.98] text-white font-semibold rounded-xl transition-[background-color,transform] duration-150 ease-out disabled:opacity-60 disabled:active:scale-100 flex items-center justify-center gap-2 shadow-sm shadow-[#3F0071]/20"
                  >
                    {inviteLoading && <Loader2 size={18} className="animate-spin" />}
                    {inviteLoading ? 'Setting up…' : 'Join Business'}
                  </button>
                </form>
              )}

              <p className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
                <button
                  type="button"
                  onClick={resetInvite}
                  className="font-semibold text-[#3F0071] dark:text-purple-300 hover:underline"
                >
                  Back to log in
                </button>
              </p>
            </>
          ) : (
          <>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            {mode === 'login' ? 'Welcome back' : 'Create your account'}
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mb-8">
            {mode === 'login'
              ? 'Log in to keep your business records up to date.'
              : 'Start tracking your business the easy way.'}
          </p>

          {error && (
            <div
              role="alert"
              className="fade-up bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-900/40 p-3 rounded-xl text-sm mb-5"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Phone number with country-code picker */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Phone Number</label>
              <div className="flex gap-2">
                {/* country picker */}
                <div className="relative" ref={pickerRef}>
                  <button
                    type="button"
                    onClick={() => setPickerOpen(o => !o)}
                    aria-label="Select country code"
                    className="h-[52px] flex items-center gap-1.5 px-3 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600 focus:border-[#3F0071] focus:ring-4 focus:ring-[#3F0071]/10 outline-none transition-[border-color,box-shadow] duration-150"
                  >
                    <span className="text-lg leading-none">{country.flag}</span>
                    <span className="text-sm text-gray-700 dark:text-gray-200">{country.dial}</span>
                    <ChevronDown size={15} className={`text-gray-400 transition-transform duration-150 ${pickerOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {pickerOpen && (
                    <div className="absolute z-50 top-full left-0 mt-2 w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl overflow-hidden">
                      <div className="p-2 border-b border-gray-100 dark:border-gray-700">
                        <div className="relative">
                          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                          <input
                            autoFocus
                            value={countrySearch}
                            onChange={e => setCountrySearch(e.target.value)}
                            placeholder="Search country…"
                            className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 dark:text-white rounded-lg outline-none focus:ring-2 focus:ring-[#3F0071]/20"
                          />
                        </div>
                      </div>
                      <div className="max-h-60 overflow-y-auto py-1">
                        {filteredCountries.map(c => (
                          <button
                            key={c.code}
                            type="button"
                            onClick={() => {
                              setCountry(c);
                              setPickerOpen(false);
                              setCountrySearch('');
                            }}
                            className="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                          >
                            <span className="text-lg leading-none">{c.flag}</span>
                            <span className="flex-1 text-sm text-gray-700 dark:text-gray-200 truncate">{c.name}</span>
                            <span className="text-sm text-gray-400">{c.dial}</span>
                          </button>
                        ))}
                        {filteredCountries.length === 0 && (
                          <p className="px-3 py-3 text-sm text-gray-400 text-center">No country found</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* local number */}
                <div className="relative flex-1">
                  <Phone size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="tel"
                    className={inputClass}
                    placeholder="700 000 000"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                    required
                    autoFocus
                  />
                </div>
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Password</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  className={`${inputClass} pr-11`}
                  placeholder="At least 6 characters"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(s => !s)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-150"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Confirm password — slides open in sign-up mode */}
            <div
              className="grid transition-[grid-template-rows] duration-300 ease-[cubic-bezier(0.23,1,0.32,1)]"
              style={{ gridTemplateRows: mode === 'register' ? '1fr' : '0fr' }}
            >
              <div className="overflow-hidden">
                <div className="pb-1">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Confirm Password</label>
                  <div className="relative">
                    <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      className={inputClass}
                      placeholder="Re-enter your password"
                      value={confirmPassword}
                      onChange={e => setConfirmPassword(e.target.value)}
                      required={mode === 'register'}
                      minLength={6}
                      tabIndex={mode === 'register' ? 0 : -1}
                    />
                  </div>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-14 bg-[#3F0071] hover:bg-[#2E0054] active:scale-[0.98] text-white font-semibold rounded-xl transition-[background-color,transform] duration-150 ease-out disabled:opacity-60 disabled:active:scale-100 flex items-center justify-center gap-2 shadow-sm shadow-[#3F0071]/20"
            >
              {loading && <Loader2 size={18} className="animate-spin" />}
              {loading
                ? (mode === 'login' ? 'Logging in…' : 'Creating account…')
                : (mode === 'login' ? 'Log In' : 'Create Account')}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button
              type="button"
              onClick={switchMode}
              className="font-semibold text-[#3F0071] dark:text-purple-300 hover:underline"
            >
              {mode === 'login' ? 'Create one' : 'Log in'}
            </button>
          </p>

          {mode === 'login' && (
            <p className="mt-3 text-center text-sm text-gray-500 dark:text-gray-400">
              <button
                type="button"
                onClick={() => setShowInvite(true)}
                className="font-semibold text-[#3F0071] dark:text-purple-300 hover:underline"
              >
                Have an invite code?
              </button>
            </p>
          )}
          </>
          )}
        </div>
      </div>

      {/* ---------- Photo panel (right, large screens only) ---------- */}
      <div className="hidden lg:block lg:w-[54%] relative overflow-hidden bg-[#3F0071]">
        <img
          src={ozzyHero}
          alt="A business owner tracking her sales by chatting with Ozzy"
          className="absolute inset-0 w-full h-full object-cover object-top"
        />
        {/* purple wash for depth + text legibility at the bottom */}
        <div
          className="absolute inset-0"
          style={{
            background:
              'linear-gradient(180deg, rgba(46,0,84,0.15) 0%, rgba(46,0,84,0.0) 40%, rgba(46,0,84,0.45) 80%, rgba(46,0,84,0.85) 100%)',
          }}
        ></div>

        <div className="absolute bottom-0 left-0 right-0 p-12 z-10">
          <h2 className="fade-up text-[2.4rem] font-bold text-white mb-3 leading-[1.15] tracking-tight">
            Track your business by chatting.
          </h2>
          <p className="fade-up fade-up-d1 text-purple-100/90 text-lg max-w-md">
            No spreadsheets, no accounting software, no training required.
          </p>
        </div>

        <p className="absolute top-8 right-12 text-white/80 text-sm font-medium tracking-wide z-10">
          Ozzy Africa Technologies
        </p>
      </div>
    </div>
  );
}
