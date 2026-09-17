import { type QueryState } from '../types/api';
import { AnswerBlock } from './AnswerBlock';
import { DataTable } from './DataTable';
import { SqlBlock } from './SqlBlock';
import { ClarificationBlock } from './ClarificationBlock';
import { ProcessingState } from './ProcessingState';
import { ErrorState } from './ErrorState';
import '../styles/ResultCard.css';

interface ResultCardProps {
  state: QueryState;
  onSubmitClarification: (answer: string) => void;
  onRetryError: () => void;
}

export function ResultCard({ state, onSubmitClarification, onRetryError }: ResultCardProps) {
  const { status, question, answer, sql, result, errorMessage, clarificationQuestion } = state;

  return (
    <div className="result-card fade-in">
      <h2 className="result-card__question-banner">{question}</h2>

      {status === 'submitting' && <ProcessingState />}

      {status === 'error' && errorMessage && (
        <ErrorState message={errorMessage} onRetry={onRetryError} />
      )}

      {status === 'clarification_needed' && clarificationQuestion && (
        <ClarificationBlock 
          question={clarificationQuestion} 
          onSubmit={onSubmitClarification} 
        />
      )}

      {status === 'ready' && (
        <>
          <AnswerBlock answer={answer || ''} />
          {result && <DataTable data={result} />}
          {sql && <SqlBlock sql={sql} />}
        </>
      )}
    </div>
  );
}
