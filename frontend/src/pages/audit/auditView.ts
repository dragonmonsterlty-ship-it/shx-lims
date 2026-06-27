function stringify(value: unknown, pretty: boolean): string {
  if (value == null) return '—'
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, pretty ? 2 : 0)
  } catch {
    return String(value)
  }
}

export function summarizeAuditJson(value: unknown, maxLength = 48): string {
  const text = stringify(value, false)
  return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text
}

export function formatAuditJson(value: unknown): string {
  return stringify(value, true)
}
