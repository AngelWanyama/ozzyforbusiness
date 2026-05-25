import { useAuth } from '../contexts/AuthContext';

export default function Settings() {
  const { plan, usage, logout } = useAuth();

  const isPaid = plan?.plan_type === 'PAID';

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Settings</h1>
      </header>

      <div className="main-content">
        {/* Plan Info */}
        <div className="settings-section">
          <h3>Subscription</h3>
          <div className="card">
            <div className="flex-between">
              <div>
                <h4 style={{ marginBottom: 4 }}>
                  {isPaid ? 'Pro Plan' : 'Free Plan'}
                </h4>
                <p className="text-muted" style={{ fontSize: '0.85rem' }}>
                  {isPaid
                    ? `Expires: ${formatDate(plan?.payment_expiry_date)}`
                    : '100 transactions/month limit'}
                </p>
              </div>
              <span className={`badge ${isPaid ? 'badge-paid' : 'badge-free'}`}>
                {isPaid ? 'ACTIVE' : 'FREE'}
              </span>
            </div>
            {usage && (
              <div className="mt-16" style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {isPaid
                  ? 'Unlimited transactions'
                  : `Used ${usage.transactions_this_month || 0} of ${usage.limit || 100} transactions this month`
                }
              </div>
            )}
            {!isPaid && (
              <button className="btn btn-accent btn-block mt-16">Upgrade to Pro - Unlimited</button>
            )}
          </div>
        </div>

        {/* Business Info */}
        <div className="settings-section">
          <h3>Business</h3>
          <div className="card">
            <div className="settings-item">
              <div className="info">
                <h4>Currency</h4>
                <p>UGX - Ugandan Shilling</p>
              </div>
              <span className="text-muted">→</span>
            </div>
            <div className="settings-item">
              <div className="info">
                <h4>Business Name</h4>
                <p>Not set</p>
              </div>
              <span className="text-muted">→</span>
            </div>
            <div className="settings-item">
              <div className="info">
                <h4>Business Type</h4>
                <p>Not set</p>
              </div>
              <span className="text-muted">→</span>
            </div>
          </div>
        </div>

        {/* Notifications */}
        <div className="settings-section">
          <h3>Notifications</h3>
          <div className="card">
            <div className="settings-item">
              <div className="info">
                <h4>Daily Summary</h4>
                <p>Get a text summary of your day's business</p>
              </div>
              <span style={{ fontSize: '1.2rem' }}>🔔</span>
            </div>
            <div className="settings-item">
              <div className="info">
                <h4>Low Stock Alerts</h4>
                <p>Get notified when items run low</p>
              </div>
              <span style={{ fontSize: '1.2rem' }}>🔔</span>
            </div>
          </div>
        </div>

        {/* Support */}
        <div className="settings-section">
          <h3>Support</h3>
          <div className="card">
            <div className="settings-item">
              <div className="info">
                <h4>Help Center</h4>
                <p>Guides and FAQs</p>
              </div>
              <span className="text-muted">→</span>
            </div>
            <div className="settings-item" style={{ borderBottom: 'none' }}>
              <div className="info">
                <h4>Contact Us</h4>
                <p>support@ozzyforbusiness.com</p>
              </div>
              <span className="text-muted">→</span>
            </div>
          </div>
        </div>

        {/* Logout */}
        <button className="btn btn-danger btn-block mt-16" onClick={logout}>
          Log Out
        </button>

        <div className="text-center mt-16" style={{ fontSize: '0.8rem', color: 'var(--text-light)', paddingBottom: 24 }}>
          Ozzy for Business v1.0.0
        </div>
      </div>
    </div>
  );
}