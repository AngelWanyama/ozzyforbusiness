import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';

function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

function Toggle({ checked, onChange }: { checked: boolean; onChange?: () => void }) {
  return (
    <label className="relative inline-flex items-center cursor-pointer">
      <input checked={checked} onChange={onChange} className="sr-only peer" type="checkbox" />
      <div className="w-11 h-6 bg-surface-container-highest rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
    </label>
  );
}

function Row({ label, icon }: { label: string; icon: string }) {
  return (
    <button className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
      <span className="font-label-md text-label-md text-on-surface-variant">{label}</span>
      <Icon name={icon} className="text-outline group-hover:translate-x-1 transition-transform" />
    </button>
  );
}

const CURRENCIES = ['UGX', 'KES', 'USD', 'TZS', 'RWF'];
const BUSINESS_TYPES = ['Retail & Distribution', 'Food & Restaurant', 'Salon & Beauty', 'Services', 'Agriculture', 'Technology & Software', 'Other'];

export default function Settings() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [dark, setDark] = useState(() => localStorage.getItem('ozzy_dark') === '1');
  const [notif, setNotif] = useState(true);
  const [bio, setBio] = useState(true);

  const [phone, setPhone] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [businessType, setBusinessType] = useState('');
  const [currency, setCurrency] = useState('UGX');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('ozzy_dark', dark ? '1' : '0');
  }, [dark]);

  useEffect(() => {
    api.getMe()
      .then((u: any) => {
        setPhone(u?.phone_number || '');
        setBusinessName(u?.business_name || '');
        setBusinessType(u?.business_type || '');
        setCurrency(u?.currency || 'UGX');
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await api.updateMe({ business_name: businessName, business_type: businessType, currency });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch {
      // keep quiet UI; could add error toast later
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => { logout(); navigate('/login'); };

  const displayName = businessName || 'Your business';

  return (
    <main className="bg-surface-container-low min-h-screen">
      <div className="max-w-[800px] mx-auto px-margin-mobile md:px-xl py-xl space-y-xl">
        {/* Profile Card */}
        <section className="bg-surface p-xl rounded-xl border border-outline-variant flex flex-col md:flex-row items-center justify-between gap-lg">
          <div className="flex items-center gap-lg w-full">
            <div className="relative group">
              <div className="w-24 h-24 rounded-full overflow-hidden border-4 border-primary-container bg-surface-container flex items-center justify-center">
                <Icon name="storefront" className="text-primary text-[40px]" />
              </div>
              <button className="absolute bottom-0 right-0 p-1.5 bg-primary text-on-primary rounded-full border-2 border-surface hover:scale-110 transition-transform">
                <Icon name="edit" className="text-[18px]" />
              </button>
            </div>
            <div className="flex-grow">
              <h3 className="font-headline-md text-headline-md text-on-surface">{loading ? 'Loading...' : displayName}</h3>
              <p className="font-body-md text-body-md text-on-surface-variant">{phone || '-'}</p>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-bold bg-secondary-container text-on-secondary-container mt-xs uppercase tracking-wider">Owner</span>
            </div>
          </div>
        </section>

        {/* Business Settings */}
        <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-lg">
          <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2"><Icon name="business" /> Business Settings</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
            <div className="space-y-sm">
              <label className="font-label-md text-label-md text-on-surface-variant ml-1">Business Name</label>
              <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                <Icon name="corporate_fare" className="text-outline" />
                <input value={businessName} onChange={e => setBusinessName(e.target.value)} placeholder="Enter your business name" className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none" type="text" />
              </div>
            </div>
            <div className="space-y-sm">
              <label className="font-label-md text-label-md text-on-surface-variant ml-1">Currency</label>
              <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                <Icon name="payments" className="text-outline" />
                <select value={currency} onChange={e => setCurrency(e.target.value)} className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none">
                  {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
            <div className="space-y-sm">
              <label className="font-label-md text-label-md text-on-surface-variant ml-1">Business Type</label>
              <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                <Icon name="category" className="text-outline" />
                <select value={businessType} onChange={e => setBusinessType(e.target.value)} className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none">
                  <option value="">Select a type</option>
                  {BUSINESS_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
            <div className="space-y-sm">
              <label className="font-label-md text-label-md text-on-surface-variant ml-1">Phone Number</label>
              <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm">
                <Icon name="call" className="text-outline" />
                <input value={phone} disabled className="bg-transparent border-none focus:ring-0 w-full font-body-md text-on-surface-variant cursor-not-allowed outline-none" type="text" />
              </div>
            </div>
          </div>
          <div className="flex items-center gap-md">
            <button onClick={save} disabled={saving} className="h-12 px-xl flex items-center justify-center bg-primary text-white rounded-xl font-bold hover:opacity-90 transition-all active:scale-95 duration-200 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            {saved && <span className="flex items-center gap-1 text-green-600 font-label-md"><Icon name="check_circle" className="text-[18px]" /> Saved</span>}
          </div>
        </div>

        {/* App Settings */}
        <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
          <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2"><Icon name="tune" /> App Settings</h4>
          <div className="flex flex-col gap-sm">
            <div className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg">
              <div className="flex flex-col">
                <span className="font-label-md text-label-md text-on-surface">Notifications</span>
                <span className="text-[12px] text-on-surface-variant">Push and SMS alerts</span>
              </div>
              <Toggle checked={notif} onChange={() => setNotif(v => !v)} />
            </div>
            <div className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg">
              <div className="flex flex-col">
                <span className="font-label-md text-label-md text-on-surface">Dark Mode</span>
                <span className="text-[12px] text-on-surface-variant">Switch theme</span>
              </div>
              <Toggle checked={dark} onChange={() => setDark(v => !v)} />
            </div>
          </div>
        </div>

        {/* Support */}
        <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
          <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2"><Icon name="support_agent" /> Support</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-md">
            {[
              { i: 'help', t: 'Help Center', s: 'Tutorials & FAQs' },
              { i: 'mail', t: 'Contact Support', s: 'Chat with us' },
              { i: 'info', t: 'About Ozzy', s: 'Version 1.0' },
            ].map(b => (
              <button key={b.t} className="flex flex-col items-center justify-center p-lg bg-surface-container-low hover:bg-surface-container-high rounded-xl border border-outline-variant transition-all hover:shadow-sm">
                <Icon name={b.i} className="text-primary mb-2" />
                <span className="font-label-md text-label-md font-bold">{b.t}</span>
                <span className="text-[12px] text-on-surface-variant">{b.s}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Bottom */}
        <div className="flex flex-col items-center gap-lg py-xl">
          <button onClick={handleLogout} className="w-full md:w-max h-12 px-xxl flex items-center justify-center gap-2 text-error border border-error bg-transparent rounded-xl font-bold hover:bg-error-container transition-all active:scale-95 duration-200">
            <Icon name="logout" /> Logout Account
          </button>
          <p className="text-[12px] text-on-surface-variant opacity-60 text-center">Ozzy for Business © 2026</p>
        </div>
      </div>
    </main>
  );
}
