/**
 * O backend retorna datas UTC sem sufixo "Z" (ex: "2026-02-21T00:24:03").
 * Adiciona o "Z" para forçar interpretação UTC correta antes de converter.
 */
function parseUTC(iso) {
  if (!iso) return null
  const s = String(iso)
  return new Date(s.endsWith('Z') || s.includes('+') ? s : s + 'Z')
}

export function fmtTime(iso) {
  const d = parseUTC(iso)
  if (!d) return '—'
  return d.toLocaleTimeString('pt-BR')
}

export function fmtDateTime(iso) {
  const d = parseUTC(iso)
  if (!d) return '—'
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}
