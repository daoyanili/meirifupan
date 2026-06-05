import { useState, useMemo } from 'react'
import type { StockItem } from '../types'

interface Props {
  stocks: StockItem[]
}

type SortKey = 'up_limit_time' | 'up_limit_keep_times' | 'fengdan_money' | 'amount' | null
type SortDir = 'asc' | 'desc'

export function StockTable({ stocks }: Props) {
  const [filter, setFilter] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>(null)
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const filtered = useMemo(() => {
    let list = filter
      ? stocks.filter(s =>
          s.stock_name.includes(filter) ||
          s.stock_code.includes(filter) ||
          s.plates.some(p => p.includes(filter))
        )
      : stocks

    if (sortKey) {
      list = [...list].sort((a, b) => {
        const va = a[sortKey] as number
        const vb = b[sortKey] as number
        return sortDir === 'asc' ? va - vb : vb - va
      })
    }
    return list
  }, [stocks, filter, sortKey, sortDir])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return ' ↕'
    return sortDir === 'asc' ? ' ↑' : ' ↓'
  }

  const thStyle = (key: SortKey): React.CSSProperties => ({
    cursor: 'pointer',
    userSelect: 'none',
    color: sortKey === key ? 'var(--color-blue)' : undefined,
  })

  return (
    <div className="card">
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>涨停个股明细 ({filtered.length})</span>
        <input
          type="text"
          placeholder="搜索股票/板块..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          style={{
            padding: '4px 8px',
            fontSize: '12px',
            backgroundColor: 'var(--bg-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            color: 'var(--text-primary)',
            outline: 'none',
            width: '200px',
          }}
        />
      </div>
      <div className="card-body" style={{ padding: 0, maxHeight: '600px', overflowY: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th style={thStyle('up_limit_time')} onClick={() => toggleSort('up_limit_time')}>
                涨停时间{sortIcon('up_limit_time')}
              </th>
              <th style={thStyle('up_limit_keep_times')} onClick={() => toggleSort('up_limit_keep_times')}>
                连板{sortIcon('up_limit_keep_times')}
              </th>
              <th>类型</th>
              <th style={thStyle('fengdan_money')} onClick={() => toggleSort('fengdan_money')}>
                封单金额{sortIcon('fengdan_money')}
              </th>
              <th>封单占比</th>
              <th style={thStyle('amount')} onClick={() => toggleSort('amount')}>
                成交额{sortIcon('amount')}
              </th>
              <th>板块</th>
              <th>原因</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(stock => (
              <tr key={stock.stock_code}>
                <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{stock.stock_code}</td>
                <td style={{ fontWeight: 600 }}>{stock.stock_name}</td>
                <td>{stock.up_limit_time}</td>
                <td className="text-red">{stock.up_limit_keep_times > 1 ? `${stock.up_limit_keep_times}板` : '首板'}</td>
                <td>
                  <span className={`tag ${stock.up_limit_type === '一字板' ? 'tag-yellow' : 'tag-blue'}`}>
                    {stock.up_limit_type}
                  </span>
                </td>
                <td style={{ fontVariantNumeric: 'tabular-nums' }}>{(stock.fengdan_money / 10000).toFixed(0)}万</td>
                <td style={{ fontVariantNumeric: 'tabular-nums' }}>{(stock.fengdan_rate * 100).toFixed(1)}%</td>
                <td style={{ fontVariantNumeric: 'tabular-nums' }}>{(stock.amount / 10000).toFixed(0)}万</td>
                <td>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px' }}>
                    {stock.plates.slice(0, 2).map(p => (
                      <span key={p} className="tag tag-blue">{p}</span>
                    ))}
                    {stock.plates.length > 2 && <span className="tag">+{stock.plates.length - 2}</span>}
                  </div>
                </td>
                <td style={{ color: 'var(--text-secondary)', maxWidth: '150px', whiteSpace: 'normal', fontSize: '12px' }}>
                  {stock.reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
