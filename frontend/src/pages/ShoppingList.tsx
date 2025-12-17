import { useState, useEffect } from 'react';
import { shoppingAPI } from '../api/client';
import type { ShoppingItem } from '../types';
import { format } from 'date-fns';

const ShoppingList = () => {
  const [items, setItems] = useState<ShoppingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'bought'>('pending');
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    quantity: '',
    category: '',
    preferred_store: '',
    notes: '',
    priority: 'medium' as 'low' | 'medium' | 'high',
  });

  useEffect(() => {
    loadItems();
  }, [filter]);

  const loadItems = async () => {
    try {
      setLoading(true);
      const params = filter === 'all' ? {} : { status: filter };
      const data = await shoppingAPI.list(params);
      setItems(data);
    } catch (error) {
      console.error('Error loading items:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await shoppingAPI.create(formData);
      setShowForm(false);
      setFormData({
        name: '',
        quantity: '',
        category: '',
        preferred_store: '',
        notes: '',
        priority: 'medium',
      });
      loadItems();
    } catch (error) {
      console.error('Error creating item:', error);
    }
  };

  const handleToggleStatus = async (item: ShoppingItem) => {
    try {
      const newStatus = item.status === 'pending' ? 'bought' : 'pending';
      await shoppingAPI.update(item.id, { status: newStatus });
      loadItems();
    } catch (error) {
      console.error('Error updating item:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this item?')) return;
    try {
      await shoppingAPI.delete(id);
      loadItems();
    } catch (error) {
      console.error('Error deleting item:', error);
    }
  };

  const groupedByStore = items.reduce((acc, item) => {
    const store = item.preferred_store || 'Other';
    if (!acc[store]) acc[store] = [];
    acc[store].push(item);
    return acc;
  }, {} as Record<string, ShoppingItem[]>);

  const priorityColors = {
    high: 'text-status-error',
    medium: 'text-primary-gold',
    low: 'text-text-medium',
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-primary-gold">Shopping List</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('pending')}
            className={`btn-secondary ${filter === 'pending' ? 'bg-primary-gold text-dark-charcoal' : ''}`}
          >
            Pending
          </button>
          <button
            onClick={() => setFilter('bought')}
            className={`btn-secondary ${filter === 'bought' ? 'bg-primary-gold text-dark-charcoal' : ''}`}
          >
            Bought
          </button>
          <button
            onClick={() => setFilter('all')}
            className={`btn-secondary ${filter === 'all' ? 'bg-primary-gold text-dark-charcoal' : ''}`}
          >
            All
          </button>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary">
            + Add Item
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card mb-6">
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-text-medium mb-2">Item Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="input-field w-full"
                  required
                />
              </div>
              <div>
                <label className="block text-text-medium mb-2">Quantity</label>
                <input
                  type="text"
                  value={formData.quantity}
                  onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                  className="input-field w-full"
                  placeholder="e.g., 2kg, 3 packs"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-text-medium mb-2">Store</label>
                <input
                  type="text"
                  value={formData.preferred_store}
                  onChange={(e) => setFormData({ ...formData, preferred_store: e.target.value })}
                  className="input-field w-full"
                  placeholder="e.g., Continente"
                />
              </div>
              <div>
                <label className="block text-text-medium mb-2">Category</label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="input-field w-full"
                />
              </div>
            </div>
            <div>
              <label className="block text-text-medium mb-2">Priority</label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value as any })}
                className="input-field w-full"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label className="block text-text-medium mb-2">Notes</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="input-field w-full"
                rows={2}
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary">
                Add Item
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center text-text-medium py-12">Loading...</div>
      ) : items.length === 0 ? (
        <div className="text-center text-text-medium py-12">
          No items found. Add your first item!
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedByStore).map(([store, storeItems]) => (
            <div key={store} className="card">
              <h3 className="text-xl font-semibold text-primary-gold mb-4">{store}</h3>
              <div className="space-y-3">
                {storeItems.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-start gap-4 p-4 rounded-lg border ${
                      item.status === 'bought'
                        ? 'bg-dark-charcoal border-dark-warm-gray opacity-60'
                        : 'bg-dark-warm-gray border-dark-warm-gray'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={item.status === 'bought'}
                      onChange={() => handleToggleStatus(item)}
                      className="mt-1 w-5 h-5 text-primary-gold"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-text-light">{item.name}</h4>
                        {item.quantity && (
                          <span className="text-text-medium text-sm">({item.quantity})</span>
                        )}
                        <span className={`text-sm font-medium ${priorityColors[item.priority]}`}>
                          {item.priority}
                        </span>
                      </div>
                      {item.notes && (
                        <p className="text-text-medium text-sm mb-1">{item.notes}</p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-text-medium">
                        {item.category && <span>Category: {item.category}</span>}
                        <span>
                          Added: {format(new Date(item.created_at), 'MMM d, yyyy')}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="text-status-error hover:text-status-error/80"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ShoppingList;

