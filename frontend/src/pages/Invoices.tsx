import { useState, useEffect } from 'react';
import { FileText, Plus, Search, Filter, MoreHorizontal, Eye, Copy, Trash2, X, Download, Printer, Share2, Mail, Save, MessageSquare, ChevronRight, Check, AlertCircle } from 'lucide-react';
import api from '../api/client';

// ─── Types ───────────────────────────────────────────────────────────────────
type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue';
type Step = 'list' | 'create' | 'template' | 'preview';

interface InvoiceItem {
  id: string;
  description: string;
  quantity: number;
  unitPrice: number;
}

interface Invoice {
  id: string;
  number: string;
  customerName: string;
  customerPhone: string;
  customerEmail: string;
  items: InvoiceItem[];
  subtotal: number;
  tax: number;
  total: number;
  status: InvoiceStatus;
  date: string;
  dueDate: string;
  notes: string;
  template: 1 | 2 | 3;
}

const TEMPLATES = [
  { id: 1, name: 'Professional', color: 'from-[#0D9488] to-[#0B7A70]', accent: '#0D9488', desc: 'Clean teal header, modern layout' },
  { id: 2, name: 'Classic', color: 'from-[#1E293B] to-[#334155]', accent: '#1E293B', desc: 'Dark header, traditional invoice' },
  { id: 3, name: 'Minimal', color: 'from-gray-100 to-white', accent: '#64748B', desc: 'No color, just clean typography' },
];

const fmt = (n: number) => 'UGX ' + Number(n).toLocaleString();

// ─── InvoiceListView ────────────────────────────────────────────────────────
function InvoiceListView({ invoices, onCreate, onView, onDuplicate, onDelete, onStatusFilter, statusFilter }: {
  invoices: Invoice[]; onCreate: () => void; onView: (i: Invoice) => void;
  onDuplicate: (i: Invoice) => void; onDelete: (id: string) => void;
  onStatusFilter: (s: InvoiceStatus | 'all') => void; statusFilter: InvoiceStatus | 'all';
}) {
  const [search, setSearch] = useState('');

  const filtered = invoices.filter(inv => {
    const matchSearch = !search || inv.customerName.toLowerCase().includes(search.toLowerCase()) || inv.number.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'all' || inv.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const statusColor: Record<InvoiceStatus, string> = { draft: 'bg-gray-100 text-gray-600', sent: 'bg-blue-100 text-blue-600', paid: 'bg-green-100 text-green-600', overdue: 'bg-red-100 text-red-600' };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Invoices</h1>
        <button onClick={onCreate} className="flex items-center gap-1.5 px-4 py-2 bg-[#0D9488] text-white rounded-xl text-sm font-medium hover:bg-[#0B7A70] transition">
          <Plus size={16} /> New Invoice
        </button>
      </div>

      {/* Search & Filter */}
      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" className="w-full pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 dark:text-white text-sm focus:ring-2 focus:ring-[#0D9488] outline-none" placeholder="Search invoices..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      <div className="flex gap-1 mb-4 overflow-x-auto pb-1">
        {(['all', 'draft', 'sent', 'paid', 'overdue'] as const).map(s => (
          <button key={s} onClick={() => onStatusFilter(s)} className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition ${statusFilter === s ? 'bg-[#0D9488] text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700'}`}>
            {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          <div className="text-5xl mb-3">🧾</div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">No invoices yet</p>
          <p className="text-xs mb-4">Create your first invoice to get paid faster</p>
          <button onClick={onCreate} className="px-5 py-2.5 bg-[#0D9488] text-white rounded-xl text-sm font-medium hover:bg-[#0B7A70] transition">+ Create Invoice</button>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(inv => (
            <div key={inv.id} className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-100 dark:border-gray-700 hover:shadow-sm transition cursor-pointer" onClick={() => onView(inv)}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-gray-900 dark:text-white">{inv.number}</span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColor[inv.status]}`}>{inv.status}</span>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{inv.customerName}</p>
                  <p className="text-xs text-gray-400">{new Date(inv.date).toLocaleDateString()}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-gray-900 dark:text-white">{fmt(inv.total)}</p>
                  <div className="flex gap-1 mt-1 justify-end">
                    <button onClick={(e) => { e.stopPropagation(); onView(inv); }} className="p-1 text-gray-400 hover:text-[#0D9488] transition"><Eye size={14} /></button>
                    <button onClick={(e) => { e.stopPropagation(); onDuplicate(inv); }} className="p-1 text-gray-400 hover:text-[#0D9488] transition"><Copy size={14} /></button>
                    <button onClick={(e) => { e.stopPropagation(); if (confirm('Delete this invoice?')) onDelete(inv.id); }} className="p-1 text-gray-400 hover:text-red-500 transition"><Trash2 size={14} /></button>
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

// ─── ConversationalInvoiceCreator ───────────────────────────────────────────
function ConversationalInvoiceCreator({ onConfirm }: { onConfirm: (invoice: Partial<Invoice>) => void }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<{ role: 'ozzy' | 'user'; text: string }[]>([]);
  const [preview, setPreview] = useState<{ customerName: string; items: { description: string; quantity: number; unitPrice: number }[] } | null>(null);
  const [step, setStep] = useState(0);

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;
    setMessages(prev => [...prev, { role: 'user', text }]);
    setInput('');

    // Parse the input
    const lines = text.split('\n').filter(Boolean);
    const customerMatch = text.match(/customer\s*(?:is|:)?\s*(.+)/i) || text.match(/for\s+(.+)/i);
    const items = lines.map(l => {
      const parts = l.split(/[,@]/).map(s => s.trim());
      const desc = parts[0]?.replace(/^\d+[\.\)]\s*/, '') || '';
      const qty = parseInt(parts[1]?.match(/\d+/)?.[0] || '1');
      const price = parseInt(parts.reverse().find(p => /\d{3,}/.test(p)) || '0');
      return { description: desc, quantity: qty, unitPrice: price };
    }).filter(i => i.description);

    if (customerMatch || items.length > 0) {
      const customerName = customerMatch?.[1]?.trim() || 'Customer';
      setPreview({ customerName, items: items.length > 0 ? items : [{ description: 'Service', quantity: 1, unitPrice: 0 }] });
      setMessages(prev => [...prev, { role: 'ozzy', text: `I found:\n\n👤 **Customer:** ${customerName}\n📦 **Items:** ${items.map(i => `${i.description} × ${i.quantity} @ ${fmt(i.unitPrice)}`).join('\n')}\n\nIs this correct? Tap "Create Invoice" to continue.` }]);
      setStep(2);
    } else {
      setMessages(prev => [...prev, { role: 'ozzy', text: 'Tell me about the invoice. For example:\n\n_"Invoice for John, 3 shirts @ 25,000, 2 pants @ 40,000"_' }]);
      setStep(1);
    }
  };

  const quickFill = (example: string) => {
    setInput(example);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-200px)]">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">💬</span>
        <h2 className="font-semibold text-gray-900 dark:text-white">Create Invoice</h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-3">
        {messages.length === 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-4 border border-gray-100 dark:border-gray-700">
            <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
              👋 Tell me about your invoice! Try typing something like:
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
      </div>

      {/* Preview Card */}
      {preview && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-4 border border-[#0D9488]/30 shadow-sm mb-3">
          <div className="flex items-center gap-2 mb-2">
            <Check size={16} className="text-green-500" />
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Extracted Preview</span>
          </div>
          <div className="space-y-1 text-sm">
            <p className="text-gray-600 dark:text-gray-400"><span className="font-medium">Customer:</span> {preview.customerName}</p>
            {preview.items.map((item, i) => (
              <p key={i} className="text-gray-500 dark:text-gray-400 ml-2">
                • {item.description} × {item.quantity} @ {fmt(item.unitPrice)}
                <span className="text-gray-700 dark:text-gray-300 ml-2">= {fmt(item.quantity * item.unitPrice)}</span>
              </p>
            ))}
            <p className="text-right font-semibold text-gray-900 dark:text-white pt-1 border-t border-gray-100 dark:border-gray-700 mt-1">
              Total: {fmt(preview.items.reduce((s, i) => s + i.quantity * i.unitPrice, 0))}
            </p>
          </div>
          <button onClick={() => onConfirm({ customerName: preview.customerName, items: preview.items.map(i => ({ ...i, id: crypto.randomUUID() })) })} className="w-full mt-3 py-2.5 bg-[#0D9488] text-white font-semibold rounded-xl text-sm hover:bg-[#0B7A70] transition">
            Create Invoice →
          </button>
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-2 shadow-sm">
        <input type="text" className="flex-1 px-3 py-2 bg-transparent text-gray-900 dark:text-white placeholder-gray-400 outline-none text-sm" placeholder="Describe the invoice..." value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }} />
        <button onClick={handleSend} disabled={!input.trim()} className="w-10 h-10 rounded-xl bg-[#0D9488] text-white flex items-center justify-center disabled:opacity-40 transition hover:bg-[#0B7A70]">
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}

// ─── TemplatePicker ─────────────────────────────────────────────────────────
function TemplatePicker({ onSelect, onBack }: { onSelect: (id: 1 | 2 | 3) => void; onBack: () => void }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <button onClick={onBack} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl"><X size={18} /></button>
        <h2 className="font-semibold text-gray-900 dark:text-white">Choose a Template</h2>
      </div>
      <div className="space-y-3">
        {TEMPLATES.map(t => (
          <button key={t.id} onClick={() => onSelect(t.id as 1 | 2 | 3)} className="w-full text-left bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 overflow-hidden hover:shadow-md transition group">
            <div className={`h-20 bg-gradient-to-r ${t.color} flex items-center justify-center`}>
              <div className="bg-white/90 dark:bg-gray-800/90 rounded-xl px-4 py-2 shadow-sm">
                <div className="flex gap-6">
                  <div className="w-16 h-10 bg-gray-200 dark:bg-gray-700 rounded" />
                  <div className="space-y-1">
                    <div className="w-20 h-2 bg-gray-300 dark:bg-gray-600 rounded" />
                    <div className="w-12 h-2 bg-gray-300 dark:bg-gray-600 rounded" />
                  </div>
                </div>
              </div>
            </div>
            <div className="p-3 flex items-center justify-between">
              <div>
                <p className="font-medium text-sm text-gray-900 dark:text-white">{t.name}</p>
                <p className="text-xs text-gray-400">{t.desc}</p>
              </div>
              <ChevronRight size={18} className="text-gray-400 group-hover:text-[#0D9488] transition" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── InvoicePreview ─────────────────────────────────────────────────────────
function InvoicePreview({ invoice, onEdit, onExport }: { invoice: Invoice; onEdit: () => void; onExport: (action: string) => void }) {
  const template = TEMPLATES.find(t => t.id === invoice.template) || TEMPLATES[0];
  const isDark = template.id === 1 || template.id === 2;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button onClick={onEdit} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl"><X size={18} /></button>
          <h2 className="font-semibold text-gray-900 dark:text-white">Invoice Preview</h2>
        </div>
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${invoice.status === 'paid' ? 'bg-green-100 text-green-600' : invoice.status === 'sent' ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'}`}>{invoice.status}</span>
      </div>

      {/* Invoice Render */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 overflow-hidden shadow-sm">
        {/* Header */}
        <div className={`bg-gradient-to-r ${template.color} p-5 text-${isDark ? 'white' : 'gray-900'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm opacity-80">INVOICE</p>
              <p className="text-lg font-bold">{invoice.number}</p>
            </div>
            <div className="text-right text-sm">
              <p className="opacity-80">Date: {new Date(invoice.date).toLocaleDateString()}</p>
              <p className="opacity-80">Due: {new Date(invoice.dueDate).toLocaleDateString()}</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-5">
          <div className="mb-4">
            <p className="text-xs text-gray-400 uppercase tracking-wider">Bill To</p>
            <p className="font-semibold text-gray-900 dark:text-white">{invoice.customerName}</p>
            <p className="text-sm text-gray-500">{invoice.customerPhone}</p>
            {invoice.customerEmail && <p className="text-sm text-gray-500">{invoice.customerEmail}</p>}
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
              {invoice.items.map(item => (
                <tr key={item.id} className="border-b border-gray-50 dark:border-gray-700/50">
                  <td className="py-2 text-gray-800 dark:text-gray-200">{item.description}</td>
                  <td className="py-2 text-right text-gray-600 dark:text-gray-400">{item.quantity}</td>
                  <td className="py-2 text-right text-gray-600 dark:text-gray-400">{fmt(item.unitPrice)}</td>
                  <td className="py-2 text-right font-medium text-gray-900 dark:text-white">{fmt(item.quantity * item.unitPrice)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="border-t border-gray-100 dark:border-gray-700 pt-3 space-y-1 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span className="text-gray-900 dark:text-white">{fmt(invoice.subtotal)}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Tax</span><span className="text-gray-900 dark:text-white">{fmt(invoice.tax)}</span></div>
            <div className="flex justify-between text-lg font-bold pt-1 border-t border-gray-100 dark:border-gray-700"><span className="text-gray-900 dark:text-white">Total</span><span className="text-[#0D9488]">{fmt(invoice.total)}</span></div>
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
          <ExportBtn icon={<Download size={16} />} label="PDF" onClick={() => onExport('pdf')} />
          <ExportBtn icon={<Printer size={16} />} label="Print" onClick={() => onExport('print')} />
          <ExportBtn icon={<Share2 size={16} />} label="WhatsApp" onClick={() => onExport('whatsapp')} />
          <ExportBtn icon={<Mail size={16} />} label="Email" onClick={() => onExport('email')} />
          <ExportBtn icon={<Save size={16} />} label="Draft" onClick={() => onExport('draft')} />
          <ExportBtn icon={<Copy size={16} />} label="Duplicate" onClick={() => onExport('duplicate')} />
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

// ─── Main Invoices Page ─────────────────────────────────────────────────────
export default function Invoices() {
  const [step, setStep] = useState<Step>('list');
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'all'>('all');
  const [currentInvoice, setCurrentInvoice] = useState<Invoice | null>(null);
  const [pendingData, setPendingData] = useState<Partial<Invoice> | null>(null);

  const generateNumber = () => `INV-${String(Date.now()).slice(-6)}`;

  const handleCreateConfirm = (data: Partial<Invoice>) => {
    setPendingData(data);
    setStep('template');
  };

  const handleTemplateSelect = (templateId: 1 | 2 | 3) => {
    if (!pendingData) return;
    const items = (pendingData.items || []).map(i => ({ ...i, id: crypto.randomUUID() }));
    const subtotal = items.reduce((s, i) => s + i.quantity * i.unitPrice, 0);
    const tax = 0;
    const total = subtotal + tax;
    const now = new Date();
    const due = new Date(now); due.setDate(due.getDate() + 30);

    const invoice: Invoice = {
      id: crypto.randomUUID(),
      number: generateNumber(),
      customerName: pendingData.customerName || 'Customer',
      customerPhone: pendingData.customerPhone || '',
      customerEmail: pendingData.customerEmail || '',
      items,
      subtotal, tax, total,
      status: 'draft',
      date: now.toISOString(),
      dueDate: due.toISOString(),
      notes: '',
      template: templateId,
    };

    setCurrentInvoice(invoice);
    setStep('preview');
  };

  const handleExport = (action: string) => {
    if (!currentInvoice) return;
    switch (action) {
      case 'print': window.print(); break;
      case 'whatsapp': {
        const text = `Invoice ${currentInvoice.number}\nCustomer: ${currentInvoice.customerName}\nTotal: ${fmt(currentInvoice.total)}`;
        window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
        break;
      }
      case 'draft':
        setInvoices(prev => [...prev, { ...currentInvoice, status: 'draft' }]);
        setStep('list');
        break;
      case 'duplicate':
        handleCreateConfirm({ customerName: currentInvoice.customerName, customerPhone: currentInvoice.customerPhone, customerEmail: currentInvoice.customerEmail, items: currentInvoice.items });
        break;
      case 'pdf':
        window.print();
        break;
      case 'email':
        window.open(`mailto:${currentInvoice.customerEmail || ''}?subject=Invoice ${currentInvoice.number}&body=Dear ${currentInvoice.customerName}, please find your invoice attached.`);
        break;
    }
  };

  const handleView = (inv: Invoice) => {
    setCurrentInvoice(inv);
    setStep('preview');
  };

  const handleDuplicate = (inv: Invoice) => {
    const newInv: Invoice = { ...inv, id: crypto.randomUUID(), number: generateNumber(), status: 'draft', date: new Date().toISOString() };
    setInvoices(prev => [...prev, newInv]);
  };

  const handleDelete = (id: string) => {
    setInvoices(prev => prev.filter(i => i.id !== id));
  };

  return (
    <div>
      {step === 'list' && (
        <InvoiceListView invoices={invoices} onCreate={() => { setPendingData(null); setStep('create'); }} onView={handleView} onDuplicate={handleDuplicate} onDelete={handleDelete} onStatusFilter={setStatusFilter} statusFilter={statusFilter} />
      )}
      {step === 'create' && (
        <ConversationalInvoiceCreator onConfirm={handleCreateConfirm} />
      )}
      {step === 'template' && (
        <TemplatePicker onSelect={handleTemplateSelect} onBack={() => setStep('create')} />
      )}
      {step === 'preview' && currentInvoice && (
        <InvoicePreview invoice={currentInvoice} onEdit={() => setStep('list')} onExport={handleExport} />
      )}
    </div>
  );
}