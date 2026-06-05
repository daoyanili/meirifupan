import { useState, useEffect } from 'react'
import { useReview, useDates, useInsights } from './hooks/useReview'
import { DateSelector } from './components/DateSelector'
import { TabBar, type TabKey } from './components/TabBar'
import { PlateGroupView } from './components/PlateGroupView'
import { BoardTiers } from './components/BoardTiers'
import { EmotionDetail } from './components/EmotionDetail'
import { InsightView } from './components/InsightView'
import { Overview } from './components/Overview'
import './styles/globals.css'

export default function App() {
  const dates = useDates()
  const [date, setDate] = useState('')
  const [tab, setTab] = useState<TabKey>('plate')
  const { data, trend, loading, error } = useReview(date)
  const { data: insights, loading: insightLoading } = useInsights(date)

  useEffect(() => {
    if (dates.length > 0 && !date) setDate(dates[0])
  }, [dates, date])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        const idx = dates.indexOf(date)
        if (idx < dates.length - 1) setDate(dates[idx + 1])
      } else if (e.key === 'ArrowRight') {
        const idx = dates.indexOf(date)
        if (idx > 0) setDate(dates[idx - 1])
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [date, dates])

  if (loading) return <div className="loading">加载中...</div>
  if (error) return <div className="error">{error}</div>
  if (!data) return null

  return (
    <div className="container">
      <div className="header">
        <h1>发家致富 · 每日复盘</h1>
        <DateSelector dates={dates} value={date} onChange={setDate} />
      </div>
      <TabBar active={tab} onChange={setTab} />
      <div className="tab-content">
        {tab === 'plate' && <PlateGroupView stocks={data.all_stocks} />}
        {tab === 'tier' && <BoardTiers tiers={data.board_tiers} fullView />}
        {tab === 'emotion' && <EmotionDetail emotion={data.emotion} trend={trend} />}
        {tab === 'insight' && (insightLoading ? <div className="loading">加载洞察数据...</div> : insights ? <InsightView data={insights} /> : <div className="error">无数据</div>)}
        {tab === 'overview' && <Overview data={data} trend={trend} />}
      </div>
    </div>
  )
}
