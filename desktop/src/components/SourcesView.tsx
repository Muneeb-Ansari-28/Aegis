import React, { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp, FileText, ShieldAlert, X } from 'lucide-react';
import { CitationItem } from '../types';

interface SourcesViewProps {
  citations: CitationItem[];
}

export const SourcesView: React.FC<SourcesViewProps> = ({ citations }) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (!citations || citations.length === 0) return null;

  // Deduplicate citations by risk_id + page + source_title
  const uniqueCitations: CitationItem[] = [];
  const seen = new Set<string>();

  for (const c of citations) {
    const key = `${c.risk_id || ''}|${c.page ?? ''}|${c.source_title || c.source}|${c.section || ''}`;
    if (!seen.has(key)) {
      seen.add(key);
      uniqueCitations.push(c);
    }
  }

  const toggleExpand = (idx: number) => {
    setExpandedIndex(current => (current === idx ? null : idx));
  };

  return (
    <div className="sources-container">
      <div className="sources-header">
        <div className="sources-title">
          <BookOpen size={12} className="sources-icon" />
          <span>Grounding & Provenance ({uniqueCitations.length})</span>
        </div>
        <small className="sources-hint">Click a reference to inspect evidence</small>
      </div>

      <div className="citation-chips-row">
        {uniqueCitations.map((c, idx) => {
          const isSelected = expandedIndex === idx;
          const label = c.risk_id
            ? `${c.risk_id}${c.page ? ` (p.${c.page})` : ''}`
            : (c.source_title || 'Aegis Docs');

          return (
            <button
              key={idx}
              type="button"
              className={`citation-chip-btn ${isSelected ? 'selected' : ''}`}
              onClick={() => toggleExpand(idx)}
              title={`Inspect source: ${c.source_title || c.source}`}
            >
              {c.risk_id ? (
                <ShieldAlert size={10} className="chip-icon" />
              ) : (
                <FileText size={10} className="chip-icon" />
              )}
              <span className="chip-label">{label}</span>
              {isSelected ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
            </button>
          );
        })}
      </div>

      {expandedIndex !== null && uniqueCitations[expandedIndex] && (
        <div className="source-detail-card">
          <div className="source-detail-head">
            <div>
              <strong className="source-doc-title">
                {uniqueCitations[expandedIndex].source_title || 'Aegis System Documentation'}
              </strong>
              <div className="source-meta-row">
                {uniqueCitations[expandedIndex].risk_id && (
                  <span className="source-badge risk-badge">
                    {uniqueCitations[expandedIndex].risk_id}
                  </span>
                )}
                {uniqueCitations[expandedIndex].section && (
                  <span className="source-badge section-badge">
                    Section: {uniqueCitations[expandedIndex].section}
                  </span>
                )}
                {uniqueCitations[expandedIndex].page && (
                  <span className="source-badge page-badge">
                    Printed Page {uniqueCitations[expandedIndex].page}
                  </span>
                )}
              </div>
            </div>
            <button
              type="button"
              className="source-close-btn"
              onClick={() => setExpandedIndex(null)}
              aria-label="Close evidence inspection"
            >
              <X size={12} />
            </button>
          </div>

          {uniqueCitations[expandedIndex].excerpt ? (
            <div className="source-excerpt">
              <span className="excerpt-label">Verified Knowledge Base Excerpt:</span>
              <p>{uniqueCitations[expandedIndex].excerpt}</p>
            </div>
          ) : (
            <div className="source-excerpt">
              <span className="excerpt-label">Verified Source Document:</span>
              <p>Reference verified against the local Aegis offline knowledge base.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
