import api from './client'

export interface Card {
  card_id: string
  name: string
  cost: number | null
  power: number | null
  counter: number
  type: string
  color: string[]
  traits: string[]
  attribute: string | null
  keywords: string[]
  roles: string[]
  effect: string
  life: number | null
  set_id: string
  set_name: string
  rarity: string
  image_url: string
  unlimited_copies: boolean
}

export async function getCards(params?: Record<string, unknown>): Promise<{ cards: Card[]; total: number }> {
  const { data } = await api.get('/cards', { params })
  return data
}

export async function getCardById(id: string): Promise<Card> {
  const { data } = await api.get(`/cards/${id}`)
  return data
}

export async function searchCards(q: string): Promise<{ cards: Card[]; total: number }> {
  const { data } = await api.get('/cards/search', { params: { q } })
  return data
}