import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  getGlobalMeta,
  getGlobalMatrix,
  type GlobalMetaResponse,
  type GlobalLeaderStat,
  type MetaRegion,
  type MetaView,
  type MetaTurnOrder,
} from '../api/meta'
import { useI18n } from '../i18n/context'

type Tab = 'stats' | 'matrix' | 'tiers'
type RegionGroup = 'west' | 'east'
type EloTier = 'elo' | 'elo+' | 'elo++'

const REGION_MAP: Record<RegionGroup, Record<EloTier, MetaRegion>> = {
  west: { elo: 'west', 'elo+': 'west+', 'elo++': 'west++' },
  east: { elo: 'east', 'elo+': 'east+', 'elo++': 'east+' },
}

const TIER_COLORS: Record<string, string> = {
  S: '#f0b90b',
  A: '#27ae60',
  B: '#3498db',
  C: '#e67e22',
  D: '#95a5a6',
}

const TIER_ORDER = ['S', 'A', 'B', 'C', 'D']

export default function MetaReportPage() {
  const { t } = useI18n()
  const [tab, setTab] = useState<Tab>('stats')
  const [regionGroup, setRegionGroup] = useState<RegionGroup>('west')
  const [elo, setElo] = useState<EloTier>('elo')
  const [turn, setTurn] = useState<MetaTurnOrder>('combined')
  const [view, setView] = useState<MetaView>('overall')

  const region = REGION_MAP[regionGroup][elo]

  const [meta, setMeta] = useState<GlobalMetaResponse | null>(null)
  const [matrix, setMatrix] = useState<Record<string, Record<string, number | null>> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadMeta = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getGlobalMeta(region, view, turn)
      setMeta(data)
    } catch (err) {
      console.error('Failed to load global meta', err)
      setError(t('meta.error_load'))
    } finally {
      setLoading(false)
    }
  }, [region, view, turn, t])

  const loadMatrix = useCallback(async () => {
    try {
      const data = await getGlobalMatrix(region, turn)
      setMatrix(data)
    } catch (err) {
      console.error('Failed to load matrix', err)
    }
  }, [region, turn])

  useEffect(() => {
    loadMeta()
  }, [loadMeta])

  useEffect(() => {
    if (tab === 'matrix' && matrix === null) {
      loadMatrix()
    }
  }, [tab, matrix, loadMatrix])

  useEffect(() => {
    setMatrix(null)
  }, [region, turn])

  const sortedLeaders = useMemo(() => {
    if (!meta) return []
    return [...meta.leaders].sort((a, b) => b.winrate - a.winrate)
  }, [meta])

  const leaderMap = useMemo(() => {
    const m: Record<string, GlobalLeaderStat> = {}
    meta?.leaders.forEach((l) => { m[l.card_id] = l })
    return m
  }, [meta])

  const matrixLeaders = useMemo(() => {
    if (!matrix) return []
    return Object.keys(matrix).sort()
  }, [matrix])

  if (loading && !meta) {
    return (
      <div>
        <h1 className="page-title">{t('meta.global_title')}</h1>
        <div className="card placeholder"><p>{t('common.loading')}</p></div>
      </div>
    )
  }

  if (error && !meta) {
    return (
      <div>
        <h1 className="page-title">{t('meta.global_title')}</h1>
        <div className="card placeholder" style={{ color: 'var(--error)' }}>
          <p>{error}</p>
          <button className="btn" style={{ marginTop: '1rem' }} onClick={loadMeta}>{t('common.retry')}</button>
        </div>
      </div>
    )
  }

  if (!meta) return null

  const totalMatches = meta.total_matches
  const fmtNum = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h1 className="page-title" style={{ margin: 0 }}>{t('meta.global_title')}</h1>
        <a
          href="https://www.optcg.one/meta"
          target="_blank"
          rel="noopener noreferrer"
          style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textDecoration: 'none' }}
        >
          {t('meta.data_source')}: optcg.one
        </a>
      </div>

      {error && (
        <div style={{ color: 'var(--error)', marginBottom: '0.75rem', fontSize: '0.85rem' }}>{error}</div>
      )}

      <FilterBar
        regionGroup={regionGroup}
        setRegionGroup={(v) => { setRegionGroup(v) }}
        elo={elo}
        setElo={setElo}
        turn={turn}
        setTurn={setTurn}
        view={view}
        setView={setView}
        t={t}
      />

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {(['stats', 'matrix', 'tiers'] as Tab[]).map((tb) => (
          <button
            key={tb}
            className="btn"
            onClick={() => setTab(tb)}
            style={tab === tb ? activeTabStyle : inactiveTabStyle}
          >
            {t(`meta.tab_${tb}`)}
          </button>
        ))}
      </div>

      {tab === 'stats' && (
        <StatsTab leaders={sortedLeaders} fmtNum={fmtNum} t={t} totalMatches={totalMatches} />
      )}

      {tab === 'matrix' && (
        <MatrixTab
          matrix={matrix}
          leaders={matrixLeaders}
          leaderMap={leaderMap}
          loading={matrix === null}
          t={t}
        />
      )}

      {tab === 'tiers' && (
        <TiersTab meta={meta} />
      )}
    </div>
  )
}

function FilterBar(props: {
  regionGroup: RegionGroup
  setRegionGroup: (v: RegionGroup) => void
  elo: EloTier
  setElo: (v: EloTier) => void
  turn: MetaTurnOrder
  setTurn: (v: MetaTurnOrder) => void
  view: MetaView
  setView: (v: MetaView) => void
  t: (key: string) => string
}) {
  const { regionGroup, setRegionGroup, elo, setElo, turn, setTurn, view, setView, t } = props
  return (
    <div className="card" style={{ padding: '0.75rem', marginBottom: '0.75rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
      <FilterGroup label={t('meta.region')}>
        <ToggleButton active={regionGroup === 'west'} onClick={() => setRegionGroup('west')}>West</ToggleButton>
        <ToggleButton active={regionGroup === 'east'} onClick={() => setRegionGroup('east')}>East</ToggleButton>
      </FilterGroup>
      <FilterGroup label={t('meta.elo')}>
        <ToggleButton active={elo === 'elo'} onClick={() => setElo('elo')}>Elo</ToggleButton>
        <ToggleButton active={elo === 'elo+'} onClick={() => setElo('elo+')}>Elo+</ToggleButton>
        {regionGroup === 'west' && (
          <ToggleButton active={elo === 'elo++'} onClick={() => setElo('elo++')}>Elo++</ToggleButton>
        )}
      </FilterGroup>
      <FilterGroup label={t('meta.turn_order')}>
        <ToggleButton active={turn === 'combined'} onClick={() => setTurn('combined')}>{t('meta.turn_both')}</ToggleButton>
        <ToggleButton active={turn === 'first'} onClick={() => setTurn('first')}>{t('meta.turn_first')}</ToggleButton>
        <ToggleButton active={turn === 'second'} onClick={() => setTurn('second')}>{t('meta.turn_second')}</ToggleButton>
      </FilterGroup>
      <FilterGroup label={t('meta.view_mode')}>
        <ToggleButton active={view === 'overall'} onClick={() => setView('overall')}>{t('meta.view_overall')}</ToggleButton>
        <ToggleButton active={view === 'winrate'} onClick={() => setView('winrate')}>{t('meta.view_winrate')}</ToggleButton>
        <ToggleButton active={view === 'steady'} onClick={() => setView('steady')}>{t('meta.view_steady')}</ToggleButton>
      </FilterGroup>
    </div>
  )
}

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginRight: '0.2rem' }}>{label}</span>
      {children}
    </div>
  )
}

function ToggleButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '0.25rem 0.6rem',
        fontSize: '0.78rem',
        border: '1px solid var(--border)',
        borderRadius: '4px',
        background: active ? 'var(--accent)' : 'var(--bg-primary)',
        color: active ? '#fff' : 'var(--text-secondary)',
        cursor: 'pointer',
        fontWeight: active ? 600 : 400,
        transition: 'all 0.15s',
      }}
    >
      {children}
    </button>
  )
}

function StatsTab({ leaders, fmtNum, t, totalMatches }: {
  leaders: GlobalLeaderStat[]
  fmtNum: (n: number) => string
  t: (key: string) => string
  totalMatches: number
}) {
  if (leaders.length === 0) {
    return <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>{t('meta.no_data')}</div>
  }
  return (
    <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.82rem' }}>
        <thead>
          <tr>
            <th style={thLeftStyle}>#</th>
            <th style={thLeftStyle}>{t('meta.leader')}</th>
            <th style={thCenterStyle}>Tier</th>
            <th style={thCenterStyle}>W</th>
            <th style={thCenterStyle}>L</th>
            <th style={thCenterStyle}>M</th>
            <th style={thCenterStyle}>WR%</th>
            <th style={thCenterStyle}>{t('meta.share')}</th>
          </tr>
        </thead>
        <tbody>
          {leaders.map((l, i) => {
            const sharePct = totalMatches > 0 ? (l.matches / totalMatches) * 100 : 0
            return (
              <tr key={l.card_id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ ...tdStyle, color: 'var(--text-secondary)', textAlign: 'center', width: '2rem' }}>{i + 1}</td>
                <td style={tdStyle}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <img src={l.image_url} alt={l.name} style={leaderImgStyle} loading="lazy" />
                    <div>
                      <div style={{ fontWeight: 600 }}>{l.name}</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>{l.card_id}</div>
                    </div>
                  </div>
                </td>
                <td style={tdCenterStyle}>
                  {l.tier && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '1.5rem',
                      height: '1.5rem',
                      borderRadius: '3px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: '#fff',
                      background: TIER_COLORS[l.tier] || 'var(--text-secondary)',
                    }}>{l.tier}</span>
                  )}
                </td>
                <td style={{ ...tdCenterStyle, color: 'var(--success)' }}>{fmtNum(l.wins)}</td>
                <td style={{ ...tdCenterStyle, color: 'var(--error)' }}>{fmtNum(l.losses)}</td>
                <td style={tdCenterStyle}>{fmtNum(l.matches)}</td>
                <td style={{ ...tdCenterStyle, fontWeight: 600, color: l.winrate >= 50 ? 'var(--success)' : 'var(--text-secondary)' }}>
                  {l.winrate.toFixed(1)}%
                </td>
                <td style={{ ...tdCenterStyle, color: 'var(--text-secondary)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', justifyContent: 'center' }}>
                    <div style={{ width: '40px', height: '4px', background: 'var(--bg-primary)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ width: `${sharePct}%`, height: '100%', background: 'var(--accent)' }} />
                    </div>
                    <span style={{ fontSize: '0.7rem' }}>{sharePct.toFixed(1)}%</span>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function MatrixTab({ matrix, leaders, leaderMap, loading, t }: {
  matrix: Record<string, Record<string, number | null>> | null
  leaders: string[]
  leaderMap: Record<string, GlobalLeaderStat>
  loading: boolean
  t: (key: string) => string
}) {
  if (loading) {
    return <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>{t('common.loading')}</div>
  }
  if (!matrix || leaders.length === 0) {
    return <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>{t('meta.no_data')}</div>
  }

  const topLeaders = leaders.slice(0, 25)

  return (
    <div className="card" style={{ padding: '0.75rem', overflowX: 'auto' }}>
      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
        {t('meta.matrix_hint')}
      </p>
      <table style={{ borderCollapse: 'collapse', fontSize: '0.72rem' }}>
        <thead>
          <tr>
            <th style={matrixThCornerStyle}>{t('meta.self_opp')}</th>
            {topLeaders.map((cid) => (
              <th key={cid} style={matrixThStyle} title={leaderMap[cid]?.name || cid}>
                <img
                  src={leaderMap[cid]?.image_url}
                  alt={cid}
                  style={{ width: '28px', height: '28px', borderRadius: '3px', display: 'block' }}
                  loading="lazy"
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {topLeaders.map((selfId) => (
            <tr key={selfId}>
              <td style={matrixTdLabelStyle}>
                <img
                  src={leaderMap[selfId]?.image_url}
                  alt={selfId}
                  style={{ width: '28px', height: '28px', borderRadius: '3px', display: 'block' }}
                  loading="lazy"
                />
              </td>
              {topLeaders.map((oppId) => {
                const wr = matrix[selfId]?.[oppId]
                if (wr == null) {
                  return <td key={oppId} style={matrixCellEmptyStyle}>–</td>
                }
                return (
                  <td key={oppId} style={matrixCellStyle(wr)} title={`${leaderMap[selfId]?.name} vs ${leaderMap[oppId]?.name}`}>
                    {wr.toFixed(0)}
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

function TiersTab({ meta }: { meta: GlobalMetaResponse }) {
  const leaderMap: Record<string, GlobalLeaderStat> = {}
  meta.leaders.forEach((l) => { leaderMap[l.card_id] = l })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {TIER_ORDER.map((tierName) => {
        const ids = meta.tiers[tierName] || []
        if (ids.length === 0) return null
        return (
          <div key={tierName} className="card" style={{ padding: '0.75rem', display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
            <div style={{
              flex: '0 0 2.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '3.5rem',
              borderRadius: '5px',
              fontSize: '1.5rem',
              fontWeight: 800,
              color: '#fff',
              background: TIER_COLORS[tierName] || 'var(--text-secondary)',
            }}>
              {tierName}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {ids.map((cid) => {
                const leader = leaderMap[cid]
                if (!leader) return null
                return (
                  <div key={cid} style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    width: '70px',
                  }}>
                    <img
                      src={leader.image_url}
                      alt={leader.name}
                      style={{ width: '50px', height: '50px', borderRadius: '4px', objectFit: 'cover' }}
                      loading="lazy"
                    />
                    <span style={{ fontSize: '0.65rem', marginTop: '2px', textAlign: 'center', lineHeight: 1.2, color: 'var(--text-primary)' }}>
                      {leader.name}
                    </span>
                    <span style={{ fontSize: '0.68rem', fontWeight: 700, color: TIER_COLORS[tierName] }}>
                      {leader.winrate.toFixed(1)}%
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}

const activeTabStyle: React.CSSProperties = {
  background: 'var(--accent)',
  color: '#fff',
  fontWeight: 600,
  border: '1px solid var(--accent)',
}

const inactiveTabStyle: React.CSSProperties = {
  background: 'var(--bg-primary)',
  color: 'var(--text-secondary)',
  border: '1px solid var(--border)',
}

const thLeftStyle: React.CSSProperties = {
  padding: '0.5rem 0.6rem',
  borderBottom: '2px solid var(--border)',
  textAlign: 'left',
  fontSize: '0.72rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: 'var(--text-secondary)',
  whiteSpace: 'nowrap',
}

const thCenterStyle: React.CSSProperties = {
  ...thLeftStyle,
  textAlign: 'center',
}

const tdStyle: React.CSSProperties = {
  padding: '0.4rem 0.6rem',
  verticalAlign: 'middle',
}

const tdCenterStyle: React.CSSProperties = {
  ...tdStyle,
  textAlign: 'center',
}

const leaderImgStyle: React.CSSProperties = {
  width: '36px',
  height: '36px',
  borderRadius: '4px',
  objectFit: 'cover',
}

const matrixThStyle: React.CSSProperties = {
  padding: '2px',
  textAlign: 'center',
}

const matrixThCornerStyle: React.CSSProperties = {
  padding: '0.3rem',
  fontSize: '0.68rem',
  color: 'var(--text-secondary)',
  textAlign: 'left',
  minWidth: '32px',
}

const matrixTdLabelStyle: React.CSSProperties = {
  padding: '2px',
}

const matrixCellEmptyStyle: React.CSSProperties = {
  padding: '2px 4px',
  textAlign: 'center',
  color: 'var(--text-secondary)',
  opacity: 0.3,
  fontSize: '0.68rem',
}

function matrixCellStyle(wr: number): React.CSSProperties {
  let bg: string
  if (wr >= 55) {
    bg = 'rgba(39, 174, 96, 0.25)'
  } else if (wr >= 50) {
    bg = 'rgba(39, 174, 96, 0.1)'
  } else if (wr >= 45) {
    bg = 'rgba(231, 76, 60, 0.1)'
  } else {
    bg = 'rgba(231, 76, 60, 0.25)'
  }
  return {
    padding: '2px 4px',
    textAlign: 'center',
    background: bg,
    fontSize: '0.68rem',
    fontWeight: 600,
    borderRadius: '2px',
  }
}
