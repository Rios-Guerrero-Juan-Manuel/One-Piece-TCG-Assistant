import { useState, useEffect, useCallback } from 'react'
import { Card, getCards, searchCards } from '../api/cards'
import { getCollection, updateOwned, importCollection, importCollectionCsv, exportCollection } from '../api/collection'
import { useI18n } from '../i18n/context'

const COLORS = ['Red', 'Blue', 'Green', 'Black', 'Yellow', 'Purple']
const TYPES = ['Leader', 'Character', 'Event', 'Stage']

export default function CollectionManager() {
  const { t } = useI18n()
  const [cards, setCards] = useState<Card[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [pageSize] = useState(50)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [filterColor, setFilterColor] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterCost, setFilterCost] = useState('')
  const [ownedMap, setOwnedMap] = useState<Record<string, number>>({})
  const [selectedCard, setSelectedCard] = useState<Card | null>(null)
  const [status, setStatus] = useState('')

  const loadCollection = useCallback(async () => {
    try {
      const data = await getCollection()
      const map: Record<string, number> = {}
      data.items.forEach((item) => { map[item.card_id] = item.owned })
      setOwnedMap(map)
    } catch (err) {
      console.error('Failed to load collection', err)
    }
  }, [])

  const loadCards = useCallback(async () => {
    setLoading(true)
    try {
      let data
      if (search) {
        data = await searchCards(search)
        setCards(data.cards)
        setTotal(data.total)
      } else {
        const params: Record<string, unknown> = {
          skip: page * pageSize,
          limit: pageSize,
        }
        if (filterColor) params.color = filterColor
        if (filterType) params.type = filterType
        if (filterCost) params.cost = filterCost
        data = await getCards(params)
        setCards(data.cards)
        setTotal(data.total)
      }
    } catch (err) {
      console.error('Failed to load cards', err)
    } finally {
      setLoading(false)
    }
  }, [search, page, pageSize, filterColor, filterType, filterCost])

  useEffect(() => {
    loadCollection()
  }, [loadCollection])

  useEffect(() => {
    loadCards()
  }, [loadCards])

  const handleOwnedChange = async (cardId: string, value: string) => {
    const owned = parseInt(value) || 0
    setOwnedMap(prev => ({ ...prev, [cardId]: owned }))
    try {
      await updateOwned(cardId, owned)
    } catch (err) {
      console.error('Failed to update owned', err)
    }
  }

  const handleExport = async () => {
    try {
      const data = await exportCollection()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'collection.json'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed', err)
    }
  }

  const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    if (file.name.toLowerCase().endsWith('.csv')) {
      const formData = new FormData()
      formData.append('file', file)
      importCollectionCsv(formData)
        .then(async (res) => {
          const parts = [`${res.imported} ${t('collection.cards')} (${res.total_owned} ${t('collection.copies')})`]
          if (res.removed) parts.push(`${res.removed} ${t('collection.removed')}`)
          const skipped = res.skipped_japanese + res.skipped_other_tcg + res.skipped_no_card_number
          if (skipped) parts.push(`${skipped} ${t('collection.skipped')}`)
          if (res.missing_card_ids.length) parts.push(`${res.missing_card_ids.length} ${t('collection.not_found')}`)
          if (res.synced) parts.push(t('collection.synced'))
          if (res.sync_failed) parts.push(t('collection.sync_failed'))
          setStatus(t('collection.csv_imported') + ': ' + parts.join(', '))
          await loadCollection()
        })
        .catch((err) => {
          console.error('CSV import failed', err)
          setStatus(t('collection.import_error'))
        })
      return
    }

    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const items = JSON.parse(e.target?.result as string)
        await importCollection(items)
        await loadCollection()
        setStatus(t('collection.imported'))
      } catch (err) {
        console.error('Import failed', err)
        setStatus(t('collection.file_import_error'))
      }
    }
    reader.readAsText(file)
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div>
      <h1 className="page-title">{t('collection.title')}</h1>

      <div className="card" style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder={t('collection.search_placeholder')}
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0) }}
          style={{ flex: 1, minWidth: '200px', padding: '0.5rem', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: '4px', color: 'var(--text-primary)' }}
        />
        <select value={filterColor} onChange={(e) => { setFilterColor(e.target.value); setPage(0) }} style={{ padding: '0.5rem', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: '4px', color: 'var(--text-primary)' }}>
          <option value="">{t('collection.all_colors')}</option>
          {COLORS.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={filterType} onChange={(e) => { setFilterType(e.target.value); setPage(0) }} style={{ padding: '0.5rem', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: '4px', color: 'var(--text-primary)' }}>
          <option value="">{t('collection.all_types')}</option>
          {TYPES.map(tp => <option key={tp} value={tp}>{tp}</option>)}
        </select>
        <select value={filterCost} onChange={(e) => { setFilterCost(e.target.value); setPage(0) }} style={{ padding: '0.5rem', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: '4px', color: 'var(--text-primary)' }}>
          <option value="">{t('collection.all_costs')}</option>
          {[0,1,2,3,4,5,6,7,8,9,10].map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <button className="btn" onClick={handleExport}>{t('common.export')}</button>
        <label className="btn" style={{ cursor: 'pointer' }}>
          {t('common.import')}
          <input type="file" accept=".json,.csv" onChange={handleImport} style={{ display: 'none' }} />
        </label>
      </div>

      {status && (
        <p style={{ marginTop: '0.5rem', padding: '0.5rem 0.75rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          {status}
        </p>
      )}

      {loading ? (
        <div className="card placeholder"><p>{t('collection.loading_cards')}</p></div>
      ) : (
        <>
          <div className="card" style={{ padding: 0, overflow: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border)' }}>
                  <th style={thStyle}>{t('collection.col_image')}</th>
                  <th style={thStyle}>{t('collection.col_name')}</th>
                  <th style={thStyle}>{t('collection.col_set')}</th>
                  <th style={thStyle}>{t('collection.col_type')}</th>
                  <th style={thStyle}>{t('collection.col_color')}</th>
                  <th style={thStyle}>{t('collection.col_cost')}</th>
                  <th style={thStyle}>{t('collection.col_power')}</th>
                  <th style={thStyle}>{t('collection.col_counter')}</th>
                  <th style={thStyle}>{t('collection.col_roles')}</th>
                  <th style={thStyle}>{t('collection.owned')}</th>
                </tr>
              </thead>
              <tbody>
                {cards.map(card => (
                  <tr
                    key={card.card_id}
                    style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                    onClick={() => setSelectedCard(card)}
                  >
                    <td style={tdStyle}>
                      {card.image_url && (
                        <img src={card.image_url} alt={card.name} style={{ width: '40px', height: '56px', borderRadius: '3px' }} />
                      )}
                    </td>
                    <td style={tdStyle}>{card.name}</td>
                    <td style={tdStyle}>{card.set_id}</td>
                    <td style={tdStyle}>{card.type}</td>
                    <td style={tdStyle}>{card.color.join(', ')}</td>
                    <td style={tdStyle}>{card.cost ?? '-'}</td>
                    <td style={tdStyle}>{card.power ?? '-'}</td>
                    <td style={tdStyle}>{card.counter > 0 ? `+${card.counter}` : '-'}</td>
                    <td style={tdStyle}>{card.roles.join(', ')}</td>
                    <td style={tdStyle} onClick={(e) => e.stopPropagation()}>
                      <input
                        type="number"
                        min="0"
                        value={ownedMap[card.card_id] || 0}
                        onChange={(e) => handleOwnedChange(card.card_id, e.target.value)}
                        style={{ width: '50px', padding: '2px 4px', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: '3px', color: 'var(--text-primary)' }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
            <button className="btn" disabled={page === 0} onClick={() => setPage(p => p - 1)}>{t('common.prev')}</button>
            <span style={{ color: 'var(--text-secondary)' }}>
              {t('collection.page')} {page + 1} {t('collection.of')} {totalPages || 1} ({total} {t('collection.cards')})
            </span>
            <button className="btn" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>{t('common.next')}</button>
          </div>
        </>
      )}

      {selectedCard && (
        <div onClick={() => setSelectedCard(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div onClick={(e) => e.stopPropagation()} className="card" style={{ maxWidth: '500px', display: 'flex', gap: '1.5rem' }}>
            {selectedCard.image_url && (
              <img src={selectedCard.image_url} alt={selectedCard.name} style={{ width: '200px', borderRadius: '8px' }} />
            )}
            <div style={{ flex: 1 }}>
              <h2 style={{ marginBottom: '0.5rem' }}>{selectedCard.name}</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}><strong>{t('collection.modal_id')}:</strong> {selectedCard.card_id}</p>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}><strong>{t('collection.modal_type')}:</strong> {selectedCard.type}</p>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}><strong>{t('collection.modal_color')}:</strong> {selectedCard.color.join(', ')}</p>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}><strong>{t('collection.modal_cost')}:</strong> {selectedCard.cost ?? '-'}</p>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}><strong>{t('collection.modal_power')}:</strong> {selectedCard.power ?? '-'}</p>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}><strong>{t('collection.modal_counter')}:</strong> {selectedCard.counter > 0 ? `+${selectedCard.counter}` : '-'}</p>
              {selectedCard.life && <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}><strong>{t('collection.modal_life')}:</strong> {selectedCard.life}</p>}
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}><strong>{t('collection.modal_traits')}:</strong> {selectedCard.traits.join(', ')}</p>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}><strong>{t('collection.modal_keywords')}:</strong> {selectedCard.keywords.join(', ')}</p>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}><strong>{t('collection.modal_roles')}:</strong> {selectedCard.roles.join(', ')}</p>
              <p style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>{selectedCard.effect}</p>
              {selectedCard.unlimited_copies && <p style={{ color: 'var(--accent)', marginTop: '0.5rem' }}>{t('collection.unlimited')}</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const thStyle: React.CSSProperties = {
  padding: '0.75rem',
  textAlign: 'left',
  fontSize: '0.875rem',
  color: 'var(--text-secondary)',
  whiteSpace: 'nowrap',
}

const tdStyle: React.CSSProperties = {
  padding: '0.5rem 0.75rem',
  fontSize: '0.875rem',
  whiteSpace: 'nowrap',
}
