function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

function Item({ inflow, title, sub, amount }: { inflow: boolean; title: string; sub: string; amount: string }) {
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
        <p className={`font-bold ${inflow ? 'text-green-600' : 'text-red-600'}`}>{amount}</p>
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
  return (
    <div className="min-h-screen p-md md:p-xl lg:p-xxl">
      <div className="max-w-[900px] mx-auto">
        <h2 className="font-headline-lg text-headline-lg text-primary mb-md">Transaction History</h2>

        {/* Search & filter */}
        <div className="flex items-center gap-sm mb-lg">
          <div className="relative flex-1">
            <Icon name="search" className="absolute left-4 top-1/2 -translate-y-1/2 text-outline" />
            <input className="w-full h-[52px] pl-12 pr-4 bg-surface-container-low rounded-lg border-none focus:ring-2 focus:ring-primary-container transition-all font-body-md outline-none" placeholder="Search transactions..." type="text" />
          </div>
          <button className="h-[52px] w-[52px] flex items-center justify-center bg-surface-container-low rounded-lg active:scale-95 duration-200 ease-out-expo transition-colors">
            <Icon name="tune" className="text-on-surface-variant" />
          </button>
        </div>

        {/* Groups */}
        <div className="space-y-xl">
          <Group title="Today">
            <Item inflow title="Client Payment: Global Logistics Ltd" sub="Invoice #GL-8820 • 09:45 AM" amount="+UGX 1,240,000" />
            <Item inflow={false} title="Vendor Settlement: Cloud Infrastructure" sub="Service Tier 3 • 08:30 AM" amount="−UGX 45,200" />
          </Group>
          <Group title="Yesterday">
            <Item inflow={false} title="Corporate Rent: Head Office" sub="Q3 Payment • 04:15 PM" amount="−UGX 2,500,000" />
            <Item inflow title="Stripe Payout" sub="Sales Ref #88902 • 11:20 AM" amount="+UGX 742,000" />
          </Group>
          <Group title="Earlier this Week">
            <Item inflow={false} title="Salary Disbursement: Sales Team" sub="Aug Batch 01 • Monday" amount="−UGX 12,400,000" />
            <button className="w-full py-md text-primary font-semibold border-2 border-dashed border-outline-variant rounded-xl hover:bg-surface-container-low transition-colors active:scale-95 duration-200">
              View More History
            </button>
          </Group>
        </div>
      </div>
    </div>
  );
}
