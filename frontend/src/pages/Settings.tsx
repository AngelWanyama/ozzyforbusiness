import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

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

export default function Settings() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [dark, setDark] = useState(() => localStorage.getItem('ozzy_dark') === '1');
  const [notif, setNotif] = useState(true);
  const [bio, setBio] = useState(true);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('ozzy_dark', dark ? '1' : '0');
  }, [dark]);

  const handleLogout = () => { logout(); navigate('/login'); };

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
              <h3 className="font-headline-md text-headline-md text-on-surface">Innovate Africa Ltd.</h3>
              <p className="font-body-md text-body-md text-on-surface-variant">+256 700 000 000</p>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-bold bg-secondary-container text-on-secondary-container mt-xs uppercase tracking-wider">Business Admin</span>
            </div>
            <button className="hidden md:flex h-12 px-lg items-center justify-center border border-primary text-primary rounded-xl font-bold hover:bg-primary/5 transition-all active:scale-95 duration-200">Edit Profile</button>
          </div>
          <button className="md:hidden w-full h-12 flex items-center justify-center border border-primary text-primary rounded-xl font-bold hover:bg-primary/5 transition-all active:scale-95 duration-200">Edit Profile</button>
        </section>

        {/* Grouped sections */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
          {/* Account */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2"><Icon name="person" /> Account</h4>
            <div className="flex flex-col">
              <Row label="Profile Details" icon="chevron_right" />
              <Row label="Add Another Account" icon="add_circle" />
              <Row label="Switch Business" icon="swap_horiz" />
            </div>
          </div>

          {/* Team & Access */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2"><Icon name="group" /> Team &amp; Access</h4>
            <div className="flex flex-col">
              <Row label="Add Worker" icon="person_add" />
              <Row label="Manage Access" icon="lock_person" />
              <Row label="Shop Assistant Access" icon="storefront" />
            </div>
          </div>

          {/* Business Settings */}
          <div className="md:col-span-2 bg-surface p-lg rounded-xl border border-outline-variant space-y-lg">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2"><Icon name="business" /> Business Settings</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
              <div className="space-y-sm">
                <label className="font-label-md text-label-md text-on-surface-variant ml-1">Business Name</label>
                <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm focus-within:border-primary transition-colors">
                  <Icon name="corporate_fare" className="text-outline" />
                  <input className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none" type="text" defaultValue="Innovate Africa Ltd." />
                </div>
              </div>
              <div className="space-y-sm">
                <label className="font-label-md text-label-md text-on-surface-variant ml-1">Currency</label>
                <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm">
                  <Icon name="payments" className="text-outline" />
                  <input className="bg-transparent border-none focus:ring-0 w-full font-body-md text-on-surface-variant cursor-not-allowed outline-none" disabled type="text" defaultValue="UGX (Ugandan Shilling)" />
                </div>
              </div>
              <div className="space-y-sm">
                <label className="font-label-md text-label-md text-on-surface-variant ml-1">Business Type</label>
                <div className="h-[52px] bg-surface-container-low border border-outline-variant rounded-lg flex items-center px-md gap-sm">
                  <Icon name="category" className="text-outline" />
                  <select className="bg-transparent border-none focus:ring-0 w-full font-body-md outline-none">
                    <option>Technology &amp; Software</option>
                    <option>Retail &amp; Distribution</option>
                    <option>Logistics</option>
                    <option>Agriculture</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-lg p-md bg-surface-container-lowest border border-dashed border-outline-variant rounded-lg">
                <div className="w-16 h-16 bg-surface-container rounded-lg flex items-center justify-center"><Icon name="image" className="text-outline" /></div>
                <div className="flex-grow">
                  <h5 className="font-label-md text-label-md text-on-surface font-bold">Business Logo</h5>
                  <p className="text-[12px] text-on-surface-variant italic">used on invoices &amp; receipts</p>
                  <button className="text-primary font-bold text-[14px] mt-1 hover:underline">Change Logo</button>
                </div>
              </div>
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

          {/* Security */}
          <div className="bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
            <h4 className="font-headline-md text-headline-md text-primary flex items-center gap-2"><Icon name="shield" /> Security</h4>
            <div className="flex flex-col">
              <Row label="Change PIN" icon="pin" />
              <div className="flex items-center justify-between p-md hover:bg-surface-container-low transition-colors rounded-lg">
                <span className="font-label-md text-label-md text-on-surface-variant">Biometric Login</span>
                <Toggle checked={bio} onChange={() => setBio(v => !v)} />
              </div>
            </div>
          </div>

          {/* Support */}
          <div className="md:col-span-2 bg-surface p-lg rounded-xl border border-outline-variant space-y-md">
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
