"""
Issue #567: Erlös-Kategorie je Position bei Ausgangsrechnungen (z. B. Übungsleiter-Einnahmen
§ 3 Nr. 26 EStG neben normalen Leistungen auf derselben Rechnung).

- Ohne gewählte Kategorie bucht die Zahlung unverändert über die automatische Erlös-Kategorie.
- Mit Kategorien wird die Zahlung je (USt-Satz, Kategorie) aufgeteilt - in „Zahlung erfassen“
  und im Bank-Import, für Kleinunternehmer und Regelbesteuerte.
- Sonderfälle (ig. Lieferung usw.) ignorieren/entfernen eine gewählte Kategorie.
- Nur Erlös-Kategorien sind zulässig.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import _buche_pfad_a
from api.rechnungen import create_rechnung, finalisiere_rechnung, update_rechnung, zahlung_bar_erstellen
from api.schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import (
    BankImport, BankTemplate, BankTransaktion, Journaleintrag, Kategorie, Konto, Kunde, Nummernkreis, Rechnung,
    Unternehmen,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Museum Muster", strasse="Weg", hausnummer="1", plz="12345", ort="Ort",
                            ist_kleinunternehmer=False))
    for typ, fmt in [("rechnung_ausgang", "RE-YY####"), ("journal", "YY####")]:
        session.add(Nummernkreis(bezeichnung=typ, typ=typ, format=fmt, naechste_nr=1, reset_jaehrlich=True, aktiv=True))
    session.add_all([
        Kategorie(name="Betriebseinnahmen", kontenart="Erlös", euer_zeile=15, konto_skr03="8400", konto_skr04="4400",
                  ust_satz_standard=19),
        Kategorie(name="Betriebseinnahmen (7%)", kontenart="Erlös", euer_zeile=15, konto_skr03="8300",
                  konto_skr04="4300", ust_satz_standard=7),
        Kategorie(name="Betriebseinnahmen (0%)", kontenart="Erlös", euer_zeile=16, konto_skr03="8100",
                  konto_skr04="4100", ust_satz_standard=0),
        Kategorie(name="Betriebseinnahmen (Kleinunternehmer)", kontenart="Erlös", euer_zeile=12,
                  konto_skr03="8192", konto_skr04="4184", ust_satz_standard=0),
        Kategorie(name="Innergemeinschaftliche Lieferungen", kontenart="Erlös", euer_zeile=16,
                  konto_skr03="8125", konto_skr04="4125", ust_satz_standard=0),
        Kategorie(name="Übungsleiter § 3 Nr. 26", kontenart="Erlös", euer_zeile=15, konto_skr03="8400",
                  konto_skr04="4400", ust_satz_standard=19),
        Kategorie(name="Büromaterial", kontenart="Aufwand", euer_zeile=60, konto_skr03="4930", konto_skr04="6815",
                  ust_satz_standard=19),
        Kunde(firmenname="Stadtmuseum", strasse="Str", hausnummer="2", plz="12345", ort="Ort", kundennummer="K-1"),
    ])
    session.commit()
    yield session
    session.close()


def _kat(db, name) -> Kategorie:
    return db.query(Kategorie).filter(Kategorie.name == name).one()


def _ku(db, an: bool = True):
    db.query(Unternehmen).one().ist_kleinunternehmer = an
    db.commit()


def _rechnung(db, positionen, **extra) -> Rechnung:
    r = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 3, 10), kunde_id=db.query(Kunde).one().id,
        positionen=positionen, **extra,
    ), db)
    finalisiere_rechnung(r.id, db)
    return db.query(Rechnung).filter(Rechnung.id == r.id).one()


def _pos(beschreibung, netto, satz="19", kategorie=None):
    return RechnungspositionCreate(beschreibung=beschreibung, netto=Decimal(netto), ust_satz=Decimal(satz),
                                   kategorie_id=kategorie.id if kategorie else None)


def _buchungen(db, r) -> dict[str, Decimal]:
    erg: dict[str, Decimal] = {}
    for e in db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == r.id).all():
        erg[e.kategorie.name] = erg.get(e.kategorie.name, Decimal("0")) + e.brutto_betrag
    return erg


def _zahlen(db, r, **kw):
    zahlung_bar_erstellen(r.id, BarZahlungCreate(datum=date(2026, 3, 20), zahlungsart="Bank", **kw), db)


# --- Bestandsverhalten ----------------------------------------------------------------------------

def test_ohne_kategorie_unveraendert_regelbesteuert(db):
    r = _rechnung(db, [_pos("Führung", "100"), _pos("Buch", "50", "7")])
    _zahlen(db, r)
    assert _buchungen(db, r) == {"Betriebseinnahmen": Decimal("172.50")}


def test_ohne_kategorie_unveraendert_kleinunternehmer(db):
    _ku(db)
    r = _rechnung(db, [_pos("Führung", "100", "0"), _pos("Workshop", "50", "0")])
    _zahlen(db, r)
    assert _buchungen(db, r) == {"Betriebseinnahmen (Kleinunternehmer)": Decimal("150.00")}


# --- Gemischte Kategorien -------------------------------------------------------------------------

def test_kleinunternehmer_zwei_kategorien(db):
    _ku(db)
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Führung", "300", "0", ul), _pos("Fotos", "200", "0")])
    _zahlen(db, r)
    assert _buchungen(db, r) == {
        "Übungsleiter § 3 Nr. 26": Decimal("300.00"),
        "Betriebseinnahmen (Kleinunternehmer)": Decimal("200.00"),
    }
    for e in db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == r.id):
        assert e.ust_betrag == Decimal("0.00")
        assert e.steuerbefreiung_grund == "§19 UStG"


def test_regelbesteuert_kategorie_und_satz_getrennt(db):
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Führung", "100", "19", ul), _pos("Vortrag", "100", "19"), _pos("Buch", "100", "7")])
    _zahlen(db, r)
    eintraege = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == r.id).all()
    je = {(e.kategorie.name, int(e.ust_satz)): (e.brutto_betrag, e.ust_betrag) for e in eintraege}
    assert je == {
        ("Übungsleiter § 3 Nr. 26", 19): (Decimal("119.00"), Decimal("19.00")),
        ("Betriebseinnahmen", 19): (Decimal("119.00"), Decimal("19.00")),
        ("Betriebseinnahmen", 7): (Decimal("107.00"), Decimal("7.00")),
    }


def test_teilzahlung_anteilig(db):
    _ku(db)
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Führung", "300", "0", ul), _pos("Fotos", "100", "0")])
    _zahlen(db, r, betrag=Decimal("200"))
    assert _buchungen(db, r) == {
        "Übungsleiter § 3 Nr. 26": Decimal("150.00"),
        "Betriebseinnahmen (Kleinunternehmer)": Decimal("50.00"),
    }


def test_skonto_je_satz_zusammengefasst(db):
    db.add(Kategorie(name="Gewährte Skonti", kontenart="Erlös", konto_skr03="8736", konto_skr04="4736"))
    db.commit()
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Führung", "100", "19", ul), _pos("Vortrag", "100", "19")])
    _zahlen(db, r, betrag=Decimal("233.24"), skonto_betrag=Decimal("4.76"))
    skonto = db.query(Journaleintrag).filter(
        Journaleintrag.rechnung_id == r.id, Journaleintrag.kategorie_id == _kat(db, "Gewährte Skonti").id,
    ).all()
    assert len(skonto) == 1
    assert skonto[0].brutto_betrag == Decimal("4.76")


def test_bank_import_zwei_kategorien(db):
    _ku(db)
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Führung", "300", "0", ul), _pos("Fotos", "200", "0")])
    konto = Konto(name="Giro", anbieter="Bank")
    db.add(konto)
    db.add(BankTemplate(id="t", name="T", bank="Bank", format="Standard", column_mapping="{}"))
    db.flush()
    imp = BankImport(konto_id=konto.id, template_id="t", dateiname="x.csv")
    db.add(imp)
    db.flush()
    tx = BankTransaktion(konto_id=konto.id, import_id=imp.id, datum=date(2026, 3, 20), betrag=Decimal("500.00"),
                         verwendungszweck=r.rechnungsnummer)
    db.add(tx)
    db.commit()
    _buche_pfad_a(db, tx, r)
    db.commit()
    assert _buchungen(db, r) == {
        "Übungsleiter § 3 Nr. 26": Decimal("300.00"),
        "Betriebseinnahmen (Kleinunternehmer)": Decimal("200.00"),
    }


# --- Sonderfälle und Prüfung ----------------------------------------------------------------------

def test_ig_lieferung_entfernt_kategorie(db):
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Ware", "100", "0", ul)], ist_eu_lieferung=True)
    assert all(p.kategorie_id is None for p in r.positionen)
    _zahlen(db, r)
    assert _buchungen(db, r) == {"Innergemeinschaftliche Lieferungen": Decimal("100.00")}


def test_kennzeichen_nachtraeglich_entfernt_kategorie(db):
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 3, 10), kunde_id=db.query(Kunde).one().id, ist_entwurf=True,
        positionen=[_pos("Ware", "100", "0", ul)],
    ), db)
    update_rechnung(r.id, RechnungUpdate(ist_eu_lieferung=True), db)
    r = db.query(Rechnung).filter(Rechnung.id == r.id).one()
    assert all(p.kategorie_id is None for p in r.positionen)


def test_automatik_kategorie_abgelehnt(db):
    """ig. Lieferung als Positionskategorie ohne Haken würde mit 19 % USt auf 8125 buchen."""
    with pytest.raises(HTTPException) as exc:
        create_rechnung(RechnungCreate(
            typ="ausgang", datum=date(2026, 3, 10), kunde_id=db.query(Kunde).one().id,
            positionen=[_pos("Ware", "100", "19", _kat(db, "Innergemeinschaftliche Lieferungen"))],
        ), db)
    assert exc.value.status_code == 422


def test_aufwandskategorie_abgelehnt(db):
    with pytest.raises(HTTPException) as exc:
        create_rechnung(RechnungCreate(
            typ="ausgang", datum=date(2026, 3, 10), kunde_id=db.query(Kunde).one().id,
            positionen=[_pos("Führung", "100", "19", _kat(db, "Büromaterial"))],
        ), db)
    assert exc.value.status_code == 422


# --- Folgemeldung Markus: weitere Teilzahlung nach offenem Betrag, Korrektur je Kategorie --------

def _eintrag(db, r, kat_name) -> Journaleintrag:
    return db.query(Journaleintrag).filter(
        Journaleintrag.rechnung_id == r.id, Journaleintrag.kategorie_id == _kat(db, kat_name).id,
    ).one()


def test_zweite_teilzahlung_nach_offenem_betrag(db):
    from api.rechnungen import ZahlungKorrigieren, zahlung_korrigieren
    _ku(db)
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Führung", "300", "0", ul), _pos("Fotos", "100", "0")])
    _zahlen(db, r, betrag=Decimal("200"))  # 150 / 50
    # Übungsleiter-Anteil per Korrektur voll bezahlt
    zahlung_korrigieren(r.id, _eintrag(db, r, "Übungsleiter § 3 Nr. 26").id,
                        ZahlungKorrigieren(neues_datum=date(2026, 3, 20), neuer_betrag=Decimal("300")), db)
    db.expire_all()
    _zahlen(db, r)  # Rest 50 € → komplett auf die noch offene Kategorie
    assert _buchungen(db, r) == {
        "Übungsleiter § 3 Nr. 26": Decimal("300.00"),
        "Betriebseinnahmen (Kleinunternehmer)": Decimal("100.00"),
    }


def test_teilzahlungen_ohne_korrektur_ergeben_positionssummen(db):
    _ku(db)
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Führung", "300", "0", ul), _pos("Fotos", "100", "0")])
    _zahlen(db, r, betrag=Decimal("123.45"))
    db.expire_all()  # in der App eigene Anfrage je Zahlung
    _zahlen(db, r, betrag=Decimal("76.55"))
    db.expire_all()
    _zahlen(db, r)
    assert _buchungen(db, r) == {
        "Übungsleiter § 3 Nr. 26": Decimal("300.00"),
        "Betriebseinnahmen (Kleinunternehmer)": Decimal("100.00"),
    }


def test_korrektur_ueber_kategorie_anteil_abgelehnt(db):
    from api.rechnungen import ZahlungKorrigieren, zahlung_korrigieren
    _ku(db)
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Führung", "300", "0", ul), _pos("Fotos", "100", "0")])
    _zahlen(db, r, betrag=Decimal("200"))  # 150 / 50
    with pytest.raises(HTTPException) as exc:
        zahlung_korrigieren(r.id, _eintrag(db, r, "Übungsleiter § 3 Nr. 26").id,
                            ZahlungKorrigieren(neues_datum=date(2026, 3, 20), neuer_betrag=Decimal("300.01")), db)
    assert exc.value.status_code == 422
    assert "300.00" in exc.value.detail


def test_voll_bezahlte_kategorie_bekommt_keine_0_euro_buchung(db):
    """Folgefund (Markus): Nach voll bezahlter Übungsleiter-Kategorie legte die nächste Teilzahlung
    eine 0-€-Buchung auf ihr an. Die ließ sich per „Zahlung korrigieren“ erhöhen, weil die
    Kategorie-Prüfung nur bei Beträgen über 0 griff - die Kategorie bekam mehr als ihre Positionen."""
    from api.rechnungen import ZahlungKorrigieren, zahlung_korrigieren
    _ku(db)
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Führung", "300", "0", ul), _pos("Fotos", "100", "0")])
    _zahlen(db, r, betrag=Decimal("200"))  # 150 / 50
    zahlung_korrigieren(r.id, _eintrag(db, r, "Übungsleiter § 3 Nr. 26").id,
                        ZahlungKorrigieren(neues_datum=date(2026, 3, 20), neuer_betrag=Decimal("300")), db)
    db.expire_all()
    _zahlen(db, r, betrag=Decimal("30"))  # geht komplett auf „Fotos“
    db.expire_all()
    ul_eintraege = db.query(Journaleintrag).filter(
        Journaleintrag.rechnung_id == r.id, Journaleintrag.kategorie_id == ul.id,
        ~Journaleintrag.beschreibung.like("STORNO %"),
    ).all()
    assert all(e.brutto_betrag != 0 for e in ul_eintraege)

    # Altbestand: eine 0-€-Buchung aus v0.7.13 darf nicht über den Kategorie-Anteil erhöht werden
    null = Journaleintrag(datum=date(2026, 3, 21), belegnr="J-NULL", beschreibung="Zahlung", zahlungsart="Bank",
                          art="Einnahme", kategorie_id=ul.id, netto_betrag=Decimal("0"), ust_satz=Decimal("0"),
                          ust_betrag=Decimal("0"), vorsteuer_betrag=Decimal("0"), brutto_betrag=Decimal("0"),
                          rechnung_id=r.id, immutable=True)
    db.add(null)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        zahlung_korrigieren(r.id, null.id,
                            ZahlungKorrigieren(neues_datum=date(2026, 3, 21), neuer_betrag=Decimal("20")), db)
    assert exc.value.status_code == 422
