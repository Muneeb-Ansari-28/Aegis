import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  return (
    <div className={`markdown-body ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h3 className="md-heading md-h1">{children}</h3>,
          h2: ({ children }) => <h4 className="md-heading md-h2">{children}</h4>,
          h3: ({ children }) => <h5 className="md-heading md-h3">{children}</h5>,
          h4: ({ children }) => <h6 className="md-heading md-h4">{children}</h6>,
          p: ({ children }) => <p className="md-paragraph">{children}</p>,
          ul: ({ children }) => <ul className="md-list md-ul">{children}</ul>,
          ol: ({ children }) => <ol className="md-list md-ol">{children}</ol>,
          li: ({ children }) => <li className="md-list-item">{children}</li>,
          table: ({ children }) => (
            <div className="md-table-wrapper">
              <table className="md-table">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="md-thead">{children}</thead>,
          tbody: ({ children }) => <tbody className="md-tbody">{children}</tbody>,
          tr: ({ children }) => <tr className="md-tr">{children}</tr>,
          th: ({ children }) => <th className="md-th">{children}</th>,
          td: ({ children }) => <td className="md-td">{children}</td>,
          blockquote: ({ children }) => <blockquote className="md-blockquote">{children}</blockquote>,
          code: ({ inline, className: codeClass, children, ...props }: any) => {
            if (inline) {
              return (
                <code className="md-inline-code" {...props}>
                  {children}
                </code>
              );
            }
            return (
              <div className="md-code-block-container">
                <pre className="md-code-block">
                  <code className={codeClass} {...props}>
                    {children}
                  </code>
                </pre>
              </div>
            );
          },
          strong: ({ children }) => <strong className="md-strong">{children}</strong>,
          em: ({ children }) => <em className="md-em">{children}</em>,
          hr: () => <hr className="md-hr" />,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
