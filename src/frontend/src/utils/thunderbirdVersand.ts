/**
 * Thunderbird als Mailversand-Option (Issue #147). RechnungsFee übergibt Empfänger, Betreff,
 * Text und Anhang an ein Thunderbird-Compose-Fenster - den eigentlichen Versand (inkl. eigener
 * Signatur/Regeln/ggf. eingerichteter Verschlüsselung) übernimmt Thunderbird unverändert wie
 * bei jeder anderen Mail. Bisher nur für Rechnungen angeboten.
 */
import { tempDir, join } from '@tauri-apps/api/path'
import { invoke } from '@tauri-apps/api/core'
import { Command } from '@tauri-apps/plugin-shell'

export class ThunderbirdNichtGefundenError extends Error {
  constructor() {
    super('Thunderbird wurde nicht gefunden.')
    this.name = 'ThunderbirdNichtGefundenError'
  }
}

export type ThunderbirdAnhang = { url: string; dateiname: string }

export type ThunderbirdMailParams = {
  an: string
  cc?: string
  betreff: string
  text: string
  anhaenge: ThunderbirdAnhang[]
}

/** Escaped einen Feldwert für Thunderbirds eigene -compose-Mini-Syntax
 *  (to='...',subject='...',...) - Reihenfolge ist wichtig: erst Backslashes selbst escapen,
 *  danach die beiden Zeichen, die in dieser Syntax Feldgrenzen markieren (Komma trennt Felder,
 *  Apostroph umschließt den Wert). */
function escapeThunderbirdFeld(wert: string): string {
  return wert
    .replace(/\\/g, '\\\\')
    .replace(/,/g, '\\,')
    .replace(/'/g, "\\'")
}

/** Schreibt den Anhang direkt in tempDir() (kein Unterordner - write_bytes_to_path (Rust)
 *  legt keine Ordner an, und tempDir() existiert auf allen drei Betriebssystemen bereits).
 *  Präfix "rechnungsfee_" macht die Datei im geteilten Temp-Verzeichnis erkennbar. Bewusst
 *  ohne Aufräum-Logik: derselbe Dateiname wird beim nächsten Versand desselben Dokuments
 *  einfach überschrieben, es sammelt sich also nichts nennenswert an. */
async function schreibeTempDatei(url: string, dateiname: string): Promise<string> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Anhang konnte nicht geladen werden: ${res.status}`)
  const bytes = new Uint8Array(await res.arrayBuffer())

  const pfad = await join(await tempDir(), `rechnungsfee_${dateiname}`)
  await invoke('write_bytes_to_path', { path: pfad, data: Array.from(bytes) })
  return pfad
}

function baueComposeString(params: ThunderbirdMailParams, anhangPfade: string[]): string {
  const felder: string[] = []
  felder.push(`to='${escapeThunderbirdFeld(params.an)}'`)
  if (params.cc?.trim()) felder.push(`cc='${escapeThunderbirdFeld(params.cc)}'`)
  felder.push(`subject='${escapeThunderbirdFeld(params.betreff)}'`)
  felder.push(`body='${escapeThunderbirdFeld(params.text)}'`)
  if (anhangPfade.length > 0) {
    const anhangWert = anhangPfade.map(p => `file://${p}`).join(',')
    felder.push(`attachment='${escapeThunderbirdFeld(anhangWert)}'`)
  }
  return felder.join(',')
}

/** Kandidaten-Kommandos für die verschiedenen Installationsarten - werden der Reihe nach
 *  versucht, das erste erfolgreiche gewinnt. Kein Bedarf, das Betriebssystem vorher zu
 *  erkennen: ein nicht passender Kandidat schlägt einfach schnell fehl. */
function kandidaten(composeString: string): { programm: string; args: string[] }[] {
  return [
    { programm: 'thunderbird', args: ['-compose', composeString] },
    { programm: 'flatpak', args: ['run', 'org.mozilla.Thunderbird', '-compose', composeString] },
    { programm: 'open', args: ['-a', 'Thunderbird', '--args', '-compose', composeString] },
    { programm: 'C:\\Program Files\\Mozilla Thunderbird\\thunderbird.exe', args: ['-compose', composeString] },
    { programm: 'C:\\Program Files (x86)\\Mozilla Thunderbird\\thunderbird.exe', args: ['-compose', composeString] },
  ]
}

export async function sendeUeberThunderbird(params: ThunderbirdMailParams): Promise<void> {
  const anhangPfade = await Promise.all(
    params.anhaenge.map(a => schreibeTempDatei(a.url, a.dateiname))
  )
  const composeString = baueComposeString(params, anhangPfade)

  for (const { programm, args } of kandidaten(composeString)) {
    try {
      const ergebnis = await Command.create(programm, args).execute()
      // code === null bedeutet: Prozess wurde gestartet, aber (bei -compose gewollt) nicht
      // auf Beendigung gewartet/liefert keinen Code zurück - beides zählt als Erfolg. Ein
      // sofortiger Non-Zero-Code (z.B. "command not found") zählt als Fehlschlag.
      if (ergebnis.code === null || ergebnis.code === 0) return
    } catch {
      // nächsten Kandidaten versuchen
    }
  }
  throw new ThunderbirdNichtGefundenError()
}
