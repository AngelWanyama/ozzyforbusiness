import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const [step, setStep] = useState('phone'); // phone | otp
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [debugCode, setDebugCode] = useState('');
  const { login, requestOTP } = useAuth();
  const navigate = useNavigate();

  const handlePhoneSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await requestOTP(phone);
      setDebugCode(result.debug_code);
      setStep('otp');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOtpChange = (index, value) => {
    if (value && !/^\d$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Auto-advance to next input
    if (value && index < 5) {
      const next = document.getElementById(`otp-${index + 1}`);
      if (next) next.focus();
    }
  };

  const handleOtpSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const code = otp.join('');
      if (code.length !== 6) {
        setError('Please enter the full 6-digit code');
        setLoading(false);
        return;
      }
      await login(phone, code);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-logo">
        <span role="img" aria-label="Ozzy">🦉</span>
      </div>
      <h1>Ozzy for Business</h1>
      <p>Track your business finances the easy way</p>

      {error && <div className="error-msg">{error}</div>}

      <div className="login-form">
        {step === 'phone' ? (
          <form onSubmit={handlePhoneSubmit}>
            <div className="form-group">
              <label>Phone Number</label>
              <input
                type="tel"
                className="form-input"
                placeholder="+256 7XX XXX XXX"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
                autoFocus
              />
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? 'Sending...' : 'Send Code'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleOtpSubmit}>
            <div className="form-group">
              <label>Enter 6-digit code sent to {phone}</label>
              <div className="otp-inputs">
                {otp.map((digit, i) => (
                  <input
                    key={i}
                    id={`otp-${i}`}
                    type="text"
                    className="otp-input"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(i, e.target.value)}
                    onFocus={(e) => e.target.select()}
                    autoFocus={i === 0}
                  />
                ))}
              </div>
            </div>
            {debugCode && (
              <div className="success-msg">
                Debug: Your OTP is <strong>{debugCode}</strong>
                <br />
                <small>(In production, this will be sent via SMS)</small>
              </div>
            )}
            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? 'Verifying...' : 'Verify & Login'}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-block mt-16"
              onClick={() => { setStep('phone'); setOtp(['', '', '', '', '', '']); setError(''); }}
            >
              Change Phone Number
            </button>
          </form>
        )}
      </div>
    </div>
  );
}