"""
Aufschlüsselung der EÜR: Einzelposten je Kategorie mit Rechnungs- und Zahlungsnummer.

Die Kategorie-Aufschlüsselung (/euer/kategorien) liefert je Kategorie die zugrunde liegenden
Journalbuchungen - mit Rechnungsnummer + rechnung_id (Link auf die Rechnung) und Belegnr der
Zahlungsbuchung (Link auf den Zahlungsbeleg). Die EÜR ist nach Ist-Versteuerung berechnet:
die "Zahlungsnummer" ist die Belegnummer der Journalbuchung (Zahlungsdatum).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import _berechne_euer_kategorien, euer_kategorien
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test", strasse="X", hausnummer="1", plz="12345", ort="Y",
                            ist_kleinunternehmer=False))
    session.add(Kategorie(name="Warenverkauf", kontenart="Erlös", konto_skr03="8400",
                          konto_skr04="4400", euer_zeile=15, ust_satz_standard=19))
    session.add(Kategorie(name="Bürobedarf", kontenart="Aufwand", konto_skr03="4925",
                          konto_skr04="6820", euer_zeile=51, ust_satz_standard=19))
    session.add(Kategorie(name="Wareneinkauf", kontenart="Aufwand", konto_skr03="3400",
                          konto_skr04="5400", euer_zeile=51, ust_satz_standard=19,
                          vorsteuer_prozent=0))
    session.commit()
    yield session
    session.close()


def _rechnung(db, nummer: str) -> Rechnung:
    r = Rechnung(typ="ausgang", rechnungsnummer=nummer, datum=date(2025, 2, 1),
                 netto_gesamt=Decimal("0.00"), ust_gesamt=Decimal("0.00"),
                 brutto_gesamt=Decimal("0.00"), ist_entwurf=False)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_kategorie_buchungen_mit_rechnungs_und_zahlungsnummer(db):
    """Einnahme mit Rechnungsverknüpfung: Einzelposten zeigt Belegnr. (Zahlung) und Rechnungsnummer."""
    rechnung = _rechnung(db, "RE-2025-0001")
    kat = db.query(Kategorie).filter_by(name="Warenverkauf").one()
    db.add(Journaleintrag(
        datum=date(2025, 2, 10), belegnr="2500010", beschreibung="Zahlung RE-2025-0001",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("1000.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("190.00"),
        brutto_betrag=Decimal("1190.00"), rechnung_id=rechnung.id,
    ))
    db.commit()

    detail = euer_kategorien(2025, db=db)
    zeile15 = next(z for z in detail.zeilen if z.zeile == 15)
    kat_summe = zeile15.kategorien[0]

    assert kat_summe.betrag == Decimal("1000.00")
    assert len(kat_summe.buchungen) == 1
    b = kat_summe.buchungen[0]
    assert b.belegnr == "2500010"                    # Zahlungsnummer (Journalbuchung)
    assert b.rechnungsnummer == "RE-2025-0001"       # Rechnungsnummer
    assert b.rechnung_id == rechnung.id              # Link-Ziel
    assert b.betrag == Decimal("1000.00")


def test_kategorie_buchungen_sortiert_und_ohne_link_ohne_rechnung(db):
    """Ohne Rechnungsverknüpfung bleibt rechnungsnummer leer; Sortierung nach Datum/Belegnr."""
    kat = db.query(Kategorie).filter_by(name="Warenverkauf").one()
    db.add(Journaleintrag(
        datum=date(2025, 3, 5), belegnr="2500020", beschreibung="Bar-Zahlung",
        kategorie_id=kat.id, zahlungsart="Bar", art="Einnahme",
        netto_betrag=Decimal("200.00"), brutto_betrag=Decimal("200.00"),
    ))
    db.add(Journaleintrag(
        datum=date(2025, 1, 15), belegnr="2500005", beschreibung="Anzahlung",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("300.00"), brutto_betrag=Decimal("300.00"),
    ))
    db.commit()

    detail = euer_kategorien(2025, db=db)
    kat_summe = next(z for z in detail.zeilen if z.zeile == 15).kategorien[0]

    assert [(b.belegnr, b.rechnungsnummer) for b in kat_summe.buchungen] == [
        ("2500005", None), ("2500020", None),
    ]
    # Summe der Einzelposten = Kategorie-Summe
    assert sum(b.betrag for b in kat_summe.buchungen) == kat_summe.betrag


def test_vorsteuer_getrennt_je_buchung(db):
    """Ausgabe mit Vorsteuer: Netto-Anteil unter der Kategorie, Vorsteuer-Anteil unter Zeile 57 -
    beide Einzelposten tragen dieselbe Zahlungsnummer (Belegnr)."""
    kat = db.query(Kategorie).filter_by(name="Bürobedarf").one()
    db.add(Journaleintrag(
        datum=date(2025, 4, 2), belegnr="2500030", beschreibung="Büromaterial",
        kategorie_id=kat.id, zahlungsart="Karte", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        vorsteuerabzug=True, vorsteuer_betrag=Decimal("19.00"), brutto_betrag=Decimal("119.00"),
    ))
    db.commit()

    detail = euer_kategorien(2025, db=db)
    zeile51 = next(z for z in detail.zeilen if z.zeile == 51)
    zeile57 = next(z for z in detail.zeilen if z.zeile == 57)

    assert zeile51.kategorien[0].betrag == Decimal("100.00")
    assert zeile51.kategorien[0].buchungen[0].belegnr == "2500030"
    assert zeile57.kategorien[0].name == "Vorsteuer"
    assert zeile57.kategorien[0].betrag == Decimal("19.00")
    assert zeile57.kategorien[0].buchungen[0].belegnr == "2500030"


def test_kategorie_summen_ohne_beitraege_unverändert(db):
    """Regression: _berechne_euer_kategorien liefert weiterhin nur die Summen (bestehende Tests)."""
    kat = db.query(Kategorie).filter_by(name="Warenverkauf").one()
    rechnung = _rechnung(db, "RE-2025-0002")
    db.add(Journaleintrag(
        datum=date(2025, 5, 1), belegnr="2500040", beschreibung="Zahlung RE-2025-0002",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("500.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("95.00"),
        brutto_betrag=Decimal("595.00"), rechnung_id=rechnung.id,
    ))
    db.commit()

    erg = _berechne_euer_kategorien(2025, db)
    assert erg[15]["Warenverkauf"] == Decimal("500.00")
    # USt des Zahlungseingangs zusätzlich in Zeile 17
    assert erg[17]["Umsatzsteuer"] == Decimal("95.00")


def test_storno_zahlung_ust_zeile_17_ohne_ust_konto(db):
    """Zahlungen auf Rechnungen haben kein USt-Konto - ihr Storno (art=Ausgabe, "STORNO "-Präfix)
    muss die vereinnahmte USt (Zeile 17) trotzdem abziehen. Sonst bleibt nach einem
    Zahlungs-Storno eine USt stehen, die nie vereinnahmt wurde."""
    kat = db.query(Kategorie).filter_by(name="Warenverkauf").one()
    db.add(Journaleintrag(
        datum=date(2025, 2, 10), belegnr="2500050", beschreibung="Zahlung RE-2025-0003",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("1000.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("190.00"),
        brutto_betrag=Decimal("1190.00"),
    ))
    # Zweite, nicht stornierte Zahlung - hält die Zeilen sichtbar (Summe ungleich 0)
    db.add(Journaleintrag(
        datum=date(2025, 2, 15), belegnr="2500052", beschreibung="Zahlung RE-2025-0004",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("500.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("95.00"),
        brutto_betrag=Decimal("595.00"),
    ))
    # Storno-Gegenbuchung, exakt wie von journal.storno/rechnungen.storno erzeugt:
    # art gespiegelt (Ausgabe), Beträge positiv, KEIN USt-Konto (wie das Original).
    db.add(Journaleintrag(
        datum=date(2025, 3, 5), belegnr="2500051", beschreibung="STORNO 2500050: RE-2025-0003 – Widerruf",
        kategorie_id=kat.id, zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("1000.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("190.00"),
        brutto_betrag=Decimal("1190.00"), immutable=True,
    ))
    db.commit()

    detail = euer_kategorien(2025, db=db)

    # Zeile 15 (Einnahmen): 500 verbleibt; Einzelposten zeigen Original + Storno + Rest
    zeile15 = next(z for z in detail.zeilen if z.zeile == 15)
    assert zeile15.betrag_gesamt == Decimal("500.00")
    posten15 = {b.belegnr: b.betrag for k in zeile15.kategorien for b in k.buchungen}
    assert posten15 == {"2500050": Decimal("1000.00"), "2500051": Decimal("-1000.00"),
                        "2500052": Decimal("500.00")}

    # Zeile 17 (vereinnahmte USt): 95 verbleibt (190 + 95 - 190); das Storno zieht seine 190 ab
    zeile17 = next(z for z in detail.zeilen if z.zeile == 17)
    assert zeile17.betrag_gesamt == Decimal("95.00")
    posten17 = {b.belegnr: b.betrag for k in zeile17.kategorien for b in k.buchungen}
    assert posten17 == {"2500050": Decimal("190.00"), "2500051": Decimal("-190.00"),
                        "2500052": Decimal("95.00")}

    # Summenfunktion identisch
    from api.euer import _berechne_euer
    assert _berechne_euer(2025, db)["zeilen"].get(17) == Decimal("95.00")


def test_storno_zahlung_ust_zeile_17_mit_ust_konto(db):
    """Storno einer manuellen Einnahme mit Einnahme-USt-Konto (1776): bestehender Zweig,
    darf durch den Fix nicht beeinträchtigt werden."""
    kat = db.query(Kategorie).filter_by(name="Warenverkauf").one()
    db.add(Journaleintrag(
        datum=date(2025, 2, 10), belegnr="2500060", beschreibung="Bar-Einnahme",
        kategorie_id=kat.id, zahlungsart="Bar", art="Einnahme",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"), konto_ust_skr03="1776",
    ))
    db.add(Journaleintrag(
        datum=date(2025, 2, 20), belegnr="2500061", beschreibung="STORNO 2500060: Korrektur",
        kategorie_id=kat.id, zahlungsart="Bar", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"), konto_ust_skr03="1776", immutable=True,
    ))
    db.commit()

    from api.euer import _berechne_euer
    assert _berechne_euer(2025, db)["zeilen"].get(17, Decimal("0.00")) == Decimal("0.00")


def test_normale_ausgabe_ohne_ust_konto_veraendert_zeile_17_nicht(db):
    """Sicherheitsnetz: Eine normale Ausgabe mit USt aber ohne USt-Konto und ohne
    STORNO-Präfix (z. B. Wareneinkauf ohne Vorsteuerabzug) darf die vereinnahmte
    USt (Zeile 17) NICHT mindern."""
    kat = db.query(Kategorie).filter_by(name="Wareneinkauf").one()
    db.add(Journaleintrag(
        datum=date(2025, 4, 2), belegnr="2500070", beschreibung="Wareneinkauf ohne Vorsteuerabzug",
        kategorie_id=kat.id, zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"), vorsteuerabzug=False,
    ))
    db.commit()

    from api.euer import _berechne_euer
    zeilen = _berechne_euer(2025, db)["zeilen"]
    assert zeilen.get(17, Decimal("0.00")) == Decimal("0.00")
    # Die Ausgabe selbst landet voll in der Ausgaben-Zeile (netto + nicht abzugsfähige USt)
    assert zeilen.get(51, Decimal("0.00")) == Decimal("119.00")


def test_storno_eingangsrechnung_vorsteuer_spiegel(db):
    """Storno einer Ausgabe MIT Vorsteuerabzug (Bug-Report 2026-11): die Storno-Gegenbuchung
    (art=Einnahme, netto/ust positiv, vorsteuer NEGATIV - so erzeugen journal.storno und
    rechnungen.storno sie) durfte in der Ausgaben-Basis nicht doppelt zählen: das Storno
    einer 30-€-Zahlung (netto 30, USt 5,70, Vorsteuer 5,70) wies -41,40 statt -30,00 aus.
    Außerdem darf der Storno die vereinnahmte USt (Zeile 17) nicht ADDIEREN - die USt war
    nie vereinnahmt, die Korrektur läuft nur über Zeile 57 (negative Vorsteuer)."""
    vst_kat = db.query(Kategorie).filter_by(name="Bürobedarf").one()
    # Original-Zahlung auf Eingangsrechnung: Vorsteuer-Konto (1406), voll abziehbar
    db.add(Journaleintrag(
        datum=date(2025, 10, 11), belegnr="2500080", beschreibung="Zahlung ER-250002: Test",
        kategorie_id=vst_kat.id, zahlungsart="PayPal", art="Ausgabe",
        netto_betrag=Decimal("30.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("5.70"),
        vorsteuerabzug=True, vorsteuer_betrag=Decimal("5.70"), brutto_betrag=Decimal("35.70"),
        konto_ust_skr03="1406",
    ))
    # Zweite, nicht stornierte Zahlung - hält die Zeilen sichtbar (Summe ungleich 0)
    db.add(Journaleintrag(
        datum=date(2025, 10, 12), belegnr="2500081", beschreibung="Zahlung ER-250003: Test",
        kategorie_id=vst_kat.id, zahlungsart="PayPal", art="Ausgabe",
        netto_betrag=Decimal("20.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("3.80"),
        vorsteuerabzug=True, vorsteuer_betrag=Decimal("3.80"), brutto_betrag=Decimal("23.80"),
        konto_ust_skr03="1406",
    ))
    # Storno-Gegenbuchung wie von rechnungen.storno erzeugt: art gespiegelt (Einnahme),
    # netto/ust positiv, vorsteuer negiert, USt-Konto vom Original übernommen
    db.add(Journaleintrag(
        datum=date(2025, 10, 11), belegnr="2500082", beschreibung="STORNO 2500080: ER-250002 – Test",
        kategorie_id=vst_kat.id, zahlungsart="PayPal", art="Einnahme",
        netto_betrag=Decimal("30.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("5.70"),
        vorsteuer_betrag=Decimal("-5.70"), brutto_betrag=Decimal("35.70"),
        konto_ust_skr03="1406", immutable=True,
    ))
    db.commit()

    from api.euer import _berechne_euer
    zeilen = _berechne_euer(2025, db)["zeilen"]

    # Ausgaben-Zeile: nur die nicht stornierte Zahlung bleibt (30 - 30 + 20)
    assert zeilen.get(51) == Decimal("20.00")
    # Vereinnahmte USt (17): Storno darf nicht +5,70 adieren
    assert zeilen.get(17, Decimal("0.00")) == Decimal("0.00")
    # Vorsteuer (57): 3,80 bleibt, Storno korrigiert -5,70
    assert zeilen.get(57) == Decimal("3.80")

    # Aufschlüsselung konsistent zu den Summen: Einzelposten spiegeln
    detail = euer_kategorien(2025, db=db)
    zeile51 = next(z for z in detail.zeilen if z.zeile == 51)
    posten = {b.belegnr: b.betrag for k in zeile51.kategorien for b in k.buchungen}
    assert posten == {"2500080": Decimal("30.00"), "2500081": Decimal("20.00"),
                      "2500082": Decimal("-30.00")}
    zeile57 = next(z for z in detail.zeilen if z.zeile == 57)
    vst_posten = {b.belegnr: b.betrag for k in zeile57.kategorien for b in k.buchungen}
    assert vst_posten == {"2500080": Decimal("5.70"), "2500081": Decimal("3.80"),
                          "2500082": Decimal("-5.70")}


def test_storno_ausgabe_ohne_vorsteuer_anteilspaßig(db):
    """Teilweiser Vorsteuerabzug (z. B. 50 % Bewirtung): Basis bei Ausgabe UND Storno muss
    den nicht abzugsfähigen Anteil identisch berücksichtigen (Spiegel)."""
    kat = db.query(Kategorie).filter_by(name="Bürobedarf").one()
    # vorsteuer_prozent 50 → von 5,70 USt sind 2,85 abziehbar, 2,85 bleiben in der Ausgabe
    kat.vorsteuer_prozent = Decimal("50")
    db.add(Journaleintrag(
        datum=date(2025, 5, 2), belegnr="2500090", beschreibung="Bewirtung",
        kategorie_id=kat.id, zahlungsart="Bar", art="Ausgabe",
        netto_betrag=Decimal("30.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("5.70"),
        vorsteuerabzug=True, vorsteuer_betrag=Decimal("2.85"), brutto_betrag=Decimal("35.70"),
        konto_ust_skr03="1406",
    ))
    db.add(Journaleintrag(
        datum=date(2025, 5, 3), belegnr="2500091", beschreibung="STORNO 2500090: Bewirtung Korrektur",
        kategorie_id=kat.id, zahlungsart="Bar", art="Einnahme",
        netto_betrag=Decimal("30.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("5.70"),
        vorsteuer_betrag=Decimal("-2.85"), brutto_betrag=Decimal("35.70"),
        konto_ust_skr03="1406", immutable=True,
    ))
    db.commit()

    from api.euer import _berechne_euer
    zeilen = _berechne_euer(2025, db)["zeilen"]
    # Original +32,85 und Storno -32,85 heben sich auf; keine Restsumme in 51 oder 17
    assert zeilen.get(51, Decimal("0.00")) == Decimal("0.00")
    assert zeilen.get(17, Decimal("0.00")) == Decimal("0.00")
    assert zeilen.get(57, Decimal("0.00")) == Decimal("0.00")


def test_storno_buendelung_felder_in_buchungen(db):
    """Bündelung der Aufschlüsselung: Original erhält storniert/storno_belegnr, die
    Gegenbuchung ist_storno/storno_von_belegnr - dieselbe Paar-Erkennung (STORNO-Präfix +
    gruppe_id-Wurzel) wie im Journal (Issue #321), damit die Oberfläche Original und
    Storno als Paar anzeigen und gezielt ausblenden kann."""
    kat = db.query(Kategorie).filter_by(name="Warenverkauf").one()
    original = Journaleintrag(
        datum=date(2025, 6, 1), belegnr="2500100", beschreibung="Zahlung RE-2025-0009",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("400.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("76.00"),
        brutto_betrag=Decimal("476.00"),
    )
    db.add(original)
    db.commit()
    db.refresh(original)
    # Gegenbuchung wie vom Storno erzeugt: gruppe_id = Wurzel, STORNO-Präfix + Original-Belegnr
    db.add(Journaleintrag(
        datum=date(2025, 6, 20), belegnr="2500101",
        beschreibung=f"STORNO 2500100: RE-2025-0009 – Rückabwicklung",
        kategorie_id=kat.id, zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("400.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("76.00"),
        brutto_betrag=Decimal("476.00"), immutable=True, gruppe_id=original.id,
    ))
    # unbeteiligte zweite Zahlung
    db.add(Journaleintrag(
        datum=date(2025, 6, 5), belegnr="2500102", beschreibung="Zahlung RE-2025-0010",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("150.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("28.50"),
        brutto_betrag=Decimal("178.50"),
    ))
    db.commit()

    detail = euer_kategorien(2025, db=db)
    zeile15 = next(z for z in detail.zeilen if z.zeile == 15)
    posten = {b.belegnr: b for k in zeile15.kategorien for b in k.buchungen}

    orig = posten["2500100"]
    storno = posten["2500101"]
    zweite = posten["2500102"]
    assert orig.storniert is True and orig.storno_belegnr == "2500101"
    assert orig.ist_storno is False
    assert storno.ist_storno is True and storno.storno_von_belegnr == "2500100"
    assert storno.storniert is False
    assert zweite.storniert is False and zweite.ist_storno is False
    assert zweite.storno_belegnr is None and zweite.storno_von_belegnr is None

    # Beträge unverändert (Paar zeigt +400/-400, Kategorie-Summe bleibt 150)
    assert orig.betrag == Decimal("400.00") and storno.betrag == Decimal("-400.00")
    assert zeile15.betrag_gesamt == Decimal("150.00")


def test_storno_ohne_gruppe_id_wird_nicht_gepaart(db):
    """Alte Bestands-Stornos ohne gruppe_id (vor Issue #321): das "STORNO "-Präfix ALLEIN darf
    die Paar-Erkennung nicht triggern - sonst würde eine eigene Buchung, deren Text zufällig
    mit "STORNO " beginnt, fälschlich als Gegenbuchung markiert. Beide Felder bleiben deshalb
    unset; die rechnerische Korrektur (Zeile 15/17) läuft weiterhin über das Präfix
    (siehe _euer_ust_beitraege und den A/B-Basis-Spiegel)."""
    kat = db.query(Kategorie).filter_by(name="Warenverkauf").one()
    # zweite, unbeteiligte Zahlung - hält die Zeile sichtbar (Original+Storno heben sich auf)
    db.add(Journaleintrag(
        datum=date(2025, 7, 5), belegnr="2500112", beschreibung="Zahlung RE-2025-0012",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("50.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("9.50"),
        brutto_betrag=Decimal("59.50"),
    ))
    db.add(Journaleintrag(
        datum=date(2025, 7, 1), belegnr="2500110", beschreibung="Zahlung RE-2025-0011",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"),
    ))
    db.add(Journaleintrag(
        datum=date(2025, 7, 10), belegnr="2500111", beschreibung="STORNO 2500110: Korrektur",
        kategorie_id=kat.id, zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"), immutable=True,
    ))
    db.commit()

    detail = euer_kategorien(2025, db=db)
    zeile15 = next(z for z in detail.zeilen if z.zeile == 15)
    posten = {b.belegnr: b for k in zeile15.kategorien for b in k.buchungen}

    assert posten["2500110"].storniert is False and posten["2500110"].storno_belegnr is None
    assert posten["2500111"].ist_storno is False and posten["2500111"].storno_von_belegnr is None
    # Beträge rechnerisch trotzdem korrekt gespiegelt: +100/-100 heben sich auf
    assert posten["2500111"].betrag == Decimal("-100.00")
    assert zeile15.betrag_gesamt == Decimal("50.00")
