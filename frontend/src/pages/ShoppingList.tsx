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
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <h2 className="text-2xl sm:text-3xl font-bold text-primary-gold">Shopping List</h2>
        <div className="flex flex-wrap gap-2 w-full sm:w-auto">
          <button
            onClick={() => setFilter('pending')}
            className={`btn-secondary text-sm ${filter === 'pending' ? 'bg-primary-gold text-dark-charcoal' : ''}`}
          >
            Pending
          </button>
          <button
            onClick={() => setFilter('bought')}
            className={`btn-secondary text-sm ${filter === 'bought' ? 'bg-primary-gold text-dark-charcoal' : ''}`}
          >
            Bought
          </button>
          <button
            onClick={() => setFilter('all')}
            className={`btn-secondary text-sm ${filter === 'all' ? 'bg-primary-gold text-dark-charcoal' : ''}`}
          >
            All
          </button>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary text-sm sm:text-base">
            + Add Item
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card mb-6">
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-text-medium mb-2 text-sm sm:text-base">Item Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="input-field w-full text-sm sm:text-base"
                  required
                />
              </div>
              <div>
                <label className="block text-text-medium mb-2 text-sm sm:text-base">Quantity</label>
                <input
                  type="text"
                  value={formData.quantity}
                  onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                  className="input-field w-full text-sm sm:text-base"
                  placeholder="e.g., 2kg, 3 packs"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-text-medium mb-2 text-sm sm:text-base">Store</label>
                <input
                  type="text"
                  value={formData.preferred_store}
                  onChange={(e) => setFormData({ ...formData, preferred_store: e.target.value })}
                  className="input-field w-full text-sm sm:text-base"
                  placeholder="e.g., Continente"
                />
              </div>
              <div>
                <label className="block text-text-medium mb-2 text-sm sm:text-base">Category</label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="input-field w-full text-sm sm:text-base"
                />
              </div>
            </div>
            <div>
              <label className="block text-text-medium mb-2 text-sm sm:text-base">Priority</label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value as any })}
                className="input-field w-full text-sm sm:text-base"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label className="block text-text-medium mb-2 text-sm sm:text-base">Notes</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="input-field w-full text-sm sm:text-base"
                rows={2}
              />
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <button type="submit" className="btn-primary text-sm sm:text-base">
                Add Item
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="btn-secondary text-sm sm:text-base"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center text-text-medium py-12 text-sm sm:text-base">Loading...</div>
      ) : items.length === 0 ? (
        <div className="text-center text-text-medium py-12 text-sm sm:text-base">
          No items found. Add your first item!
        </div>
      ) : (
        <div className="space-y-4 sm:space-y-6">
          {Object.entries(groupedByStore).map(([store, storeItems]) => (
            <div key={store} className="card">
              <h3 className="text-lg sm:text-xl font-semibold text-primary-gold mb-3 sm:mb-4">{store}</h3>
              <div className="space-y-2 sm:space-y-3">
                {storeItems.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-start gap-2 sm:gap-4 p-3 sm:p-4 rounded-lg border ${
                      item.status === 'bought'
                        ? 'bg-dark-charcoal border-dark-warm-gray opacity-60'
                        : 'bg-dark-warm-gray border-dark-warm-gray'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={item.status === 'bought'}
                      onChange={() => handleToggleStatus(item)}
                      className="mt-1 w-4 h-4 sm:w-5 sm:h-5 text-primary-gold flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-1">
                        <h4 className="font-semibold text-text-light text-sm sm:text-base break-words">{item.name}</h4>
                        {item.quantity && (
                          <span className="text-text-medium text-xs sm:text-sm whitespace-nowrap">({item.quantity})</span>
                        )}
                        <span className={`text-xs sm:text-sm font-medium ${priorityColors[item.priority]} whitespace-nowrap`}>
                          {item.priority}
                        </span>
                      </div>
                      {item.notes && (
                        <p className="text-text-medium text-xs sm:text-sm mb-1 break-words">{item.notes}</p>
                      )}
                      <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs text-text-medium">
                        {item.category && <span className="whitespace-nowrap">Category: {item.category}</span>}
                        <span className="whitespace-nowrap">
                          Added: {format(new Date(item.created_at), 'MMM d, yyyy')}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="text-status-error hover:text-status-error/80 flex-shrink-0 text-lg sm:text-xl"
                      aria-label="Delete item"
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

