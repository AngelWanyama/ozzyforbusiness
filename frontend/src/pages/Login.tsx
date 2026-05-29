import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Phone, ShieldCheck, ArrowLeft } from 'lucide-react';

export default function Login() {
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [debugCode, setDebugCode] = useState('');
  const { login, requestOTP } = useAuth();
  const navigate = useNavigate();

  const handlePhoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const result = await requestOTP(phone);
      setDebugCode(result.debug_code);
      setStep('otp');
    } catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  };

  const handleOtpChange = (i: number, v: string) => {
    if (v && !/^\d$/.test(v)) return;
    const next = [...otp]; next[i] = v; setOtp(next);
    if (v && i < 5) document.getElementById(`otp-${i + 1}`)?.focus();
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const code = otp.join('');
      if (code.length !== 6) { setError('Enter full 6-digit code'); setLoading(false); return; }
      await login(phone, code);
      navigate('/dashboard', { replace: true });
    } catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#FEF7ED] to-white dark:from-gray-900 dark:to-gray-950 p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-[#0D9488] rounded-2xl flex items-center justify-center text-4xl mx-auto mb-4 shadow-lg">🦉</div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Ozzy for Business</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Track your business finances the easy way</p>
        </div>

        {error && <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 p-3 rounded-xl text-sm mb-4 text-center">{error}</div>}

        {step === 'phone' ? (
          <form onSubmit={handlePhoneSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Phone Number</label>
              <div className="relative">
                <Phone size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input type="tel" className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#0D9488] focus:border-transparent outline-none transition" placeholder="+256 7XX XXX XXX" value={phone} onChange={e => setPhone(e.target.value)} required autoFocus />
              </div>
            </div>
            <button type="submit" disabled={loading} className="w-full py-3 bg-[#0D9488] hover:bg-[#0B7A70] text-white font-semibold rounded-xl transition disabled:opacity-50">
              {loading ? 'Sending...' : 'Send Code'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleOtpSubmit} className="space-y-4">
            <div className="text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">Enter code sent to <strong className="text-gray-700 dark:text-gray-200">{phone}</strong></p>
            </div>
            <div className="flex gap-2 justify-center">
              {otp.map((d, i) => (
                <input key={i} id={`otp-${i}`} type="text" className="w-12 h-14 text-center text-xl font-bold border-2 border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#0D9488] focus:border-transparent outline-none transition" maxLength={1} value={d} onChange={e => handleOtpChange(i, e.target.value)} autoFocus={i === 0} />
              ))}
            </div>
            {debugCode && (
              <div className="bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 p-3 rounded-xl text-sm text-center">
                Debug: Your OTP is <strong>{debugCode}</strong><br />
                <span className="text-xs">(In production, sent via SMS)</span>
              </div>
            )}
            <button type="submit" disabled={loading} className="w-full py-3 bg-[#0D9488] hover:bg-[#0B7A70] text-white font-semibold rounded-xl transition disabled:opacity-50">
              {loading ? 'Verifying...' : 'Verify & Login'}
            </button>
            <button type="button" onClick={() => { setStep('phone'); setOtp(['', '', '', '', '', '']); setError(''); }} className="w-full py-3 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition flex items-center justify-center gap-1">
              <ArrowLeft size={16} /> Change Phone Number
            </button>
          </form>
        )}
      </div>
    </div>
  );
}