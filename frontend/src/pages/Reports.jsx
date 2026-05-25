import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';

export default function Reports() {
  const { plan } = useAuth();
  const [reportType, setReportType] = useState('pnl');
  const [period, setPeriod] = useState('monthly');
  const [reportData, setReportData] = useState(null);
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const isPaid = plan?.plan_type === 'PAID';

  const reportTypes = [
    { id: 'pnl', label: 'P&L' },
    { id: 'balance_sheet', label: 'Balance Sheet' },
    { id: 'cash_flow', label: 'Cash Flow' },
  ];

  const periods = [
    { id: 'daily', label: 'Daily' },
    { id: 'weekly', label: 'Weekly' },
    { id: 'monthly', label: 'Monthly' },
  ];

  const generateReport = async () => {
    if (!isPaid) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.getAccountingReport({
        type: reportType,
        period: period,
      });
      setReportData(data.data);
      setSummary(data.summary || '');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const exportPDF = async () => {
    if (!isPaid) return;
    try {
      const response = await api.getAccountingReport({
        type: reportType,
        period: period,
        exportPdf: true,
      });
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${reportType}_${period}_report.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  };

  const formatCurrency = (amount) => {
    const num = Number(amount || 0);
    return 'UGX ' + num.toLocaleString();
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Reports</h1>
      </header>

      <div className="main-content">
        {!isPaid ? (
          <div className="card" style={{ textAlign: 'center', padding: 32 }}>
            <div style={{ fontSize: '3rem', marginBottom: 12 }}>🔒</div>
            <h2 style={{ marginBottom: 8 }}>Premium Feature</h2>
            <p className="text-muted" style={{ marginBottom: 16 }}>
              Accounting reports (P&L, Balance Sheet, Cash Flow) are available on the Paid plan.
            </p>
            <a href="#/settings" className="btn btn-accent">Upgrade Now</a>
          </div>
        ) : (
          <>
            <div className="tab-bar">
              {reportTypes.map(rt => (
                <button key={rt.id} className={`tab-item ${reportType === rt.id ? 'active' : ''}`}
                  onClick={() => setReportType(rt.id)}>
                  {rt.label}
                </button>
              ))}
            </div>

            <div className="tab-bar" style={{ marginBottom: 16 }}>
              {periods.map(p => (
                <button key={p.id} className={`tab-item ${period === p.id ? 'active' : ''}`}
                  onClick={() => setPeriod(p.id)}>
                  {p.label}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={generateReport} disabled={loading}>
                {loading ? 'Generating...' : 'Generate Report'}
              </button>
              {reportData && (
                <button className="btn btn-secondary" onClick={exportPDF}>
                  📄 PDF
                </button>
              )}
            </div>

            {error && <div className="error-msg">{error}</div>}

            {!reportData && !loading && (
              <div className="empty-state">
                <div className="icon">📊</div>
                <h3>Generate a report</h3>
                <p>Select report type and period, then click Generate.</p>
              </div>
            )}

            {loading && (
              <div className="loading"><div className="spinner"></div> Generating report...</div>
            )}

            {reportData && !loading && (
              <>
                {summary && (
                  <div className="card mb-16" style={{ background: 'var(--primary-light)' }}>
                    <p style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>{summary}</p>
                  </div>
                )}

                <div className="card">
                  {reportType === 'pnl' && (
                    <>
                      <h3 style={{ marginBottom: 16 }}>Profit & Loss</h3>
                      <div className="flex-between mb-16">
                        <span>Revenue</span>
                        <strong style={{ color: 'var(--green)' }}>{formatCurrency(reportData.total_revenue)}</strong>
                      </div>
                      <div className="flex-between mb-16">
                        <span>Cost of Goods Sold</span>
                        <strong style={{ color: 'var(--red)' }}>{formatCurrency(reportData.cogs)}</strong>
                      </div>
                      <div className="flex-between mb-16">
                        <span>Operating Expenses</span>
                        <strong style={{ color: 'var(--red)' }}>{formatCurrency(reportData.operating_expenses)}</strong>
                      </div>
                      <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '12px 0' }} />
                      <div className="flex-between">
                        <strong>Net Profit</strong>
                        <strong style={{ color: (reportData.net_profit || 0) >= 0 ? 'var(--green)' : 'var(--red)' }}>
                          {formatCurrency(reportData.net_profit)}
                        </strong>
                      </div>
                    </>
                  )}
                  {reportType === 'balance_sheet' && (
                    <>
                      <h3 style={{ marginBottom: 16 }}>Balance Sheet</h3>
                      <div className="flex-between mb-16">
                        <span>Total Assets</span>
                        <strong>{formatCurrency(reportData.total_assets)}</strong>
                      </div>
                      <div className="flex-between mb-16">
                        <span>Total Liabilities</span>
                        <strong style={{ color: 'var(--red)' }}>{formatCurrency(reportData.total_liabilities)}</strong>
                      </div>
                      <div className="flex-between">
                        <span>Equity</span>
                        <strong style={{ color: 'var(--green)' }}>{formatCurrency(reportData.equity)}</strong>
                      </div>
                    </>
                  )}
                  {reportType === 'cash_flow' && (
                    <>
                      <h3 style={{ marginBottom: 16 }}>Cash Flow</h3>
                      <div className="flex-between mb-16">
                        <span>Operating Activities</span>
                        <strong>{formatCurrency(reportData.operating_activities)}</strong>
                      </div>
                      <div className="flex-between mb-16">
                        <span>Investing Activities</span>
                        <strong>{formatCurrency(reportData.investing_activities)}</strong>
                      </div>
                      <div className="flex-between">
                        <span>Net Cash Flow</span>
                        <strong style={{ color: (reportData.net_cash_flow || 0) >= 0 ? 'var(--green)' : 'var(--red)' }}>
                          {formatCurrency(reportData.net_cash_flow)}
                        </strong>
                      </div>
                    </>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}