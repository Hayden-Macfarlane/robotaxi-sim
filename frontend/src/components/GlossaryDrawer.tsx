import { useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { CATEGORY_LABELS, FLEET_TERMS, searchTerms, type TermCategory } from '../lib/fleetTerminology'
import { useUiMode } from '../contexts/UiModeContext'

/** Searchable fleet terminology glossary drawer. */
export function GlossaryDrawer() {
  const { glossaryOpen, setGlossaryOpen, navigate } = useUiMode()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<TermCategory | 'all'>('all')

  const results = useMemo(() => {
    let terms = searchTerms(query)
    if (category !== 'all') terms = terms.filter(t => t.category === category)
    return terms
  }, [query, category])

  if (!glossaryOpen) return null

  // Portal + z-index above Leaflet map panes (~400–1000).
  return createPortal(
    <>
      <button
        type="button"
        className="fixed inset-0 z-[2000] bg-black/50"
        aria-label="Close glossary"
        onClick={() => setGlossaryOpen(false)}
      />
      <aside className="fixed top-0 right-0 bottom-0 z-[2001] w-full max-w-md bg-surface-base border-l border-border-default flex flex-col shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border-default">
          <h2 className="text-sm font-semibold text-text-primary">Fleet glossary</h2>
          <button type="button" onClick={() => setGlossaryOpen(false)} className="text-text-secondary hover:text-text-primary text-sm">
            Close
          </button>
        </div>
        <div className="p-3 space-y-2 border-b border-border-default">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search terms…"
            className="input-dark w-full text-sm"
          />
          <select value={category} onChange={e => setCategory(e.target.value as TermCategory | 'all')} className="input-dark w-full text-xs">
            <option value="all">All categories</option>
            {(Object.keys(CATEGORY_LABELS) as TermCategory[]).map(c => (
              <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
            ))}
          </select>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {results.map(term => (
            <div key={term.id} className="border border-border-default rounded-lg p-3 text-xs">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-medium text-text-primary">{term.industryLabel}</div>
                  <div className="text-accent text-[10px] mt-0.5">{term.plainLabel}</div>
                </div>
                <span className="text-[10px] text-text-secondary shrink-0">{CATEGORY_LABELS[term.category]}</span>
              </div>
              <p className="text-text-secondary mt-2 leading-relaxed">{term.description}</p>
              {term.policySubTab === 'rules' && (
                <button
                  type="button"
                  onClick={() => navigate({ tab: 'rules', rulesSubTab: 'library', libraryView: 'constraints' })}
                  className="text-accent hover:underline mt-2 text-[10px]"
                >
                  Open Rules → Library
                </button>
              )}
              {term.policySubTab === 'market' && (
                <button
                  type="button"
                  onClick={() => navigate({ settingsOpen: true, settingsSection: 'market' })}
                  className="text-accent hover:underline mt-2 text-[10px]"
                >
                  Open Settings → Market
                </button>
              )}
              {term.policySubTab === 'operations' && (
                <button
                  type="button"
                  onClick={() => navigate({ settingsOpen: true, settingsSection: 'operations' })}
                  className="text-accent hover:underline mt-2 text-[10px]"
                >
                  Open Settings → Operations
                </button>
              )}
              {!term.policySubTab && term.id.startsWith('score_weight') && (
                <button
                  type="button"
                  onClick={() => navigate({ settingsOpen: true, settingsSection: 'analyze' })}
                  className="text-accent hover:underline mt-2 text-[10px]"
                >
                  Open Settings → Performance
                </button>
              )}
            </div>
          ))}
          {results.length === 0 && (
            <p className="text-text-secondary italic text-center py-8">No matching terms</p>
          )}
        </div>
        <div className="px-3 py-2 border-t border-border-default text-[10px] text-text-secondary">
          {FLEET_TERMS.length} terms · Industry labels shown in Expert mode
        </div>
      </aside>
    </>,
    document.body,
  )
}
