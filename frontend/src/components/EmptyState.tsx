import { Sparkles, Users, TrendingUp, ShoppingCart, Calendar } from 'lucide-react';
import '../styles/EmptyState.css';

interface EmptyStateProps {
  onSuggestionClick: (query: string) => void;
}

export function EmptyState({ onSuggestionClick }: EmptyStateProps) {
  const suggestions = [
    {
      icon: <Users size={16} />,
      text: 'How many customers do we have?',
    },
    {
      icon: <TrendingUp size={16} />,
      text: 'Which products generated the most revenue?',
    },
    {
      icon: <ShoppingCart size={16} />,
      text: 'Which employees processed the most orders?',
    },
    {
      icon: <Calendar size={16} />,
      text: 'What was our total revenue in 2007?',
    },
  ];

  return (
    <div className="empty-state fade-in">
      <div className="empty-state__icon-wrapper">
        <Sparkles size={32} />
      </div>
      <h2 className="empty-state__title">Explore your data</h2>
      <p className="empty-state__description">
        Ask natural-language questions to analyze your database. QueryLens translates your question into SQL, executes it, and explains the results.
      </p>

      <div className="empty-state__suggestions">
        <h3 className="empty-state__suggestions-title">Try an example</h3>
        <div className="empty-state__suggestion-grid">
          {suggestions.map((s, i) => (
            <button
              key={i}
              className="empty-state__suggestion-card"
              onClick={() => onSuggestionClick(s.text)}
            >
              <div className="empty-state__suggestion-icon">{s.icon}</div>
              <span className="empty-state__suggestion-text">{s.text}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
