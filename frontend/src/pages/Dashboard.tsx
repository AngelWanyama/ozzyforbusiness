import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, DollarSign, AlertTriangle, Plus, Package } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const { plan } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<any>(null);
  const [recentTxns, setRecentTxns] = useState<any[]>([]);
  const [inventory, setInventory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getReportSummary().catch(() => null),
      api.getTransactions(0, 5).catch(() => ({ items: [] })),
      api.getInventory().catch(() => []),
    ]).then(([s, t, i]) => {
      setSummary(s); setRecentTxns(t.items || []); setInventory(i || []);
    }).finally(() => setLoading(false));
  }, []);

  const fmt = (n: number | string) => {
    const num = Number(n || 0);
    return (summary?.currency || 'UGX') + ' ' + num.toLocaleString();
  };

  const lowStock = inventory.filter(i => !i.is_service && i.stock_level < 5);

  if (loading) return <div className="flex items-center justify-center py-20"><div className="animate-spin w-8 h-8 border-4 border-[#0D9488] border-t-transparent rounded-full" /></div>;

  return (
    <div>
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Sales</span>
            <div className="w-10 h-10 rounded-xl bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
              <TrendingUp size={20} className="text-green-600" />
            </div>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{summary ? fmt(summary.total_sales) : '—'}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Expenses</span>
            <div className="w-10 h-10 rounded-xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <TrendingDown size={20} className="text-red-600" />
            </div>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{summary ? fmt(summary.total_expenses) : '—'}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Profit</span>
            <div className="w-10 h-10 rounded-xl bg-[#0D9488]/10 dark:bg-[#0D9488]/20 flex items-center justify-center">
              <DollarSign size={20} className="text-[#0D9488]" />
            </div>
          </div>
          <p className="text-2xl font-bold" style={{ color: summary && Number(summary.net_profit) >= 0 ? '#10B981' : '#EF4444' }}>
            {summary ? fmt(summary.net_profit) : '—'}
          </p>
        </div>
      </div>

      {/* Low Stock Alert */}
      {lowStock.length > 0 && (
        <div className="flex items-center gap-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-xl p-4 mb-6">
          <AlertTriangle size={20} className="text-orange-500 shrink-0" />
          <p className="text-sm font-medium text-orange-800 dark:text-orange-300">
            {lowStock.length} item{lowStock.length > 1 ? 's' : ''} low on stock
          </p>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <button onClick={() => navigate('/transactions')} className="flex flex-col items-center gap-2 bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition">
          <div className="w-12 h-12 rounded-xl bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
            <Plus size={22} className="text-green-600" />
          </div>
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Record Sale</span>
        </button>
        <button onClick={() => navigate('/transactions')} className="flex flex-col items-center gap-2 bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition">
          <div className="w-12 h-12 rounded-xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
            <TrendingDown size={22} className="text-red-600" />
          </div>
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Record Expense</span>
        </button>
        <button onClick={() => navigate('/inventory')} className="flex flex-col items-center gap-2 bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition">
          <div className="w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <Package size={22} className="text-blue-600" />
          </div>
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Check Stock</span>
        </button>
      </div>

      {/* Recent Transactions */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-5">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Recent Transactions</h2>
        {recentTxns.length === 0 ? (
          <div className="text-center py-8 text-gray-400 dark:text-gray-500">
            <div className="text-4xl mb-2">📝</div>
            <p className="text-sm">No transactions yet. Start recording!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recentTxns.map((txn: any) => (
              <div key={txn.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 transition">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${txn.type === 'sale' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                  {txn.type === 'sale' ? '↑' : '↓'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-gray-900 dark:text-white truncate">{txn.description || (txn.type === 'sale' ? 'Sale' : 'Expense')}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">{new Date(txn.transaction_date).toLocaleDateString()}</p>
                </div>
                <p className={`font-semibold text-sm ${txn.type === 'sale' ? 'text-green-600' : 'text-red-600'}`}>
                  {fmt(txn.amount)}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Free Plan Upgrade CTA */}
      {plan?.plan_type === 'FREE' && (
        <div className="mt-6 bg-gradient-to-r from-[#0D9488] to-[#0B7A70] rounded-2xl p-5 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">Free Plan</h3>
              <p className="text-sm text-white/80 mt-1">Upgrade for unlimited transactions, reports & more</p>
            </div>
            <button onClick={() => navigate('/settings')} className="px-4 py-2 bg-white text-[#0D9488] font-semibold rounded-xl text-sm hover:bg-gray-100 transition">
              Upgrade
            </button>
          </div>
        </div>
      )}
    </div>
  );
}