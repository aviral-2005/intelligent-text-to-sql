import { useCallback, useRef, useState } from 'react';
import { submitQuery, ApiError } from '../services/api';
import type {
  QueryState,
  QueryStatus,
  HistoryEntry,
} from '../types/api';
import { generateId } from '../utils/format';

const INITIAL_STATE: QueryState = {
  status: 'idle',
  question: '',
  conversationId: '',
};

/**
 * Core query state machine hook.
 *
 * Manages the full lifecycle:
 *   idle → submitting → ready | clarification_needed | error
 *                       clarification_needed → submitting → ready | error
 */
export function useQuery() {
  const [state, setState] = useState<QueryState>(INITIAL_STATE);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  // ── Submit a new question ──────────────────────────────────

  const askQuestion = useCallback(async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed) return;

    // Cancel any inflight request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    const conversationId = generateId();

    setState({
      status: 'submitting',
      question: trimmed,
      conversationId,
    });

    try {
      const response = await submitQuery({
        conversation_id: conversationId,
        question: trimmed,
      });

      if (response.status === 'ready') {
        const newState: QueryState = {
          status: 'ready',
          question: trimmed,
          conversationId,
          answer: response.answer,
          sql: response.sql,
          result: response.result,
        };
        setState(newState);

        // Add to session history
        setHistory((prev) => [
          {
            id: conversationId,
            question: trimmed,
            answer: response.answer,
            sql: response.sql,
            result: response.result,
            timestamp: Date.now(),
          },
          ...prev,
        ]);
      } else if (response.status === 'clarification_needed') {
        setState({
          status: 'clarification_needed',
          question: trimmed,
          conversationId,
          clarificationQuestion: response.clarification_question,
        });
      } else {
        // error response from backend
        setState({
          status: 'error',
          question: trimmed,
          conversationId,
          errorMessage: response.message,
        });
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : 'An unexpected error occurred. Please try again.';

      setState({
        status: 'error',
        question: trimmed,
        conversationId,
        errorMessage: message,
      });
    }
  }, []);

  // ── Submit a clarification answer ──────────────────────────

  const submitClarification = useCallback(
    async (clarificationAnswer: string) => {
      const trimmed = clarificationAnswer.trim();
      if (!trimmed) return;

      const { question, conversationId } = state;

      setState((prev) => ({
        ...prev,
        status: 'submitting' as QueryStatus,
      }));

      try {
        const response = await submitQuery({
          conversation_id: conversationId,
          clarification_answer: trimmed,
        });

        if (response.status === 'ready') {
          const newState: QueryState = {
            status: 'ready',
            question,
            conversationId,
            answer: response.answer,
            sql: response.sql,
            result: response.result,
          };
          setState(newState);

          setHistory((prev) => [
            {
              id: conversationId,
              question,
              answer: response.answer,
              sql: response.sql,
              result: response.result,
              timestamp: Date.now(),
            },
            ...prev,
          ]);
        } else if (response.status === 'clarification_needed') {
          setState({
            status: 'clarification_needed',
            question,
            conversationId,
            clarificationQuestion: response.clarification_question,
          });
        } else {
          setState({
            status: 'error',
            question,
            conversationId,
            errorMessage: response.message,
          });
        }
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : 'An unexpected error occurred. Please try again.';

        setState({
          status: 'error',
          question,
          conversationId,
          errorMessage: message,
        });
      }
    },
    [state],
  );

  // ── Load a previous result from session history ────────────

  const loadFromHistory = useCallback((entry: HistoryEntry) => {
    setState({
      status: 'ready',
      question: entry.question,
      conversationId: entry.id,
      answer: entry.answer,
      sql: entry.sql,
      result: entry.result,
    });
  }, []);

  // ── Reset to idle ──────────────────────────────────────────

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState(INITIAL_STATE);
  }, []);

  return {
    state,
    history,
    askQuestion,
    submitClarification,
    loadFromHistory,
    reset,
  };
}
