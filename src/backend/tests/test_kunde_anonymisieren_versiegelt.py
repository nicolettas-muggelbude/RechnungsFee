"""
Nebenfund Issue #566: „Anonymisieren“ eines Kunden scheiterte mit IntegrityError (FOREIGN KEY),
sobald versiegelte Journalbuchungen auf ihn verwiesen - journal.kunde_id hat einen Fremdschlüssel,
versiegelte Zeilen lassen sich nicht ändern. Jetzt bleibt der Datensatz als leere Hülle stehen
(alle personenbezogenen Daten entfernt, deaktiviert). Ohne versiegelte Buchungen wird er wie
bisher gelöscht - auch wenn Rechnungen auf eine Lieferadresse zeigen.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import api.kunden as kunden_mod
from api.kunden import anonymisiere_kunde
from database.connection import Base
from database.models import Beleg, Journaleintrag, Kunde, KundeBeleg, KundeLieferadresse, Rechnung


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(kunden_mod, "APP_DATA_DIR", tmp_path)
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _kunde(db, tmp_path) -> Kunde:
    k = Kunde(firmenname="Muster GmbH", vorname="Max", nachname="Muster", strasse="Weg", hausnummer="1",
              plz="12345", ort="Ort", email="max@example.org", telefon="0123", notizen="privat")
    db.add(k)
    db.flush()
    adresse = KundeLieferadresse(kunde_id=k.id, name="Filiale", strasse="Gasse", plz="12345", ort="Ort")
    db.add(adresse)
    datei = tmp_path / "uploads" / "belege" / "vertrag.pdf"
    datei.parent.mkdir(parents=True)
    datei.write_bytes(b"%PDF")
    beleg = Beleg(dateiname="belege/vertrag.pdf", original_name="vertrag.pdf", mime_type="application/pdf",
                  dateigroesse=4)
    db.add(beleg)
    db.flush()
    db.add(KundeBeleg(kunde_id=k.id, beleg_id=beleg.id, bezeichnung="Vertrag"))
    db.add(Rechnung(typ="ausgang", datum=date(2026, 1, 1), kunde_id=k.id, lieferadresse_id=adresse.id))
    db.commit()
    return k


def _buchung(db, kunde_id):
    db.add(Journaleintrag(datum=date(2026, 1, 1), belegnr="260001", beschreibung="Zahlung", kunde_id=kunde_id,
                          zahlungsart="Bank", art="Einnahme", netto_betrag=Decimal("1"),
                          brutto_betrag=Decimal("1"), immutable=True))
    db.commit()


def test_mit_versiegelter_buchung_wird_geleert(db, tmp_path):
    k = _kunde(db, tmp_path)
    _buchung(db, k.id)
    erg = anonymisiere_kunde(k.id, db)
    assert erg["unveraenderlich_verblieben"] == 1
    k = db.query(Kunde).one()
    assert (k.firmenname, k.vorname, k.nachname, k.email, k.notizen, k.aktiv) == (
        f"Anonymisierter Kunde #{k.id}", None, None, None, None, False)
    a = db.query(KundeLieferadresse).one()
    assert (a.name, a.strasse) == (None, None)
    assert db.query(KundeBeleg).count() == 0 and db.query(Beleg).count() == 0
    assert not (tmp_path / "uploads" / "belege" / "vertrag.pdf").exists()


def test_ohne_versiegelte_buchung_wird_geloescht(db, tmp_path):
    k = _kunde(db, tmp_path)
    anonymisiere_kunde(k.id, db)
    assert db.query(Kunde).count() == 0
    r = db.query(Rechnung).one()
    assert (r.kunde_id, r.lieferadresse_id, r.partner_freitext) == (None, None, "Muster GmbH Max Muster")
