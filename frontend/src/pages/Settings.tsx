import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { AFRICA_COUNTRIES } from '../data/africaCountries';

function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`} style={{ fontSize: 'inherit' }}>{name}</span>;
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

// Short FAQ shown in the Help Center panel.
const HELP_FAQS = [
  { q: 'How do I record a sale or expense?', a: 'Go to Chat and type it in plain language, like "Sold 3 sodas 6,000" or "Bought airtime 5,000". Ozzy will confirm before saving it.' },
  { q: 'How do I change my business name, type, or currency?', a: 'Open Settings and edit the Business Settings card, then tap Save Changes.' },
  { q: 'How do I add my business logo?', a: 'In Settings, tap the pencil icon on your profile picture, or "Change Logo" in the Business Logo card, and choose a PNG, JPEG, or WEBP image under 5MB.' },
  { q: 'Can workers see everything I see?', a: 'Not yet fully built — workers will only be able to record sales/expenses and see recent activity, without access to reports or settings.' },
  { q: 'Is my business data private?', a: 'Yes. Only your account (and, once the Workers feature is finished, staff you personally invite) can see your business data.' },
];

// Turn a stored image path like "/uploads/logos/xyz.png" into a full URL against the backend host.
const API_ORIGIN = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/?api\/v1\/?$/, '');
function logoSrc(url?: string | null) {
  if (!url) return '';
  return url.startsWith('http') ? url : `${API_ORIGIN}${url}`;
}

const ALLOWED_LOGO_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
const MAX_LOGO_BYTES = 5 * 1024 * 1024; // 5MB, matches backend limit

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

// A settings row for a feature that isn't built yet — stays visible, but is honest that it's not live.
function ComingSoonRow({ icon, label, onClick }: { icon: string; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
      <span className="flex items-center gap-2">
        <span className="font-label-md text-label-md text-on-surface-variant">{label}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-surface-container-highest text-on-surface-variant">Soon</span>
      </span>
      <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name={icon} /></span>
    </button>
  );
}

export default function Settings() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [dark, setDark] = useState(() => localStorage.getItem('ozzy_dark') === '1');

  const [phone, setPhone] = useState('');
  const [role, setRole] = useState('owner');
  const [businessName, setBusinessName] = useState('');
  const [businessType, setBusinessType] = useState('');
  const [currency, setCurrency] = useState('UGX');
  const [ownerName, setOwnerName] = useState('');
  const [email, setEmail] = useState('');
  const [businessDescription, setBusinessDescription] = useState('');
  const [yearsInBusiness, setYearsInBusiness] = useState('');
  const [logoUrl, setLogoUrl] = useState('');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [editingProfile, setEditingProfile] = useState(false);

  const [logoUploading, setLogoUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [toast, setToast] = useState<string | null>(null);
  const [supportModal, setSupportModal] = useState<'help' | 'contact' | 'about' | null>(null);

  // Add Worker / Manage Access (Team & Access)
  const [addWorkerOpen, setAddWorkerOpen] = useState(false);
  const [workerPhoneInput, setWorkerPhoneInput] = useState('');
  const [generatingCode, setGeneratingCode] = useState(false);
  const [generateError, setGenerateError] = useState('');
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);
  const [manageAccessOpen, setManageAccessOpen] = useState(false);
  const [workersList, setWorkersList] = useState<any[]>([]);
  const [workersLoading, setWorkersLoading] = useState(false);
  const [workersError, setWorkersError] = useState('');

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('ozzy_dark', dark ? '1' : '0');
  }, [dark]);

  useEffect(() => {
    api.getMe()
      .then((u: any) => {
        setPhone(u?.phone_number || '');
        setRole(u?.role || 'owner');
        setBusinessName(u?.business_name || '');
        setBusinessType(u?.business_type || '');
        setCurrency(u?.currency || 'UGX');
        setOwnerName(u?.owner_name || '');
        setEmail(u?.email || '');
        setBusinessDescription(u?.business_description || '');
        setYearsInBusiness(u?.years_in_business != null ? String(u.years_in_business) : '');
        setLogoUrl(u?.logo_url || '');
        setNotificationsEnabled(u?.notifications_enabled !== false);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const showToast = (msg: string) => setToast(msg);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(t);
  }, [toast]);

  const comingSoon = (label: string) => showToast(`${label} is coming soon.`);

  const save = async () => {
    setSaving(true); setSaved(false);
    try {
      await api.updateMe({
        business_name: businessName,
        business_type: businessType,
        currency,
        owner_name: ownerName,
        email,
        business_description: businessDescription,
        years_in_business: yearsInBusiness.trim() ? parseInt(yearsInBusiness, 10) : undefined,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch {
      showToast('Could not save your changes. Check your connection and try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleLogoChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (!ALLOWED_LOGO_TYPES.includes(file.type)) {
      showToast('Please choose a PNG, JPEG, or WEBP image.');
      return;
    }
    if (file.size > MAX_LOGO_BYTES) {
      showToast('That image is too big — please choose one under 5MB.');
      return;
    }
    setLogoUploading(true);
    try {
      const updated: any = await api.uploadLogo(file);
      setLogoUrl(updated?.logo_url || '');
      showToast('Logo updated.');
    } catch (err: any) {
      showToast(err?.message || 'Could not upload logo. Try again.');
    } finally {
      setLogoUploading(false);
    }
  };

  const handleNotifToggle = async () => {
    const next = !notificationsEnabled;
    setNotificationsEnabled(next);
    try {
      await api.updateMe({ notifications_enabled: next });
    } catch {
      setNotificationsEnabled(!next);
      showToast('Could not update notifications. Try again.');
    }
  };

  const handleLogout = () => { logout(); navigate('/login'); };

  const openAddWorker = () => {
    setAddWorkerOpen(true);
    setGeneratedCode(null);
    setGenerateError('');
    setWorkerPhoneInput('');
  };

  const generateInviteCode = async () => {
    setGeneratingCode(true);
    setGenerateError('');
    try {
      const body: any = {};
      if (workerPhoneInput.trim()) body.phone_number = workerPhoneInput.trim();
      const res: any = await (api as any).request('/invites/generate', { method: 'POST', body: JSON.stringify(body) });
      setGeneratedCode(res.code);
    } catch (err: any) {
      setGenerateError(err?.message || 'Could not generate an invite code. Please try again.');
    } finally {
      setGeneratingCode(false);
    }
  };

  const copyInviteCode = async () => {
    if (!generatedCode) return;
    try {
      await navigator.clipboard.writeText(generatedCode);
      showToast('Code copied to clipboard.');
    } catch {
      showToast('Could not copy the code.');
    }
  };

  const openManageAccess = async () => {
    setManageAccessOpen(true);
    setWorkersLoading(true);
    setWorkersError('');
    try {
      const res: any = await (api as any).request('/invites/workers');
      setWorkersList(Array.isArray(res) ? res : []);
    } catch (err: any) {
      setWorkersError(err?.message || 'Could not load your workers. Please try again.');
    } finally {
      setWorkersLoading(false);
    }
  };

  const p = phoneParts(phone);
  const displayName = businessName || (loading ? 'Loading...' : 'Your business');

  if (!loading && role === 'worker') {
    return (
      <div className="min-h-screen flex items-center justify-center p-xl text-center">
        <div>
          <Icon name="lock" className="text-outline text-[40px]" />
          <p className="font-body-md text-body-md text-on-surface-variant mt-md">Settings are only available to the business owner.</p>
        </div>
      </div>
    );
  }

  return (
    <main className="bg-surface-container-low min-h-screen">
      <div className="max-w-[800px] mx-auto px-margin-mobile md:px-xl py-xl space-y-xl">

        {/* Hidden file input shared by both logo triggers */}
        <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleLogoChange} />

        {/* Profile Card */}
        <section className="bg-surface p-xl rounded-xl border border-outline-variant flex flex-col md:flex-row items-center justify-between gap-lg">
          <div className="flex flex-col w-full">
            <div className="flex items-center gap-lg w-full">
              <div className="relative group">
                <div className="w-24 h-24 rounded-full overflow-hidden border-4 border-primary-container bg-surface-container flex items-center justify-center">
                  {logoUrl ? (
                    <img src={logoSrc(logoUrl)} alt="Business logo" className="w-full h-full object-cover" />
                  ) : (
                    <Icon name="storefront" className="text-primary text-[40px]" />
                  )}
                </div>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={logoUploading}
                  className="absolute bottom-0 right-0 p-1.5 bg-primary text-on-primary rounded-full border-2 border-surface hover:scale-110 transition-transform text-[18px] disabled:opacity-50"
                >
                  <Icon name={logoUploading ? 'progress_activity' : 'edit'} />
                </button>
              </div>
              <div className="flex-grow">
                <h3 className="font-headline-md text-headline-md text-on-surface">{displayName}</h3>
                {ownerName && <p className="text-[13px] text-on-surface-variant">{ownerName}</p>}
                <p className="font-body-md text-body-md text-on-surface-variant">{p.flag} {p.dial} {p.local || ''}</p>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-bold bg-secondary-container text-on-secondary-container mt-xs uppercase tracking-wider">
                  {role === 'worker' ? 'Worker' : 'Owner'}
                </span>
              </div>
              <button
                onClick={() => setEditingProfile(v => !v)}
                className="hidden md:flex h-12 px-lg items-center justify-center border border-primary text-primary rounded-xl font-bold hover:bg-primary/5 transition-all active:scale-95 duration-200"
              >
                {editingProfile ? 'Close' : 'Edit Profile'}
              </button>
            </div>

            {editingProfile && (
              <div className="w-full mt-lg pt-lg border-t border-outline-variant grid grid-cols-1 md:grid-cols-2 gap-lg">
                <div className="space-y-sm">
                  <label className="font-label-md text-label-md text-on-surface-variant ml-1">Your Name</label>
                  <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                    <span className="text-outline text-[20px]"><Icon name="person" /></span>
                    <input value={ownerName} onChange={e => setOwnerName(e.target.value)} placeholder="Your full name" className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none" type="text" />
                  </div>
                </div>
                <div className="space-y-sm">
                  <label className="font-label-md text-label-md text-on-surface-variant ml-1">Email (optional)</label>
                  <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                    <span className="text-outline text-[20px]"><Icon name="mail" /></span>
                    <input value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none" type="email" />
                  </div>
                </div>
                <div className="space-y-sm">
                  <label className="font-label-md text-label-md text-on-surface-variant ml-1">What your business does</label>
                  <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                    <span className="text-outline text-[20px]"><Icon name="storefront" /></span>
                    <input value={businessDescription} onChange={e => setBusinessDescription(e.target.value)} placeholder="e.g. Sells shoes and clothes" className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none" type="text" />
                  </div>
                </div>
                <div className="space-y-sm">
                  <label className="font-label-md text-label-md text-on-surface-variant ml-1">Years in Business</label>
                  <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                    <span className="text-outline text-[20px]"><Icon name="calendar_month" /></span>
                    <input value={yearsInBusiness} onChange={e => setYearsInBusiness(e.target.value.replace(/[^0-9]/g, ''))} placeholder="e.g. 3" inputMode="numeric" className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none" type="text" />
                  </div>
                </div>
                <p className="md:col-span-2 text-[12px] text-on-surface-variant">Tap "Save Changes" in Business Settings below to save your profile.</p>
              </div>
            )}
          </div>
          <button
            onClick={() => setEditingProfile(v => !v)}
            className="md:hidden w-full h-12 flex items-center justify-center border border-primary text-primary rounded-xl font-bold hover:bg-primary/5 transition-all active:scale-95 duration-200"
          >
            {editingProfile ? 'Close' : 'Edit Profile'}
          </button>
        </section>

        {/* Bento grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">

          {/* Account */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="person" /> Account</h4>
            <div className="flex flex-col">
              <ComingSoonRow icon="chevron_right" label="Profile Details" onClick={() => comingSoon('Profile Details')} />
              <ComingSoonRow icon="add_circle" label="Add Another Account" onClick={() => comingSoon('Add Another Account')} />
              <ComingSoonRow icon="swap_horiz" label="Switch Business" onClick={() => comingSoon('Switch Business')} />
            </div>
          </div>

          {/* Invoices & Receipts */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="receipt_long" /> Invoices &amp; Receipts</h4>
            <div className="flex flex-col">
              <button onClick={() => navigate('/invoices')} className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
                <span className="font-label-md text-label-md text-on-surface-variant">View Invoices &amp; Receipts</span>
                <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name="chevron_right" /></span>
              </button>
            </div>
          </div>

          {/* Team & Access */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="group" /> Team &amp; Access</h4>
            <div className="flex flex-col">
              <button onClick={openAddWorker} className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
                <span className="font-label-md text-label-md text-on-surface-variant">Add Worker</span>
                <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name="person_add" /></span>
              </button>
              <button onClick={openManageAccess} className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg group">
                <span className="font-label-md text-label-md text-on-surface-variant">Manage Access</span>
                <span className="text-outline group-hover:translate-x-1 transition-transform text-[20px]"><Icon name="lock_person" /></span>
              </button>
              <ComingSoonRow icon="storefront" label="Shop Assistant Access" onClick={() => comingSoon('Shop Assistant Access')} />
            </div>
          </div>

          {/* Business Settings — read-only labels until "Edit Profile" is tapped above */}
          <div className="md:col-span-2 bg-surface p-lg rounded-xl border border-outline-variant space-y-lg">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="business" /> Business Settings</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
              <div className="space-y-sm">
                <label className="font-label-md text-label-md text-on-surface-variant ml-1">Business Name</label>
                {editingProfile ? (
                  <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                    <span className="text-outline text-[20px]"><Icon name="corporate_fare" /></span>
                    <input value={businessName} onChange={e => setBusinessName(e.target.value)} placeholder="Enter your business name" className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none" type="text" />
                  </div>
                ) : (
                  <div className="h-[52px] flex items-center px-md gap-sm">
                    <span className="text-outline text-[20px]"><Icon name="corporate_fare" /></span>
                    <span className="font-body-md text-body-md text-on-surface">{businessName || 'Not set'}</span>
                  </div>
                )}
              </div>
              <div className="space-y-sm">
                <label className="font-label-md text-label-md text-on-surface-variant ml-1">Currency</label>
                {editingProfile ? (
                  <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                    <span className="text-outline text-[20px]"><Icon name="payments" /></span>
                    <select value={currency} onChange={e => setCurrency(e.target.value)} className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none">
                      {AFRICA_CURRENCIES.map(c => <option key={c.code} value={c.code}>{c.label}</option>)}
                    </select>
                  </div>
                ) : (
                  <div className="h-[52px] flex items-center px-md gap-sm">
                    <span className="text-outline text-[20px]"><Icon name="payments" /></span>
                    <span className="font-body-md text-body-md text-on-surface">{AFRICA_CURRENCIES.find(c => c.code === currency)?.label || currency}</span>
                  </div>
                )}
              </div>
              <div className="space-y-sm">
                <label className="font-label-md text-label-md text-on-surface-variant ml-1">Business Type</label>
                {editingProfile ? (
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
                ) : (
                  <div className="h-[52px] flex items-center px-md gap-sm">
                    <span className="text-outline text-[20px]"><Icon name="category" /></span>
                    <span className="font-body-md text-body-md text-on-surface">{businessType || 'Not set'}</span>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-lg p-md bg-surface-container-lowest border border-dashed border-outline-variant rounded-lg">
                <div className="w-16 h-16 bg-surface-container rounded-lg flex items-center justify-center text-outline text-[24px] overflow-hidden shrink-0">
                  {logoUrl ? (
                    <img src={logoSrc(logoUrl)} alt="Business logo" className="w-full h-full object-cover" />
                  ) : (
                    <Icon name="image" />
                  )}
                </div>
                <div className="flex-grow">
                  <h5 className="font-label-md text-label-md text-on-surface font-bold">Business Logo</h5>
                  <p className="text-[12px] text-on-surface-variant italic">used on invoices &amp; receipts</p>
                  {editingProfile && (
                    <button onClick={() => fileInputRef.current?.click()} disabled={logoUploading} className="text-primary font-bold text-[14px] mt-1 hover:underline disabled:opacity-50">
                      {logoUploading ? 'Uploading...' : 'Change Logo'}
                    </button>
                  )}
                </div>
              </div>
            </div>
            {editingProfile && (
              <div className="flex items-center gap-md">
                <button onClick={save} disabled={saving} className="h-12 px-xl flex items-center justify-center bg-primary text-white rounded-xl font-bold hover:opacity-90 transition-all active:scale-95 duration-200 disabled:opacity-50">
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
                {saved && <span className="flex items-center gap-1 text-green-600 font-label-md"><span className="text-[18px]"><Icon name="check_circle" /></span> Saved</span>}
              </div>
            )}
          </div>

          {/* App Settings */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="tune" /> App Settings</h4>
            <div className="flex flex-col gap-sm">
              <div className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg">
                <div className="flex flex-col">
                  <span className="font-label-md text-label-md text-on-surface">Notifications</span>
                  <span className="text-[12px] text-on-surface-variant">Turn in-app alerts on or off</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input checked={notificationsEnabled} onChange={handleNotifToggle} className="sr-only peer" type="checkbox" />
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
              <ComingSoonRow icon="pin" label="Change PIN" onClick={() => comingSoon('Change PIN')} />
              <div className="flex items-center justify-between p-md rounded-lg opacity-60">
                <span className="flex items-center gap-2">
                  <span className="font-label-md text-label-md text-on-surface-variant">Biometric Login</span>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-surface-container-highest text-on-surface-variant">Soon</span>
                </span>
                <label className="relative inline-flex items-center cursor-not-allowed" onClick={() => comingSoon('Biometric Login')}>
                  <input disabled className="sr-only peer" type="checkbox" />
                  <div className="w-11 h-6 bg-surface-container-highest rounded-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Support */}
          <div className="md:col-span-2 bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2 text-[24px]"><Icon name="support_agent" /> Support</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-md">
              {[
                { key: 'help' as const, i: 'help', t: 'Help Center', s: 'Tutorials & FAQs' },
                { key: 'contact' as const, i: 'mail', t: 'Contact Support', s: 'Get in touch' },
                { key: 'about' as const, i: 'info', t: 'About Ozzy', s: 'Version 1.0' },
              ].map(b => (
                <button key={b.t} onClick={() => setSupportModal(b.key)} className="flex flex-col items-center justify-center p-lg bg-surface-container-low hover:bg-surface-container-high rounded-xl border border-outline-variant transition-all hover:shadow-sm">
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

      {/* Support modal */}
      {supportModal && (
        <div className="fixed inset-0 z-30 bg-black/40 flex items-end sm:items-center justify-center" onClick={() => setSupportModal(null)}>
          <div className="bg-surface rounded-t-2xl sm:rounded-2xl p-xl w-full sm:max-w-[28rem] max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            {supportModal === 'help' && (
              <>
                <h2 className="font-headline-md text-headline-md text-primary mb-md flex items-center gap-2"><Icon name="help" /> Help Center</h2>
                <div className="space-y-md">
                  {HELP_FAQS.map(f => (
                    <div key={f.q}>
                      <p className="font-label-md text-label-md text-on-surface font-bold">{f.q}</p>
                      <p className="font-body-md text-body-md text-on-surface-variant">{f.a}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
            {supportModal === 'contact' && (
              <>
                <h2 className="font-headline-md text-headline-md text-primary mb-md flex items-center gap-2"><Icon name="mail" /> Contact Support</h2>
                <p className="font-body-md text-body-md text-on-surface-variant">
                  A dedicated support inbox hasn't been set up yet, so there isn't a real address to give you here.
                  In the meantime, please reach out to whoever set up your Ozzy account for help — this panel will be
                  updated with a real contact option soon.
                </p>
              </>
            )}
            {supportModal === 'about' && (
              <>
                <h2 className="font-headline-md text-headline-md text-primary mb-md flex items-center gap-2"><Icon name="info" /> About Ozzy</h2>
                <p className="font-body-md text-body-md text-on-surface-variant mb-sm">
                  Ozzy for Business is an AI-powered assistant that helps African small businesses manage sales, expenses,
                  and reports as easily as chatting on WhatsApp — built for Uganda first.
                </p>
                <p className="text-[12px] text-on-surface-variant">Version 1.0</p>
              </>
            )}
            <button onClick={() => setSupportModal(null)} className="mt-lg h-12 w-full flex items-center justify-center bg-primary text-white rounded-xl font-bold hover:opacity-90 transition-all active:scale-95 duration-200">
              Close
            </button>
          </div>
        </div>
      )}

      {/* Add Worker modal */}
      {addWorkerOpen && (
        <div className="fixed inset-0 z-30 bg-black/40 flex items-end sm:items-center justify-center" onClick={() => setAddWorkerOpen(false)}>
          <div className="bg-surface rounded-t-2xl sm:rounded-2xl p-xl w-full sm:max-w-[28rem] max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h2 className="font-headline-md text-headline-md text-primary mb-md flex items-center gap-2"><Icon name="person_add" /> Add Worker</h2>
            {!generatedCode ? (
              <>
                <p className="font-body-md text-body-md text-on-surface-variant mb-lg">
                  Generate a 6-digit code for your new worker. They'll use it on the login screen to set their own
                  password and join your business. The code works once and expires in 7 days.
                </p>
                <label className="font-label-md text-label-md text-on-surface-variant ml-1">Worker's phone number (optional)</label>
                <div className="h-[52px] mt-1 mb-md bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                  <Icon name="call" className="text-outline text-[20px]" />
                  <input
                    value={workerPhoneInput}
                    onChange={e => setWorkerPhoneInput(e.target.value)}
                    placeholder="e.g. +256700123456"
                    className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none"
                    type="tel"
                  />
                </div>
                <p className="text-[12px] text-on-surface-variant mb-md">
                  Recommended: a code generated without a phone number can't be completed by the worker yet — please
                  add their number here so they can finish joining.
                </p>
                {generateError && <p className="text-red-600 text-sm mb-md">{generateError}</p>}
                <button
                  onClick={generateInviteCode}
                  disabled={generatingCode}
                  className="h-12 w-full flex items-center justify-center bg-primary text-white rounded-xl font-bold hover:opacity-90 transition-all active:scale-95 duration-200 disabled:opacity-50"
                >
                  {generatingCode ? 'Generating…' : 'Generate Code'}
                </button>
              </>
            ) : (
              <>
                <p className="font-body-md text-body-md text-on-surface-variant mb-md">
                  Share this code with your new worker — read it out or send it to them. It's valid for 7 days and works once.
                </p>
                <div className="flex items-center justify-center gap-md p-lg bg-surface-container-low rounded-xl mb-sm">
                  <span className="font-headline-lg text-headline-lg text-primary tracking-[0.3em]">{generatedCode}</span>
                  <button onClick={copyInviteCode} className="p-2 text-primary hover:bg-primary/10 rounded-lg transition-colors" aria-label="Copy code">
                    <Icon name="content_copy" />
                  </button>
                </div>
                <p className="text-[12px] text-on-surface-variant text-center mb-lg">Valid for 7 days · one-time use</p>
              </>
            )}
            <button onClick={() => setAddWorkerOpen(false)} className="mt-lg h-12 w-full flex items-center justify-center border border-outline-variant text-on-surface rounded-xl font-bold hover:bg-surface-container-low transition-all active:scale-95 duration-200">
              Close
            </button>
          </div>
        </div>
      )}

      {/* Manage Access modal */}
      {manageAccessOpen && (
        <div className="fixed inset-0 z-30 bg-black/40 flex items-end sm:items-center justify-center" onClick={() => setManageAccessOpen(false)}>
          <div className="bg-surface rounded-t-2xl sm:rounded-2xl p-xl w-full sm:max-w-[28rem] max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h2 className="font-headline-md text-headline-md text-primary mb-md flex items-center gap-2"><Icon name="lock_person" /> Manage Access</h2>
            {workersLoading ? (
              <p className="text-on-surface-variant text-center py-lg">Loading your workers…</p>
            ) : workersError ? (
              <p className="text-red-600 text-center py-lg">{workersError}</p>
            ) : workersList.length === 0 ? (
              <p className="text-on-surface-variant text-center py-lg">You haven't added any workers yet. Use "Add Worker" to invite one.</p>
            ) : (
              <div className="space-y-sm">
                {workersList.map(w => (
                  <div key={w.id} className="flex items-center gap-md p-md bg-surface-container-low rounded-lg">
                    <div className="w-10 h-10 rounded-full bg-primary-container/30 flex items-center justify-center text-primary shrink-0">
                      <Icon name="person" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-bold text-on-surface truncate">{w.phone_number || 'No phone number on file'}</p>
                      <p className="text-[12px] text-on-surface-variant">
                        Joined {w.created_at ? new Date(w.created_at).toLocaleDateString() : '—'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <button onClick={() => setManageAccessOpen(false)} className="mt-lg h-12 w-full flex items-center justify-center bg-primary text-white rounded-xl font-bold hover:opacity-90 transition-all active:scale-95 duration-200">
              Close
            </button>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-24 md:bottom-8 left-1/2 -translate-x-1/2 bg-on-surface text-surface px-lg py-sm rounded-full shadow-lg text-[14px] font-label-md z-50 whitespace-nowrap">
          {toast}
        </div>
      )}
    </main>
  );
}
