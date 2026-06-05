import { useState, useMemo, useRef, useCallback } from 'react'
import type { StockItem } from '../types'

interface Props {
  stocks: StockItem[]
}

type SortKey = 'up_limit_time' | 'up_limit_keep_times' | 'fengdan_money' | 'amount'

interface PlateGroup {
  plate: string
  stocks: StockItem[]
}

export function PlateGroupView({ stocks }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('fengdan_money')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const [showReason, setShowReason] = useState(true)
  const [search, setSearch] = useState('')
  const plateRefs = useRef<Record<string, HTMLDivElement | null>>({})

  // Filter by search
  const filtered = useMemo(() => {
    if (!search) return stocks
    return stocks.filter(s =>
      s.stock_name.includes(search) ||
      s.stock_code.includes(search) ||
      s.plates.some(p => p.includes(search))
    )
  }, [stocks, search])

  // Group by primary_plate
  const groups: PlateGroup[] = useMemo(() => {
    const map = new Map<string, StockItem[]>()
    for (const s of filtered) {
      const plate = s.primary_plate || '其他'
      if (!map.has(plate)) map.set(plate, [])
      map.get(plate)!.push(s)
    }
    return Array.from(map.entries())
      .map(([plate, stocks]) => {
        const sorted = [...stocks].sort((a, b) => {
          const va = a[sortKey] as number
          const vb = b[sortKey] as number
          return sortDir === 'asc' ? va - vb : vb - va
        })
        return { plate, stocks: sorted }
      })
      .sort((a, b) => b.stocks.length - a.stocks.length)
  }, [filtered, sortKey, sortDir])

  const toggleCollapse = useCallback((plate: string) => {
    setCollapsed(prev => {
      const next = new Set(prev)
      if (next.has(plate)) next.delete(plate)
      else next.add(plate)
      return next
    })
  }, [])

  const scrollToPlate = useCallback((plate: string) => {
    plateRefs.current[plate]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return ' ↕'
    return sortDir === 'asc' ? ' ↑' : ' ↓'
  }

  const fmt = (v: number) => {
    if (v >= 100000000) return (v / 100000000).toFixed(1) + '亿'
    if (v >= 10000) return (v / 10000).toFixed(0) + '万'
    return v.toFixed(0)
  }

  return (
    <div className="plate-group-container">
      {/* Toolbar */}
      <div className="plate-toolbar">
        <input
          type="text"
          placeholder="搜索股票/板块..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="plate-search"
        />
        <div className="plate-toggles">
          <label className="toggle-label">
            <input type="checkbox" checked={showReason} onChange={e => setShowReason(e.target.checked)} />
            <span>涨停原因</span>
          </label>
        </div>
        <div className="plate-sort-group">
          {(['fengdan_money', 'up_limit_time', 'up_limit_keep_times', 'amount'] as SortKey[]).map(key => {
            const labels: Record<SortKey, string> = {
              fengdan_money: '封单额',
              up_limit_time: '时间',
              up_limit_keep_times: '连板',
              amount: '成交额',
            }
            return (
              <button
                key={key}
                className={`sort-btn ${sortKey === key ? 'active' : ''}`}
                onClick={() => toggleSort(key)}
              >
                {labels[key]}{sortIcon(key)}
              </button>
            )
          })}
        </div>
      </div>

      <div className="plate-main-layout">
        {/* Sidebar navigation */}
        <div className="plate-nav-sidebar">
          <div className="plate-nav-title">板块导航</div>
          {groups.map(g => (
            <button
              key={g.plate}
              className={`plate-nav-item ${collapsed.has(g.plate) ? '' : 'active'}`}
              onClick={() => {
                if (collapsed.has(g.plate)) toggleCollapse(g.plate)
                scrollToPlate(g.plate)
              }}
            >
              <span className="plate-nav-name">{g.plate}</span>
              <span className="plate-nav-count">{g.stocks.length}</span>
            </button>
          ))}
        </div>

        {/* Plate groups */}
        <div className="plate-groups">
          {groups.map(g => (
            <div
              key={g.plate}
              ref={el => { plateRefs.current[g.plate] = el }}
              className="plate-section"
            >
              <div
                className="plate-header"
                onClick={() => toggleCollapse(g.plate)}
              >
                <span className="plate-header-name">{g.plate}</span>
                <span className="plate-header-count">{g.stocks.length}只</span>
                <span className="plate-header-arrow">{collapsed.has(g.plate) ? '▸' : '▾'}</span>
              </div>
              {!collapsed.has(g.plate) && (
                <div className="plate-table-wrap">
                  <table className="table plate-table">
                    <thead>
                      <tr>
                        <th>名称</th>
                        <th>代码</th>
                        <th>时间</th>
                        <th>板高</th>
                        <th>封单额</th>
                        <th>成交额</th>
                        {showReason && <th>涨停原因</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {g.stocks.map(s => (
                        <tr key={s.stock_code}>
                          <td style={{ fontWeight: 600 }}>{s.stock_name}</td>
                          <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{s.stock_code}</td>
                          <td>{s.up_limit_time}</td>
                          <td>
                            <span className={s.up_limit_keep_times > 1 ? 'text-red' : ''}>
                              {s.up_limit_keep_times > 1 ? `${s.up_limit_keep_times}板` : '首板'}
                            </span>
                          </td>
                          <td style={{ fontVariantNumeric: 'tabular-nums' }}>{fmt(s.fengdan_money)}</td>
                          <td style={{ fontVariantNumeric: 'tabular-nums' }}>{fmt(s.amount)}</td>
                          {showReason && (
                            <td style={{ color: 'var(--text-secondary)', fontSize: '12px', maxWidth: '200px', whiteSpace: 'normal' }}>
                              {s.reason}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
