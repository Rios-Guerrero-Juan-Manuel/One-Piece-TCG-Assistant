import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { I18nProvider, useI18n } from './i18n/context'
import Dashboard from './pages/Dashboard'
import DeckBuilder from './pages/DeckBuilder'
import MatchAnalyzer from './pages/MatchAnalyzer'
import CollectionManager from './pages/CollectionManager'
import MetaReport from './pages/MetaReport'
import Settings from './pages/Settings'

function Sidebar() {
  const { t } = useI18n()
  return (
    <aside className="sidebar">
      <div className="sidebar-title">{t('app.title')}</div>
      <ul className="sidebar-nav">
        <li><NavLink to="/">{t('nav.dashboard')}</NavLink></li>
        <li><NavLink to="/deck-builder">{t('nav.deck_builder')}</NavLink></li>
        <li><NavLink to="/match-analyzer">{t('nav.match_analyzer')}</NavLink></li>
        <li><NavLink to="/collection">{t('nav.collection')}</NavLink></li>
        <li><NavLink to="/meta">{t('nav.meta_report')}</NavLink></li>
        <li><NavLink to="/settings">{t('nav.settings')}</NavLink></li>
      </ul>
    </aside>
  )
}

export default function App() {
  return (
    <I18nProvider>
      <BrowserRouter>
        <div className="app-layout">
          <Sidebar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/deck-builder" element={<DeckBuilder />} />
              <Route path="/match-analyzer" element={<MatchAnalyzer />} />
              <Route path="/collection" element={<CollectionManager />} />
              <Route path="/meta" element={<MetaReport />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </I18nProvider>
  )
}