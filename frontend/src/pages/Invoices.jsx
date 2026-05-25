import { useState } from 'react';

export default function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newInvoice, setNewInvoice] = useState({
    customerName: '',
    customerPhone: '',
    items: [{ description: '', quantity: 1, unitPrice: '' }],
    dueDate: '',
  });

  const addLineItem = () => {
    setNewInvoice({
      ...newInvoice,
      items: [...newInvoice.items, { description: '', quantity: 1, unitPrice: '' }],
    });
  };

  const updateLineItem = (index, field, value) => {
    const items = [...newInvoice.items];
    items[index][field] = value;
    setNewInvoice({ ...newInvoice, items });
  };

  const removeLineItem = (index) => {
    const items = newInvoice.items.filter((_, i) => i !== index);
    setNewInvoice({ ...newInvoice, items });
  };

  const calculateTotal = () => {
    return newInvoice.items.reduce((sum, item) => {
      return sum + (parseFloat(item.unitPrice) || 0) * (parseInt(item.quantity) || 0);
    }, 0);
  };

  const handleCreate = (e) => {
    e.preventDefault();
    const invoice = {
      id: `INV-${Date.now()}`,
      ...newInvoice,
      total: calculateTotal(),
      date: new Date().toISOString(),
      status: 'pending',
    };
    setInvoices([invoice, ...invoices]);
    setShowCreate(false);
    setNewInvoice({ customerName: '', customerPhone: '', items: [{ description: '', quantity: 1, unitPrice: '' }], dueDate: '' });
  };

  const formatCurrency = (amount) => 'UGX ' + Number(amount).toLocaleString();

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Invoices</h1>
        <button className="btn btn-sm" style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}
          onClick={() => setShowCreate(true)}>
          + New
        </button>
      </header>

      <div className="main-content">
        {invoices.length === 0 && !showCreate ? (
          <div className="empty-state">
            <div className="icon">🧾</div>
            <h3>No invoices yet</h3>
            <p>Create professional invoices for your customers.</p>
            <button className="btn btn-primary mt-16" onClick={() => setShowCreate(true)}>Create Invoice</button>
          </div>
        ) : (
          invoices.map(inv => (
            <div key={inv.id} className="card mb-16">
              <div className="flex-between mb-16">
                <div>
                  <strong>{inv.id}</strong>
                  <p className="text-muted" style={{ fontSize: '0.8rem' }}>{inv.customerName}</p>
                </div>
                <span className={`badge ${inv.status === 'paid' ? 'badge-paid' : 'badge-free'}`}>
                  {inv.status}
                </span>
              </div>
              <div className="flex-between">
                <span className="text-muted">{new Date(inv.date).toLocaleDateString()}</span>
                <strong>{formatCurrency(inv.total)}</strong>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Invoice Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>New Invoice</h2>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Customer Name</label>
                <input type="text" className="form-input" placeholder="Customer name" required
                  value={newInvoice.customerName} onChange={e => setNewInvoice({...newInvoice, customerName: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Customer Phone</label>
                <input type="tel" className="form-input" placeholder="+256 7XX XXX XXX"
                  value={newInvoice.customerPhone} onChange={e => setNewInvoice({...newInvoice, customerPhone: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Due Date</label>
                <input type="date" className="form-input" required
                  value={newInvoice.dueDate} onChange={e => setNewInvoice({...newInvoice, dueDate: e.target.value})} />
              </div>

              <label style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: 8, display: 'block' }}>Items</label>
              {newInvoice.items.map((item, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                  <input type="text" className="form-input" placeholder="Item" style={{ flex: 2, minHeight: 40, fontSize: '0.85rem' }}
                    value={item.description} onChange={e => updateLineItem(i, 'description', e.target.value)} required />
                  <input type="number" className="form-input" placeholder="Qty" style={{ width: 60, minHeight: 40, fontSize: '0.85rem' }}
                    value={item.quantity} onChange={e => updateLineItem(i, 'quantity', e.target.value)} min="1" required />
                  <input type="number" className="form-input" placeholder="Price" style={{ flex: 1, minHeight: 40, fontSize: '0.85rem' }}
                    value={item.unitPrice} onChange={e => updateLineItem(i, 'unitPrice', e.target.value)} required />
                  {newInvoice.items.length > 1 && (
                    <button type="button" className="btn btn-sm btn-danger" style={{ minHeight: 40, padding: '0 10px' }}
                      onClick={() => removeLineItem(i)}>✕</button>
                  )}
                </div>
              ))}
              <button type="button" className="btn btn-sm btn-secondary" onClick={addLineItem}>+ Add Item</button>

              <div className="flex-between mt-16 mb-16" style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                <span>Total:</span>
                <span>{formatCurrency(calculateTotal())}</span>
              </div>

              <button type="submit" className="btn btn-primary btn-block">Create Invoice</button>
              <button type="button" className="btn btn-secondary btn-block mt-16"
                onClick={() => setShowCreate(false)}>Cancel</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}