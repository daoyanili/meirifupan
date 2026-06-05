import type { ReviewData, EmotionTrendItem } from '../types'
import { IndexCards } from './IndexCards'
import { LimitUpStats } from './LimitUpStats'
import { EmotionGauge } from './EmotionGauge'
import { EmotionTrend } from './EmotionTrend'
import { BoardTiers } from './BoardTiers'
import { HotPlates } from './HotPlates'
import { HighStocks } from './HighStocks'
import { StockTable } from './StockTable'

interface Props {
  data: ReviewData
  trend: EmotionTrendItem[]
}

export function Overview({ data, trend }: Props) {
  return (
    <>
      <div className="top-row">
        <IndexCards indices={data.indices} />
        <LimitUpStats stats={data.limit_up_stats} />
        <EmotionGauge emotion={data.emotion} />
      </div>
      <EmotionTrend trend={trend} />
      <div className="grid-2">
        <BoardTiers tiers={data.board_tiers} />
        <HotPlates plates={data.hot_plates} stocks={data.all_stocks} />
      </div>
      <HighStocks stocks={data.high_stocks} />
      <StockTable stocks={data.all_stocks} />
    </>
  )
}
