import { useState, useEffect } from 'react'
import {
  fetchReview,
  fetchEmotionTrend,
  fetchDates,
  fetchMarketOverviewTrend,
  fetchQuantzzDaily,
  fetchInsights,
  fetchHot,
  fetchHotDates,
  fetchLatestJob,
} from '../api/client'
import type {
  ReviewData,
  EmotionTrendItem,
  MarketInsights,
  HotData,
  DataJob,
  MarketOverviewTrendItem,
  QuantzzDailyOverview,
} from '../types'

export function useReview(date: string) {
  const [data, setData] = useState<ReviewData | null>(null)
  const [trend, setTrend] = useState<EmotionTrendItem[]>([])
  const [marketTrend, setMarketTrend] = useState<MarketOverviewTrendItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!date) {
      setData(null)
      setTrend([])
      setMarketTrend([])
      setLoading(false)
      setError(null)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    Promise.all([
      fetchReview(date, ctrl.signal),
      fetchEmotionTrend(date, 60, ctrl.signal),
      fetchMarketOverviewTrend(date, 60, ctrl.signal),
    ])
      .then(([review, trend, marketTrend]) => {
        setData(review)
        setTrend(trend)
        setMarketTrend(marketTrend)
        setError(null)
      })
      .catch(e => {
        if (e.name !== 'AbortError') setError(e.message)
      })
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [date])

  return { data, trend, marketTrend, loading, error }
}

export function useDates() {
  const [dates, setDates] = useState<string[]>([])
  useEffect(() => {
    const ctrl = new AbortController()
    fetchDates(ctrl.signal).then(setDates).catch(e => {
      if (e.name !== 'AbortError') console.error(e)
    })
    return () => ctrl.abort()
  }, [])
  return dates
}

export function useInsights(date: string) {
  const [data, setData] = useState<MarketInsights | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!date) {
      setData(null)
      setLoading(false)
      setError(null)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    fetchInsights(date, ctrl.signal)
      .then(d => { setData(d); setError(null) })
      .catch(e => {
        if (e.name !== 'AbortError') setError(e.message)
      })
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [date])

  return { data, loading, error }
}

export function useHot(date: string) {
  const [data, setData] = useState<HotData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!date) {
      setData(null)
      setLoading(false)
      setError(null)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    fetchHot(date, ctrl.signal)
      .then(d => { setData(d); setError(null) })
      .catch(e => {
        if (e.name !== 'AbortError') setError(e.message)
      })
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [date])

  return { data, loading, error }
}

export function useHotDates() {
  const [dates, setDates] = useState<string[]>([])
  useEffect(() => {
    const ctrl = new AbortController()
    fetchHotDates(ctrl.signal).then(setDates).catch(e => {
      if (e.name !== 'AbortError') console.error(e)
    })
    return () => ctrl.abort()
  }, [])
  return dates
}

export function useLatestJob() {
  const [job, setJob] = useState<DataJob | null>(null)
  useEffect(() => {
    const ctrl = new AbortController()
    fetchLatestJob(ctrl.signal).then(setJob).catch(e => {
      if (e.name !== 'AbortError') console.error(e)
    })
    return () => ctrl.abort()
  }, [])
  return job
}

export function useQuantzzDaily(date: string) {
  const [data, setData] = useState<QuantzzDailyOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!date) {
      setData(null)
      setLoading(false)
      setError(null)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    fetchQuantzzDaily(date, 60, ctrl.signal)
      .then(d => { setData(d); setError(null) })
      .catch(e => {
        if (e.name !== 'AbortError') setError(e.message)
      })
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [date])

  return { data, loading, error }
}
