import { useState, useCallback, type KeyboardEvent } from 'react';
import { HelpCircle, ArrowRight } from 'lucide-react';
import '../styles/ClarificationBlock.css';

interface ClarificationBlockProps {
  question: string;
  onSubmit: (answer: string) => void;
  disabled?: boolean;
}

export function ClarificationBlock({
  question,
  onSubmit,
  disabled = false,
}: ClarificationBlockProps) {
  const [value, setValue] = useState('');

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
  }, [value, disabled, onSubmit]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div className="clarification-block fade-in">
      <div className="clarification-block__header">
        <HelpCircle size={16} />
        <span>Clarification Needed</span>
      </div>
      
      <h3 className="clarification-block__question">{question}</h3>
      
      <div
        className={`clarification-block__input-wrapper${
          disabled ? ' clarification-block__input-wrapper--disabled' : ''
        }`}
      >
        <label htmlFor="clarification-input" className="sr-only">
          Provide clarification
        </label>
        <input
          id="clarification-input"
          type="text"
          className="clarification-block__input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your clarification..."
          disabled={disabled}
          autoFocus
        />
        <button
          className="clarification-block__submit"
          onClick={handleSubmit}
          disabled={disabled || !value.trim()}
          aria-label="Submit clarification"
          type="button"
        >
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
