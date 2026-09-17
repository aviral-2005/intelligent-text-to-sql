import { useMemo, useState } from 'react';
import { formatCellValue, humanizeColumnName } from '../utils/format';
import '../styles/DataTable.css';

interface DataTableProps {
  data: Record<string, unknown>[];
}

const PAGE_SIZE = 100;

export function DataTable({ data }: DataTableProps) {
  const [page, setPage] = useState(0);

  const columns = useMemo(() => {
    if (!data || data.length === 0) return [];
    // Extract columns from the first row
    return Object.keys(data[0]);
  }, [data]);

  const totalRows = data.length;
  const totalPages = Math.ceil(totalRows / PAGE_SIZE);
  
  const visibleData = useMemo(() => {
    const start = page * PAGE_SIZE;
    return data.slice(start, start + PAGE_SIZE);
  }, [data, page]);

  if (!data || data.length === 0) {
    return (
      <div className="data-table-container">
        <div className="data-table-empty">
          No records to display.
        </div>
      </div>
    );
  }

  return (
    <div className="data-table-container fade-in">
      <div className="data-table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col} scope="col">
                  {humanizeColumnName(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleData.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((col) => {
                  const val = row[col];
                  const isNumeric = typeof val === 'number';
                  return (
                    <td key={col} data-is-numeric={isNumeric}>
                      {formatCellValue(val, col)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="data-table-footer">
        <span>
          Showing {page * PAGE_SIZE + 1} to {Math.min((page + 1) * PAGE_SIZE, totalRows)} of {totalRows} rows
        </span>
        
        {totalPages > 1 && (
          <div className="data-table-pagination">
            <button 
              disabled={page === 0} 
              onClick={() => setPage(p => p - 1)}
              style={{ marginRight: 8, padding: '4px 8px', borderRadius: 4, background: page === 0 ? 'transparent' : 'var(--color-bg-subtle)' }}
            >
              Previous
            </button>
            <button 
              disabled={page >= totalPages - 1} 
              onClick={() => setPage(p => p + 1)}
              style={{ padding: '4px 8px', borderRadius: 4, background: page >= totalPages - 1 ? 'transparent' : 'var(--color-bg-subtle)' }}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
