import { useState } from 'react'
import { getTerm } from '../../lib/fleetTerminology'

interface Props {
  termId: string
}

/** Compact help popover for a fleet terminology entry. */
export function HelpPopover({ termId }: Props) {
  const [open, setOpen] = useState(false)
  const term = getTerm(termId)
  if (!term) return null

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="h-4 w-4 rounded-full border border-border-default text-[10px] text-text-secondary hover:text-accent hover:border-accent leading-none"
        aria-label={`Help: ${term.industryLabel}`}
      >
        ?
      </button>
      {open && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 cursor-default"
            aria-label="Close help"
            onClick={() => setOpen(false)}
          />
          <div className="absolute left-0 top-5 z-50 w-56 p-2 rounded-lg border border-border-default bg-surface-header shadow-lg text-left">
            <div className="text-xs font-medium text-text-primary">{term.industryLabel}</div>
            <div className="text-[10px] text-accent mt-0.5">{term.plainLabel}</div>
            <p className="text-[10px] text-text-secondary mt-1 leading-relaxed">{term.description}</p>
            {term.affects && term.affects.length > 0 && (
              <p className="text-[10px] text-text-secondary mt-1">
                Affects: {term.affects.join(', ')}
              </p>
            )}
          </div>
        </>
      )}
    </span>
  )
}
