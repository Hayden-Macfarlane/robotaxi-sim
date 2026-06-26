interface Props {
  options: { id: string; label: string }[]
  active: string | null
  onChange: (id: string | null) => void
  allLabel?: string
}

/** Toggle chip row for catalog filters. */
export function FilterChips({ options, active, onChange, allLabel = 'All' }: Props) {
  return (
    <div className="flex flex-wrap gap-1">
      <button
        type="button"
        onClick={() => onChange(null)}
        className={`px-2 py-0.5 rounded text-[10px] border ${
          active === null
            ? 'border-accent text-accent bg-accent/10'
            : 'border-border-default text-text-secondary hover:text-text-primary'
        }`}
      >
        {allLabel}
      </button>
      {options.map(opt => (
        <button
          key={opt.id}
          type="button"
          onClick={() => onChange(opt.id)}
          className={`px-2 py-0.5 rounded text-[10px] border capitalize ${
            active === opt.id
              ? 'border-accent text-accent bg-accent/10'
              : 'border-border-default text-text-secondary hover:text-text-primary'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
