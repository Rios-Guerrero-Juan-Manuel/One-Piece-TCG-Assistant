import api from './client'

export interface MatchListItem {
  match_id: string
  source_file: string
  leader_self: string
  leader_opp: string
  opponent_user: string | null
  result: string
  reason: string | null
  duration_turns: number | null
  deck_id_self: string | null
  deck_id_opp: string | null
  played_at: string | null
}

export interface CounterAction {
  card_id?: string
  name?: string | null
  value?: number
  actor?: string | null
  [key: string]: unknown
}

export interface AttackAction {
  attacker?: string
  attacker_name?: string | null
  target?: string
  target_name?: string | null
  attacker_power?: number
  defender_power?: number
  result?: string | null
  damage?: number | null
  counters?: CounterAction[]
  [key: string]: unknown
}

export interface CardPlayed {
  card_id?: string
  name?: string | null
}

export interface MatchTurn {
  turn_no: number
  player_idx: number
  don_drawn: number
  don_unused: number
  cards_played: CardPlayed[]
  attacks: AttackAction[]
  counters: CounterAction[]
  errors: string[]
  state_end: Record<string, unknown>
}

export interface MatchDetail {
  match_id: string
  room_id: string | null
  version: string | null
  source_file: string
  leader_self: string
  leader_opp: string
  opponent_user: string | null
  result: string
  reason: string | null
  duration_turns: number | null
  deck_id_self: string | null
  deck_id_opp: string | null
  self_player_idx: number | null
  turns: MatchTurn[]
  card_names: Record<string, string>
}

export interface ImportResult {
  match_id: string
  source_file: string
  result: string
  turns: number
  leader_self: string
  leader_opp: string
  deck_id_self: string | null
  deck_id_opp: string | null
}

export interface FileImportResultEntry {
  filename: string
  success: boolean
  match_id: string | null
  turns: number | null
  error: string | null
}

export interface BatchImportResult {
  imported: number
  errors: number
  total: number
  results: FileImportResultEntry[]
}

export async function getMatches(
  skip?: number,
  limit?: number,
): Promise<{ matches: MatchListItem[]; total: number }> {
  const params: Record<string, number> = {}
  if (skip !== undefined) params.skip = skip
  if (limit !== undefined) params.limit = limit
  const { data } = await api.get<{ matches: MatchListItem[]; total: number }>('/matches', { params })
  return data
}

export async function getMatch(match_id: string): Promise<MatchDetail> {
  const { data } = await api.get<MatchDetail>(`/matches/${match_id}`)
  return data
}

export async function importMatch(file: File): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<ImportResult>('/matches/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function importDirectory(): Promise<BatchImportResult> {
  const { data } = await api.post<BatchImportResult>('/matches/import-directory')
  return data
}

export async function importMatchesBatch(files: File[]): Promise<BatchImportResult> {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  const { data } = await api.post<BatchImportResult>('/matches/import-batch', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function assignMatchDeck(
  matchId: string,
  deckIdSelf: string | null,
  deckIdOpp: string | null,
): Promise<{ match_id: string; deck_id_self: string | null; deck_id_opp: string | null }> {
  const { data } = await api.put(`/matches/${matchId}/deck-assignment`, {
    deck_id_self: deckIdSelf,
    deck_id_opp: deckIdOpp,
  })
  return data
}

export async function autoAssignMatchDeck(
  matchId: string,
): Promise<{ match_id: string; deck_id_self: string | null; deck_id_opp: string | null }> {
  const { data } = await api.post(`/matches/${matchId}/auto-assign-deck`)
  return data
}
