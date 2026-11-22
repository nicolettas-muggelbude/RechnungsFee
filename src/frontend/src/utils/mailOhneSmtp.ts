/**
 * Issue #582: Versand ohne SMTP für Dokumente, die bisher nur per SMTP (Kontokorrent-Auszug) oder
 * nur per mailto (Buchungsbeleg) gingen - wie bei Rechnungen: Thunderbird, falls in den
 * Einstellungen aktiviert, sonst Standard-Mailprogramm mit heruntergeladener PDF.
 */
import { getApiBase, ladeDateiHerunter, openUrl, isTauri, type KontokorrentMailData } from '../api/client'
import { sendeUeberThunderbird, type ThunderbirdAnhang } from './thunderbirdVersand'

export async function mailMitAnhaengen(params: {
  an: string
  cc?: string
  betreff: string
  text: string
  anhaenge: ThunderbirdAnhang[]
  thunderbird: boolean
}): Promise<void> {
  if (params.thunderbird) {
    await sendeUeberThunderbird(params)
    return
  }
  for (const a of params.anhaenge) await ladeDateiHerunter(a.url, a.dateiname)
  const teile = [
    `subject=${encodeURIComponent(params.betreff)}`,
    `body=${encodeURIComponent(params.text + (params.anhaenge.length ? '\n\n(Bitte die heruntergeladenen Dateien als Anhang einfügen.)' : ''))}`,
  ]
  if (params.cc?.trim()) teile.unshift(`cc=${encodeURIComponent(params.cc.trim())}`)
  const mailto = `mailto:${params.an}?${teile.join('&')}`
  if (isTauri()) await openUrl(mailto)
  else window.location.href = mailto
}

export async function kontokorrentMailOhneSmtp(
  art: 'kunden' | 'lieferanten', id: number, data: KontokorrentMailData, thunderbird: boolean,
): Promise<void> {
  const base = await getApiBase()
  await mailMitAnhaengen({
    an: data.an, cc: data.cc, betreff: data.betreff, text: data.text, thunderbird,
    anhaenge: [{
      url: `${base}/${art}/${id}/kontokorrent/pdf?von=${data.von}&bis=${data.bis}`,
      dateiname: `Kontokorrent_${data.von}_${data.bis}.pdf`,
    }],
  })
}
