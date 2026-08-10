/**
 * Exports are presigned-URL redirects, never blobs proxied through the console —
 * a title deed should not pass through the browser's memory to reach the disk.
 * Every export is an audited event on the backend (S12).
 */

export type ExportFormat = 'docx' | 'pdf' | 'xlsx' | 'json';

export function downloadFromUrl(url: string, filename?: string): void {
  const a = document.createElement('a');
  a.href = url;
  if (filename) a.download = filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export function exportFilename(docType: string, format: ExportFormat, signed: boolean): string {
  const stamp = new Date().toISOString().slice(0, 10);
  return `${docType}_${stamp}${signed ? '' : '_draft'}.${format}`;
}
