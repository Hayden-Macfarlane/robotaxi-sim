interface Props {
  title: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}

/** Plain-language automation toggle with title and helper text. */
export function ToggleCard({ title, description, checked, onChange }: Props) {
  return (
    <label className="flex items-start gap-3 p-3 rounded-lg border border-border-default bg-surface-base/40 cursor-pointer hover:bg-surface-base/70 transition-colors">
      <input
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        className="checkbox-dark mt-0.5 flex-shrink-0"
      />
      <div className="min-w-0">
        <div className="text-sm font-medium text-text-primary">{title}</div>
        <div className="text-xs text-text-secondary mt-0.5 leading-relaxed">{description}</div>
      </div>
    </label>
  )
}
