import api from './client'

export async function getTranslations(lang: string): Promise<Record<string, string>> {
  const { data } = await api.get(`/i18n/${lang}`)
  return data
}