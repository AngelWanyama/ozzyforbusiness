import { useState, useEffect } from 'react';
import api from '../api/client';

export default function Inventory() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showStockModal, setShowStockModal] = useState(null);
  const [newItem, setNewItem] = useState({ name: '', category: '', unit_price: '', stock_level: '', is_service: false });
  const [stockAdjust, setStockAdjust] = useState(0);

  useEffect(() => { loadInventory(); }, []);

  const loadInventory = async () => {
    try {
      const data = await api.getInventory();
      setItems(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddItem = async (e) => {
    e.preventDefault();
    try {
      await api.createItem({
        name: newItem.name,
        category: newItem.category || undefined,
        unit_price: parseFloat(newItem.unit_price) || 0,
        stock_level: newItem.is_service ? 0 : (parseFloat(newItem.stock_level) || 0),
        is_service: newItem.is_service,
      });
      setShowAddModal(false);
      setNewItem({ name: '', category: '', unit_price: '', stock_level: '', is_service: false });
      loadInventory();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleStockAdjust = async (itemId) => {
    try {
      await api.adjustStock(itemId, parseFloat(stockAdjust));
      setShowStockModal(null);
      setStockAdjust(0);
      loadInventory();
    } catch (err) {
      setError(err.message);
    }
  };

  const formatCurrency = (amount) => 'UGX ' + Number(amount).toLocaleString();

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Inventory</h1>
        <button className="btn btn-sm" style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}
          onClick={() => setShowAddModal(true)}>
          + Add
        </button>
      </header>

      <div className="main-content">
        {error && <div className="error-msg">{error}</div>}

        {loading ? (
          <div className="loading"><div className="spinner"></div></div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <div className="icon">📦</div>
            <h3>No inventory items</h3>
            <p>Add items or services you sell to track stock levels.</p>
            <button className="btn btn-primary mt-16" onClick={() => setShowAddModal(true)}>Add Item</button>
          </div>
        ) : (
          <div className="inventory-grid">
            {items.map(item => (
              <div key={item.id} className="inventory-item">
                <div className="item-info">
                  <h4>{item.name}</h4>
                  <div className="stock">
                    {item.is_service ? 'Service' : `Stock: ${item.stock_level}`}
                    {item.category && ` · ${item.category}`}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="item-price">{formatCurrency(item.unit_price)}</div>
                  {!item.is_service && (
                    <button className="btn btn-sm btn-secondary" style={{ marginTop: 4, fontSize: '0.75rem', padding: '4px 8px', minHeight: 30 }}
                      onClick={() => { setShowStockModal(item); setStockAdjust(0); }}>
                      Adjust Stock
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Item Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>Add Item</h2>
            <form onSubmit={handleAddItem}>
              <div className="form-group">
                <label>Item Name</label>
                <input type="text" className="form-input" placeholder="e.g., Dress, Haircut" required
                  value={newItem.name} onChange={e => setNewItem({...newItem, name: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Category</label>
                <input type="text" className="form-input" placeholder="e.g., Clothing, Services"
                  value={newItem.category} onChange={e => setNewItem({...newItem, category: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Unit Price (UGX)</label>
                <input type="number" className="form-input" placeholder="20000" required min="0"
                  value={newItem.unit_price} onChange={e => setNewItem({...newItem, unit_price: e.target.value})} />
              </div>
              <div className="form-group">
                <label>
                  <input type="checkbox" checked={newItem.is_service}
                    onChange={e => setNewItem({...newItem, is_service: e.target.checked})} style={{ marginRight: 8 }} />
                  This is a service (no stock tracking)
                </label>
              </div>
              {!newItem.is_service && (
                <div className="form-group">
                  <label>Initial Stock Level</label>
                  <input type="number" className="form-input" placeholder="10" min="0"
                    value={newItem.stock_level} onChange={e => setNewItem({...newItem, stock_level: e.target.value})} />
                </div>
              )}
              <button type="submit" className="btn btn-primary btn-block">Add Item</button>
              <button type="button" className="btn btn-secondary btn-block mt-16"
                onClick={() => setShowAddModal(false)}>Cancel</button>
            </form>
          </div>
        </div>
      )}

      {/* Adjust Stock Modal */}
      {showStockModal && (
        <div className="modal-overlay" onClick={() => setShowStockModal(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>Adjust Stock: {showStockModal.name}</h2>
            <p className="text-muted mb-16">Current stock: {showStockModal.stock_level}</p>
            <div className="form-group">
              <label>Adjustment Amount</label>
              <input type="number" className="form-input" placeholder="e.g., 5 (add) or -3 (remove)"
                value={stockAdjust} onChange={e => setStockAdjust(e.target.value)} />
            </div>
            <button className="btn btn-primary btn-block" onClick={() => handleStockAdjust(showStockModal.id)}>
              Update Stock
            </button>
            <button className="btn btn-secondary btn-block mt-16" onClick={() => setShowStockModal(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}