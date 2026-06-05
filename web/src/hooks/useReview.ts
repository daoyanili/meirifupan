import { useState, useEffect } from 'react'
import { fetchReview, fetchEmotionTrend, fetchDates, fetchInsights } from '../api/client'
import type { ReviewData, EmotionTrendItem, MarketInsights } from '../types'

export function useReview(date: string) {
  const [data, setData] = useState<ReviewData | null>(null)
  const [trend, setTrend] = useState<EmotionTrendItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!date) return
    setLoading(true)
    Promise.all([fetchReview(date), fetchEmotionTrend(date, 5)])
      .then(([review, trend]) => {
        setData(review)
        setTrend(trend)
        setError(null)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [date])

  return { data, trend, loading, error }
}

export function useDates() {
  const [dates, setDates] = useState<string[]>([])
  useEffect(() => {
    fetchDates().then(setDates).catch(console.error)
  }, [])
  return dates
}

export function useInsights(date: string) {
  const [data, setData] = useState<MarketInsights | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!date) return
    setLoading(true)
    fetchInsights(date)
      .then(d => { setData(d); setError(null) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [date])

  return { data, loading, error }
}
