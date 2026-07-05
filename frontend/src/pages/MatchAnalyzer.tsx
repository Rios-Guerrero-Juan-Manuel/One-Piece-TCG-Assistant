import { useState, useEffect, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  getMatches,
  getMatch,
  importMatch,
  importMatchesBatch,
  assignMatchDeck,
  autoAssignMatchDeck,
  type MatchListItem,
  type MatchDetail,
  type BatchImportResult,
} from '../api/matches'
import { getDeckVersions, getDecks, type DeckVersion } from '../api/decks'
import { getSettings } from '../api/settings'
import { useI18n } from '../i18n/context'

export default function MatchAnalyzer() {
  const { t } = useI18n()
  const [matches, setMatches] = useState<MatchListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const pageSize = 50
  const [loadingList, setLoadingList] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<MatchDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const [importing, setImporting] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [batchResults, setBatchResults] = useState<BatchImportResult | null>(null)

  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const [selfDeckVersions, setSelfDeckVersions] = useState<DeckVersion[]>([])
  const [oppDeckVersions, setOppDeckVersions] = useState<DeckVersion[]>([])
  const [editDeckSelf, setEditDeckSelf] = useState<string>('')
  const [editDeckOpp, setEditDeckOpp] = useState<string>('')
  const [savingDeck, setSavingDeck] = useState(false)
  const [selfUserConfigured, setSelfUserConfigured] = useState<boolean | null>(null)
  const [hasDecks, setHasDecks] = useState<boolean | null>(null)

  const loadList = useCallback(async () => {
    setLoadingList(true)
    setError('')
    try {
      const data = await getMatches(page * pageSize, pageSize)
      setMatches(data.matches)
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to load matches', err)
      setError(t('match_analyzer.error_load'))
    } finally {
      setLoadingList(false)
    }
  }, [page, t])

  useEffect(() => {
    loadList()
  }, [loadList])

  useEffect(() => {
    getSettings()
      .then((s) => setSelfUserConfigured(!!(s.self_user && s.self_user.trim())))
      .catch(() => setSelfUserConfigured(false))
  }, [])

  useEffect(() => {
    getDecks()
      .then((d) => setHasDecks(d.length > 0))
      .catch(() => setHasDecks(false))
  }, [])

  const loadDetail = useCallback(async (id: string) => {
    setLoadingDetail(true)
    setError('')
    try {
      const data = await getMatch(id)
      setDetail(data)
      setEditDeckSelf(data.deck_id_self || '')
      setEditDeckOpp(data.deck_id_opp || '')
    } catch (err) {
      console.error('Failed to load match detail', err)
      setError(t('match_analyzer.error_detail'))
      setDetail(null)
    } finally {
      setLoadingDetail(false)
    }
  }, [t])

  useEffect(() => {
    if (selectedId) {
      loadDetail(selectedId)
    } else {
      setDetail(null)
    }
  }, [selectedId, loadDetail])

  useEffect(() => {
    if (detail?.leader_self) {
      getDeckVersions(detail.leader_self).then(setSelfDeckVersions).catch(() => setSelfDeckVersions([]))
    } else {
      setSelfDeckVersions([])
    }
    if (detail?.leader_opp) {
      getDeckVersions(detail.leader_opp).then(setOppDeckVersions).catch(() => setOppDeckVersions([]))
    } else {
      setOppDeckVersions([])
    }
  }, [detail?.leader_self, detail?.leader_opp])

  const doImport = async (files: File[]) => {
    setError('')
    setStatus('')
    setBatchResults(null)
    if (files.length === 0) return

    const extractError = (err: unknown): string => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      return detail || ''
    }

    if (files.length === 1) {
      setImporting(true)
      try {
        const result = await importMatch(files[0])
        setStatus(t('match_analyzer.import_success')
          .replace('{file}', result.source_file)
          .replace('{result}', result.result)
          .replace('{turns}', String(result.turns)))
        await loadList()
        setSelectedId(result.match_id)
      } catch (err) {
        console.error('Import failed', err)
        setError(extractError(err) || t('match_analyzer.error_import'))
      } finally {
        setImporting(false)
      }
    } else {
      setImporting(true)
      try {
        const result = await importMatchesBatch(files)
        setBatchResults(result)
        setStatus(t('match_analyzer.batch_result')
          .replace('{imported}', String(result.imported))
          .replace('{total}', String(result.total))
          .replace('{errors}', String(result.errors)))
        await loadList()
      } catch (err) {
        console.error('Batch import failed', err)
        setError(extractError(err) || t('match_analyzer.error_batch'))
      } finally {
        setImporting(false)
      }
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    if (files.length > 0) {
      setSelectedFiles((prev) => [...prev, ...files])
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files ?? [])
    if (files.length > 0) {
      setSelectedFiles((prev) => [...prev, ...files])
    }
  }

  const handleConfirmImport = async () => {
    if (selectedFiles.length === 0) return
    try {
      await doImport(selectedFiles)
    } finally {
      setSelectedFiles([])
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleClearFiles = () => {
    setSelectedFiles([])
    setStatus('')
    setBatchResults(null)
  }

  const handleSaveDeck = async () => {
    if (!selectedId) return
    setSavingDeck(true)
    try {
      const result = await assignMatchDeck(selectedId, editDeckSelf || null, editDeckOpp || null)
      setDetail((prev) => prev ? { ...prev, deck_id_self: result.deck_id_self, deck_id_opp: result.deck_id_opp } : null)
      await loadList()
    } catch (err) {
      console.error('Failed to save deck assignment', err)
      setError(t('match_analyzer.error_save_deck'))
    } finally {
      setSavingDeck(false)
    }
  }

  const handleAutoAssign = async () => {
    if (!selectedId) return
    setSavingDeck(true)
    try {
      const result = await autoAssignMatchDeck(selectedId)
      setEditDeckSelf(result.deck_id_self || '')
      setEditDeckOpp(result.deck_id_opp || '')
      setDetail((prev) => prev ? { ...prev, deck_id_self: result.deck_id_self, deck_id_opp: result.deck_id_opp } : null)
      await loadList()
    } catch (err) {
      console.error('Failed to auto-assign deck', err)
      setError(t('match_analyzer.error_auto_assign'))
    } finally {
      setSavingDeck(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const isWin = detail?.result.toLowerCase().startsWith('win')
  const isBusy = importing

  return (
    <div>
      <h1 className="page-title">{t('match_analyzer.title')}</h1>

      {(error || status) && (
        <div style={{ marginBottom: '1rem' }}>
          {error && <div style={{ color: 'var(--error)' }}>{error}</div>}
          {status && <div style={{ color: 'var(--success)' }}>{status}</div>}
        </div>
      )}

      {/* No decks warning */}
      {hasDecks === false && (
        <div className="card" style={{ padding: '1rem 1.5rem', marginBottom: '1rem', borderColor: 'var(--warning, var(--accent))' }}>
          <p style={{ color: 'var(--text-primary)', margin: 0, marginBottom: '0.5rem' }}>
            {t('match_analyzer.no_decks_warning')}
          </p>
          <Link to="/deck-builder" className="btn" style={{ display: 'inline-block', textDecoration: 'none' }}>
            {t('match_analyzer.go_to_deck_builder')}
          </Link>
        </div>
      )}

      {/* Import section */}
      {selfUserConfigured === false ? (
        <div className="card" style={{ padding: '1.5rem', borderColor: 'var(--warning, var(--accent))' }}>
          <p style={{ color: 'var(--text-primary)', margin: 0, marginBottom: '0.75rem' }}>
            {t('match_analyzer.self_user_required')}
          </p>
          <Link to="/settings" className="btn" style={{ display: 'inline-block', textDecoration: 'none' }}>
            {t('match_analyzer.go_to_settings')}
          </Link>
        </div>
      ) : (
      <div className="card" style={{ padding: '1rem' }}>
        <label
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          style={{
            display: 'block',
            border: `2px dashed ${dragOver ? 'var(--accent)' : 'var(--border)'}`,
            borderRadius: '6px',
            padding: '1.5rem',
            textAlign: 'center',
            marginBottom: '0.75rem',
            transition: 'border-color 0.15s',
            background: dragOver ? 'rgba(232, 168, 56, 0.06)' : 'transparent',
            cursor: 'pointer',
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".txt,.log,application/octet-stream,text/plain"
            onChange={handleFileInput}
            style={{ display: 'none' }}
          />
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
            {isBusy ? t('match_analyzer.importing') : t('match_analyzer.drag_drop')}
          </p>
        </label>

        {selectedFiles.length > 0 && (
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              {t('match_analyzer.files_ready').replace('{count}', String(selectedFiles.length))}
            </div>
            <div style={{ maxHeight: '150px', overflowY: 'auto', fontSize: '0.78rem', border: '1px solid var(--border)', borderRadius: '4px' }}>
              {selectedFiles.map((f, i) => (
                <div key={`${f.name}-${i}`} style={{ padding: '0.3rem 0.5rem', borderBottom: '1px solid var(--border)', color: 'var(--text-primary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.7rem', flexShrink: 0 }}>{(f.size / 1024).toFixed(1)} KB</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {batchResults && batchResults.results.length > 0 && (
          <div style={{ marginBottom: '0.75rem', maxHeight: '200px', overflowY: 'auto', fontSize: '0.8rem' }}>
            {batchResults.results.map((r, i) => (
              <div key={i} style={{
                padding: '0.25rem 0.5rem',
                color: r.success ? 'var(--success)' : 'var(--error)',
                borderBottom: '1px solid var(--border)',
              }}>
                {r.success ? '\u2713' : '\u2717'} {r.filename}
                {r.error && <span style={{ color: 'var(--text-secondary)' }}>: {r.error}</span>}
              </div>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className="btn"
            onClick={handleConfirmImport}
            disabled={isBusy || selectedFiles.length === 0}
            style={{ flex: 1, opacity: (isBusy || selectedFiles.length === 0) ? 0.6 : 1 }}
          >
            {importing ? t('match_analyzer.importing') : t('match_analyzer.confirm_import')}
          </button>
          {selectedFiles.length > 0 && (
            <button
              className="btn"
              onClick={handleClearFiles}
              disabled={isBusy}
              style={btnSmall}
            >
              {t('match_analyzer.clear_selection')}
            </button>
          )}
        </div>
      </div>
      )}

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Left panel: match list */}
        <div style={{ flex: '1 1 280px', minWidth: '280px', maxWidth: '340px' }}>
          <div className="card" style={{ padding: '1rem' }}>
            <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
              {t('match_analyzer.matches')} <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>({total})</span>
            </h2>
            {loadingList ? (
              <p style={{ color: 'var(--text-secondary)' }}>{t('common.loading')}</p>
            ) : matches.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>{t('match_analyzer.no_matches')}</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {matches.map((m) => {
                  const win = m.result.toLowerCase().startsWith('win')
                  return (
                    <li
                      key={m.match_id}
                      onClick={() => setSelectedId(m.match_id)}
                      style={listItemStyle(selectedId === m.match_id)}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={badgeStyle(win)}>{m.result}</span>
                        {m.duration_turns != null && (
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{m.duration_turns} {t('dashboard.turns')}</span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.8rem', marginTop: '4px', color: 'var(--text-primary)' }}>
                        {m.leader_self} <span style={{ color: 'var(--text-secondary)' }}>{t('match_analyzer.vs')}</span> {m.leader_opp}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {m.played_at ? formatPlayedAt(m.played_at) : m.source_file}
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem' }}>
                <button className="btn" style={btnSmall} disabled={page === 0} onClick={() => setPage((p) => p - 1)}>{t('common.prev')}</button>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {page + 1} / {totalPages}
                </span>
                <button className="btn" style={btnSmall} disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>{t('common.next')}</button>
              </div>
            )}
          </div>
        </div>

        {/* Right panel: match detail */}
        <div style={{ flex: '2 1 400px', minWidth: '300px' }}>
          {!selectedId ? (
            <div className="card placeholder">
              <p>{t('match_analyzer.select_match')}</p>
            </div>
          ) : loadingDetail ? (
            <div className="card placeholder">
              <p>{t('match_analyzer.loading_match')}</p>
            </div>
          ) : detail ? (
            <>
              {/* Header card */}
              <div className="card" style={{ padding: '1rem 1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                  <span style={badgeStyle(!!isWin)}>{detail.result}</span>
                  {detail.version && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>v{detail.version}</span>
                  )}
                  {detail.duration_turns != null && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{detail.duration_turns} {t('dashboard.turns')}</span>
                  )}
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: 'auto' }}>
                    {detail.match_id}
                  </span>
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                  <strong>{detail.leader_self}</strong>
                  <span style={{ color: 'var(--text-secondary)' }}> {t('match_analyzer.vs')} </span>
                  <strong>{detail.leader_opp}</strong>
                  {detail.opponent_user && (
                    <span style={{ color: 'var(--text-secondary)' }}> · {t('match_analyzer.opp')}: {detail.opponent_user}</span>
                  )}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  {detail.source_file}
                </div>
                {detail.reason && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.4rem' }}>
                    {t('match_analyzer.reason')}: {detail.reason}
                  </div>
                )}
              </div>

              {/* Deck assignment panel */}
              <div className="card" style={{ padding: '1rem 1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                  <h3 style={{ fontSize: '0.9rem', color: 'var(--accent)', margin: 0 }}>{t('match_analyzer.deck_assignment')}</h3>
                  <button className="btn" style={btnSmall} onClick={handleAutoAssign} disabled={savingDeck}>
                    {t('match_analyzer.auto_assign')}
                  </button>
                  <button className="btn" style={btnSmall} onClick={handleSaveDeck} disabled={savingDeck}>
                    {savingDeck ? t('common.loading') : t('common.save')}
                  </button>
                </div>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  <div style={{ flex: '1 1 200px' }}>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{t('match_analyzer.your_deck')} ({detail.leader_self})</label>
                    <select
                      value={editDeckSelf}
                      onChange={(e) => setEditDeckSelf(e.target.value)}
                      style={{ ...inputSelectStyle, marginTop: '2px' }}
                    >
                      <option value="">— {t('match_analyzer.none')} —</option>
                      {selfDeckVersions.map((v) => (
                        <option key={v.deck_id} value={v.deck_id}>
                          {v.name} (v{v.version}) — {v.card_count} {t('deck_builder.cards')}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div style={{ flex: '1 1 200px' }}>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{t('match_analyzer.opp_deck')} ({detail.leader_opp})</label>
                    <select
                      value={editDeckOpp}
                      onChange={(e) => setEditDeckOpp(e.target.value)}
                      style={{ ...inputSelectStyle, marginTop: '2px' }}
                    >
                      <option value="">— {t('match_analyzer.none')} —</option>
                      {oppDeckVersions.map((v) => (
                        <option key={v.deck_id} value={v.deck_id}>
                          {v.name} (v{v.version}) — {v.card_count} {t('deck_builder.cards')}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Turn timeline */}
              {detail.turns.length === 0 ? (
                <div className="card placeholder">
                  <p>{t('match_analyzer.no_turn_data')}</p>
                </div>
              ) : (
                detail.turns.map((turn) => {
                  const selfTurn = detail.self_player_idx != null && turn.player_idx === detail.self_player_idx
                  const handList = Array.isArray(turn.state_end.hand) ? (turn.state_end.hand as string[]) : null
                  const boardList = Array.isArray(turn.state_end.board) ? (turn.state_end.board as string[]) : null
                  const life = readNum(turn.state_end, 'life')
                  const oppHandList = Array.isArray(turn.state_end.opp_hand) ? (turn.state_end.opp_hand as string[]) : null
                  const oppBoardList = Array.isArray(turn.state_end.opp_board) ? (turn.state_end.opp_board as string[]) : null
                  const oppLife = readNum(turn.state_end, 'opp_life')
                  const cn = detail.card_names ?? {}
                  return (
                    <div
                      key={turn.turn_no}
                      className="card"
                      style={{
                        padding: '0.75rem 1rem',
                        borderLeft: selfTurn ? '3px solid var(--accent)' : '3px solid var(--border)',
                        marginLeft: selfTurn ? '0' : '24px',
                        marginRight: selfTurn ? '24px' : '0',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <strong style={{ fontSize: '0.9rem' }}>
                          {t('match_analyzer.turn')} {turn.turn_no}
                        </strong>
                        <span style={playerTagStyle(selfTurn)}>
                          {selfTurn ? t('match_analyzer.you') : t('match_analyzer.opp')}
                        </span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          DON: +{turn.don_drawn} · {Number(turn.state_end?.don_active ?? turn.don_unused)} active{Number(turn.state_end?.don_rested) > 0 ? ` · ${turn.state_end!.don_rested} cost` : ''}{Number(turn.state_end?.don_attached) > 0 ? ` · ${turn.state_end!.don_attached} attached` : ''}
                        </span>
                      </div>

                      {/* Cards played */}
                      {turn.cards_played.length > 0 && (
                        <div style={{ marginBottom: '0.4rem' }}>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{t('match_analyzer.played')}: </span>
                          {turn.cards_played.map((c, i) => (
                            <span key={`${c.card_id}-${i}`} style={cardTagStyle}>
                              {cardLabel(c.name, c.card_id)}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Attacks with outcomes + nested counters */}
                      {turn.attacks.length > 0 && (
                        <div style={{ marginBottom: '0.4rem' }}>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{t('match_analyzer.attacks')}:</span>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
                            {turn.attacks.map((a, i) => (
                              <div key={i} style={{ fontSize: '0.8rem', padding: '0.3rem 0.4rem', background: 'var(--bg-primary)', borderRadius: '4px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
                                  <span style={{ color: 'var(--accent)', fontWeight: 600 }}>
                                    {cardLabel(a.attacker_name, a.attacker)}
                                  </span>
                                  {a.attacker_power != null && (
                                    <span style={{ color: 'var(--text-secondary)' }}>{a.attacker_power}</span>
                                  )}
                                  <span style={{ color: 'var(--text-secondary)' }}>{t('match_analyzer.vs')}</span>
                                  <span style={{ fontWeight: 600 }}>
                                    {cardLabel(a.target_name, a.target)}
                                  </span>
                                  {a.defender_power != null && (
                                    <span style={{ color: 'var(--text-secondary)' }}>{a.defender_power}</span>
                                  )}
                                  {a.result && (
                                    <span style={resultBadgeStyle(a.result)}>
                                      {resultLabel(t, a.result, a.damage)}
                                    </span>
                                  )}
                                </div>
                                {a.counters && a.counters.length > 0 && (
                                  <div style={{ marginTop: '3px', paddingLeft: '0.5rem', borderLeft: '2px solid rgba(34, 197, 94, 0.4)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                    <span>🛡 {t('match_analyzer.counters')}</span>
                                    {a.counters[0]?.actor ? <span> {t('match_analyzer.by')} {a.counters[0].actor}</span> : null}
                                    <span>: </span>
                                    {a.counters.map((c, j) => (
                                      <span key={j} style={counterTagStyle}>
                                        {cardLabel(c.name, c.card_id)}{c.value != null ? ` +${c.value}` : ''}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Loose counters (not tied to an attack) */}
                      {turn.counters.length > 0 && (
                        <div style={{ marginBottom: '0.4rem' }}>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{t('match_analyzer.counters')}:</span>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '2px' }}>
                            {turn.counters.map((c, i) => (
                              <span key={i} style={counterTagStyle}>
                                {cardLabel(c.name, c.card_id)}{c.value != null ? ` +${c.value}` : ''}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Errors */}
                      {turn.errors.length > 0 && (
                        <div style={{ borderLeft: '3px solid var(--error)', paddingLeft: '0.5rem', marginTop: '0.4rem' }}>
                          {turn.errors.map((err, i) => (
                            <p key={i} style={{ color: 'var(--error)', fontSize: '0.78rem', marginBottom: '2px' }}>
                              ⚠ {err}
                            </p>
                          ))}
                        </div>
                      )}

                      {/* Board state — both players */}
                      <div style={{ marginTop: '0.4rem', fontSize: '0.72rem', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                        {boardList && boardList.length > 0 && (
                          <div>
                            <span style={{ color: 'var(--text-secondary)' }}>{selfTurn ? '🔵' : '🔴'} {t('match_analyzer.board')}: </span>
                            {boardList.map((cid, i) => (
                              <span key={`${cid}-${i}`} style={cardTagStyle}>{cardLabel(cn[cid], cid)}</span>
                            ))}
                          </div>
                        )}
                        {oppBoardList && oppBoardList.length > 0 && (
                          <div>
                            <span style={{ color: 'var(--text-secondary)' }}>{selfTurn ? '🔴' : '🔵'} {t('match_analyzer.opp_board')}: </span>
                            {oppBoardList.map((cid, i) => (
                              <span key={`${cid}-${i}`} style={oppCardTagStyle}>{cardLabel(cn[cid], cid)}</span>
                            ))}
                          </div>
                        )}
                        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                          {life != null && <span style={{ color: life === 0 ? 'var(--error)' : 'var(--text-secondary)' }}>{t('match_analyzer.life')}: {life}</span>}
                          {oppLife != null && <span style={{ color: oppLife === 0 ? 'var(--error)' : 'var(--text-secondary)' }}>{t('match_analyzer.opp_life')}: {oppLife}</span>}
                          {handList && <span style={{ color: 'var(--text-secondary)' }}>{t('match_analyzer.hand')}: {handList.length}</span>}
                          {oppHandList && <span style={{ color: 'var(--text-secondary)' }}>{t('match_analyzer.opp_hand_short')}: {oppHandList.length}</span>}
                        </div>
                        {handList && handList.length > 0 && (
                          <div style={{ marginTop: '2px' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>{t('match_analyzer.hand')}: </span>
                            {handList.map((cid, i) => (
                              <span key={`${cid}-${i}`} style={smallCardTagStyle}>{cardLabel(cn[cid], cid)}</span>
                            ))}
                          </div>
                        )}
                        {oppHandList && oppHandList.length > 0 && (
                          <div style={{ marginTop: '2px' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>{t('match_analyzer.opp_hand_short')}: </span>
                            {oppHandList.map((cid, i) => (
                              <span key={`${cid}-${i}`} style={smallCardTagStyle}>{cardLabel(cn[cid], cid)}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}

type TFunc = (key: string, fallback?: string) => string

function readNum(state: Record<string, unknown>, ...keys: string[]): number | null {
  for (const k of keys) {
    const v = state[k]
    if (typeof v === 'number') return v
    if (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v))) return Number(v)
  }
  return null
}

function formatPlayedAt(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${dd}/${mm}/${d.getFullYear()} ${hh}:${min}`
}

function cardLabel(name: string | null | undefined, id: string | null | undefined): string {
  let cleanName = (name ?? '').trim()
  if (id) {
    const escaped = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    cleanName = cleanName.replace(new RegExp('\\s*\\(?' + escaped + '\\)?\\s*$', 'i'), '').trim()
  }
  if (cleanName && id) return `${cleanName} (${id})`
  if (cleanName) return cleanName
  if (id) return id
  return '?'
}

function resultLabel(t: TFunc, result: string, damage: number | null | undefined): string {
  switch (result) {
    case 'hit':
      return damage ? `${t('match_analyzer.result_hit')} −${damage} ${t('match_analyzer.life')}` : t('match_analyzer.result_hit')
    case 'destroyed':
      return t('match_analyzer.result_destroyed')
    case 'failed':
      return t('match_analyzer.result_blocked')
    default:
      return result
  }
}

function resultBadgeStyle(result: string): React.CSSProperties {
  let bg = 'rgba(156, 163, 175, 0.15)'
  let color = 'var(--text-secondary)'
  let border = 'var(--border)'
  if (result === 'hit') {
    bg = 'rgba(249, 115, 22, 0.18)'
    color = '#f97316'
    border = 'rgba(249, 115, 22, 0.4)'
  } else if (result === 'destroyed') {
    bg = 'rgba(239, 68, 68, 0.18)'
    color = 'var(--error)'
    border = 'rgba(239, 68, 68, 0.4)'
  }
  return {
    display: 'inline-block',
    padding: '1px 6px',
    borderRadius: '3px',
    fontSize: '0.7rem',
    fontWeight: 700,
    marginLeft: '0.25rem',
    background: bg,
    color,
    border: `1px solid ${border}`,
  }
}

const btnSmall: React.CSSProperties = {
  padding: '0.3rem 0.7rem',
  fontSize: '0.78rem',
}

const inputSelectStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.4rem',
  background: 'var(--bg-primary)',
  border: '1px solid var(--border)',
  borderRadius: '4px',
  color: 'var(--text-primary)',
  fontSize: '0.8rem',
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

function badgeStyle(win: boolean): React.CSSProperties {
  return {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 700,
    background: win ? 'rgba(34, 197, 94, 0.18)' : 'rgba(239, 68, 68, 0.18)',
    color: win ? 'var(--success)' : 'var(--error)',
    border: `1px solid ${win ? 'rgba(34, 197, 94, 0.35)' : 'rgba(239, 68, 68, 0.35)'}`,
  }
}

function playerTagStyle(self: boolean): React.CSSProperties {
  return {
    display: 'inline-block',
    padding: '1px 6px',
    borderRadius: '3px',
    fontSize: '0.7rem',
    background: self ? 'rgba(232, 168, 56, 0.18)' : 'rgba(156, 163, 175, 0.15)',
    color: self ? 'var(--accent)' : 'var(--text-secondary)',
    border: `1px solid ${self ? 'rgba(232, 168, 56, 0.3)' : 'var(--border)'}`,
  }
}

const cardTagStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '1px 6px',
  marginRight: '4px',
  marginBottom: '2px',
  borderRadius: '3px',
  fontSize: '0.72rem',
  background: 'rgba(232, 168, 56, 0.12)',
  color: 'var(--accent)',
  border: '1px solid rgba(232, 168, 56, 0.25)',
}

const counterTagStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '1px 6px',
  borderRadius: '3px',
  fontSize: '0.72rem',
  background: 'rgba(34, 197, 94, 0.12)',
  color: 'var(--success)',
  border: '1px solid rgba(34, 197, 94, 0.25)',
}

const oppCardTagStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '1px 6px',
  marginRight: '4px',
  marginBottom: '2px',
  borderRadius: '3px',
  fontSize: '0.72rem',
  background: 'rgba(239, 68, 68, 0.12)',
  color: '#ef4444',
  border: '1px solid rgba(239, 68, 68, 0.25)',
}

const smallCardTagStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '0px 4px',
  marginRight: '3px',
  marginBottom: '1px',
  borderRadius: '2px',
  fontSize: '0.68rem',
  background: 'rgba(100, 116, 139, 0.12)',
  color: 'var(--text-secondary)',
  border: '1px solid var(--border)',
}
