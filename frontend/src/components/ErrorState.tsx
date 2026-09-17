import { AlertCircle, RefreshCw } from 'lucide-react';
import '../styles/ErrorState.css';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="error-state fade-in" role="alert">
      <AlertCircle className="error-state__icon" size={20} />
      <div className="error-state__content">
        <h3 className="error-state__title">Query Failed</h3>
        <p className="error-state__message">{message}</p>
        
        {onRetry && (
          <button className="error-state__retry" onClick={onRetry} type="button">
            <RefreshCw size={14} />
            Try again
          </button>
        )}
      </div>
    </div>
  );
}
