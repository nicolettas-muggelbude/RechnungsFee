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

/** Kandidaten - werden der Reihe nach versucht, der erste erfolgreiche Start gewinnt. Kein
 *  Bedarf, das Betriebssystem vorher zu erkennen: ein nicht passender Kandidat schlägt
 *  einfach schnell fehl.
 *
 *  WICHTIG: "programm" ist NICHT der auszuführende Befehl selbst, sondern der Name eines in
 *  src-tauri/capabilities/default.json fest hinterlegten Scope-Eintrags (shell:allow-execute).
 *  Tauri v2 lässt Command.create() grundsätzlich nur exakt vorab benannte Kommandos zu, auch
 *  wenn die Berechtigung selbst "ohne Scope" heißt - ein beliebiger Programmname/Pfad aus JS
 *  wird sonst mit "Programm nicht erlaubt" abgelehnt, bevor überhaupt ein Prozess gestartet
 *  wird. Der tatsächliche Pfad (inkl. der Windows-Variable $LOCALDATA für die Installation
 *  ohne Admin-Rechte) steht ausschließlich in der Capabilities-Datei. */
function kandidaten(composeString: string): { programm: string; args: string[] }[] {
  return [
    { programm: 'thunderbird', args: ['-compose', composeString] },
    { programm: 'thunderbird-flatpak', args: ['run', 'org.mozilla.Thunderbird', '-compose', composeString] },
    { programm: 'thunderbird-macos', args: ['-a', 'Thunderbird', '--args', '-compose', composeString] },
    { programm: 'thunderbird-win-64', args: ['-compose', composeString] },
    { programm: 'thunderbird-win-32', args: ['-compose', composeString] },
    { programm: 'thunderbird-win-appdata', args: ['-compose', composeString] },
  ]
}

export async function sendeUeberThunderbird(params: ThunderbirdMailParams): Promise<void> {
  const anhangPfade = await Promise.all(
    params.anhaenge.map(a => schreibeTempDatei(a.url, a.dateiname))
  )
  const composeString = baueComposeString(params, anhangPfade)

  for (const { programm, args } of kandidaten(composeString)) {
    try {
      // spawn() statt execute(): Thunderbird ist ein langlebiger GUI-Prozess, der (falls noch
      // keine Instanz laeuft) erst beim eigenen Beenden zurueckkehrt - execute() haette bis
      // dahin blockiert. Kein Rueckgabewert zu pruefen: schlaegt spawn() nicht fehl (Datei
      // gefunden, ausfuehrbar), gilt der Kandidat als Erfolg.
      await Command.create(programm, args).spawn()
      return
    } catch (e) {
      console.warn(`[Thunderbird] Kandidat "${programm}" fehlgeschlagen:`, e)
    }
  }
  throw new ThunderbirdNichtGefundenError()
}
