import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

function Icon({ name, className = '', fill = false }: { name: string; className?: string; fill?: boolean }) {
  return <span className={`material-symbols-outlined ${className}`} style={fill ? { fontVariationSettings: "'FILL' 1" } : undefined}>{name}</span>;
}

type Period = 'today' | 'week' | 'month';

interface DailyPoint { label: string; date: string; sales: number; expenses: number; }
interface CategorySlice { category: string; amount: number; percent: number; }
interface BestSeller { name: string; units: number; revenue: number; }
interface Dashboard {
  period: Period;
  currency: string;
  total_sales: number;
  total_expenses: number;
  net_profit: number;
  sales_change_pct: number | null;
  expenses_change_pct: number | null;
  daily: DailyPoint[];
  category_breakdown: CategorySlice[];
  best_sellers: BestSeller[];
}

const DONUT_COLORS = ['#3F0071', '#744c9a', '#a97fd6', '#d5a9ff', '#ede1ff'];

function ChangeBadge({ pct, invert = false }: { pct: number | null; invert?: boolean }) {
  if (pct === null) return null;
  const good = invert ? pct <= 0 : pct >= 0;
  return (
    <span className={`text-xs font-bold px-2 py-1 rounded ${good ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50'}`}>
      {pct >= 0 ? '+' : ''}{pct.toFixed(1)}%
    </span>
  );
}

export default function Reports() {
  const [profile, setProfile] = useState<any>(null);
  const [period, setPeriod] = useState<Period>('month');
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [shareMsg, setShareMsg] = useState<string | null>(null);

  useEffect(() => { api.getMe().then(setProfile).catch(() => {}); }, []);

  const load = useCallback(async (p: Period) => {
    setLoading(true);
    setError(null);
    try {
      const d: any = await (api as any).request(`/reports/dashboard?period=${p}`);
      setData(d);
    } catch (e: any) {
      setError(e?.message?.includes('403') ? 'Reports are only available to the business owner.' : "Couldn't load your reports. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(period); }, [period, load]);

  const fmt = (n: number | string) => `${data?.currency || 'UGX'} ${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const token = localStorage.getItem('ozzy_access_token');
      const base = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1';
      const res = await fetch(`${base}/reports/dashboard/pdf?period=${period}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ozzy_report_${period}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setShareMsg("Couldn't download the PDF. Please try again.");
      setTimeout(() => setShareMsg(null), 3000);
    } finally {
      setDownloading(false);
    }
  };

  const shareReport = async () => {
    if (!data) return;
    const text = `My Ozzy for Business report (${period}): Sales ${fmt(data.total_sales)}, Spent ${fmt(data.total_expenses)}, Profit ${fmt(data.net_profit)}.`;
    if ((navigator as any).share) {
      try { await (navigator as any).share({ title: 'Ozzy Business Report', text }); } catch { /* user cancelled */ }
    } else {
      try {
        await navigator.clipboard.writeText(text);
        setShareMsg('Report summary copied to clipboard!');
      } catch {
        setShareMsg('Could not copy the report. Please try again.');
      }
      setTimeout(() => setShareMsg(null), 3000);
    }
  };

  if (profile?.role === 'worker') {
    return (
      <div className="min-h-screen flex items-center justify-center p-xl text-center">
        <div>
          <Icon name="lock" className="text-outline text-[40px]" />
          <p className="font-body-md text-body-md text-on-surface-variant mt-md">Reports are only available to the business owner.</p>
        </div>
      </div>
    );
  }

  const maxDaily = data ? Math.max(1, ...data.daily.map(d => Math.max(d.sales, d.expenses))) : 1;
  const bestDay = data && data.daily.length ? data.daily.reduce((a, b) => (b.sales > a.sales ? b : a)) : null;
  const topSeller = data?.best_sellers?.[0];
  const topSellerShare = data && topSeller && Number(data.total_sales) > 0 ? (Number(topSeller.revenue) / Number(data.total_sales)) * 100 : 0;

  return (
    <div className="min-h-screen p-md md:p-xl lg:p-xxl">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-xl gap-lg">
        <div>
          <h1 className="font-headline-lg text-headline-lg text-primary mb-2">See how your business is doing</h1>
          <div className="inline-flex p-1 bg-surface-container rounded-xl">
            {([['today', 'Today'], ['week', 'This Week'], ['month', 'This Month']] as [Period, string][]).map(([val, label]) => (
              <button key={val} onClick={() => setPeriod(val)}
                className={`px-md py-2 rounded-lg font-label-md text-label-md transition-all ${period === val ? 'bg-white text-primary shadow-sm' : 'hover:text-primary'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-md">
          <button onClick={downloadPdf} disabled={downloading || !data} className="flex items-center gap-2 px-lg py-3 border border-primary text-primary rounded-xl font-label-md text-label-md hover:bg-primary/5 transition-all active:scale-95 disabled:opacity-50">
            <Icon name="download" /> {downloading ? 'Preparing…' : 'Download PDF'}
          </button>
          <button onClick={shareReport} disabled={!data} className="flex items-center gap-2 px-lg py-3 bg-primary text-white rounded-xl font-label-md text-label-md hover:opacity-90 transition-all active:scale-95 disabled:opacity-50">
            <Icon name="share" /> Share Report
          </button>
        </div>
      </div>

      {shareMsg && (
        <div className="mb-lg p-md bg-surface-container rounded-lg text-on-surface-variant text-sm">{shareMsg}</div>
      )}

      {error ? (
        <div className="p-xl bg-white rounded-xl border border-outline-variant text-center text-on-surface-variant">{error}</div>
      ) : loading || !data ? (
        <div className="p-xl bg-white rounded-xl border border-outline-variant text-center text-on-surface-variant">Loading your report…</div>
      ) : (
        <div className="bento-grid">
          {/* Summary cards */}
          <div className="col-span-12 md:col-span-4 bg-white p-lg rounded-xl border border-outline-variant hover:shadow-sm transition-shadow">
            <div className="flex justify-between items-start mb-md">
              <div className="p-2 bg-primary-container/20 rounded-lg"><Icon name="trending_up" className="text-primary" /></div>
              <ChangeBadge pct={data.sales_change_pct} />
            </div>
            <p className="font-label-md text-label-md text-outline uppercase tracking-wider mb-1">Total Sales</p>
            <h2 className="font-headline-md text-headline-md text-primary">{fmt(data.total_sales)}</h2>
          </div>
          <div className="col-span-12 md:col-span-4 bg-white p-lg rounded-xl border border-outline-variant hover:shadow-sm transition-shadow">
            <div className="flex justify-between items-start mb-md">
              <div className="p-2 bg-secondary-container/20 rounded-lg"><Icon name="payments" className="text-secondary" /></div>
              <ChangeBadge pct={data.expenses_change_pct} invert />
            </div>
            <p className="font-label-md text-label-md text-outline uppercase tracking-wider mb-1">Money Spent</p>
            <h2 className="font-headline-md text-headline-md text-on-surface">{fmt(data.total_expenses)}</h2>
          </div>
          <div className="col-span-12 md:col-span-4 bg-white p-lg rounded-xl border border-outline-variant hover:shadow-sm transition-shadow">
            <div className="flex justify-between items-start mb-md">
              <div className="p-2 bg-on-tertiary-container/10 rounded-lg"><Icon name="account_balance_wallet" className="text-tertiary-container" /></div>
            </div>
            <p className="font-label-md text-label-md text-outline uppercase tracking-wider mb-1">Money Left</p>
            <h2 className="font-headline-md text-headline-md text-on-surface">{fmt(data.net_profit)}</h2>
          </div>

          {/* Weekly bar chart */}
          <div className="col-span-12 lg:col-span-8 bg-white p-lg rounded-xl border border-outline-variant">
            <div className="flex justify-between items-center mb-xl">
              <h3 className="font-headline-md text-primary">Weekly Performance</h3>
              <div className="flex items-center gap-2 text-outline font-label-md"><span className="w-3 h-3 bg-primary rounded-full"></span> Sales</div>
            </div>
            <div className="h-64 flex items-end justify-between gap-sm px-md pb-md border-b border-outline-variant">
              {data.daily.map(d => (
                <div key={d.date} className="flex-1 flex flex-col items-center gap-sm">
                  <div className="chart-bar w-full max-w-[48px] bg-primary rounded-t-lg" style={{ height: `${Math.max(4, (d.sales / maxDaily) * 100)}%` }}></div>
                  <span className="text-xs font-label-md text-outline">{d.label}</span>
                </div>
              ))}
            </div>
            <div className="mt-md p-md bg-surface-container rounded-lg flex items-start gap-md">
              <Icon name="info" className="text-primary" fill />
              <p className="font-body-md text-on-surface-variant">
                {bestDay && bestDay.sales > 0 ? (
                  <>Highest sales on <span className="font-bold text-primary">{bestDay.label}</span> this week{topSeller ? <> — <span className="font-bold text-primary">{topSeller.name}</span> is your top seller, making up {topSellerShare.toFixed(0)}% of this period's revenue.</> : '.'}</>
                ) : (
                  <>No sales recorded in the last 7 days yet — once you record some in Chat, this chart fills in automatically.</>
                )}
              </p>
            </div>
          </div>

          {/* Donut */}
          <div className="col-span-12 lg:col-span-4 bg-white p-lg rounded-xl border border-outline-variant">
            <h3 className="font-headline-md text-primary mb-xl">Category Mix</h3>
            {data.category_breakdown.length === 0 ? (
              <p className="font-body-md text-on-surface-variant text-center py-xl">No expenses recorded this period yet.</p>
            ) : (
              <div className="flex flex-col items-center gap-xl">
                <div className="relative w-48 h-48">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <circle cx="18" cy="18" fill="transparent" r="16" stroke="#f0edec" strokeWidth="4"></circle>
                    {(() => {
                      let offset = 0;
                      return data.category_breakdown.map((s, i) => {
                        const dash = `${s.percent} ${100 - s.percent}`;
                        const el = (
                          <circle key={s.category} className="donut-segment" cx="18" cy="18" fill="transparent" r="16"
                            stroke={DONUT_COLORS[i % DONUT_COLORS.length]} strokeDasharray={dash} strokeDashoffset={-offset} strokeWidth="4"></circle>
                        );
                        offset += s.percent;
                        return el;
                      });
                    })()}
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="font-headline-md text-primary">{fmt(data.total_expenses)}</span>
                    <span className="text-xs text-outline">Spent</span>
                  </div>
                </div>
                <div className="w-full flex flex-col gap-sm">
                  {data.category_breakdown.map((s, i) => (
                    <div key={s.category} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: DONUT_COLORS[i % DONUT_COLORS.length] }}></div>
                        <span className="font-label-md text-on-surface">{s.category}</span>
                      </div>
                      <span className="font-bold text-primary">{s.percent.toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Best selling */}
          <div className="col-span-12 bg-white p-lg rounded-xl border border-outline-variant">
            <div className="flex justify-between items-center mb-lg">
              <h3 className="font-headline-md text-primary">Best Selling Products</h3>
            </div>
            {data.best_sellers.length === 0 ? (
              <p className="font-body-md text-on-surface-variant text-center py-xl">No sales recorded this period yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-outline-variant">
                      <th className="pb-md font-label-md text-outline uppercase tracking-wider">Product</th>
                      <th className="pb-md font-label-md text-outline uppercase tracking-wider text-right">Units Sold</th>
                      <th className="pb-md font-label-md text-outline uppercase tracking-wider text-right">Revenue</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant">
                    {data.best_sellers.map(p => (
                      <tr key={p.name} className="group hover:bg-surface-container-low transition-colors">
                        <td className="py-md flex items-center gap-md">
                          <div className="w-12 h-12 bg-surface-container rounded-lg flex items-center justify-center overflow-hidden">
                            <Icon name="inventory_2" className="text-outline" />
                          </div>
                          <p className="font-bold text-primary">{p.name}</p>
                        </td>
                        <td className="py-md text-right font-bold">{Number(p.units).toLocaleString()}</td>
                        <td className="py-md text-right font-bold text-primary">{fmt(p.revenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
