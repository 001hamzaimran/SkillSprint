import * as React from "react"
import { Badge } from "@/components/ui/badge"

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const normalizedStatus = status.toLowerCase()
  
  let variant: "default" | "warning" | "success" | "destructive" = "default"
  
  if (['published', 'active', 'approved', 'completed'].includes(normalizedStatus)) {
    variant = "success"
  } else if (['rejected', 'failed'].includes(normalizedStatus)) {
    variant = "destructive"
  } else if (['stale sources', 'needs correction', 'pending', 'draft', 'queued', 'running'].includes(normalizedStatus)) {
    variant = "warning"
  }
  
  const displayStatus = status.charAt(0).toUpperCase() + status.slice(1)
  
  return (
    <Badge variant={variant} className={className}>
      {displayStatus}
    </Badge>
  )
}
