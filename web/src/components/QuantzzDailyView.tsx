import type { QuantzzDailyOverview, HotBoardRank, HotStockRank } from '../types'
import { CollapsibleSection } from './CollapsibleSection'

interface Props {
  data: QuantzzDailyOverview | null
  loading: boolean
  error: string | null
}

function fmtAmount(value: number | null | undefined) {
  if (value == null) return '-'
  return `${Math.round(value / 100000000)}亿`
}

function fmtPct(value: number | null | undefined, digits = 1) {
  if (value == null) return '-'
  return `${value > 0 ? '+' : ''}${value.toFixed(digits)}%`
}

function plainPct(value: number | null | undefined, digits = 1) {
  if (value == null) return '-'
  return `${value.toFixed(digits)}%`
}

function toneClass(value: number | null | undefined) {
  if (value == null || value === 0) return ''
  return value > 0 ? 'text-red' : 'text-green'
}

function sourceStatus(status: string) {
  if (status === 'skipped') return '本版不做'
  if (status === 'missing') return '待补'
  return status
}

function buildVerdict(data: QuantzzDailyOverview) {
  const { market, popularity, space_board, loss_feedback } = data
  const overlap = popularity.limit_up_overlap_rate
  const risk = loss_feedback.limit_down_count + loss_feedback.broken_limit_up_count
  if (risk >= market.limit_up_count) {
    return `亏钱反馈偏重，跌停和炸板合计 ${risk}，先看修复，不适合无脑扩仓。`
  }
  if ((overlap ?? 0) >= 30 && space_board.highest_board >= 4) {
    return `人气和涨停有重合，空间板 ${space_board.highest_board} 板，短线方向比较集中。`
  }
  if ((popularity.top20_count || 0) > 0 && (overlap ?? 0) < 15) {
    return `人气榜和涨停池重合不高，单看涨停会漏掉趋势核心。`
  }
  return `日线结构可读，先看空间板、人气前排和板块榜能否互相确认。`
}

export function QuantzzDailyView({ data, loading, error }: Props) {
  if (loading) return <div className="loading">加载量化全景...</div>
  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="error">暂无量化全景数据</div>

  const conceptTop = data.hot_boards.concept.slice(0, 5)
  const industryTop = data.hot_boards.industry.slice(0, 5)
  const promotionSummary = data.promotion.levels
    .filter(item => item.level >= 2)
    .slice(0, 3)
    .map(item => `${item.level}板晋级${item.advancement_rate}%`)
    .join(' · ')

  return (
    <div className="quantzz-page">
      <section className="quantzz-hero">
        <div>
          <div className="home-date">{data.date}</div>
          <h2>量化全景</h2>
          <p>{buildVerdict(data)}</p>
        </div>
        <div className="quantzz-hero-metrics">
          <Metric label="成交额" value={fmtAmount(data.market.amount)} />
          <Metric label="平均涨幅" value={fmtPct(data.market.avg_change_pct, 2)} tone={toneClass(data.market.avg_change_pct)} />
          <Metric label="空间板" value={`${data.space_board.highest_board || '-'}板`} tone="text-purple" />
          <Metric label="封板率" value={plainPct(data.market.seal_success_rate)} tone="text-yellow" />
        </div>
      </section>

      <section className="quantzz-main-grid">
        <div className="quantzz-panel">
          <PanelHead title="情绪周期" sub="日线口径" />
          <div className="quantzz-metric-grid">
            <Metric label="涨停" value={`${data.market.limit_up_count}只`} tone="text-red" />
            <Metric label="跌停" value={`${data.loss_feedback.limit_down_count}只`} tone="text-green" />
            <Metric label="炸板" value={`${data.loss_feedback.broken_limit_up_count}只`} tone="text-yellow" />
            <Metric label="红盘率" value={plainPct(data.market.up_rate)} />
          </div>
          <div className="quantzz-note">
            自然涨停 {data.market.natural_limit_up_count ?? '-'}，自然跌停 {data.market.natural_limit_down_count ?? '-'}。
          </div>
        </div>

        <div className="quantzz-panel">
          <PanelHead title="空间板" sub="高度和核心股" />
          {data.space_board.stocks.length === 0 ? (
            <div className="quantzz-empty">暂无空间板数据</div>
          ) : (
            <div className="quantzz-stock-list">
              {data.space_board.stocks.slice(0, 4).map(stock => (
                <div className="quantzz-stock-row" key={stock.stock_code}>
                  <div>
                    <strong>{stock.stock_name}</strong>
                    <span>{stock.stock_code}</span>
                  </div>
                  <em>{stock.up_limit_desc || `${stock.up_limit_keep_times}板`}</em>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="quantzz-panel quantzz-panel-wide">
          <PanelHead title="人气核心" sub={`前20 · 重合涨停 ${data.popularity.limit_up_overlap_count} 只`} />
          <div className="quantzz-metric-grid compact">
            <Metric label="人气数量" value={`${data.popularity.top20_count}只`} />
            <Metric label="涨停重合" value={plainPct(data.popularity.limit_up_overlap_rate)} tone="text-red" />
            <Metric label="上涨" value={`${data.popularity.up_count}只`} tone="text-red" />
            <Metric label="重挫" value={`${data.popularity.heavy_fall_count}只`} tone="text-green" />
          </div>
          <HotStocks stocks={data.popularity.top20.slice(0, 10)} />
        </div>
      </section>

      <section className="quantzz-folds">
        <CollapsibleSection title="热点板块" summary={`概念 ${conceptTop.length} · 行业 ${industryTop.length}`} defaultOpen>
          <div className="quantzz-board-grid">
            <BoardList title="概念板块" boards={conceptTop} />
            <BoardList title="行业板块" boards={industryTop} />
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="晋级反馈" summary={promotionSummary || '暂无连续晋级数据'}>
          {data.promotion.levels.length === 0 ? (
            <div className="quantzz-empty">暂无晋级数据</div>
          ) : (
            <div className="quantzz-table-wrap">
              <table className="table quantzz-table">
                <thead>
                  <tr>
                    <th>梯队</th>
                    <th>昨日数量</th>
                    <th>晋级</th>
                    <th>断板</th>
                    <th>晋级率</th>
                    <th>断板样本</th>
                  </tr>
                </thead>
                <tbody>
                  {data.promotion.levels.map(item => (
                    <tr key={item.level}>
                      <td>{item.level}板</td>
                      <td>{item.total}</td>
                      <td className="text-red">{item.advanced}</td>
                      <td className="text-green">{item.failed}</td>
                      <td>{plainPct(item.advancement_rate)}</td>
                      <td>{item.failed_names.join('、') || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CollapsibleSection>

        <CollapsibleSection title="亏钱反馈" summary={`跌停 ${data.loss_feedback.limit_down_count} · 炸板 ${data.loss_feedback.broken_limit_up_count}`}>
          <div className="quantzz-board-grid">
            <FeedbackList title="跌停反馈" rows={data.loss_feedback.limit_down} />
            <FeedbackList title="炸板反馈" rows={data.loss_feedback.broken_limit_up} />
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="后续数据源" summary={`${data.missing_sources.length} 项`}>
          <div className="quantzz-gap-list">
            {data.missing_sources.map(item => (
              <div className="quantzz-gap" key={item.key}>
                <strong>{item.title}</strong>
                <span>{sourceStatus(item.status)}</span>
                <p>{item.reason}</p>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      </section>
    </div>
  )
}

function PanelHead({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="quantzz-panel-head">
      <h3>{title}</h3>
      <span>{sub}</span>
    </div>
  )
}

function Metric({ label, value, tone = '' }: { label: string; value: string; tone?: string }) {
  return (
    <div className="quantzz-metric">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
    </div>
  )
}

function HotStocks({ stocks }: { stocks: HotStockRank[] }) {
  if (stocks.length === 0) return <div className="quantzz-empty">暂无人气榜数据</div>
  return (
    <div className="quantzz-rank-list">
      {stocks.map(stock => (
        <div className="quantzz-rank-row" key={stock.stock_code}>
          <span>#{stock.rank_no}</span>
          <strong>{stock.stock_name ?? '-'}</strong>
          <small>{stock.stock_code}</small>
          <em className={toneClass(stock.change_pct)}>{fmtPct(stock.change_pct, 2)}</em>
        </div>
      ))}
    </div>
  )
}

function BoardList({ title, boards }: { title: string; boards: HotBoardRank[] }) {
  return (
    <div className="quantzz-mini-panel">
      <h4>{title}</h4>
      {boards.length === 0 ? (
        <div className="quantzz-empty">暂无数据</div>
      ) : boards.map(board => (
        <div className="quantzz-board-row" key={`${title}-${board.board_code || board.rank_no}`}>
          <span>#{board.rank_no}</span>
          <strong>{board.board_name ?? '-'}</strong>
          <em className={toneClass(board.change_pct)}>{fmtPct(board.change_pct, 2)}</em>
          <small>{board.leading_stock ?? '-'}</small>
        </div>
      ))}
    </div>
  )
}

function FeedbackList({ title, rows }: { title: string; rows: Array<{ stock_code: string; stock_name: string; change_pct?: number | null }> }) {
  return (
    <div className="quantzz-mini-panel">
      <h4>{title}</h4>
      {rows.length === 0 ? (
        <div className="quantzz-empty">暂无数据</div>
      ) : rows.map(row => (
        <div className="quantzz-board-row" key={`${title}-${row.stock_code}`}>
          <span>{row.stock_code}</span>
          <strong>{row.stock_name}</strong>
          <em className={toneClass(row.change_pct)}>{fmtPct(row.change_pct, 2)}</em>
        </div>
      ))}
    </div>
  )
}
