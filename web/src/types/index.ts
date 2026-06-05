export interface IndexData {
  index_code: string
  index_name: string
  close_price: number
  change_pct: number
}

export interface LimitUpStats {
  total: number
  first_board: number
  multi_board: number
  highest_board: number
  prev_total: number
}

export interface BoardTierStock {
  stock_code: string
  stock_name: string
  up_limit_time: string
  up_limit_type: string
  fengdan_money: number
  plates: string[]
}

export interface BoardTier {
  level: number
  count: number
  stock_names: string
  stocks: BoardTierStock[]
}

export interface HotPlate {
  plate_code: string
  plate_name: string
  score: number
  rank_no: number
  limit_up_count: number
  days_in_hot: number
  is_new: boolean
}

export interface HighStock {
  stock_code: string
  stock_name: string
  board_count: number
  up_limit_time: string
  up_limit_type: string
  fengdan_money: number
  plates: string[]
  reason: string
}

export interface StockItem {
  stock_code: string
  stock_name: string
  stock_price: number
  up_limit_time: string
  up_limit_desc: string
  up_limit_keep_times: number
  up_limit_type: string
  fengdan_money: number
  fengdan_rate: number
  reason: string
  amount: number
  primary_plate: string
  plates: string[]
}

export interface EmotionScoreDetail {
  value: number
  score: number
  weight: number
  label: string
}

export interface EmotionScores {
  limit_up_count: EmotionScoreDetail
  board_height: EmotionScoreDetail
  first_board_count: EmotionScoreDetail
  limit_ratio: EmotionScoreDetail
  market_change: EmotionScoreDetail
}

export interface EmotionData {
  date: string
  scores: EmotionScores
  total_score: number
  level: string
  advice: string
}

export interface EmotionTrendItem {
  date: string
  scores: EmotionScores
  total_score: number
  level: string
  advice: string
}

export interface ReviewData {
  date: string
  indices: IndexData[]
  limit_up_stats: LimitUpStats
  board_tiers: BoardTier[]
  hot_plates: HotPlate[]
  high_stocks: HighStock[]
  all_stocks: StockItem[]
  emotion: EmotionData
}

// --- Market Insights ---

export interface SealQuality {
  total: number
  one_seal: number
  normal_seal: number
  broken_seal: number
  broken_rate: number
  one_seal_rate: number
  first_board: number
  multi_board: number
  first_board_rate: number
  avg_seal_rate: number
  avg_seal_money: number
  prev_total: number
  prev_broken_rate: number
  prev_avg_seal_rate: number
}

export interface BoardAdvancement {
  level: number
  total: number
  advanced: number
  maintained: number
  failed: number
  advancement_rate: number
  fail_rate: number
  failed_names: string[]
}

export interface CapitalFlow {
  plate_code: string
  plate_name: string
  net_flow: number
  buy: number
  sell: number
  rate: number
  trade_money: number
  volume_ration: number
}

export interface HotStock {
  stock_code: string
  stock_name: string
  up_limit_keep_times: number
  up_limit_time: string
  up_limit_type: string
  fengdan_money: number
  fengdan_rate: number
  reason: string
  amount: number
  plates: string[]
  plate_count: number
}

export interface MarketInsights {
  date: string
  seal_quality: SealQuality
  board_advancement: BoardAdvancement[]
  capital_flow: CapitalFlow[]
  hot_stocks: HotStock[]
}
