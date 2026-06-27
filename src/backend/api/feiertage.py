"""
Gesetzliche Feiertage für alle 16 Bundesländer.
Ostertermin nach Gauß-Algorithmus, bewegliche + feste Feiertage.
"""
from datetime import date, timedelta

# Bundesland-Kürzel → Anzeigename
BUNDESLAENDER = {
    "BB": "Brandenburg",
    "BE": "Berlin",
    "BW": "Baden-Württemberg",
    "BY": "Bayern",
    "HB": "Bremen",
    "HE": "Hessen",
    "HH": "Hamburg",
    "MV": "Mecklenburg-Vorpommern",
    "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz",
    "SH": "Schleswig-Holstein",
    "SL": "Saarland",
    "SN": "Sachsen",
    "ST": "Sachsen-Anhalt",
    "TH": "Thüringen",
}


def _ostern(year: int) -> date:
    """Gauss-Algorithmus für den Ostersonntag."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def feiertage(year: int, bundesland: str) -> dict[date, str]:
    """
    Gibt alle gesetzlichen Feiertage für ein Jahr + Bundesland zurück.
    Key: date, Value: Bezeichnung
    """
    bl = bundesland.upper()
    o = _ostern(year)
    result: dict[date, str] = {}

    def add(d: date, name: str) -> None:
        result[d] = name

    # Bundesweite Feiertage
    add(date(year, 1, 1),   "Neujahr")
    add(o - timedelta(days=2), "Karfreitag")
    add(o,                     "Ostersonntag")
    add(o + timedelta(days=1), "Ostermontag")
    add(date(year, 5, 1),   "Tag der Arbeit")
    add(o + timedelta(days=39), "Christi Himmelfahrt")
    add(o + timedelta(days=49), "Pfingstsonntag")
    add(o + timedelta(days=50), "Pfingstmontag")
    add(date(year, 10, 3),  "Tag der Deutschen Einheit")
    add(date(year, 12, 25), "1. Weihnachtstag")
    add(date(year, 12, 26), "2. Weihnachtstag")

    # Heilige Drei Könige: BW, BY, ST
    if bl in ("BW", "BY", "ST"):
        add(date(year, 1, 6), "Heilige Drei Könige")

    # Internationaler Frauentag: BE, MV, TH (seit 2019/2023)
    if bl in ("BE", "MV"):
        add(date(year, 3, 8), "Internationaler Frauentag")

    # Gründonnerstag nur BY (nur Gemeinden mit Rasttag-Tradition – kein gesetzlicher FT)
    # Fronleichnam: BW, BY, HE, NW, RP, SL, SN (Teile), TH (Teile)
    if bl in ("BW", "BY", "HE", "NW", "RP", "SL"):
        add(o + timedelta(days=60), "Fronleichnam")

    # Augsburger Friedensfest: nur Augsburg (BY) – zu spezifisch, weglassen

    # Mariä Himmelfahrt: BY (kath. Gemeinden), SL
    if bl in ("BY", "SL"):
        add(date(year, 8, 15), "Mariä Himmelfahrt")

    # Weltkindertag: TH
    if bl == "TH":
        add(date(year, 9, 20), "Weltkindertag")

    # Reformationstag: BB, HB, HH, MV, NI, SN, ST, TH (+ seit 2018: SH, RP)
    if bl in ("BB", "HB", "HH", "MV", "NI", "SN", "ST", "TH", "SH", "RP"):
        add(date(year, 10, 31), "Reformationstag")

    # Allerheiligen: BW, BY, NW, RP, SL
    if bl in ("BW", "BY", "NW", "RP", "SL"):
        add(date(year, 11, 1), "Allerheiligen")

    # Buß- und Bettag: SN
    if bl == "SN":
        # Mittwoch vor dem 23. November
        nov23 = date(year, 11, 23)
        bbt = nov23 - timedelta(days=(nov23.weekday() - 2) % 7)
        add(bbt, "Buß- und Bettag")

    return result


def ist_feiertag(d: date, bundesland: str) -> bool:
    return d in feiertage(d.year, bundesland)


def naechster_werktag(d: date, bundesland: str) -> date:
    """Verschiebt ein Datum auf den nächsten Werktag wenn Wochenende oder Feiertag."""
    fts = {**feiertage(d.year, bundesland), **feiertage(d.year + 1, bundesland)}
    while d.weekday() >= 5 or d in fts:
        d += timedelta(days=1)
    return d
