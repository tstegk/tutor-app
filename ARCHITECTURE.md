# KI Tutor – System Architecture

---

## 1. Server Infrastructure

- VServer (Upgrade durchgeführt)
- 2 vCPU
- 4 GB RAM
- 60+ GB SSD
- Ubuntu Cloud Image
- Docker Engine + Docker Compose v2

---

## 2. Security Configuration

### SSH
- SSH Key Authentication only
- PasswordAuthentication disabled
- PermitRootLogin disabled
- Dedicated sudo user (tobias)
- User added to docker group

### Firewall
- UFW enabled
- Default: deny incoming
- Allowed ports:
  - 22 (SSH)
  - 80 (HTTP)
  - 443 (HTTPS)

### Intrusion Protection
- Fail2Ban active (SSH protection)

### HTTPS / Reverse Proxy
- Nginx Proxy Manager
- Let's Encrypt SSL certificates
- No external Basic Authentication
- Authentication handled exclusively at application layer

---

## 3. Container Architecture

Docker Compose services:

- tutor-app (Streamlit)
- nginx-proxy (Reverse Proxy)

Ports:
- 80 / 443 → Nginx
- 8501 → internal Streamlit (not publicly exposed via firewall)

Persistent Data:
- nginx/data
- nginx/letsencrypt

Build Isolation:
- `.dockerignore` excludes:
  - nginx/
  - users.db
  - chat_history_*
  - .env

---

## 4. Application Architecture

### Backend Stack
- Streamlit
- OpenAI API (gpt-4.1)
- SQLite (users.db)
- bcrypt password hashing
- PyMuPDF for PDF parsing

### LLM Abstraction Layer
- `llm_service.py`
- Provider decoupled from UI
- Model configurable via ENV:
  - OPENAI_MODEL
- Web search tool enabled
- Max token limit configured (default 800)

Architecture pattern:

UI (app.py)
    ↓
LLM Service (llm_service.py)
    ↓
OpenAI Responses API
    ↓
Formatted output + usage metadata

---

## 5. Authentication & Roles

- Role-based login
- Roles:
  - child
  - parent
  - admin
- Passwords stored as bcrypt hashes
- Session state handled via Streamlit

---

## 6. Data Persistence

- users.db → user credentials
- chat_history_<username>.json → user-specific chat history
- Docker log rotation enabled:
  - max-size: 10m
  - max-file: 3

---

## 7. AI Behavior

- Socratic tutoring approach
- No direct solution policy
- Supports:
  - Text prompts
  - PDF uploads
  - Image uploads
  - Optional web search integration
- Sources required when web search is used

---

## 8. Cost & Usage Management (Planned)

- Token usage returned per request
- Usage logging to be implemented
- Estimated cost calculation per request
- Monthly usage monitoring planned

---

## 9. Change Log (High-Level)

- Removed Gemini SDK
- Switched to OpenAI (gpt-4.1)
- Introduced LLM abstraction layer
- Enabled Web Search tool
- Implemented firewall (UFW)
- Installed Fail2Ban
- Enabled Docker log rotation
- Removed Nginx Basic Auth