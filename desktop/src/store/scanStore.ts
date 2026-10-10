// State store for scan configurations
export interface ScanStateStore {
  activeScanId: string | null;
  scans: Record<string, any>;
}
