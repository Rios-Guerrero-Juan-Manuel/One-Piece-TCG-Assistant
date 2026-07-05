import api from './client'

export interface Insight {
  doc_id: string
  title: string
  content: string
  hash: string
  expandable?: boolean
}

export async function getInsights(): Promise<Insight[]> {
  const { data } = await api.get<Insight[]>('/knowledge/insights')
  return data
}

export async function generateInsights(): Promise<Insight[]> {
  const { data } = await api.post<Insight[]>('/knowledge/insights/generate')
  return data
}