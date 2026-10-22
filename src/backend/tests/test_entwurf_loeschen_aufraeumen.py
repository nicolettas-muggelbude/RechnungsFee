"""
Entwurf löschen räumt alles auf, was nur zu ihm gehört: Beleganhang, ZUGFeRD-Zusatzanhänge
(jeweils Datensatz + Datei + PDF/A-Fassung) und ein bereits gespeichertes Original-PDF.
Vorher blieben diese als verwaister Datenmüll zurück - und blockierten über den
SHA-256-Dublettenschutz z. B. einen erneuten Import aus dem Rechnungspostfach (Issue #451).
Ein Beleg, den noch ein anderer Datensatz verwendet, bleibt erhalten.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.rechnungen as rechnungen_api
from database.connection import Base
from database.models import Beleg, Journaleintrag, Rechnung, RechnungZugferdAnhang


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(rechnungen_api, "APP_DATA_DIR", tmp_path)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session, tmp_path
    session.close()


def _beleg(db, basis, name: str, mit_pdfa: bool = True) -> Beleg:
    rel = f"belege/2026/10/{name}"
    (basis / "uploads" / rel).parent.mkdir(parents=True, exist_ok=True)
    (basis / "uploads" / rel).write_bytes(b"%PDF")
    pdfa = None
    if mit_pdfa:
        pdfa = rel.replace(".pdf", "_pdfa.pdf")
        (basis / "uploads" / pdfa).write_bytes(b"%PDF-A")
    b = Beleg(dateiname=rel, original_name=name, sha256=name, beleg_pdfa_pfad=pdfa)
    db.add(b)
    db.flush()
    return b


def _entwurf(db, **kw) -> Rechnung:
    r = Rechnung(typ="eingang", datum=date(2026, 10, 1), ist_entwurf=True, partner_freitext="X", **kw)
    db.add(r)
    db.flush()
    return r


def test_entwurf_loeschen_entfernt_beleg_samt_dateien(db):
    session, basis = db
    b = _beleg(session, basis, "re.pdf")
    r = _entwurf(session, beleg_id=b.id)
    session.commit()

    rechnungen_api.delete_rechnung(r.id, session)

    assert session.query(Beleg).count() == 0
    assert not list((basis / "uploads").rglob("*.pdf"))


def test_zugferd_anhaenge_und_original_pdf_werden_entfernt(db):
    session, basis = db
    anhang = _beleg(session, basis, "stundennachweis.pdf", mit_pdfa=False)
    (basis / "originale").mkdir()
    (basis / "originale" / "orig.pdf").write_bytes(b"%PDF")
    r = _entwurf(session, original_pdf_pfad="originale/orig.pdf")
    session.add(RechnungZugferdAnhang(rechnung_id=r.id, beleg_id=anhang.id))
    session.commit()

    rechnungen_api.delete_rechnung(r.id, session)

    assert session.query(Beleg).count() == 0
    assert session.query(RechnungZugferdAnhang).count() == 0
    assert not (basis / "originale" / "orig.pdf").exists()
    assert not list((basis / "uploads").rglob("*.pdf"))


def test_beleg_der_noch_verwendet_wird_bleibt(db):
    session, basis = db
    b = _beleg(session, basis, "geteilt.pdf")
    r = _entwurf(session, beleg_id=b.id)
    session.add(Journaleintrag(
        datum=date(2026, 10, 1), belegnr="J-1", beschreibung="Buchung mit demselben Beleg",
        zahlungsart="Bank", art="Ausgabe", netto_betrag=1, ust_satz=0, ust_betrag=0, brutto_betrag=1,
        vorsteuerabzug=False, beleg_id=b.id,
    ))
    session.commit()

    rechnungen_api.delete_rechnung(r.id, session)

    assert session.query(Rechnung).count() == 0
    assert session.query(Beleg).count() == 1
    assert (basis / "uploads" / b.dateiname).exists()


def test_einzelnen_zugferd_anhang_entfernen_loescht_auch_pdfa(db):
    session, basis = db
    anhang = _beleg(session, basis, "vertrag.pdf", mit_pdfa=True)
    r = _entwurf(session)
    za = RechnungZugferdAnhang(rechnung_id=r.id, beleg_id=anhang.id)
    session.add(za)
    session.commit()

    rechnungen_api.delete_zugferd_anhang(r.id, za.id, session)

    assert session.query(Beleg).count() == 0
    assert not list((basis / "uploads").rglob("*.pdf"))   # Original UND PDF/A weg


def test_buchungsvorlage_loeschen_entfernt_ihren_beleg(db, monkeypatch):
    from decimal import Decimal
    import api.buchungsvorlagen as bv_api
    from database.models import Buchungsvorlage

    session, basis = db
    beleg_dir = basis / "uploads" / "belege"
    monkeypatch.setattr(bv_api, "BELEG_DIR", beleg_dir)
    beleg_dir.mkdir(parents=True)
    (beleg_dir / "mietvertrag.pdf").write_bytes(b"%PDF")   # Buchungsvorlagen: relativ zu BELEG_DIR
    b = Beleg(dateiname="mietvertrag.pdf", original_name="Mietvertrag.pdf", sha256="mv")
    session.add(b)
    session.flush()
    v = Buchungsvorlage(
        bezeichnung="Büromiete", betrag=Decimal("500.00"), ist_brutto=True, ust_satz=Decimal("19"),
        intervall="monatlich", naechstes_datum=date(2026, 1, 1), modus="direkt", art="Ausgabe", beleg_id=b.id,
    )
    session.add(v)
    session.commit()

    bv_api.loesche_vorlage(v.id, session)

    assert session.query(Buchungsvorlage).count() == 0
    assert session.query(Beleg).count() == 0
    assert not (beleg_dir / "mietvertrag.pdf").exists()


def test_entwurf_ohne_anhang_unveraendert_loeschbar(db):
    session, _ = db
    r = _entwurf(session)
    session.commit()
    rechnungen_api.delete_rechnung(r.id, session)
    assert session.query(Rechnung).count() == 0
