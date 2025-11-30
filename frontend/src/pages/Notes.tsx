import { useState, useEffect } from 'react';
import { notesAPI } from '../api/client';
import type { Note } from '../types';
import { format } from 'date-fns';

const Notes = () => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formText, setFormText] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    loadNotes();
  }, []);

  const loadNotes = async () => {
    try {
      setLoading(true);
      const data = await notesAPI.list();
      setNotes(data);
    } catch (error) {
      console.error('Error loading notes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formText.trim()) return;
    
    try {
      await notesAPI.create(formText);
      setFormText('');
      setShowForm(false);
      loadNotes();
    } catch (error) {
      console.error('Error creating note:', error);
    }
  };

  const handleUpdate = async (id: number, text: string) => {
    try {
      await notesAPI.update(id, text);
      setEditingId(null);
      loadNotes();
    } catch (error) {
      console.error('Error updating note:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this note?')) return;
    try {
      await notesAPI.delete(id);
      loadNotes();
    } catch (error) {
      console.error('Error deleting note:', error);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-primary-gold">Notes</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary">
          + Add Note
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-text-medium mb-2">Note</label>
              <textarea
                value={formText}
                onChange={(e) => setFormText(e.target.value)}
                className="input-field w-full"
                rows={6}
                placeholder="Write your note here..."
                autoFocus
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary">
                Save Note
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setFormText('');
                }}
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
      ) : notes.length === 0 ? (
        <div className="text-center text-text-medium py-12">
          No notes yet. Add your first note!
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {notes.map((note) => (
            <div key={note.id} className="card">
              {editingId === note.id ? (
                <div className="space-y-2">
                  <textarea
                    defaultValue={note.text}
                    className="input-field w-full"
                    rows={6}
                    autoFocus
                    onBlur={(e) => {
                      if (e.target.value !== note.text) {
                        handleUpdate(note.id, e.target.value);
                      } else {
                        setEditingId(null);
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') {
                        setEditingId(null);
                      } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        handleUpdate(note.id, e.currentTarget.value);
                      }
                    }}
                  />
                </div>
              ) : (
                <>
                  <p className="text-text-light whitespace-pre-wrap mb-4">
                    {note.text}
                  </p>
                  <div className="flex justify-between items-center text-xs text-text-medium border-t border-dark-warm-gray pt-3">
                    <span>
                      {format(new Date(note.created_at), 'MMM d, yyyy')}
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setEditingId(note.id)}
                        className="hover:text-primary-gold"
                      >
                        ✏️
                      </button>
                      <button
                        onClick={() => handleDelete(note.id)}
                        className="hover:text-status-error"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Notes;

