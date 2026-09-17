import '../styles/ProcessingState.css';

export function ProcessingState() {
  return (
    <div className="processing-state fade-in" aria-live="polite">
      <div className="processing-state__spinner" aria-hidden="true">
        <div className="processing-state__dot"></div>
        <div className="processing-state__dot"></div>
        <div className="processing-state__dot"></div>
      </div>
      <p className="processing-state__text">Working on your query…</p>
    </div>
  );
}
