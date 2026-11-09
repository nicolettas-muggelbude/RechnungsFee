"""
Adressrollen je Dokument (Issue #495).

Ein Kunde hat neben seiner Stammanschrift beliebig viele weitere Adressen (Filialen, Standorte,
Lieferadressen – Tabelle kunden_lieferadressen). Jedes Ausgangsdokument kann zwei davon nutzen:

| Dokument                         | Adressfeld                        | Lieferadresse        |
|----------------------------------|-----------------------------------|----------------------|
| Angebot                          | Empfänger (empfaenger_adresse_id) | –                    |
| Auftrag, Proforma                | Rechnungsadresse (empfaenger_…)   | lieferadresse_id     |
| Lieferschein                     | Lieferadresse (lieferadresse_id)  | (= Adressfeld)       |
| Rechnung, Abschlag, Gutschrift   | Rechnungsadresse (empfaenger_…)   | lieferadresse_id     |

Leer = Stammanschrift des Kunden. Oben im Adressfeld steht der Name/die Firma der Adresse, falls
dort eingetragen (z. B. eine eigene Gesellschaft der Filiale), sonst der des Kunden (Firmenname
bzw. bei Privatkunden der Name).
"""

# Dokumente, deren Adressfeld über empfaenger_adresse_id auf eine weitere Adresse zeigen kann.
# Der Lieferschein speichert den Wert nur zum Weiterreichen an die Rechnung, im Adressfeld steht
# bei ihm die Lieferadresse.
EMPFAENGER_DOKUMENTE = (
    "Angebot", "Auftrag", "Proforma", "Lieferschein", "Rechnung", "Abschlagsrechnung", "Gutschrift",
)

# Dokumente mit Lieferadresse
LIEFERADRESSE_DOKUMENTE = ("Auftrag", "Proforma", "Lieferschein", "Rechnung", "Abschlagsrechnung", "Gutschrift")


def _dokument_typ(r) -> str:
    return getattr(r, "dokument_typ", None) or "Rechnung"


def adressfeld_adresse(r):
    """Weitere Adresse des Kunden, die im Adressfeld steht – None = Stammanschrift."""
    if getattr(r, "typ", "ausgang") != "ausgang" or not getattr(r, "kunde_id", None):
        return None
    if _dokument_typ(r) == "Lieferschein":
        return getattr(r, "lieferadresse", None)
    if _dokument_typ(r) in EMPFAENGER_DOKUMENTE:
        return getattr(r, "empfaenger_adresse", None)
    return None


def lieferzeile_adresse(r):
    """Lieferadresse als eigene Zeile bei den Dokumentdaten – nur wenn sie nicht ohnehin schon
    im Adressfeld steht."""
    if getattr(r, "typ", "ausgang") != "ausgang" or _dokument_typ(r) not in LIEFERADRESSE_DOKUMENTE:
        return None
    la = getattr(r, "lieferadresse", None)
    if la is None:
        return None
    feld = adressfeld_adresse(r)
    if feld is not None and feld.id == la.id:
        return None
    return la


def kundenname(kunde) -> str:
    """Firmenname, bei Privatkunden Vor- und Nachname."""
    if kunde is None:
        return ""
    firma = (getattr(kunde, "firmenname", None) or "").strip()
    if firma:
        return firma
    return " ".join(filter(None, [(getattr(kunde, "vorname", None) or "").strip(),
                                  (getattr(kunde, "nachname", None) or "").strip()]))


def name_fuer_adresse(la, kunde) -> str:
    """Eigener Name/Firma der Adresse, sonst Name/Firma aus den Kundenstammdaten."""
    return (getattr(la, "name", None) or "").strip() or kundenname(kunde)


def adresszeilen_weitere_adresse(la, kunde) -> list[str]:
    """Adressfeld für eine weitere Adresse: Name/Firma, Bezeichnung der Filiale, z. Hd., Anschrift."""
    zeilen = []
    name = name_fuer_adresse(la, kunde)
    if name:
        zeilen.append(name)
    bezeichnung = (getattr(la, "bezeichnung", None) or "").strip()
    if bezeichnung and bezeichnung != name:
        zeilen.append(bezeichnung)
    z_hd = (getattr(la, "z_hd", None) or "").strip()
    if z_hd:
        zeilen.append(f"z.Hd. {z_hd}")
    if la.strasse:
        zeilen.append(f"{la.strasse} {la.hausnummer or ''}".strip())
    if la.plz or la.ort:
        zeilen.append(f"{la.plz or ''} {la.ort or ''}".strip())
    if (la.land or "DE").upper() != "DE":
        zeilen.append(la.land.upper())
    return zeilen


def empfaenger_email(r):
    """Mailadresse für den Versand: die der Adresse im Adressfeld, sonst die des Kunden."""
    la = adressfeld_adresse(r)
    if la is not None and (getattr(la, "email", None) or "").strip():
        return la.email.strip()
    kunde = getattr(r, "kunde", None)
    return getattr(kunde, "email", None) if kunde is not None else None
