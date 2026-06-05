import type { IndexData } from '../types'

interface Props {
  indices: IndexData[]
}

export function IndexCards({ indices }: Props) {
  return (
    <div className="card">
      <div className="card-header">大盘指数</div>
      <div className="card-body">
        <div style={{ display: 'flex', gap: '16px' }}>
          {indices.map(idx => {
            const isUp = idx.change_pct >= 0
            return (
              <div key={idx.index_code} style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '4px' }}>
                  {idx.index_name}
                </div>
                <div style={{ fontSize: '18px', fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
                  {idx.close_price.toFixed(2)}
                </div>
                <div
                  className={isUp ? 'text-red' : 'text-green'}
                  style={{
                    fontSize: '14px',
                    fontWeight: 600,
                    fontVariantNumeric: 'tabular-nums',
                    marginTop: '2px',
                  }}
                >
                  {isUp ? '+' : ''}{idx.change_pct.toFixed(2)}%
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
