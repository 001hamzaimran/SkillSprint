import * as React from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

interface Column {
  key: string
  label: string
  className?: string
}

interface DataTableProps {
  columns: Column[]
  data: Record<string, any>[]
  renderCell?: (row: Record<string, any>, column: Column) => React.ReactNode
  onRowClick?: (row: Record<string, any>) => void
  emptyMessage?: string
  className?: string
}

export function DataTable({
  columns,
  data,
  renderCell,
  onRowClick,
  emptyMessage = "No data available",
  className
}: DataTableProps) {
  return (
    <div className={cn("rounded-[11px] border border-[var(--border)] bg-[var(--white)] overflow-hidden", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((col) => (
              <TableHead key={col.key} className={col.className}>
                {col.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} className="text-center text-[var(--muted)] h-24">
                {emptyMessage}
              </TableCell>
            </TableRow>
          ) : (
            data.map((row, rowIndex) => (
              <TableRow 
                key={rowIndex} 
                onClick={() => onRowClick?.(row)}
                className={cn(onRowClick && "cursor-pointer")}
              >
                {columns.map((col) => (
                  <TableCell key={col.key} className={col.className}>
                    {renderCell ? renderCell(row, col) : row[col.key]}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
