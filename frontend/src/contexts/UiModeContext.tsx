import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { PolicySubTab } from '../lib/fleetTerminology'

export type UiMode = 'standard' | 'expert'

export type SidebarTabId = 'live' | 'dispatch' | 'policy' | 'analyze'

export type LiveSubTabId = 'fleet' | 'orders'

interface NavigateTarget {
  tab: SidebarTabId
  policySubTab?: PolicySubTab
  liveSubTab?: LiveSubTabId
}

interface UiModeContextValue {
  uiMode: UiMode
  setUiMode: (mode: UiMode) => void
  glossaryOpen: boolean
  setGlossaryOpen: (open: boolean) => void
  activeTab: SidebarTabId
  setActiveTab: (tab: SidebarTabId) => void
  policySubTab: PolicySubTab
  setPolicySubTab: (tab: PolicySubTab) => void
  liveSubTab: LiveSubTabId
  setLiveSubTab: (tab: LiveSubTabId) => void
  navigate: (target: NavigateTarget) => void
}

const UiModeContext = createContext<UiModeContextValue | null>(null)

/** UI mode, navigation, and glossary state for the control tower. */
export function UiModeProvider({ children }: { children: ReactNode }) {
  const [uiMode, setUiMode] = useState<UiMode>('standard')
  const [glossaryOpen, setGlossaryOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<SidebarTabId>('live')
  const [policySubTab, setPolicySubTab] = useState<PolicySubTab>('matching')
  const [liveSubTab, setLiveSubTab] = useState<LiveSubTabId>('fleet')

  const navigate = useCallback((target: NavigateTarget) => {
    setActiveTab(target.tab)
    if (target.policySubTab) setPolicySubTab(target.policySubTab)
    if (target.liveSubTab) setLiveSubTab(target.liveSubTab)
    setGlossaryOpen(false)
  }, [])

  const value = useMemo(
    () => ({
      uiMode,
      setUiMode,
      glossaryOpen,
      setGlossaryOpen,
      activeTab,
      setActiveTab,
      policySubTab,
      setPolicySubTab,
      liveSubTab,
      setLiveSubTab,
      navigate,
    }),
    [uiMode, glossaryOpen, activeTab, policySubTab, liveSubTab, navigate],
  )

  return <UiModeContext.Provider value={value}>{children}</UiModeContext.Provider>
}

export function useUiMode(): UiModeContextValue {
  const ctx = useContext(UiModeContext)
  if (!ctx) throw new Error('useUiMode must be used within UiModeProvider')
  return ctx
}
