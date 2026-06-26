import { useState, useEffect, useRef } from 'react';
import { Send, Plus, TrendingUp, TrendingDown } from 'lucide-react';
import api from '../api/client';
import { useNavigate } from 'react-router-dom';

interface Message {
  id: string;
  role: 'ozzy' | 'user';
  text: string;
  timestamp: Date;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(!localStorage.getItem('ozzy_onboarding_shown'));
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (showOnboarding) {
      setMessages([{
        id: 'onboarding',
        role: 'ozzy',
        text: `👋 Hi! I'm Ozzy.

Just tell me what happens in your business, like:

"Sold rice 15,000"
"Paid rent 200,000"
"Bought stock 50,000"

I'll take care of the bookkeeping! 📊

Try it now 👇`,
        timestamp: new Date(),
      }]);
    }
    scrollToBottom();
  }, [showOnboarding]);

  const scrollToBottom = () => {
    setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  };

  const addMessage = (role: 'ozzy' | 'user', text: string) => {
    const msg: Message = { id: Date.now().toString(), role, text, timestamp: new Date() };
    setMessages(prev => [...prev, msg]);
    scrollToBottom();
  };

  const handleSend = async (text?: string) => {
    const msg = text || input.trim();
    if (!msg) return;

    // Mark onboarding as seen on first interaction
    if (showOnboarding) {
      localStorage.setItem('ozzy_onboarding_shown', 'true');
      setShowOnboarding(false);
    }

    addMessage('user', msg);
    setInput('');
    setLoading(true);

    try {
      // Try the NLP parse endpoint
      const result = await api.processChat(msg);
      const parsed = result.parsed || result;

      if (parsed.type === 'sale' || parsed.type === 'expense') {
        addMessage('ozzy', `Got it! I understood:\n\n${parsed.type === 'sale' ? '💰 Sale' : '💸 Expense'}: ${parsed.description || msg}\nAmount: UGX ${Number(parsed.amount || 0).toLocaleString()}\n\n✅ Would you like me to record this?`);

        // Auto-record for demo
        await api.createTransaction({
          type: parsed.type,
          amount: parseFloat(parsed.amount) || 0,
          description: parsed.description || msg,
          quantity: parseInt(parsed.quantity) || 1,
        });
        addMessage('ozzy', `✅ ${parsed.type === 'sale' ? 'Sale' : 'Expense'} recorded! Check your Dashboard to see updates.`);
      } else {
        addMessage('ozzy', `I understood: "${msg}".\n\nDid you mean:\n• A **sale** (earning money)?\n• An **expense** (spending money)?`);
      }
    } catch {
      // Fallback: try to parse manually
      const lower = msg.toLowerCase();
      const isSale = lower.includes('sold') || lower.includes('sale') || !lower.includes('paid') && !lower.includes('bought') && !lower.includes('expense');
      const isExpense = lower.includes('paid') || lower.includes('bought') || lower.includes('expense') || lower.includes('rent') || lower.includes('fuel');

      if (isSale || isExpense) {
        const nums = msg.match(/[\d,]+/g);
        const amount = nums ? parseFloat(nums[0].replace(/,/g, '')) : 0;
        const desc = msg.replace(/sold|paid|bought|sale|expense/i, '').replace(/[\d,]+/g, '').trim() || (isSale ? 'Sale' : 'Expense');

        if (amount > 0) {
          try {
            await api.createTransaction({
              type: isSale ? 'sale' : 'expense',
              amount,
              description: desc,
              quantity: 1,
            });
            addMessage('ozzy', `✅ Recorded! ${isSale ? '💰 Sale' : '💸 Expense'}: ${desc} — UGX ${amount.toLocaleString()}`);
          } catch {
            addMessage('ozzy', `I'd record this as a ${isSale ? 'sale' : 'expense'} of UGX ${amount.toLocaleString()} for "${desc}". Use the +Sale or +Expense buttons to be more specific next time!`);
          }
        } else {
          addMessage('ozzy', `Sorry! Could you tell me again? Try: "Sold rice 10,000" or "Paid rent 300,000"`);
        }
      } else {
        addMessage('ozzy', `Sorry! Could you tell me again? Try: "Sold rice 10,000" or "Paid rent 300,000"`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const tryExample = () => {
    handleSend('Sold rice 15,000');
    localStorage.setItem('ozzy_onboarding_shown', 'true');
    setShowOnboarding(false);
  };

  const quickInsert = (type: 'sale' | 'expense') => {
    const prefix = type === 'sale' ? 'Sold ' : 'Paid ';
    setInput(prefix);
    const inputEl = document.getElementById('chat-input');
    if (inputEl) inputEl.focus();
  };

  return (
    <div className="flex flex-col h-[calc(100vh-180px)]">
      <div className="flex-1 overflow-y-auto space-y-3 px-1 pb-3">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 whitespace-pre-wrap text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-[#0D9488] text-white rounded-br-md'
                : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-100 dark:border-gray-700 rounded-bl-md shadow-sm'
            }`}>
              {msg.text}
            </div>
          </div>
        ))}

        {showOnboarding && (
          <div className="flex justify-center mt-2">
            <button onClick={tryExample} className="px-5 py-3 bg-[#0D9488]/10 text-[#0D9488] font-medium rounded-xl text-sm border border-[#0D9488]/20 hover:bg-[#0D9488]/20 transition min-h-[48px]">
              ✨ Try an Example
            </button>
          </div>
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-gray-800 rounded-2xl px-4 py-3 border border-gray-100 dark:border-gray-700">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick-insert chips [+ Sale] [+ Expense] */}
      <div className="flex gap-2 mb-2">
        <button onClick={() => quickInsert('sale')} className="flex items-center gap-1.5 px-4 py-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-xl text-sm font-medium border border-green-200 dark:border-green-800 hover:bg-green-100 dark:hover:bg-green-900/30 transition min-h-[48px]">
          <TrendingUp size={16} /> + Sale
        </button>
        <button onClick={() => quickInsert('expense')} className="flex items-center gap-1.5 px-4 py-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-xl text-sm font-medium border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/30 transition min-h-[48px]">
          <TrendingDown size={16} /> + Expense
        </button>
        <button onClick={() => navigate('/transactions')} className="flex items-center gap-1.5 px-4 py-3 bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-xl text-sm border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition min-h-[48px]">
          <History size={16} /> History
        </button>
      </div>

      {/* Input Bar (WhatsApp-like) */}
      <div className="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-2 shadow-sm">
        <input
          id="chat-input"
          type="text"
          className="flex-1 px-3 py-2 bg-transparent text-gray-900 dark:text-white placeholder-gray-400 outline-none text-sm"
          placeholder="Type a message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          className="w-10 h-10 rounded-xl bg-[#0D9488] text-white flex items-center justify-center disabled:opacity-40 transition hover:bg-[#0B7A70]"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}