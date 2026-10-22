"""
Issue #459: §13b-Eingangsrechnungen (z. B. Provision einer EU-Buchungsplattform).

Der ausländische Lieferant weist keine deutsche USt aus - Rechnungs- und Zahlbetrag sind der
Nettobetrag, die USt schuldet der Leistungsempfänger selbst (§13b UStG). Bisher:
- mit 0 % erfasst (wie auf der Rechnung): USt fehlte ganz (KZ 47 = 0),
- mit 19 % erfasst: Rechnungsbetrag 119 € statt 100 €, die Zahlungsbuchung schlug auf die
  119 € noch einmal 19 % auf, EÜR zu hoch.
Kleinunternehmer schulden die §13b-Steuer ebenfalls, haben aber keinen Vorsteuerabzug - die
freie Journalbuchung setzte ihn trotzdem.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import _berechne_euer
from api.journal import create_eintrag
from api.rechnungen import create_rechnung, finalisiere_rechnung, rechnung_vorschau, zahlung_bar_erstellen
from api.schemas import JournalEintragCreate
from api.schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate, RechnungVorschauRequest
from api.ustva import _berechne_kz
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, Unternehmen, VorsteuerAnspruch


@pytest.fixture(params=[False, True], ids=["regel", "kleinunternehmer"])
def db(request, monkeypatch):
    import api.rechnungen as rechnungen_api
    import api.ustva as ustva_api
    monkeypatch.setattr(rechnungen_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    monkeypatch.setattr(ustva_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Ferienwohnung", strasse="X", hausnummer="1", plz="12345", ort="Y",
                            ist_kleinunternehmer=request.param))
    session.add(Kategorie(name="EU-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand", konto_skr03="3123",
                          konto_skr04="5923", vorsteuer_prozent=100, ust_satz_standard=19,
                          ust_sonderfall="13b_abs1", euer_zeile=60))
    session.commit()
    session.ist_ku = request.param
    yield session
    session.close()


def _kat(db) -> Kategorie:
    return db.query(Kategorie).one()


def _provision(db, satz: str) -> Rechnung:
    kat = _kat(db)
    resp = create_rechnung(RechnungCreate(
        typ="eingang", datum=date(2026, 8, 5), kategorie_id=kat.id, partner_freitext="Plattform Ireland Ltd.",
        positionen=[RechnungspositionCreate(beschreibung="Provision", netto=Decimal("100"),
                                            ust_satz=Decimal(satz), kategorie_id=kat.id)],
    ), db)
    finalisiere_rechnung(resp.id, db)
    return db.query(Rechnung).filter(Rechnung.id == resp.id).one()


@pytest.mark.parametrize("satz", ["0", "19"])
def test_rechnungsbetrag_ist_nettobetrag_und_ust_laeuft_nebenher(db, satz):
    rechnung = _provision(db, satz)
    assert rechnung.brutto_gesamt == Decimal("100.00")  # offener Posten = tatsächlich zu zahlen
    assert rechnung.netto_gesamt == Decimal("100.00")
    va = db.query(VorsteuerAnspruch).one()
    assert va.ust_satz == Decimal("19.00")  # 0 % auf der Lieferantenrechnung → Standardsatz der Kategorie
    assert va.netto_betrag == Decimal("100.00")
    assert va.ust_betrag == Decimal("19.00")
    assert va.vorsteuer_betrag == (Decimal("0.00") if db.ist_ku else Decimal("19.00"))


@pytest.mark.parametrize("satz", ["0", "19"])
def test_zahlung_ustva_und_euer(db, satz):
    rechnung = _provision(db, satz)
    zahlung_bar_erstellen(rechnung.id, BarZahlungCreate(datum=date(2026, 9, 2), zahlungsart="Bank"), db)
    db.refresh(rechnung)
    assert rechnung.zahlungsstatus == "bezahlt"
    zahlung = db.query(Journaleintrag).one()
    assert zahlung.brutto_betrag == Decimal("100.00")
    assert zahlung.ust_betrag == Decimal("19.00")

    # Steuer entsteht im Monat der Rechnung, unabhängig von der Zahlung im Folgemonat
    kz_aug, _ = _berechne_kz(date(2026, 8, 1), date(2026, 8, 31), db)
    assert kz_aug["kz_46"] == Decimal("100.00")
    assert kz_aug["kz_47"] == Decimal("19.00")
    assert kz_aug["kz_67"] == (Decimal("0.00") if db.ist_ku else Decimal("19.00"))
    kz_sep, _ = _berechne_kz(date(2026, 9, 1), date(2026, 9, 30), db)
    assert kz_sep["kz_46"] == Decimal("0.00") and kz_sep["kz_47"] == Decimal("0.00")

    # EÜR: nur die gezahlte Provision; die §13b-USt wird erst bei Zahlung ans FA Betriebsausgabe
    assert _berechne_euer(2026, db)["zeilen"] == {60: Decimal("100.00")}


def test_vorschau_zeigt_nettobetrag(db):
    kat = _kat(db)
    vorschau = rechnung_vorschau(RechnungVorschauRequest(
        typ="eingang", kategorie_id=kat.id,
        positionen=[RechnungspositionCreate(beschreibung="Provision", netto=Decimal("100"), ust_satz=Decimal("19"))],
    ), db)
    assert vorschau.brutto_gesamt == Decimal("100.00")
    assert vorschau.ust_gesamt == Decimal("0.00")


def test_normale_eingangsrechnung_unveraendert(db):
    kat = Kategorie(name="Bürobedarf", kontenart="Aufwand", konto_skr03="4930", konto_skr04="6815",
                    vorsteuer_prozent=100, ust_satz_standard=19, euer_zeile=60)
    db.add(kat)
    db.commit()
    resp = create_rechnung(RechnungCreate(
        typ="eingang", datum=date(2026, 8, 5), kategorie_id=kat.id, partner_freitext="Händler GmbH",
        positionen=[RechnungspositionCreate(beschreibung="Papier", netto=Decimal("100"), ust_satz=Decimal("19"))],
    ), db)
    assert resp.brutto_gesamt == Decimal("119.00")


def test_freie_journalbuchung_kleinunternehmer_ohne_vorsteuer(db):
    eintrag = create_eintrag(JournalEintragCreate(
        datum=date(2026, 8, 5), beschreibung="Provision", kategorie_id=_kat(db).id, art="Ausgabe",
        brutto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), vorsteuerabzug=True,
        ust_sonderfall="13b_abs1", zahlungsart="Bank",
    ), db)
    j = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag.id).one()
    assert j.brutto_betrag == Decimal("100.00") and j.ust_betrag == Decimal("19.00")
    assert j.vorsteuer_betrag == (Decimal("0.00") if db.ist_ku else Decimal("19.00"))
    kz, _ = _berechne_kz(date(2026, 8, 1), date(2026, 8, 31), db)
    assert kz["kz_47"] == Decimal("19.00")
    assert kz["kz_67"] == (Decimal("0.00") if db.ist_ku else Decimal("19.00"))


# ---------------------------------------------------------------------------
# UStVA für Kleinunternehmer: nur §13b/ig. Erwerb, ohne Vorsteuer (§18 Abs. 4a UStG)
# ---------------------------------------------------------------------------

def test_ustva_kleinunternehmer_mit_13b(db):
    from api.ustva import jahresumsatzsteuer, ku_pruefen, ustva_berechnen, ustva_posten
    _provision(db, "0")
    ergebnis = ustva_berechnen("2026-08", db=db)
    assert ergebnis.befreit is False
    assert ergebnis.kz_46 == Decimal("100.00") and ergebnis.kz_47 == Decimal("19.00")
    if db.ist_ku:
        assert ergebnis.kz_67 == Decimal("0.00")
        assert ergebnis.zahllast == Decimal("19.00")
        assert ergebnis.hinweis and "§18 Abs. 4a" in ergebnis.hinweis
        assert ku_pruefen(db=db).hat_reverse_charge is True
        assert jahresumsatzsteuer(2026, db=db).kz_47 == Decimal("19.00")
        assert ustva_posten("2026-08", "66", db=db) == []
    else:
        assert ergebnis.zahllast == Decimal("0.00")


def test_ustva_kleinunternehmer_ohne_13b_bleibt_befreit(db):
    from fastapi import HTTPException
    from api.ustva import ku_pruefen, ustva_berechnen, ustva_xml
    if not db.ist_ku:
        pytest.skip("nur Kleinunternehmer")
    ergebnis = ustva_berechnen("2026-08", db=db)
    assert ergebnis.befreit is True
    assert ku_pruefen(db=db).hat_reverse_charge is False
    with pytest.raises(HTTPException) as exc:
        ustva_xml("2026-08", db=db)
    assert exc.value.status_code == 422


def test_ustva_kleinunternehmer_eigene_umsaetze_nicht_gemeldet(db):
    """Eigene Ausgangsumsätze eines Kleinunternehmers gehören nicht in die Voranmeldung."""
    from api.ustva import ustva_berechnen
    if not db.ist_ku:
        pytest.skip("nur Kleinunternehmer")
    _provision(db, "19")
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 8, 10), partner_freitext="Gast",
        positionen=[RechnungspositionCreate(beschreibung="Übernachtung", netto=Decimal("500"), ust_satz=Decimal("0"))],
    ), db)
    finalisiere_rechnung(resp.id, db)
    ergebnis = ustva_berechnen("2026-08", db=db)
    assert ergebnis.kz_81 == Decimal("0.00") and ergebnis.kz_86 == Decimal("0.00")
    assert ergebnis.zahllast == Decimal("19.00")


def test_lieferantengutschrift_korrigiert_13b_im_gutschriftsmonat(db):
    """Vollständige Gutschrift einer §13b-Provision in einem späteren Zeitraum: Betrag = −Netto,
    die Steuer wird im Monat der Gutschrift berichtigt, der Ursprungsmonat bleibt unverändert."""
    from api.rechnungen import create_gutschrift
    kat = _kat(db)
    resp = create_rechnung(RechnungCreate(
        typ="eingang", datum=date(2026, 1, 10), kategorie_id=kat.id, partner_freitext="Plattform",
        positionen=[RechnungspositionCreate(beschreibung="Provision", netto=Decimal("100"), ust_satz=Decimal("0"))],
    ), db)
    finalisiere_rechnung(resp.id, db)
    zahlung_bar_erstellen(resp.id, BarZahlungCreate(datum=date(2026, 2, 2), zahlungsart="Bank"), db)

    gutschrift = db.query(Rechnung).filter(Rechnung.id == create_gutschrift(resp.id, db).id).one()
    assert gutschrift.brutto_gesamt == Decimal("-100.00")
    gutschrift.datum = date(2026, 10, 12)
    db.commit()
    finalisiere_rechnung(gutschrift.id, db)
    zahlung_bar_erstellen(gutschrift.id, BarZahlungCreate(datum=date(2026, 10, 15), zahlungsart="Bank"), db)

    kz_jan, _ = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)
    kz_okt, _ = _berechne_kz(date(2026, 10, 1), date(2026, 10, 31), db)
    assert (kz_jan["kz_46"], kz_jan["kz_47"]) == (Decimal("100.00"), Decimal("19.00"))
    assert (kz_okt["kz_46"], kz_okt["kz_47"]) == (Decimal("-100.00"), Decimal("-19.00"))
    assert kz_okt["kz_67"] == (Decimal("0.00") if db.ist_ku else Decimal("-19.00"))
    assert _berechne_euer(2026, db)["zeilen"].get(60, Decimal("0")) == Decimal("0")
