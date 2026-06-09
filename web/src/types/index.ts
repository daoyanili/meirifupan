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
  limit_down_count?: number
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

export interface MarketOverviewTrendItem {
  date: string
  amount: number | null
  amount_change_pct: number | null
  total_count: number
  up_count: number
  down_count: number
  flat_count: number
  up_rate: number | null
  down_rate?: number | null
  avg_change_pct?: number | null
  natural_limit_up_count?: number | null
  natural_limit_down_count?: number | null
  limit_up_count: number
  has_limit_up_events?: boolean
  limit_down_count: number
  broken_limit_up_count: number
  highest_board: number
}

export interface MarketBreadth {
  total_count: number
  up_count: number
  down_count: number
  flat_count: number
  limit_up_count: number
  limit_down_count: number
  amount: number
  up_rate: number
}

export interface LimitDownItem {
  stock_code: string
  stock_name: string
  latest_price: number | null
  change_pct: number | null
  limit_down_days: number | null
  open_count: number | null
  industry: string | null
}

export interface BrokenLimitUpItem {
  stock_code: string
  stock_name: string
  latest_price: number | null
  change_pct: number | null
  first_limit_up_time: string | null
  open_count: number | null
  limit_up_stat: string | null
  industry: string | null
}

export interface LhbItem {
  stock_code: string
  stock_name: string
  reason: string | null
  buy_amount: number | null
  sell_amount: number | null
  net_buy_amount: number | null
}

export interface MovementSummaryItem {
  alert_type: string
  count: number
}

export interface MarketHotItem {
  item_name: string
  score: number | null
  rank_no: number | null
  raw_payload: string | null
}

export interface MarketEnvironment {
  breadth: MarketBreadth
  limit_down_total: number
  broken_limit_up_total: number
  limit_down: LimitDownItem[]
  broken_limit_up: BrokenLimitUpItem[]
  lhb: LhbItem[]
  movement_summary: MovementSummaryItem[]
  market_hot: MarketHotItem[]
}

export interface SavedReviewPlate {
  plate_code?: string
  plate_name: string
  limit_up_count?: number
  score?: number | null
  stage?: string
  stocks?: string[]
}

export interface SavedReviewStock {
  stock_code: string
  stock_name: string
  up_limit_keep_times?: number | null
  up_limit_time?: string | null
  fengdan_money?: number | null
  primary_plate?: string | null
  reason?: string | null
}

export interface SavedReviewHotStockSummary {
  total?: number
  non_limit_up_count?: number
  rising_count?: number
  falling_count?: number
  limit_up_count?: number
  text?: string
}

export interface SavedReviewHotStock {
  rank_no?: number
  stock_code: string
  stock_name: string
  latest_price?: number | null
  change_pct?: number | null
  is_limit_up?: boolean
  signal?: string
  primary_plate?: string | null
}

export interface SavedReviewWatchStock {
  stock_code: string
  stock_name: string
  category: string
  reason: string
  change_pct?: number | null
  rank_no?: number | null
  primary_plate?: string | null
}

export interface SavedReviewPlateActivity {
  trade_date: string
  limit_up_count: number
  seal_amount?: number | null
}

export interface SavedReviewPlateCoreStock {
  stock_code: string
  stock_name: string
  active_days?: number
  is_today_limit_up?: boolean
  highest_board?: number
  hot_rank?: number | null
  hot_change_pct?: number | null
  total_seal_amount?: number | null
  reason?: string
  event_reason?: string | null
}

export interface SavedReviewPlateIndexSummary {
  source?: string
  board_type?: string
  window_days?: number
  start_trade_date?: string
  end_trade_date?: string
  start_close?: number | null
  end_close?: number | null
  today_change_pct?: number | null
  window_change_pct?: number | null
  amount?: number | null
  series?: Array<{
    trade_date: string
    close_price?: number | null
    change_pct?: number | null
    amount?: number | null
  }>
}

export interface SavedReviewPlateReview {
  plate_code: string
  plate_name: string
  data_scope: string
  window_days: number
  active_days: number
  today_limit_up_count: number
  trend: string
  review_text: string
  index_summary?: SavedReviewPlateIndexSummary | null
  activity: SavedReviewPlateActivity[]
  core_stocks: SavedReviewPlateCoreStock[]
}

export interface SavedReview {
  trade_date: string
  limit_up_stock_count: number
  limit_up_plate_count: number
  first_board_count: number
  multi_board_count: number
  highest_board: number
  strongest_plates: SavedReviewPlate[]
  plate_reviews?: SavedReviewPlateReview[]
  core_stocks: SavedReviewStock[]
  hot_stock_summary?: SavedReviewHotStockSummary
  hot_stocks?: SavedReviewHotStock[]
  watch_stocks?: SavedReviewWatchStock[]
  risk_flags: string[]
  opportunities: string[]
  next_plan: string[]
  summary: string
  markdown_path?: string | null
  updated_at?: string | null
}

export interface ReviewData {
  date: string
  indices: IndexData[]
  limit_up_stats: LimitUpStats
  market_environment: MarketEnvironment
  saved_review: SavedReview | null
  board_tiers: BoardTier[]
  hot_plates: HotPlate[]
  high_stocks: HighStock[]
  all_stocks: StockItem[]
  emotion: EmotionData
}

export interface DataJobStep {
  name: string
  status: string
  started_at?: string
  finished_at?: string
  message?: string
  result?: Record<string, unknown>
}

export interface DataJob {
  id: number
  job_name: string
  trade_date: string | null
  status: string
  message: string | null
  details: {
    steps?: DataJobStep[]
    status?: string
    message?: string
  }
  started_at: string | null
  finished_at: string | null
  created_at: string
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

// --- Hot Data ---

export interface HotStockRank {
  rank_no: number
  stock_code: string
  stock_name: string | null
  latest_price: number | null
  change_pct: number | null
  change_amount: number | null
  amount?: number | null
  turnover_rate?: number | null
  source?: string | null
}

export interface HotBoardRank {
  rank_no: number
  board_code: string
  board_name: string | null
  latest_price: number | null
  change_pct: number | null
  change_amount: number | null
  total_market_cap: number | null
  turnover_rate: number | null
  up_count: number | null
  down_count: number | null
  leading_stock: string | null
  leading_stock_change: number | null
}

export interface HotData {
  date: string
  hot_stocks: HotStockRank[]
  concept_boards: HotBoardRank[]
  industry_boards: HotBoardRank[]
}

export interface QuantzzMissingSource {
  key: string
  title: string
  status: 'missing' | 'skipped' | string
  reason: string
}

export interface QuantzzSpaceBoard {
  highest_board: number
  stocks: Array<{
    stock_code: string
    stock_name: string
    up_limit_keep_times: number
    up_limit_desc?: string | null
    up_limit_time?: string | null
    fengdan_money?: number | null
    fengdan_rate?: number | null
  }>
}

export interface QuantzzPromotionLevel {
  level: number
  total: number
  advanced: number
  maintained: number
  failed: number
  advancement_rate: number
  fail_rate: number
  failed_names: string[]
}

export interface QuantzzDailyOverview {
  date: string
  days: number
  market: {
    total_count: number
    up_count: number
    down_count: number
    flat_count: number
    up_rate: number | null
    down_rate: number | null
    avg_change_pct: number | null
    amount: number | null
    limit_up_count: number
    natural_limit_up_count: number | null
    natural_limit_down_count: number | null
    seal_success_rate: number | null
    broken_rate: number | null
  }
  emotion_heat: MarketOverviewTrendItem & Record<string, unknown>
  emotion_trend: Array<MarketOverviewTrendItem & Record<string, unknown>>
  space_board: QuantzzSpaceBoard
  popularity: {
    top20_count: number
    top20: HotStockRank[]
    avg_change_pct: number | null
    up_count: number
    down_count: number
    heavy_fall_count: number
    limit_up_overlap_count: number
    limit_up_overlap_rate: number | null
  }
  hot_boards: {
    concept: HotBoardRank[]
    industry: HotBoardRank[]
  }
  promotion: {
    levels: QuantzzPromotionLevel[]
  }
  loss_feedback: {
    limit_down_count: number
    broken_limit_up_count: number
    heavy_fall_hot_count: number
    limit_down: LimitDownItem[]
    broken_limit_up: BrokenLimitUpItem[]
  }
  missing_sources: QuantzzMissingSource[]
}
