# Sicherheit

## Sicherheitslücke melden

Bitte melde Sicherheitslücken **nicht** in einem öffentlichen Issue, sondern vertraulich über GitHub:

**[Sicherheitslücke melden](https://github.com/nicolettas-muggelbude/RechnungsFee/security/advisories/new)**
(Reiter „Security“ → „Report a vulnerability“)

Hilfreich sind:

- betroffene Version und Betriebssystem
- Beschreibung und mögliche Auswirkung
- Schritte zum Nachstellen (gern mit Beispieldatei)
- falls vorhanden: Vorschlag zur Behebung

Du bekommst eine Rückmeldung, sobald wir die Meldung geprüft haben. Bis eine korrigierte Version
veröffentlicht ist, bleibt die Meldung vertraulich. Danach veröffentlichen wir einen Hinweis und
nennen dich gern als Finder:in – sag einfach Bescheid, ob und wie.

## Unterstützte Versionen

Sicherheitskorrekturen gibt es nur für die jeweils aktuelle Version. Die eingebaute Update-Prüfung
bietet neue Versionen automatisch an.

## Hintergrund

RechnungsFee ist eine Desktop-App. Die Oberfläche spricht mit einem lokalen Hintergrunddienst,
der nur auf `127.0.0.1` lauscht; Daten verlassen den Rechner nur, wenn du es auslöst
(Mailversand, externes Backup, Rechnungspostfach).
