# Brainstorming: MCP-Server für RechnungsFee

**Issue:** #429
**Status:** Reines Brainstorming, keine Umsetzungsentscheidung. Melder sehr knapp ("volle
Automation via KI-Agenten"), Rückfrage nach konkretem Anwendungsfall im Issue gestellt, noch
unbeantwortet.

---

## Was MCP ist (Kurzfassung)

Model Context Protocol (Anthropic, Nov. 2024 offengelegt, seitdem auch von OpenAI, Microsoft
u. a. übernommen – kein Anthropic-Exklusivprotokoll). Ein MCP-Server exponiert "Tools"
(Funktionen mit Schema), ein KI-Client (Claude Desktop, etc.) ruft sie auf Anfrage des Nutzers
auf. Rein anfragegetrieben – RechnungsFee würde nie selbst etwas an die KI senden.

Architektur für RechnungsFee: ein lokaler MCP-Server-Prozess, der mit dem bereits lokal
laufenden Backend (Port 8002) spricht. Kein Cloud-Dienst, kein RechnungsFee-Konto nötig – die
einzige "Account"-Frage betrifft den KI-Anbieter (Claude.ai-Abo, API-Key, o. ä.), nicht
RechnungsFee selbst.

---

## Datenschutz: lokal vs. Cloud-Modell

Das Protokoll selbst macht keine Aussage darüber, wohin Daten fließen – das entscheidet allein
das Modell hinter dem KI-Client:

| Modell-Wahl | Datenfluss |
|---|---|
| Cloud (Claude, GPT, Gemini, …) | Von einem Tool-Aufruf zurückgegebene RechnungsFee-Daten (z. B. Rechnungsinhalte für eine Auswertung) werden Teil der Konversation beim jeweiligen Anbieter – wie Copy-Paste in den Chat. |
| Cloud, EU-Anbieter (z. B. Mistral) | Unterliegt direkt der DSGVO ohne Drittland-Problematik (Schrems II/US CLOUD Act) – datenschutzrechtlich klar besser als US-Anbieter, aber immer noch ein Drittanbieter-Vertrauensverhältnis. |
| Lokales Modell (Ollama, LM Studio, …) | Nichts verlässt den Rechner. Einzige Option ganz ohne Drittanbieter-Vertrauen. |

RechnungsFee ist bisher komplett lokal (SQLite pro Profil, kein eigener Server) – MCP wäre die
**erste** Funktion mit potenziellem Cloud-Datenfluss, aber nur als bewusste Opt-in-Entscheidung
des Nutzers (Wahl von Client/Modell liegt bei ihm). Falls umgesetzt: lokales Modell als
empfohlener Default, Cloud-Anbieter klar als Opt-in kennzeichnen.

---

## Wie groß müsste ein lokales Modell sein?

Keine gemessenen Benchmark-Zahlen dazu, sondern eine Einschätzung aus bekannten
Function-Calling-Mustern (z. B. Berkeley Function-Calling Leaderboard-Trends) – mit
entsprechendem Vorbehalt.

**Wichtiger als die Parameterzahl: wie viele Tools, wie gut deren Schema/Namen sind, und ob es
sich um Lese- oder Schreib-Aktionen handelt.**

### Faustregel nach Einsatzzweck

| Zweck | Risiko bei Fehler | Realistische Modellgröße | Hardware |
|---|---|---|---|
| **Auswertung/Statistik** (nur Lesen, z. B. "Umsatz pro Monat") | Gering – falsche Zusammenfassung ist gegen die echten Zahlen prüfbar | ~7–14 B (z. B. Qwen2.5-14B, Mistral-NeMo-12B), mit Function-Calling-Finetune | 8–16 GB VRAM, läuft auch brauchbar auf CPU |
| **Schreib-Aktionen** (Rechnung buchen, Zahlung erfassen, stornieren) | Hoch – falscher Betrag/falsche Rechnung hat echte Buchhaltungs-/GoBD-Folgen | Eher 24–32 B+ (z. B. Mistral-Small-24B, Qwen2.5-32B) **und/oder** ein Bestätigungsschritt im Tool-Design selbst (Vorschau statt Direktausführung) | 24 GB+ VRAM (z. B. eine RTX 3090/4090) |
| Komplexe Mehrschritt-Aktionen (mehrere verknüpfte Buchungen) | Hoch | 70 B+ nähert sich Cloud-Qualität an | 48 GB+ VRAM oder starke Quantisierung – für die meisten Freiberufler-Rechner nicht realistisch |

### Wichtigster Hebel: Tool-Design, nicht nur Modellgröße

RechnungsFees Backend hat Dutzende Endpunkte (Rechnungen, Journal, Kunden, UStVA, Mahnwesen,
Bank-Import, …). Diese 1:1 als MCP-Tools zu exponieren würde selbst ein großes Modell bei der
Tool-Auswahl überfordern. Sinnvoller: eine kleine Zahl kuratierter, hochrangiger Tools (z. B.
`suche_kunde`, `liste_offene_rechnungen`, `erstelle_rechnung`, `buche_zahlung`,
`auswertung_zeitraum`) statt aller Rohendpunkte. Das senkt die nötige Modellgröße deutlich und
ist unabhängig von Hardware-Fragen umsetzbar.

**Fazit:** Für den von der Nutzerin genannten Anwendungsfall ("Auswertungen und Statistik")
ist ein handhabbares lokales Modell (14B-Klasse) schon heute plausibel. Für Schreibaktionen mit
echten Buchhaltungsfolgen würde ich zusätzlich zu einem größeren Modell eine
Bestätigungs-/Vorschau-Stufe im Tool selbst einplanen – unabhängig davon, wie groß das Modell
ist.

---

## Offene Fragen

- Konkreter Anwendungsfall von duczz (Issue #429) steht noch aus.
- Tool-Scope: nur Lesen (Auswertungen) als erster, risikoärmerer Schritt? Schreibaktionen später?
- Mehrprofil-Frage: welches Profil/welche DB spricht der MCP-Server an, wenn mehrere existieren?
