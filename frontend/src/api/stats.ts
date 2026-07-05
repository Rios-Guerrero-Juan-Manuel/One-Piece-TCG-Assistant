import api from './client'

export interface MostPlayedCard {
  card_id: string
  count: number
}

export interface StatsData {
  total_matches: number
  winrate: number
  winrate_by_leader: Record<string, number>
  winrate_by_matchup: Record<string, number>
  winrate_by_deck: Record<string, number>
  winrate_by_deck_vs_opp_leader: Record<string, Record<string, number>>
  deck_vs_opp_leader_totals: Record<string, Record<string, number>>
  avg_duration_turns: number
  most_played_cards: MostPlayedCard[]
  avg_don_unused: number
  leaders_used: Record<string, number>
  card_names: Record<string, string>
  deck_names: Record<string, string>
}

export async function getStats(): Promise<StatsData> {
  const { data } = await api.get<StatsData>('/stats')
  return data
}

export interface MatchupStats {
  self_leader: string
  opp_leader: string
  winrate: number
}

export async function getMatchupStats(selfLeader: string, oppLeader: string): Promise<MatchupStats> {
  const { data } = await api.get<MatchupStats>('/stats/matchup', {
    params: { self_leader: selfLeader, opp_leader: oppLeader },
  })
  return data
}

export async function getDeckStats(deckId: string): Promise<StatsData> {
  const { data } = await api.get<StatsData>(`/stats/deck/${deckId}`)
  return data
}
