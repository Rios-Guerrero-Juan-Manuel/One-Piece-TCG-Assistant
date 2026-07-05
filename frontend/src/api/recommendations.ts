import api from './client'

export interface Recommendation {
  rec_id: string
  deck_id: string | null
  card_out: string | null
  card_in: string
  qty: number
  score: number
  rationale: {
    problem?: string
    description?: string
    card_out?: string
    card_out_name?: string
    card_in?: string
    card_in_name?: string
    roles_gained?: string[]
    role_overlap?: string[]
    roles_lost?: string[]
    cost_delta?: number
    score?: number
    [key: string]: unknown
  }
  created_at: string | null
}

export async function getRecommendations(deckId: string): Promise<Recommendation[]> {
  const { data } = await api.get<Recommendation[]>(`/recommendations/${deckId}`)
  return data
}

export async function generateRecommendations(deckId: string): Promise<Recommendation[]> {
  const { data } = await api.post<Recommendation[]>(`/recommendations/${deckId}/generate`)
  return data
}