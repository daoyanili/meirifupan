import { useRef, useEffect } from 'react'
import * as echarts from 'echarts'
import type { EmotionData } from '../types'

interface Props {
  emotion: EmotionData
}

const LEVEL_COLORS: [number, string][] = [
  [0.2, '#22c55e'],
  [0.4, '#84cc16'],
  [0.6, '#eab308'],
  [0.8, '#f97316'],
  [1, '#ef4444'],
]

export function EmotionGauge({ emotion }: Props) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!chartRef.current) return
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current)
    }
    const chart = chartInstance.current

    chart.setOption({
      series: [
        {
          type: 'gauge',
          startAngle: 200,
          endAngle: -20,
          min: 0,
          max: 5,
          splitNumber: 5,
          axisLine: {
            lineStyle: {
              width: 20,
              color: LEVEL_COLORS,
            },
          },
          pointer: {
            icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
            length: '60%',
            width: 8,
            offsetCenter: [0, '-50%'],
            itemStyle: { color: 'auto' },
          },
          axisTick: { distance: -20, length: 6, lineStyle: { color: '#fff', width: 1 } },
          splitLine: { distance: -24, length: 14, lineStyle: { color: '#fff', width: 2 } },
          axisLabel: {
            color: 'var(--text-secondary)',
            distance: 28,
            fontSize: 11,
            formatter: (v: number) => {
              if (v === 0) return '冰点'
              if (v === 1) return '低迷'
              if (v === 2) return '中性'
              if (v === 3) return '偏热'
              if (v === 4) return '亢奋'
              if (v === 5) return '过热'
              return ''
            },
          },
          detail: {
            valueAnimation: true,
            formatter: '{value}',
            fontSize: 28,
            fontWeight: 700,
            offsetCenter: [0, '20%'],
            color: 'var(--text-primary)',
          },
          title: {
            offsetCenter: [0, '45%'],
            fontSize: 14,
            color: 'var(--text-secondary)',
          },
          data: [{ value: emotion.total_score, name: emotion.level }],
        },
      ],
    })

    return () => { /* keep instance alive */ }
  }, [emotion])

  useEffect(() => {
    const handleResize = () => chartInstance.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div className="card">
      <div className="card-header">情绪指标</div>
      <div className="card-body" style={{ padding: '8px' }}>
        <div ref={chartRef} style={{ width: '100%', height: '200px' }} />
        <div style={{ textAlign: 'center', fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          {emotion.advice}
        </div>
      </div>
    </div>
  )
}
