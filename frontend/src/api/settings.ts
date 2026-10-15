import api from './client'

export async function getSettings(): Promise<Record<string, string>> {
  const { data } = await api.get('/settings')
  return data.settings
}

export async function updateSettings(settings: Record<string, string>): Promise<void> {
  await api.put('/settings', { settings })
}

export interface LogsDirValidation {
  exists: boolean
  is_dir: boolean
  files_found: number
  autosaved_found: number
}

export async function validateLogsDir(path: string): Promise<LogsDirValidation> {
  const { data } = await api.post<LogsDirValidation>('/settings/validate-logs-dir', { path })
  return data
}