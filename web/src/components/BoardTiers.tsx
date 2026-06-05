import type { BoardTier } from '../types'

interface Props {
  tiers: BoardTier[]
  fullView?: boolean
}

export function BoardTiers({ tiers, fullView }: Props) {
  if (tiers.length === 0) {
    return (
      <div className="card">
        <div className="card-header">连板梯队</div>
        <div className="card-body" style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          暂无连板数据
        </div>
      </div>
    )
  }

  const sorted = [...tiers].sort((a, b) => b.level - a.level)

  const fmt = (v: number) => {
    if (v >= 100000000) return (v / 100000000).toFixed(1) + '亿'
    if (v >= 10000) return (v / 10000).toFixed(0) + '万'
    return v.toFixed(0)
  }

  if (fullView) {
    return (
      <div>
        {sorted.map(tier => (
          <div key={tier.level} className="card" style={{ marginBottom: '16px' }}>
            <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="tag tag-red">{tier.level}连板</span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{tier.count}只</span>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th>代码</th>
                    <th>涨停时间</th>
                    <th>类型</th>
                    <th>封单额</th>
                    <th>板块</th>
                  </tr>
                </thead>
                <tbody>
                  {tier.stocks.map(stock => (
                    <tr key={stock.stock_code}>
                      <td style={{ fontWeight: 600 }}>{stock.stock_name}</td>
                      <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{stock.stock_code}</td>
                      <td>{stock.up_limit_time}</td>
                      <td>
                        <span className={`tag ${stock.up_limit_type === '一字板' ? 'tag-yellow' : 'tag-blue'}`}>
                          {stock.up_limit_type}
                        </span>
                      </td>
                      <td style={{ fontVariantNumeric: 'tabular-nums' }}>{fmt(stock.fengdan_money)}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                          {stock.plates.slice(0, 3).map(p => (
                            <span key={p} className="tag tag-blue" style={{ fontSize: '10px' }}>{p}</span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-header">连板梯队</div>
      <div className="card-body">
        {sorted.map(tier => (
          <div key={tier.level} style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span className="tag tag-red">{tier.level}连板</span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{tier.count}只</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {tier.stocks.map(stock => (
                <div
                  key={stock.stock_code}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-tertiary)',
                    borderRadius: '6px',
                    fontSize: '12px',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                  }}
                >
                  <span style={{ fontWeight: 600, minWidth: '60px' }}>{stock.stock_name}</span>
                  <span style={{ color: 'var(--text-secondary)', fontFamily: 'monospace', fontSize: '11px' }}>
                    {stock.stock_code}
                  </span>
                  <span style={{ color: 'var(--text-secondary)' }}>{stock.up_limit_time}</span>
                  <span className={`tag ${stock.up_limit_type === '一字板' ? 'tag-yellow' : 'tag-blue'}`}>
                    {stock.up_limit_type}
                  </span>
                  <span style={{ color: 'var(--color-yellow)', fontSize: '11px' }}>
                    {fmt(stock.fengdan_money)}
                  </span>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginLeft: 'auto' }}>
                    {stock.plates.slice(0, 2).map(p => (
                      <span key={p} className="tag tag-blue" style={{ fontSize: '10px' }}>{p}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
