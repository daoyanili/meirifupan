import type { EmotionData, EmotionTrendItem } from '../types'
import { EmotionGauge } from './EmotionGauge'
import { EmotionTrend } from './EmotionTrend'

interface Props {
  emotion: EmotionData
  trend: EmotionTrendItem[]
}

export function EmotionDetail({ emotion, trend }: Props) {
  const details = [
    emotion.scores.limit_up_count,
    emotion.scores.board_height,
    emotion.scores.first_board_count,
    emotion.scores.limit_ratio,
    emotion.scores.market_change,
  ]

  return (
    <>
      <div className="grid-2" style={{ marginBottom: '16px' }}>
        <EmotionGauge emotion={emotion} />
        <div className="card">
          <div className="card-header">评分明细</div>
          <div className="card-body">
            {details.map(d => (
              <div key={d.label} style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{d.label}</span>
                  <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                    {d.value} → <span style={{ color: 'var(--color-blue)', fontWeight: 600 }}>{d.score}</span>/3
                    <span style={{ marginLeft: '8px', fontSize: '11px' }}>权重 {(d.weight * 100).toFixed(0)}%</span>
                  </span>
                </div>
                <div style={{
                  height: '8px',
                  backgroundColor: 'var(--bg-tertiary)',
                  borderRadius: '4px',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%',
                    width: `${(d.score / 3) * 100}%`,
                    borderRadius: '4px',
                    backgroundColor: d.score >= 3 ? 'var(--color-red)' : d.score >= 2 ? 'var(--color-yellow)' : d.score >= 1 ? 'var(--color-blue)' : 'var(--color-green)',
                    transition: 'width 0.6s ease',
                  }} />
                </div>
              </div>
            ))}
            <div style={{
              marginTop: '20px',
              padding: '12px',
              backgroundColor: 'var(--bg-tertiary)',
              borderRadius: '6px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>操作建议</div>
              <div style={{ fontSize: '14px', color: 'var(--text-primary)' }}>{emotion.advice}</div>
            </div>
          </div>
        </div>
      </div>
      <EmotionTrend trend={trend} />
    </>
  )
}
