import type { PremarketAnnouncement, PremarketGuide, PremarketNewsItem, PremarketUsMarket } from '../types'
import { CollapsibleSection } from './CollapsibleSection'

interface Props {
  data: PremarketGuide | null
  loading: boolean
  error: string | null
}

function fmtPct(value: number | null | undefined) {
  if (value == null) return '-'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

function fmtAmount(value: number | string | null | undefined) {
  if (value == null || value === '') return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value)
  return `${Math.round(num / 100000000)}亿`
}

function toneClass(value: number | null | undefined) {
  if (value == null || value === 0) return ''
  return value > 0 ? 'text-red' : 'text-green'
}

function plateName(item: PremarketGuide['focus_plates'][number]) {
  return item.plate_name || item.board_name || '-'
}

export function PremarketGuideView({ data, loading, error }: Props) {
  if (loading) return <div className="loading">加载盘前指引...</div>
  if (error) return <div className="error">还没有生成盘前指引，8:30 自动更新后会出现在这里。</div>
  if (!data) return <div className="error">暂无盘前指引</div>

  const market = data.market_snapshot || {}
  const topUs = data.us_markets.slice(0, 6)

  return (
    <div className="premarket-page">
      <section className="premarket-hero">
        <div>
          <div className="home-date">
            {data.guide_date} 盘前 · 基于 {data.review_date} 复盘
          </div>
          <h2>盘前指引</h2>
          <p>{data.headline}</p>
          <small>{data.market_tone}</small>
        </div>
        <div className="premarket-hero-metrics">
          <Metric label="昨日成交额" value={fmtAmount(market.amount)} />
          <Metric label="平均涨幅" value={fmtPct(Number(market.avg_change_pct ?? 0))} tone={toneClass(Number(market.avg_change_pct ?? 0))} />
          <Metric label="涨停" value={`${market.limit_up_count ?? '-'}只`} tone="text-red" />
          <Metric label="跌停" value={`${market.limit_down_count ?? '-'}只`} tone="text-green" />
        </div>
      </section>

      <section className="premarket-grid">
        <div className="premarket-panel premarket-panel-main">
          <PanelHead title="今天先看什么" sub={`${data.watch_points.length} 条`} />
          <div className="premarket-point-list">
            {data.watch_points.map((item, index) => (
              <div className="premarket-point" key={`${item.title}-${index}`}>
                <span>{index + 1}</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.reason}</p>
                  {item.trigger && <em>{item.trigger}</em>}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="premarket-panel">
          <PanelHead title="风险提醒" sub="开盘先确认" />
          <div className="premarket-risk-list">
            {data.risk_points.map((item, index) => (
              <div className="premarket-risk" key={`${item.title}-${index}`}>
                <strong>{item.title}</strong>
                <p>{item.reason}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="premarket-grid compact">
        <div className="premarket-panel">
          <PanelHead title="主线板块" sub="昨日强度" />
          <div className="premarket-list">
            {data.focus_plates.slice(0, 6).map(item => (
              <div className="premarket-row" key={`${item.plate_code || item.board_code}-${plateName(item)}`}>
                <strong>{plateName(item)}</strong>
                <span>{item.reason}</span>
                <em className={toneClass(item.change_pct)}>{fmtPct(item.change_pct)}</em>
              </div>
            ))}
          </div>
        </div>

        <div className="premarket-panel">
          <PanelHead title="隔夜美股" sub="映射方向" />
          <div className="premarket-us-list">
            {topUs.length === 0 ? (
              <div className="quantzz-empty">暂无美股数据</div>
            ) : topUs.map(item => <UsRow item={item} key={item.symbol} />)}
          </div>
        </div>
      </section>

      <section className="premarket-folds">
        <CollapsibleSection title="新闻催化" summary={`${data.catalyst_news.length} 条`}>
          <NewsList items={data.catalyst_news} />
        </CollapsibleSection>
        <CollapsibleSection title="公告跟踪" summary={`${data.announcements.length} 条`}>
          <AnnouncementList items={data.announcements} />
        </CollapsibleSection>
        <CollapsibleSection title="昨日人气和空间板" summary={`${data.hot_stocks.length} 只人气股`}>
          <div className="premarket-two-list">
            <div className="premarket-panel flush">
              <h4>人气前排</h4>
              {data.hot_stocks.slice(0, 8).map(stock => (
                <div className="premarket-row" key={stock.stock_code}>
                  <strong>{stock.stock_name || stock.stock_code}</strong>
                  <span>#{stock.rank_no} · {stock.stock_code}</span>
                  <em className={toneClass(stock.change_pct)}>{fmtPct(stock.change_pct)}</em>
                </div>
              ))}
            </div>
            <div className="premarket-panel flush">
              <h4>空间板</h4>
              {data.space_stocks.slice(0, 8).map(stock => (
                <div className="premarket-row" key={stock.stock_code}>
                  <strong>{stock.stock_name}</strong>
                  <span>{stock.stock_code}</span>
                  <em>{stock.up_limit_desc || `${stock.up_limit_keep_times}板`}</em>
                </div>
              ))}
            </div>
          </div>
        </CollapsibleSection>
      </section>
    </div>
  )
}

function PanelHead({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="premarket-panel-head">
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

function UsRow({ item }: { item: PremarketUsMarket }) {
  return (
    <div className="premarket-us-row">
      <div>
        <strong>{item.stock_name || item.symbol}</strong>
        <span>{item.symbol}{item.mapped_theme ? ` · ${item.mapped_theme}` : ''}</span>
      </div>
      <em className={toneClass(item.change_pct)}>{fmtPct(item.change_pct)}</em>
    </div>
  )
}

function NewsList({ items }: { items: PremarketNewsItem[] }) {
  if (items.length === 0) return <div className="quantzz-empty">暂无新闻数据</div>
  return (
    <div className="premarket-news-list">
      {items.slice(0, 12).map((item, index) => (
        <a className="premarket-news" href={item.url || undefined} target="_blank" rel="noreferrer" key={`${item.title}-${index}`}>
          <strong>{item.title}</strong>
          <span>{item.source}{item.published_at ? ` · ${item.published_at}` : ''}</span>
          {item.content && <p>{item.content}</p>}
        </a>
      ))}
    </div>
  )
}

function AnnouncementList({ items }: { items: PremarketAnnouncement[] }) {
  if (items.length === 0) return <div className="quantzz-empty">暂无公告数据</div>
  return (
    <div className="premarket-news-list">
      {items.slice(0, 12).map((item, index) => (
        <a className="premarket-news" href={item.url || undefined} target="_blank" rel="noreferrer" key={`${item.title}-${index}`}>
          <strong>{item.stock_name || item.stock_code || '公告'}</strong>
          <span>{item.notice_type || '公告'} · {item.title}</span>
        </a>
      ))}
    </div>
  )
}
