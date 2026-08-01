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
  amount?: number | string;
  quantity?: number;
  created_at?: string;
  date?: string;
}

function Item({ inflow, title, sub, amount, cur }: { inflow: boolean; title: string; sub: string; amount: number; cur: string }) {
  const fmt = `${inflow ? '+' : '-'}${cur} ${Number(amount || 0).toLocaleString()}`;
  return (
    <div className="flex items-center p-md bg-surface-container-lowest rounded-xl border border-outline-variant hover:bg-surface-container-low transition-colors group cursor-pointer active:scale-[0.98] duration-200 ease-out-expo">
      <div className={`w-12 h-12 rounded-full flex items-center justify-center mr-md ${inflow ? 'bg-green-100' : 'bg-red-100'}`}>
        <Icon name={inflow ? 'arrow_upward' : 'arrow_downward'} className={inflow ? 'text-green-600' : 'text-red-600'} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-on-surface truncate">{title}</p>
        <p className="text-sm text-on-surface-variant truncate">{sub}</p>
      </div>
      <div className="text-right ml-sm">
        <p className={`font-bold ${inflow ? 'text-green-600' : 'text-red-600'}`}>{fmt}</p>
      </div>
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="font-label-md text-label-md text-outline uppercase tracking-wider mb-sm">{title}</h3>
      <div className="space-y-xs">{children}</div>
    </div>
  );
}

export default function Transactions() {
  const [txns, setTxns] = useState<Txn[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [cur, setCur] = useState('UGX');

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
  const dateOf = (t: Txn) => new Date(t.created_at || t.date || Date.now());
  const amountOf = (t: Txn) => Number(t.amount || 0);

  const filtered = txns.filter(t => titleOf(t).toLowerCase().includes(search.toLowerCase()));

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 86400000;

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

  const timeLabel = (t: Txn) =>
    dateOf(t).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

  const renderItems = (list: Txn[]) =>
    list.map((t, i) => (
      <Item
        key={t.id ?? i}
        inflow={isInflow(t)}
        title={titleOf(t)}
        sub={timeLabel(t)}
        amount={amountOf(t)}
        cur={cur}
      />
    ));

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
              placeholder="Search transactions..."
              type="text"
            />
          </div>
          <button className="h-[52px] w-[52px] flex items-center justify-center bg-surface-container-low rounded-lg active:scale-95 duration-200 ease-out-expo transition-colors">
            <Icon name="tune" className="text-on-surface-variant" />
          </button>
        </div>

        {loading ? (
          <p className="text-center text-on-surface-variant py-xxl">Loading your activity...</p>
        ) : error ? (
          <p className="text-center text-red-600 py-xxl">{error}</p>
        ) : filtered.length === 0 ? (
          <div className="text-center py-xxl">
            <Icon name="receipt_long" className="text-outline text-[48px]" />
            <p className="font-body-md text-on-surface-variant mt-md">
              {search ? 'No transactions match your search.' : 'No activity yet. Record your first sale or expense in Chat.'}
            </p>
          </div>
        ) : (
          <div className="space-y-xl">
            {today.length > 0 && <Group title="Today">{renderItems(today)}</Group>}
            {yesterday.length > 0 && <Group title="Yesterday">{renderItems(yesterday)}</Group>}
            {earlier.length > 0 && <Group title="Earlier">{renderItems(earlier)}</Group>}
          </div>
        )}
      </div>
    </div>
  );
}
