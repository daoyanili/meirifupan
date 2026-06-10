import type { EmotionTrendItem, MarketOverviewTrendItem, ReviewData } from '../types'
import type { TabKey } from './TabBar'
import { EmotionCycleChart } from './EmotionCycleChart'
import { VolumeTrendChart } from './VolumeTrendChart'

interface Props {
  data: ReviewData
  emotionTrend: EmotionTrendItem[]
  marketTrend: MarketOverviewTrendItem[]
  onOpenTab: (tab: TabKey) => void
}

function fmtAmount(value: number | null | undefined) {
  if (value == null) return '-'
  return `${Math.round(value / 100000000)}亿`
}

function fmtSigned(value: number | null | undefined) {
  if (value == null) return '-'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

function fmtPct(value: number | null | undefined) {
  if (value == null) return '-'
  return `${value.toFixed(1)}%`
}

function trendWord(value: number | null | undefined) {
  if (value == null) return '缺少对比'
  if (value >= 8) return '明显放量'
  if (value >= 2) return '温和放量'
  if (value <= -8) return '明显缩量'
  if (value <= -2) return '温和缩量'
  return '量能持平'
}

function emotionTone(score: number) {
  if (score >= 2.3) return '偏热'
  if (score >= 1.5) return '中性'
  if (score >= 0.8) return '偏冷'
  return '冰点'
}

function buildConclusion(data: ReviewData, latestMarket?: MarketOverviewTrendItem, prevMarket?: MarketOverviewTrendItem) {
  const amountText = fmtAmount(latestMarket?.amount ?? data.market_environment.breadth.amount)
  const changeText = fmtSigned(latestMarket?.amount_change_pct)
  const upRate = latestMarket?.up_rate ?? data.market_environment.breadth.up_rate
  const limitDown = latestMarket?.limit_down_count || data.market_environment.limit_down_total
  const broken = latestMarket?.broken_limit_up_count ?? data.market_environment.broken_limit_up_total
  const limitUp = latestMarket?.has_limit_up_events === false ? data.limit_up_stats.total : latestMarket?.limit_up_count ?? data.limit_up_stats.total
  const prevLimitUp = prevMarket?.has_limit_up_events === false ? data.limit_up_stats.prev_total : prevMarket?.limit_up_count ?? data.limit_up_stats.prev_total
  const limitDiff = limitUp - (prevLimitUp || 0)
  const score = data.emotion.total_score
  const tone = emotionTone(score)

  if (limitDown >= limitUp || broken >= limitUp * 0.45) {
    return `量能 ${amountText}，${trendWord(latestMarket?.amount_change_pct)}，但亏钱反馈偏重。涨停 ${limitUp} 只、跌停 ${limitDown} 只、炸板 ${broken} 只，情绪 ${tone}，先看风险释放是否结束。`
  }
  if ((latestMarket?.amount_change_pct ?? 0) > 0 && limitDiff > 0 && score >= 1.5) {
    return `量能 ${amountText}，较前一日 ${changeText}，涨停增加 ${limitDiff} 只，情绪 ${tone}。这类组合更适合围绕主线找强分歧后的回流。`
  }
  if ((latestMarket?.amount_change_pct ?? 0) < -5 && score < 1.5) {
    return `量能 ${amountText}，较前一日 ${changeText}，情绪 ${tone}。缩量叠加弱情绪时，不适合扩大出手范围。`
  }
  return `量能 ${amountText}，${trendWord(latestMarket?.amount_change_pct)}，红盘率 ${fmtPct(upRate)}。情绪 ${tone}，先看涨停数量和连板高度能否继续修复。`
}

export function ReviewHome({ data, emotionTrend, marketTrend, onOpenTab }: Props) {
  const latestMarket = marketTrend.at(-1)
  const prevMarket = marketTrend.at(-2)
  const amountChange = latestMarket?.amount_change_pct
  const latestHasEvents = latestMarket?.has_limit_up_events !== false
  const limitDown = latestHasEvents ? latestMarket?.limit_down_count || data.market_environment.limit_down_total : data.market_environment.limit_down_total
  const broken = latestHasEvents ? latestMarket?.broken_limit_up_count ?? data.market_environment.broken_limit_up_total : data.market_environment.broken_limit_up_total
  const highBoard = latestHasEvents ? latestMarket?.highest_board ?? data.limit_up_stats.highest_board : data.limit_up_stats.highest_board
  const hotSummary = data.saved_review?.hot_stock_summary

  return (
    <div className="home-page">
      <section className="home-brief">
        <div>
          <div className="home-date">{data.date}</div>
          <h2>复盘首页</h2>
          <p>{buildConclusion(data, latestMarket, prevMarket)}</p>
        </div>
        <div className="home-score">
          <span>情绪指标</span>
          <strong>{data.emotion.total_score.toFixed(2)}</strong>
          <small>{data.emotion.level}</small>
        </div>
      </section>

      <section className="home-chart-grid">
        <div className="home-panel">
          <div className="home-panel-head">
            <div>
              <h3>量能趋势</h3>
              <span>每日成交额</span>
            </div>
            <strong>{fmtAmount(latestMarket?.amount)}</strong>
          </div>
          <VolumeTrendChart trend={marketTrend} />
          <div className="home-tips">
            <span>温馨提示</span>
            <p>红柱代表放量，绿柱代表缩量；黄线是近 5 日均量。复盘时先看量能是否支撑题材继续扩散。</p>
          </div>
        </div>

        <div className="home-panel">
          <div className="home-panel-head">
            <div>
              <h3>市场情绪</h3>
              <span>情绪分 + 涨停反馈</span>
            </div>
            <strong>{data.emotion.level}</strong>
          </div>
          <EmotionCycleChart emotionTrend={emotionTrend} marketTrend={marketTrend} />
          <div className="home-emotion-metrics">
            <Metric label="涨停家数" value={String(data.limit_up_stats.total)} tone="red" />
            <Metric label="跌停反馈" value={String(limitDown)} tone="green" />
            <Metric label="炸板反馈" value={String(broken)} tone="yellow" />
            <Metric label="连板高度" value={String(highBoard)} tone="purple" />
          </div>
        </div>
      </section>

      <section className="home-action-grid">
        <ActionCard
          title="盘前指引"
          value="8:30"
          text="结合昨日复盘、隔夜新闻公告和美股映射，早上先看方向。"
          onClick={() => onOpenTab('premarket-guide')}
        />
        <ActionCard
          title="量化全景"
          value={data.emotion.level}
          text="先看情绪、空间板、人气核心和亏钱反馈是否互相印证。"
          onClick={() => onOpenTab('quantzz-daily')}
        />
        <ActionCard
          title="涨停复盘"
          value={`${data.limit_up_stats.total}只`}
          text={`首板 ${data.limit_up_stats.first_board}，连板 ${data.limit_up_stats.multi_board}，最高 ${data.limit_up_stats.highest_board} 板。`}
          onClick={() => onOpenTab('limit-up-review')}
        />
        <ActionCard
          title="情绪复盘"
          value={hotSummary ? `${hotSummary.non_limit_up_count ?? 0}只` : data.emotion.level}
          text={hotSummary?.text ?? data.emotion.advice}
          onClick={() => onOpenTab('emotion-review')}
        />
        <ActionCard
          title="赚钱效应"
          value={amountChange == null ? '-' : fmtSigned(amountChange)}
          text={`成交额变化 ${fmtSigned(amountChange)}，红盘率 ${fmtPct(latestMarket?.up_rate ?? data.market_environment.breadth.up_rate)}。`}
          onClick={() => onOpenTab('profit-effect')}
        />
        <ActionCard
          title="数据总览"
          value={fmtAmount(latestMarket?.amount)}
          text="查看指数、跌停、炸板、龙虎榜和自动更新状态。"
          onClick={() => onOpenTab('data-overview')}
        />
      </section>
    </div>
  )
}

function Metric({ label, value, tone }: { label: string; value: string; tone: 'red' | 'green' | 'yellow' | 'purple' }) {
  return (
    <div className="home-emotion-metric">
      <span>{label}</span>
      <strong className={`text-${tone}`}>{value}</strong>
    </div>
  )
}

function ActionCard({ title, value, text, onClick }: { title: string; value: string; text: string; onClick: () => void }) {
  return (
    <button className="home-action-card" onClick={onClick}>
      <span>{title}</span>
      <strong>{value}</strong>
      <p>{text}</p>
    </button>
  )
}
