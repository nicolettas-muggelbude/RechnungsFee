"""
Regressionstest für Issue #353 (UStVA – Anzeigehilfe einzeln aufgeschlüsselt).

_berechne_kz() sammelt jetzt neben den KZ-Summen auch die einzelnen beitragenden Journal-
einträge/Vorsteuer-Ansprüche (posten). Die Posten werden an derselben Stelle im Code
gesammelt, an der auch die Summe gebildet wird (single source of truth) - der wichtigste
Test ist deshalb die Invariante "Summe der Posten == KZ-Summe" für mehrere Szenarien
(normale Buchung, Storno, Sonderfall, Vorsteuer-Soll-Prinzip).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.journal import storno_eintrag, create_eintrag
from api.schemas import JournalEintragCreate, StornoRequest
from api.rechnungen import finalisiere_rechnung
from api.ustva import _berechne_kz, ustva_posten
from database.connection import Base
from database.models import Kategorie, Rechnung, Rechnungsposition, Unternehmen


@pytest.fixture
def db(monkeypatch):
    import api.rechnungen as rechnungen_api
    import api.ustva as ustva_api
    monkeypatch.setattr(rechnungen_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    monkeypatch.setattr(ustva_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def _kategorie(db, name="Bürobedarf", skr03="4930", skr04="6815") -> Kategorie:
    kat = Kategorie(name=name, kontenart="Aufwand", konto_skr03=skr03, konto_skr04=skr04,
                     vorsteuer_prozent=100, ust_satz_standard=19)
    db.add(kat)
    db.commit()
    db.refresh(kat)
    return kat


def test_normale_ausgabe_erscheint_als_posten_in_kz66(db):
    kat = _kategorie(db)
    create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 1, 10), beschreibung="Büromaterial Amazon",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("119.00"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, zahlungsart="Bank",
        ),
        db,
    )
    kz, posten = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)
    assert kz["kz_66"] == Decimal("19.00")
    assert len(posten["kz_66"]) == 1
    p = posten["kz_66"][0]
    assert p["quelle"] == "journal"
    assert p["beschreibung"] == "Büromaterial Amazon"
    assert p["betrag"] == Decimal("19.00")


def test_summe_posten_entspricht_kz_summe_bei_mehreren_buchungen(db):
    kat = _kategorie(db)
    for i, betrag in enumerate([Decimal("119.00"), Decimal("238.00"), Decimal("59.50")]):
        create_eintrag(
            JournalEintragCreate(
                datum=date(2026, 1, 5 + i), beschreibung=f"Buchung {i}",
                kategorie_id=kat.id, art="Ausgabe", brutto_betrag=betrag,
                ust_satz=Decimal("19"), vorsteuerabzug=True, zahlungsart="Bank",
            ),
            db,
        )
    kz, posten = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)
    summe_posten = sum((p["betrag"] for p in posten["kz_66"]), Decimal("0"))
    assert summe_posten == kz["kz_66"]
    assert len(posten["kz_66"]) == 3


def test_storno_erzeugt_gegenlaeufigen_posten_der_sich_aufhebt(db):
    kat = _kategorie(db)
    eintrag = create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 2, 5), beschreibung="Hosting-Rechnung",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("119.00"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, zahlungsart="Bank",
        ),
        db,
    )
    storno_eintrag(eintrag.id, StornoRequest(grund="Testkorrektur"), db)

    kz, posten = _berechne_kz(date(2026, 2, 1), date(2026, 2, 28), db)
    assert kz["kz_66"] == Decimal("0.00")
    assert len(posten["kz_66"]) == 2
    summe_posten = sum((p["betrag"] for p in posten["kz_66"]), Decimal("0"))
    assert summe_posten == Decimal("0.00")


def test_sonderfall_13b_erscheint_in_posten(db):
    kat = Kategorie(
        name="EU-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand",
        konto_skr03="3123", konto_skr04="5923", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 3, 5), beschreibung="Finom Kontoführung",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("128.38"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, ust_sonderfall="13b_abs1",
            zahlungsart="Bank",
        ),
        db,
    )
    kz, posten = _berechne_kz(date(2026, 3, 1), date(2026, 3, 31), db)
    assert len(posten["kz_46"]) == 1
    assert posten["kz_46"][0]["betrag"] == kz["kz_46"]
    assert len(posten["kz_47"]) == 1
    assert len(posten["kz_67"]) == 1


def _eingangsrechnung_finalisiert(db, kategorie_id, datum=date(2026, 4, 10)) -> Rechnung:
    netto = Decimal("100.00")
    ust = Decimal("19.00")
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer=None, datum=datum,
        brutto_gesamt=netto + ust, netto_gesamt=netto, ust_gesamt=ust,
        ist_entwurf=True, kategorie_id=kategorie_id,
    )
    db.add(rechnung)
    db.commit()
    db.refresh(rechnung)
    pos = Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"), einheit="Stk.",
        netto=netto, ust_satz=Decimal("19"), ust_betrag=ust, brutto=netto + ust,
        kategorie_id=kategorie_id,
    )
    db.add(pos)
    db.commit()
    finalisiere_rechnung(rechnung.id, db)
    db.refresh(rechnung)
    return rechnung


def test_vorsteuer_anspruch_erscheint_in_kz66_posten(db):
    kat = _kategorie(db)
    rechnung = _eingangsrechnung_finalisiert(db, kat.id)

    kz, posten = _berechne_kz(date(2026, 4, 1), date(2026, 4, 30), db)
    assert kz["kz_66"] == Decimal("19.00")
    assert len(posten["kz_66"]) == 1
    p = posten["kz_66"][0]
    assert p["quelle"] == "vorsteuer_anspruch"
    assert p["rechnung_id"] == rechnung.id
    assert p["betrag"] == Decimal("19.00")


def test_endpoint_liefert_posten_fuer_gueltige_kz(db):
    kat = _kategorie(db)
    create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 5, 5), beschreibung="Testbuchung",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("119.00"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, zahlungsart="Bank",
        ),
        db,
    )
    ergebnis = ustva_posten(zeitraum="2026-05", kz="66", db=db)
    assert len(ergebnis) == 1
    assert ergebnis[0].betrag == Decimal("19.00")
    assert ergebnis[0].beschreibung == "Testbuchung"


def test_endpoint_unbekannte_kz_gibt_422(db):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ustva_posten(zeitraum="2026-05", kz="999", db=db)
    assert exc.value.status_code == 422
