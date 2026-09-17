import React from 'react';
import '../styles/AnswerBlock.css';

interface AnswerBlockProps {
  answer: string;
}

function renderMarkdown(text: string) {
  // Split by bold, italic, or code blocks.
  // The capturing group in split() keeps the matched separators in the output array.
  const parts = text.split(/(\*\*.*?\*\*|\*.*?\*|`.*?`)/g);
  
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2 && !part.startsWith('**')) {
      return <em key={index}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return <code key={index} className="answer-block__code">{part.slice(1, -1)}</code>;
    }
    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
}

export function AnswerBlock({ answer }: AnswerBlockProps) {
  if (!answer) return null;

  return (
    <div className="answer-block fade-in">
      <h3 className="answer-block__title">Answer</h3>
      <p className="answer-block__content">{renderMarkdown(answer)}</p>
    </div>
  );
}
