import type { ReviewData, EmotionTrendItem, MarketInsights } from '../types'

const BASE = '/api'

export async function fetchDates(): Promise<string[]> {
  const res = await fetch(`${BASE}/dates`)
  if (!res.ok) {
    throw new Error(`Failed to fetch dates: ${res.statusText}`)
  }
  const json = await res.json()
  return json.dates
}

export async function fetchReview(date: string): Promise<ReviewData> {
  const res = await fetch(`${BASE}/review?date=${date}`)
  if (!res.ok) {
    throw new Error(`Failed to fetch review: ${res.statusText}`)
  }
  return res.json()
}

export async function fetchEmotionTrend(date: string, days = 5): Promise<EmotionTrendItem[]> {
  const res = await fetch(`${BASE}/emotion/trend?date=${date}&days=${days}`)
  if (!res.ok) {
    throw new Error(`Failed to fetch emotion trend: ${res.statusText}`)
  }
  const json = await res.json()
  return json.trend
}

export async function fetchInsights(date: string): Promise<MarketInsights> {
  const res = await fetch(`${BASE}/insights?date=${date}`)
  if (!res.ok) {
    throw new Error(`Failed to fetch insights: ${res.statusText}`)
  }
  return res.json()
}
