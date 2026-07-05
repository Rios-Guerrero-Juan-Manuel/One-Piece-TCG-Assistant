import api from './client'

export interface CollectionItem {
  card_id: string
  owned: number
}

export interface CollectionResponse {
  items: CollectionItem[]
}

export async function getCollection(): Promise<CollectionResponse> {
  const { data } = await api.get('/collection')
  return data
}

export async function updateOwned(card_id: string, owned: number): Promise<CollectionItem> {
  const { data } = await api.post('/collection', { card_id, owned })
  return data
}

export async function importCollection(items: Record<string, number>): Promise<{ imported: number }> {
  const { data } = await api.post('/collection/import', { items })
  return data
}

export async function exportCollection(): Promise<Record<string, number>> {
  const { data } = await api.get('/collection/export')
  return data
}

export interface CsvImportResult {
  imported: number
  total_owned: number
  removed: number
  skipped_other_tcg: number
  skipped_japanese: number
  skipped_no_card_number: number
  synced: boolean
  sync_failed: boolean
  missing_card_ids: string[]
}

export async function importCollectionCsv(formData: FormData): Promise<CsvImportResult> {
  const { data } = await api.post('/collection/import-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}