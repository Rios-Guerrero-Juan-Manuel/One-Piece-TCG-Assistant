import api from './client'

export interface PopularDeck {
  leader_card_id: string
  deck_count: number
  deck_names: string[]
}

export interface CardUsage {
  card_id: string
  count: number
  trend?: string
}

export interface MetaReport {
  popular_decks: PopularDeck[]
  winrates: Record<string, number>
  most_used_cards: CardUsage[]
  emerging_cards: CardUsage[]
  declining_cards: CardUsage[]
  matchup_table: Record<string, Record<string, number>>
  meta_summary: {
    total_decks: number
    total_matches: number
    top_leader?: string
    top_leader_winrate?: number
    [key: string]: unknown
  }
}

export async function getMetaReport(): Promise<MetaReport> {
  const { data } = await api.get<MetaReport>('/meta/report')
  return data
}

export async function getPopularDecks(): Promise<PopularDeck[]> {
  const { data } = await api.get<PopularDeck[]>('/meta/decks')
  return data
}

export async function computeMeta(): Promise<MetaReport> {
  const { data } = await api.post<MetaReport>('/meta/compute')
  return data
}

export interface Pattern {
  pattern_id: string
  filter: Record<string, unknown>
  description: string
  severity: string
}

export async function getPatterns(): Promise<Pattern[]> {
  const { data } = await api.get<Pattern[]>('/meta/patterns')
  return data
}

export async function detectPatterns(): Promise<Pattern[]> {
  const { data } = await api.post<Pattern[]>('/meta/patterns/detect')
  return data
}

export interface GlobalLeaderStat {
  card_id: string
  name: string
  image_url: string
  wins: number
  losses: number
  matches: number
  winrate: number
  bayesian_winrate: number
  tier: string
  avg_matchup_wr: number
  balance_score: number
  overall_score: number
}

export interface GlobalMetaResponse {
  leaders: GlobalLeaderStat[]
  tiers: Record<string, string[]>
  total_matches: number
  total_wins: number
  total_losses: number
  timestamp: string
  region: string
  ranking: string
  game_mode: string
  source: string
}

export type MetaRegion = 'west' | 'west+' | 'west++' | 'east' | 'east+'
export type MetaView = 'overall' | 'winrate' | 'steady'
export type MetaTurnOrder = 'combined' | 'first' | 'second'

export async function getGlobalMeta(
  region: MetaRegion = 'west',
  view: MetaView = 'overall',
  turn: MetaTurnOrder = 'combined',
): Promise<GlobalMetaResponse> {
  const { data } = await api.get<GlobalMetaResponse>('/meta/global', {
    params: { region, view, turn },
  })
  return data
}

export async function getGlobalMatrix(
  region: MetaRegion = 'west',
  turn: MetaTurnOrder = 'combined',
): Promise<Record<string, Record<string, number | null>>> {
  const { data } = await api.get('/meta/global/matrix', {
    params: { region, turn },
  })
  return data
}