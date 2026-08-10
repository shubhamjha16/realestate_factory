import type { ReactNode } from 'react';

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  /** Money and area align right and use tabular figures, so columns tie visually. */
  numeric?: boolean;
}

interface Props<T> {
  columns: readonly Column<T>[];
  rows: readonly T[];
  rowKey: (row: T) => string;
  caption?: string;
  empty?: ReactNode;
}

export function DataGrid<T>({ columns, rows, rowKey, caption, empty }: Props<T>) {
  if (rows.length === 0) return <>{empty ?? null}</>;
  return (
    <table className="w-full border-collapse text-sm">
      {caption ? <caption className="pb-2 text-left text-xs text-ink/60">{caption}</caption> : null}
      <thead>
        <tr className="bg-navy text-white">
          {columns.map((c) => (
            <th key={c.key} scope="col" className={`px-3 py-2 ${c.numeric ? 'text-right' : 'text-left'}`}>
              {c.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={rowKey(row)} className="border-b border-ink/10">
            {columns.map((c) => (
              <td key={c.key} className={`px-3 py-2 ${c.numeric ? 'text-right font-mono tabular-nums' : ''}`}>
                {c.render(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
