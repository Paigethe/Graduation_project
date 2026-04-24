export function fmtDateTime(iso?: string | null): string {
  if (!iso) return ''
  const s = String(iso)
  return s.slice(0, 19).replace('T', ' ')
}

export function clampText(text: string, maxLen: number): string {
  const s = String(text ?? '')
  if (s.length <= maxLen) return s
  return s.slice(0, maxLen - 1) + '…'
}

