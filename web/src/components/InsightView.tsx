import { useRef, useEffect } from 'react'
import * as echarts from 'echarts'
import type { MarketInsights } from '../types'

interface Props {
  data: MarketInsights
}

export function InsightView({ data }: Props) {
  const { seal_quality: sq, board_advancement: adv, capital_flow: flow, hot_stocks: hot } = data

  return (
    <div className="insight-container">
      {/* Row 1: Seal Quality + Board Advancement */}
      <div className="insight-row">
        <SealQualityCard sq={sq} />
        <BoardAdvancementCard adv={adv} />
      </div>
      {/* Row 2: Capital Flow Chart */}
      <CapitalFlowChart flow={flow} />
      {/* Row 3: Hot Stocks */}
      <HotStocksCard stocks={hot} />
    </div>
  )
}

function SealQualityCard({ sq }: { sq: MarketInsights['seal_quality'] }) {
  const brokenDelta = sq.broken_rate - sq.prev_broken_rate
  const sealDelta = (sq.avg_seal_rate || 0) - (sq.prev_avg_seal_rate || 0)

  return (
    <div className="card insight-card">
      <div className="card-header">赚钱效应</div>
      <div className="card-body">
        <div className="insight-metrics">
          <div className="insight-metric">
            <div className="insight-metric-label">烂板率</div>
            <div className="insight-metric-value" style={{ color: sq.broken_rate > 30 ? 'var(--color-red)' : 'var(--color-green)' }}>
              {sq.broken_rate}%
            </div>
            <div className="insight-metric-delta" style={{ color: brokenDelta > 0 ? 'var(--color-red)' : 'var(--color-green)' }}>
              {brokenDelta > 0 ? '+' : ''}{brokenDelta.toFixed(1)}% vs 昨日
            </div>
          </div>
          <div className="insight-metric">
            <div className="insight-metric-label">一字板占比</div>
            <div className="insight-metric-value" style={{ color: 'var(--color-yellow)' }}>
              {sq.one_seal_rate}%
            </div>
            <div className="insight-metric-sub">{sq.one_seal}只 / {sq.total}只</div>
          </div>
          <div className="insight-metric">
            <div className="insight-metric-label">平均封单率</div>
            <div className="insight-metric-value" style={{ color: 'var(--color-blue)' }}>
              {((sq.avg_seal_rate || 0) * 100).toFixed(1)}%
            </div>
            <div className="insight-metric-delta" style={{ color: sealDelta > 0 ? 'var(--color-green)' : 'var(--color-red)' }}>
              {sealDelta > 0 ? '+' : ''}{(sealDelta * 100).toFixed(1)}% vs 昨日
            </div>
          </div>
          <div className="insight-metric">
            <div className="insight-metric-label">首板占比</div>
            <div className="insight-metric-value" style={{ color: 'var(--color-purple)' }}>
              {sq.first_board_rate}%
            </div>
            <div className="insight-metric-sub">{sq.first_board}只首板 / {sq.multi_board}只连板</div>
          </div>
        </div>

        {/* Seal type distribution bar */}
        <div style={{ marginTop: '16px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>封板类型分布</div>
          <div className="seal-bar">
            <div className="seal-bar-segment" style={{
              width: `${sq.one_seal_rate}%`,
              background: 'var(--color-yellow)',
            }} title={`一字板 ${sq.one_seal}`} />
            <div className="seal-bar-segment" style={{
              width: `${100 - sq.one_seal_rate - sq.broken_rate}%`,
              background: 'var(--color-green)',
            }} title={`换手板 ${sq.normal_seal}`} />
            <div className="seal-bar-segment" style={{
              width: `${sq.broken_rate}%`,
              background: 'var(--color-red)',
            }} title={`烂板 ${sq.broken_seal}`} />
          </div>
          <div style={{ display: 'flex', gap: '16px', marginTop: '4px', fontSize: '11px' }}>
            <span><span style={{ color: 'var(--color-yellow)' }}>■</span> 一字板 {sq.one_seal}</span>
            <span><span style={{ color: 'var(--color-green)' }}>■</span> 换手板 {sq.normal_seal}</span>
            <span><span style={{ color: 'var(--color-red)' }}>■</span> 烂板 {sq.broken_seal}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function BoardAdvancementCard({ adv }: { adv: MarketInsights['board_advancement'] }) {
  if (adv.length === 0) {
    return (
      <div className="card insight-card">
        <div className="card-header">连板晋级</div>
        <div className="card-body" style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          无前日数据
        </div>
      </div>
    )
  }

  return (
    <div className="card insight-card">
      <div className="card-header">连板晋级率（vs 昨日）</div>
      <div className="card-body" style={{ padding: 0 }}>
        <table className="table">
          <thead>
            <tr>
              <th>层级</th>
              <th>昨日</th>
              <th>晋级</th>
              <th>断板</th>
              <th>晋级率</th>
              <th>断板率</th>
            </tr>
          </thead>
          <tbody>
            {adv.map(a => (
              <tr key={a.level}>
                <td><span className="tag tag-red">{a.level}板</span></td>
                <td>{a.total}只</td>
                <td className="text-red">{a.advanced}↑</td>
                <td className="text-green">{a.failed}↓</td>
                <td style={{
                  color: a.advancement_rate >= 50 ? 'var(--color-red)' : 'var(--color-green)',
                  fontWeight: 600,
                }}>
                  {a.advancement_rate}%
                </td>
                <td style={{
                  color: a.fail_rate >= 50 ? 'var(--color-red)' : 'var(--color-green)',
                }}>
                  {a.fail_rate}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function CapitalFlowChart({ flow }: { flow: MarketInsights['capital_flow'] }) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!chartRef.current || flow.length === 0) return
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current)
    }
    const chart = chartInstance.current

    const sorted = [...flow].sort((a, b) => a.net_flow - b.net_flow)
    const names = sorted.map(f => f.plate_name)
    const values = sorted.map(f => f.net_flow)

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: '#1e2330',
        borderColor: '#30363d',
        textStyle: { color: '#e6edf3', fontSize: 12 },
        formatter: (params: any) => {
          const idx = params[0].dataIndex
          const f = sorted[idx]
          const sign = f.net_flow >= 0 ? '+' : ''
          return `<b>${f.plate_name}</b><br/>` +
            `净流入: <span style="color:${f.net_flow >= 0 ? '#ef4444' : '#22c55e'}">${sign}${(f.net_flow / 100000000).toFixed(2)}亿</span><br/>` +
            `买入: ${(f.buy / 100000000).toFixed(2)}亿<br/>` +
            `卖出: ${(f.sell / 100000000).toFixed(2)}亿<br/>` +
            `涨跌: ${f.rate > 0 ? '+' : ''}${f.rate.toFixed(2)}%`
        },
      },
      grid: { top: 8, right: 60, bottom: 8, left: 8, containLabel: true },
      xAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: '#21262d' } },
        axisLabel: {
          color: '#8b949e',
          fontSize: 10,
          formatter: (v: number) => (v / 100000000).toFixed(0) + '亿',
        },
      },
      yAxis: {
        type: 'category',
        data: names,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#e6edf3', fontSize: 11, width: 70, overflow: 'truncate' },
      },
      series: [{
        type: 'bar',
        data: values.map(v => ({
          value: v,
          itemStyle: { color: v >= 0 ? '#ef4444' : '#22c55e' },
        })),
        barWidth: 12,
        itemStyle: { borderRadius: (v: number) => v >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3] },
        label: {
          show: true,
          position: 'right',
          formatter: (p: any) => {
            const v = p.value
            return (v >= 0 ? '+' : '') + (v / 100000000).toFixed(1) + '亿'
          },
          color: '#8b949e',
          fontSize: 10,
        },
      }],
    })

    chart.off('click')
    return () => { /* keep instance alive */ }
  }, [flow])

  useEffect(() => {
    const handleResize = () => chartInstance.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const chartHeight = Math.max(200, flow.length * 28 + 16)

  return (
    <div className="card" style={{ marginBottom: '16px' }}>
      <div className="card-header">板块主力资金流向 Top20</div>
      <div className="card-body" style={{ padding: '8px' }}>
        <div ref={chartRef} style={{ width: '100%', height: `${chartHeight}px` }} />
      </div>
    </div>
  )
}

function HotStocksCard({ stocks }: { stocks: MarketInsights['hot_stocks'] }) {
  const fmt = (v: number) => {
    if (v >= 100000000) return (v / 100000000).toFixed(1) + '亿'
    if (v >= 10000) return (v / 10000).toFixed(0) + '万'
    return v.toFixed(0)
  }

  return (
    <div className="card">
      <div className="card-header">热门个股（封单额 Top20）</div>
      <div className="card-body" style={{ padding: 0, maxHeight: '500px', overflowY: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th>#</th>
              <th>名称</th>
              <th>代码</th>
              <th>连板</th>
              <th>封单额</th>
              <th>封单率</th>
              <th>成交额</th>
              <th>板块</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s, i) => (
              <tr key={s.stock_code}>
                <td style={{ color: i < 3 ? 'var(--color-red)' : 'var(--text-secondary)', fontWeight: i < 3 ? 700 : 400 }}>
                  {i + 1}
                </td>
                <td style={{ fontWeight: 600 }}>{s.stock_name}</td>
                <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{s.stock_code}</td>
                <td>
                  <span className={s.up_limit_keep_times > 1 ? 'text-red' : ''}>
                    {s.up_limit_keep_times > 1 ? `${s.up_limit_keep_times}板` : '首板'}
                  </span>
                </td>
                <td style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 600, color: 'var(--color-yellow)' }}>
                  {fmt(s.fengdan_money)}
                </td>
                <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {((s.fengdan_rate || 0) * 100).toFixed(1)}%
                </td>
                <td style={{ fontVariantNumeric: 'tabular-nums' }}>{s.amount.toFixed(1)}亿</td>
                <td>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {s.plates.slice(0, 3).map(p => (
                      <span key={p} className="tag tag-blue" style={{ fontSize: '10px' }}>{p}</span>
                    ))}
                    {s.plate_count > 3 && <span className="tag" style={{ fontSize: '10px' }}>+{s.plate_count - 3}</span>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
