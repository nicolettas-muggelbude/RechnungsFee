"""
Issue #568: Der Vertrag einer Buchungsvorlage wird beim Buchen als eigene Kopie an die Buchung
gehängt (bisher gar nicht). Ein beim Buchen hochgeladener Beleg hat Vorrang.

Nebenfund: Entfernen/Ersetzen eines Journal-Anhangs löschte die Datei ungeprüft - jetzt nur,
wenn den Beleg nichts anderes mehr verwendet.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.buchungsvorlagen as bv_mod
import api.journal as journal_mod
import api.rechnungen as rechnungen_mod
from api.buchungsvorlagen import BuchenRequest, buche_vorlage
from api.journal import delete_anhang
from database.connection import Base
from database.models import Beleg, Buchungsvorlage, Journaleintrag


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    belege = tmp_path / "uploads" / "belege"
    for mod in (bv_mod, journal_mod, rechnungen_mod):
        monkeypatch.setattr(mod, "BELEG_DIR", belege, raising=False)
        monkeypatch.setattr(mod, "APP_DATA_DIR", tmp_path, raising=False)
    monkeypatch.setattr(journal_mod, "konvertiere_zu_pdfa", lambda *a, **k: None)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    # Vertrag der Vorlage: relativ zu uploads/belege/ gespeichert (wie lade_beleg_hoch)
    belege.mkdir(parents=True)
    (belege / "vertrag123.pdf").write_bytes(b"%PDF-1.4 Honorarvertrag")
    vertrag = Beleg(dateiname="vertrag123.pdf", original_name="Honorarvertrag.pdf",
                    mime_type="application/pdf", dateigroesse=23)
    db.add(vertrag)
    db.flush()
    v = Buchungsvorlage(bezeichnung="Honorar", betrag=Decimal("300"), ist_brutto=True, ust_satz=Decimal("0"),
                        intervall="monatlich", naechstes_datum=date(2026, 11, 1), modus="direkt", art="Einnahme",
                        beleg_id=vertrag.id)
    db.add(v)
    db.commit()
    yield db, v, tmp_path
    db.close()


def _eintrag(db, v) -> Journaleintrag:
    return db.query(Journaleintrag).filter(Journaleintrag.buchungsvorlage_id == v.id).order_by(
        Journaleintrag.id.desc()).first()


def test_vertrag_wird_als_kopie_angehaengt(umgebung):
    db, v, tmp_path = umgebung
    buche_vorlage(v.id, data=BuchenRequest(), db=db)
    e = _eintrag(db, v)
    assert e.beleg_id and e.beleg_id != v.beleg_id
    kopie = db.query(Beleg).filter(Beleg.id == e.beleg_id).one()
    assert kopie.original_name == "Honorarvertrag.pdf"
    assert kopie.dateiname.startswith("belege/")
    assert (tmp_path / "uploads" / kopie.dateiname).read_bytes() == b"%PDF-1.4 Honorarvertrag"


def test_eigener_beleg_hat_vorrang(umgebung):
    db, v, _ = umgebung
    eigener = Beleg(dateiname="belege/x.pdf", original_name="Abrechnung.pdf", mime_type="application/pdf",
                    dateigroesse=1)
    db.add(eigener)
    db.commit()
    buche_vorlage(v.id, data=BuchenRequest(beleg_id=eigener.id), db=db)
    assert _eintrag(db, v).beleg_id == eigener.id


def test_anhang_entfernen_loescht_geteilten_beleg_nicht(umgebung):
    db, v, tmp_path = umgebung
    # Journalbuchung, die (z. B. aus Altbestand) denselben Beleg wie die Vorlage nutzt
    e = Journaleintrag(datum=date(2026, 11, 1), belegnr="260001", beschreibung="x", zahlungsart="Bank",
                       art="Einnahme", netto_betrag=Decimal("1"), brutto_betrag=Decimal("1"),
                       beleg_id=v.beleg_id, immutable=False)
    db.add(e)
    db.commit()
    delete_anhang(e.id, db)
    assert db.query(Beleg).filter(Beleg.id == v.beleg_id).count() == 1
    assert (tmp_path / "uploads" / "belege" / "vertrag123.pdf").exists()
