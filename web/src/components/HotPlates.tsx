import { useRef, useEffect, useState } from 'react'
import * as echarts from 'echarts'
import type { HotPlate, StockItem } from '../types'
import { PlateDrilldown } from './PlateDrilldown'

interface Props {
  plates: HotPlate[]
  stocks?: StockItem[]
}

export function HotPlates({ plates, stocks = [] }: Props) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)
  const [drillPlate, setDrillPlate] = useState<string | null>(null)

  useEffect(() => {
    if (!chartRef.current || plates.length === 0) return
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current)
    }
    const chart = chartInstance.current

    const sorted = [...plates].sort((a, b) => a.score - b.score)
    const names = sorted.map(p => p.plate_name + (p.is_new ? ' 🆕' : ''))
    const scores = sorted.map(p => p.score)
    const limitCounts = sorted.map(p => p.limit_up_count)

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: '#1e2330',
        borderColor: '#30363d',
        textStyle: { color: '#e6edf3', fontSize: 12 },
        formatter: (params: any) => {
          const idx = params[0].dataIndex
          const p = sorted[idx]
          return `<b>${p.plate_name}</b>${p.is_new ? ' 🆕' : ''}<br/>` +
            `得分: <span style="color:#f59e0b">${p.score}</span><br/>` +
            `涨停数: <span style="color:#ef4444">${p.limit_up_count}</span><br/>` +
            `热度天数: ${p.days_in_hot}天<br/>` +
            `排名: #${p.rank_no}`
        },
      },
      grid: { top: 8, right: 60, bottom: 8, left: 8, containLabel: true },
      xAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: '#21262d' } },
        axisLabel: { color: '#8b949e', fontSize: 10 },
      },
      yAxis: {
        type: 'category',
        data: names,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#e6edf3', fontSize: 11, width: 70, overflow: 'truncate' },
      },
      series: [
        {
          type: 'bar',
          data: scores,
          barWidth: 14,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: 'rgba(88,166,255,0.3)' },
              { offset: 1, color: '#58a6ff' },
            ]),
            borderRadius: [0, 3, 3, 0],
          },
          label: {
            show: true,
            position: 'right',
            formatter: (p: any) => `${p.value} (${limitCounts[p.dataIndex]}股)`,
            color: '#8b949e',
            fontSize: 10,
          },
        },
      ],
    })

    chart.off('click')
    chart.on('click', (params: any) => {
      setDrillPlate(sorted[params.dataIndex].plate_name)
    })

    return () => { /* keep instance alive */ }
  }, [plates])

  useEffect(() => {
    const handleResize = () => chartInstance.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const chartHeight = Math.max(200, plates.length * 32 + 16)

  return (
    <div className="card">
      <div className="card-header">热门板块 Top10</div>
      <div className="card-body" style={{ padding: '8px' }}>
        <div ref={chartRef} style={{ width: '100%', height: `${chartHeight}px` }} />
      </div>
      {drillPlate && <PlateDrilldown plateName={drillPlate} stocks={stocks} onClose={() => setDrillPlate(null)} />}
    </div>
  )
}
