/** Minimal SVG sparkline for KPI time series. */
export function Sparkline({
  values,
  width = 120,
  height = 28,
  stroke = '#34d399',
}: {
  values: number[]
  width?: number
  height?: number
  stroke?: string
}) {
  if (values.length < 2) {
    return <svg width={width} height={height} className="opacity-30" />
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width
      const y = height - ((v - min) / range) * (height - 4) - 2
      return `${x},${y}`
    })
    .join(' ')
  return (
    <svg width={width} height={height} className="block">
      <polyline fill="none" stroke={stroke} strokeWidth="1.5" points={pts} />
    </svg>
  )
}
