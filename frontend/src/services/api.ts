import type { QueryRequest, QueryResponse } from '../types/api';

/**
 * Isolated API service layer.
 *
 * All HTTP communication with the backend flows through this module.
 * UI components never call fetch() directly.
 */

const BASE = '/api';

class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function submitQuery(
  request: QueryRequest,
): Promise<QueryResponse> {
  let res: Response;

  try {
    res = await fetch(`${BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  } catch {
    throw new ApiError(
      'Unable to reach the server. Please check that the backend is running and try again.',
    );
  }

  if (!res.ok) {
    // Try to extract a meaningful message from the response body
    let detail = `Request failed (HTTP ${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) {
        // FastAPI validation errors
        if (Array.isArray(body.detail)) {
          detail = body.detail.map((d: { msg?: string }) => d.msg).join('; ');
        } else {
          detail = String(body.detail);
        }
      }
    } catch {
      // Response body wasn't JSON — use the status text
    }
    throw new ApiError(detail, res.status);
  }

  let data: unknown;
  try {
    data = await res.json();
  } catch {
    throw new ApiError('Received an invalid response from the server.');
  }

  // Validate the response has a status field
  if (
    typeof data !== 'object' ||
    data === null ||
    !('status' in data) ||
    !['ready', 'clarification_needed', 'error'].includes(
      (data as { status: string }).status,
    )
  ) {
    throw new ApiError('Received an unexpected response from the server.');
  }

  return data as QueryResponse;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/`);
    return res.ok;
  } catch {
    return false;
  }
}

export { ApiError };
