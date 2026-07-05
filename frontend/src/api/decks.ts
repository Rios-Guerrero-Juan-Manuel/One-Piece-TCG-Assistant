import api from './client'

export interface DeckListItem {
  deck_id: string
  name: string
  leader_card_id: string
  source: string | null
  card_count: number
  version: number
}

export interface DeckCard {
  card_id: string
  name: string
  cost: number | null
  power: number | null
  counter: number
  type: string
  color: string[]
  traits: string[]
  keywords: string[]
  roles: string[]
  effect: string
  image_url: string
  set_id: string
  qty: number
}

export interface DeckDetail {
  deck_id: string
  name: string
  leader_card_id: string
  source: string | null
  event: string | null
  date: string | null
  version: number
  cards: DeckCard[]
}

export interface ValidationResult {
  errors: string[]
  warnings: string[]
}

export interface DeckScore {
  deck_id: string
  overall: number
  breakdown: Record<string, number>
  version: number
}

export interface MissingCard {
  card_id: string
  name: string
  needed: number
  owned: number
  missing: number
  avg_price: number | null
  extended_price: number | null
}

export interface SubstitutionSuggestion {
  card_out_id: string
  card_in_id: string
  card_in_name: string
  score: number
  image_url: string | null
}

export interface CompleteDeckResponse {
  missing: MissingCard[]
  substitutions: SubstitutionSuggestion[]
  validation: ValidationResult
  total_missing_price: number | null
}

export interface ImportDeckResponse {
  deck_id: string
  name: string
  leader_card_id: string
  card_count: number
  version: number
}

export interface DeckVersion {
  deck_id: string
  name: string
  version: number
  card_count: number
  created_at: string | null
}

export async function getDecks(): Promise<DeckListItem[]> {
  const { data } = await api.get('/decks')
  return data.decks
}

export async function getDeck(deck_id: string): Promise<DeckDetail> {
  const { data } = await api.get(`/decks/${deck_id}`)
  return data
}

export async function getDeckVersions(leaderCardId: string): Promise<DeckVersion[]> {
  const { data } = await api.get<{ leader_card_id: string; versions: DeckVersion[] }>(
    `/decks/leader/${leaderCardId}/versions`,
  )
  return data.versions
}

export async function deleteDeck(deck_id: string): Promise<void> {
  await api.delete(`/decks/${deck_id}`)
}

export async function importDeck(
  name: string,
  text: string,
  source?: string,
  mode?: string,
  leaderCardId?: string,
): Promise<ImportDeckResponse> {
  const { data } = await api.post('/decks/import', { name, text, source, mode, leader_card_id: leaderCardId })
  return data
}

export async function validateDeck(deck_id: string, format_name?: string): Promise<ValidationResult> {
  const params: Record<string, string> = {}
  if (format_name) params.format_name = format_name
  const { data } = await api.post(`/decks/${deck_id}/validate`, null, { params })
  return data
}

export async function getDeckScore(deck_id: string): Promise<DeckScore> {
  const { data } = await api.get(`/decks/${deck_id}/score`)
  return data
}

export async function completeDeck(deck_id: string, format_name?: string): Promise<CompleteDeckResponse> {
  const params: Record<string, string> = {}
  if (format_name) params.format_name = format_name
  const { data } = await api.post(`/decks/${deck_id}/complete`, null, { params })
  return data
}
