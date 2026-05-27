import { useState, useEffect } from 'react';
import { Search, Filter, Plus, Edit3, Trash2, X } from 'lucide-react';
import api from '../api/client';

export default function Transactions() {
  const [txns, setTxns] = useState<any[]>([]);
  const [filter, setFilter] = useState<'all' | 'sale' | 'expense'>('all');
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editTxn, setEditTxn] = useState<any>(null);
  const [form, setForm] = useState({ type: 'sale', amount: '', description: '', quantity: '1' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try { const d = await api.getTransactions(0, 500); setTxns(d.items || []); } catch {}
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const filtered = txns
    .filter(t => filter === 'all' || t.type === filter)
    .filter(t => !search || (t.description || '').toLowerCase().includes(search.toLowerCase()));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const data = { type: form.type, amount: parseFloat(form.amount), description: form.description || undefined, quantity: parseInt(form.quantity) || 1 };
      if (editTxn) await api.updateTransaction(editTxn.id, data);
      else await api.createTransaction(data);
      setShowModal(false); setEditTxn(null); setForm({ type: 'sale', amount: '', description: '', quantity: '1' });
      load();
    } catch (err: any) { setError(err.message); }
  };

  const handleEdit = (txn: any) => {
    setForm({ type: txn.type, amount: String(txn.amount), description: txn.description || '', quantity: String(txn.quantity) });
    setEditTxn(txn); setShowModal(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this transaction?')) return;
    try { await api.deleteTransaction(id); load(); } catch {}
  };

  const openAdd = () => { setEditTxn(null); setForm({ type: 'sale', amount: '', description: '', quantity: '1' }); setShowModal(true); };

  const fmt = (n: number) => 'UGX ' + Number(n).toLocaleString();

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Transactions</h1>
        <button onClick={openAdd} className="flex items-center gap-1.5 px-4 py-2 bg-[#0D9488] text-white rounded-xl text-sm font-medium hover:bg-[#0B7A70] transition">
          <Plus size={16} /> Add
        </button>
      </div>

      {/* Search & Filter */}
      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" className="w-full pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white text-sm focus:ring-2 focus:ring-[#0D9488] outline-none" placeholder="Search..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="flex gap-1">
          {(['all', 'sale', 'expense'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)} className={`px-3 py-2 rounded-xl text-sm font-medium transition ${filter === f ? 'bg-[#0D9488] text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
              {f === 'all' ? 'All' : f === 'sale' ? 'Sales' : 'Expenses'}
            </button>
          ))}
        </div>
      </div>

      {loading ? <div className="text-center py-12"><div className="animate-spin w-8 h-8 border-4 border-[#0D9488] border-t-transparent rounded-full mx-auto" /></div>
      : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-400 dark:text-gray-500">
          <div className="text-4xl mb-2">📭</div>
          <p className="text-sm">No transactions found</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {filtered.map((txn: any) => (
              <div key={txn.id} className="flex items-center gap-3 p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${txn.type === 'sale' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                  {txn.type === 'sale' ? '↑' : '↓'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-gray-900 dark:text-white truncate">{txn.description || (txn.type === 'sale' ? 'Sale' : 'Expense')}</p>
                  <p className="text-xs text-gray-400">{new Date(txn.transaction_date).toLocaleString()} {txn.quantity > 1 && `· Qty: ${txn.quantity}`}</p>
                </div>
                <div className="flex items-center gap-2">
                  <p className={`font-semibold text-sm ${txn.type === 'sale' ? 'text-green-600' : 'text-red-600'}`}>{fmt(txn.amount)}</p>
                  <button onClick={() => handleEdit(txn)} className="p-2 text-gray-400 hover:text-[#0D9488] transition"><Edit3 size={14} /></button>
                  <button onClick={() => handleDelete(txn.id)} className="p-2 text-gray-400 hover:text-red-500 transition"><Trash2 size={14} /></button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-30 bg-black/40 flex items-end sm:items-center justify-center" onClick={() => setShowModal(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl rounded-b-none sm:rounded-2xl p-6 w-full max-w-md max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-lg text-gray-900 dark:text-white">{editTxn ? 'Edit Transaction' : 'Add Transaction'}</h2>
              <button onClick={() => setShowModal(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl"><X size={18} /></button>
            </div>
            {error && <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 p-3 rounded-xl text-sm mb-4">{error}</div>}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Type</label>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setForm({...form, type: 'sale'})} className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition ${form.type === 'sale' ? 'bg-green-100 text-green-700 border border-green-200' : 'bg-gray-100 dark:bg-gray-700 text-gray-500'}`}>💰 Sale</button>
                  <button type="button" onClick={() => setForm({...form, type: 'expense'})} className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition ${form.type === 'expense' ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-gray-100 dark:bg-gray-700 text-gray-500'}`}>💸 Expense</button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                <input type="text" className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#0D9488] outline-none" placeholder="e.g., Sold dress" required value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Amount</label>
                  <input type="number" className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#0D9488] outline-none" placeholder="20000" required min="1" value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Qty</label>
                  <input type="number" className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#0D9488] outline-none" placeholder="1" min="1" value={form.quantity} onChange={e => setForm({...form, quantity: e.target.value})} />
                </div>
              </div>
              <button type="submit" className="w-full py-3 bg-[#0D9488] text-white font-semibold rounded-xl hover:bg-[#0B7A70] transition">
                {editTxn ? 'Update Transaction' : 'Add Transaction'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}