import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';

export default function Dashboard() {
  const { plan } = useAuth();
  const [summary, setSummary] = useState(null);
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const [summaryData, txnsData, invData] = await Promise.all([
        api.getReportSummary(),
        api.getTransactions(0, 5),
        api.getInventory(),
      ]);
      setSummary(summaryData);
      setRecentTransactions(txnsData.items || []);
      setInventory(invData || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const lowStockItems = inventory.filter(item => item.stock_level < 5);

  const formatCurrency = (amount) => {
    const num = Number(amount);
    return (summary?.currency || 'UGX') + ' ' + num.toLocaleString();
  };

  if (loading) {
    return (
      <div className="app-container">
        <header className="app-header">
          <h1>Ozzy for Business</h1>
        </header>
        <div className="loading"><div className="spinner"></div> Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Dashboard</h1>
      </header>

      <div className="main-content">
        {lowStockItems.length > 0 && (
          <div className="alert-banner">
            ⚠️ {lowStockItems.length} item{lowStockItems.length > 1 ? 's' : ''} low on stock
          </div>
        )}

        {error && <div className="error-msg">{error}</div>}

        <div className="summary-cards">
          <div className="summary-card sales">
            <span className="label">Today's Sales</span>
            <span className="amount">{summary ? formatCurrency(summary.total_sales) : '—'}</span>
          </div>
          <div className="summary-card expenses">
            <span className="label">Today's Expenses</span>
            <span className="amount">{summary ? formatCurrency(summary.total_expenses) : '—'}</span>
          </div>
          <div className="summary-card profit">
            <span className="label">Today's Profit</span>
            <span className="amount">{summary ? formatCurrency(summary.net_profit) : '—'}</span>
          </div>
        </div>

        <div className="section-title">Recent Transactions</div>
        <div className="card">
          {recentTransactions.length === 0 ? (
            <div className="empty-state">
              <div className="icon">📝</div>
              <h3>No transactions yet</h3>
              <p>Start recording your sales and expenses to see them here.</p>
            </div>
          ) : (
            recentTransactions.map((txn) => (
              <div key={txn.id} className="transaction-item">
                <div className={`transaction-icon ${txn.type}`}>
                  {txn.type === 'sale' ? '↑' : '↓'}
                </div>
                <div className="transaction-details">
                  <div className="name">{txn.description || (txn.type === 'sale' ? 'Sale' : 'Expense')}</div>
                  <div className="meta">
                    {new Date(txn.transaction_date).toLocaleDateString()}
                    {txn.quantity > 1 && ` · Qty: ${txn.quantity}`}
                  </div>
                </div>
                <div className={`transaction-amount ${txn.type}`}>
                  {formatCurrency(txn.amount)}
                </div>
              </div>
            ))
          )}
        </div>

        {plan?.plan_type === 'FREE' && (
          <div className="card mt-16" style={{ background: 'var(--primary-light)', border: '1px solid #B2DFDB' }}>
            <div className="flex-between">
              <div>
                <strong>Free Plan</strong>
                <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: 4 }}>
                  Upgrade for unlimited transactions, reports & more
                </p>
              </div>
              <a href="#/settings" className="btn btn-accent btn-sm">Upgrade</a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}