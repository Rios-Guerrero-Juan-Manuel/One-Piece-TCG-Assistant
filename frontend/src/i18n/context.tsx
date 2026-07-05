import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import es from '../i18n/es.json'
import en from '../i18n/en.json'

type Translations = Record<string, string>

const _translations: Record<string, Translations> = { es, en }

interface I18nContextValue {
  lang: string
  setLang: (lang: string) => void
  t: (key: string, fallback?: string) => string
}

const I18nContext = createContext<I18nContextValue>({
  lang: 'es',
  setLang: () => {},
  t: (_key: string, fallback?: string) => fallback ?? _key,
})

export function I18nProvider({ children, initialLang }: {
  children: ReactNode
  initialLang?: string
}) {
  const [lang, setLangState] = useState(() => {
    return localStorage.getItem('optcg-lang') || initialLang || 'en'
  })

  const setLang = useCallback((newLang: string) => {
    setLangState(newLang)
    localStorage.setItem('optcg-lang', newLang)
  }, [])

  useEffect(() => {
    localStorage.setItem('optcg-lang', lang)
  }, [lang])

  const t = useCallback((key: string, fallback?: string) => {
    const dict = _translations[lang] || _translations.es
    return dict[key] ?? fallback ?? key
  }, [lang])

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  return useContext(I18nContext)
}
