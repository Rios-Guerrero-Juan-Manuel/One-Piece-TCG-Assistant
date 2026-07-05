import api from './client'

export interface FormatInfo {
  format_name: string
  banned_cards: string[]
  banned_sets: string[]
  banned_blocks: string[]
  banned_pair1: string[]
  banned_pair2: string[]
}

export async function getFormats(): Promise<{ formats: FormatInfo[] }> {
  const { data } = await api.get('/formats')
  return data
}