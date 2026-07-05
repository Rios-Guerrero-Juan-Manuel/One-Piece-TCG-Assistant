import { useState, useEffect, useCallback, useMemo } from 'react'
import { useI18n } from '../i18n/context'
import {
  getDecks,
  getDeck,
  importDeck,
  deleteDeck,
  validateDeck,
  getDeckScore,
  completeDeck,
  type DeckListItem,
  type DeckDetail,
  type ValidationResult,
  type DeckScore,
  type CompleteDeckResponse,
} from '../api/decks'

const COST_BUCKETS = [
  { label: '0-1', min: 0, max: 1 },
  { label: '2-3', min: 2, max: 3 },
  { label: '4-5', min: 4, max: 5 },
  { label: '6+', min: 6, max: Infinity },
]

const FORMAT_NAME = 'Western'

export default function DeckBuilder() {
  const { t } = useI18n()
  const [deckList, setDeckList] = useState<DeckListItem[]>([])
  const [selectedDeckId, setSelectedDeckId] = useState<string | null>(null)
  const [deckDetail, setDeckDetail] = useState<DeckDetail | null>(null)
  const [loadingList, setLoadingList] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const [importName, setImportName] = useState('')
  const [importText, setImportText] = useState('')
  const [importMode, setImportMode] = useState<'new' | 'new_version'>('new')
  const [versionTargetLeader, setVersionTargetLeader] = useState('')
  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState('')

  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [validating, setValidating] = useState(false)

  const [score, setScore] = useState<DeckScore | null>(null)
  const [scoring, setScoring] = useState(false)

  const [completion, setCompletion] = useState<CompleteDeckResponse | null>(null)
  const [completing, setCompleting] = useState(false)

  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [expandedLeaders, setExpandedLeaders] = useState<Set<string>>(new Set())

  const loadDeckList = useCallback(async () => {
    setLoadingList(true)
    try {
      const data = await getDecks()
      setDeckList(data)
    } catch (err) {
      console.error('Failed to load deck list', err)
    } finally {
      setLoadingList(false)
    }
  }, [])

  useEffect(() => {
    loadDeckList()
  }, [loadDeckList])

  const loadDeckDetail = useCallback(async (deckId: string) => {
    setLoadingDetail(true)
    setError('')
    setValidation(null)
    setScore(null)
    setCompletion(null)
    try {
      const data = await getDeck(deckId)
      setDeckDetail(data)
    } catch (err) {
      console.error('Failed to load deck detail', err)
      setError('Failed to load deck detail')
    } finally {
      setLoadingDetail(false)
    }
  }, [])

  useEffect(() => {
    if (selectedDeckId) {
      loadDeckDetail(selectedDeckId)
    } else {
      setDeckDetail(null)
    }
  }, [selectedDeckId, loadDeckDetail])

  const deckGroups = useMemo(() => {
    const groups = new Map<string, DeckListItem[]>()
    for (const d of deckList) {
      const arr = groups.get(d.leader_card_id) ?? []
      arr.push(d)
      groups.set(d.leader_card_id, arr)
    }
    for (const arr of groups.values()) {
      arr.sort((a, b) => b.version - a.version)
    }
    return groups
  }, [deckList])

  const multiVersionLeaderIds = useMemo(
    () => Array.from(deckGroups.entries()).filter(([, arr]) => arr.length > 1).map(([id]) => id),
    [deckGroups],
  )

  const leaderOptions = useMemo(
    () => Array.from(deckGroups.entries()).map(([leaderId, versions]) => {
      const latest = versions[0]
      const baseName = latest.name.replace(/\s+v\d+$/, '')
      return { leaderId, baseName, latestVersion: latest.version }
    }),
    [deckGroups],
  )

  const hasMultiVersions = multiVersionLeaderIds.length > 0
  const allExpanded = multiVersionLeaderIds.length > 0 && multiVersionLeaderIds.every((id) => expandedLeaders.has(id))

  useEffect(() => {
    if (selectedDeckId) {
      const leaderId = deckList.find((d) => d.deck_id === selectedDeckId)?.leader_card_id
      if (leaderId) {
        setExpandedLeaders((prev) => {
          if (prev.has(leaderId)) return prev
          const next = new Set(prev)
          next.add(leaderId)
          return next
        })
      }
    }
  }, [selectedDeckId, deckList])

  const toggleLeader = (leaderId: string) => {
    setExpandedLeaders((prev) => {
      const next = new Set(prev)
      if (next.has(leaderId)) {
        next.delete(leaderId)
      } else {
        next.add(leaderId)
      }
      return next
    })
  }

  const toggleAll = () => {
    if (allExpanded) {
      setExpandedLeaders(new Set())
    } else {
      setExpandedLeaders(new Set(multiVersionLeaderIds))
    }
  }

  const handleImport = async () => {
    if (!importText.trim()) {
      setImportError(t('deck_builder.error_text_required'))
      return
    }
    let name = ''
    let leaderCardId: string | undefined
    if (importMode === 'new_version') {
      if (!versionTargetLeader) {
        setImportError(t('deck_builder.select_deck'))
        return
      }
      const opt = leaderOptions.find((o) => o.leaderId === versionTargetLeader)
      name = opt?.baseName ?? ''
      leaderCardId = versionTargetLeader
    } else {
      if (!importName.trim()) {
        setImportError(t('deck_builder.error_name_required'))
        return
      }
      name = importName.trim()
    }
    setImporting(true)
    setImportError('')
    try {
      const result = await importDeck(name, importText.trim(), undefined, importMode, leaderCardId)
      setImportName('')
      setImportText('')
      setVersionTargetLeader('')
      await loadDeckList()
      setSelectedDeckId(result.deck_id)
    } catch (err: unknown) {
      console.error('Import failed', err)
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (detail && detail.includes('does not match')) {
        setImportError(t('deck_builder.error_leader_mismatch'))
      } else {
        setImportError(t('deck_builder.error_import'))
      }
    } finally {
      setImporting(false)
    }
  }

  const handleDelete = async (deckId: string, deckName: string) => {
    if (!window.confirm(t('deck_builder.delete_confirm').replace('{name}', deckName))) {
      return
    }
    setDeletingId(deckId)
    setError('')
    try {
      await deleteDeck(deckId)
      if (selectedDeckId === deckId) {
        setSelectedDeckId(null)
        setDeckDetail(null)
      }
      await loadDeckList()
    } catch (err) {
      console.error('Delete failed', err)
      setError(t('deck_builder.error_delete'))
    } finally {
      setDeletingId(null)
    }
  }

  const handleValidate = async () => {
    if (!selectedDeckId) return
    setValidating(true)
    try {
      const result = await validateDeck(selectedDeckId, FORMAT_NAME)
      setValidation(result)
    } catch (err) {
      console.error('Validation failed', err)
      setValidation({ errors: [t('deck_builder.error_validate')], warnings: [] })
    } finally {
      setValidating(false)
    }
  }

  const handleScore = async () => {
    if (!selectedDeckId) return
    setScoring(true)
    try {
      const result = await getDeckScore(selectedDeckId)
      setScore(result)
    } catch (err) {
      console.error('Score failed', err)
      setError(t('deck_builder.error_score'))
    } finally {
      setScoring(false)
    }
  }

  const handleComplete = async () => {
    if (!selectedDeckId) return
    setCompleting(true)
    try {
      const result = await completeDeck(selectedDeckId, FORMAT_NAME)
      setCompletion(result)
    } catch (err) {
      console.error('Complete failed', err)
      setError(t('deck_builder.error_complete'))
    } finally {
      setCompleting(false)
    }
  }

  const leader = deckDetail?.cards.find((c) => c.type === 'Leader') ?? null
  const nonLeaderCards = deckDetail?.cards.filter((c) => c.type !== 'Leader') ?? []
  const cardsByBucket = COST_BUCKETS.map((bucket) => ({
    ...bucket,
    cards: nonLeaderCards.filter((c) => (c.cost ?? 0) >= bucket.min && (c.cost ?? 0) <= bucket.max),
  }))

  return (
    <div>
      <h1 className="page-title">{t('deck_builder.title')}</h1>

      {error && <div style={{ color: 'var(--error)', marginBottom: '1rem' }}>{error}</div>}

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Left Panel: Deck List + Import */}
        <div style={{ flex: '1 1 280px', minWidth: '280px', maxWidth: '320px' }}>
          <div className="card" style={{ padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <h2 style={{ fontSize: '1rem' }}>{t('deck_builder.decks')}</h2>
              {hasMultiVersions && (
                <button className="btn" onClick={toggleAll} style={{ ...btnSmallStyle, opacity: 0.85 }}>
                  {allExpanded ? t('deck_builder.collapse_all') : t('deck_builder.expand_all')}
                </button>
              )}
            </div>
            {loadingList ? (
              <p style={{ color: 'var(--text-secondary)' }}>{t('common.loading')}</p>
            ) : deckList.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>{t('deck_builder.no_decks')}</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {Array.from(deckGroups.entries()).map(([leaderId, versions]) => {
                  if (versions.length === 1) {
                    const d = versions[0]
                    return (
                      <li
                        key={d.deck_id}
                        onClick={() => setSelectedDeckId(d.deck_id)}
                        style={deckListItemStyle(selectedDeckId === d.deck_id)}
                      >
                        {renderDeckRowContent(d, t, deletingId, handleDelete)}
                      </li>
                    )
                  }
                  const expanded = expandedLeaders.has(leaderId)
                  return (
                    <li key={leaderId} style={{ marginBottom: '4px' }}>
                      <div
                        onClick={() => toggleLeader(leaderId)}
                        style={groupHeaderStyle(expanded)}
                      >
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', width: '1em', flexShrink: 0 }}>
                          {expanded ? '▾' : '▸'}
                        </span>
                        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                          {versions[0].name.replace(/\s+v\d+$/, '')}
                        </span>
                        <span style={{
                          fontSize: '0.7rem',
                          padding: '1px 6px',
                          borderRadius: '3px',
                          background: 'rgba(232, 168, 56, 0.15)',
                          color: 'var(--accent)',
                          border: '1px solid rgba(232, 168, 56, 0.3)',
                          marginLeft: 'auto',
                          whiteSpace: 'nowrap',
                        }}>
                          {versions.length} {t('deck_builder.versions')}
                        </span>
                      </div>
                      {expanded && (
                        <ul style={{ listStyle: 'none', padding: 0, marginLeft: '0.75rem', marginTop: '2px' }}>
                          {versions.map((d) => (
                            <li
                              key={d.deck_id}
                              onClick={() => setSelectedDeckId(d.deck_id)}
                              style={deckListItemStyle(selectedDeckId === d.deck_id)}
                            >
                              {renderDeckRowContent(d, t, deletingId, handleDelete)}
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          <div className="card" style={{ padding: '1rem' }}>
            <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>{t('deck_builder.import_deck')}</h2>
            <select
              value={importMode}
              onChange={(e) => {
                setImportMode(e.target.value as 'new' | 'new_version')
                setImportError('')
              }}
              style={{ ...inputStyle, marginBottom: '0.5rem' }}
            >
              <option value="new">{t('deck_builder.new_deck')}</option>
              <option value="new_version">{t('deck_builder.new_version')}</option>
            </select>
            {importMode === 'new_version' ? (
              <select
                value={versionTargetLeader}
                onChange={(e) => setVersionTargetLeader(e.target.value)}
                style={inputStyle}
              >
                <option value="">{t('deck_builder.select_deck')}</option>
                {leaderOptions.map((opt) => (
                  <option key={opt.leaderId} value={opt.leaderId}>
                    {opt.baseName} (v{opt.latestVersion})
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                placeholder={t('deck_builder.deck_name')}
                value={importName}
                onChange={(e) => setImportName(e.target.value)}
                style={inputStyle}
              />
            )}
            <textarea
              placeholder={t('deck_builder.paste_text')}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              rows={8}
              style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace', marginTop: '0.5rem' }}
            />
            {importError && (
              <p style={{ color: 'var(--error)', fontSize: '0.8rem', marginTop: '0.5rem' }}>{importError}</p>
            )}
            <button
              className="btn"
              onClick={handleImport}
              disabled={importing}
              style={{ marginTop: '0.75rem', width: '100%', opacity: importing ? 0.6 : 1 }}
            >
              {importing ? 'Importing...' : t('deck_builder.import_btn')}
            </button>
          </div>
        </div>

        {/* Center Panel: Deck Detail + Validation */}
        <div style={{ flex: '2 1 400px', minWidth: '300px' }}>
          {!selectedDeckId ? (
            <div className="card placeholder">
              <p>{t('deck_builder.no_deck_selected')}</p>
            </div>
          ) : loadingDetail ? (
            <div className="card placeholder">
              <p>{t('deck_builder.loading_deck')}</p>
            </div>
          ) : deckDetail ? (
            <>
              {/* Leader card */}
              {leader && (
                <div className="card" style={{ display: 'flex', gap: '1rem' }}>
                  {leader.image_url && (
                    <img
                      src={leader.image_url}
                      alt={leader.name}
                      style={{ width: '100px', borderRadius: '6px', flexShrink: 0 }}
                    />
                  )}
                  <div style={{ flex: 1 }}>
                    <h2 style={{ fontSize: '1.1rem', marginBottom: '0.25rem' }}>{leader.name}</h2>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                      {leader.type} · {leader.color.join(', ')} · {leader.set_id}
                    </div>
                    {leader.traits.length > 0 && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                        <strong>{t('deck_builder.traits')}:</strong> {leader.traits.join(', ')}
                      </div>
                    )}
                    {leader.effect && (
                      <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>{leader.effect}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Deck info bar */}
              <div className="card" style={{ padding: '0.75rem 1rem', display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <strong>{deckDetail.name}</strong>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  {nonLeaderCards.reduce((sum, c) => sum + c.qty, 0)} {t('deck_builder.cards')}
                </span>
                <span style={{
                  fontSize: '0.75rem',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: 'rgba(232, 168, 56, 0.15)',
                  color: 'var(--accent)',
                  border: '1px solid rgba(232, 168, 56, 0.3)',
                }}>
                  v{deckDetail.version}
                </span>
                {deckDetail.event && (
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{t('deck_builder.event')}: {deckDetail.event}</span>
                )}
                {deckDetail.source && (
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{t('deck_builder.source')}: {deckDetail.source}</span>
                )}
              </div>

              {/* Cards grouped by cost */}
              {cardsByBucket.map((bucket) =>
                bucket.cards.length === 0 ? null : (
                  <div key={bucket.label} className="card" style={{ padding: '1rem' }}>
                    <h3 style={{ fontSize: '0.95rem', marginBottom: '0.75rem', color: 'var(--accent)' }}>
                      Cost {bucket.label} ({bucket.cards.reduce((s, c) => s + c.qty, 0)})
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {bucket.cards.map((card) => (
                        <div key={card.card_id} style={cardRowStyle}>
                          {card.image_url && (
                            <img
                              src={card.image_url}
                              alt={card.name}
                              style={{ width: '40px', height: '56px', borderRadius: '3px', flexShrink: 0 }}
                            />
                          )}
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                              {card.name} <span style={{ color: 'var(--accent)' }}>×{card.qty}</span>
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                              {card.type} · Cost {card.cost ?? '-'}{card.power != null ? ` · ${card.power} PW` : ''}
                              {card.counter > 0 ? ` · +${card.counter}` : ''}
                              {' · '}{card.color.join(', ')}
                            </div>
                            {(card.keywords.length > 0 || card.roles.length > 0) && (
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                                {card.keywords.map((kw) => (
                                  <span key={kw} style={tagStyle('kw')}>{kw}</span>
                                ))}
                                {card.roles.map((r) => (
                                  <span key={r} style={tagStyle('role')}>{r}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              )}

              {/* Validation Panel */}
              <div className="card" style={{ padding: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                  <h3 style={{ fontSize: '0.95rem', color: 'var(--accent)' }}>Validation</h3>
                  <button className="btn" onClick={handleValidate} disabled={validating} style={btnSmallStyle}>
                    {validating ? 'Validating...' : t('deck_builder.validate')}
                  </button>
                </div>
                {!validation ? (
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{t('deck_builder.click_validate')}</p>
                ) : (
                  <div>
                    {validation.errors.length === 0 && validation.warnings.length === 0 ? (
                      <p style={{ color: 'var(--success)', fontSize: '0.85rem' }}>{t('deck_builder.no_validation_issues')}</p>
                    ) : (
                      <>
                        {validation.errors.map((e, i) => (
                          <p key={`e${i}`} style={{ color: 'var(--error)', fontSize: '0.85rem', marginBottom: '4px' }}>
                            ✗ {e}
                          </p>
                        ))}
                        {validation.warnings.map((w, i) => (
                          <p key={`w${i}`} style={{ color: 'var(--warning)', fontSize: '0.85rem', marginBottom: '4px' }}>
                            ⚠ {w}
                          </p>
                        ))}
                      </>
                    )}
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>

        {/* Right Panel: Score + Complete */}
        <div style={{ flex: '1 1 280px', minWidth: '280px', maxWidth: '320px' }}>
          {/* Score Panel */}
          <div className="card" style={{ padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <h3 style={{ fontSize: '0.95rem', color: 'var(--accent)' }}>{t('deck_builder.score')}</h3>
              <button className="btn" onClick={handleScore} disabled={scoring || !selectedDeckId} style={btnSmallStyle}>
                {scoring ? 'Scoring...' : t('deck_builder.score')}
              </button>
            </div>
            {!score ? (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{t('deck_builder.click_score')}</p>
            ) : (
              <div>
                <div style={{ fontSize: '2rem', fontWeight: 700, color: scoreColor(score.overall), marginBottom: '0.75rem' }}>
                  {score.overall}
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}> / 100</span>
                </div>
                {Object.entries(score.breakdown).map(([key, val]) => (
                  <div key={key} style={{ marginBottom: '0.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '2px' }}>
                      <span style={{ textTransform: 'capitalize' }}>{key}</span>
                      <span style={{ color: 'var(--text-secondary)' }}>{val}</span>
                    </div>
                    <div style={{ background: 'var(--bg-primary)', borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${val}%`,
                          height: '100%',
                          background: scoreColor(val),
                          borderRadius: '4px',
                          transition: 'width 0.3s',
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Complete Panel */}
          <div className="card" style={{ padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <h3 style={{ fontSize: '0.95rem', color: 'var(--accent)' }}>{t('deck_builder.complete')}</h3>
              <button className="btn" onClick={handleComplete} disabled={completing || !selectedDeckId} style={btnSmallStyle}>
                {completing ? t('deck_builder.working') : t('deck_builder.complete')}
              </button>
            </div>
            {!completion ? (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{t('deck_builder.click_complete')}</p>
            ) : (
              <div>
                {/* Missing cards */}
                {completion.missing.length > 0 && (
                  <div style={{ marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--warning)' }}>
                        {t('deck_builder.missing_cards')} ({completion.missing.length})
                      </h4>
                      {completion.total_missing_price != null && (
                        <span style={{
                          fontSize: '0.85rem',
                          fontWeight: 700,
                          color: 'var(--accent)',
                          background: 'rgba(232, 168, 56, 0.15)',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          border: '1px solid rgba(232, 168, 56, 0.3)',
                        }}>
                          Total: {completion.total_missing_price.toFixed(2)} €
                        </span>
                      )}
                    </div>
                    {completion.missing.map((m) => (
                      <div key={m.card_id} style={{ fontSize: '0.8rem', marginBottom: '3px', display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
                        <span>
                          {m.name} <span style={{ color: 'var(--text-secondary)' }}>({m.card_id})</span>
                          <span style={{ color: 'var(--error)' }}> — {t('deck_builder.need')} {m.needed}, {t('deck_builder.have')} {m.owned}, {t('deck_builder.missing')} {m.missing}</span>
                        </span>
                        {m.avg_price != null && (
                          <span style={{ color: 'var(--accent)', whiteSpace: 'nowrap', flexShrink: 0 }}>
                            {m.avg_price.toFixed(2)} €{m.missing > 1 ? ` ×${m.missing} = ${m.extended_price?.toFixed(2)} €` : ''}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Substitutions */}
                {completion.substitutions.length > 0 && (
                  <div style={{ marginBottom: '0.75rem' }}>
                    <h4 style={{ fontSize: '0.85rem', marginBottom: '0.4rem', color: 'var(--accent)' }}>
                      {t('deck_builder.substitutions')}
                    </h4>
                    {completion.substitutions.map((s, i) => (
                      <div key={`${s.card_out_id}-${s.card_in_id}-${i}`} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '6px' }}>
                        {s.image_url && (
                          <img src={s.image_url} alt={s.card_in_name} style={{ width: '28px', height: '40px', borderRadius: '2px', flexShrink: 0 }} />
                        )}
                        <div style={{ fontSize: '0.8rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>{s.card_out_id}</span>
                          {' → '}
                          <strong>{s.card_in_name}</strong>
                          <span style={{ color: 'var(--text-secondary)', marginLeft: '4px' }}>(score: {s.score})</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Validation result */}
                {completion.validation && (
                  <div>
                    <h4 style={{ fontSize: '0.85rem', marginBottom: '0.4rem' }}>{t('deck_builder.validation_after')}</h4>
                    {completion.validation.errors.length === 0 && completion.validation.warnings.length === 0 ? (
                      <p style={{ color: 'var(--success)', fontSize: '0.8rem' }}>{t('deck_builder.no_errors')}</p>
                    ) : (
                      <>
                        {completion.validation.errors.map((e, i) => (
                          <p key={`e${i}`} style={{ color: 'var(--error)', fontSize: '0.8rem', marginBottom: '2px' }}>✗ {e}</p>
                        ))}
                        {completion.validation.warnings.map((w, i) => (
                          <p key={`w${i}`} style={{ color: 'var(--warning)', fontSize: '0.8rem', marginBottom: '2px' }}>⚠ {w}</p>
                        ))}
                      </>
                    )}
                  </div>
                )}

                {completion.missing.length === 0 && completion.substitutions.length === 0 && (
                  <p style={{ color: 'var(--success)', fontSize: '0.85rem' }}>{t('deck_builder.complete_done')}</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.5rem',
  background: 'var(--bg-primary)',
  border: '1px solid var(--border)',
  borderRadius: '4px',
  color: 'var(--text-primary)',
  fontSize: '0.85rem',
}

const btnSmallStyle: React.CSSProperties = {
  padding: '0.35rem 0.75rem',
  fontSize: '0.8rem',
}

const deleteBtnStyle: React.CSSProperties = {
  flexShrink: 0,
  padding: '0.15rem 0.45rem',
  fontSize: '0.75rem',
  lineHeight: 1,
  color: 'var(--error)',
  borderColor: 'rgba(239, 68, 68, 0.4)',
  background: 'transparent',
}

const cardRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '0.5rem',
  alignItems: 'flex-start',
  padding: '0.4rem',
  background: 'var(--bg-primary)',
  borderRadius: '6px',
}

function deckListItemStyle(selected: boolean): React.CSSProperties {
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

function groupHeaderStyle(expanded: boolean): React.CSSProperties {
  return {
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
    padding: '0.5rem 0.6rem',
    borderRadius: '4px',
    cursor: 'pointer',
    background: expanded ? 'var(--bg-primary)' : 'transparent',
    borderLeft: '3px solid var(--accent)',
    transition: 'background 0.15s',
  }
}

function renderDeckRowContent(
  d: DeckListItem,
  t: (key: string) => string,
  deletingId: string | null,
  handleDelete: (deckId: string, deckName: string) => void,
) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 600 }}>{d.name}</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {d.card_count} {t('deck_builder.cards')} · v{d.version}{d.source ? ` · ${d.source}` : ''}
        </div>
      </div>
      <button
        className="btn"
        onClick={(e) => { e.stopPropagation(); handleDelete(d.deck_id, d.name) }}
        disabled={deletingId === d.deck_id}
        title={t('common.delete')}
        style={deleteBtnStyle}
      >
        {deletingId === d.deck_id ? '…' : '✕'}
      </button>
    </div>
  )
}

function tagStyle(kind: 'kw' | 'role'): React.CSSProperties {
  return {
    display: 'inline-block',
    padding: '1px 6px',
    borderRadius: '3px',
    fontSize: '0.7rem',
    background: kind === 'kw' ? 'rgba(232, 168, 56, 0.2)' : 'rgba(34, 197, 94, 0.15)',
    color: kind === 'kw' ? 'var(--accent)' : 'var(--success)',
    border: kind === 'kw' ? '1px solid rgba(232, 168, 56, 0.3)' : '1px solid rgba(34, 197, 94, 0.3)',
  }
}

function scoreColor(val: number): string {
  if (val >= 80) return 'var(--success)'
  if (val >= 50) return 'var(--warning)'
  return 'var(--error)'
}
