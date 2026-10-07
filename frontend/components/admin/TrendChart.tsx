"use client"

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import type { TooltipContentProps } from "recharts"

import { formatDay } from "@/lib/format/numbers"

export interface TrendSeries {
  key: string // the field of a data row that holds the value
  label: string
  color: string // a CSS colour, normally a var(--series-n) token
}

interface TrendChartProps<Row extends { date: string }> {
  rows: Row[]
  series: TrendSeries[]
  formatValue: (value: number) => string // for the tooltip and the axis
  integersOnly?: boolean // counts: no ticks like 2.5
  ariaLabel: string
}

type Point = Record<string, number | string | null>

// the line key shown in the legend and the tooltip: a short stroke, like the line itself
function LineKey({ color }: { color: string }) {
  return <span aria-hidden="true" className="inline-block h-[2px] w-4 rounded-full" style={{ background: color }} />
}

function Legend({ series }: { series: TrendSeries[] }) {
  return (
    <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
      {series.map((item) => (
        <li key={item.key} className="flex items-center gap-2">
          <LineKey color={item.color} />
          {item.label}
        </li>
      ))}
    </ul>
  )
}

// One tooltip for every series at the hovered day. The value leads, the name follows.
function makeTooltip(series: TrendSeries[], formatValue: (value: number) => string) {
  return function ChartTooltip({ active, payload, label }: TooltipContentProps) {
    if (!active || !payload || payload.length === 0) return null

    return (
      <div className="rounded-control border border-line bg-surface px-3 py-2 text-sm shadow-card">
        <p className="mb-1 text-muted">{formatDay(String(label))}</p>
        <ul className="space-y-1">
          {series.map((item) => {
            const entry = payload.find((p) => p.dataKey === item.key)
            const value = typeof entry?.value === "number" ? formatValue(entry.value) : "–"
            return (
              <li key={item.key} className="flex items-center gap-2">
                <LineKey color={item.color} />
                <span className="font-semibold">{value}</span>
                <span className="text-muted">{item.label}</span>
              </li>
            )
          })}
        </ul>
      </div>
    )
  }
}

// A point is drawn as a dot only where a line would not show it: the last value (the "now" of the chart)
// and a value with an empty day on both sides. Everything else is the line itself.
function shouldDraw(values: (number | null)[], index: number): boolean {
  if (values[index] === null) return false
  const last = values.map((v) => v !== null).lastIndexOf(true)
  const isolated = (index === 0 || values[index - 1] === null) && (index === values.length - 1 || values[index + 1] === null)
  return index === last || isolated
}

export function TrendChart<Row extends { date: string }>({
  rows,
  series,
  formatValue,
  integersOnly = false,
  ariaLabel,
}: TrendChartProps<Row>) {
  const data = rows as unknown as Point[]
  const Content = makeTooltip(series, formatValue)

  return (
    // a group, not an image: the tooltip inside stays reachable; the table under the chart is the text version
    <div role="group" aria-label={ariaLabel}>
      {series.length > 1 && <Legend series={series} />}
      <ResponsiveContainer width="100%" height={240} initialDimension={{ width: 600, height: 240 }}>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDay}
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            tickLine={false}
            tickMargin={8}
            axisLine={{ stroke: "var(--border)" }}
            minTickGap={24}
          />
          <YAxis
            width={48}
            domain={[0, "auto"]}
            allowDecimals={!integersOnly}
            tickFormatter={formatValue}
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={Content} cursor={{ stroke: "var(--border)", strokeWidth: 1 }} />
          {series.map((item) => {
            const values = data.map((row) => (typeof row[item.key] === "number" ? (row[item.key] as number) : null))
            return (
              <Line
                key={item.key}
                dataKey={item.key}
                type="linear" // straight segments: a smooth curve would suggest values between the days that were never measured
                stroke={item.color}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                connectNulls={false}
                isAnimationActive={false}
                dot={({ cx, cy, index, key }) =>
                  shouldDraw(values, index) ? (
                    // 8px dot with a 2px ring in the surface colour, so it stays clear where it meets a line
                    <circle key={key} cx={cx} cy={cy} r={4} fill={item.color} stroke="var(--surface)" strokeWidth={2} />
                  ) : (
                    <g key={key} />
                  )
                }
                activeDot={{ r: 4, fill: item.color, stroke: "var(--surface)", strokeWidth: 2 }}
              />
            )
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
