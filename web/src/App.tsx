import { useState, useEffect, useMemo } from 'react'
import { useReview, useDates, useInsights, useHot, useHotDates, useLatestJob, useQuantzzDaily } from './hooks/useReview'
import { DateSelector } from './components/DateSelector'
import { TabBar, type TabKey } from './components/TabBar'
import { DataOverview } from './components/DataOverview'
import { EmotionReview } from './components/EmotionReview'
import { LimitUpReview } from './components/LimitUpReview'
import { ProfitEffectReview } from './components/ProfitEffectReview'
import { QuantzzDailyView } from './components/QuantzzDailyView'
import { ReviewHome } from './components/ReviewHome'
import './styles/globals.css'

export default function App() {
  const reviewDates = useDates()
  const hotDates = useHotDates()
  const latestJob = useLatestJob()
  const [date, setDate] = useState('')
  const [tab, setTab] = useState<TabKey>('review-home')

  const activeDates = reviewDates

  // Compute effective date: if current date isn't in activeDates, pick the first available
  const effectiveDate = useMemo(() => {
    if (activeDates.length === 0) return ''
    if (activeDates.includes(date)) return date
    return activeDates[0]
  }, [activeDates, date])

  // Sync date state when effectiveDate changes
  useEffect(() => {
    if (effectiveDate && effectiveDate !== date) {
      setDate(effectiveDate)
    }
  }, [effectiveDate, date])

  const { data, trend, marketTrend, loading, error } = useReview(effectiveDate)
  const { data: insights, loading: insightLoading } = useInsights(effectiveDate)
  const hotDate = hotDates.includes(effectiveDate) ? effectiveDate : hotDates[0] ?? ''
  const { data: hotData, loading: hotLoading, error: hotError } = useHot(tab === 'emotion-review' ? hotDate : '')
  const {
    data: quantzzDaily,
    loading: quantzzLoading,
    error: quantzzError,
  } = useQuantzzDaily(tab === 'quantzz-daily' ? effectiveDate : '')

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        const idx = activeDates.indexOf(date)
        if (idx < activeDates.length - 1) setDate(activeDates[idx + 1])
      } else if (e.key === 'ArrowRight') {
        const idx = activeDates.indexOf(date)
        if (idx > 0) setDate(activeDates[idx - 1])
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [date, activeDates])

  if (loading) return <div className="loading">加载中...</div>
  if (error) return <div className="error">{error}</div>

  return (
    <div className="container">
      <div className="header">
        <h1>发家致富 · 每日复盘</h1>
        <DateSelector dates={activeDates} value={date} onChange={setDate} />
      </div>
      <TabBar active={tab} onChange={setTab} />
      <div className="tab-content">
        {tab === 'review-home' && data && (
          <ReviewHome data={data} emotionTrend={trend} marketTrend={marketTrend} onOpenTab={setTab} />
        )}
        {tab === 'quantzz-daily' && (
          <QuantzzDailyView data={quantzzDaily} loading={quantzzLoading} error={quantzzError} />
        )}
        {tab === 'limit-up-review' && data && <LimitUpReview data={data} />}
        {tab === 'emotion-review' && data && (
          <EmotionReview data={data} trend={trend} hotData={hotData} hotLoading={hotLoading} hotError={hotError} />
        )}
        {tab === 'profit-effect' && data && (
          <ProfitEffectReview data={data} insights={insights} loading={insightLoading} />
        )}
        {tab === 'data-overview' && data && (
          <DataOverview data={data} trend={trend} marketTrend={marketTrend} latestJob={latestJob} />
        )}
      </div>
    </div>
  )
}
