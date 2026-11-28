"""
Umbuchung zwischen eigenen Konten (Community-Frage Pascal): Kategorie „Geldtransit“ (Neutral,
SKR03 1360 / SKR04 1460), Umbuchung im Bank-Import mit Gegenstück aus einem anderen Konto oder
der Kasse, DATEV-Nummer für jedes neue Konto, DATEV-Export nutzt die Nummern der Konten.
"""
import asyncio
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import UmbuchungRequest, umbuchung_buchen, umbuchung_vorschlag
from api.datev import datev_buchungsstapel
from api.journal import _get_bar_kassenstand
from api.konten import create_konto, datev_vorschlag
from api.schemas import KontoCreate
from database.connection import Base
from database.models import BankImport, BankTransaktion, Journaleintrag, Kategorie, Konto, Unternehmen
from database.seed import GELDTRANSIT_NAME, STANDARD_KATEGORIEN
from main import app


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="Testfirma", strasse="Str.", hausnummer="1", plz="12345", ort="Ort",
                      kontenrahmen="SKR04", geschaeftsjahr_beginn=1))
    s.add(Kategorie(name=GELDTRANSIT_NAME, kontenart="Neutral", konto_skr03="1360", konto_skr04="1460"))
    s.add(Kategorie(name="Bürobedarf", kontenart="Aufwand", konto_skr03="4930", konto_skr04="6815",
                    euer_zeile=60))
    s.commit()
    yield s
    s.close()


def _bank(db, name, iban, **kw) -> Konto:
    return db.get(Konto, create_konto(KontoCreate(name=name, anbieter="Bank", iban=iban, **kw), db).id)


def _paypal(db, name="PayPal", **kw) -> Konto:
    return db.get(Konto, create_konto(KontoCreate(name=name, anbieter="PayPal", kontoart="zahlungsdienstleister",
                                                  kennung=f"{name.lower()}@example.org", **kw), db).id)


_imp: dict[int, int] = {}


def _tx(db, konto, betrag, datum=date(2026, 5, 4), **kw) -> BankTransaktion:
    if konto.id not in _imp or db.get(BankImport, _imp[konto.id]) is None:
        imp = BankImport(konto_id=konto.id, dateiname="test.csv", template_id="CAMT_XML")
        db.add(imp)
        db.flush()
        _imp[konto.id] = imp.id
    tx = BankTransaktion(konto_id=konto.id, import_id=_imp[konto.id], datum=datum, betrag=Decimal(betrag),
                         partner_name="Ich selbst", verwendungszweck="Umbuchung", ist_geschaeftlich=True, **kw)
    db.add(tx)
    db.commit()
    return tx


def _datev_zeilen(db):
    response = datev_buchungsstapel(von=date(2026, 1, 1), bis=date(2026, 12, 31), mit_belegen=False, db=db)
    inhalt = b"".join(asyncio.run(_lesen(response))).decode("utf-8-sig")
    return response, [z.split(";") for z in inhalt.split("\r\n")[2:]]


async def _lesen(response):
    return [teil async for teil in response.body_iterator]


# --- Kategorie -----------------------------------------------------------------------------

def test_kategorie_in_seed():
    kat = next(k for k in STANDARD_KATEGORIEN if k["name"] == GELDTRANSIT_NAME)
    assert (kat["kontenart"], kat["konto_skr03"], kat["konto_skr04"], kat["euer_zeile"]) == ("Neutral", "1360", "1460", None)


# --- DATEV-Nummer je Konto -----------------------------------------------------------------

def test_neue_konten_bekommen_naechste_freie_nummer(db):
    assert _bank(db, "Geschäftskonto", "DE02120300000000202051").datev_kontonummer == "1800"
    assert _bank(db, "Rücklagen", "DE02500105170137075030").datev_kontonummer == "1810"
    assert _paypal(db).datev_kontonummer == "1820"
    assert _paypal(db, "Stripe").datev_kontonummer == "1830"
    # eigene Nummer vom Steuerbüro bleibt
    assert _bank(db, "Tagesgeld", "DE89370400440532013000", datev_kontonummer="1899").datev_kontonummer == "1899"
    assert datev_vorschlag(kontoart="bank", db=db) == {"kontonummer": "1840", "geldtransit": "1460"}


def test_globale_nummer_vom_steuerbuero_geht_an_das_konto(db):
    db.query(Unternehmen).one().datev_konto_paypal = "1890"
    db.commit()
    assert _paypal(db).datev_kontonummer == "1890"
    assert _paypal(db, "Stripe").datev_kontonummer == "1800"


def test_kontenrahmen_wechsel_stellt_nummern_um(db):
    from api.schemas import UnternehmenUpdate
    from api.unternehmen import update_unternehmen
    db.query(Unternehmen).one().kontenrahmen = "SKR03"
    db.commit()
    a = _bank(db, "Geschäftskonto", "DE02120300000000202051")
    p = _paypal(db)
    eigen = _bank(db, "Tagesgeld", "DE89370400440532013000", datev_kontonummer="1299")
    assert (a.datev_kontonummer, p.datev_kontonummer) == ("1200", "1210")

    update_unternehmen(UnternehmenUpdate(kontenrahmen="SKR04"), db)
    db.expire_all()
    assert [db.get(Konto, k.id).datev_kontonummer for k in (a, p, eigen)] == ["1800", "1810", "1299"]

    update_unternehmen(UnternehmenUpdate(kontenrahmen="SKR03"), db)
    db.expire_all()
    assert [db.get(Konto, k.id).datev_kontonummer for k in (a, p, eigen)] == ["1200", "1210", "1299"]


def test_kontenrahmen_wechsel_weicht_belegter_nummer_aus(db):
    from utils.datev_konten import finanzkonten_umstellen
    db.query(Unternehmen).one().kontenrahmen = "SKR03"
    db.commit()
    a = _bank(db, "Geschäftskonto", "DE02120300000000202051")              # 1200 → eigentlich 1800
    fremd = _bank(db, "Altkonto", "DE02500105170137075030", datev_kontonummer="1800")  # schon belegt
    finanzkonten_umstellen(db, "SKR03", "SKR04")
    assert (a.datev_kontonummer, fremd.datev_kontonummer) == ("1810", "1800")


# --- DATEV-Export --------------------------------------------------------------------------

def _journal(db, zahlungsart, konto_id=None, belegnr="J-1"):
    kat = db.query(Kategorie).filter(Kategorie.name == "Bürobedarf").one()
    db.add(Journaleintrag(datum=date(2026, 3, 5), belegnr=belegnr, beschreibung=f"Test {zahlungsart}",
                          kategorie_id=kat.id, konto_skr04="6815", zahlungsart=zahlungsart, art="Ausgabe",
                          netto_betrag=Decimal("10"), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
                          vorsteuer_betrag=Decimal("0"), brutto_betrag=Decimal("10"), konto_id=konto_id))
    db.commit()


def test_paypal_ohne_konto_nutzt_einzigen_zahlungsdienstleister(db):
    _paypal(db)
    _journal(db, "PayPal")
    response, zeilen = _datev_zeilen(db)
    assert zeilen[0][6:8] == ["6815", "1800"]
    assert response.headers["X-Datev-Geldtransit-Kollision"] == "0"


def test_paypal_mehrdeutig_faellt_auf_standard_und_warnt(db):
    _paypal(db)
    _paypal(db, "Stripe")
    _journal(db, "PayPal")
    response, zeilen = _datev_zeilen(db)
    assert zeilen[0][7] == "1460"  # bisheriger SKR04-Standard
    assert response.headers["X-Datev-Geldtransit-Kollision"] == "1"


def test_konto_an_der_buchung_gilt_auch_fuer_paypal(db):
    _paypal(db)
    stripe = _paypal(db, "Stripe")
    _journal(db, "PayPal", konto_id=stripe.id)
    _, zeilen = _datev_zeilen(db)
    assert zeilen[0][7] == "1810"


def test_bank_ohne_konto_nutzt_standardkonto(db):
    _bank(db, "Geschäftskonto", "DE02120300000000202051", datev_kontonummer="1805")
    _journal(db, "Bank")
    _, zeilen = _datev_zeilen(db)
    assert zeilen[0][7] == "1805"


def test_geldtransit_header_freigegeben():
    cors = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
    assert "X-Datev-Geldtransit-Kollision" in set(cors.kwargs["expose_headers"])


# --- Umbuchung im Bank-Import --------------------------------------------------------------

def test_umbuchung_mit_gegenstueck(db):
    a = _bank(db, "Geschäftskonto", "DE02120300000000202051")
    b = _bank(db, "Rücklagen", "DE02500105170137075030")
    ab = _tx(db, a, "-500.00", date(2026, 5, 4))
    zu = _tx(db, b, "500.00", date(2026, 5, 6))
    _tx(db, b, "500.00", date(2026, 5, 20))  # zu weit weg
    vorschlag = umbuchung_vorschlag(ab.id, db)
    assert [g.tx_id for g in vorschlag.gegenstuecke] == [zu.id]

    umbuchung_buchen(ab.id, UmbuchungRequest(gegenseite="transaktion", gegen_tx_id=zu.id), db)
    db.expire_all()
    seiten = {j.konto_id: j for j in db.query(Journaleintrag).all()}
    assert seiten[a.id].art == "Ausgabe" and seiten[b.id].art == "Einnahme"
    assert all(j.kategorie.name == GELDTRANSIT_NAME and j.ust_betrag == 0 for j in seiten.values())
    assert db.get(BankTransaktion, ab.id).journal_id and db.get(BankTransaktion, zu.id).journal_id

    _, zeilen = _datev_zeilen(db)
    assert sorted((z[6], z[7], z[1]) for z in zeilen) == [("1460", "1800", "S"), ("1460", "1810", "H")]


def test_ignorierte_umbuchung_nachtraeglich_buchen(db):
    a = _bank(db, "Geschäftskonto", "DE02120300000000202051")
    b = _bank(db, "Rücklagen", "DE02500105170137075030")
    ab = _tx(db, a, "-50.00", ignoriert=True)
    zu = _tx(db, b, "50.00", ignoriert=True)
    assert [g.tx_id for g in umbuchung_vorschlag(ab.id, db).gegenstuecke] == [zu.id]
    umbuchung_buchen(ab.id, UmbuchungRequest(gegenseite="transaktion", gegen_tx_id=zu.id), db)
    assert not db.get(BankTransaktion, ab.id).ignoriert


def test_falsches_gegenstueck_abgelehnt(db):
    a = _bank(db, "Geschäftskonto", "DE02120300000000202051")
    b = _bank(db, "Rücklagen", "DE02500105170137075030")
    ab = _tx(db, a, "-500.00")
    falsch = _tx(db, b, "499.00")
    with pytest.raises(HTTPException) as e:
        umbuchung_buchen(ab.id, UmbuchungRequest(gegenseite="transaktion", gegen_tx_id=falsch.id), db)
    assert e.value.status_code == 409
    assert db.query(Journaleintrag).count() == 0


def test_abhebung_in_die_kasse(db):
    a = _bank(db, "Geschäftskonto", "DE02120300000000202051")
    ab = _tx(db, a, "-200.00")
    umbuchung_buchen(ab.id, UmbuchungRequest(gegenseite="kasse"), db)
    bar = db.query(Journaleintrag).filter(Journaleintrag.zahlungsart == "Bar").one()
    assert (bar.art, bar.brutto_betrag, bar.beschreibung) == ("Einnahme", Decimal("200.00"), "Abhebung von Geschäftskonto")
    assert _get_bar_kassenstand(db) == Decimal("200.00")


def test_einzahlung_aus_der_kasse_prueft_kassenbestand(db):
    a = _bank(db, "Geschäftskonto", "DE02120300000000202051")
    ein = _tx(db, a, "300.00")
    with pytest.raises(HTTPException) as e:
        umbuchung_buchen(ein.id, UmbuchungRequest(gegenseite="kasse"), db)
    assert e.value.status_code == 409
    assert db.query(Journaleintrag).count() == 0


def test_nur_diese_seite(db):
    a = _bank(db, "Geschäftskonto", "DE02120300000000202051")
    ab = _tx(db, a, "-80.00")
    ergebnis = umbuchung_buchen(ab.id, UmbuchungRequest(gegenseite="keine"), db)
    assert len(ergebnis) == 1 and db.query(Journaleintrag).count() == 1
    with pytest.raises(HTTPException) as e:
        umbuchung_buchen(ab.id, UmbuchungRequest(gegenseite="keine"), db)
    assert e.value.status_code == 409
