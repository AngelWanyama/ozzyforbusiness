import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { AFRICA_COUNTRIES } from '../data/africaCountries';

function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span className="material-symbols-outlined" style={{ fontSize: 'inherit' }}>{name}</span>;
}

// Every African currency, so Ozzy can serve the whole continent.
const AFRICA_CURRENCIES = [
  { code: 'UGX', label: 'UGX — Ugandan Shilling' },
  { code: 'KES', label: 'KES — Kenyan Shilling' },
  { code: 'TZS', label: 'TZS — Tanzanian Shilling' },
  { code: 'RWF', label: 'RWF — Rwandan Franc' },
  { code: 'BIF', label: 'BIF — Burundian Franc' },
  { code: 'SSP', label: 'SSP — South Sudanese Pound' },
  { code: 'ETB', label: 'ETB — Ethiopian Birr' },
  { code: 'SOS', label: 'SOS — Somali Shilling' },
  { code: 'DJF', label: 'DJF — Djiboutian Franc' },
  { code: 'ERN', label: 'ERN — Eritrean Nakfa' },
  { code: 'NGN', label: 'NGN — Nigerian Naira' },
  { code: 'GHS', label: 'GHS — Ghanaian Cedi' },
  { code: 'XOF', label: 'XOF — West African CFA Franc' },
  { code: 'XAF', label: 'XAF — Central African CFA Franc' },
  { code: 'GNF', label: 'GNF — Guinean Franc' },
  { code: 'SLL', label: 'SLL — Sierra Leonean Leone' },
  { code: 'LRD', label: 'LRD — Liberian Dollar' },
  { code: 'GMD', label: 'GMD — Gambian Dalasi' },
  { code: 'MRU', label: 'MRU — Mauritanian Ouguiya' },
  { code: 'CVE', label: 'CVE — Cape Verdean Escudo' },
  { code: 'STN', label: 'STN — São Tomé and Príncipe Dobra' },
  { code: 'AOA', label: 'AOA — Angolan Kwanza' },
  { code: 'ZMW', label: 'ZMW — Zambian Kwacha' },
  { code: 'ZWL', label: 'ZWL — Zimbabwean Dollar' },
  { code: 'MWK', label: 'MWK — Malawian Kwacha' },
  { code: 'MZN', label: 'MZN — Mozambican Metical' },
  { code: 'BWP', label: 'BWP — Botswana Pula' },
  { code: 'NAD', label: 'NAD — Namibian Dollar' },
  { code: 'ZAR', label: 'ZAR — South African Rand' },
  { code: 'LSL', label: 'LSL — Lesotho Loti' },
  { code: 'SZL', label: 'SZL — Eswatini Lilangeni' },
  { code: 'MGA', label: 'MGA — Malagasy Ariary' },
  { code: 'MUR', label: 'MUR — Mauritian Rupee' },
  { code: 'SCR', label: 'SCR — Seychellois Rupee' },
  { code: 'KMF', label: 'KMF — Comorian Franc' },
  { code: 'EGP', label: 'EGP — Egyptian Pound' },
  { code: 'LYD', label: 'LYD — Libyan Dinar' },
  { code: 'TND', label: 'TND — Tunisian Dinar' },
  { code: 'DZD', label: 'DZD — Algerian Dinar' },
  { code: 'MAD', label: 'MAD — Moroccan Dirham' },
  { code: 'SDG', label: 'SDG — Sudanese Pound' },
  { code: 'USD', label: 'USD — US Dollar' },
];

// Split a stored international number (e.g. +256700123456) into flag + local part for display.
function phoneParts(full: string) {
  const match = AFRICA_COUNTRIES
    .slice()
    .sort((a, b) => b.dial.length - a.dial.length)
    .find(c => full.startsWith(c.dial));
  if (match) {
    return { flag: match.flag, dial: match.dial, local: full.slice(match.dial.length) };
  }
  return { flag: '🌍', dial: '', local: full };
}

export default function Settings() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [dark, setDark] = useState(() => localStorage.getItem('ozzy_dark') === '1');

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
    setSaving(true); setSaved(false);
    try {
      await api.updateMe({ business_name: businessName, business_type: businessType, currency });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch { /* silent for now */ } finally { setSaving(false); }
  };

  const handleLogout = () => { logout(); navigate('/login'); };

  const p = phoneParts(phone);
  const displayName = businessName || (loading ? 'Loading...' : 'Your business');

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
              <button className="absolute bottom-0 right-0 p-1.5 bg-primary text-on-primary rounded-full border-2 border-surface hover:scale-110 transition-transform text-[18px]">
                <Icon name="edit" />
              </button>
            </div>
            <div className="flex-grow">
              <h3 className="font-headline-md text-headline-md text-on-surface">{displayName}</h3>
              <p className="font-body-md text-body-md text-on-surface-variant">{p.flag} {p.dial} {p.local || ''}</p>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-bold bg-secondary-container text-on-secondary-container mt-xs uppercase tracking-wider">Owner</span>
            </div>
            <button className="hidden md:flex h-12 px-lg items-center justify-center border border-primary text-primary rounded-xl font-bold hover:bg-primary/5 transition-all active:scale-95 duration-200">Edit Profile</button>
          </div>
          <button className="md:hidden w-full h-12 flex items-center justify-center border border-primary text-primary rounded-xl font-bold hover:bg-primary/5 transition-all active:scale-95 duration-200">Edit Profile</button>
        </section>

        {/* Bento grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">

          {/* Account */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="person" /> Account</h4>
            <div className="flex flex-col">
              <button className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
                <span className="font-label-md text-label-md text-on-surface-variant">Profile Details</span>
                <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name="chevron_right" /></span>
              </button>
              <button className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
                <span className="font-label-md text-label-md text-on-surface-variant">Add Another Account</span>
                <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name="add_circle" /></span>
              </button>
              <button className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
                <span className="font-label-md text-label-md text-on-surface-variant">Switch Business</span>
                <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name="swap_horiz" /></span>
              </button>
            </div>
          </div>

          {/* Team & Access */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="group" /> Team &amp; Access</h4>
            <div className="flex flex-col">
              <button className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
                <span className="font-label-md text-label-md text-on-surface-variant">Add Worker</span>
                <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name="person_add" /></span>
              </button>
              <button className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
                <span className="font-label-md text-label-md text-on-surface-variant">Manage Access</span>
                <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name="lock_person" /></span>
              </button>
              <button className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
                <span className="font-label-md text-label-md text-on-surface-variant">Shop Assistant Access</span>
                <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name="storefront" /></span>
              </button>
            </div>
          </div>

          {/* Business Settings */}
          <div className="md:col-span-2 bg-surface p-lg rounded-xl border border-outline-variant space-y-lg">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="business" /> Business Settings</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
              <div className="space-y-sm">
                <label className="font-label-md text-label-md text-on-surface-variant ml-1">Business Name</label>
                <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                  <span className="text-outline text-[20px]"><Icon name="corporate_fare" /></span>
                  <input value={businessName} onChange={e => setBusinessName(e.target.value)} placeholder="Enter your business name" className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none" type="text" />
                </div>
              </div>
              <div className="space-y-sm">
                <label className="font-label-md text-label-md text-on-surface-variant ml-1">Currency</label>
                <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                  <span className="text-outline text-[20px]"><Icon name="payments" /></span>
                  <select value={currency} onChange={e => setCurrency(e.target.value)} className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none">
                    {AFRICA_CURRENCIES.map(c => <option key={c.code} value={c.code}>{c.label}</option>)}
                  </select>
                </div>
              </div>
              <div className="space-y-sm">
                <label className="font-label-md text-label-md text-on-surface-variant ml-1">Business Type</label>
                <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                  <span className="text-outline text-[20px]"><Icon name="category" /></span>
                  <select value={businessType} onChange={e => setBusinessType(e.target.value)} className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none">
                    <option value="">Select a type</option>
                    <option>Retail &amp; Distribution</option>
                    <option>Food &amp; Restaurant</option>
                    <option>Salon &amp; Beauty</option>
                    <option>Fashion &amp; Tailoring</option>
                    <option>Services</option>
                    <option>Agriculture</option>
                    <option>Logistics</option>
                    <option>Technology &amp; Software</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-lg p-md bg-surface-container-lowest border border-dashed border-outline-variant rounded-lg">
                <div className="w-16 h-16 bg-surface-container rounded-lg flex items-center justify-center text-outline text-[24px]"><Icon name="image" /></div>
                <div className="flex-grow">
                  <h5 className="font-label-md text-label-md text-on-surface font-bold">Business Logo</h5>
                  <p className="text-[12px] text-on-surface-variant italic">used on invoices &amp; receipts</p>
                  <button className="text-primary font-bold text-[14px] mt-1 hover:underline">Change Logo</button>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-md">
              <button onClick={save} disabled={saving} className="h-12 px-xl flex items-center justify-center bg-primary text-white rounded-xl font-bold hover:opacity-90 transition-all active:scale-95 duration-200 disabled:opacity-50">
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              {saved && <span className="flex items-center gap-1 text-green-600 font-label-md"><span className="text-[18px]"><Icon name="check_circle" /></span> Saved</span>}
            </div>
          </div>

          {/* App Settings */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="tune" /> App Settings</h4>
            <div className="flex flex-col gap-sm">
              <div className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg">
                <div className="flex flex-col">
                  <span className="font-label-md text-label-md text-on-surface">Notifications</span>
                  <span className="text-[12px] text-on-surface-variant">Push and SMS alerts</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input defaultChecked className="sr-only peer" type="checkbox" />
                  <div className="w-11 h-6 bg-surface-container-highest rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
              <div className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg">
                <div className="flex flex-col">
                  <span className="font-label-md text-label-md text-on-surface">Dark Mode</span>
                  <span className="text-[12px] text-on-surface-variant">Switch theme</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input checked={dark} onChange={() => setDark(v => !v)} className="sr-only peer" type="checkbox" />
                  <div className="w-11 h-6 bg-surface-container-highest rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Security */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="shield" /> Security</h4>
            <div className="flex flex-col">
              <button className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
                <span className="font-label-md text-label-md text-on-surface-variant">Change PIN</span>
                <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name="pin" /></span>
              </button>
              <div className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg">
                <span className="font-label-md text-label-md text-on-surface-variant">Biometric Login</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input defaultChecked className="sr-only peer" type="checkbox" />
                  <div className="w-11 h-6 bg-surface-container-highest rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Support */}
          <div className="md:col-span-2 bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="support_agent" /> Support</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-md">
              {[
                { i: 'help', t: 'Help Center', s: 'Tutorials & FAQs' },
                { i: 'mail', t: 'Contact Support', s: 'Chat with us' },
                { i: 'info', t: 'About Ozzy', s: 'Version 1.0' },
              ].map(b => (
                <button key={b.t} className="flex flex-col items-center justify-center p-lg bg-surface-container-low hover:bg-surface-container-high rounded-xl border border-outline-variant transition-all hover:shadow-sm">
                  <span className="text-primary mb-2 text-[24px]"><Icon name={b.i} /></span>
                  <span className="font-label-md text-label-md font-bold">{b.t}</span>
                  <span className="text-[12px] text-on-surface-variant">{b.s}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom */}
        <div className="flex flex-col items-center gap-lg py-xl">
          <button onClick={handleLogout} className="w-full md:w-max h-12 px-xxl flex items-center justify-center gap-2 text-error border border-error bg-transparent rounded-xl font-bold hover:bg-error-container transition-all active:scale-95 duration-200">
            <Icon name="logout" /> Logout Account
          </button>
          <p className="text-[12px] text-on-surface-variant opacity-60 text-center">Ozzy for Business • © 2026</p>
        </div>
      </div>
    </main>
  );
}
