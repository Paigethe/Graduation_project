export type RiskLevel = 'low' | 'medium' | 'high' | string

export function riskLabel(level: RiskLevel): string {
  if (level === 'low') return '安全'
  if (level === 'medium') return '关注'
  if (level === 'high') return '高风险'
  return String(level || '未知')
}

export function riskTone(level: RiskLevel): 'success' | 'warning' | 'danger' | 'info' {
  if (level === 'low') return 'success'
  if (level === 'medium') return 'warning'
  if (level === 'high') return 'danger'
  return 'info'
}

export function riskPillClass(level: RiskLevel): string {
  if (level === 'low') return 'bg-emerald-50 text-emerald-700 border-emerald-100'
  if (level === 'medium') return 'bg-amber-50 text-amber-700 border-amber-100'
  if (level === 'high') return 'bg-rose-50 text-rose-700 border-rose-100'
  return 'bg-slate-50 text-slate-700 border-slate-100'
}

