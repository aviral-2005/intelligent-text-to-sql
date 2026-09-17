/**
 * Formatting utilities for display purposes.
 *
 * These never alter the underlying data — they produce display strings only.
 */

/**
 * Format a cell value for display in the data table.
 * Returns a string suitable for rendering. The original value is preserved.
 */
export function formatCellValue(value: unknown, columnName?: string): string {
  if (value === null || value === undefined) {
    return '—';
  }

  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }

  if (typeof value === 'number') {
    if (columnName) {
      const lowerCol = columnName.toLowerCase();
      const isMonetary = ['revenue', 'price', 'cost', 'sales', 'amount', 'total', 'freight'].some(keyword => lowerCol.includes(keyword));
      if (isMonetary) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
      }
    }
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 }).format(value);
  }

  if (typeof value === 'string') {
    return value;
  }

  // Objects/arrays — serialize
  return JSON.stringify(value);
}

/**
 * Convert a snake_case or camelCase column name into a readable header.
 */
export function humanizeColumnName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Generate a UUID v4 for conversation IDs.
 */
export function generateId(): string {
  return crypto.randomUUID();
}
