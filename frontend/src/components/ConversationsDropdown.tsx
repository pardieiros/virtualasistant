import { useState, useEffect, useRef } from 'react';
import { conversationsAPI } from '../api/client';
import type { Conversation } from '../types';

interface ConversationsDropdownProps {
  currentConversation: Conversation | null;
  onSelectConversation: (conversationId: number) => void;
  onNewConversation: () => void;
  onConversationsUpdated?: number;
}

const ConversationsDropdown = ({
  currentConversation,
  onSelectConversation,
  onNewConversation,
  onConversationsUpdated,
}: ConversationsDropdownProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (onConversationsUpdated !== undefined && onConversationsUpdated > 0) {
      loadConversations();
    }
  }, [onConversationsUpdated]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const loadConversations = async () => {
    try {
      setLoadingConversations(true);
      const convs = await conversationsAPI.list();
      setConversations(convs);
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setLoadingConversations(false);
    }
  };

  const handleSelectConversation = (conversationId: number) => {
    onSelectConversation(conversationId);
    setIsOpen(false);
  };

  const handleNewConversation = () => {
    onNewConversation();
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="btn-secondary p-2 sm:p-2.5 md:p-3 transition-all hover:bg-primary-gold/10 hover:text-primary-gold text-base sm:text-lg"
        title="Conversations"
      >
        💬
      </button>

      {isOpen && (
        <>
          {/* Overlay */}
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown */}
          <div className="absolute right-0 bottom-full mb-2 w-64 sm:w-72 md:w-80 bg-dark-warm-gray/95 backdrop-blur-sm border border-primary-gold/20 rounded-lg shadow-2xl z-50 max-h-[70vh] overflow-y-auto">
            <div className="p-3 md:p-4">
              <div className="flex items-center justify-between mb-3 md:mb-4">
                <h3 className="text-sm md:text-base font-semibold text-text-light">Conversations</h3>
                <button
                  onClick={handleNewConversation}
                  className="text-xs md:text-sm btn-secondary px-2 md:px-3 py-1 md:py-2"
                >
                  New
                </button>
              </div>
              {loadingConversations ? (
                <div className="text-text-medium text-xs md:text-sm">Loading...</div>
              ) : conversations.length === 0 ? (
                <div className="text-text-medium text-xs md:text-sm">No conversations yet</div>
              ) : (
                <div className="space-y-1 md:space-y-2">
                  {conversations.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => handleSelectConversation(conv.id)}
                      className={`w-full text-left p-2 md:p-3 rounded-lg text-xs md:text-sm transition-colors ${
                        currentConversation?.id === conv.id
                          ? 'bg-primary-gold/20 text-primary-gold border border-primary-gold/30'
                          : 'bg-dark-warm-gray/50 text-text-medium hover:bg-dark-warm-gray'
                      }`}
                    >
                      <div className="truncate">{conv.title || 'Untitled'}</div>
                      <div className="text-xs text-text-medium mt-1">
                        {conv.message_count} messages
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ConversationsDropdown;

