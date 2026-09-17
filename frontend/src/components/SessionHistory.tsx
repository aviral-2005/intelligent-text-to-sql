import { PanelLeftClose, PanelLeftOpen, History } from 'lucide-react';
import { type HistoryEntry } from '../types/api';
import '../styles/SessionHistory.css';

interface SessionHistoryProps {
  history: HistoryEntry[];
  currentId?: string;
  onSelect: (entry: HistoryEntry) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function SessionHistory({ history, currentId, onSelect, isCollapsed, onToggleCollapse }: SessionHistoryProps) {
  const formatTime = (ts: number) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(ts));
  };

  if (isCollapsed) {
    return (
      <aside className="session-history session-history--collapsed">
        <button
          className="session-history__toggle-btn"
          onClick={onToggleCollapse}
          aria-label="Expand sidebar"
          title="Expand sidebar"
        >
          <PanelLeftOpen size={18} />
        </button>
        <div className="session-history__collapsed-icon" title="Session History">
          <History size={18} />
        </div>
      </aside>
    );
  }

  return (
    <aside className="session-history">
      <div className="session-history__header">
        <span>Session History</span>
        {onToggleCollapse && (
          <button
            className="session-history__toggle-btn session-history__toggle-btn--inline"
            onClick={onToggleCollapse}
            aria-label="Collapse sidebar"
            title="Collapse sidebar"
          >
            <PanelLeftClose size={16} />
          </button>
        )}
      </div>
      
      <div className="session-history__list">
        {history.length === 0 ? (
          <div className="session-history__empty">
            Your query history for this session will appear here.
          </div>
        ) : (
          history.map((entry) => {
            const isActive = entry.id === currentId;
            return (
              <button
                key={entry.id}
                className={`session-history__item ${isActive ? 'session-history__item--active' : ''}`}
                onClick={() => onSelect(entry)}
                aria-current={isActive ? 'true' : undefined}
                type="button"
              >
                <span className="session-history__question">{entry.question}</span>
                <span className="session-history__time">{formatTime(entry.timestamp)}</span>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}
