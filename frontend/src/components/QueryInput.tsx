import { useRef, useCallback, type KeyboardEvent, type ChangeEvent } from 'react';
import { ArrowUp } from 'lucide-react';
import '../styles/QueryInput.css';

interface QueryInputProps {
  onSubmit: (question: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function QueryInput({
  onSubmit,
  disabled = false,
  placeholder = 'Ask a question about your database…',
}: QueryInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const value = textareaRef.current?.value.trim();
    if (!value || disabled) return;
    onSubmit(value);
    if (textareaRef.current) {
      textareaRef.current.value = '';
      textareaRef.current.style.height = 'auto';
    }
  }, [onSubmit, disabled]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const handleInput = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, []);

  return (
    <div className="query-input" role="search">
      <div
        className={`query-input__wrapper${disabled ? ' query-input__wrapper--disabled' : ''}`}
      >
        <label htmlFor="query-textarea" className="sr-only">
          Database query
        </label>
        <textarea
          ref={textareaRef}
          id="query-textarea"
          className="query-input__textarea"
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          onKeyDown={handleKeyDown}
          onChange={handleInput}
          aria-label="Enter a natural-language database question"
        />
        <button
          className="query-input__submit"
          onClick={handleSubmit}
          disabled={disabled}
          aria-label="Submit query"
          type="button"
        >
          <ArrowUp size={18} />
        </button>
      </div>
      <p className="query-input__hint">
        <kbd>Enter</kbd> to submit · <kbd>Shift + Enter</kbd> for new line
      </p>
    </div>
  );
}
