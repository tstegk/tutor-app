# CLAUDE.md

Sokratischer KI-Tutor – privates Familienprojekt (ein Elternaccount, Kinder-Accounts), keine öffentliche Multi-Tenant-Anwendung.

## Stack
- Python 3.11, Streamlit (UI und "Backend" in einem – kein separates API-Layer)
- SQLite (`users.db`): `users`-Tabelle (Auth, bcrypt) + `usage`-Tabelle (Kosten-Tracking)
- LLM-Anbindung über `llm_service.py` (aktuell OpenAI, Migration zu Claude/Anthropic geplant – siehe TECH_ASSESSMENT.md Phase 1)
- Deployment: Docker Compose + nginx-proxy-manager (Details: ARCHITECTURE.md)

## Setup / lokal starten
- `.env` mit API-Key + Modell-Env-Var anlegen
- `python init_db.py` (Achtung: legt aktuell nur die `users`-Tabelle an, nicht `usage` – siehe TECH_ASSESSMENT.md A2.14)
- Nutzer anlegen über `create_user.py` (lokal, absichtlich nicht in Git)
- `streamlit run app.py`

## Wichtige Dateien
- `app.py` – gesamte App (Auth, Eltern-/Admin-Dashboard, Chat) in einer Datei
- `llm_service.py` – Wrapper um die LLM-API
- `usage_logger.py` – Kosten-/Token-Tracking

## Konventionen
- UI-Texte und Kommentare durchgängig Deutsch
- Solo-/Familienprojekt ohne Team-Review-Prozess – Tests/CI sind bewusst (noch) niedrig priorisiert

## Vorsicht
- `users.db`, `.env`, `chat_history_*.json` nie committen
- `create_user.py` / `reset_password.py` enthalten bzw. erzeugen Zugangsdaten – bleiben absichtlich außerhalb von Git

## Vor jedem Commit
- `git status` / `git diff --cached` prüfen, bevor committet wird
- Sicherstellen, dass `users.db`, `.env` und `chat_history_*.json` **nicht** gestaged sind (`users.db` wurde in der Vergangenheit versehentlich mit-committed, siehe TECH_ASSESSMENT.md A1.1)

## Siehe auch
- `ARCHITECTURE.md` – Infrastruktur/Deployment
- `TECH_ASSESSMENT.md` – Technical Debt & Entwicklungsplan (inkl. Familienkontext-Priorisierung)
