import { useState, useEffect, useCallback } from 'react'
import {
  getDecks,
  type DeckListItem,
} from '../api/decks'
import {
  getRecommendations,
  generateRecommendations,
  type Recommendation,
} from '../api/recommendations'
import { useI18n } from '../i18n/context'

export default function Recommendations() {
  const { t } = useI18n()
  const [deckList, setDeckList] = useState<DeckListItem[]>([])
  const [selectedDeckId, setSelectedDeckId] = useState<string | null>(null)
  const [recs, setRecs] = useState<Recommendation[]>([])
  const [loadingList, setLoadingList] = useState(false)
  const [loadingRecs, setLoadingRecs] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  const loadDeckList = useCallback(async () => {
    setLoadingList(true)
    try {
      const decks = await getDecks()
      setDeckList(decks)
    } catch (err) {
      console.error('Failed to load decks', err)
      setError(t('recommendations.error_load_decks'))
    } finally {
      setLoadingList(false)
    }
  }, [t])

  useEffect(() => {
    loadDeckList()
  }, [loadDeckList])

  const loadRecs = useCallback(async (deckId: string) => {
    setLoadingRecs(true)
    setError('')
    try {
      const data = await getRecommendations(deckId)
      setRecs(data)
    } catch (err) {
      console.error('Failed to load recommendations', err)
      setError(t('recommendations.error_load_recs'))
      setRecs([])
    } finally {
      setLoadingRecs(false)
    }
  }, [t])

  useEffect(() => {
    if (selectedDeckId) {
      loadRecs(selectedDeckId)
    } else {
      setRecs([])
    }
  }, [selectedDeckId, loadRecs])

  const handleGenerate = async () => {
    if (!selectedDeckId) return
    setGenerating(true)
    setError('')
    try {
      const data = await generateRecommendations(selectedDeckId)
      setRecs(data)
    } catch (err) {
      console.error('Failed to generate recommendations', err)
      setError(t('recommendations.error_generate'))
      setRecs([])
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div>
      <h1 className="page-title">{t('recommendations.title')}</h1>

      {error && (
        <div style={{ color: 'var(--error)', marginBottom: '1rem', fontSize: '0.85rem' }}>{error}</div>
      )}

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Left panel: deck list */}
        <div style={{ flex: '1 1 260px', minWidth: '260px', maxWidth: '320px' }}>
          <div className="card" style={{ padding: '1rem' }}>
            <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
              {t('recommendations.decks')} <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>({deckList.length})</span>
            </h2>
            {loadingList ? (
              <p style={{ color: 'var(--text-secondary)' }}>{t('common.loading')}</p>
            ) : deckList.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>{t('recommendations.no_decks')}</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {deckList.map((d) => (
                  <li
                    key={d.deck_id}
                    onClick={() => setSelectedDeckId(d.deck_id)}
                    style={listItemStyle(selectedDeckId === d.deck_id)}
                  >
                    <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{d.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {d.leader_card_id} · {d.card_count} {t('deck_builder.cards')}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Right panel: recommendations */}
        <div style={{ flex: '2 1 400px', minWidth: '300px' }}>
          {!selectedDeckId ? (
            <div className="card placeholder">
              <p>{t('recommendations.no_deck_selected')}</p>
            </div>
          ) : (
            <>
              <div className="card" style={{ padding: '1rem 1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h2 style={{ fontSize: '1rem', fontWeight: 600 }}>
                      {deckList.find((d) => d.deck_id === selectedDeckId)?.name || selectedDeckId}
                    </h2>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {recs.length} {recs.length !== 1 ? t('recommendations.recommendations') : t('recommendations.recommendation')}
                    </p>
                  </div>
                  <button
                    className="btn"
                    onClick={handleGenerate}
                    disabled={generating}
                    style={{ opacity: generating ? 0.6 : 1 }}
                  >
                    {generating ? t('recommendations.generating') : t('recommendations.generate')}
                  </button>
                </div>
              </div>

              {loadingRecs ? (
                <div className="card placeholder">
                  <p>{t('recommendations.loading_recs')}</p>
                </div>
              ) : recs.length === 0 ? (
                <div className="card placeholder">
                  <p>{t('recommendations.no_recs')}</p>
                </div>
              ) : (
                recs.map((rec) => (
                  <RecommendationCard key={rec.rec_id} rec={rec} />
                ))
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function RecommendationCard({ rec }: {
  rec: Recommendation
}) {
  const { t } = useI18n()
  const score = rec.score
  const scoreColor = score >= 70 ? 'var(--success)' : score >= 50 ? 'var(--accent)' : 'var(--warning)'
  const rationale = rec.rationale || {}
  const rolesGained = rationale.roles_gained || []
  const rolesLost = rationale.roles_lost || []
  const problem = rationale.problem || 'unknown'
  const description = rationale.description || ''
  const costDelta = rationale.cost_delta

  return (
    <div className="card" style={{ padding: '1rem 1.25rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <span style={scoreBadgeStyle(scoreColor)}>{score}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>
            <span style={{ color: 'var(--text-secondary)', textDecoration: 'line-through' }}>
              {rec.card_out || '—'}
            </span>
            <span style={{ color: 'var(--text-secondary)', margin: '0 0.3rem' }}>→</span>
            <span style={{ color: 'var(--accent)' }}>{rec.card_in}</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            {problem}
          </div>
        </div>
        <span style={problemBadgeStyle()}>{problem.replace(/_/g, ' ')}</span>
      </div>

      {/* Description */}
      {description && (
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
          {description}
        </p>
      )}

      {/* Roles */}
      {(rolesGained.length > 0 || rolesLost.length > 0) && (
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.4rem' }}>
          {rolesGained.length > 0 && (
            <div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{t('recommendations.gains')} </span>
              {rolesGained.map((r) => (
                <span key={r} style={roleBadgeStyle('gain')}>{r}</span>
              ))}
            </div>
          )}
          {rolesLost.length > 0 && (
            <div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{t('recommendations.loses')} </span>
              {rolesLost.map((r) => (
                <span key={r} style={roleBadgeStyle('loss')}>{r}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Cost delta */}
      {costDelta != null && costDelta !== 0 && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          {t('recommendations.cost')}: {costDelta > 0 ? '+' : ''}{costDelta} DON
        </div>
      )}
    </div>
  )
}

function listItemStyle(selected: boolean): React.CSSProperties {
  return {
    padding: '0.5rem 0.6rem',
    borderRadius: '4px',
    cursor: 'pointer',
    marginBottom: '4px',
    background: selected ? 'var(--bg-primary)' : 'transparent',
    borderLeft: selected ? '3px solid var(--accent)' : '3px solid transparent',
    transition: 'background 0.15s',
  }
}

function scoreBadgeStyle(color: string): React.CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '40px',
    height: '40px',
    borderRadius: '6px',
    fontSize: '1rem',
    fontWeight: 700,
    background: `${color}22`,
    color,
    border: `1px solid ${color}55`,
    flexShrink: 0,
  }
}

function problemBadgeStyle(): React.CSSProperties {
  return {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '0.7rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    background: 'var(--bg-primary)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
  }
}

function roleBadgeStyle(type: 'gain' | 'loss'): React.CSSProperties {
  return {
    display: 'inline-block',
    padding: '1px 6px',
    marginRight: '4px',
    marginBottom: '2px',
    borderRadius: '3px',
    fontSize: '0.72rem',
    background: type === 'gain' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
    color: type === 'gain' ? 'var(--success)' : 'var(--error)',
    border: `1px solid ${type === 'gain' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
  }
}
