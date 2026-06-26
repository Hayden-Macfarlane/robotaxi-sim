import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { RuleV2 } from '../types/playbook'
import type { RuleCreationMode } from '../types/playbook'

export type UiMode = 'standard' | 'expert'

export type SidebarTabId = 'rules' | 'live'

export type RulesSubTabId = 'build' | 'monitor' | 'library'

export type LibraryViewId = 'constraints' | 'thresholds' | 'templates' | 'actions'

export type SettingsSectionId = 'dispatch' | 'market' | 'operations' | 'analyze'

export type LiveSubTabId = 'fleet' | 'orders'

interface NavigateTarget {
  tab?: SidebarTabId
  rulesSubTab?: RulesSubTabId
  libraryView?: LibraryViewId
  liveSubTab?: LiveSubTabId
  settingsOpen?: boolean
  settingsSection?: SettingsSectionId
  highlightRuleId?: string | null
  highlightVehicleId?: string | null
}

interface UiModeContextValue {
  uiMode: UiMode
  setUiMode: (mode: UiMode) => void
  glossaryOpen: boolean
  setGlossaryOpen: (open: boolean) => void
  activeTab: SidebarTabId
  setActiveTab: (tab: SidebarTabId) => void
  rulesSubTab: RulesSubTabId
  setRulesSubTab: (tab: RulesSubTabId) => void
  libraryView: LibraryViewId
  setLibraryView: (view: LibraryViewId) => void
  liveSubTab: LiveSubTabId
  setLiveSubTab: (tab: LiveSubTabId) => void
  settingsOpen: boolean
  setSettingsOpen: (open: boolean) => void
  settingsSection: SettingsSectionId
  setSettingsSection: (section: SettingsSectionId) => void
  highlightRuleId: string | null
  setHighlightRuleId: (id: string | null) => void
  pendingMetricId: string | null
  setPendingMetricId: (id: string | null) => void
  pendingWizardDraft: RuleV2 | null
  pendingWizardMode: RuleCreationMode
  setPendingWizardDraft: (draft: RuleV2 | null, mode?: RuleCreationMode) => void
  navigate: (target: NavigateTarget) => void
}

const UiModeContext = createContext<UiModeContextValue | null>(null)

/** UI mode, navigation, and glossary state for the control tower. */
export function UiModeProvider({ children }: { children: ReactNode }) {
  const [uiMode, setUiMode] = useState<UiMode>('standard')
  const [glossaryOpen, setGlossaryOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<SidebarTabId>('rules')
  const [rulesSubTab, setRulesSubTab] = useState<RulesSubTabId>('build')
  const [libraryView, setLibraryView] = useState<LibraryViewId>('constraints')
  const [liveSubTab, setLiveSubTab] = useState<LiveSubTabId>('fleet')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsSection, setSettingsSection] = useState<SettingsSectionId>('dispatch')
  const [highlightRuleId, setHighlightRuleId] = useState<string | null>(null)
  const [pendingMetricId, setPendingMetricId] = useState<string | null>(null)
  const [pendingWizardDraft, setPendingWizardDraftState] = useState<RuleV2 | null>(null)
  const [pendingWizardMode, setPendingWizardMode] = useState<RuleCreationMode>('wizard')

  const setPendingWizardDraft = useCallback((draft: RuleV2 | null, mode: RuleCreationMode = 'wizard') => {
    setPendingWizardDraftState(draft)
    setPendingWizardMode(mode)
  }, [])

  const navigate = useCallback((target: NavigateTarget) => {
    if (target.tab) setActiveTab(target.tab)
    if (target.rulesSubTab) setRulesSubTab(target.rulesSubTab)
    if (target.libraryView) setLibraryView(target.libraryView)
    if (target.liveSubTab) setLiveSubTab(target.liveSubTab)
    if (target.settingsOpen !== undefined) setSettingsOpen(target.settingsOpen)
    if (target.settingsSection) setSettingsSection(target.settingsSection)
    if (target.highlightRuleId !== undefined) setHighlightRuleId(target.highlightRuleId)
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
      rulesSubTab,
      setRulesSubTab,
      libraryView,
      setLibraryView,
      liveSubTab,
      setLiveSubTab,
      settingsOpen,
      setSettingsOpen,
      settingsSection,
      setSettingsSection,
      highlightRuleId,
      setHighlightRuleId,
      pendingMetricId,
      setPendingMetricId,
      pendingWizardDraft,
      pendingWizardMode,
      setPendingWizardDraft,
      navigate,
    }),
    [
      uiMode,
      glossaryOpen,
      activeTab,
      rulesSubTab,
      libraryView,
      liveSubTab,
      settingsOpen,
      settingsSection,
      highlightRuleId,
      pendingMetricId,
      pendingWizardDraft,
      pendingWizardMode,
      navigate,
      setPendingWizardDraft,
    ],
  )

  return <UiModeContext.Provider value={value}>{children}</UiModeContext.Provider>
}

/** Access UI mode and navigation context. */
export function useUiMode(): UiModeContextValue {
  const ctx = useContext(UiModeContext)
  if (!ctx) throw new Error('useUiMode must be used within UiModeProvider')
  return ctx
}
