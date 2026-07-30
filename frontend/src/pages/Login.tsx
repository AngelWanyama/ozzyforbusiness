import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Phone, Lock, UserPlus, LogIn, Mic, TrendingUp, MapPin, FileText } from 'lucide-react';
import ozzyLogo from '../assets/ozzy-logo.png';

export default function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (mode === 'register' && password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      if (mode === 'login') {
        await login(phone, password);
      } else {
        await register(phone, password);
      }
      navigate('/dashboard', { replace: true });
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

  const features = [
    { icon: Mic, text: 'Speak your transactions instead of typing, in English' },
    { icon: FileText, text: 'Generate invoices and receipts on the spot, with your business logo' },
    { icon: TrendingUp, text: 'Get daily profit summaries and trends, automatically' },
    { icon: MapPin, text: 'Built for local currency and how business really works across Africa' },
  ];

  return (
    <div className="min-h-screen flex">
      {/* Brand panel — hidden on small screens, shown from large screens up */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#3F0071] flex-col justify-center px-16 relative overflow-hidden">
        {/* decorative background circles */}
        <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-white/5"></div>
        <div className="absolute bottom-0 right-0 w-72 h-72 rounded-full bg-white/5 translate-x-1/3 translate-y-1/3"></div>

        <div className="relative z-10 max-w-md">
          <h2 className="text-4xl font-bold text-white mb-4 leading-tight">
            Track your business by chatting.
          </h2>
          <p className="text-purple-200 mb-10 text-lg">
            No spreadsheets, no accounting software, no training required.
          </p>
          <div className="space-y-5">
            {features.map((f, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-white/10 flex items-center justify-center flex-shrink-0">
                  <f.icon size={18} className="text-white" />
                </div>
                <p className="text-purple-100 text-sm pt-1.5">{f.text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Form panel */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-gradient-to-br from-white to-[#F9FAFB] dark:from-gray-900 dark:to-gray-950 p-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <img src={ozzyLogo} alt="Ozzy for Business" className="h-32 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">Track your business finances the easy way</p>
          </div>

          {error && <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 p-3 rounded-xl text-sm mb-4 text-center">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Phone Number</label>
              <div className="relative">
                <Phone size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="tel"
                  className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#3F0071] focus:border-transparent outline-none transition"
                  placeholder="+256 7XX XXX XXX"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  required
                  autoFocus
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Password</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="password"
                  className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#3F0071] focus:border-transparent outline-none transition"
                  placeholder="At least 6 characters"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  minLength={6}
                />
              </div>
            </div>

            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Confirm Password</label>
                <div className="relative">
                  <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="password"
                    className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#3F0071] focus:border-transparent outline-none transition"
                    placeholder="Re-enter your password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    required
                    minLength={6}
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-[#3F0071] hover:bg-[#2E0054] text-white font-semibold rounded-xl transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {mode === 'login' ? <LogIn size={18} /> : <UserPlus size={18} />}
              {loading ? (mode === 'login' ? 'Logging in...' : 'Creating account...') : (mode === 'login' ? 'Log In' : 'Create Account')}
            </button>

            <button
              type="button"
              onClick={switchMode}
              className="w-full py-2 text-sm text-gray-500 dark:text-gray-400 hover:text-[#3F0071] dark:hover:text-gray-200 transition text-center"
            >
              {mode === 'login' ? "Don't have an account? Create one" : "Already have an account? Log in"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}