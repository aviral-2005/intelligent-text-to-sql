import React, { useState, useCallback, useMemo } from 'react';
import { ChevronDown, Code2, Copy, Check } from 'lucide-react';
import hljs from 'highlight.js/lib/core';
import sqlLang from 'highlight.js/lib/languages/sql';
import '../styles/SqlBlock.css';

// Register only SQL to keep bundle small
hljs.registerLanguage('sql', sqlLang);

interface SqlBlockProps {
  sql: string;
}

export function SqlBlock({ sql }: SqlBlockProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const toggleOpen = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  const handleCopy = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [sql]);

  // Highlight SQL once
  const highlightedSql = useMemo(() => {
    if (!sql) return '';
    return hljs.highlight(sql, { language: 'sql' }).value;
  }, [sql]);

  if (!sql) return null;

  return (
    <div className="sql-block">
      <div className="sql-block__header" onClick={toggleOpen} role="button" aria-expanded={isOpen}>
        <div className="sql-block__title">
          <Code2 size={16} />
          <span>Executed SQL</span>
        </div>
        <div className="sql-block__actions">
          <button
            className="sql-block__copy"
            onClick={handleCopy}
            title="Copy SQL to clipboard"
            type="button"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
          <ChevronDown
            size={18}
            className={`sql-block__toggle-icon ${isOpen ? 'sql-block__toggle-icon--open' : ''}`}
          />
        </div>
      </div>
      
      {isOpen && (
        <div className="sql-block__content fade-in">
          <pre className="sql-block__pre">
            <code
              className="sql-block__code hljs"
              dangerouslySetInnerHTML={{ __html: highlightedSql }}
            />
          </pre>
        </div>
      )}
    </div>
  );
}
