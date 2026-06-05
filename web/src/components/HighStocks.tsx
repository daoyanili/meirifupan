import type { HighStock } from '../types'

interface Props {
  stocks: HighStock[]
}

export function HighStocks({ stocks }: Props) {
  return (
    <div className="card" style={{ marginBottom: '16px' }}>
      <div className="card-header">高位股</div>
      <div className="card-body">
        <table className="table">
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>连板数</th>
              <th>封单金额</th>
              <th>所属板块</th>
              <th>上涨原因</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map(stock => (
              <tr key={stock.stock_code}>
                <td>{stock.stock_code}</td>
                <td style={{ fontWeight: 600 }}>{stock.stock_name}</td>
                <td className="text-red">{stock.board_count}板</td>
                <td>{(stock.fengdan_money / 10000).toFixed(0)}万</td>
                <td>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {stock.plates.map(p => (
                      <span key={p} className="tag tag-blue">{p}</span>
                    ))}
                  </div>
                </td>
                <td style={{ color: 'var(--text-secondary)', maxWidth: '200px', whiteSpace: 'normal' }}>
                  {stock.reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
