import type { StockItem } from '../types'

interface Props {
  plateName: string
  stocks?: StockItem[]
  onClose: () => void
}

export function PlateDrilldown({ plateName, stocks = [], onClose }: Props) {
  const filtered = stocks.filter(s =>
    s.plates.some(p => p.includes(plateName) || plateName.includes(p))
  )

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{ width: '85%', maxWidth: '900px', maxHeight: '80vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>板块详情: {plateName} ({filtered.length}只涨停)</span>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)',
              padding: '4px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
            }}
          >
            关闭
          </button>
        </div>
        <div className="card-body" style={{ padding: 0, overflowY: 'auto', flex: 1 }}>
          {filtered.length === 0 ? (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
              该板块暂无涨停股数据
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th>涨停时间</th>
                  <th>连板</th>
                  <th>类型</th>
                  <th>封单金额</th>
                  <th>成交额</th>
                  <th>原因</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(stock => (
                  <tr key={stock.stock_code}>
                    <td>{stock.stock_code}</td>
                    <td style={{ fontWeight: 600 }}>{stock.stock_name}</td>
                    <td>{stock.up_limit_time}</td>
                    <td className="text-red">{stock.up_limit_keep_times > 1 ? `${stock.up_limit_keep_times}板` : '首板'}</td>
                    <td>{stock.up_limit_type}</td>
                    <td>{(stock.fengdan_money / 10000).toFixed(0)}万</td>
                    <td>{(stock.amount / 10000).toFixed(0)}万</td>
                    <td style={{ color: 'var(--text-secondary)', maxWidth: '200px', whiteSpace: 'normal', fontSize: '12px' }}>
                      {stock.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
