"""
Verrechnung eines Zahlungs-Überschusses gegen offene Mahngebühr/Verzugszinsen
(docs/plan-mahnwesen.md, Abschnitt E).

Wird von der manuellen Zahlungserfassung (api/rechnungen.py, zahlung_bar_erstellen), vom
Bank-Import (api/bank_import.py, _buche_pfad_a) und von der kundenweiten Restgebühr-Zahlung
(api/mahnwesen.py, kunden_gebuehr_zahlung - für Kunden ohne offene Rechnung) genutzt.

Kundenweit statt rechnungsweise (Nutzer-Vorgabe: "Solange der Kontokorrent nicht ausgeglichen
ist müssen die Mahnstufen weiterlaufen... sonst gibt es keine Übereinstimmung mit dem
Kontokorrent") - eine Zahlung auf IRGENDEINE Rechnung eines Kunden darf gegen JEDE offene
Gebühr/Zinsen dieses Kunden verrechnet werden, nicht nur gegen die, die zufällig an der
bezahlten Rechnung hängt. Das schließt auch konsolidierte Mahnungen und reine
Gebühren-Mahnungen ohne Rechnung mit ein - die frühere Beschränkung auf "genau eine
verknüpfte Rechnung" war nur nötig, solange die Verrechnung noch rechnungsweise lief (die
Journaleinträge selbst tragen ohnehin keine rechnung_id mehr, siehe _buche()).
"""

from datetime import date
from decimal import Decimal
from typing import Callable

from sqlalchemy.orm import Session

from database.models import Kategorie, Journaleintrag, Mahnung, Rechnung
from utils.signatur import signatur_journaleintrag

Q = Decimal("0.01")


def _offene_mahnungen_kunde(db: Session, kunde_id: int) -> list[Mahnung]:
    """Versendete, NICHT übertragene Mahnungen eines Kunden, älteste zuerst - unabhängig davon,
    ob sie konsolidiert sind oder (Gebühren-Eskalation ohne Rechnung) überhaupt keine Rechnung
    mehr tragen."""
    return (
        db.query(Mahnung)
        .filter(
            Mahnung.kunde_id == kunde_id,
            Mahnung.status == "versendet",
            Mahnung.uebertragen_in_mahnung_id.is_(None),
        )
        .order_by(Mahnung.erstellt_am)
        .all()
    )


def offene_mahngebuehr_summe_kunde(db: Session, kunde_id: int) -> Decimal:
    """Noch nicht bezahlter Anteil aus Mahngebühr + Verzugszinsen aller versendeten,
    nicht übertragenen Mahnungen eines Kunden."""
    gesamt = Decimal("0")
    for m in _offene_mahnungen_kunde(db, kunde_id):
        gesamt += (m.mahngebuehr or Decimal("0")) - (m.mahngebuehr_bezahlt or Decimal("0"))
        gesamt += (m.verzugszinsen or Decimal("0")) - (m.verzugszinsen_bezahlt or Decimal("0"))
    return gesamt.quantize(Q)


def offene_mahngebuehr_summe(db: Session, rechnung_id: int) -> Decimal:
    """Kompatibilitäts-Wrapper: löst den Kunden zur Rechnung auf und delegiert kundenweit."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung or not rechnung.kunde_id:
        return Decimal("0.00")
    return offene_mahngebuehr_summe_kunde(db, rechnung.kunde_id)


def verrechne_mahngebuehren_kunde(
    db: Session,
    kunde_id: int,
    betrag: Decimal,
    datum: date,
    zahlungsart: str,
    naechste_belegnr_fn: Callable[[Session, date], str],
    konto_id: int | None = None,
    referenz: str | None = None,
) -> tuple[Decimal, list[int]]:
    """Verteilt `betrag` auf offene Mahngebühr/Verzugszinsen eines Kunden (älteste Mahnung
    zuerst, je Mahnung erst Gebühr dann Zinsen), bucht je Kategorie einen eigenen
    Journaleintrag (Einnahme, 0% USt - Mahngebühr = Schadensersatz §288 BGB, Verzugszinsen =
    Zinsertrag, beide nicht umsatzsteuerbar) und markiert die verrechneten Beträge auf der
    jeweiligen Mahnung. Committet NICHT selbst (Aufrufer committet/flusht).

    Gibt (nicht verrechenbarer Restbetrag, [erzeugte journal.id]) zurück - der Rest ist der
    tatsächliche Überschuss, der z.B. als Kundenguthaben zu erfassen ist.
    """
    rest = betrag.quantize(Q)
    if rest <= Decimal("0.004"):
        return rest, []

    kat_gebuehr = db.query(Kategorie).filter(Kategorie.name == "Mahngebühren", Kategorie.aktiv == True).first()  # noqa: E712
    kat_zinsen = db.query(Kategorie).filter(Kategorie.name == "Verzugszinsen (Einnahme)", Kategorie.aktiv == True).first()  # noqa: E712

    def _buche(kat: Kategorie | None, anteil: Decimal, beschreibung: str) -> Journaleintrag:
        # Bewusst OHNE rechnung_id: _aktualisiere_zahlungsstatus() (api/rechnungen.py) summiert
        # bei jeder Neuberechnung ALLE Journaleinträge mit passender rechnung_id in
        # rechnung.bezahlt_betrag - würde die Mahngebühr rechnung_id tragen, würde eine spätere
        # Neuberechnung (z.B. Korrektur einer anderen Zahlung derselben Rechnung) die Gebühr
        # fälschlich als Teilzahlung der Rechnung selbst mitzählen und bezahlt_betrag über
        # brutto_gesamt hinaus aufblähen. Kontokorrent-Anzeige holt sich die Buchung stattdessen
        # separat über kunde_id + Kategorie (_mahngebuehr_bewegungen(), api/kunden.py).
        e = Journaleintrag(
            datum=datum,
            belegnr=naechste_belegnr_fn(db, datum),
            beschreibung=beschreibung,
            kategorie_id=kat.id if kat else None,
            konto_skr03=kat.konto_skr03 if kat else None,
            konto_skr04=kat.konto_skr04 if kat else None,
            kunde_id=kunde_id,
            zahlungsart=zahlungsart,
            art="Einnahme",
            netto_betrag=anteil,
            ust_satz=Decimal("0"),
            ust_betrag=Decimal("0"),
            vorsteuer_betrag=Decimal("0"),
            brutto_betrag=anteil,
            vorsteuerabzug=False,
            konto_id=konto_id,
            immutable=True,
        )
        e.signatur = signatur_journaleintrag(e)
        db.add(e)
        db.flush()
        return e

    erzeugte: list[int] = []
    for m in _offene_mahnungen_kunde(db, kunde_id):
        if rest <= Decimal("0.004"):
            break

        ref = referenz or (m.mahnnummer or "")
        offen_gebuehr = (m.mahngebuehr or Decimal("0")) - (m.mahngebuehr_bezahlt or Decimal("0"))
        if offen_gebuehr > Decimal("0.004"):
            anteil = min(offen_gebuehr, rest).quantize(Q)
            e = _buche(kat_gebuehr, anteil, f"Mahngebühr {m.mahnnummer or ''} · {ref}".strip())
            m.mahngebuehr_bezahlt = (m.mahngebuehr_bezahlt or Decimal("0")) + anteil
            rest -= anteil
            erzeugte.append(e.id)

        if rest <= Decimal("0.004"):
            break

        offen_zinsen = (m.verzugszinsen or Decimal("0")) - (m.verzugszinsen_bezahlt or Decimal("0"))
        if offen_zinsen > Decimal("0.004"):
            anteil = min(offen_zinsen, rest).quantize(Q)
            e = _buche(kat_zinsen, anteil, f"Verzugszinsen {m.mahnnummer or ''} · {ref}".strip())
            m.verzugszinsen_bezahlt = (m.verzugszinsen_bezahlt or Decimal("0")) + anteil
            rest -= anteil
            erzeugte.append(e.id)

    return rest.quantize(Q), erzeugte


def verrechne_mahngebuehren(
    db: Session,
    rechnung_id: int,
    betrag: Decimal,
    datum: date,
    zahlungsart: str,
    naechste_belegnr_fn: Callable[[Session, date], str],
    konto_id: int | None = None,
) -> tuple[Decimal, list[int]]:
    """Kompatibilitäts-Wrapper: löst den Kunden zur Rechnung auf und delegiert kundenweit."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung or not rechnung.kunde_id:
        return betrag.quantize(Q), []
    return verrechne_mahngebuehren_kunde(
        db, rechnung.kunde_id, betrag, datum, zahlungsart, naechste_belegnr_fn,
        konto_id=konto_id, referenz=rechnung.rechnungsnummer or str(rechnung_id),
    )
