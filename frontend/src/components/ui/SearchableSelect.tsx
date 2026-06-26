import { useMemo, useState } from 'react'

export interface SearchableOption {
  value: string
  label: string
  group?: string
  description?: string
  meta?: string
}

interface Props {
  options: SearchableOption[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  dropdownZIndex?: number
  emptyMessage?: string
}

/** Filterable combobox for large catalogs (metrics, constants, actions). */
export function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = 'Search…',
  className = '',
  dropdownZIndex = 50,
  emptyMessage = 'No matches',
}: Props) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

  const selected = options.find(o => o.value === value)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return options
    return options.filter(
      o =>
        o.label.toLowerCase().includes(q) ||
        o.value.toLowerCase().includes(q) ||
        (o.description?.toLowerCase().includes(q) ?? false) ||
        (o.meta?.toLowerCase().includes(q) ?? false),
    )
  }, [options, query])

  const grouped = useMemo(() => {
    const map = new Map<string, SearchableOption[]>()
    for (const opt of filtered) {
      const g = opt.group ?? 'Other'
      if (!map.has(g)) map.set(g, [])
      map.get(g)!.push(opt)
    }
    return [...map.entries()]
  }, [filtered])

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="input-dark w-full text-left text-xs flex items-center justify-between gap-2"
      >
        <span className="truncate">{selected?.label ?? value.replace(/\./g, ' ')}</span>
        <span className="text-text-secondary shrink-0">▾</span>
      </button>
      {open && (
        <div
          className="absolute mt-1 w-full rounded border border-border-default bg-surface-raised shadow-lg max-h-56 flex flex-col"
          style={{ zIndex: dropdownZIndex }}
        >
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={placeholder}
            className="input-dark text-xs m-2"
            autoFocus
          />
          <div className="overflow-y-auto flex-1 pb-2">
            {grouped.length === 0 && (
              <p className="px-3 py-2 text-[10px] text-text-secondary">{emptyMessage}</p>
            )}
            {grouped.map(([group, items]) => (
              <div key={group}>
                <div className="px-3 py-1 text-[10px] uppercase text-text-secondary font-medium">{group}</div>
                {items.map(opt => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      onChange(opt.value)
                      setOpen(false)
                      setQuery('')
                    }}
                    className={`w-full text-left px-3 py-1.5 text-xs hover:bg-surface-base ${
                      opt.value === value ? 'text-accent bg-accent/10' : 'text-text-primary'
                    }`}
                  >
                    <div className="font-medium">{opt.label}</div>
                    {opt.description && (
                      <div className="text-[10px] text-text-secondary line-clamp-2">{opt.description}</div>
                    )}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
      {open && (
        <button
          type="button"
          className="fixed inset-0"
          style={{ zIndex: dropdownZIndex - 1 }}
          aria-label="Close picker"
          onClick={() => setOpen(false)}
        />
      )}
    </div>
  )
}
