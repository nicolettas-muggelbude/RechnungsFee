"""
Leitweg-ID öffentlicher Auftraggeber (Issue #530) – Format nach KoSIT-Spezifikation „Format der
Leitweg-ID“: Grobadressierung (2–12 Ziffern) – optional Feinadressierung (bis 30 Zeichen A–Z/0–9)
– Prüfziffer (2 Ziffern, Modulo 97-10 wie bei der IBAN; Buchstaben A=10 … Z=35).
Beispiel: 991-33333TEST-33 (Test-ID der Zentralen Rechnungseingangsplattform des Bundes).
"""
import re

_MUSTER = re.compile(r"^(\d{2,12})(?:-([A-Z0-9]{1,30}))?-(\d{2})$")


def normalisiere_leitweg_id(wert: str | None) -> str | None:
    wert = (wert or "").strip().upper().replace(" ", "")
    return wert or None


def leitweg_id_fehler(wert: str | None) -> str | None:
    """None wenn gültig, sonst eine verständliche Fehlermeldung."""
    lid = normalisiere_leitweg_id(wert)
    if not lid:
        return "Leitweg-ID fehlt."
    m = _MUSTER.match(lid)
    if not m:
        return ("Leitweg-ID hat kein gültiges Format – erwartet z. B. 991-33333TEST-33 "
                "(Ziffern, optional Feinadressierung, zweistellige Prüfziffer, getrennt durch Bindestriche).")
    grob, fein, pz = m.group(1), m.group(2) or "", m.group(3)
    zahl = "".join(str(int(c, 36)) for c in grob + fein) + pz
    if int(zahl) % 97 != 1:
        return "Die Prüfziffer der Leitweg-ID stimmt nicht – bitte auf Tippfehler prüfen."
    return None
