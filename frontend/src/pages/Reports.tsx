import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { Lock } from 'lucide-react';

const COLORS = ['#10B981', '#EF4444', '#0D9488', '#F97316', '#6366F1', '#8B5CF6'];

// Sample data for chart preview
const sampleSalesData = [
  { day: 'Mon', sales: 85000, expenses: 32000 },
  { day: 'Tue', sales: 92000, expenses: 28000 },
  { day: 'Wed', sales: 78000, expenses: 35000 },
  { day: 'Thu', sales: 105000, expenses: 30000 },
  { day: 'Fri', sales: 95000, expenses: 25000 },
  { day: 'Sat', sales: 120000, expenses: 40000 },
  { day: 'Sun', sales: 65000, expenses: 22000 },
];

const sampleExpenseBreakdown = [
  { name: 'Rent', value: 150000 },
  { name: 'Supplies', value: 85000 },
  { name: 'Utilities', value: 45000 },
  { name: 'Transport', value: 35000 },
  { name: 'Other', value: 25000 },
];

const sampleProfitTrend = [
  { month: 'Jan', profit: 52000 },
  { month: 'Feb', profit: 48000 },
  { month: 'Mar', profit: 61000 },
  { month: 'Apr', profit: 55000 },
  { month: 'May', profit: 73000 },
  { month: 'Jun', profit: 68000 },
];

export default function Reports() {
  const { plan } = useAuth();
  const [tab, setTab] = useState('sales');
  const isPaid = plan?.plan_type === 'PAID';

  const fmt = (n: number) => 'UGX ' + Number(n).toLocaleString();

  if (!isPaid) {
    return (
      <div className="text-center py-16">
        <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Lock size={28} className="text-gray-400" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Premium Feature</h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm mb-4 max-w-sm mx-auto">
          Detailed analytics and chart reports are available on the Pro plan.
        </p>
        <a href="#/settings" className="inline-block px-6 py-2.5 bg-[#F97316] text-white font-semibold rounded-xl hover:bg-[#E8630A] transition">
          Upgrade Now
        </a>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Reports & Analytics</h1>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl">
        {['sales', 'expenses', 'profit', 'products'].map(t => (
          <button key={t} onClick={() => setTab(t)} className={`flex-1 py-2 text-sm font-medium rounded-lg transition ${tab === t ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
            {t === 'sales' ? 'Sales' : t === 'expenses' ? 'Expenses' : t === 'profit' ? 'Profit' : 'Products'}
          </button>
        ))}
      </div>

      {tab === 'sales' && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Weekly Sales vs Expenses</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sampleSalesData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="day" tick={{ fontSize: 12 }} stroke="#94A3B8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94A3B8" tickFormatter={(v) => (v/1000) + 'k'} />
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Bar dataKey="sales" name="Sales" fill="#10B981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="expenses" name="Expenses" fill="#EF4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {tab === 'expenses' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm">
            <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Expense Breakdown</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={sampleExpenseBreakdown} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {sampleExpenseBreakdown.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmt(v)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="space-y-2">
            {sampleExpenseBreakdown.map((item, i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-3 border border-gray-100 dark:border-gray-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[i] }} />
                  <span className="text-sm text-gray-600 dark:text-gray-400">{item.name}</span>
                </div>
                <span className="text-sm font-medium text-gray-900 dark:text-white">{fmt(item.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'profit' && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Profit Trend (6 Months)</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sampleProfitTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="#94A3B8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94A3B8" tickFormatter={(v) => (v/1000) + 'k'} />
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Line type="monotone" dataKey="profit" stroke="#0D9488" strokeWidth={3} dot={{ fill: '#0D9488' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {tab === 'products' && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Best Selling Products</h2>
          <div className="space-y-3">
            {[
              { name: 'Dress', sales: 45, revenue: 900000 },
              { name: 'Shirt', sales: 32, revenue: 480000 },
              { name: 'Shoes', sales: 28, revenue: 560000 },
              { name: 'Skirt', sales: 18, revenue: 270000 },
              { name: 'Accessory', sales: 15, revenue: 75000 },
            ].map((p, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
                <div className="w-8 h-8 rounded-xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-sm font-bold text-gray-500">{i + 1}</div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{p.name}</p>
                  <p className="text-xs text-gray-400">{p.sales} units sold</p>
                </div>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">{fmt(p.revenue)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}