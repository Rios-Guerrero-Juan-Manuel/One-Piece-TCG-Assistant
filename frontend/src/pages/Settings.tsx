import { useState, useEffect } from 'react'
import { getSettings, updateSettings } from '../api/settings'
import { useI18n } from '../i18n/context'

export default function Settings() {
  const { t, lang, setLang } = useI18n()
  const [settings, setSettings] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await getSettings()
      setSettings(data)
      if (data.language && data.language !== lang) {
        setLang(data.language)
      }
    } catch (err) {
      console.error('Failed to load settings', err)
    }
  }

  const handleChange = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateSettings(settings)
      setSaved(true)
    } catch (err) {
      console.error('Failed to save settings', err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h1 className="page-title">{t('settings.title')}</h1>
      <div className="card" style={{ maxWidth: '500px', padding: '1.25rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{t('settings.language')}</label>
            <select
              value={lang}
              onChange={(e) => {
                setLang(e.target.value)
                handleChange('language', e.target.value)
              }}
              style={inputStyle}
            >
              <option value="es">{t('stats.spanish')}</option>
              <option value="en">{t('stats.english')}</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{t('settings.self_user')}</label>
            <input
              type="text"
              value={settings.self_user || ''}
              onChange={(e) => handleChange('self_user', e.target.value)}
              placeholder={t('settings.self_user_placeholder')}
              style={inputStyle}
            />
            <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {t('settings.self_user_help')}
            </p>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{t('settings.active_format')}</label>
            <select
              value={settings.active_format || 'Western'}
              onChange={(e) => handleChange('active_format', e.target.value)}
              style={inputStyle}
            >
              <option value="Western">Western</option>
              <option value="Eastern">Eastern</option>
              <option value="Korean">Korean</option>
              <option value="Nationals">Nationals</option>
            </select>
          </div>
          <button className="btn" onClick={handleSave} disabled={saving}>
            {saving ? t('common.loading') : t('settings.save_settings')}
          </button>
          {saved && <p style={{ color: 'var(--success)', fontSize: '0.875rem' }}>{t('settings.saved')}</p>}
        </div>
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.5rem',
  background: 'var(--bg-primary)',
  border: '1px solid var(--border)',
  borderRadius: '4px',
  color: 'var(--text-primary)',
  fontSize: '0.875rem',
}
