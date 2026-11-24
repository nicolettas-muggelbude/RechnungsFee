"""
Issue #600: In der Schlussrechnung müssen bei verrechneten Abschlagsrechnungen das gezahlte
Entgelt UND der darauf entfallende Steuerbetrag abgesetzt werden (§ 14 Abs. 5 Satz 2 UStG,
UStAE 14.8 Abs. 7). Bisher stand die Abzugszeile mit Steuersatz, aber ohne Steuerbetrag in der
Positionstabelle, der Summenblock zeigte nur den Rest. Jetzt: Leistung gesamt (netto/USt/brutto),
je Abschlag Bruttoabzug mit darin enthaltenem Netto und USt, dann Restbetrag. Beide Vorlagen,
Netto- und Bruttorechnung, Kleinunternehmer ohne Steuerzeilen.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Rechnung, Rechnungsposition
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_base import abschlag_abzuege
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1

D = Decimal
UNT = {"firmenname": "T", "strasse": "S", "hausnummer": "1", "plz": "12345", "ort": "O",
       "steuernummer": "12/345/67890", "ist_kleinunternehmer": False}


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _schluss(db, ust=True, zweiter_abschlag=False, unbezahlt=False):
    satz = D("19") if ust else D("0")
    f = D("0.19") if ust else D("0")
    abschlaege = []
    for i, (nr, tag) in enumerate([("AR-260001", 1), ("AR-260002", 15)][: 2 if zweiter_abschlag else 1]):
        a = Rechnung(typ="ausgang", dokument_typ="Abschlagsrechnung", rechnungsnummer=nr,
                     datum=date(2026, 10, tag), netto_gesamt=D("250"), ust_gesamt=D("250") * f,
                     brutto_gesamt=D("250") * (1 + f), ist_entwurf=False)
        db.add(a)
        db.flush()
        abschlaege.append(a)
    abz_netto = D("500") if not zweiter_abschlag else D("250")
    rest_netto = D("1000") - abz_netto * len(abschlaege)
    r = Rechnung(typ="ausgang", dokument_typ="Rechnung", rechnungsnummer="RE-1", datum=date(2026, 11, 20),
                 partner_freitext="Kunde", netto_gesamt=rest_netto, ust_gesamt=rest_netto * f,
                 brutto_gesamt=rest_netto * (1 + f), ist_entwurf=False)
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(rechnung_id=r.id, position_nr=1, beschreibung="Gartenarbeiten", menge=D("1"),
                             einheit="Pauschal", netto=D("1000"), ust_satz=satz, ust_betrag=D("1000") * f,
                             brutto=D("1000") * (1 + f)))
    for i, a in enumerate(abschlaege, start=2):
        db.add(Rechnungsposition(rechnung_id=r.id, position_nr=i, beschreibung=f"Abschlag {a.rechnungsnummer}",
                                 menge=D("-1"), einheit="Pauschal", netto=abz_netto, ust_satz=satz,
                                 ust_betrag=-abz_netto * f, brutto=-abz_netto * (1 + f),
                                 abschlag_rechnung_id=a.id))
    if unbezahlt:
        a = Rechnung(typ="ausgang", dokument_typ="Abschlagsrechnung", rechnungsnummer="AR-260009",
                     datum=date(2026, 11, 1), netto_gesamt=D("100"), ust_gesamt=D("0"), brutto_gesamt=D("100"),
                     ist_entwurf=False)
        db.add(a)
        db.flush()
        db.add(Rechnungsposition(rechnung_id=r.id, position_nr=9, beschreibung="AR-260009 (noch nicht bezahlt)",
                                 menge=D("0"), einheit="Pauschal", netto=D("0"), ust_satz=satz,
                                 ust_betrag=D("0"), brutto=D("0"), abschlag_rechnung_id=a.id))
    db.commit()
    db.refresh(r)
    return r


def _text(r, unt, erzeuge, ist_netto):
    pdf = erzeuge(r, unt, ist_netto=ist_netto)
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)


def test_abzuege_je_abschlag(db):
    r = _schluss(db, zweiter_abschlag=True, unbezahlt=True)
    abz = abschlag_abzuege(r.positionen)
    assert [a["bezeichnung"] for a in abz] == [
        "Abschlagsrechnung AR-260001 vom 01.10.2026", "Abschlagsrechnung AR-260002 vom 15.10.2026"]
    assert abz[0]["netto"] == D("250") and abz[0]["ust"] == D("47.50") and abz[0]["brutto"] == D("297.50")
    assert abz[0]["ust_je_satz"] == [(D("19"), D("47.50"))]


@pytest.mark.parametrize("erzeuge", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
@pytest.mark.parametrize("ist_netto", [True, False])
def test_summenblock_zeigt_steuer_des_abzugs(db, erzeuge, ist_netto):
    t = _text(_schluss(db), UNT, erzeuge, ist_netto)
    assert "Leistung gesamt netto" in t and "1.000,00" in t
    assert "zzgl. USt 19 %" in t and "190,00" in t
    assert "Gesamtbetrag der Leistung" in t and "1.190,00" in t
    assert "abzgl. Abschlagsrechnung AR-260001 vom 01.10.2026" in t and "-595,00" in t
    assert "darin netto 500,00 € · USt 19 % 95,00 €" in t
    assert "Restbetrag netto" in t and "Zu zahlen" in t
    # Abzugszeile steht nicht mehr in der Positionstabelle
    assert "Abschlag AR-260001\n" not in t and "-1" not in t.split("Gartenarbeiten")[0][-20:]


@pytest.mark.parametrize("erzeuge", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
def test_kleinunternehmer_ohne_steuerzeilen(db, erzeuge):
    t = _text(_schluss(db, ust=False), {**UNT, "ist_kleinunternehmer": True}, erzeuge, False)
    assert "abzgl. Abschlagsrechnung AR-260001" in t and "-500,00" in t
    assert "Zu zahlen" in t and "zzgl. USt" not in t and "Restbetrag netto" not in t and "darin" not in t


@pytest.mark.parametrize("erzeuge", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
def test_ohne_abschlag_unveraendert(db, erzeuge):
    r = _schluss(db)
    for p in list(r.positionen):
        if p.abschlag_rechnung_id:
            db.delete(p)
    r.netto_gesamt, r.ust_gesamt, r.brutto_gesamt = D("1000"), D("190"), D("1190")
    db.commit()
    db.refresh(r)
    t = _text(r, UNT, erzeuge, True)
    assert "Gesamtbetrag" in t and "Leistung gesamt" not in t and "Zu zahlen" not in t
