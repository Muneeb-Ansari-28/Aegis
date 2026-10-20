import FindingsInspector from './FindingsInspector';

/**
 * ReportViewer view component.
 * In accordance with the Findings and Export PDF implementation plan,
 * this delegates to the unified FindingsInspector view which integrates
 * vulnerability inspection, turn evidence, and executive PDF reporting.
 */
export default function ReportViewer() {
  return <FindingsInspector />;
}
