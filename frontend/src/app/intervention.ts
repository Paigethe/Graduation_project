export type InterventionStatus = 'draft' | 'sent' | 'in_progress' | 'done' | string

export function interventionStatusLabel(status: InterventionStatus): string {
  if (status === 'draft') return '草稿'
  if (status === 'sent') return '已推送'
  if (status === 'in_progress') return '进行中'
  if (status === 'done') return '已完成'
  return String(status || '未知')
}

export function interventionStatusType(
  status: InterventionStatus,
): 'info' | 'warning' | 'success' | 'danger' {
  if (status === 'draft') return 'info'
  if (status === 'sent') return 'warning'
  if (status === 'in_progress') return 'warning'
  if (status === 'done') return 'success'
  return 'info'
}

export function interventionProgressPercent(status: InterventionStatus): number {
  if (status === 'draft') return 10
  if (status === 'sent') return 40
  if (status === 'in_progress') return 70
  if (status === 'done') return 100
  return 25
}

export function interventionSeenStorageKey(userId?: number | string | null): string {
  return `bs001_intervention_seen_at_${userId ?? 'anonymous'}`
}
