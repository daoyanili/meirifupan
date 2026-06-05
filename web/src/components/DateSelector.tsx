interface Props {
  dates: string[]
  value: string
  onChange: (date: string) => void
}

export function DateSelector({ dates, value, onChange }: Props) {
  return (
    <div className="date-selector" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <button
        className="btn"
        onClick={() => {
          const idx = dates.indexOf(value)
          if (idx < dates.length - 1) onChange(dates[idx + 1])
        }}
        disabled={dates.indexOf(value) >= dates.length - 1}
      >
        &larr;
      </button>
      <select
        className="select"
        value={value}
        onChange={e => onChange(e.target.value)}
      >
        {dates.map(d => (
          <option key={d} value={d}>{d}</option>
        ))}
      </select>
      <button
        className="btn"
        onClick={() => {
          const idx = dates.indexOf(value)
          if (idx > 0) onChange(dates[idx - 1])
        }}
        disabled={dates.indexOf(value) <= 0}
      >
        &rarr;
      </button>
      <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
        左右方向键切换
      </span>
    </div>
  )
}
