export type NavItem = { label: string; slug: string }
export type NavGroup = { heading: string | null; items: NavItem[] }

export const HANDBUCH_NAV: NavGroup[] = [
  {
    heading: 'Einstieg',
    items: [
      { label: 'Erste Schritte', slug: 'erste-schritte' },
      { label: 'Unternehmen einrichten', slug: 'unternehmen-einrichten' },
    ],
  },
  {
    heading: 'Fakturierung',
    items: [
      { label: 'Angebote', slug: 'angebote' },
      { label: 'Aufträge', slug: 'auftraege' },
      { label: 'Proforma-Rechnungen', slug: 'proforma-rechnungen' },
      { label: 'Lieferscheine', slug: 'lieferscheine' },
      { label: 'Rechnungen', slug: 'rechnungen' },
      { label: 'Wiederkehrende Rechnungen', slug: 'wiederkehrende-rechnungen' },
      { label: 'E-Mail-Versand', slug: 'e-mail-versand' },
      { label: 'Belege scannen & OCR', slug: 'belege-scannen-und-ocr' },
      { label: 'Backup & Wiederherstellung', slug: 'backup' },
    ],
  },
  {
    heading: 'Buchhaltung',
    items: [
      { label: 'Journal & Buchungen', slug: 'journal-und-buchungen' },
      { label: 'Buchungsvorlagen', slug: 'buchungsvorlagen' },
    ],
  },
  {
    heading: 'Stammdaten & Einstellungen',
    items: [
      { label: 'Stammdaten', slug: 'stammdaten' },
      { label: 'Kategorien', slug: 'kategorien' },
    ],
  },
  {
    heading: 'Auswertungen',
    items: [
      { label: 'Auswertungen & Export', slug: 'auswertungen-und-export' },
      { label: 'Anlage AVEÜR', slug: 'anlage-aveür' },
    ],
  },
  {
    heading: null,
    items: [
      { label: 'Häufige Fragen', slug: 'haeufige-fragen' },
    ],
  },
]
