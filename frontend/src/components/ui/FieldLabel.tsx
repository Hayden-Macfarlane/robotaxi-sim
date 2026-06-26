import type { ReactNode } from 'react'
import { useUiMode } from '../../contexts/UiModeContext'
import { getTerm, labelForTerm } from '../../lib/fleetTerminology'
import { HelpPopover } from './HelpPopover'

interface Props {
  termId: string
  children?: ReactNode
  className?: string
  showHelp?: boolean
}

/** Dual-label field header: industry or plain label plus optional help. */
export function FieldLabel({ termId, children, className = '', showHelp = true }: Props) {
  const { uiMode } = useUiMode()
  const term = getTerm(termId)
  const primary = labelForTerm(termId, uiMode)
  const secondary = term && uiMode === 'standard' ? term.industryLabel : term?.plainLabel

  return (
    <div className={`space-y-1 ${className}`}>
      <div className="flex items-center gap-1.5">
        <span className="text-text-secondary text-xs font-medium">{primary}</span>
        {showHelp && <HelpPopover termId={termId} />}
      </div>
      {term && (
        <p className="text-[10px] text-text-secondary/80 leading-snug">
          {uiMode === 'standard' ? term.description : secondary}
        </p>
      )}
      {children}
    </div>
  )
}
