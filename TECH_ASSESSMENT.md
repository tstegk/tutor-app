# Technical Assessment & Entwicklungsplan

Stand: 2026-09-20. Diese Datei fasst eine vollständige Code-Analyse des Projekts zusammen und leitet daraus einen priorisierten Entwicklungsplan ab. Sie ergänzt [ARCHITECTURE.md](ARCHITECTURE.md) (Infrastruktur/Deployment) um die Sicht auf Code-Qualität, Bugs und Risiken.

## Einordnung: Familienprojekt, kein Multi-Tenant-Produkt

Die App wird ausschließlich innerhalb der eigenen Familie genutzt (ein Elternaccount, die eigenen Kinder), nicht von fremden Familien oder einer größeren Nutzerbasis. Das ändert die Risikobewertung eines Teils der Befunde deutlich:

- Befunde, die von einem Multi-Tenant-/Öffentlichkeits-Szenario ausgehen (fremde Familien, viele parallele Nutzer, rechtliche Verantwortlichkeit gegenüber Dritten), werden **nicht entfernt**, aber unten explizit mit **„Priorität: gering – Familienkontext"** markiert.
- Befunde, die unabhängig von der Nutzerzahl gelten (z. B. ein offen auf der Platte liegender API-Key, Zugangsdaten in der Git-Historie, fehlende Backups für unwiederbringliche Familiendaten), bleiben in ihrer ursprünglichen Priorität, weil sie sich aus der Familiennutzung nicht relativieren.

---

## Teil A — Technical Debt (Risiko, Bugs, Sicherheitslücken)

### A1. Sicherheit & Zugangsdaten

Punkte 1–3 sind reine Zugangsdaten-/Hygiene-Themen und gelten unabhängig davon, wer die App nutzt – ein offen liegender API-Key oder ein Klartext-Passwort im Code ist genauso riskant, ob eine Familie oder tausend Nutzer betroffen sind. Keine Abstufung durch den Familienkontext.

1. **`users.db` ist in Git committed** und liegt im Remote (`github.com:tstegk/tutor-app.git`) – bcrypt-Hashes von 5 echten Accounts (u. a. Kinder-Accounts) sind dauerhaft in der Git-Historie, auch wenn die Datei heute noch getrackt wird (`git ls-files`, Commits u. a. `819a412`). Falls das Repo privat ist, sinkt das praktische Risiko (kein öffentlicher Leak), bleibt aber schlechte Praxis, die bei jedem Repo-Zugriff (Collaborator, Backup-Export, künftiges Öffentlich-Machen) zum Problem werden kann.
2. **Klartext-OpenAI-API-Key** liegt in `.env` auf der Platte (nicht in Git, aber ungeschützt lesbar).
3. **Klartext-Passwort im Code**: `reset_password.py:5` (`new_password = "12-33-97-7B-2C-2C"`) für den Eltern-Account – dieses Skript ist zudem weiterhin live auf dem Server, obwohl es per Commit `55bd00c` „aus Git entfernt" wurde (nur der Git-Tracking wurde beendet, die Datei existiert weiter).
4. **Default-Passwort `"-"`** für alle initial angelegten Accounts (`create_user.py:22-26`, inkl. Kinder-Accounts) – falls nie manuell geändert, sind das De-facto-Blanko-Zugänge zu Kinderkonten. *Bleibt trivial und kostenlos zu fixen – auch im Familienkontext sinnvoll, da die App übers Internet erreichbar ist und automatisierte Login-Scans generisch nach schwachen Passwörtern suchen, nicht gezielt gegen „fremde Nutzer".*
5. **Kein Datenisolations-Modell**: Eltern-Dashboard und Admin-Bereich fragen `usage`/Chat-Historien **ohne Owner-Filter** ab (`app.py:106-147`, `197-225`) – jeder Eltern-Account sieht Kosten/Aktivität **aller** Nutzer, nicht nur der eigenen Kinder. Es gibt keine `parent_id`/`child_id`-Verknüpfung im Datenmodell.
   **[Priorität: gering – Familienkontext]** In einer Ein-Familien-Installation mit genau einem Elternaccount gibt es keine „fremde Familie", deren Daten dadurch geleakt würden – technisch korrekt, aber ohne praktische Auswirkung, solange kein Account außerhalb der eigenen Familie vergeben wird.
6. **Chat-Verläufe der Kinder liegen unverschlüsselt als JSON-Dateien** im Projektverzeichnis (`chat_history_<user>.json`), teils root-owned (Docker-Container läuft als root), ohne Zugriffskontrolle über Dateisystemrechte hinaus, ohne Aufbewahrungs-/Löschkonzept.
   **[Priorität: gering – Familienkontext]** Die datenschutzrechtliche Brisanz (COPPA/DSGVO-Framing) betraf primär das Szenario „Anbieter verarbeitet Daten fremder Kinder" – hier sind es die eigenen Kinder der eigenen Eltern. Ein Restpunkt bleibt unabhängig vom Familienkontext: Die Chatinhalte gehen an einen externen LLM-Anbieter (aktuell OpenAI, künftig Claude) – das ist grundsätzlich bedenkenswert.
7. **Kein Rate-Limiting/Lockout** beim Login (`app.py:19-36`) – Brute-Force gegen die schwachen `"-"`-Passwörter ist unbegrenzt möglich.
   **[Priorität: gering – Familienkontext]** Kein attraktives Massenziel, aber die App ist trotzdem öffentlich über Internet erreichbar (Nginx Proxy Manager + Let's Encrypt), daher weiterhin sinnvoll als günstige Absicherung, nur nicht mehr dringlich.
8. **Docker-Bind-Mount (`.:/app`)** spiegelt das komplette Host-Repo (inkl. `.env`, `users.db`, Admin-Skripte, `.git`) 1:1 in den Container – das Image ist damit nicht die „Quelle der Wahrheit"; `.dockerignore`-Ausschlüsse werden dadurch effektiv unterlaufen. *Reine Engineering-Hygiene, unabhängig von der Nutzerzahl.*
9. **Mögliche Firewall-Lücke**: `docker-compose.yml` published Ports `8501` und `81` (nginx-proxy-manager Admin-UI) direkt – Docker manipuliert iptables oft an UFW vorbei, wodurch diese Ports trotz dokumentierter UFW-Regeln öffentlich erreichbar sein könnten.
10. **Prompt-Injection über Uploads**: extrahierter PDF-Text wird ungefiltert in den Prompt eingefügt (`app.py:385-389`), kein Escaping/Instruction-Hierarchie-Schutz.
    **[Priorität: gering – Familienkontext]** Das Angreifermodell setzt voraus, dass ein Familienmitglied selbst eine präparierte Datei hochlädt – im Familienrahmen unwahrscheinlich und folgenarm.

### A2. Funktionale Bugs (aktuell live, unbemerkt durch verschluckte Exceptions)

11. **Eltern-Dashboard „Letzte Fragen" ist komplett kaputt**: `app.py:167-191` behandelt `questions` (Liste von Strings) fälschlich wie eine Liste von Dicts (`q.get(...)`) → `AttributeError` bei jedem Aufruf, verschluckt durch `except: pass` (Zeile 190). Feature hat vermutlich nie funktioniert.
12. **Bild-Upload an die KI ist nicht funktionsfähig**: `app.py:391-403` übergibt ein rohes `PIL.Image`-Objekt statt einer Base64-/Data-URI-URL an die OpenAI-API – das zentrale „Foto der Hausaufgabe hochladen"-Feature schlägt fehl.
13. Mehrere weitere **bare `except: pass`** verschlucken Fehler ohne Logging (`app.py:183`, `190`, `287`) – Bugs bleiben unsichtbar, Nutzer bekommen keine Rückmeldung.
14. **Schema-Drift**: Die Tabelle `usage` existiert in der Live-DB, wird aber **in keinem getrackten Skript** angelegt (`init_db.py` erstellt nur `users`). Ein frischer Rebuild aus dem Repo würde beim ersten Eltern-/Admin-Login crashen (`no such table: usage`).
15. **Kosten-Schätzung ist von der Modellkonfiguration entkoppelt**: `usage_logger.py:5-6` verwendet hartcodierte Preise für `gpt-4.1`, unabhängig vom tatsächlich über `OPENAI_MODEL` konfigurierten Modell. *Wird beim Provider-Wechsel zu Claude ohnehin komplett neu gezogen, siehe Phase 1.*
16. **Enge Kopplung an die OpenAI-API („Vendor Lock-in")**: `llm_service.py` wrappt OpenAI-spezifische Response-Shapes 1:1 (`response.output`, `usage.input_tokens`, `image_url`-Content-Blocks, `enable_web_search`) statt eine echte Abstraktion zu bilden. Ein Provider-Wechsel berührt dadurch mehrere Stellen statt eines zentralen Punkts.

### A3. Fehlende Grundlagen (Wartbarkeit, Reproduzierbarkeit)

17. **Keine Tests** (0 Testdateien, keine Testframeworks eingebunden).
    **[Priorität: gering – Familienkontext]** Für ein Solo-/Familienprojekt ohne Team und ohne Release-Druck kein dringendes Bedürfnis – relevant wird es erst, wenn der Code komplexer wird oder mehrere Personen daran arbeiten.
18. **Keine CI/CD** – keine GitHub Actions o. ä.
    **[Priorität: gering – Familienkontext]** Gleiche Begründung wie bei Tests.
19. **Keine Migrationen** – Schema-Änderungen passieren manuell direkt an der Live-DB (siehe A2.14), nicht reproduzierbar. *Mittlere Priorität bleibt, da dies unabhängig vom Familienkontext zu einem konkreten Rebuild-Bug führt.*
20. **Unversionierte Dependencies** (`requirements.txt` ohne Pins, kein Lockfile) – `llm_service.py` nutzt die neuere OpenAI Responses-API, die von der laschen Untergrenze `openai>=1.0.0` nicht garantiert wird; ein Rebuild kann jederzeit brechen. *Bleibt relevant unabhängig vom Familienkontext.*
21. **Kein Backup-Mechanismus** für `users.db`/Chat-Historien – `backups/`-Verzeichnis existiert, ist aber leer und wird von nichts befüllt. Bei Datenverlust sind alle Accounts/Verläufe/Kosten-Historie unwiederbringlich weg.
    **Bleibt hoch priorisiert, gerade wegen des Familienkontexts:** Es gibt keine IT-Abteilung, die das im Ernstfall wiederherstellt – verlorene Chatverläufe der eigenen Kinder sind für eine Familie echte, unwiederbringliche Historie.
22. **Kein Logging-Framework** – keine strukturierten Logs, kein Error-Tracking; rohe Exception-Texte werden teils direkt an Nutzer (auch Kinder) ausgegeben (`app.py:341,349,434`).
    **[Priorität: mittel]** Für die Fehlersuche im eigenen Familienbetrieb weiterhin nützlich, aber kein produktionskritisches Muss.
23. **Kein Kosten-Deckel**: `usage_logger.py` protokolliert Kosten nur nachträglich, keine Sperre bei Budget-Überschreitung. *Bleibt relevant unabhängig vom Familienkontext – die eigene Kreditkarte haftet für unerwartete API-Kosten.*

### A4. Dokumentations-Drift (ARCHITECTURE.md vs. Realität)

24. Doc behauptet, `users.db` sei „sensitiv und ausgeschlossen" – stimmt nur für den Docker-Build-Kontext, nicht für Git (siehe A1.1).
25. Doc behauptet Docker-Log-Rotation (max-size 10m/max-file 3) – in `docker-compose.yml` nicht konfiguriert.
26. Doc beschreibt UFW-Firewall-Schutz, der durch Docker-Portfreigaben unterlaufen sein könnte (siehe A1.9).
27. **Kein README** – Setup-Schritte für neue Entwickler (`.env` anlegen, `init_db.py` ausführen, User anlegen, App starten) sind nirgends dokumentiert.

---

## Teil B — Optimierungspotenzial (funktioniert, aber verbesserbar)

### B1. Architektur & Code-Qualität
- **Monolithisches `app.py`** (443 Zeilen) vermischt Auth, UI, DB-Zugriff, Datei-I/O und LLM-Orchestrierung ohne Funktions-/Modultrennung.
- **Duplizierte DB-Verbindungen** (`sqlite3.connect("users.db")` 5+ mal inline statt zentraler DAO-/Connection-Helper).
- **Duplizierte Kosten-Abfragen** (nahezu identischer Code in Eltern- und Admin-Dashboard, `app.py:106-147` vs. `197-225`).
- **Tote Artefakte**: leeres `backups/`- und `data/`-Verzeichnis (letzteres sogar als Docker-Volume gemountet, aber nie benutzt); verwaistes `chat_history.json` aus der allerersten Commit-Version.
- Gemischte deutsch/englische Namensgebung (`SYSTEM_PROMPT`, `AUFGABENBLATT`, Kommentare) – kein Bug, aber Konsistenz-Thema.

### B2. Performance
- Kein Connection-Pooling/Caching (`st.cache_resource` nirgends genutzt).
- Keine Indizes auf `usage(username, timestamp)` – aktuell unkritisch, wird bei Wachstum zum Full-Table-Scan-Problem.
- Chat-Historie wird bei jeder Nachricht komplett neu geschrieben – unkritisch bei aktueller Größe, aber nicht skalierend.
- „Letzte Fragen"-Feature liest bei jedem Rerun alle `chat_history_*.json`-Dateien neu ein (kein Caching).

### B3. UX / Produktqualität
- Keine Eingabevalidierung im Login (leere Felder, keine Längenbegrenzung).
- Keine Bestätigung vor destruktiver Aktion („🔄 Neues Thema beginnen" löscht sofort die Historie).
- Keine Internationalisierung (hartcodiertes Deutsch überall) – für dieses Familienprojekt aktuell kein Problem.

### B4. Nice-to-have Features (laut ARCHITECTURE.md „geplant")
- Budget-Alerts / Kostenobergrenzen pro Nutzer.
- Erweitertes Monitoring über SQL-Queries hinaus.

---

## Teil C — Entwicklungsplan (priorisiert, phasenweise)

### Phase 0 — Sofortmaßnahmen (Sicherheit)
Ziel: Sicherheitsrisiken schließen, die unabhängig von der Nutzerzahl gelten.
1. `.env`-Dateiberechtigungen auf `600` setzen (schützt den aktuell noch aktiven OpenAI-Key vor anderen lokalen Nutzern/Prozessen). **Der Widerruf des OpenAI-Keys selbst erfolgt bewusst erst in Phase 1, Schritt 14** – nachdem die Claude-Migration steht und verifiziert läuft, damit der Tutor-Chat zwischen Widerruf und fertiger Migration nicht ausfällt.
2. Alle Passwörter zurücksetzen (insbesondere die `"-"`-Platzhalter und das `reset_password.py`-Klartextpasswort).
3. ✅ Erledigt: `reset_password.py` und `create_user.py` von hartcodierten Klartext-Credentials befreien (fragen Benutzername/Passwort/Rolle jetzt interaktiv ab, Passwort via `getpass`).
4. `users.db` und `chat_history.json` aus der Git-Historie entfernen (`git filter-repo` o. ä.) und sauber in `.gitignore` halten.
5. Docker/UFW-Portfreigabe für 8501/81 prüfen und ggf. auf `127.0.0.1`-Bindung umstellen.

*(Owner-Scoping zwischen Eltern-Accounts wurde in den Backlog nach Phase 5 verschoben – im Familienkontext mit einem Elternaccount ohne praktische Wirkung.)*

### Phase 1 — Provider-Wechsel: OpenAI → Claude API
Ziel: Umstieg auf Claude, dabei zwei bestehende Bugs (Bild-Upload, entkoppelte Kostenschätzung) im selben Zug lösen.
6. Anthropic-API-Key beschaffen, als `ANTHROPIC_API_KEY` in `.env` hinterlegen; `.env.example` mit benötigten Variablen anlegen.
7. `llm_service.py` auf die Anthropic-Messages-API umstellen (`client.messages.create`), inkl. korrekter Anbindung von `usage.input_tokens`/`output_tokens`.
8. Bild-Upload korrekt implementieren (Base64-codierte Image-Content-Blocks) – behebt A2.12 im Zuge der Migration.
9. Web-Suche-Feature klären: äquivalentes Server-Tool bei Claude einbinden oder bewusst weglassen.
10. `usage_logger.py`: Preistabelle auf aktuelle Claude-Preise umstellen, an die konfigurierte Modell-Env-Var koppeln – behebt A2.15.
11. `requirements.txt`: `openai` durch `anthropic` ersetzen, mit gepinnter Version.
12. System-Prompt (`app.py:234-271`) gegen Claude testen, bei Bedarf anpassen.
13. `ARCHITECTURE.md`/README (Phase 3) entsprechend aktualisieren.
14. **Nach verifiziertem Umstieg: alten OpenAI-Key/-Account widerrufen.** Vollzug von Phase-0-Punkt 1 (dort nur die `.env`-Rechte) – bewusst hierher verschoben, damit der Tutor-Chat zwischen Widerruf und Migration nicht ausfällt.

### Phase 2 — Stabilisierung (übrige bestehende Bugs)
15. „Letzte Fragen"-Bug im Eltern-Dashboard beheben (`app.py:167-191`).
16. Bare `except:`-Blöcke durch spezifisches Exception-Handling + Logging ersetzen.
17. `init_db.py` um die fehlende `usage`-Tabelle ergänzen.

### Phase 3 — Grundlagen für nachhaltige Entwicklung
18. Minimaler Logging-Aufbau (Python `logging`-Modul).
19. Backup-Skript für `users.db` (täglicher Cron-Dump) + Rotationspolitik für Chat-Historien.
20. Restliche Abhängigkeiten pinnen + Lockfile einführen.
21. README.md mit Setup-Anleitung.

### Phase 4 — Code-Qualität & Testbarkeit (nicht dringend, siehe A3.17/18)
22. `app.py` in Module aufteilen: `auth.py`, `db.py`, `dashboards/parent.py`, `dashboards/admin.py`, `chat.py`.
23. **[Priorität: gering]** Erste Unit-Tests für `authenticate()`, DB-Zugriffsfunktionen, Kostenberechnung, History-Logik.
24. **[Priorität: gering]** Einfache CI (GitHub Actions).
25. Dead Code entfernen (`chat_history.json`, leeres `data/`-Verzeichnis).

### Phase 5 — Produkt-/Sicherheitshärtung (langfristiger Backlog, aktuell nicht dringend)
Enthält bewusst nur Punkte mit niedriger Priorität im Familienkontext.
26. **[Priorität: gering]** Owner-Scoping zwischen Eltern-Accounts – erst relevant außerhalb der eigenen Familie.
27. **[Priorität: gering]** Rate-Limiting/Lockout für Login-Versuche.
28. **[Priorität: gering]** Prompt-Injection-Härtung bei PDF-/Bild-Uploads.
29. Bestätigungsdialog vor destruktiven Aktionen (Chat-Reset).
30. Non-root-User im Docker-Image.
31. Budget-Deckel pro Nutzer/Tag.

### Reihenfolge-Logik
Phase 0 zuerst, weil hier echte Sicherheitsrisiken vorliegen, die unabhängig von der Nutzerzahl gelten (Zugangsdaten in Git-Historie/Code). Der OpenAI-Key-Widerruf selbst wandert bewusst als letzter Schritt in Phase 1 (statt an den Anfang von Phase 0), damit die Claude-Migration erst steht, bevor der alte Zugang gekappt wird – sonst hätte der Tutor-Chat eine Downtime zwischen Widerruf und fertiger Migration. Phase 2 behebt die verbleibenden, auffälligen Bugs. Phase 3 sichert die für eine Familie besonders schmerzhaften Lücken ab (v. a. Backups). Phase 4 (Tests/CI/Modularisierung) und Phase 5 (Härtung) sind bewusst nach hinten geschoben, weil sie primär für Multi-Tenant-/Team-Szenarien an Bedeutung gewinnen, die im aktuellen Familienkontext nicht vorliegen.
