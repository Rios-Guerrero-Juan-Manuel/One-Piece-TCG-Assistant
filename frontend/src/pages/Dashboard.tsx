import { useState, useEffect, useCallback } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { getStats, type StatsData } from '../api/stats'
import { getPatterns, detectPatterns, type Pattern } from '../api/meta'
import { getInsights, generateInsights, type Insight } from '../api/knowledge'
import { useI18n } from '../i18n/context'

export default function Dashboard() {
  const { t } = useI18n()
  const [stats, setStats] = useState<StatsData | null>(null)
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [insights, setInsights] = useState<Insight[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [s, p, i] = await Promise.all([
        getStats(),
        getPatterns(),
        getInsights().catch(() => []),
      ])
      setStats(s)
      setPatterns(p)
      setInsights(i)
    } catch (err) {
      console.error('Failed to load dashboard data', err)
      setError(t('dashboard.error_load'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const handleDetectPatterns = async () => {
    try {
      const p = await detectPatterns()
      setPatterns(p)
    } catch (err) {
      console.error('Pattern detection failed', err)
      setError(t('dashboard.error_detect'))
    }
  }

  const handleGenerateInsights = async () => {
    try {
      const i = await generateInsights()
      setInsights(i)
    } catch (err) {
      console.error('Insight generation failed', err)
      setError(t('dashboard.error_insights'))
    }
  }

  if (loading) {
    return (
      <div>
        <h1 className="page-title">{t('dashboard.title')}</h1>
        <div className="card placeholder">
          <p>{t('common.loading')}</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h1 className="page-title">{t('dashboard.title')}</h1>
        <div className="card placeholder" style={{ color: 'var(--error)' }}>
          <p>{error}</p>
          <button className="btn" style={{ marginTop: '1rem' }} onClick={loadAll}>{t('common.retry')}</button>
        </div>
      </div>
    )
  }

  if (!stats || stats.total_matches === 0) {
    return (
      <div>
        <h1 className="page-title">{t('dashboard.title')}</h1>
        <div className="card placeholder">
          <p>{t('dashboard.no_data')}</p>
        </div>
      </div>
    )
  }

  const wr = stats.winrate.toFixed(1)
  const dur = stats.avg_duration_turns.toFixed(1)
  const don = stats.avg_don_unused.toFixed(1)
  const wrColor = stats.winrate >= 60 ? 'var(--success)' : stats.winrate < 40 ? 'var(--error)' : 'var(--accent)'

  const leaderEntries = Object.entries(stats.leaders_used).sort((a, b) => b[1] - a[1])

  const leaderLabel = (id: string) => (stats.card_names[id] ? `${id} ${stats.card_names[id]}` : id)
  const deckLabel = (id: string) => stats.deck_names[id] ?? id

  const leaderChartData = leaderEntries.map(([leader, count]) => ({
    name: leaderLabel(leader),
    matches: count,
    winrate: stats.winrate_by_leader[leader] ?? 0,
  }))

  const mostPlayedData = stats.most_played_cards.slice(0, 10).map((c) => ({
    name: stats.card_names[c.card_id] ?? c.card_id,
    count: c.count,
  }))

  const winLossData = [
    { name: t('dashboard.wins'), value: Math.round(stats.total_matches * stats.winrate / 100) },
    { name: t('dashboard.losses'), value: Math.round(stats.total_matches * (100 - stats.winrate) / 100) },
  ]

  return (
    <div>
      <h1 className="page-title">{t('dashboard.title')}</h1>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div className="card" style={statCardStyle}>
          <div style={statLabelStyle}>{t('dashboard.winrate')}</div>
          <div style={{ ...statValueStyle, color: wrColor }}>{wr}%</div>
          <div style={statSubStyle}>{stats.total_matches} {t('dashboard.matches')}</div>
        </div>
        <div className="card" style={statCardStyle}>
          <div style={statLabelStyle}>{t('dashboard.avg_duration')}</div>
          <div style={statValueStyle}>{dur}</div>
          <div style={statSubStyle}>{t('dashboard.turns')}</div>
        </div>
        <div className="card" style={statCardStyle}>
          <div style={statLabelStyle}>{t('dashboard.don_unused')}</div>
          <div style={{ ...statValueStyle, color: parseFloat(don) > 2 ? 'var(--warning)' : 'var(--success)' }}>
            {don}
          </div>
          <div style={statSubStyle}>{t('dashboard.avg_per_turn')}</div>
        </div>
        <div className="card" style={statCardStyle}>
          <div style={statLabelStyle}>{t('dashboard.leaders_used')}</div>
          <div style={statValueStyle}>{leaderEntries.length}</div>
          <div style={statSubStyle}>{t('dashboard.unique')}</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <div style={{ flex: '1 1 300px', minWidth: '300px' }}>
          <div className="card" style={{ padding: '1.25rem' }}>
            <h2 style={cardTitleStyle}>{t('dashboard.winrate')}</h2>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={winLossData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {winLossData.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? 'var(--success)' : 'var(--error)'} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => `${value} ${t('dashboard.matches')}`} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="card" style={{ padding: '1.25rem' }}>
            <h2 style={cardTitleStyle}>{t('dashboard.leader_performance')}</h2>
            {leaderChartData.length === 0 ? (
              <p style={emptyTextStyle}>{t('dashboard.no_leader_data')}</p>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={leaderChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--text-secondary)" opacity={0.2} />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '6px' }}
                    labelStyle={{ color: 'var(--text-primary)' }}
                  />
                  <Bar dataKey="matches" fill="var(--accent)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {mostPlayedData.length > 0 && (
            <div className="card" style={{ padding: '1.25rem' }}>
              <h2 style={cardTitleStyle}>{t('dashboard.most_played')}</h2>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={mostPlayedData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--text-secondary)" opacity={0.2} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} width={80} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '6px' }}
                    labelStyle={{ color: 'var(--text-primary)' }}
                  />
                  <Bar dataKey="count" fill="var(--accent)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {Object.keys(stats.winrate_by_deck || {}).length > 0 && (
            <div className="card" style={{ padding: '1.25rem' }}>
              <h2 style={cardTitleStyle}>{t('dashboard.winrate_by_deck')}</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Object.entries(stats.winrate_by_deck)
                  .sort(([, a], [, b]) => b - a)
                  .map(([deckId, wr]) => {
                    const wrColor = wr >= 60 ? 'var(--success)' : wr < 40 ? 'var(--error)' : 'var(--accent)'
                    return (
                      <div key={deckId} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ fontSize: '0.8rem', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {deckLabel(deckId)}
                        </span>
                        <div style={{ flex: '2', background: 'var(--bg-primary)', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
                          <div style={{ width: `${wr}%`, height: '100%', background: wrColor, borderRadius: '4px' }} />
                        </div>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: wrColor, minWidth: '48px', textAlign: 'right' }}>
                          {wr.toFixed(1)}%
                        </span>
                      </div>
                    )
                  })}
              </div>
            </div>
          )}

          {Object.keys(stats.winrate_by_deck_vs_opp_leader || {}).length > 0 && (
            <DeckVsLeaderMatrix
              matrix={stats.winrate_by_deck_vs_opp_leader}
              totals={stats.deck_vs_opp_leader_totals || {}}
              deckNames={stats.deck_names || {}}
              cardNames={stats.card_names || {}}
              title={t('dashboard.deck_vs_leader')}
            />
          )}
        </div>

        <div style={{ flex: '1 1 300px', minWidth: '300px' }}>
          <div className="card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <h2 style={{ ...cardTitleStyle, marginBottom: 0 }}>{t('dashboard.patterns')}</h2>
              <button className="btn" style={{ padding: '0.3rem 0.7rem', fontSize: '0.78rem' }} onClick={handleDetectPatterns}>
                {t('dashboard.redetect')}
              </button>
            </div>
            {patterns.length === 0 ? (
              <p style={emptyTextStyle}>{t('dashboard.no_patterns')}</p>
            ) : (
              patterns.map((p) => (
                <div key={p.pattern_id} style={patternItemStyle(p.severity)}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '4px' }}>
                    <span style={severityBadgeStyle(p.severity)}>{p.severity}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{p.pattern_id}</span>
                  </div>
                  <p style={{ fontSize: '0.85rem', margin: 0 }}>{p.description}</p>
                </div>
              ))
            )}
          </div>

          <div className="card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <h2 style={{ ...cardTitleStyle, marginBottom: 0 }}>{t('dashboard.insights')}</h2>
              <button className="btn" style={{ padding: '0.3rem 0.7rem', fontSize: '0.78rem' }} onClick={handleGenerateInsights}>
                {t('common.generate')}
              </button>
            </div>
            {insights.length === 0 ? (
              <p style={emptyTextStyle}>{t('dashboard.no_insights')}</p>
            ) : (
              insights.map((ins) => (
                <div key={ins.doc_id} style={insightItemStyle}>
                  {ins.expandable ? (
                    <details>
                      <summary style={{ fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer' }}>{ins.title}</summary>
                      <div style={{ marginTop: '0.5rem' }}>
                        {ins.content.split('\n').map((line, i) => (
                          <p key={i} style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '0.25rem 0' }}>{line}</p>
                        ))}
                      </div>
                    </details>
                  ) : (
                    <>
                      <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '4px' }}>{ins.title}</h3>
                      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0 }}>{ins.content}</p>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function DeckVsLeaderMatrix({
  matrix,
  totals,
  deckNames,
  cardNames,
  title,
}: {
  matrix: Record<string, Record<string, number>>
  totals: Record<string, Record<string, number>>
  deckNames: Record<string, string>
  cardNames: Record<string, string>
  title: string
}) {
  const { t } = useI18n()
  const deckIds = Object.keys(matrix)
  const oppLeaders = Array.from(
    new Set(deckIds.flatMap((d) => Object.keys(matrix[d]))),
  )

  const cellColor = (wr: number) =>
    wr >= 60 ? 'var(--success)' : wr < 40 ? 'var(--error)' : 'var(--accent)'

  return (
    <div className="card" style={{ padding: '1.25rem', overflowX: 'auto' }}>
      <h2 style={cardTitleStyle}>{title}</h2>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.75rem' }}>
        <thead>
          <tr>
            <th style={matrixHeaderStyle}></th>
            {oppLeaders.map((opp) => (
              <th key={opp} style={matrixHeaderStyle}>
                {cardNames[opp] ? `${opp}\n${cardNames[opp]}` : opp}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {deckIds.map((deckId) => (
            <tr key={deckId}>
              <td style={matrixRowHeaderStyle}>
                {deckNames[deckId] ?? deckId}
              </td>
              {oppLeaders.map((opp) => {
                const wr = matrix[deckId]?.[opp]
                const total = totals[deckId]?.[opp]
                const hasData = wr !== undefined
                return (
                  <td key={opp} style={{ textAlign: 'center', padding: '0.4rem' }}>
                    {hasData ? (
                      <span
                        title={`${total} ${t('dashboard.matches')}`}
                        style={{
                          display: 'inline-block',
                          minWidth: '44px',
                          fontWeight: 600,
                          color: cellColor(wr),
                          background: `${cellColor(wr)}1a`,
                          borderRadius: '4px',
                          padding: '2px 6px',
                        }}
                      >
                        {wr.toFixed(0)}%
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-secondary)' }}>–</span>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const matrixHeaderStyle: React.CSSProperties = {
  padding: '0.4rem',
  fontSize: '0.7rem',
  fontWeight: 600,
  color: 'var(--text-secondary)',
  textAlign: 'center',
  whiteSpace: 'pre-line',
  borderBottom: '1px solid var(--border)',
}

const matrixRowHeaderStyle: React.CSSProperties = {
  padding: '0.4rem',
  fontSize: '0.75rem',
  fontWeight: 600,
  textAlign: 'right',
  whiteSpace: 'nowrap',
  borderBottom: '1px solid var(--border)',
}

const statCardStyle: React.CSSProperties = {
  flex: '0 1 180px',
  padding: '1.25rem',
  textAlign: 'center',
}

const statLabelStyle: React.CSSProperties = {
  fontSize: '0.75rem',
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: '0.5rem',
}

const statValueStyle: React.CSSProperties = {
  fontSize: '2rem',
  fontWeight: 700,
  lineHeight: 1,
}

const statSubStyle: React.CSSProperties = {
  fontSize: '0.72rem',
  color: 'var(--text-secondary)',
  marginTop: '0.4rem',
}

const cardTitleStyle: React.CSSProperties = {
  fontSize: '1rem',
  fontWeight: 600,
  marginBottom: '0.75rem',
}

const emptyTextStyle: React.CSSProperties = {
  color: 'var(--text-secondary)',
  fontSize: '0.85rem',
  textAlign: 'center',
  padding: '0.5rem',
}

function patternItemStyle(severity: string): React.CSSProperties {
  return {
    padding: '0.6rem 0.75rem',
    borderRadius: '5px',
    marginBottom: '0.5rem',
    background: 'var(--bg-primary)',
    borderLeft: `3px solid ${severityColor(severity)}`,
  }
}

function severityBadgeStyle(severity: string): React.CSSProperties {
  return {
    display: 'inline-block',
    padding: '1px 6px',
    borderRadius: '3px',
    fontSize: '0.7rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    background: `${severityColor(severity)}22`,
    color: severityColor(severity),
  }
}

function severityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'high': return 'var(--error)'
    case 'medium': return 'var(--warning)'
    case 'low': return 'var(--accent)'
    default: return 'var(--text-secondary)'
  }
}

const insightItemStyle: React.CSSProperties = {
  padding: '0.75rem',
  borderRadius: '5px',
  marginBottom: '0.5rem',
  background: 'var(--bg-primary)',
  borderLeft: '3px solid var(--accent)',
}
