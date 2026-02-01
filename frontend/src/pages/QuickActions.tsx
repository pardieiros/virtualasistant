import { useMemo, useRef, useState } from 'react';
import { chatAPI } from '../api/client';
import { usePusher } from '../hooks/usePusher';
import { getUserIdFromToken } from '../utils/jwt';

type QuickActionKey = 'shopping' | 'agenda' | 'todo' | 'notes';

type QuickActionsFormState = {
  shopping: {
    itemName: string;
    quantity: string;
    preferredStore: string;
    notes: string;
  };
  agenda: {
    title: string;
    when: string;
    location: string;
    description: string;
  };
  todo: {
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high';
  };
  notes: {
    text: string;
  };
};

const QuickActions = () => {
  const userId = getUserIdFromToken();

  const [selectedAction, setSelectedAction] = useState<QuickActionKey>('shopping');
  const [isSending, setIsSending] = useState(false);
  const [isWaitingForPusher, setIsWaitingForPusher] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSentMessage, setLastSentMessage] = useState<string | null>(null);
  const [lastReply, setLastReply] = useState<string | null>(null);
  const pendingRef = useRef(false);

  const [form, setForm] = useState<QuickActionsFormState>({
    shopping: {
      itemName: '',
      quantity: '',
      preferredStore: '',
      notes: '',
    },
    agenda: {
      title: '',
      when: '',
      location: '',
      description: '',
    },
    todo: {
      title: '',
      description: '',
      priority: 'medium',
    },
    notes: {
      text: '',
    },
  });

  const actionConfig = useMemo(
    () => ({
      shopping: {
        label: 'Shopping',
        icon: '🛒',
        description: 'Add an item to your shopping list.',
      },
      agenda: {
        label: 'Agenda',
        icon: '📅',
        description: 'Add an event to your agenda.',
      },
      todo: {
        label: 'To Do',
        icon: '✅',
        description: 'Add a task to your to-do list.',
      },
      notes: {
        label: 'Notes',
        icon: '📝',
        description: 'Create a new note.',
      },
    }),
    []
  );

  const buildChatMessage = (action: QuickActionKey, state: QuickActionsFormState): string => {
    // IMPORTANT: we send a natural-language instruction to the backend chat endpoint,
    // exactly like the Chat page does, so the assistant can choose the correct tool.
    //
    // The assistant prompt is PT-PT, so we phrase the instruction in PT-PT for best results.
    if (action === 'shopping') {
      const { itemName, quantity, preferredStore, notes } = state.shopping;
      const parts: string[] = [];
      parts.push(`Adiciona à minha lista de compras: ${itemName.trim()}.`);
      if (quantity.trim()) parts.push(`Quantidade: ${quantity.trim()}.`);
      if (preferredStore.trim()) parts.push(`Loja preferida: ${preferredStore.trim()}.`);
      if (notes.trim()) parts.push(`Notas: ${notes.trim()}.`);
      return parts.join(' ');
    }

    if (action === 'agenda') {
      const { title, when, location, description } = state.agenda;
      const parts: string[] = [];
      parts.push(`Adiciona à minha agenda: ${title.trim()}.`);
      parts.push(`Quando: ${when.trim()}.`);
      if (location.trim()) parts.push(`Local: ${location.trim()}.`);
      if (description.trim()) parts.push(`Descrição: ${description.trim()}.`);
      return parts.join(' ');
    }

    if (action === 'todo') {
      const { title, description, priority } = state.todo;
      const parts: string[] = [];
      parts.push(`Adiciona à minha lista de tarefas: ${title.trim()}.`);
      parts.push(`Prioridade: ${priority}.`);
      if (description.trim()) parts.push(`Descrição: ${description.trim()}.`);
      return parts.join(' ');
    }

    const { text } = state.notes;
    return `Cria uma nota com o seguinte texto: ${text.trim()}`;
  };

  const validateForm = (action: QuickActionKey, state: QuickActionsFormState): string | null => {
    if (action === 'shopping' && !state.shopping.itemName.trim()) return 'Item name is required.';
    if (action === 'agenda') {
      if (!state.agenda.title.trim()) return 'Event title is required.';
      if (!state.agenda.when.trim()) return 'When is required (you can write natural language).';
    }
    if (action === 'todo' && !state.todo.title.trim()) return 'Task title is required.';
    if (action === 'notes' && !state.notes.text.trim()) return 'Note text is required.';
    return null;
  };

  usePusher(userId, (event, data) => {
    if (event !== 'assistant-message') return;
    // Important: don't gate on React state here, to avoid race conditions where
    // the Pusher message arrives before we flip "waiting" to true.
    if (!pendingRef.current) return;

    const message = data?.message;
    if (typeof message !== 'string' || !message.trim()) return;

    setLastReply(message);
    setIsWaitingForPusher(false);
    setIsSending(false);
    pendingRef.current = false;
  });

  const handleSend = async () => {
    setError(null);
    setLastReply(null);

    const validationError = validateForm(selectedAction, form);
    if (validationError) {
      setError(validationError);
      return;
    }

    const message = buildChatMessage(selectedAction, form);
    setLastSentMessage(message);
    // Set "pending" BEFORE the HTTP request, so we can't miss fast Pusher replies.
    pendingRef.current = true;
    setIsWaitingForPusher(true);
    setIsSending(true);

    try {
      const response = await chatAPI.send(message, []);

      // Backend may respond via Pusher (reply=null + via_pusher=true) or directly with reply.
      if (response.reply) {
        setLastReply(response.reply);
        setIsWaitingForPusher(false);
        pendingRef.current = false;
      } else if (response.via_pusher || response.search_in_progress) {
        setIsWaitingForPusher(true);
      } else {
        // Defensive fallback: avoid leaving the UI in a forever-loading state.
        setIsWaitingForPusher(false);
        pendingRef.current = false;
        setError('No reply received. Please try again.');
      }
    } catch (e: any) {
      setIsWaitingForPusher(false);
      pendingRef.current = false;
      setError('Sorry, I encountered an error. Please try again.');
      // eslint-disable-next-line no-console
      console.error('QuickActions chat error:', e);
    } finally {
      setIsSending(false);
    }
  };

  const selected = actionConfig[selectedAction];

  return (
    <div className="h-full p-4 md:p-6 bg-gradient-to-b from-dark-charcoal via-dark-charcoal to-dark-warm-gray/30">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl md:text-3xl font-semibold bg-gradient-to-r from-primary-gold to-primary-gold-soft bg-clip-text text-transparent">
            Quick Actions
          </h2>
          <p className="text-text-medium mt-2">
            Choose an action, fill the details, and we will send it to the assistant (same backend flow as the Chat page).
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
          {(Object.keys(actionConfig) as QuickActionKey[]).map((key) => {
            const cfg = actionConfig[key];
            const isActive = selectedAction === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setSelectedAction(key);
                  setError(null);
                  setLastReply(null);
                }}
                className={`text-left p-4 rounded-xl border transition-all ${
                  isActive
                    ? 'border-primary-gold bg-primary-gold/10'
                    : 'border-primary-gold/10 bg-dark-warm-gray/50 hover:bg-dark-warm-gray/70 hover:border-primary-gold/30'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{cfg.icon}</span>
                  <div>
                    <div className="text-text-light font-semibold">{cfg.label}</div>
                    <div className="text-xs text-text-medium">{cfg.description}</div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="bg-dark-warm-gray/60 border border-primary-gold/10 rounded-2xl p-4 md:p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">{selected.icon}</span>
            <div>
              <div className="text-text-light font-semibold text-lg">{selected.label}</div>
              <div className="text-text-medium text-sm">{selected.description}</div>
            </div>
          </div>

          {selectedAction === 'shopping' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm text-text-medium mb-1">Item</label>
                <input
                  value={form.shopping.itemName}
                  onChange={(e) => setForm((prev) => ({ ...prev, shopping: { ...prev.shopping, itemName: e.target.value } }))}
                  className="input-field w-full"
                  placeholder="e.g. Leite"
                  autoComplete="off"
                />
              </div>
              <div>
                <label className="block text-sm text-text-medium mb-1">Quantity (optional)</label>
                <input
                  value={form.shopping.quantity}
                  onChange={(e) => setForm((prev) => ({ ...prev, shopping: { ...prev.shopping, quantity: e.target.value } }))}
                  className="input-field w-full"
                  placeholder="e.g. 2"
                  autoComplete="off"
                />
              </div>
              <div>
                <label className="block text-sm text-text-medium mb-1">Preferred store (optional)</label>
                <input
                  value={form.shopping.preferredStore}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, shopping: { ...prev.shopping, preferredStore: e.target.value } }))
                  }
                  className="input-field w-full"
                  placeholder="e.g. Continente"
                  autoComplete="off"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm text-text-medium mb-1">Notes (optional)</label>
                <textarea
                  value={form.shopping.notes}
                  onChange={(e) => setForm((prev) => ({ ...prev, shopping: { ...prev.shopping, notes: e.target.value } }))}
                  className="input-field w-full resize-none"
                  rows={3}
                  placeholder="e.g. Sem lactose"
                />
              </div>
            </div>
          )}

          {selectedAction === 'agenda' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm text-text-medium mb-1">Title</label>
                <input
                  value={form.agenda.title}
                  onChange={(e) => setForm((prev) => ({ ...prev, agenda: { ...prev.agenda, title: e.target.value } }))}
                  className="input-field w-full"
                  placeholder="e.g. Consulta no dentista"
                  autoComplete="off"
                />
              </div>
              <div>
                <label className="block text-sm text-text-medium mb-1">When</label>
                <input
                  value={form.agenda.when}
                  onChange={(e) => setForm((prev) => ({ ...prev, agenda: { ...prev.agenda, when: e.target.value } }))}
                  className="input-field w-full"
                  placeholder="e.g. amanhã às 15:00"
                  autoComplete="off"
                />
              </div>
              <div>
                <label className="block text-sm text-text-medium mb-1">Location (optional)</label>
                <input
                  value={form.agenda.location}
                  onChange={(e) => setForm((prev) => ({ ...prev, agenda: { ...prev.agenda, location: e.target.value } }))}
                  className="input-field w-full"
                  placeholder="e.g. Clínica X"
                  autoComplete="off"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm text-text-medium mb-1">Description (optional)</label>
                <textarea
                  value={form.agenda.description}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, agenda: { ...prev.agenda, description: e.target.value } }))
                  }
                  className="input-field w-full resize-none"
                  rows={3}
                  placeholder="e.g. Levar exames"
                />
              </div>
            </div>
          )}

          {selectedAction === 'todo' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm text-text-medium mb-1">Title</label>
                <input
                  value={form.todo.title}
                  onChange={(e) => setForm((prev) => ({ ...prev, todo: { ...prev.todo, title: e.target.value } }))}
                  className="input-field w-full"
                  placeholder="e.g. Pagar a luz"
                  autoComplete="off"
                />
              </div>
              <div>
                <label className="block text-sm text-text-medium mb-1">Priority</label>
                <select
                  value={form.todo.priority}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, todo: { ...prev.todo, priority: e.target.value as any } }))
                  }
                  className="input-field w-full"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm text-text-medium mb-1">Description (optional)</label>
                <textarea
                  value={form.todo.description}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, todo: { ...prev.todo, description: e.target.value } }))
                  }
                  className="input-field w-full resize-none"
                  rows={3}
                  placeholder="e.g. Até sexta-feira"
                />
              </div>
            </div>
          )}

          {selectedAction === 'notes' && (
            <div>
              <label className="block text-sm text-text-medium mb-1">Note</label>
              <textarea
                value={form.notes.text}
                onChange={(e) => setForm((prev) => ({ ...prev, notes: { ...prev.notes, text: e.target.value } }))}
                className="input-field w-full resize-none"
                rows={6}
                placeholder="Write your note here..."
              />
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 rounded-lg border border-status-error/30 bg-status-error/10 text-text-light">
              {error}
            </div>
          )}

          <div className="mt-6 flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
            <div className="text-xs text-text-medium">
              {lastSentMessage ? (
                <span>
                  <strong className="text-text-light">Last message:</strong> {lastSentMessage}
                </span>
              ) : (
                <span>Fill the form and click Send.</span>
              )}
            </div>
            <button
              type="button"
              onClick={handleSend}
              disabled={isSending || isWaitingForPusher}
              className="btn-primary px-5 py-2 disabled:opacity-50"
            >
              {isWaitingForPusher ? 'Waiting…' : isSending ? 'Sending…' : 'Send'}
            </button>
          </div>
        </div>

        {lastReply && (
          <div className="mt-6 bg-dark-warm-gray/60 border border-primary-gold/10 rounded-2xl p-4 md:p-6 shadow-xl">
            <div className="text-text-light font-semibold mb-2">Assistant reply</div>
            <p className="text-text-light whitespace-pre-wrap leading-relaxed">{lastReply}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default QuickActions;

