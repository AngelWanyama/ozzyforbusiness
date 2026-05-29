import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { LogOut, Globe, Bell, HelpCircle, CreditCard } from 'lucide-react';

export default function Settings() {
  const { plan, usage, logout } = useAuth();
  const navigate = useNavigate();

  const isPaid = plan?.plan_type === 'PAID';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Settings</h1>

      {/* Plan Card */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm mb-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="font-semibold text-gray-900 dark:text-white">{isPaid ? 'Pro Plan' : 'Free Plan'}</h2>
            <p className="text-sm text-gray-400 mt-0.5">
              {isPaid ? `Expires: ${plan?.payment_expiry_date ? new Date(plan.payment_expiry_date).toLocaleDateString() : 'N/A'}` : '100 transactions/month limit'}
            </p>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${isPaid ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
            {isPaid ? 'ACTIVE' : 'FREE'}
          </span>
        </div>
        {usage && (
          <p className="text-xs text-gray-400 mb-3">
            {isPaid ? 'Unlimited transactions' : `Used ${usage.transactions_this_month || 0} of ${usage.limit || 100} transactions`}
          </p>
        )}
        {!isPaid && (
          <button className="w-full py-2.5 bg-[#F97316] text-white font-semibold rounded-xl text-sm hover:bg-[#E8630A] transition flex items-center justify-center gap-2">
            <CreditCard size={16} /> Upgrade to Pro
          </button>
        )}
      </div>

      {/* Business Section */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm mb-4 overflow-hidden">
        <div className="px-5 pt-4 pb-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Business</p>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-gray-700">
          <SettingRow icon={<Globe size={18} />} title="Currency" subtitle="UGX - Ugandan Shilling" />
          <SettingRow icon={<Globe size={18} />} title="Business Name" subtitle="Not set" />
          <SettingRow icon={<Globe size={18} />} title="Business Type" subtitle="Not set" />
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm mb-4 overflow-hidden">
        <div className="px-5 pt-4 pb-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Notifications</p>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-gray-700">
          <SettingRow icon={<Bell size={18} />} title="Daily Summary" subtitle="Get a text of your day's business" />
          <SettingRow icon={<Bell size={18} />} title="Low Stock Alerts" subtitle="Get notified when items run low" />
        </div>
      </div>

      {/* Support */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm mb-6 overflow-hidden">
        <div className="px-5 pt-4 pb-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Support</p>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-gray-700">
          <SettingRow icon={<HelpCircle size={18} />} title="Help Center" subtitle="Guides and FAQs" />
          <SettingRow icon={<HelpCircle size={18} />} title="Contact Us" subtitle="support@ozzyforbusiness.com" />
        </div>
      </div>

      {/* Logout */}
      <button onClick={handleLogout} className="w-full py-3 bg-red-500 text-white font-semibold rounded-xl hover:bg-red-600 transition flex items-center justify-center gap-2">
        <LogOut size={18} /> Log Out
      </button>

      <p className="text-center text-xs text-gray-400 mt-6 pb-4">Ozzy for Business v1.0.0</p>
    </div>
  );
}

function SettingRow({ icon, title, subtitle }: { icon: React.ReactNode; title: string; subtitle: string }) {
  return (
    <div className="flex items-center gap-3 px-5 py-3.5">
      <div className="w-9 h-9 rounded-xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-500">{icon}</div>
      <div>
        <p className="text-sm font-medium text-gray-900 dark:text-white">{title}</p>
        <p className="text-xs text-gray-400">{subtitle}</p>
      </div>
    </div>
  );
}