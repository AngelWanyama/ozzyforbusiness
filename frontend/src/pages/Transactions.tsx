import { useState, useEffect } from 'react';
import api from '../api/client';

function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

interface Txn {
  id?: string | number;
  type?: string;
  intent?: string;
  description?: string;
  item?: string;
  category?: string;
  amount?: number | string;
  quantity?: number;
  created_at?: string;
  date?: string;
}

type DateRange = 'all' | 'today' | 'week' | 'month';

export default function Transactions() {
  const [txns, setTxns] = useState<Txn[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [cur, setCur] = useState('UGX');
  const [range, setRange] = useState<DateRange>('all');
  const [filterOpen, setFilterOpen] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    api.getReportSummary().then((s: any) => { if (s?.currency) setCur(s.currency); }).catch(() => {});
    api.getTransactions()
      .then((res: any) => {
        const items = res?.items || res || [];
        setTxns(Array.isArray(items) ? items : []);
      })
      .catch(() => setError("Couldn't load your activity. Please try again."))
      .finally(() => setLoading(false));
  }, []);

  const isInflow = (t: Txn) => (t.type || t.intent) === 'sale';
  const titleOf = (t: Txn) => t.description || t.item || 'Transaction';
  const catOf = (t: Txn) => t.category || '';
  const dateOf = (t: Txn) => new Date(t.created_at || t.date || Date.now());
  const amountOf = (t: Txn) => Number(t.amount || 0);
  const qtyOf = (t: Txn) => Number(t.quantity || 0);
  const money = (n: number) => `${cur} ${Number(n || 0).toLocaleString()}`;

  // Warm, plain-language explanation using only real data
  const explain = (t: Txn) => {
    const name = titleOf(t);
    const total = amountOf(t);
    const qty = qtyOf(t);
    if (isInflow(t)) {
      if (qty > 1) {
        const each = Math.round(total / qty);
        return `You sold ${qty} ${name}, each at ${money(each)}. That brought in ${money(total)}.`;
      }
      return `You sold ${name}. That brought in ${money(total)}.`;
    } else {
      if (qty > 1) {
        const each = Math.round(total / qty);
        return `You bought ${qty} ${name}, each at ${money(each)}. Money went out: ${money(total)}.`;
      }
      return `You bought ${name}. Money went out: ${money(total)}.`;
    }
  };

  const matchesSearch = (t: Txn) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    const dateStr = dateOf(t).toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' }).toLowerCase();
    const haystack = [titleOf(t).toLowerCase(), catOf(t).toLowerCase(), String(amountOf(t)), amountOf(t).toLocaleString(), dateStr].join(' ');
    return haystack.includes(q);
  };

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 86400000;
  const startOfWeek = startOfToday - 6 * 86400000;
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1).getTime();

  const matchesRange = (t: Txn) => {
    const d = dateOf(t).getTime();
    if (range === 'today') return d >= startOfToday;
    if (range === 'week') return d >= startOfWeek;
    if (range === 'month') return d >= startOfMonth;
    return true;
  };

  const filtered = txns.filter(t => matchesSearch(t) && matchesRange(t));

  const today: Txn[] = [];
  const yesterday: Txn[] = [];
  const earlier: Txn[] = [];
  [...filtered]
    .sort((a, b) => dateOf(b).getTime() - dateOf(a).getTime())
    .forEach(t => {
      const d = dateOf(t).getTime();
      if (d >= startOfToday) today.push(t);
      else if (d >= startOfYesterday) yesterday.push(t);
      else earlier.push(t);
    });

  const timeLabel = (t: Txn) => dateOf(t).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const rowKey = (t: Txn, i: number) => String(t.id ?? `${titleOf(t)}-${i}`);

  const Row = ({ t, k }: { t: Txn; k: string }) => {
    const inflow = isInflow(t);
    const open = expanded === k;
    return (
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant hover:bg-surface-container-low transition-colors overflow-hidden">
        <button
          onClick={() => setExpanded(open ? null : k)}
          className="w-full flex items-center p-md text-left active:scale-[0.99] duration-200 ease-out-expo"
        >
          <div className={`w-12 h-12 rounded-full flex items-center justify-center mr-md ${inflow ? 'bg-green-100' : 'bg-red-100'}`}>
            <Icon name={inflow ? 'arrow_upward' : 'arrow_downward'} className={inflow ? 'text-green-600' : 'text-red-600'} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-on-surface truncate">{titleOf(t)}</p>
            <p className="text-sm text-on-surface-variant truncate">{timeLabel(t)}</p>
          </div>
          <div className="text-right ml-sm flex items-center gap-1">
            <p className={`font-bold ${inflow ? 'text-green-600' : 'text-red-600'}`}>
              {inflow ? '+' : '-'}{money(amountOf(t))}
            </p>
            <Icon name={open ? 'expand_less' : 'expand_more'} className="text-outline" />
          </div>
        </button>
        {open && (
          <div className="px-md pb-md pt-0">
            <div className="bg-surface-container-low rounded-lg p-md">
              <p className="font-body-md text-body-md text-on-surface">{explain(t)}</p>
              {catOf(t) && (
                <p className="mt-2 font-label-md text-label-md text-outline">Category: {catOf(t)}</p>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const Group = ({ title, list }: { title: string; list: Txn[] }) => (
    <div>
      <h3 className="font-label-md text-label-md text-outline uppercase tracking-wider mb-sm">{title}</h3>
      <div className="space-y-xs">
        {list.map((t, i) => { const k = rowKey(t, i); return <Row key={k} t={t} k={k} />; })}
      </div>
    </div>
  );

  const rangeLabels: Record<DateRange, string> = { all: 'All time', today: 'Today', week: 'This week', month: 'This month' };

  return (
    <div className="min-h-screen p-md md:p-xl lg:p-xxl">
      <div className="max-w-[900px] mx-auto">
        <h2 className="font-headline-lg text-headline-lg text-primary mb-md">Activities</h2>

        <div className="flex items-center gap-sm mb-lg">
          <div className="relative flex-1">
            <Icon name="search" className="absolute left-4 top-1/2 -translate-y-1/2 text-outline" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full h-[52px] pl-12 pr-4 bg-surface-container-low rounded-lg border-none focus:ring-2 focus:ring-primary-container transition-all font-body-md outline-none"
              placeholder="Search by item, amount, date, or category..."
              type="text"
            />
          </div>
          <div className="relative">
            <button
              onClick={() => setFilterOpen(o => !o)}
              className={`h-[52px] w-[52px] flex items-center justify-center rounded-lg active:scale-95 duration-200 ease-out-expo transition-colors ${range !== 'all' ? 'bg-primary text-white' : 'bg-surface-container-low text-on-surface-variant'}`}
            >
              <Icon name="tune" />
            </button>
            {filterOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-lg z-40 overflow-hidden">
                <p className="px-lg pt-md pb-xs font-label-md text-label-md text-outline uppercase tracking-wider">Date range</p>
                {(['today', 'week', 'month', 'all'] as DateRange[]).map(r => (
                  <button
                    key={r}
                    onClick={() => { setRange(r); setFilterOpen(false); }}
                    className={`w-full text-left px-lg py-3 font-body-md hover:bg-surface-container-low transition-colors ${range === r ? 'text-primary font-bold' : 'text-on-surface'}`}
                  >
                    {rangeLabels[r]}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {range !== 'all' && (
          <div className="mb-lg flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-md py-1 bg-primary-container text-primary rounded-full font-label-md text-label-md">
              {rangeLabels[range]}
              <button onClick={() => setRange('all')} className="ml-1"><Icon name="close" className="text-[16px]" /></button>
            </span>
          </div>
        )}

        {loading ? (
          <p className="text-center text-on-surface-variant py-xxl">Loading your activity...</p>
        ) : error ? (
          <p className="text-center text-red-600 py-xxl">{error}</p>
        ) : filtered.length === 0 ? (
          <div className="text-center py-xxl">
            <Icon name="receipt_long" className="text-outline text-[48px]" />
            <p className="font-body-md text-on-surface-variant mt-md">
              {search || range !== 'all' ? 'No transactions match your search or filter.' : 'No activity yet. Record your first sale or expense in Chat.'}
            </p>
          </div>
        ) : (
          <div className="space-y-xl">
            {today.length > 0 && <Group title="Today" list={today} />}
            {yesterday.length > 0 && <Group title="Yesterday" list={yesterday} />}
            {earlier.length > 0 && <Group title="Earlier" list={earlier} />}
          </div>
        )}
      </div>
    </div>
  );
}
