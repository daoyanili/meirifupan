export type TabKey = 'review-home' | 'premarket-guide' | 'quantzz-daily' | 'limit-up-review' | 'emotion-review' | 'profit-effect' | 'data-overview'

interface Props {
  active: TabKey
  onChange: (tab: TabKey) => void
}

const tabs: { key: TabKey; label: string }[] = [
  { key: 'review-home', label: '复盘首页' },
  { key: 'premarket-guide', label: '盘前指引' },
  { key: 'quantzz-daily', label: '量化全景' },
  { key: 'limit-up-review', label: '涨停复盘' },
  { key: 'emotion-review', label: '情绪复盘' },
  { key: 'profit-effect', label: '赚钱效应' },
  { key: 'data-overview', label: '数据总览' },
]

export function TabBar({ active, onChange }: Props) {
  return (
    <div className="tab-bar">
      {tabs.map(tab => (
        <button
          key={tab.key}
          className={`tab-btn ${active === tab.key ? 'active' : ''}`}
          onClick={() => onChange(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
