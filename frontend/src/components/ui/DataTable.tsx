import type { ReactNode } from 'react'

export interface Column<T> {
  key: string
  header: string
  sortable?: boolean
  render: (row: T) => ReactNode
  className?: string
}

interface Props<T> {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  sortKey?: string
  sortDir?: 'asc' | 'desc'
  onSort?: (key: string) => void
  selectedKey?: string | null
  onSelectRow?: (row: T) => void
  emptyMessage?: string
}

/** Lightweight sortable table without external dependencies. */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  sortKey,
  sortDir,
  onSort,
  selectedKey,
  onSelectRow,
  emptyMessage = 'No rows',
}: Props<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border-default text-text-secondary">
            {columns.map(col => (
              <th
                key={col.key}
                className={`text-left font-medium py-1.5 px-2 ${col.className ?? ''} ${
                  col.sortable ? 'cursor-pointer hover:text-text-primary select-none' : ''
                }`}
                onClick={() => col.sortable && onSort?.(col.key)}
              >
                {col.header}
                {col.sortable && sortKey === col.key && (
                  <span className="ml-1 opacity-60">{sortDir === 'asc' ? '↑' : '↓'}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="py-4 text-center text-text-secondary">
                {emptyMessage}
              </td>
            </tr>
          )}
          {rows.map(row => {
            const key = rowKey(row)
            const selected = selectedKey === key
            return (
              <tr
                key={key}
                onClick={() => onSelectRow?.(row)}
                className={`border-b border-border-default/40 last:border-0 ${
                  onSelectRow ? 'cursor-pointer hover:bg-surface-base/50' : ''
                } ${selected ? 'bg-accent/15 ring-1 ring-inset ring-accent/40' : ''}`}
              >
                {columns.map(col => (
                  <td key={col.key} className={`py-1.5 px-2 ${col.className ?? ''}`}>
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
