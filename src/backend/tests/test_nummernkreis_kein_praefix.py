"""
Regressionstest für Issue #399, Wunsch 1: Der Nummernkreis-Präfix ("RE-"/"ER-") stand bisher
fest im Code, nicht im frei konfigurierbaren Nummernkreis-Format. Eine eigene Rechnungsnummern-
Konvention (z.B. "R###-YYYY") wurde dadurch immer zu "RE-R###-YYYY" verfälscht. Ab jetzt
entscheidet ausschließlich das am Nummernkreis hinterlegte Format über die erzeugte Nummer.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, _naechste_rechnungsnummer
from api.nummernkreise import naechste_nummer
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Nummernkreis, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def _position() -> RechnungspositionCreate:
    return RechnungspositionCreate(beschreibung="Beratung", menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("19"))


def test_eigenes_format_wird_nicht_mit_re_verfaelscht(db):
    """Genau das Beispiel aus dem Issue: Rxxx-YYYY (hier als R###-YYYY) muss unverändert
    durchgereicht werden, kein zusätzliches "RE-" davor."""
    db.add(Nummernkreis(bezeichnung="Ausgangsrechnungen", typ="rechnung_ausgang", format="R###-YYYY", naechste_nr=1, reset_jaehrlich=True))
    db.commit()

    data = RechnungCreate(typ="ausgang", datum=date(2026, 1, 15), ist_entwurf=False, partner_freitext="Testkunde", positionen=[_position()])
    ergebnis = create_rechnung(data, db)

    assert ergebnis.rechnungsnummer == "R001-2026"


def test_eigenes_format_eingang_wird_nicht_mit_er_verfaelscht(db):
    db.add(Nummernkreis(bezeichnung="Eingangsrechnungen", typ="rechnung_eingang", format="ER###-YYYY", naechste_nr=1, reset_jaehrlich=True))
    db.commit()

    data = RechnungCreate(typ="eingang", datum=date(2026, 1, 15), ist_entwurf=False, partner_freitext="Testlieferant", positionen=[_position()])
    ergebnis = create_rechnung(data, db)

    # Wer selbst "ER" im Format will, bekommt es einmal - nicht zusätzlich vom Code verdoppelt.
    assert ergebnis.rechnungsnummer == "ER001-2026"


def test_wer_re_praefix_will_traegt_ihn_selbst_im_format_ein(db):
    """Bisheriges Verhalten bleibt erreichbar, wenn gewünscht - jetzt aber explizit im Format."""
    db.add(Nummernkreis(bezeichnung="Ausgangsrechnungen", typ="rechnung_ausgang", format="RE-YY####", naechste_nr=1, reset_jaehrlich=True))
    db.commit()

    data = RechnungCreate(typ="ausgang", datum=date(2026, 1, 15), ist_entwurf=False, partner_freitext="Testkunde", positionen=[_position()])
    ergebnis = create_rechnung(data, db)

    assert ergebnis.rechnungsnummer == "RE-260001"


def test_naechste_rechnungsnummer_helper_kein_praefix(db):
    """_naechste_rechnungsnummer() wird von 6 Konvertierungen genutzt (Ersatzrechnung,
    Lieferschein/Angebot/Auftrag/Proforma -> Rechnung) - hatte eine eigene, zweite Kopie des
    Bugs unabhängig von create_rechnung()."""
    db.add(Nummernkreis(bezeichnung="Ausgangsrechnungen", typ="rechnung_ausgang", format="R###-YYYY", naechste_nr=1, reset_jaehrlich=True))
    db.commit()

    nr = _naechste_rechnungsnummer(date(2026, 1, 15), db)

    assert nr == "R001-2026"


def test_naechste_nummer_generischer_helper_respektiert_datum_fuer_jahreswechsel(db):
    """Der konsolidierte Helper muss das übergebene Belegdatum nutzen, nicht date.today() -
    sonst würde ein rückdatierter Beleg den Jahres-Rollover am falschen Datum festmachen. Jahr
    2030 bewusst weit in der Zukunft gewählt, damit der Test unabhängig vom echten "heute"
    eindeutig zeigt, dass das übergebene Datum verwendet wird."""
    db.add(Nummernkreis(bezeichnung="Ausgangsrechnungen", typ="rechnung_ausgang", format="YY####", naechste_nr=5, reset_jaehrlich=True, letztes_jahr=2030))
    db.commit()

    nr = naechste_nummer("rechnung_ausgang", db, date(2030, 3, 1))

    assert nr == "300005"  # Jahr laut uebergebenem Datum (2030) = letztes_jahr -> kein Reset, Zaehler bleibt bei 5
