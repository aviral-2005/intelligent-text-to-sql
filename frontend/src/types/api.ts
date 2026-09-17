/**
 * Types derived directly from backend/models.py and backend/main.py.
 *
 * The backend POST /query endpoint accepts a QueryRequest and returns
 * one of three response shapes: ready, clarification_needed, or error.
 */

// ── Request ────────────────────────────────────────────────

export interface QueryRequest {
  conversation_id: string;
  question?: string | null;
  clarification_answer?: string | null;
}

// ── Response variants ──────────────────────────────────────

export interface ReadyResponse {
  status: 'ready';
  answer: string;
  sql: string;
  result: Record<string, unknown>[];
}

export interface ClarificationResponse {
  status: 'clarification_needed';
  clarification_question: string;
}

export interface ErrorResponse {
  status: 'error';
  message: string;
}

export type QueryResponse =
  | ReadyResponse
  | ClarificationResponse
  | ErrorResponse;

// ── App-level state ────────────────────────────────────────

export type QueryStatus =
  | 'idle'
  | 'submitting'
  | 'clarification_needed'
  | 'ready'
  | 'error';

export interface QueryState {
  status: QueryStatus;
  question: string;
  conversationId: string;
  clarificationQuestion?: string;
  answer?: string;
  sql?: string;
  result?: Record<string, unknown>[];
  errorMessage?: string;
}

export interface HistoryEntry {
  id: string;
  question: string;
  answer?: string;
  sql?: string;
  result?: Record<string, unknown>[];
  timestamp: number;
}
