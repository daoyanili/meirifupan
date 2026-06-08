import type { SavedReview, SavedReviewHotStock, SavedReviewPlateReview, SavedReviewWatchStock } from '../types'

interface Props {
  review: SavedReview | null
}

function fmtMoney(value: number | null | undefined) {
  if (value == null) return '-'
  if (Math.abs(value) >= 100000000) return `${(value / 100000000).toFixed(1)}亿`
  if (Math.abs(value) >= 10000) return `${(value / 10000).toFixed(0)}万`
  return value.toFixed(0)
}

function fmtPct(value: number | null | undefined) {
  if (value == null) return '-'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

function changeClass(value: number | null | undefined) {
  if (value == null || value === 0) return 'report-change'
  return `report-change ${value > 0 ? 'text-red' : 'text-green'}`
}

function compactParts(parts: Array<string | number | null | undefined>) {
  return parts.filter(part => part !== null && part !== undefined && `${part}`.trim() !== '').join(' · ')
}

function hotSummaryTags(summary: SavedReview['hot_stock_summary']) {
  if (!summary) return []

  return [
    summary.total != null ? `全部 ${summary.total}` : null,
    summary.non_limit_up_count != null ? `非涨停 ${summary.non_limit_up_count}` : null,
    summary.limit_up_count != null ? `涨停 ${summary.limit_up_count}` : null,
    summary.rising_count != null ? `上涨 ${summary.rising_count}` : null,
    summary.falling_count != null ? `下跌 ${summary.falling_count}` : null,
  ].filter((item): item is string => item !== null)
}

export function ReviewReport({ review }: Props) {
  if (!review) {
    return (
      <div className="card">
        <div className="card-header">复盘报告</div>
        <div className="card-body">
          <div className="report-empty">这一天还没有生成复盘结论，先运行生成脚本。</div>
        </div>
      </div>
    )
  }

  const hotStocks = review.hot_stocks?.slice(0, 8) ?? []
  const watchStocks = review.watch_stocks?.slice(0, 8) ?? []
  const plateReviews = review.plate_reviews?.slice(0, 6) ?? []
  const summaryText = review.hot_stock_summary?.text?.trim()
  const summaryTags = hotSummaryTags(review.hot_stock_summary)
  const showFocusSections = Boolean(summaryText || summaryTags.length > 0 || hotStocks.length > 0 || watchStocks.length > 0)

  return (
    <div className="report-page">
      <div className="report-summary">
        <div>
          <div className="report-kicker">{review.trade_date}</div>
          <h2>复盘结论</h2>
          <p>{review.summary}</p>
        </div>
        <div className="report-scoreboard">
          <Metric label="涨停" value={`${review.limit_up_stock_count}`} />
          <Metric label="首板/连板" value={`${review.first_board_count}/${review.multi_board_count}`} />
          <Metric label="最高板" value={`${review.highest_board}板`} />
          <Metric label="板块数" value={`${review.limit_up_plate_count}`} />
        </div>
      </div>

      {showFocusSections && (
        <div className="report-grid report-focus-grid">
          <section className="card">
            <div className="card-header">人气核心</div>
            <div className="card-body report-list">
              {summaryText && <p className="report-focus-text">{summaryText}</p>}
              {summaryTags.length > 0 && (
                <div className="report-tags report-summary-tags">
                  {summaryTags.map(tag => <span key={tag} className="tag tag-blue">{tag}</span>)}
                </div>
              )}
              {hotStocks.length > 0 ? (
                hotStocks.map(stock => <HotStockRow key={stock.stock_code} stock={stock} />)
              ) : (
                <div className="report-empty report-empty-compact">暂无人气股数据</div>
              )}
            </div>
          </section>

          <section className="card">
            <div className="card-header">观察名单</div>
            <div className="card-body report-list">
              {watchStocks.length > 0 ? (
                watchStocks.map(stock => <WatchStockRow key={`${stock.stock_code}-${stock.category}`} stock={stock} />)
              ) : (
                <div className="report-empty report-empty-compact">暂无观察名单</div>
              )}
            </div>
          </section>
        </div>
      )}

      {plateReviews.length > 0 && (
        <section className="card">
          <div className="card-header">核心板块复盘</div>
          <div className="card-body report-plate-review-list">
            {plateReviews.map(plate => <PlateReviewCard key={plate.plate_code} plate={plate} />)}
          </div>
        </section>
      )}

      <div className="report-grid">
        <section className="card">
          <div className="card-header">{plateReviews.length > 0 ? '主线板块速览' : '主线板块'}</div>
          <div className="card-body report-list">
            {review.strongest_plates.map(plate => (
              <div key={plate.plate_code ?? plate.plate_name} className="report-plate">
                <div className="report-plate-head">
                  <strong>{plate.plate_name}</strong>
                  <span className="tag tag-red">{plate.stage ?? '观察'}</span>
                </div>
                <div className="report-muted">{plate.limit_up_count ?? 0}只涨停 · 强度 {plate.score ?? '-'}</div>
                {plate.stocks && plate.stocks.length > 0 && (
                  <div className="report-tags">
                    {plate.stocks.slice(0, 8).map(stock => <span key={stock} className="tag">{stock}</span>)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="card-header">涨停核心</div>
          <div className="card-body report-list">
            {review.core_stocks.slice(0, 10).map(stock => (
              <div key={stock.stock_code} className="report-stock-row">
                <div>
                  <strong>{stock.stock_name}</strong>
                  <small>{stock.stock_code} · {stock.primary_plate ?? '-'}</small>
                </div>
                <div className="report-stock-meta">
                  <span className="tag tag-yellow">{stock.up_limit_keep_times ?? 1}板</span>
                  <span>{fmtMoney(stock.fengdan_money)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="report-three">
        <TextList title="风险点" items={review.risk_flags} tone="green" />
        <TextList title="机会观察" items={review.opportunities} tone="red" />
        <TextList title="明日计划" items={review.next_plan} tone="blue" />
      </div>
    </div>
  )
}

function PlateReviewCard({ plate }: { plate: SavedReviewPlateReview }) {
  const trendClass = plate.trend === '升温' || plate.trend === '持续活跃' ? 'tag-red' : plate.trend === '降温' ? 'tag-green' : 'tag-blue'
  const index = plate.index_summary
  const peak = Math.max(0, ...(plate.activity?.map(item => item.limit_up_count ?? 0) ?? []))

  return (
    <div className="report-plate-review">
      <div className="report-plate-head">
        <strong>{plate.plate_name}</strong>
        <span className={`tag ${trendClass}`}>{plate.trend}</span>
      </div>
      <p className="report-focus-text">{plate.review_text}</p>
      <div className="report-tags">
        <span className="tag tag-blue">近{plate.window_days}日活跃 {plate.active_days}天</span>
        <span className="tag">今日 {plate.today_limit_up_count}只</span>
        <span className="tag">高点 {peak}只</span>
      </div>
      {index && (
        <div className="report-index-strip">
          <span>真实走势</span>
          <strong className={changeClass(index.today_change_pct)}>今日 {fmtPct(index.today_change_pct)}</strong>
          <strong className={changeClass(index.window_change_pct)}>近{index.window_days ?? plate.window_days}日 {fmtPct(index.window_change_pct)}</strong>
          <span>成交 {fmtMoney(index.amount)}</span>
          {index.source && <span className="report-source">{index.source}</span>}
        </div>
      )}
      {plate.core_stocks.length > 0 && (
        <div className="report-plate-core">
          {plate.core_stocks.slice(0, 4).map(stock => (
            <div key={stock.stock_code} className="report-stock-row report-focus-row">
              <div className="report-stock-main">
                <div className="report-stock-title">
                  <strong>{stock.stock_name}</strong>
                  {stock.hot_rank != null && <span className="report-rank">人气#{stock.hot_rank}</span>}
                </div>
                <small>{compactParts([stock.stock_code, stock.is_today_limit_up ? '今日涨停' : null, stock.active_days != null ? `活跃${stock.active_days}天` : null])}</small>
                {stock.reason && <div className="report-watch-reason">{stock.reason}</div>}
                {stock.event_reason && <div className="report-event-reason">{stock.event_reason}</div>}
              </div>
              <div className="report-stock-meta">
                <span className="tag tag-yellow">{stock.highest_board ?? 1}板</span>
                <span>{fmtMoney(stock.total_seal_amount)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function HotStockRow({ stock }: { stock: SavedReviewHotStock }) {
  const status = stock.is_limit_up ? '涨停' : '非涨停'
  const meta = compactParts([
    stock.stock_code,
    stock.primary_plate,
    stock.latest_price != null ? `价 ${stock.latest_price.toFixed(2)}` : null,
    stock.signal,
  ])

  return (
    <div className="report-stock-row report-focus-row">
      <div className="report-stock-main">
        <div className="report-stock-title">
          <strong>{stock.stock_name}</strong>
          <span className="report-rank">#{stock.rank_no ?? '-'}</span>
        </div>
        <small>{meta}</small>
      </div>
      <div className="report-stock-meta">
        <span className={`tag ${stock.is_limit_up ? 'tag-red' : 'tag-blue'}`}>{status}</span>
        <span className={changeClass(stock.change_pct)}>{fmtPct(stock.change_pct)}</span>
      </div>
    </div>
  )
}

function WatchStockRow({ stock }: { stock: SavedReviewWatchStock }) {
  const meta = compactParts([
    stock.stock_code,
    stock.primary_plate,
    stock.rank_no != null ? `人气#${stock.rank_no}` : null,
  ])

  return (
    <div className="report-stock-row report-focus-row">
      <div className="report-stock-main">
        <div className="report-stock-title">
          <strong>{stock.stock_name}</strong>
          <span className="report-rank">{stock.category}</span>
        </div>
        <small>{meta}</small>
        <div className="report-watch-reason">{stock.reason}</div>
      </div>
      <div className="report-stock-meta">
        <span className={changeClass(stock.change_pct)}>{fmtPct(stock.change_pct)}</span>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="report-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function TextList({ title, items, tone }: { title: string; items: string[]; tone: 'red' | 'green' | 'blue' }) {
  return (
    <section className="card">
      <div className="card-header">{title}</div>
      <div className="card-body">
        <ul className={`report-bullets report-bullets-${tone}`}>
          {items.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}
        </ul>
      </div>
    </section>
  )
}
