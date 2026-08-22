"""
Regressionstest fuer einen beim Umsetzen von Issue #366 (Gutschrift-Verrechnung) gefundenen
Bestandsfehler in forderung_verrechnen(): Ein Kundenguthaben (z.B. aus einer Ueberzahlung),
das gegen eine offene Ausgangsrechnung verrechnet wird, wurde bisher OHNE Kategorie/Erloeskonto
gebucht - Ausgangsrechnungen fuehren nie ein eigenes kategorie_id je Position (siehe Kommentar
in zahlung_bar_erstellen: "keine UI dafuer"), wodurch der bisherige kat_gruppen-Fallback immer
auf kat_id=None lief. Die USt selbst war davon nicht betroffen (UStVA blieb korrekt), aber die
Buchung fehlte in EUER-Berechnung und DATEV-Export.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.forderungen import forderung_verrechnen, VerrechnenRequest
from database.connection import Base
from database.models import Forderung, Kategorie, Rechnung, Rechnungsposition, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.add(Kategorie(
        name="Betriebseinnahmen", kontenart="Erlös", konto_skr03="8400", konto_skr04="4400",
        vorsteuer_prozent=0, ust_satz_standard=19,
    ))
    session.commit()
    yield session
    session.close()


def _offene_ausgangsrechnung(db, betrag_netto="200.00", satz="19") -> Rechnung:
    netto = Decimal(betrag_netto)
    ust = (netto * Decimal(satz) / 100).quantize(Decimal("0.01"))
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2026-9", datum=date(2026, 6, 1),
        brutto_gesamt=netto + ust, netto_gesamt=netto, ust_gesamt=ust,
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
    )
    db.add(rechnung)
    db.flush()
    # Realistischer Fall: Ausgangsrechnungs-Position OHNE eigene Kategorie (keine UI dafuer) -
    # genau der Fall, der den Bug ausgeloest hat.
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"),
        einheit="Stk.", netto=netto, ust_satz=Decimal(satz), ust_betrag=ust, brutto=netto + ust,
        kategorie_id=None,
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_kundenguthaben_verrechnung_setzt_erloes_kategorie(db):
    rechnung = _offene_ausgangsrechnung(db)
    guthaben = Forderung(typ="kundenguthaben", betrag=Decimal("50.00"), partner_typ="kunde", partner_id=None)
    db.add(guthaben)
    db.commit()
    db.refresh(guthaben)

    ergebnis = forderung_verrechnen(guthaben.id, VerrechnenRequest(rechnung_id=rechnung.id), db)

    assert ergebnis.status == "ausgeglichen"
    eintrag = rechnung.journaleintraege[0]
    assert eintrag.kategorie_id is not None
    kat = db.query(Kategorie).filter(Kategorie.id == eintrag.kategorie_id).first()
    assert kat.name == "Betriebseinnahmen"
    assert eintrag.konto_skr03 == "8400"
    assert eintrag.konto_skr04 == "4400"
