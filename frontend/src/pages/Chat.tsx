import { useState, useEffect, useRef } from 'react';
import api from '../api/client';
import ozzyLogo from '../assets/ozzy-icon-logo.png';
import { useNavigate } from 'react-router-dom';

function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

interface Draft { type: 'sale' | 'expense'; description: string; amount: number; quantity: number; category?: string; original: string; }

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

  const [scanning, setScanning] = useState(false);
  const [chips, setChips] = useState<string[]>(['Record a sale', 'Record an expense', 'Check stock']);

  const [recording, setRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [transcribing, setTranscribing] = useState(false);

  const endRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const receiptInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const recordTimerRef = useRef<number | null>(null);
  const silenceRafRef = useRef<number | null>(null);
  const initializedRef = useRef(false);
  const navigate = useNavigate();

  const cur = summary?.currency || 'UGX';
  const fmt = (n: number | string) => `${cur} ${Number(n || 0).toLocaleString()}`;

  // Today's totals for the summary strip — owners only (Workers can't see profit/totals).
  // Cast to bypass client.ts's typed method list rather than widen a shared file mid-flight.
  const loadSummary = () => (api as any).request('/reports/dashboard?period=today').then(setSummary).catch(() => {});
  const push = (m: Omit<Msg, 'id'>) => setMessages(p => [...p, { ...m, id: Date.now() + '' + Math.random() }]);

  // Saves one profile field immediately, as each onboarding answer comes in.
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

  const scanReceiptFile = async (file: File) => {
    const token = localStorage.getItem('ozzy_access_token');
    const base = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1';
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${base}/chat/scan-receipt`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) throw new Error('Scan failed');
    return res.json();
  };

  // "today" / "yesterday" / weekday name / full date — whichever reads most naturally.
  const describeDate = (isoDate: string): string => {
    const d = new Date(isoDate + 'T00:00:00');
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const diffDays = Math.round((today.getTime() - d.getTime()) / 86400000);
    if (diffDays === 0) return 'today';
    if (diffDays === 1) return 'yesterday';
    if (diffDays > 1 && diffDays < 7) return `on ${d.toLocaleDateString([], { weekday: 'long' })}`;
    return `on ${d.toLocaleDateString()}`;
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

  const handleReceiptFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    if (!['image/png', 'image/jpeg', 'image/jpg', 'image/webp'].includes(file.type)) {
      push({ role: 'ozzy', kind: 'text', text: 'That needs to be a PNG, JPEG, or WEBP photo — could you try another one?' });
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      push({ role: 'ozzy', kind: 'text', text: 'That photo is a bit large — please use one under 8MB.' });
      return;
    }

    push({ role: 'user', kind: 'text', text: `📷 ${file.name}` });
    setScanning(true);
    try {
      const scan: any = await scanReceiptFile(file);
      const amount = Number(scan.amount) || 0;
      if (amount <= 0) {
        push({ role: 'ozzy', kind: 'text', text: `I had trouble reading that receipt clearly. Could you try a clearer photo, or just type the expense instead?` });
        return;
      }
      const when = describeDate(scan.transaction_date);
      const vendorPart = scan.vendor && scan.vendor !== 'Unknown' ? ` at ${scan.vendor}` : '';
      push({
        role: 'ozzy', kind: 'text',
        text: `I see ${fmt(amount)} spent on ${scan.item}${vendorPart} ${when}, is that right?`,
      });
      showConfirm({
        type: 'expense',
        description: scan.item || 'expense',
        amount,
        quantity: 1,
        category: scan.category,
        original: `${scan.item} ${amount}`,
      });
    } catch {
      push({ role: 'ozzy', kind: 'text', text: `Sorry, I couldn't read that receipt. Please try again or type the expense instead.` });
    } finally {
      setScanning(false);
    }
  };

  // ─── Setup ───────────────────────────────────────────────────────────────────

  // Maps a greeting/quick-action chip's label to what tapping it should do.
  const runChip = (label: string) => {
    const l = label.toLowerCase();
    if (l.includes('sale')) { setInput('Sold '); return; }
    if (l.includes('expense')) { setInput('Paid '); return; }
    if (l.includes('stock')) { navigate('/inventory'); return; }
    if (l.includes('invoice')) { navigate('/invoices'); return; }
    if (l.includes('report')) { navigate('/reports'); return; }
    if (l.includes('activity') || l.includes('yesterday')) { navigate('/transactions'); return; }
    setInput(label);
  };

  const loadGreeting = () => (api as any).request('/chat/greeting')
    .then((g: any) => {
      push({ role: 'ozzy', kind: 'text', text: g.text });
      if (Array.isArray(g.chips) && g.chips.length) setChips(g.chips);
    })
    .catch(() => push({ role: 'ozzy', kind: 'text', text: WELCOME_BACK_TEXT }));

  useEffect(() => {
    // Guards against the greeting/onboarding being fetched and pushed twice — React 18's
    // StrictMode intentionally mounts, unmounts, and remounts this effect once in development,
    // which otherwise double-fires this one-time initial load.
    if (initializedRef.current) return;
    initializedRef.current = true;

    api.getMe().then((u: any) => {
      setProfile(u);
      if (u?.role === 'owner') loadSummary(); // Workers can't see profit/totals, so skip it entirely for them.
      if (u?.role === 'owner' && !u?.onboarding_completed) {
        askOnboardStep(0, {});
      } else {
        loadGreeting();
      }
    }).catch(() => {
      push({ role: 'ozzy', kind: 'text', text: WELCOME_BACK_TEXT });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { setTimeout(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), 80); }, [messages]);

  // Never leave the microphone running if the user navigates away mid-recording.
  useEffect(() => () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') mediaRecorderRef.current.stop();
    if (audioCtxRef.current) audioCtxRef.current.close().catch(() => {});
    if (recordTimerRef.current) clearInterval(recordTimerRef.current);
    if (silenceRafRef.current) cancelAnimationFrame(silenceRafRef.current);
  }, []);

  const firstNumber = (t: string) => { const m = t.replace(/,/g, '').match(/\d+(\.\d+)?/); return m ? parseFloat(m[0]) : 0; };

  const showConfirm = (d: Draft) => push({ role: 'ozzy', kind: 'confirm', draft: d });

  // Shared by typed and voice messages: given the chat engine's { reply, action, draft }
  // response, decide whether to show a Yes/No confirm card, ask for a missing amount, or just
  // display the reply text.
  const applyChatResult = (res: any, originalText: string) => {
    if (res.action === 'confirm_sale' || res.action === 'confirm_expense') {
      const type: 'sale' | 'expense' = res.action === 'confirm_sale' ? 'sale' : 'expense';
      const d = res.draft || {};
      showConfirm({ type, description: d.description || 'item', amount: parseFloat(d.amount) || 0, quantity: parseFloat(d.quantity) || 1, category: d.category, original: originalText });
    } else if (res.action === 'need_amount') {
      const d = res.draft || {};
      setPending({ type: d.type === 'expense' ? 'expense' : 'sale', description: d.description || 'item', amount: 0, quantity: parseFloat(d.quantity) || 1, category: d.category, original: originalText });
      push({ role: 'ozzy', kind: 'text', text: res.reply || `Got it. How much was it?` });
    } else {
      push({ role: 'ozzy', kind: 'text', text: res.reply || `Sorry, I didn't quite catch that — could you rephrase?` });
    }
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

      // The backend now runs real tool-calling (record_sale, record_expense, get_summary,
      // get_inventory, create_invoice/receipt, list_low_stock) instead of a fixed classifier,
      // so it decides for itself what to do and just tells us which UI action to show.
      const res: any = await api.processChat(msg);
      applyChatResult(res, msg);
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
      await api.createTransaction({ type: m.draft.type, amount: m.draft.amount, description: m.draft.description, quantity: m.draft.quantity, category: m.draft.category });
      push({ role: 'ozzy', kind: 'recorded', draft: m.draft });
      if (profile?.role === 'owner') loadSummary();
    } catch { push({ role: 'ozzy', kind: 'text', text: `Couldn't save that. Please try again.` }); }
  };
  const confirmEdit = (m: Msg) => {
    setMessages(p => p.filter(x => x.id !== m.id));
    setInput(m.draft?.original || '');
    push({ role: 'ozzy', kind: 'text', text: `Sure — I've put it back below. Fix it and send again.` });
    document.getElementById('chat-input')?.focus();
  };

  const onKey = (e: React.KeyboardEvent) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } };

  // ─── Voice input ─────────────────────────────────────────────────────────────

  const cleanupRecording = () => {
    if (recordTimerRef.current) { clearInterval(recordTimerRef.current); recordTimerRef.current = null; }
    if (silenceRafRef.current) { cancelAnimationFrame(silenceRafRef.current); silenceRafRef.current = null; }
    if (audioCtxRef.current) { audioCtxRef.current.close().catch(() => {}); audioCtxRef.current = null; }
  };

  // Auto-stops the recording after a short pause in speech, so the user doesn't have to
  // remember to tap again — but tapping the mic again still stops it immediately too.
  const watchForSilence = (stream: MediaStream) => {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    const audioCtx = new AudioCtx();
    audioCtxRef.current = audioCtx;
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);
    const SILENCE_LEVEL = 10;
    const SILENCE_MS = 1600;
    let lastLoudAt = Date.now();

    const check = () => {
      if (!mediaRecorderRef.current || mediaRecorderRef.current.state === 'inactive') return;
      analyser.getByteFrequencyData(data);
      const avg = data.reduce((a, b) => a + b, 0) / data.length;
      const now = Date.now();
      if (avg > SILENCE_LEVEL) lastLoudAt = now;
      else if (now - lastLoudAt > SILENCE_MS) { stopRecording(); return; }
      silenceRafRef.current = requestAnimationFrame(check);
    };
    silenceRafRef.current = requestAnimationFrame(check);
  };

  const startRecording = async () => {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      push({ role: 'ozzy', kind: 'text', text: "I need microphone access to hear you — please allow microphone permission for this site in your browser, then try again." });
      return;
    }

    const recorder = new MediaRecorder(stream);
    mediaRecorderRef.current = recorder;
    audioChunksRef.current = [];
    recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      cleanupRecording();
      setRecording(false);
      const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      if (blob.size < 800) {
        push({ role: 'ozzy', kind: 'text', text: "I didn't catch any audio there — please try recording again." });
        return;
      }
      await sendVoice(blob);
    };

    recorder.start();
    setRecording(true);
    setRecordSeconds(0);
    recordTimerRef.current = window.setInterval(() => setRecordSeconds(s => s + 1), 1000);
    watchForSilence(stream);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  };

  const toggleRecording = () => { if (recording) stopRecording(); else startRecording(); };

  const sendVoice = async (blob: Blob) => {
    setTranscribing(true);
    try {
      const token = localStorage.getItem('ozzy_access_token');
      const base = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1';
      const form = new FormData();
      form.append('file', blob, 'recording.webm');
      const res = await fetch(`${base}/chat/voice`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      });
      const data = await res.json();
      if (!res.ok) {
        push({ role: 'ozzy', kind: 'text', text: data.detail || "Sorry, I couldn't hear that clearly. Please try again." });
        return;
      }
      push({ role: 'user', kind: 'text', text: data.transcript });
      applyChatResult(data, data.transcript);
    } catch {
      push({ role: 'ozzy', kind: 'text', text: "Sorry, something went wrong sending your recording. Please try again." });
    } finally {
      setTranscribing(false);
    }
  };

  return (
    <div className="h-screen flex flex-col relative overflow-hidden">
      {/* Summary strip — owners only; Workers can't see profit/totals */}
      {profile?.role !== 'worker' && (
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
      )}

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

          {(loading || scanning || transcribing) && (
            <div className="flex items-center gap-2 text-outline">
              <div className="w-2 h-2 bg-outline rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-outline rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-outline rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              {scanning && <span className="text-sm">Reading your receipt…</span>}
              {transcribing && <span className="text-sm">Listening to your recording…</span>}
            </div>
          )}
          <div ref={endRef} />
        </div>
      </section>

      <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleLogoFileChange} />
      <input ref={receiptInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleReceiptFileChange} />

      {/* Input */}
      <div className="absolute bottom-0 left-0 w-full p-lg md:px-margin-desktop bg-gradient-to-t from-surface via-surface to-transparent pt-xxl">
        <div className="max-w-2xl mx-auto">
          {onboardIndex === null && (
            <div className="flex gap-sm mb-md overflow-x-auto pb-2 no-scrollbar">
              {chips.map(label => (
                <button key={label} onClick={() => runChip(label)} className="whitespace-nowrap px-lg py-2 bg-white border border-outline-variant rounded-full font-label-md text-label-md text-on-surface-variant hover:border-primary hover:text-primary transition-all shadow-sm">{label}</button>
              ))}
              <button onClick={() => receiptInputRef.current?.click()} disabled={scanning} className="whitespace-nowrap flex items-center gap-1 px-lg py-2 bg-white border border-outline-variant rounded-full font-label-md text-label-md text-on-surface-variant hover:border-primary hover:text-primary transition-all shadow-sm disabled:opacity-50">
                <Icon name="photo_camera" className="text-[16px]" /> {scanning ? 'Reading receipt…' : 'Scan a receipt'}
              </button>
            </div>
          )}
          <div className="relative flex items-center group">
            {recording ? (
              <button onClick={toggleRecording} className="w-full h-14 pl-lg pr-lg bg-white border-2 border-red-400 rounded-full flex items-center gap-3 shadow-lg">
                <span className="relative flex w-3 h-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
                </span>
                <span className="font-body-md text-body-md text-on-surface">
                  Recording… {String(Math.floor(recordSeconds / 60)).padStart(1, '0')}:{String(recordSeconds % 60).padStart(2, '0')} — tap to stop
                </span>
              </button>
            ) : (
              <>
                <input id="chat-input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey} disabled={loading || transcribing}
                  className="w-full h-14 pl-lg pr-28 bg-white border border-outline-variant rounded-full text-body-md focus:ring-2 focus:ring-primary focus:border-transparent transition-all shadow-lg group-hover:shadow-xl outline-none"
                  placeholder={onboardIndex !== null ? 'Type your answer…' : transcribing ? 'Listening to your recording…' : 'Type a message to Ozzy...'} type="text" />
                {onboardIndex === null && (
                  <button onClick={toggleRecording} disabled={loading || transcribing} title="Record a voice message"
                    className="absolute right-14 w-10 h-10 text-on-surface-variant hover:text-primary rounded-full flex items-center justify-center hover:scale-105 active:scale-90 transition-all disabled:opacity-50">
                    <Icon name={transcribing ? 'hourglass_empty' : 'mic'} />
                  </button>
                )}
                <button onClick={() => send()} disabled={loading || transcribing} className="absolute right-2 w-10 h-10 bg-primary text-white rounded-full flex items-center justify-center hover:scale-105 active:scale-90 transition-all shadow-sm disabled:opacity-50">
                  <Icon name="send" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
