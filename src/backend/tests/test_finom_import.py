"""
Regressionstest für Issue #342 (Bank-Import-Template "Finom").

Deckt die im Issue genannten Besonderheiten des Finom-CSV-Exports ab:
  - Dezimaltrennzeichen ist der Punkt, nicht das Komma
  - leere Felder stehen als "N/A" statt leer (Verwendungszweck/BIC/IBAN bei Kartenzahlungen)
  - ein Feld mit eingebettetem Komma ist gequotet (Finom-Gebühr)
  - Wallet-IBAN (eigenes Konto) darf nicht als partner_iban interpretiert werden

Nur der CSV-Export wird unterstützt - RechnungsFee hat aktuell keinen SWIFT/MT940-
Tag-Parser (":61:"/":86:" etc.), das würde ein eigenes, größeres Feature erfordern.
"""
from decimal import Decimal
from datetime import date

import pytest

from database.seed import SYSTEM_BANK_TEMPLATES
from utils.bank_csv_parser import parse_csv


def _finom_mapping() -> dict:
    tpl = next(t for t in SYSTEM_BANK_TEMPLATES if t["id"] == "finom")
    return {"__erkennungs__": tpl["erkennungs_spalten"], **tpl["column_mapping"]}


FINOM_CSV = (
    "Buchungsdatum,Time completed,Status,Transaktionsart,Auftraggeber/Empfänger,"
    "Counterparty BIC,Counterparty IBAN,Verwendungszweck,Tags,Zahlungsfreigeber,"
    "Kartennummer,Ursprungswährung,Ursprungsbetrag,Zahlungswährung,Zahlungsbetrag,"
    "Wallet-Saldo nach Transaktion,Wallet-Name,Wallet-IBAN,Begleitende Dokumente,Transaktions-ID\n"
    "03.03.2026,03.03.2026 10:15:00,Completed,Transfer,Max Mustermann,GENODEF1XXX,"
    "DE62370400440532013001,Rechnung 2026-001,N/A,N/A,N/A,EUR,500.00,EUR,500.00,"
    "500.00,Hauptkonto,DE00000000000000000000,N/A,TX-001\n"
    "04.03.2026,04.03.2026 12:00:00,Completed,Card,SumUp  *Haendler GmbH,N/A,N/A,N/A,N/A,"
    "aGVsbG8rd29ybGQ9/,**** 1234,EUR,-20.00,EUR,-20.00,"
    "480.00,Hauptkonto,DE00000000000000000000,N/A,TX-002\n"
    "05.03.2026,05.03.2026 00:00:00,Completed,FeeByOption,PNL Fintech B.V.,N/A,"
    "NL00PNLF0000000000,\"Jahresgebühr, Kontoführung (incl. VAT)\",N/A,N/A,N/A,EUR,-9.00,"
    "EUR,-9.00,471.00,Hauptkonto,DE00000000000000000000,N/A,TX-003\n"
)


def test_finom_csv_wird_korrekt_geparst():
    result = parse_csv(
        FINOM_CSV.encode("utf-8"),
        column_mapping=_finom_mapping(),
        delimiter=",",
        encoding="UTF-8",
        decimal_separator=".",
        date_format="%d.%m.%Y",
        skip_rows=0,
    )
    assert len(result) == 3

    gutschrift = result[0]
    assert gutschrift["datum"] == date(2026, 3, 3)
    assert gutschrift["betrag"] == Decimal("500.00")
    assert gutschrift["waehrung"] == "EUR"
    assert gutschrift["partner_name"] == "Max Mustermann"
    assert gutschrift["partner_bic"] == "GENODEF1XXX"
    assert gutschrift["partner_iban"] == "DE62370400440532013001"
    assert gutschrift["verwendungszweck"] == "Rechnung 2026-001"
    assert gutschrift["saldo"] == Decimal("500.00")
    assert gutschrift["referenz"] == "TX-001"
    assert gutschrift["buchungstext"] == "Transfer"


def test_finom_kartenzahlung_n_a_wird_als_leer_behandelt():
    result = parse_csv(
        FINOM_CSV.encode("utf-8"),
        column_mapping=_finom_mapping(),
        delimiter=",", encoding="UTF-8", decimal_separator=".", date_format="%d.%m.%Y",
    )
    kartenzahlung = result[1]
    assert kartenzahlung["betrag"] == Decimal("-20.00")
    # "N/A" darf nicht als literaler Text in der Buchung landen
    assert kartenzahlung["verwendungszweck"] is None
    assert kartenzahlung["partner_bic"] is None
    assert kartenzahlung["partner_iban"] is None
    assert kartenzahlung["partner_name"] == "SumUp  *Haendler GmbH"


def test_finom_gequotetes_feld_mit_komma_bleibt_ein_feld():
    result = parse_csv(
        FINOM_CSV.encode("utf-8"),
        column_mapping=_finom_mapping(),
        delimiter=",", encoding="UTF-8", decimal_separator=".", date_format="%d.%m.%Y",
    )
    gebuehr = result[2]
    assert gebuehr["verwendungszweck"] == "Jahresgebühr, Kontoführung (incl. VAT)"
    assert gebuehr["betrag"] == Decimal("-9.00")


def test_finom_wallet_iban_wird_nicht_als_partner_iban_uebernommen():
    """Wallet-IBAN ist das eigene Konto, nicht das der Gegenseite - darf nicht gemappt werden."""
    mapping = _finom_mapping()
    assert "Wallet-IBAN" not in {k: v for k, v in mapping.items() if v == "partner_iban"}
