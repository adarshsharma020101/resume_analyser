interface Props { score: number; label?: string; size?: number }

export function ScoreGauge({ score, label = 'ATS Readiness Estimate', size = 140 }: Props) {
  const pct = Math.min(100, Math.max(0, score))
  const color = pct >= 70 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444'
  const r = (size / 2) * 0.8
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={10} />
        <circle
          cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={10}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeDashoffset={circ / 4}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
        <text x="50%" y="50%" textAnchor="middle" dy="0.3em" fontSize={size * 0.22} fontWeight="bold" fill={color}>
          {Math.round(pct)}
        </text>
        <text x="50%" y="50%" textAnchor="middle" dy="1.5em" fontSize={size * 0.09} fill="#6b7280">
          /100
        </text>
      </svg>
      <span className="text-sm font-medium text-gray-600 text-center max-w-[140px]">{label}</span>
    </div>
  )
}
