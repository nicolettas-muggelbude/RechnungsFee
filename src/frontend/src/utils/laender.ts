/**
 * Länder für die Land-Dropdowns (Kunden, Lieferanten, eigenes Unternehmen).
 *
 * LAENDER_QUELLE enthält die vollständige Länderliste des Auswärtigen Amts
 * ("Verzeichnis der Staatennamen für den amtlichen Gebrauch in der Bundesrepublik
 * Deutschland", Kurzform + 2-stelliger ISO-Code, Stand der AA-Quelle: 29.07.2026,
 * abgerufen 2026-10-03 von https://www.auswaertiges-amt.de/de/service/terminologie/215252-215252).
 * Issue #401: einmalig vollständig statt bisher auf Zuruf erweitert. Einige amtliche
 * Kurzformen wurden zugunsten des im allgemeinen Sprachgebrauch üblichen deutschen Namens
 * angepasst (z.B. "USA" statt "Vereinigte Staaten", "Nordkorea"/"Südkorea" statt
 * "Korea, Demokratische Volksrepublik"/"Korea, Republik") - das betrifft nur die Anzeige,
 * nicht den ISO-Code.
 *
 * Die steuerliche Sonderbehandlung (nicht steuerbare Leistung nach §3a Abs. 2 UStG,
 * Ausfuhrlieferung nach §4 Nr. 1a UStG) hängt allein daran, dass der Code nicht in
 * EU_LAENDER_CODES steht - ein neues Land in LAENDER_QUELLE braucht dafür nichts weiter.
 *
 * Reihenfolge im Dropdown: Deutschland, Österreich, Schweiz zuerst (deckt den Großteil
 * der Fälle ab), darunter alle übrigen Länder alphabetisch nach deutschem Namen. Sortiert
 * wird zur Laufzeit - ein neuer Eintrag in LAENDER_QUELLE landet dadurch automatisch an
 * der richtigen Stelle, egal wo er eingefügt wurde.
 */

export type Land = { code: string; name: string }

/** ISO-Codes der 27 EU-Mitgliedstaaten (Stand 2026). Alles was hier nicht steht, gilt als
 * Drittland - diese Liste muss deshalb nur bei einem EU-Beitritt/-Austritt angefasst
 * werden, nicht bei jedem neuen Land im Dropdown. */
export const EU_LAENDER_CODES = new Set([
  'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GR', 'HR', 'HU',
  'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK',
])

/** Codes, die im Dropdown in dieser Reihenfolge ganz oben stehen (Issue #350: die
 * Länderliste wächst auf Zuruf, der DACH-Raum soll trotzdem sofort greifbar bleiben). */
const BEVORZUGTE_CODES = ['DE', 'AT', 'CH']

const LAENDER_QUELLE: Land[] = [
  { code: 'AD', name: 'Andorra' },
  { code: 'AE', name: 'Vereinigte Arabische Emirate' },
  { code: 'AF', name: 'Afghanistan' },
  { code: 'AG', name: 'Antigua und Barbuda' },
  { code: 'AL', name: 'Albanien' },
  { code: 'AM', name: 'Armenien' },
  { code: 'AO', name: 'Angola' },
  { code: 'AR', name: 'Argentinien' },
  { code: 'AT', name: 'Österreich' },
  { code: 'AU', name: 'Australien' },
  { code: 'AZ', name: 'Aserbaidschan' },
  { code: 'BA', name: 'Bosnien und Herzegowina' },
  { code: 'BB', name: 'Barbados' },
  { code: 'BD', name: 'Bangladesch' },
  { code: 'BE', name: 'Belgien' },
  { code: 'BF', name: 'Burkina Faso' },
  { code: 'BG', name: 'Bulgarien' },
  { code: 'BH', name: 'Bahrain' },
  { code: 'BI', name: 'Burundi' },
  { code: 'BJ', name: 'Benin' },
  { code: 'BN', name: 'Brunei Darussalam' },
  { code: 'BO', name: 'Bolivien' },
  { code: 'BR', name: 'Brasilien' },
  { code: 'BS', name: 'Bahamas' },
  { code: 'BT', name: 'Bhutan' },
  { code: 'BW', name: 'Botsuana' },
  { code: 'BY', name: 'Belarus' },
  { code: 'BZ', name: 'Belize' },
  { code: 'CA', name: 'Kanada' },
  { code: 'CD', name: 'Demokratische Republik Kongo' },
  { code: 'CF', name: 'Zentralafrikanische Republik' },
  { code: 'CG', name: 'Kongo' },
  { code: 'CH', name: 'Schweiz' },
  { code: 'CI', name: 'Côte d\'Ivoire' },
  { code: 'CK', name: 'Cookinseln' },
  { code: 'CL', name: 'Chile' },
  { code: 'CM', name: 'Kamerun' },
  { code: 'CN', name: 'China' },
  { code: 'CO', name: 'Kolumbien' },
  { code: 'CR', name: 'Costa Rica' },
  { code: 'CU', name: 'Kuba' },
  { code: 'CV', name: 'Cabo Verde' },
  { code: 'CY', name: 'Zypern' },
  { code: 'CZ', name: 'Tschechien' },
  { code: 'DE', name: 'Deutschland' },
  { code: 'DJ', name: 'Dschibuti' },
  { code: 'DK', name: 'Dänemark' },
  { code: 'DM', name: 'Dominica' },
  { code: 'DO', name: 'Dominikanische Republik' },
  { code: 'DZ', name: 'Algerien' },
  { code: 'EC', name: 'Ecuador' },
  { code: 'EE', name: 'Estland' },
  { code: 'EG', name: 'Ägypten' },
  { code: 'ER', name: 'Eritrea' },
  { code: 'ES', name: 'Spanien' },
  { code: 'ET', name: 'Äthiopien' },
  { code: 'FI', name: 'Finnland' },
  { code: 'FJ', name: 'Fidschi' },
  { code: 'FM', name: 'Mikronesien' },
  { code: 'FR', name: 'Frankreich' },
  { code: 'GA', name: 'Gabun' },
  { code: 'GB', name: 'Vereinigtes Königreich' },
  { code: 'GD', name: 'Grenada' },
  { code: 'GE', name: 'Georgien' },
  { code: 'GH', name: 'Ghana' },
  { code: 'GM', name: 'Gambia' },
  { code: 'GN', name: 'Guinea' },
  { code: 'GQ', name: 'Äquatorialguinea' },
  { code: 'GR', name: 'Griechenland' },
  { code: 'GT', name: 'Guatemala' },
  { code: 'GW', name: 'Guinea-Bissau' },
  { code: 'GY', name: 'Guyana' },
  { code: 'HN', name: 'Honduras' },
  { code: 'HR', name: 'Kroatien' },
  { code: 'HT', name: 'Haiti' },
  { code: 'HU', name: 'Ungarn' },
  { code: 'ID', name: 'Indonesien' },
  { code: 'IE', name: 'Irland' },
  { code: 'IL', name: 'Israel' },
  { code: 'IN', name: 'Indien' },
  { code: 'IQ', name: 'Irak' },
  { code: 'IR', name: 'Iran' },
  { code: 'IS', name: 'Island' },
  { code: 'IT', name: 'Italien' },
  { code: 'JM', name: 'Jamaika' },
  { code: 'JO', name: 'Jordanien' },
  { code: 'JP', name: 'Japan' },
  { code: 'KE', name: 'Kenia' },
  { code: 'KG', name: 'Kirgisistan' },
  { code: 'KH', name: 'Kambodscha' },
  { code: 'KI', name: 'Kiribati' },
  { code: 'KM', name: 'Komoren' },
  { code: 'KN', name: 'St. Kitts und Nevis' },
  { code: 'KP', name: 'Nordkorea' },
  { code: 'KR', name: 'Südkorea' },
  { code: 'KW', name: 'Kuwait' },
  { code: 'KZ', name: 'Kasachstan' },
  { code: 'LA', name: 'Laos' },
  { code: 'LB', name: 'Libanon' },
  { code: 'LC', name: 'St. Lucia' },
  { code: 'LI', name: 'Liechtenstein' },
  { code: 'LK', name: 'Sri Lanka' },
  { code: 'LR', name: 'Liberia' },
  { code: 'LS', name: 'Lesotho' },
  { code: 'LT', name: 'Litauen' },
  { code: 'LU', name: 'Luxemburg' },
  { code: 'LV', name: 'Lettland' },
  { code: 'LY', name: 'Libyen' },
  { code: 'MA', name: 'Marokko' },
  { code: 'MC', name: 'Monaco' },
  { code: 'MD', name: 'Moldau' },
  { code: 'ME', name: 'Montenegro' },
  { code: 'MG', name: 'Madagaskar' },
  { code: 'MH', name: 'Marshallinseln' },
  { code: 'MK', name: 'Nordmazedonien' },
  { code: 'ML', name: 'Mali' },
  { code: 'MM', name: 'Myanmar' },
  { code: 'MN', name: 'Mongolei' },
  { code: 'MR', name: 'Mauretanien' },
  { code: 'MT', name: 'Malta' },
  { code: 'MU', name: 'Mauritius' },
  { code: 'MV', name: 'Malediven' },
  { code: 'MW', name: 'Malawi' },
  { code: 'MX', name: 'Mexiko' },
  { code: 'MY', name: 'Malaysia' },
  { code: 'MZ', name: 'Mosambik' },
  { code: 'NA', name: 'Namibia' },
  { code: 'NE', name: 'Niger' },
  { code: 'NG', name: 'Nigeria' },
  { code: 'NI', name: 'Nicaragua' },
  { code: 'NL', name: 'Niederlande' },
  { code: 'NO', name: 'Norwegen' },
  { code: 'NP', name: 'Nepal' },
  { code: 'NR', name: 'Naoero' },
  { code: 'NU', name: 'Niue' },
  { code: 'NZ', name: 'Neuseeland' },
  { code: 'OM', name: 'Oman' },
  { code: 'PA', name: 'Panama' },
  { code: 'PE', name: 'Peru' },
  { code: 'PG', name: 'Papua-Neuguinea' },
  { code: 'PH', name: 'Philippinen' },
  { code: 'PK', name: 'Pakistan' },
  { code: 'PL', name: 'Polen' },
  { code: 'PT', name: 'Portugal' },
  { code: 'PW', name: 'Palau' },
  { code: 'PY', name: 'Paraguay' },
  { code: 'QA', name: 'Katar' },
  { code: 'RO', name: 'Rumänien' },
  { code: 'RS', name: 'Serbien' },
  { code: 'RU', name: 'Russische Föderation' },
  { code: 'RW', name: 'Ruanda' },
  { code: 'SA', name: 'Saudi-Arabien' },
  { code: 'SB', name: 'Salomonen' },
  { code: 'SC', name: 'Seychellen' },
  { code: 'SD', name: 'Sudan' },
  { code: 'SE', name: 'Schweden' },
  { code: 'SG', name: 'Singapur' },
  { code: 'SI', name: 'Slowenien' },
  { code: 'SK', name: 'Slowakei' },
  { code: 'SL', name: 'Sierra Leone' },
  { code: 'SM', name: 'San Marino' },
  { code: 'SN', name: 'Senegal' },
  { code: 'SO', name: 'Somalia' },
  { code: 'SR', name: 'Suriname' },
  { code: 'SS', name: 'Südsudan' },
  { code: 'ST', name: 'São Tomé und Príncipe' },
  { code: 'SV', name: 'El Salvador' },
  { code: 'SY', name: 'Syrien' },
  { code: 'SZ', name: 'Eswatini' },
  { code: 'TD', name: 'Tschad' },
  { code: 'TG', name: 'Togo' },
  { code: 'TH', name: 'Thailand' },
  { code: 'TJ', name: 'Tadschikistan' },
  { code: 'TL', name: 'Timor-Leste' },
  { code: 'TM', name: 'Turkmenistan' },
  { code: 'TN', name: 'Tunesien' },
  { code: 'TO', name: 'Tonga' },
  { code: 'TR', name: 'Türkei' },
  { code: 'TT', name: 'Trinidad und Tobago' },
  { code: 'TV', name: 'Tuvalu' },
  { code: 'TZ', name: 'Tansania' },
  { code: 'UA', name: 'Ukraine' },
  { code: 'UG', name: 'Uganda' },
  { code: 'US', name: 'USA' },
  { code: 'UY', name: 'Uruguay' },
  { code: 'UZ', name: 'Usbekistan' },
  { code: 'VA', name: 'Vatikanstadt' },
  { code: 'VC', name: 'St. Vincent und die Grenadinen' },
  { code: 'VE', name: 'Venezuela' },
  { code: 'VN', name: 'Vietnam' },
  { code: 'VU', name: 'Vanuatu' },
  { code: 'WS', name: 'Samoa' },
  { code: 'YE', name: 'Jemen' },
  { code: 'ZA', name: 'Südafrika' },
  { code: 'ZM', name: 'Sambia' },
  { code: 'ZW', name: 'Simbabwe' },
]

export const LAENDER: Land[] = [
  ...BEVORZUGTE_CODES.flatMap((code) => LAENDER_QUELLE.filter((l) => l.code === code)),
  ...LAENDER_QUELLE.filter((l) => !BEVORZUGTE_CODES.includes(l.code)).sort((a, b) =>
    a.name.localeCompare(b.name, 'de')
  ),
]

export function istEuLand(code: string | null | undefined): boolean {
  return !!code && EU_LAENDER_CODES.has(code.toUpperCase())
}

// USt-IdNr-Formatmuster je EU-Land (Issue #358) - Quelle: EU_LAENDER in
// database/seed.py (bewusst dupliziert, wie schon LAENDER selbst - Backend und Frontend
// teilen sich keine gemeinsame Konstanten-Datei). Griechenland nutzt fuer die USt-IdNr
// abweichend das Präfix "EL" statt des ISO-Landescodes "GR".
const UST_IDNR_FORMATE: Record<string, RegExp> = {
  AT: /^ATU[0-9]{8}$/,
  BE: /^BE[0-9]{10}$/,
  BG: /^BG[0-9]{9,10}$/,
  CY: /^CY[0-9]{8}[A-Z]$/,
  CZ: /^CZ[0-9]{8,10}$/,
  DE: /^DE[0-9]{9}$/,
  DK: /^DK[0-9]{8}$/,
  EE: /^EE[0-9]{9}$/,
  ES: /^ES[A-Z0-9][0-9]{7}[A-Z0-9]$/,
  FI: /^FI[0-9]{8}$/,
  FR: /^FR[A-Z0-9]{2}[0-9]{9}$/,
  GR: /^EL[0-9]{9}$/,
  HR: /^HR[0-9]{11}$/,
  HU: /^HU[0-9]{8}$/,
  IE: /^IE[0-9]{7}[A-Z]{1,2}$/,
  IT: /^IT[0-9]{11}$/,
  LT: /^LT([0-9]{9}|[0-9]{12})$/,
  LU: /^LU[0-9]{8}$/,
  LV: /^LV[0-9]{11}$/,
  MT: /^MT[0-9]{8}$/,
  NL: /^NL[0-9]{9}B[0-9]{2}$/,
  PL: /^PL[0-9]{10}$/,
  PT: /^PT[0-9]{9}$/,
  RO: /^RO[0-9]{2,10}$/,
  SE: /^SE[0-9]{12}$/,
  SI: /^SI[0-9]{8}$/,
  SK: /^SK[0-9]{10}$/,
}

/** Formale Prüfung der USt-IdNr für ein EU-Land (Issue #358). Liefert null wenn das Feld
 * leer ist oder für das Land kein Muster hinterlegt ist (z.B. Drittland) - in beiden Fällen
 * gibt es nichts zu warnen. Prüft nur die Form, nicht die tatsächliche Gültigkeit (dafür der
 * Link zur BZSt-eVatR-Abfrage). */
export function pruefeUstIdnrFormat(land: string | null | undefined, ustIdnr: string | null | undefined): boolean | null {
  if (!ustIdnr || !ustIdnr.trim()) return null
  const muster = land ? UST_IDNR_FORMATE[land.toUpperCase()] : undefined
  if (!muster) return null
  return muster.test(ustIdnr.trim().toUpperCase())
}
