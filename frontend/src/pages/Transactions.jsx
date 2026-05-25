import { useState, useEffect } from 'react';
import api from '../api/client';

export default function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all'); // all | sale | expense
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTxn, setNewTxn] = useState({ type: 'sale', amount: '', description: '', quantity: 1 });
  const [addError, setAddError] = useState('');

  useEffect(() => { loadTransactions(); }, []);

  const loadTransactions = async () => {
    try {
      const data = await api.getTransactions(0, 200);
      setTransactions(data.items || []);
      setTotal(data.total);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    setAddError('');
    try {
      await api.createTransaction({
        type: newTxn.type,
        amount: parseFloat(newTxn.amount),
        description: newTxn.description || undefined,
        quantity: parseInt(newTxn.quantity) || 1,
      });
      setShowAddModal(false);
      setNewTxn({ type: 'sale', amount: '', description: '', quantity: 1 });
      loadTransactions();
    } catch (err) {
      setAddError(err.message);
    }
  };

  const filteredTxns = filter === 'all'
    ? transactions
    : transactions.filter(t => t.type === filter);

  const formatCurrency = (amount) => 'UGX ' + Number(amount).toLocaleString();

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Transactions</h1>
        <button className="btn btn-sm" style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}
          onClick={() => setShowAddModal(true)}>
          + Add
        </button>
      </header>

      <div className="main-content">
        <div className="flex-between mb-16">
          <span className="text-muted">{total} transaction{total !== 1 ? 's' : ''}</span>
        </div>

        <div className="filter-bar">
          {['all', 'sale', 'expense'].map(f => (
            <button key={f} className={`filter-chip ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}>
              {f === 'all' ? 'All' : f === 'sale' ? '💰 Sales' : '💸 Expenses'}
            </button>
          ))}
        </div>

        {error && <div className="error-msg">{error}</div>}

        {loading ? (
          <div className="loading"><div className="spinner"></div></div>
        ) : filteredTxns.length === 0 ? (
          <div className="empty-state">
            <div className="icon">📭</div>
            <h3>No transactions found</h3>
            <p>Add your first transaction to get started.</p>
          </div>
        ) : (
          <div className="card">
            {filteredTxns.map((txn) => (
              <div key={txn.id} className="transaction-item">
                <div className={`transaction-icon ${txn.type}`}>
                  {txn.type === 'sale' ? '↑' : '↓'}
                </div>
                <div className="transaction-details">
                  <div className="name">{txn.description || (txn.type === 'sale' ? 'Sale' : 'Expense')}</div>
                  <div className="meta">
                    {new Date(txn.transaction_date).toLocaleString()}
                    {txn.quantity > 1 && ` · Qty: ${txn.quantity}`}
                    {txn.item_id && ` · Item #${txn.item_id.slice(0, 8)}`}
                  </div>
                </div>
                <div className={`transaction-amount ${txn.type}`}>
                  {formatCurrency(txn.amount)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Transaction Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>Add Transaction</h2>
            {addError && <div className="error-msg">{addError}</div>}
            <form onSubmit={handleAdd}>
              <div className="form-group">
                <label>Type</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button type="button" className={`btn btn-sm ${newTxn.type === 'sale' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setNewTxn({...newTxn, type: 'sale'})}>💰 Sale</button>
                  <button type="button" className={`btn btn-sm ${newTxn.type === 'expense' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setNewTxn({...newTxn, type: 'expense'})}>💸 Expense</button>
                </div>
              </div>
              <div className="form-group">
                <label>Description</label>
                <input type="text" className="form-input" placeholder="e.g., Sold dress" required
                  value={newTxn.description} onChange={e => setNewTxn({...newTxn, description: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Amount (UGX)</label>
                <input type="number" className="form-input" placeholder="20000" required min="1"
                  value={newTxn.amount} onChange={e => setNewTxn({...newTxn, amount: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Quantity</label>
                <input type="number" className="form-input" placeholder="1" min="1"
                  value={newTxn.quantity} onChange={e => setNewTxn({...newTxn, quantity: e.target.value})} />
              </div>
              <button type="submit" className="btn btn-primary btn-block">Add Transaction</button>
              <button type="button" className="btn btn-secondary btn-block mt-16"
                onClick={() => setShowAddModal(false)}>Cancel</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}