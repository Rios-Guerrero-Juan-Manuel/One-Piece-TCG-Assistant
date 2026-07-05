import api from './client'

export async function getSettings(): Promise<Record<string, string>> {
  const { data } = await api.get('/settings')
  return data.settings
}

export async function updateSettings(settings: Record<string, string>): Promise<void> {
  await api.put('/settings', { settings })
}