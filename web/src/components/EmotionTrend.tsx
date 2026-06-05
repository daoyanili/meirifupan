import { useRef, useEffect } from 'react'
import * as echarts from 'echarts'
import type { EmotionTrendItem } from '../types'

interface Props {
  trend: EmotionTrendItem[]
}

export function EmotionTrend({ trend }: Props) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!chartRef.current || trend.length === 0) return
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current)
    }
    const chart = chartInstance.current

    const dates = trend.map(t => t.date.slice(5))
    const scores = trend.map(t => t.total_score)
    const limitCounts = trend.map(t => t.scores.limit_up_count.value)
    const highBoards = trend.map(t => t.scores.board_height.value)

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1e2330',
        borderColor: '#30363d',
        textStyle: { color: '#e6edf3', fontSize: 12 },
      },
      legend: {
        data: ['情绪得分', '涨停数', '最高板'],
        textStyle: { color: '#8b949e', fontSize: 11 },
        top: 0,
        right: 0,
        itemWidth: 14,
        itemHeight: 8,
      },
      grid: { top: 32, right: 60, bottom: 24, left: 48 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#30363d' } },
        axisLabel: { color: '#8b949e', fontSize: 11 },
        axisTick: { show: false },
      },
      yAxis: [
        {
          type: 'value',
          name: '得分',
          nameTextStyle: { color: '#8b949e', fontSize: 10 },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { lineStyle: { color: '#21262d' } },
          axisLabel: { color: '#8b949e', fontSize: 11 },
          min: 0,
          max: 5,
        },
        {
          type: 'value',
          name: '数量',
          nameTextStyle: { color: '#8b949e', fontSize: 10 },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { color: '#8b949e', fontSize: 11 },
        },
      ],
      series: [
        {
          name: '情绪得分',
          type: 'line',
          data: scores,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2, color: '#58a6ff' },
          itemStyle: { color: '#58a6ff' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(88,166,255,0.25)' },
              { offset: 1, color: 'rgba(88,166,255,0)' },
            ]),
          },
        },
        {
          name: '涨停数',
          type: 'bar',
          yAxisIndex: 1,
          data: limitCounts,
          barWidth: 20,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(239,68,68,0.8)' },
              { offset: 1, color: 'rgba(239,68,68,0.2)' },
            ]),
            borderRadius: [2, 2, 0, 0],
          },
        },
        {
          name: '最高板',
          type: 'line',
          yAxisIndex: 1,
          data: highBoards,
          symbol: 'diamond',
          symbolSize: 8,
          lineStyle: { width: 2, color: '#f59e0b', type: 'dashed' },
          itemStyle: { color: '#f59e0b' },
        },
      ],
    })

    return () => { /* keep instance alive */ }
  }, [trend])

  useEffect(() => {
    const handleResize = () => chartInstance.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div className="card" style={{ marginBottom: '16px' }}>
      <div className="card-header">近5日趋势</div>
      <div className="card-body" style={{ padding: '8px' }}>
        <div ref={chartRef} style={{ width: '100%', height: '220px' }} />
      </div>
    </div>
  )
}
