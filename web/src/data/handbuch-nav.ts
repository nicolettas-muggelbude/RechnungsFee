export type NavItem = { label: string; slug: string; anchors?: { label: string; id: string }[] }
export type NavGroup = { heading: string | null; items: NavItem[] }

export const HANDBUCH_NAV: NavGroup[] = [
  {
    heading: null,
    items: [
      { label: '🏠 Startseite', slug: 'Home' },
    ],
  },
  {
    heading: 'Einstieg',
    items: [
      { label: 'Erste Schritte', slug: 'Erste-Schritte' },
      { label: 'Unternehmen einrichten', slug: 'Unternehmen-einrichten' },
    ],
  },
  {
    heading: 'Fakturierung',
    items: [
      { label: 'Angebote', slug: 'Angebote' },
      { label: 'Aufträge', slug: 'Auftraege' },
      { label: 'Proforma-Rechnungen', slug: 'Proforma-Rechnungen' },
      { label: 'Lieferscheine', slug: 'Lieferscheine' },
      { label: 'Rechnungen', slug: 'Rechnungen' },
      { label: 'Wiederkehrende Rechnungen', slug: 'Wiederkehrende-Rechnungen' },
      { label: 'E-Mail-Versand', slug: 'E-Mail-Versand' },
      { label: 'Belege scannen & OCR', slug: 'Belege-scannen-und-OCR' },
      { label: 'Backup & Wiederherstellung', slug: 'Backup' },
    ],
  },
  {
    heading: 'Buchhaltung',
    items: [
      { label: 'Journal & Buchungen', slug: 'Journal-und-Buchungen' },
      { label: 'Buchungsvorlagen', slug: 'Buchungsvorlagen' },
    ],
  },
  {
    heading: 'Stammdaten & Einstellungen',
    items: [
      { label: 'Stammdaten', slug: 'Stammdaten' },
      { label: 'Kategorien', slug: 'Kategorien' },
    ],
  },
  {
    heading: 'Auswertungen',
    items: [
      { label: 'Auswertungen & Export', slug: 'Auswertungen-und-Export' },
      { label: 'Anlage AVEÜR', slug: 'Anlage-AVEÜR' },
    ],
  },
  {
    heading: null,
    items: [
      { label: 'Häufige Fragen', slug: 'Haeufige-Fragen' },
    ],
  },
]
