"""
Issue #607: Anschaffungen auf Anlage-Kategorien (z. B. „EDV / Software (Sofortabschreibung)“)
fehlten im Cockpit komplett - das Cockpit lässt Anlage-Buchungen weg und kannte die AfA aus dem
Anlagenverzeichnis nicht. Jetzt: AfA monatsweise im Cockpit, Hinweis auf Anlage-Käufe ohne
Eintrag im Anlagenverzeichnis (Cockpit + EÜR), Vorschlag zum Eintragen aus der Buchung.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.anlageverzeichnis import (
    AnlagegutCreate, afa_je_monat, aktualisieren, erstellen, offene_anschaffungen, vorschlag_aus_buchung,
)
from api.cockpit import get_cockpit
from database.connection import Base
from database.models import Anlagegut, Journaleintrag, Kategorie, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="Testfirma", strasse="Str.", hausnummer="1", plz="12345", ort="Ort",
                      ist_kleinunternehmer=True))
    s.add(Kategorie(name="EDV / Software (Sofortabschreibung)", kontenart="Anlage", euer_zeile=None))
    s.commit()
    yield s
    s.close()


def _kat(s) -> Kategorie:
    return s.query(Kategorie).filter(Kategorie.kontenart == "Anlage").one()


_nr = iter(range(1, 1000))


def _buchung(s, datum, brutto="760.65", art="Ausgabe", beschreibung="Zahlung ER-260001: Hottgenroth Software AG",
             **kw) -> Journaleintrag:
    """Kleinunternehmer-Ausgabe: USt real, keine abziehbare Vorsteuer (Migration 161)."""
    b = Decimal(brutto)
    netto = (b / Decimal("1.19")).quantize(Decimal("0.01"))
    e = Journaleintrag(datum=datum, belegnr=f"26{next(_nr):04d}", beschreibung=beschreibung,
                       kategorie_id=_kat(s).id, zahlungsart="Bank", art=art, netto_betrag=netto,
                       ust_satz=Decimal("19"), ust_betrag=b - netto, brutto_betrag=b,
                       steuerbefreiung_grund="§19 UStG", **kw)
    s.add(e)
    s.commit()
    return e


def _gut(**kw) -> Anlagegut:
    werte = dict(bezeichnung="Software", typ="edv", kaufdatum=date(2026, 1, 2),
                 kaufpreis_netto=Decimal("760.65"), nutzungsdauer_jahre=1, afa_sofort=True,
                 privat_anteil_prozent=Decimal("0"))
    werte.update(kw)
    return Anlagegut(**werte)


# --- AfA je Monat ----------------------------------------------------------------------------

def test_afa_sofort_im_kaufmonat():
    assert afa_je_monat(_gut(kaufdatum=date(2025, 12, 31)), 2025) == {12: Decimal("760.65")}
    assert afa_je_monat(_gut(kaufdatum=date(2025, 12, 31)), 2026) == {}


def test_afa_linear_auf_monate_verteilt():
    gut = _gut(typ="sonstig", afa_sofort=False, nutzungsdauer_jahre=3, kaufdatum=date(2026, 4, 15),
               kaufpreis_netto=Decimal("3600.00"))
    kaufjahr = afa_je_monat(gut, 2026)
    assert sorted(kaufjahr) == list(range(4, 13)) and sum(kaufjahr.values()) == Decimal("900.00")
    assert sum(afa_je_monat(gut, 2027).values()) == Decimal("1200.00")
    restjahr = afa_je_monat(gut, 2029)
    assert sorted(restjahr) == [1, 2, 3] and sum(restjahr.values()) == Decimal("300.00")


def test_afa_endet_im_verkaufsmonat():
    gut = _gut(typ="sonstig", afa_sofort=False, nutzungsdauer_jahre=3, kaufdatum=date(2025, 1, 1),
               kaufpreis_netto=Decimal("3600.00"), verkauft_am=date(2026, 6, 10))
    monate = afa_je_monat(gut, 2026)
    assert sorted(monate) == list(range(1, 7)) and sum(monate.values()) == Decimal("600.00")


# --- Cockpit ---------------------------------------------------------------------------------

def test_cockpit_zeigt_afa_statt_kaufpreis(db):
    _buchung(db, date(2026, 1, 2))
    db.add(_gut())
    db.commit()
    jan = get_cockpit(zeitraum="monat", wert="2026-01", db=db)
    assert jan["kpis"]["ausgaben"] == 760.65
    assert jan["ausgaben_kategorien"] == [{"name": "Abschreibungen (AfA)", "betrag": 760.65}]
    assert jan["offene_anschaffungen"] == []  # über Betrag + Datum als eingetragen erkannt
    jahr = get_cockpit(zeitraum="jahr", wert="2026", db=db)
    assert jahr["monatsbalken"][0]["ausgaben"] == 760.65


def test_cockpit_meldet_anschaffung_ohne_anlagenverzeichnis(db):
    e = _buchung(db, date(2026, 9, 3), brutto="332.01", beschreibung="Zahlung ER-260007: Hottgenroth Software AG")
    sep = get_cockpit(zeitraum="monat", wert="2026-09", db=db)
    assert sep["kpis"]["ausgaben"] == 0
    assert [o["journal_id"] for o in sep["offene_anschaffungen"]] == [e.id]
    assert sep["offene_anschaffungen"][0]["betrag"] == 332.01  # Kleinunternehmer: brutto


def test_stornierte_anschaffung_nicht_gemeldet(db):
    e = _buchung(db, date(2026, 3, 1))
    _buchung(db, date(2026, 3, 5), art="Einnahme", beschreibung=f"STORNO {e.belegnr}: falsch", gruppe_id=e.id)
    assert offene_anschaffungen(db, date(2026, 1, 1), date(2026, 12, 31)) == []


# --- Vorschlag + Verknüpfung -----------------------------------------------------------------

def test_vorschlag_und_verknuepfung(db):
    e = _buchung(db, date(2026, 9, 3), brutto="332.01")
    v = vorschlag_aus_buchung(db, e.id)
    assert v == {
        "bezeichnung": "Hottgenroth Software AG", "typ": "edv", "kaufdatum": "2026-09-03",
        "kaufpreis_netto": "332.01", "nutzungsdauer_jahre": 1, "afa_sofort": True, "journal_id": e.id,
    }
    # abweichender Betrag: nur die Verknüpfung macht sie zur eingetragenen Anschaffung
    gut = erstellen(AnlagegutCreate(**{**v, "kaufpreis_netto": Decimal("300.00")}), db)
    assert offene_anschaffungen(db, date(2026, 1, 1), date(2026, 12, 31)) == []
    # Bearbeiten im Formular (ohne journal_id) behält die Verknüpfung
    aktualisieren(gut.id, AnlagegutCreate(bezeichnung="Neu", typ="edv", kaufdatum=date(2026, 9, 3),
                                          kaufpreis_netto=Decimal("300.00"), nutzungsdauer_jahre=1,
                                          afa_sofort=True), db)
    assert db.get(Anlagegut, gut.id).journal_id == e.id
    assert get_cockpit(zeitraum="monat", wert="2026-09", db=db)["kpis"]["ausgaben"] == 300.0


def test_regelbesteuert_netto(db):
    db.query(Unternehmen).one().ist_kleinunternehmer = False
    e = Journaleintrag(datum=date(2026, 5, 2), belegnr="269999", beschreibung="Laptop",
                       kategorie_id=_kat(db).id, zahlungsart="Bank", art="Ausgabe",
                       netto_betrag=Decimal("1000.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("190.00"),
                       vorsteuer_betrag=Decimal("190.00"), vorsteuerabzug=True, brutto_betrag=Decimal("1190.00"))
    db.add(e)
    db.commit()
    assert vorschlag_aus_buchung(db, e.id)["kaufpreis_netto"] == "1000.00"
