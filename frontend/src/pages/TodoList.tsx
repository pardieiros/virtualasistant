import { useState, useEffect } from 'react';
import { todoAPI } from '../api/client';
import type { TodoItem } from '../types';
import { format } from 'date-fns';

const TodoList = () => {
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed'>('pending');
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium' as 'low' | 'medium' | 'high',
    due_date: '',
  });

  useEffect(() => {
    loadTodos();
  }, [filter]);

  const loadTodos = async () => {
    try {
      setLoading(true);
      const params = filter === 'all' ? {} : { status: filter };
      const data = await todoAPI.list(params);
      setTodos(data);
    } catch (error) {
      console.error('Error loading todos:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const todoData: any = {
        title: formData.title,
        description: formData.description,
        priority: formData.priority,
      };
      
      if (formData.due_date) {
        // Convert local date to ISO string
        const date = new Date(formData.due_date);
        todoData.due_date = date.toISOString();
      }
      
      await todoAPI.create(todoData);
      setShowForm(false);
      setFormData({
        title: '',
        description: '',
        priority: 'medium',
        due_date: '',
      });
      loadTodos();
    } catch (error) {
      console.error('Error creating todo:', error);
    }
  };

  const handleToggleStatus = async (todo: TodoItem) => {
    try {
      const newStatus = todo.status === 'pending' ? 'completed' : 'pending';
      await todoAPI.update(todo.id, { status: newStatus });
      loadTodos();
    } catch (error) {
      console.error('Error updating todo:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this task?')) return;
    try {
      await todoAPI.delete(id);
      loadTodos();
    } catch (error) {
      console.error('Error deleting todo:', error);
    }
  };

  const priorityColors = {
    high: 'text-status-error',
    medium: 'text-primary-gold',
    low: 'text-text-medium',
  };

  const priorityBgColors = {
    high: 'bg-status-error/20 border-status-error/50',
    medium: 'bg-primary-gold/20 border-primary-gold/50',
    low: 'bg-text-medium/20 border-text-medium/50',
  };

  const sortedTodos = [...todos].sort((a, b) => {
    // Sort by priority first (high > medium > low)
    const priorityOrder = { high: 3, medium: 2, low: 1 };
    const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
    if (priorityDiff !== 0) return priorityDiff;
    
    // Then by due date (earlier first)
    if (a.due_date && b.due_date) {
      return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
    }
    if (a.due_date) return -1;
    if (b.due_date) return 1;
    
    // Finally by creation date (newer first)
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <h2 className="text-2xl sm:text-3xl font-bold text-primary-gold">To Do List</h2>
        <div className="flex flex-wrap gap-2 w-full sm:w-auto">
          <button
            onClick={() => setFilter('pending')}
            className={`btn-secondary text-sm ${filter === 'pending' ? 'bg-primary-gold text-dark-charcoal' : ''}`}
          >
            Pending
          </button>
          <button
            onClick={() => setFilter('completed')}
            className={`btn-secondary text-sm ${filter === 'completed' ? 'bg-primary-gold text-dark-charcoal' : ''}`}
          >
            Completed
          </button>
          <button
            onClick={() => setFilter('all')}
            className={`btn-secondary text-sm ${filter === 'all' ? 'bg-primary-gold text-dark-charcoal' : ''}`}
          >
            All
          </button>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary text-sm sm:text-base">
            + Add Task
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card mb-6 animate-fade-in">
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-text-medium mb-2 text-sm sm:text-base">Task Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="input-field w-full text-sm sm:text-base"
                placeholder="Enter task title..."
                required
                autoFocus
              />
            </div>
            <div>
              <label className="block text-text-medium mb-2 text-sm sm:text-base">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="input-field w-full text-sm sm:text-base"
                rows={3}
                placeholder="Add details about this task..."
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                <label className="block text-text-medium mb-2 text-sm sm:text-base">Due Date</label>
                <input
                  type="datetime-local"
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                  className="input-field w-full text-sm sm:text-base"
                />
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <button type="submit" className="btn-primary text-sm sm:text-base">
                Add Task
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
      ) : sortedTodos.length === 0 ? (
        <div className="text-center text-text-medium py-12 text-sm sm:text-base">
          <div className="text-6xl mb-4">✅</div>
          <p>No tasks found. Add your first task!</p>
        </div>
      ) : (
        <div className="space-y-3 sm:space-y-4">
          {sortedTodos.map((todo) => {
            const isOverdue = todo.due_date && new Date(todo.due_date) < new Date() && todo.status === 'pending';
            
            return (
              <div
                key={todo.id}
                className={`card transition-all duration-200 hover:shadow-lg hover:shadow-primary-gold/20 ${
                  todo.status === 'completed'
                    ? 'opacity-60 bg-dark-warm-gray/50'
                    : isOverdue
                    ? 'border-l-4 border-status-error'
                    : 'bg-dark-warm-gray'
                }`}
              >
                <div className="flex items-start gap-3 sm:gap-4">
                  <input
                    type="checkbox"
                    checked={todo.status === 'completed'}
                    onChange={() => handleToggleStatus(todo)}
                    className="mt-1 w-5 h-5 sm:w-6 sm:h-6 text-primary-gold flex-shrink-0 cursor-pointer rounded"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <h3 className={`font-semibold text-sm sm:text-base break-words ${
                        todo.status === 'completed' ? 'line-through text-text-medium' : 'text-text-light'
                      }`}>
                        {todo.title}
                      </h3>
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${priorityColors[todo.priority]} ${priorityBgColors[todo.priority]}`}>
                        {todo.priority}
                      </span>
                      {isOverdue && (
                        <span className="px-2 py-1 rounded text-xs font-medium bg-status-error/20 text-status-error border border-status-error/50">
                          Overdue
                        </span>
                      )}
                    </div>
                    {todo.description && (
                      <p className={`text-text-medium text-xs sm:text-sm mb-2 break-words ${
                        todo.status === 'completed' ? 'line-through' : ''
                      }`}>
                        {todo.description}
                      </p>
                    )}
                    <div className="flex flex-wrap items-center gap-3 sm:gap-4 text-xs text-text-medium">
                      {todo.due_date && (
                        <span className={`whitespace-nowrap ${isOverdue ? 'text-status-error font-semibold' : ''}`}>
                          📅 Due: {format(new Date(todo.due_date), 'MMM d, yyyy HH:mm')}
                        </span>
                      )}
                      <span className="whitespace-nowrap">
                        Created: {format(new Date(todo.created_at), 'MMM d, yyyy')}
                      </span>
                      {todo.completed_at && (
                        <span className="whitespace-nowrap text-primary-gold">
                          ✅ Completed: {format(new Date(todo.completed_at), 'MMM d, yyyy')}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(todo.id)}
                    className="text-status-error hover:text-status-error/80 flex-shrink-0 text-lg sm:text-xl transition-colors"
                    aria-label="Delete task"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default TodoList;






