import { useState, useEffect, useRef } from 'react';
import api from '../api/client';
import { useNavigate } from 'react-router-dom';

function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

interface Draft { type: 'sale' | 'expense'; description: string; amount: number; quantity: number; }
interface Msg {
  id: string;
  role: 'ozzy' | 'user';
  kind: 'text' | 'confirm' | 'recorded';
  text?: string;
  draft?: Draft;
}

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([{
    id: 'welcome', role: 'ozzy', kind: 'text',
    text: "Hi! I'm Ozzy. Tell me what happened in your business, like \"Sold 3 sodas 6,000\" or \"Paid rent 200,000\", and I'll record it.",
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const cur = summary?.currency || 'UGX';
  const fmt = (n: number | string) => `${cur} ${Number(n || 0).toLocaleString()}`;

  const loadSummary = () => api.getReportSummary().then(setSummary).catch(() => {});
  useEffect(() => { loadSummary(); }, []);
  useEffect(() => { setTimeout(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), 80); }, [messages]);

  const push = (m: Omit<Msg, 'id'>) => setMessages(p => [...p, { ...m, id: Date.now() + '' + Math.random() }]);

  const send = async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg) return;
    push({ role: 'user', kind: 'text', text: msg });
    setInput('');
    setLoading(true);
    try {
      const res: any = await api.processChat(msg);
      const p = res.parsed || res;
      const intent = p.intent || p.type;           // backend returns 'intent'
      const description = p.item || p.description || msg;  // backend returns 'item'
      const amount = parseFloat(p.amount) || 0;
      const quantity = parseFloat(p.quantity) || 1;
      if ((intent === 'sale' || intent === 'expense') && amount > 0) {
        push({ role: 'ozzy', kind: 'confirm', draft: { type: intent, description, amount, quantity } });
      } else {
        push({ role: 'ozzy', kind: 'text', text: `I didn't catch an amount. Try "Sold rice 10,000" or "Paid rent 300,000".` });
      }
    } catch {
      push({ role: 'ozzy', kind: 'text', text: `Sorry, something went wrong. Please try again.` });
    } finally {
      setLoading(false);
    }
  };

  const confirmYes = async (m: Msg) => {
    if (!m.draft) return;
    setMessages(p => p.filter(x => x.id !== m.id));
    try {
      await api.createTransaction({ type: m.draft.type, amount: m.draft.amount, description: m.draft.description, quantity: m.draft.quantity });
      push({ role: 'ozzy', kind: 'recorded', draft: m.draft });
      loadSummary();
    } catch {
      push({ role: 'ozzy', kind: 'text', text: `Couldn't save that. Please try again.` });
    }
  };
  const confirmNo = (m: Msg) => {
    setMessages(p => p.filter(x => x.id !== m.id));
    push({ role: 'ozzy', kind: 'text', text: `No problem, I didn't record it.` });
  };

  const onKey = (e: React.KeyboardEvent) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } };

  return (
    <div className="h-screen flex flex-col relative overflow-hidden">
      {/* Summary strip */}
      <div className="z-30 px-lg py-md md:px-margin-desktop">
        <button
          onClick={() => navigate('/reports')}
          className="mx-auto flex items-center justify-center gap-lg bg-surface-container-low hover:bg-surface-container hover:shadow-sm cursor-pointer transition-all rounded-full px-lg py-3 border border-outline-variant/40"
        >
          <span className="flex items-center gap-2 whitespace-nowrap">
            <Icon name="trending_up" className="text-[#1EBFA3] text-[18px]" />
            <span className="font-label-md text-label-md text-on-surface-variant">Today's sales</span>
            <span className="font-label-md text-label-md font-bold text-primary">{summary ? fmt(summary.total_sales) : '—'}</span>
          </span>
          <span className="w-px h-5 bg-outline-variant"></span>
          <span className="flex items-center gap-2 whitespace-nowrap">
            <Icon name="trending_down" className="text-outline text-[18px]" />
            <span className="font-label-md text-label-md text-on-surface-variant">Spent</span>
            <span className="font-label-md text-label-md font-bold text-on-surface">{summary ? fmt(summary.total_expenses) : '—'}</span>
          </span>
        </button>
      </div>

      {/* Header */}
      <div className="text-center pt-md pb-md">
        <h2 className="font-headline-lg text-headline-lg text-primary">Chat with Ozzy</h2>
        <p className="font-body-md text-body-md text-outline">Your business assistant is ready to help.</p>
      </div>

      {/* Conversation */}
      <section className="flex-1 overflow-y-auto px-lg md:px-margin-desktop pb-32">
        <div className="max-w-2xl mx-auto flex flex-col gap-lg">
          {messages.map(m => m.role === 'user' ? (
            <div key={m.id} className="flex flex-col gap-sm items-end">
              <span className="font-label-md text-label-md text-outline mr-2">You</span>
              <div className="bg-[#1EBFA3] text-white px-lg py-md rounded-2xl rounded-tr-none max-w-[85%] shadow-md">
                <p className="font-body-md text-body-md">{m.text}</p>
              </div>
            </div>
          ) : (
            <div key={m.id} className="flex flex-col gap-sm items-start">
              <div className="flex items-center gap-sm">
                <div className="w-6 h-6 rounded-full bg-[#1EBFA3] flex items-center justify-center">
                  <Icon name="token" className="text-[14px] text-white" />
                </div>
                <span className="font-label-md text-label-md text-outline">Ozzy</span>
              </div>

              {m.kind === 'confirm' && m.draft ? (
                <div className="bg-surface-container-high text-on-surface px-lg py-md rounded-2xl rounded-tl-none max-w-[85%] shadow-sm space-y-md">
                  <p className="font-body-md text-body-md">Please confirm:</p>
                  <div className="bg-surface-container-lowest border border-outline-variant p-lg rounded-xl shadow-sm">
                    <div className="flex items-center justify-between mb-md">
                      <div className="flex items-center gap-sm">
                        <Icon name="check_circle" className="text-primary" />
                        <span className="font-label-md text-label-md font-bold text-primary">{m.draft.type === 'sale' ? 'Sale' : 'Expense'}</span>
                      </div>
                    </div>
                    <div className="flex justify-between items-center py-sm border-t border-b border-surface-container">
                      <span className="font-body-md text-body-md">{m.draft.description}{m.draft.quantity > 1 ? ` × ${m.draft.quantity}` : ''}</span>
                      <span className={`font-body-md text-body-md font-bold ${m.draft.type === 'sale' ? 'text-green-600' : 'text-red-600'}`}>{fmt(m.draft.amount)}</span>
                    </div>
                    <div className="flex gap-sm mt-lg">
                      <button onClick={() => confirmYes(m)} className="flex-1 py-3 bg-primary text-white font-bold rounded-lg hover:opacity-90 active:scale-95 transition-all">Yes</button>
                      <button onClick={() => confirmNo(m)} className="flex-1 py-3 border border-primary text-primary font-bold rounded-lg hover:bg-primary/5 active:scale-95 transition-all">No</button>
                    </div>
                  </div>
                </div>
              ) : m.kind === 'recorded' && m.draft ? (
                <div className="bg-surface-container-high text-on-surface px-lg py-md rounded-2xl rounded-tl-none max-w-[85%] shadow-sm">
                  <div className="flex items-center gap-2">
                    <Icon name="check_circle" className="text-green-600" />
                    <span className="font-body-md text-body-md">Recorded {m.draft.type === 'sale' ? 'sale' : 'expense'}: <span className="font-bold">{m.draft.description}</span> <span className={m.draft.type === 'sale' ? 'text-green-600 font-bold' : 'text-red-600 font-bold'}>{fmt(m.draft.amount)}</span></span>
                  </div>
                </div>
              ) : (
                <div className="bg-surface-container-high text-on-surface px-lg py-md rounded-2xl rounded-tl-none max-w-[85%] shadow-sm">
                  <p className="font-body-md text-body-md">{m.text}</p>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-outline">
              <div className="w-2 h-2 bg-outline rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-outline rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-outline rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          )}
          <div ref={endRef} />
        </div>
      </section>

      {/* Input */}
      <div className="absolute bottom-0 left-0 w-full p-lg md:px-margin-desktop bg-gradient-to-t from-surface via-surface to-transparent pt-xxl">
        <div className="max-w-2xl mx-auto">
          <div className="flex gap-sm mb-md overflow-x-auto pb-2 no-scrollbar">
            <button onClick={() => setInput('Sold ')} className="whitespace-nowrap px-lg py-2 bg-white border border-outline-variant rounded-full font-label-md text-label-md text-on-surface-variant hover:border-primary hover:text-primary transition-all shadow-sm">Record a sale</button>
            <button onClick={() => setInput('Paid ')} className="whitespace-nowrap px-lg py-2 bg-white border border-outline-variant rounded-full font-label-md text-label-md text-on-surface-variant hover:border-primary hover:text-primary transition-all shadow-sm">Record an expense</button>
            <button onClick={() => navigate('/inventory')} className="whitespace-nowrap px-lg py-2 bg-white border border-outline-variant rounded-full font-label-md text-label-md text-on-surface-variant hover:border-primary hover:text-primary transition-all shadow-sm">Check stock</button>
          </div>
          <div className="relative flex items-center group">
            <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey} disabled={loading}
              className="w-full h-14 pl-lg pr-16 bg-white border border-outline-variant rounded-full text-body-md focus:ring-2 focus:ring-primary focus:border-transparent transition-all shadow-lg group-hover:shadow-xl outline-none" placeholder="Type a message to Ozzy..." type="text" />
            <button onClick={() => send()} disabled={loading} className="absolute right-2 w-10 h-10 bg-primary text-white rounded-full flex items-center justify-center hover:scale-105 active:scale-90 transition-all shadow-sm disabled:opacity-50">
              <Icon name="send" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
