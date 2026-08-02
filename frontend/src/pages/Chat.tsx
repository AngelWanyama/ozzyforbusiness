import { useState, useEffect, useRef } from 'react';
import api from '../api/client';
import ozzyLogo from '../assets/ozzy-icon-logo.png';
import { useNavigate } from 'react-router-dom';

function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

interface Draft { type: 'sale' | 'expense'; description: string; amount: number; quantity: number; original: string; }

type OnboardStepKey =
  | 'owner_name' | 'business_name' | 'business_location'
  | 'business_description' | 'years_in_business' | 'logo' | 'phone_confirm' | 'email';

const ONBOARD_STEPS: OnboardStepKey[] = [
  'owner_name', 'business_name', 'business_location',
  'business_description', 'years_in_business', 'logo', 'phone_confirm', 'email',
];

interface Msg {
  id: string;
  role: 'ozzy' | 'user';
  kind: 'text' | 'confirm' | 'recorded' | 'onboard-choice' | 'onboard-logo';
  text?: string;
  draft?: Draft;
  choices?: { label: string; value: string }[];
  stepKey?: OnboardStepKey;
}

const WELCOME_BACK_TEXT = "👋 Hi! I'm Ozzy, your business partner. Tell me what happened today, like \"Sold 3 sodas 6,000\" or \"Bought airtime 5,000\". You can also ask me things like \"What's my profit today?\"";

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [pending, setPending] = useState<Draft | null>(null);   // waiting for a missing amount

  const [profile, setProfile] = useState<any>(null);
  const [onboardIndex, setOnboardIndex] = useState<number | null>(null); // null = not in onboarding
  const [onboardAnswers, setOnboardAnswers] = useState<Record<string, string>>({});
  const [awaitingFieldFor, setAwaitingFieldFor] = useState<'contact_phone' | 'email' | null>(null);

  const endRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const cur = summary?.currency || 'UGX';
  const fmt = (n: number | string) => `${cur} ${Number(n || 0).toLocaleString()}`;

  const loadSummary = () => api.getReportSummary().then(setSummary).catch(() => {});
  const push = (m: Omit<Msg, 'id'>) => setMessages(p => [...p, { ...m, id: Date.now() + '' + Math.random() }]);

  // Saves one profile field immediately, as each onboarding answer comes in.
  // Cast to bypass client.ts's narrower updateMe() typing rather than widen a shared file mid-flight.
  const patchMe = (data: Record<string, any>) => (api as any).updateMe(data);

  const uploadLogoFile = async (file: File) => {
    const token = localStorage.getItem('ozzy_access_token');
    const base = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1';
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${base}/users/me/logo`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  };

  // ─── Onboarding conversation ────────────────────────────────────────────────

  const onboardQuestion = (stepKey: OnboardStepKey, answers: Record<string, string>): string => {
    const name = answers.owner_name || '';
    const biz = answers.business_name || 'your business';
    switch (stepKey) {
      case 'owner_name':
        return "👋 Hi! I'm Ozzy, your business partner. Before we dive in, let's get to know each other — what's your name?";
      case 'business_name':
        return `Thanks, ${name}! Let's get your business ready. What's your business called?`;
      case 'business_location':
        return `Nice! Where is ${biz} located?`;
      case 'business_description':
        return `And what does ${biz} do?`;
      case 'years_in_business':
        return `How long has ${biz} been running?`;
      case 'logo':
        return `Want to add your business logo? It'll show up on your invoices and receipts.`;
      case 'phone_confirm':
        return `Should customers reach you on the number you used to log in${profile?.phone_number ? ` (${profile.phone_number})` : ''}, or a different one?`;
      case 'email':
        return `Last thing — do you have an email to share, or shall we continue with just your phone?`;
      default:
        return '';
    }
  };

  const askOnboardStep = (index: number, answers: Record<string, string>) => {
    if (index >= ONBOARD_STEPS.length) { finishOnboarding(answers); return; }
    const stepKey = ONBOARD_STEPS[index];
    const question = onboardQuestion(stepKey, answers);

    if (stepKey === 'logo') {
      push({ role: 'ozzy', kind: 'onboard-logo', text: question, stepKey });
    } else if (stepKey === 'phone_confirm') {
      push({
        role: 'ozzy', kind: 'onboard-choice', text: question, stepKey,
        choices: [{ label: 'Use this number', value: 'same' }, { label: 'Use a different one', value: 'different' }],
      });
    } else if (stepKey === 'email') {
      push({
        role: 'ozzy', kind: 'onboard-choice', text: question, stepKey,
        choices: [{ label: 'Add an email', value: 'add' }, { label: 'Just my phone is fine', value: 'skip' }],
      });
    } else {
      push({ role: 'ozzy', kind: 'text', text: question });
    }
    setOnboardIndex(index);
  };

  const finishOnboarding = async (answers: Record<string, string>) => {
    try { await patchMe({ onboarding_completed: true }); } catch { /* not fatal — worst case they see onboarding again next login */ }
    push({
      role: 'ozzy', kind: 'text',
      text: `🎉 All set, ${answers.owner_name || 'there'}! ${answers.business_name || 'Your business'} is ready to go. Tell me about your first sale or expense whenever you're ready — like "Sold 3 sodas 6,000".`,
    });
    setOnboardIndex(null);
  };

  const handleOnboardTextAnswer = async (text: string) => {
    const stepKey = ONBOARD_STEPS[onboardIndex!];
    const value = text.trim();
    if (!value) { push({ role: 'ozzy', kind: 'text', text: 'Sorry, could you say that again?' }); return; }

    setLoading(true);
    const newAnswers = { ...onboardAnswers, [stepKey]: value };
    setOnboardAnswers(newAnswers);
    try {
      if (stepKey === 'years_in_business') {
        const m = value.match(/\d+(\.\d+)?/);
        let years = m ? Math.round(parseFloat(m[0])) : 0;
        if (/month/i.test(value) && years < 1) years = 0; // "6 months" etc. — round down to 0 full years
        await patchMe({ years_in_business: years });
      } else {
        const fieldMap: Partial<Record<OnboardStepKey, string>> = {
          owner_name: 'owner_name', business_name: 'business_name',
          business_location: 'business_location', business_description: 'business_description',
        };
        const field = fieldMap[stepKey];
        if (field) await patchMe({ [field]: value });
      }
    } catch { /* don't block the conversation on a single save hiccup */ }
    setLoading(false);
    askOnboardStep(onboardIndex! + 1, newAnswers);
  };

  const handleOnboardChoice = async (m: Msg, value: string) => {
    setMessages(p => p.filter(x => x.id !== m.id));
    const stepKey = m.stepKey!;
    const idx = onboardIndex!;

    if (stepKey === 'phone_confirm') {
      if (value === 'same') {
        push({ role: 'user', kind: 'text', text: 'Use this number' });
        askOnboardStep(idx + 1, onboardAnswers);
      } else {
        push({ role: 'user', kind: 'text', text: 'Use a different one' });
        push({ role: 'ozzy', kind: 'text', text: 'What number should we use instead?' });
        setAwaitingFieldFor('contact_phone');
      }
    } else if (stepKey === 'email') {
      if (value === 'skip') {
        push({ role: 'user', kind: 'text', text: 'Just my phone is fine' });
        finishOnboarding(onboardAnswers);
      } else {
        push({ role: 'user', kind: 'text', text: 'Add an email' });
        push({ role: 'ozzy', kind: 'text', text: "What's your email?" });
        setAwaitingFieldFor('email');
      }
    }
  };

  const handleLogoFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    if (!['image/png', 'image/jpeg', 'image/jpg', 'image/webp'].includes(file.type)) {
      push({ role: 'ozzy', kind: 'text', text: 'That needs to be a PNG, JPEG, or WEBP photo. Want to try again, or use "Skip for now" above?' });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      push({ role: 'ozzy', kind: 'text', text: 'That photo is a bit large — please choose one under 5MB, or use "Skip for now" above.' });
      return;
    }

    setMessages(p => p.filter(x => !(x.kind === 'onboard-logo')));
    push({ role: 'user', kind: 'text', text: `📷 ${file.name}` });
    setLoading(true);
    try {
      await uploadLogoFile(file);
      push({ role: 'ozzy', kind: 'text', text: 'Got it — logo saved!' });
    } catch {
      push({ role: 'ozzy', kind: 'text', text: "Hmm, that didn't upload. Let's move on for now — you can add it later in Settings." });
    }
    setLoading(false);
    askOnboardStep(onboardIndex! + 1, onboardAnswers);
  };

  const skipLogo = (m: Msg) => {
    setMessages(p => p.filter(x => x.id !== m.id));
    push({ role: 'user', kind: 'text', text: 'Skip for now' });
    askOnboardStep(onboardIndex! + 1, onboardAnswers);
  };

  // ─── Setup ───────────────────────────────────────────────────────────────────

  useEffect(() => {
    loadSummary();
    api.getMe().then((u: any) => {
      setProfile(u);
      if (u?.role === 'owner' && !u?.onboarding_completed) {
        askOnboardStep(0, {});
      } else {
        push({ role: 'ozzy', kind: 'text', text: WELCOME_BACK_TEXT });
      }
    }).catch(() => {
      push({ role: 'ozzy', kind: 'text', text: WELCOME_BACK_TEXT });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { setTimeout(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), 80); }, [messages]);

  const firstNumber = (t: string) => { const m = t.replace(/,/g, '').match(/\d+(\.\d+)?/); return m ? parseFloat(m[0]) : 0; };

  const showConfirm = (d: Draft) => push({ role: 'ozzy', kind: 'confirm', draft: d });

  const answerQuery = async (msg: string) => {
    const s = await api.getReportSummary().catch(() => null);
    const sales = Number(s?.total_sales || 0), spent = Number(s?.total_expenses || 0);
    const profit = sales - spent;
    const q = msg.toLowerCase();
    if (q.includes('profit')) push({ role: 'ozzy', kind: 'text', text: `Today your profit is ${fmt(profit)} — you sold ${fmt(sales)} and spent ${fmt(spent)}.` });
    else if (q.includes('spent') || q.includes('expense')) push({ role: 'ozzy', kind: 'text', text: `You've spent ${fmt(spent)} today.` });
    else push({ role: 'ozzy', kind: 'text', text: `Today you've sold ${fmt(sales)}, spent ${fmt(spent)}, so your profit is ${fmt(profit)}.` });
  };

  const send = async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg) return;
    push({ role: 'user', kind: 'text', text: msg });
    setInput('');

    // Onboarding takes over the whole conversation until it's done.
    if (onboardIndex !== null) {
      if (awaitingFieldFor) {
        const field = awaitingFieldFor;
        setAwaitingFieldFor(null);
        setLoading(true);
        try { await patchMe({ [field]: msg }); } catch { /* not fatal */ }
        setLoading(false);
        if (field === 'contact_phone') askOnboardStep(onboardIndex + 1, onboardAnswers);
        else finishOnboarding(onboardAnswers);
        return;
      }
      const stepKey = ONBOARD_STEPS[onboardIndex];
      if (stepKey === 'logo' || stepKey === 'phone_confirm' || stepKey === 'email') {
        push({ role: 'ozzy', kind: 'text', text: 'You can use the buttons above to answer that one 🙂' });
        return;
      }
      await handleOnboardTextAnswer(msg);
      return;
    }

    setLoading(true);
    try {
      // waiting for an amount from a previous message
      if (pending) {
        const amt = firstNumber(msg);
        if (amt > 0) { const d = { ...pending, amount: amt, original: `${pending.original} ${msg}` }; setPending(null); showConfirm(d); }
        else push({ role: 'ozzy', kind: 'text', text: `How much was it? Just type the amount, like 5,000.` });
        return;
      }

      const res: any = await api.processChat(msg);
      const p = res.parsed || res;
      const intent = p.intent || p.type;
      const description = p.item || p.description || 'item';
      const amount = parseFloat(p.amount) || 0;
      const quantity = parseFloat(p.quantity) || 1;

      if (intent === 'query') { await answerQuery(msg); return; }

      // buying stock counts as money out (expense)
      const type: 'sale' | 'expense' = intent === 'sale' ? 'sale' : 'expense';

      if (amount > 0) {
        showConfirm({ type, description, amount, quantity, original: msg });
      } else {
        // no amount yet -> ask for it (guided)
        setPending({ type, description, amount: 0, quantity, original: msg });
        push({ role: 'ozzy', kind: 'text', text: `Got it — ${description}. How much was it?` });
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
    } catch { push({ role: 'ozzy', kind: 'text', text: `Couldn't save that. Please try again.` }); }
  };
  const confirmEdit = (m: Msg) => {
    setMessages(p => p.filter(x => x.id !== m.id));
    setInput(m.draft?.original || '');
    push({ role: 'ozzy', kind: 'text', text: `Sure — I've put it back below. Fix it and send again.` });
    document.getElementById('chat-input')?.focus();
  };

  const onKey = (e: React.KeyboardEvent) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } };

  return (
    <div className="h-screen flex flex-col relative overflow-hidden">
      {/* Summary strip */}
      <div className="z-30 px-lg py-md md:px-margin-desktop">
        <button onClick={() => navigate('/reports')} className="mx-auto flex items-center justify-center gap-xl bg-surface-container-low hover:bg-surface-container hover:shadow-sm cursor-pointer transition-all rounded-full px-xl py-4 border border-outline-variant/40">
          <span className="flex items-center gap-2 whitespace-nowrap">
            <Icon name="trending_up" className="text-[#1EBFA3] text-[22px]" />
            <span className="text-[15px] text-on-surface-variant">Today's sales</span>
            <span className="text-[16px] font-bold text-primary">{summary ? fmt(summary.total_sales) : '—'}</span>
          </span>
          <span className="w-px h-5 bg-outline-variant"></span>
          <span className="flex items-center gap-2 whitespace-nowrap">
            <Icon name="trending_down" className="text-outline text-[22px]" />
            <span className="text-[15px] text-on-surface-variant">Spent</span>
            <span className="text-[16px] font-bold text-on-surface">{summary ? fmt(summary.total_expenses) : '—'}</span>
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
            <div key={m.id} className="flex flex-col gap-sm items-start w-full">
              <div className="flex items-center gap-sm">
                <img src={ozzyLogo} alt="Ozzy" className="w-6 h-6 rounded-full object-cover" />
                <span className="font-label-md text-label-md text-outline">Ozzy</span>
              </div>

              {m.kind === 'confirm' && m.draft ? (
                <div className="bg-surface-container-high text-on-surface p-lg rounded-2xl rounded-tl-none w-full max-w-[420px] shadow-sm">
                  <p className="font-body-md text-body-md mb-md">Please confirm:</p>
                  <div className="bg-surface-container-lowest border border-outline-variant p-lg rounded-xl">
                    <div className="flex items-center gap-2 mb-lg">
                      <Icon name="check_circle" className="text-primary" />
                      <span className="text-[15px] font-bold text-primary">{m.draft.type === 'sale' ? 'Sale' : 'Expense'}</span>
                    </div>
                    <div className="flex justify-between items-center gap-6 py-md border-t border-b border-surface-container">
                      <span className="font-body-md text-body-md">{m.draft.description}{m.draft.quantity > 1 ? ` × ${m.draft.quantity}` : ''}</span>
                      <span className={`text-[16px] font-bold ${m.draft.type === 'sale' ? 'text-green-600' : 'text-red-600'}`}>{fmt(m.draft.amount)}</span>
                    </div>
                    <div className="flex gap-md mt-lg">
                      <button onClick={() => confirmYes(m)} className="flex-1 py-3.5 bg-primary text-white font-bold rounded-xl hover:opacity-90 active:scale-95 transition-all">Yes, record it</button>
                      <button onClick={() => confirmEdit(m)} className="px-5 py-3.5 border border-primary text-primary font-bold rounded-xl hover:bg-primary/5 active:scale-95 transition-all">Edit</button>
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
              ) : m.kind === 'onboard-choice' && m.choices ? (
                <div className="bg-surface-container-high text-on-surface p-lg rounded-2xl rounded-tl-none w-full max-w-[420px] shadow-sm">
                  <p className="font-body-md text-body-md mb-md">{m.text}</p>
                  <div className="flex flex-col gap-sm">
                    {m.choices.map(c => (
                      <button key={c.value} onClick={() => handleOnboardChoice(m, c.value)} className="w-full py-3 bg-primary text-white font-bold rounded-xl hover:opacity-90 active:scale-95 transition-all">{c.label}</button>
                    ))}
                  </div>
                </div>
              ) : m.kind === 'onboard-logo' ? (
                <div className="bg-surface-container-high text-on-surface p-lg rounded-2xl rounded-tl-none w-full max-w-[420px] shadow-sm">
                  <p className="font-body-md text-body-md mb-md">{m.text}</p>
                  <div className="flex gap-md">
                    <button onClick={() => fileInputRef.current?.click()} className="flex-1 py-3 bg-primary text-white font-bold rounded-xl hover:opacity-90 active:scale-95 transition-all">Upload a photo</button>
                    <button onClick={() => skipLogo(m)} className="px-5 py-3 border border-primary text-primary font-bold rounded-xl hover:bg-primary/5 active:scale-95 transition-all">Skip for now</button>
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

      <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleLogoFileChange} />

      {/* Input */}
      <div className="absolute bottom-0 left-0 w-full p-lg md:px-margin-desktop bg-gradient-to-t from-surface via-surface to-transparent pt-xxl">
        <div className="max-w-2xl mx-auto">
          {onboardIndex === null && (
            <div className="flex gap-sm mb-md overflow-x-auto pb-2 no-scrollbar">
              <button onClick={() => setInput('Sold ')} className="whitespace-nowrap px-lg py-2 bg-white border border-outline-variant rounded-full font-label-md text-label-md text-on-surface-variant hover:border-primary hover:text-primary transition-all shadow-sm">Record a sale</button>
              <button onClick={() => setInput('Paid ')} className="whitespace-nowrap px-lg py-2 bg-white border border-outline-variant rounded-full font-label-md text-label-md text-on-surface-variant hover:border-primary hover:text-primary transition-all shadow-sm">Record an expense</button>
              <button onClick={() => navigate('/inventory')} className="whitespace-nowrap px-lg py-2 bg-white border border-outline-variant rounded-full font-label-md text-label-md text-on-surface-variant hover:border-primary hover:text-primary transition-all shadow-sm">Check stock</button>
            </div>
          )}
          <div className="relative flex items-center group">
            <input id="chat-input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey} disabled={loading}
              className="w-full h-14 pl-lg pr-16 bg-white border border-outline-variant rounded-full text-body-md focus:ring-2 focus:ring-primary focus:border-transparent transition-all shadow-lg group-hover:shadow-xl outline-none"
              placeholder={onboardIndex !== null ? 'Type your answer…' : 'Type a message to Ozzy...'} type="text" />
            <button onClick={() => send()} disabled={loading} className="absolute right-2 w-10 h-10 bg-primary text-white rounded-full flex items-center justify-center hover:scale-105 active:scale-90 transition-all shadow-sm disabled:opacity-50">
              <Icon name="send" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
