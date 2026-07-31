function Icon({ name, className = '', fill = false }: { name: string; className?: string; fill?: boolean }) {
  return <span className={`material-symbols-outlined ${className}`} style={fill ? { fontVariationSettings: "'FILL' 1" } : undefined}>{name}</span>;
}

const bars = [
  { d: 'Mon', h: '60%', c: 'bg-primary' },
  { d: 'Tue', h: '45%', c: 'bg-primary' },
  { d: 'Wed', h: '80%', c: 'bg-primary' },
  { d: 'Thu', h: '35%', c: 'bg-primary' },
  { d: 'Fri', h: '95%', c: 'bg-primary-container/40' },
  { d: 'Sat', h: '70%', c: 'bg-primary' },
  { d: 'Sun', h: '55%', c: 'bg-primary' },
];

export default function Reports() {
  return (
    <div className="min-h-screen p-md md:p-xl lg:p-xxl">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-xl gap-lg">
        <div>
          <h1 className="font-headline-lg text-headline-lg text-primary mb-2">See how your business is doing</h1>
          <div className="inline-flex p-1 bg-surface-container rounded-xl">
            <button className="px-md py-2 rounded-lg font-label-md text-label-md transition-all hover:text-primary">Today</button>
            <button className="px-md py-2 rounded-lg font-label-md text-label-md transition-all hover:text-primary">This Week</button>
            <button className="px-md py-2 rounded-lg font-label-md text-label-md bg-white text-primary shadow-sm">This Month</button>
          </div>
        </div>
        <div className="flex items-center gap-md">
          <button className="flex items-center gap-2 px-lg py-3 border border-primary text-primary rounded-xl font-label-md text-label-md hover:bg-primary/5 transition-all active:scale-95 ease-out-expo">
            <Icon name="download" /> Download PDF
          </button>
          <button className="flex items-center gap-2 px-lg py-3 bg-primary text-white rounded-xl font-label-md text-label-md hover:opacity-90 transition-all active:scale-95 ease-out-expo">
            <Icon name="share" /> Share Report
          </button>
        </div>
      </div>

      {/* Grid */}
      <div className="bento-grid">
        {/* Summary cards */}
        <div className="col-span-12 md:col-span-4 bg-white p-lg rounded-xl border border-outline-variant hover:shadow-sm transition-shadow">
          <div className="flex justify-between items-start mb-md">
            <div className="p-2 bg-primary-container/20 rounded-lg"><Icon name="trending_up" className="text-primary" /></div>
            <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded">+12.4%</span>
          </div>
          <p className="font-label-md text-label-md text-outline uppercase tracking-wider mb-1">Total Sales</p>
          <h2 className="font-headline-md text-headline-md text-primary">$45,230.00</h2>
        </div>
        <div className="col-span-12 md:col-span-4 bg-white p-lg rounded-xl border border-outline-variant hover:shadow-sm transition-shadow">
          <div className="flex justify-between items-start mb-md">
            <div className="p-2 bg-secondary-container/20 rounded-lg"><Icon name="payments" className="text-secondary" /></div>
            <span className="text-xs font-bold text-red-600 bg-red-50 px-2 py-1 rounded">-5.2%</span>
          </div>
          <p className="font-label-md text-label-md text-outline uppercase tracking-wider mb-1">Money Spent</p>
          <h2 className="font-headline-md text-headline-md text-on-surface">$12,845.00</h2>
        </div>
        <div className="col-span-12 md:col-span-4 bg-white p-lg rounded-xl border border-outline-variant hover:shadow-sm transition-shadow">
          <div className="flex justify-between items-start mb-md">
            <div className="p-2 bg-on-tertiary-container/10 rounded-lg"><Icon name="account_balance_wallet" className="text-tertiary-container" /></div>
          </div>
          <p className="font-label-md text-label-md text-outline uppercase tracking-wider mb-1">Money Left</p>
          <h2 className="font-headline-md text-headline-md text-on-surface">$32,385.00</h2>
        </div>

        {/* Weekly bar chart */}
        <div className="col-span-12 lg:col-span-8 bg-white p-lg rounded-xl border border-outline-variant">
          <div className="flex justify-between items-center mb-xl">
            <h3 className="font-headline-md text-primary">Weekly Performance</h3>
            <div className="flex items-center gap-2 text-outline font-label-md"><span className="w-3 h-3 bg-primary rounded-full"></span> Sales</div>
          </div>
          <div className="h-64 flex items-end justify-between gap-sm px-md pb-md border-b border-outline-variant">
            {bars.map(b => (
              <div key={b.d} className="flex-1 flex flex-col items-center gap-sm">
                <div className={`chart-bar w-full max-w-[48px] ${b.c} rounded-t-lg`} style={{ height: b.h }}></div>
                <span className="text-xs font-label-md text-outline">{b.d}</span>
              </div>
            ))}
          </div>
          <div className="mt-md p-md bg-surface-container rounded-lg flex items-start gap-md">
            <Icon name="info" className="text-primary" fill />
            <p className="font-body-md text-on-surface-variant">High volume on Friday. <span className="font-bold text-primary">Dresses are selling the most this week</span>, contributing to 42% of total revenue.</p>
          </div>
        </div>

        {/* Donut */}
        <div className="col-span-12 lg:col-span-4 bg-white p-lg rounded-xl border border-outline-variant">
          <h3 className="font-headline-md text-primary mb-xl">Category Mix</h3>
          <div className="flex flex-col items-center gap-xl">
            <div className="relative w-48 h-48">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" fill="transparent" r="16" stroke="#f0edec" strokeWidth="4"></circle>
                <circle className="donut-segment" cx="18" cy="18" fill="transparent" r="16" stroke="#230042" strokeDasharray="50 100" strokeDashoffset="0" strokeWidth="4"></circle>
                <circle className="donut-segment" cx="18" cy="18" fill="transparent" r="16" stroke="#744c9a" strokeDasharray="25 100" strokeDashoffset="-50" strokeWidth="4"></circle>
                <circle className="donut-segment" cx="18" cy="18" fill="transparent" r="16" stroke="#d5a9ff" strokeDasharray="15 100" strokeDashoffset="-75" strokeWidth="4"></circle>
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-headline-md text-primary">100%</span>
                <span className="text-xs text-outline">Share</span>
              </div>
            </div>
            <div className="w-full flex flex-col gap-sm">
              {[
                { n: 'Apparel', p: '50%', c: 'bg-primary' },
                { n: 'Logistics', p: '25%', c: 'bg-secondary' },
                { n: 'Operations', p: '15%', c: 'bg-secondary-container' },
                { n: 'Others', p: '10%', c: 'bg-surface-container-highest' },
              ].map(r => (
                <div key={r.n} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${r.c}`}></div>
                    <span className="font-label-md text-on-surface">{r.n}</span>
                  </div>
                  <span className="font-bold text-primary">{r.p}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Best selling */}
        <div className="col-span-12 bg-white p-lg rounded-xl border border-outline-variant">
          <div className="flex justify-between items-center mb-lg">
            <h3 className="font-headline-md text-primary">Best Selling Products</h3>
            <button className="text-primary font-bold hover:underline">View All</button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-outline-variant">
                  <th className="pb-md font-label-md text-outline uppercase tracking-wider">Product</th>
                  <th className="pb-md font-label-md text-outline uppercase tracking-wider">SKU</th>
                  <th className="pb-md font-label-md text-outline uppercase tracking-wider text-right">Units Sold</th>
                  <th className="pb-md font-label-md text-outline uppercase tracking-wider text-right">Revenue</th>
                  <th className="pb-md font-label-md text-outline uppercase tracking-wider text-right">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {[
                  { name: 'Silk Floral Dress', cat: 'Apparel', sku: 'OZ-DRS-492', units: '1,240', rev: '$24,800.00', trend: '24%', up: true },
                  { name: 'Leather Chelsea Boots', cat: 'Footwear', sku: 'OZ-SH-102', units: '890', rev: '$15,575.00', trend: '12%', up: true },
                  { name: 'Classic Gold Watch', cat: 'Accessories', sku: 'OZ-ACC-931', units: '420', rev: '$12,600.00', trend: '2%', up: false },
                ].map(p => (
                  <tr key={p.sku} className="group hover:bg-surface-container-low transition-colors">
                    <td className="py-md flex items-center gap-md">
                      <div className="w-12 h-12 bg-surface-container rounded-lg flex items-center justify-center overflow-hidden">
                        <Icon name="checkroom" className="text-outline" />
                      </div>
                      <div>
                        <p className="font-bold text-primary">{p.name}</p>
                        <p className="text-xs text-outline">Category: {p.cat}</p>
                      </div>
                    </td>
                    <td className="py-md font-code text-on-surface-variant">{p.sku}</td>
                    <td className="py-md text-right font-bold">{p.units}</td>
                    <td className="py-md text-right font-bold text-primary">{p.rev}</td>
                    <td className="py-md text-right">
                      <span className={`flex items-center justify-end gap-1 ${p.up ? 'text-green-600' : 'text-on-surface-variant'}`}>
                        <Icon name={p.up ? 'trending_up' : 'remove'} className="text-sm" /> {p.trend}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
