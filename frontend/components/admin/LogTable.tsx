import { QueryStatusBadge } from "@/components/admin/QueryStatusBadge"
import { formatLatency } from "@/lib/format/numbers"
import { formatTime } from "@/lib/format/time"
import type { QueryLogItem } from "@/lib/types/logs"

interface LogTableProps {
  items: QueryLogItem[]
  onOpen: (item: QueryLogItem) => void
}

const HEADER_CELL =
  "border-b border-line px-4 py-3 text-left text-xs font-semibold tracking-wider whitespace-nowrap text-muted uppercase"

// On a narrow screen each row becomes a small card (every table part turns into a block).
const CELL = "border-b border-line px-4 py-2.5 align-middle max-sm:block max-sm:border-none max-sm:px-0 max-sm:py-[0.15rem]"

export function LogTable({ items, onOpen }: LogTableProps) {
  return (
    <div className="overflow-x-auto rounded-card border border-line bg-surface shadow-card">
      <table className="w-full border-collapse text-[0.925rem] max-sm:block">
        <caption className="sr-only">Questions asked by all users</caption>
        <thead className="max-sm:sr-only">
          <tr>
            <th scope="col" className={HEADER_CELL}>
              Time
            </th>
            <th scope="col" className={HEADER_CELL}>
              Asked by
            </th>
            <th scope="col" className={HEADER_CELL}>
              Question
            </th>
            <th scope="col" className={HEADER_CELL}>
              Status
            </th>
            <th scope="col" className={`${HEADER_CELL} text-right`}>
              Response time
            </th>
          </tr>
        </thead>
        <tbody className="max-sm:block">
          {items.map((item) => (
            <tr key={item.id} className="last:*:border-b-0 max-sm:block max-sm:border-b max-sm:border-line max-sm:px-4 max-sm:py-3 max-sm:last:border-b-0">
              <td className={`${CELL} whitespace-nowrap text-muted`}>{formatTime(item.created_at)}</td>
              <td className={`${CELL} text-muted max-sm:hidden`}>{item.user_email}</td>
              <td className={`${CELL} max-w-[26rem]`}>
                <button
                  type="button"
                  onClick={() => onOpen(item)}
                  className="block w-full cursor-pointer truncate text-left text-accent hover:underline"
                  title={item.question}
                >
                  {item.question}
                </button>
              </td>
              <td className={CELL}>
                <QueryStatusBadge status={item.status} />
              </td>
              <td className={`${CELL} text-right whitespace-nowrap tabular-nums max-sm:text-left max-sm:text-muted`}>
                {formatLatency(item.latency_ms)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
