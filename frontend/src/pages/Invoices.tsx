import { useState, useEffect } from 'react';
import { FileText, Plus, Search, Eye, Copy, Trash2, X, Download, Printer, Share2, Mail, Save, ChevronRight, Check, Loader } from 'lucide-react';
import api from '../api/client';

// ─── Types ───────────────────────────────────────────────────────────────────
type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue';
type Step = 'list' | 'create' | 'preview';

interface InvoiceItem {
  id: string;
  description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

interface Invoice {
  id: string;
  user_id: string;
  invoice_number: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  customer_address: string;
  status: InvoiceStatus;
  template: string;
  total_amount: number;
  currency: string;
  notes: string;
  due_date: string;
  created_at: string;
  updated_at: string;
  items: InvoiceItem[];
}

const TEMPLATES = [
  { id: 'professional', name: 'Professional', color: 'from-[#0D9488] to-[#0B7A70]', desc: 'Clean teal header, modern layout' },
  { id: 'modern', name: 'Modern', color: 'from-[#1E293B] to-[#334155]', desc: 'Dark header, contemporary style' },
  { id: 'simple', name: 'Simple', color: 'from-gray-100 to-white', desc: 'Minimal, no color accents' },
  { id: 'custom', name: 'Custom', color: 'from-[#F97316] to-[#EA580C]', desc: 'Warm orange, your brand' },
];

const fmt = (n: number | string) => {
  const num = Number(n || 0);
  return 'UGX ' + num.toLocaleString();
};

// ─── InvoiceListView (API-backed) ────────────────────────────────────────────
function InvoiceListView({ onCreate }: { onCreate: () => void }) {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'all'>('all');
  const [viewInvoice, setViewInvoice] = useState<Invoice | null>(null);

  const load = async () => {
    try {
      const data = await api.getInvoices(0, 200);
      setInvoices(data || []);
    } catch { /* backend may not be running */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const filtered = invoices.filter(inv => {
    const matchSearch = !search || inv.customer_name?.toLowerCase().includes(search.toLowerCase()) || inv.invoice_number?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'all' || inv.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const statusColor: Record<string, string> = { draft: 'bg-gray-100 text-gray-600', sent: 'bg-blue-100 text-blue-600', paid: 'bg-green-100 text-green-600', overdue: 'bg-red-100 text-red-600' };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this invoice?')) return;
    try { await api.deleteInvoice(id); load(); } catch {}
  };

  const handleDuplicate = async (inv: Invoice) => {
    // Generate a new invoice via text with the same details
    const text = `Invoice for ${inv.customer_name}, ${inv.items.map(i => `${i.quantity} ${i.description} @ ${i.unit_price}`).join(', ')}`;
    try {
      const created = await api.generateInvoiceFromText(text);
      if (created) load();
    } catch {}
  };

  const handleStatusUpdate = async (id: string, status: InvoiceStatus) => {
    try { await api.updateInvoice(id, { status }); load(); } catch {}
  };

  if (viewInvoice) {
    return <InvoicePreviewPanel invoice={viewInvoice} onBack={() => setViewInvoice(null)} onStatusUpdate={(s) => handleStatusUpdate(viewInvoice.id, s)} onDeleted={() => { handleDelete(viewInvoice.id); setViewInvoice(null); }} />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Invoices</h1>
        <button onClick={onCreate} className="flex items-center gap-1.5 px-4 py-2 bg-[#0D9488] text-white rounded-xl text-sm font-medium hover:bg-[#0B7A70] transition">
          <Plus size={16} /> New Invoice
        </button>
      </div>

      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" className="w-full pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white text-sm focus:ring-2 focus:ring-[#0D9488] outline-none" placeholder="Search invoices..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      <div className="flex gap-1 mb-4 overflow-x-auto pb-1">
        {(['all', 'draft', 'sent', 'paid', 'overdue'] as const).map(s => (
          <button key={s} onClick={() => setStatusFilter(s)} className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition ${statusFilter === s ? 'bg-[#0D9488] text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700'}`}>
            {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-16"><Loader size={24} className="animate-spin mx-auto text-gray-400" /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          <div className="text-5xl mb-3">🧾</div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">No invoices yet</p>
          <p className="text-xs mb-4">Create your first invoice to get paid faster</p>
          <button onClick={onCreate} className="px-5 py-2.5 bg-[#0D9488] text-white rounded-xl text-sm font-medium hover:bg-[#0B7A70] transition">+ Create Invoice</button>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(inv => (
            <div key={inv.id} className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-100 dark:border-gray-700 hover:shadow-sm transition cursor-pointer" onClick={() => setViewInvoice(inv)}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-gray-900 dark:text-white">{inv.invoice_number}</span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColor[inv.status]}`}>{inv.status}</span>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{inv.customer_name}</p>
                  <p className="text-xs text-gray-400">{new Date(inv.created_at).toLocaleDateString()}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-gray-900 dark:text-white">{fmt(inv.total_amount)}</p>
                  <div className="flex gap-1 mt-1 justify-end">
                    <button onClick={(e) => { e.stopPropagation(); setViewInvoice(inv); }} className="p-1 text-gray-400 hover:text-[#0D9488] transition"><Eye size={14} /></button>
                    <button onClick={(e) => { e.stopPropagation(); handleDuplicate(inv); }} className="p-1 text-gray-400 hover:text-[#0D9488] transition"><Copy size={14} /></button>
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(inv.id); }} className="p-1 text-gray-400 hover:text-red-500 transition"><Trash2 size={14} /></button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── InvoicePreviewPanel (API-backed) ────────────────────────────────────────
function InvoicePreviewPanel({ invoice, onBack, onStatusUpdate, onDeleted }: {
  invoice: Invoice; onBack: () => void; onStatusUpdate: (s: InvoiceStatus) => void; onDeleted: () => void;
}) {
  const [saving, setSaving] = useState(false);

  const handlePdf = async () => {
    try {
      const res = await api.getInvoicePdf(invoice.id);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(url), 10000);
    } catch {
      window.print();
    }
  };

  const handleWhatsApp = () => {
    const text = `Invoice ${invoice.invoice_number}\nCustomer: ${invoice.customer_name}\nTotal: ${fmt(invoice.total_amount)}\nStatus: ${invoice.status}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
  };

  const handleEmail = () => {
    window.open(`mailto:${invoice.customer_email || ''}?subject=Invoice ${invoice.invoice_number}&body=Dear ${invoice.customer_name}, please find your invoice attached. Total: ${fmt(invoice.total_amount)}`);
  };

  const handleStatusChange = async (status: InvoiceStatus) => {
    setSaving(true);
    try { await api.updateInvoice(invoice.id, { status }); onStatusUpdate(status); } catch {}
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!confirm('Delete this invoice?')) return;
    try { await api.deleteInvoice(invoice.id); onDeleted(); } catch {}
  };

  const statusColor: Record<string, string> = { draft: 'bg-gray-100 text-gray-600', sent: 'bg-blue-100 text-blue-600', paid: 'bg-green-100 text-green-600', overdue: 'bg-red-100 text-red-600' };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button onClick={onBack} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl"><X size={18} /></button>
          <h2 className="font-semibold text-gray-900 dark:text-white">Invoice {invoice.invoice_number}</h2>
        </div>
        <div className="flex items-center gap-2">
          <select value={invoice.status} onChange={(e) => handleStatusChange(e.target.value as InvoiceStatus)} disabled={saving} className="text-xs px-2 py-1.5 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300">
            <option value="draft">Draft</option>
            <option value="sent">Sent</option>
            <option value="paid">Paid</option>
            <option value="overdue">Overdue</option>
          </select>
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColor[invoice.status]}`}>{invoice.status}</span>
        </div>
      </div>

      {/* Invoice Render */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 overflow-hidden shadow-sm">
        <div className="bg-gradient-to-r from-[#0D9488] to-[#0B7A70] p-5 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm opacity-80">INVOICE</p>
              <p className="text-lg font-bold">{invoice.invoice_number}</p>
            </div>
            <div className="text-right text-sm">
              <p className="opacity-80">Date: {new Date(invoice.created_at).toLocaleDateString()}</p>
              <p className="opacity-80">Due: {invoice.due_date ? new Date(invoice.due_date).toLocaleDateString() : 'N/A'}</p>
            </div>
          </div>
        </div>
        <div className="p-5">
          <div className="mb-4">
            <p className="text-xs text-gray-400 uppercase tracking-wider">Bill To</p>
            <p className="font-semibold text-gray-900 dark:text-white">{invoice.customer_name}</p>
            {invoice.customer_phone && <p className="text-sm text-gray-500">{invoice.customer_phone}</p>}
            {invoice.customer_email && <p className="text-sm text-gray-500">{invoice.customer_email}</p>}
            {invoice.customer_address && <p className="text-sm text-gray-500">{invoice.customer_address}</p>}
          </div>
          <table className="w-full text-sm mb-4">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-700">
                <th className="text-left py-2 text-gray-500 font-medium">Item</th>
                <th className="text-right py-2 text-gray-500 font-medium">Qty</th>
                <th className="text-right py-2 text-gray-500 font-medium">Price</th>
                <th className="text-right py-2 text-gray-500 font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {(invoice.items || []).map((item: any) => (
                <tr key={item.id} className="border-b border-gray-50 dark:border-gray-700/50">
                  <td className="py-2 text-gray-800 dark:text-gray-200">{item.description}</td>
                  <td className="py-2 text-right text-gray-600 dark:text-gray-400">{item.quantity}</td>
                  <td className="py-2 text-right text-gray-600 dark:text-gray-400">{fmt(item.unit_price)}</td>
                  <td className="py-2 text-right font-medium text-gray-900 dark:text-white">{fmt(item.total_price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t border-gray-100 dark:border-gray-700 pt-3 space-y-1 text-sm">
            <div className="flex justify-between text-lg font-bold"><span className="text-gray-900 dark:text-white">Total</span><span className="text-[#0D9488]">{fmt(invoice.total_amount)}</span></div>
          </div>
          {invoice.notes && (
            <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
              <p className="text-xs text-gray-500 mb-1">Notes</p>
              <p className="text-sm text-gray-700 dark:text-gray-300">{invoice.notes}</p>
            </div>
          )}
        </div>
      </div>

      {/* ExportBar */}
      <div className="sticky bottom-0 mt-4 bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 p-3 shadow-lg">
        <div className="flex gap-2 overflow-x-auto">
          <ExportBtn icon={<Download size={16} />} label="PDF" onClick={handlePdf} />
          <ExportBtn icon={<Printer size={16} />} label="Print" onClick={() => window.print()} />
          <ExportBtn icon={<Share2 size={16} />} label="WhatsApp" onClick={handleWhatsApp} />
          <ExportBtn icon={<Mail size={16} />} label="Email" onClick={handleEmail} />
          <ExportBtn icon={<Trash2 size={16} />} label="Delete" onClick={handleDelete} />
        </div>
      </div>
    </div>
  );
}

function ExportBtn({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="flex flex-col items-center gap-1 px-3 py-2 min-w-[60px] rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition group">
      <span className="text-gray-400 group-hover:text-[#0D9488] transition">{icon}</span>
      <span className="text-[10px] text-gray-500 group-hover:text-gray-700 dark:group-hover:text-gray-300 transition">{label}</span>
    </button>
  );
}

// ─── ConversationalInvoiceCreator (API-backed) ──────────────────────────────
function ConversationalInvoiceCreator({ onCreated }: { onCreated: () => void }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<{ role: 'ozzy' | 'user'; text: string }[]>([]);
  const [preview, setPreview] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setMessages(prev => [...prev, { role: 'user', text }]);
    setInput('');
    setLoading(true);

    try {
      const invoice = await api.generateInvoiceFromText(text);
      setPreview(invoice);
      setMessages(prev => [...prev, {
        role: 'ozzy',
        text: `✅ Invoice created!\n\n**${invoice.invoice_number}** — ${invoice.customer_name}\nTotal: ${fmt(invoice.total_amount)}\nItems: ${invoice.items?.length || 0}\n\nInvoice is saved as **Draft**. You can view it in the list.`
      }]);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'ozzy', text: `Sorry, I couldn't create that invoice. ${err.message || 'Try a different format.'}` }]);
    } finally {
      setLoading(false);
    }
  };

  const quickFill = (example: string) => setInput(example);

  return (
    <div className="flex flex-col h-[calc(100vh-200px)]">
      <div className="flex items-center gap-2 mb-3">
        <button onClick={onCreated} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl"><X size={18} /></button>
        <span className="text-xl">💬</span>
        <h2 className="font-semibold text-gray-900 dark:text-white">Create Invoice</h2>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 mb-3">
        {messages.length === 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-4 border border-gray-100 dark:border-gray-700">
            <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
              👋 Tell me about your invoice! Try:
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {[
                'Invoice for Grace, 3 dresses @ 35,000, 2 scarves @ 15,000',
                'For John: 2 shirts @ 25,000, 1 suit @ 150,000',
                'Customer: Mary, 5kg rice @ 6,000, 3L oil @ 12,000',
              ].map((ex, i) => (
                <button key={i} onClick={() => quickFill(ex)} className="text-xs px-3 py-2 bg-[#0D9488]/10 text-[#0D9488] rounded-xl border border-[#0D9488]/20 hover:bg-[#0D9488]/20 transition">
                  {ex.slice(0, 40)}...
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 whitespace-pre-wrap text-sm leading-relaxed ${
              msg.role === 'user' ? 'bg-[#0D9488] text-white rounded-br-md' : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-100 dark:border-gray-700 rounded-bl-md'
            }`}>
              {msg.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-gray-800 rounded-2xl px-4 py-3 border border-gray-100 dark:border-gray-700">
              <Loader size={18} className="animate-spin text-[#0D9488]" />
            </div>
          </div>
        )}
      </div>

      {/* Preview Card */}
      {preview && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-4 border border-[#0D9488]/30 shadow-sm mb-3">
          <div className="flex items-center gap-2 mb-2">
            <Check size={16} className="text-green-500" />
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Created: {preview.invoice_number}</span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">Customer: {preview.customer_name}</p>
          <p className="text-sm font-semibold text-[#0D9488]">Total: {fmt(preview.total_amount)}</p>
          <button onClick={onCreated} className="w-full mt-3 py-2.5 bg-[#0D9488] text-white font-semibold rounded-xl text-sm hover:bg-[#0B7A70] transition">
            View in List →
          </button>
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-2 shadow-sm">
        <input type="text" className="flex-1 px-3 py-2 bg-transparent text-gray-900 dark:text-white placeholder-gray-400 outline-none text-sm" placeholder="Describe the invoice..." value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }} disabled={loading} />
        <button onClick={handleSend} disabled={!input.trim() || loading} className="w-10 h-10 rounded-xl bg-[#0D9488] text-white flex items-center justify-center disabled:opacity-40 transition hover:bg-[#0B7A70]">
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}

// ─── Main Invoices Page ─────────────────────────────────────────────────────
export default function Invoices() {
  const [step, setStep] = useState<Step>('list');

  return (
    <div>
      {step === 'list' && <InvoiceListView onCreate={() => setStep('create')} />}
      {step === 'create' && <ConversationalInvoiceCreator onCreated={() => setStep('list')} />}
    </div>
  );
}