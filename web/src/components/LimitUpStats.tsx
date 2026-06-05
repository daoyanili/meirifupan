import type { LimitUpStats as LimitUpStatsType } from '../types'

interface Props {
  stats: LimitUpStatsType
}

export function LimitUpStats({ stats }: Props) {
  const diff = stats.total - stats.prev_total
  const diffPct = stats.prev_total > 0 ? ((diff / stats.prev_total) * 100).toFixed(0) : null

  const items = [
    { label: '涨停数', value: stats.total, color: 'var(--color-red)' },
    { label: '首板', value: stats.first_board, color: 'var(--color-blue)' },
    { label: '连板', value: stats.multi_board, color: 'var(--color-purple)' },
    { label: '最高板', value: stats.highest_board, color: 'var(--color-yellow)' },
  ]

  return (
    <div className="card">
      <div className="card-header">涨停统计</div>
      <div className="card-body">
        <div style={{ display: 'flex', gap: '16px' }}>
          {items.map(item => (
            <div key={item.label} style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '4px' }}>
                {item.label}
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: item.color, fontVariantNumeric: 'tabular-nums' }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
        {stats.prev_total > 0 && (
          <div style={{
            marginTop: '8px',
            fontSize: '12px',
            color: 'var(--text-secondary)',
            textAlign: 'center',
            display: 'flex',
            justifyContent: 'center',
            gap: '8px',
          }}>
            <span>昨日: {stats.prev_total}</span>
            <span className={diff >= 0 ? 'text-red' : 'text-green'}>
              {diff >= 0 ? '+' : ''}{diff}
              {diffPct !== null && ` (${diff >= 0 ? '+' : ''}${diffPct}%)`}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
