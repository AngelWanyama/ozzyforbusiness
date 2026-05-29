import { useState, useEffect } from 'react';
import { Plus, AlertTriangle } from 'lucide-react';
import api from '../api/client';

export default function Inventory() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);
  const [form, setForm] = useState({ name: '', category: '', unit_price: '', stock_level: '', is_service: false });

  const load = async () => {
    try { const d = await api.getInventory(); setItems(d || []); } catch {}
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data = {
        name: form.name,
        category: form.category || undefined,
        unit_price: parseFloat(form.unit_price) || 0,
        stock_level: form.is_service ? 0 : (parseFloat(form.stock_level) || 0),
        is_service: form.is_service,
      };
      if (editItem) await api.updateItem(editItem.id, data);
      else await api.createItem(data);
      setShowModal(false); setEditItem(null);
      setForm({ name: '', category: '', unit_price: '', stock_level: '', is_service: false });
      load();
    } catch {}
  };

  const openAdd = () => {
    setEditItem(null);
    setForm({ name: '', category: '', unit_price: '', stock_level: '', is_service: false });
    setShowModal(true);
  };

  const openEdit = (item: any) => {
    setEditItem(item);
    setForm({ name: item.name, category: item.category || '', unit_price: String(item.unit_price), stock_level: String(item.stock_level), is_service: item.is_service });
    setShowModal(true);
  };

  const handleAdjust = async (id: string) => {
    const amt = prompt('Adjustment amount (positive to add, negative to remove):');
    if (!amt) return;
    try { await api.adjustStock(id, parseFloat(amt)); load(); } catch {}
  };

  const fmt = (n: number) => 'UGX ' + Number(n).toLocaleString();
  const lowStock = items.filter(i => !i.is_service && i.stock_level < 5);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Inventory</h1>
        <button onClick={openAdd} className="flex items-center gap-1.5 px-4 py-2 bg-[#0D9488] text-white rounded-xl text-sm font-medium hover:bg-[#0B7A70] transition">
          <Plus size={16} /> Add Item
        </button>
      </div>

      {lowStock.length > 0 && (
        <div className="flex items-center gap-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-xl p-4 mb-4">
          <AlertTriangle size={20} className="text-orange-500 shrink-0" />
          <p className="text-sm font-medium text-orange-800 dark:text-orange-300">{lowStock.length} item{lowStock.length > 1 ? 's' : ''} low on stock</p>
        </div>
      )}

      {loading ? <div className="text-center py-12"><div className="animate-spin w-8 h-8 border-4 border-[#0D9488] border-t-transparent rounded-full mx-auto" /></div>
      : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400 dark:text-gray-500">
          <div className="text-4xl mb-2">📦</div>
          <p className="text-sm mb-4">No inventory items</p>
          <button onClick={openAdd} className="px-4 py-2 bg-[#0D9488] text-white rounded-xl text-sm font-medium">Add Item</button>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item: any) => (
            <div key={item.id} className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-100 dark:border-gray-700 flex items-center justify-between hover:shadow-sm transition">
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white">{item.name}</h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  {item.is_service ? 'Service' : `Stock: ${item.stock_level}`}
                  {item.category && ` \u00b7 ${item.category}`}
                </p>
              </div>
              <div className="text-right">
                <p className="font-semibold text-[#0D9488]">{fmt(item.unit_price)}</p>
                <div className="flex gap-1 mt-1">
                  <button onClick={() => openEdit(item)} className="text-xs px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition">Edit</button>
                  {!item.is_service && (
                    <button onClick={() => handleAdjust(item.id)} className="text-xs px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition">Stock</button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 z-30 bg-black/40 flex items-end sm:items-center justify-center" onClick={() => setShowModal(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl rounded-b-none sm:rounded-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h2 className="font-bold text-lg text-gray-900 dark:text-white mb-4">{editItem ? 'Edit Item' : 'Add Item'}</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name</label>
                <input type="text" className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#0D9488] outline-none" required value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Category</label>
                <input type="text" className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#0D9488] outline-none" placeholder="e.g., Clothing" value={form.category} onChange={e => setForm({...form, category: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Unit Price</label>
                  <input type="number" className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#0D9488] outline-none" required min="0" value={form.unit_price} onChange={e => setForm({...form, unit_price: e.target.value})} />
                </div>
                {!form.is_service && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Stock Level</label>
                    <input type="number" className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-[#0D9488] outline-none" min="0" value={form.stock_level} onChange={e => setForm({...form, stock_level: e.target.value})} />
                  </div>
                )}
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <input type="checkbox" checked={form.is_service} onChange={e => setForm({...form, is_service: e.target.checked})} className="rounded" />
                This is a service (no stock tracking)
              </label>
              <button type="submit" className="w-full py-3 bg-[#0D9488] text-white font-semibold rounded-xl hover:bg-[#0B7A70] transition">
                {editItem ? 'Update Item' : 'Add Item'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}