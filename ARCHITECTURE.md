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

### System Diagram
Internet
       │
       ▼
┌─────────────────────────┐
│ Nginx Proxy Manager │
│ Reverse Proxy + SSL │
│ Ports: 80 / 443 │
└─────────────┬───────────┘
│
▼
┌─────────────────────────┐
│ tutor-app container │
│ Streamlit Application │
│ Port: 8501 (internal) │
└─────────────┬───────────┘
│
▼
┌─────────────────────────┐
│ Application Layer │
│ app.py │
│ UI + Authentication │
└─────────────┬───────────┘
│
▼
┌─────────────────────────┐
│ LLM Service Layer │
│ llm_service.py │
│ Anthropic API Integration│
└─────────────┬───────────┘
│
▼
┌─────────────────────────┐
│ Anthropic Claude API │
│ Claude Sonnet 5 + Web Search│
└─────────────┬───────────┘
│
▼
┌─────────────────────────┐
│ SQLite Database │
│ users.db │
│ users + usage tables │
└─────────────────────────┘

### Backend Stack
- Streamlit
- Anthropic Claude API (claude-sonnet-5)
- SQLite (users.db)
- bcrypt password hashing
- PyMuPDF for PDF parsing

### LLM Abstraction Layer
- `llm_service.py`
- Provider decoupled from UI
- Model configurable via ENV:
  - ANTHROPIC_MODEL
- Web search server tool enabled (`web_search_20260209`)
- Max token limit configured (default 800)

Architecture pattern:

UI (app.py)
    ↓
LLM Service (llm_service.py)
    ↓
Anthropic Messages API
    ↓
Formatted output + usage metadata

> **Providerwechsel (2026):** Ursprünglich lief die App über die OpenAI Responses API
> (gpt-4.1). Im Zuge einer Sicherheitsbereinigung (siehe `TECH_ASSESSMENT.md`, Phase 1)
> wurde auf die Anthropic Claude API umgestellt – u.a. weil dabei zwei bestehende Bugs
> (nicht funktionierender Bild-Upload, an das Modell entkoppelte Kostenschätzung) im
> selben Zug behoben werden konnten.

---

## 5. Authentication & Roles

- Role-based login
- Roles:
  - child
  - parent
  - admin
- Passwords stored as bcrypt hashes
- Session state handled via Streamlit

Parent users access a monitoring dashboard instead of the tutor chat interface.

The dashboard provides:

- daily activity per child
- total system cost
- cost per child
- recent questions (with timestamps)

---

## 6. Data Persistence

- users.db → user credentials
- chat_history_<username>.json → user-specific chat history
- Docker log rotation enabled:
  - max-size: 10m
  - max-file: 3

Each message entry may include a timestamp field:

{
 "role": "user",
 "content": "...",
 "timestamp": "ISO8601 datetime"
}

This timestamp is used for activity monitoring in the parent dashboard.

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

## 8. Cost & Usage Management

### Token Usage Logging

Each LLM request logs:

- username
- prompt_tokens
- completion_tokens
- total_tokens
- estimated_cost
- timestamp

Storage:

SQLite table `usage`.

### Cost Calculation

Pricing model, keyed by the configured `ANTHROPIC_MODEL` (see `usage_logger.py`):

- claude-sonnet-5 (current default): $2.00 / 1M input tokens, $10.00 / 1M output tokens
- claude-opus-5: $5.00 / 1M input tokens, $25.00 / 1M output tokens
- claude-haiku-4-5: $1.00 / 1M input tokens, $5.00 / 1M output tokens

Cost estimate calculated per request. Unlike the previous OpenAI-only implementation,
this is no longer hardcoded to a single model — an unrecognized `ANTHROPIC_MODEL`
falls back to Sonnet-5 pricing with a console warning instead of silently using the
wrong numbers.

### Admin Cost Monitoring

Admin users can view:

- total system cost
- cost per user

Displayed in Streamlit sidebar.

### Planned Enhancements

- monthly cost aggregation
- budget limits
- cost alerts

---

## 9. Conversation Context Management

To control token usage, conversation history sent to the model is limited.

MAX_HISTORY = 10

Only the most recent messages are included in the prompt.

Older messages remain stored locally but are not sent to the LLM.

Benefits:

- significantly reduced token usage
- improved latency
- stable context size

---

## 10. Repository Hygiene

Operational scripts are excluded from version control.

Examples:

- `create_user.py`
- `reset_password.py`

These scripts are ignored via `.gitignore`.

Sensitive runtime files excluded from repository:

- `.env`
- `users.db`
- chat histories
- nginx runtime data

---

## 11. Monitoring & Debugging

System monitoring currently possible via:

- SQLite queries
- Admin UI cost dashboard
- Docker logs

Example queries:

Total cost:
SELECT SUM(cost_estimate) FROM usage;

Cost per user:
SELECT username, SUM(cost_estimate)
FROM usage
GROUP BY username;

## 12. Change Log (High-Level)

Initial system setup:

- Dockerized Streamlit application
- Reverse proxy with Nginx Proxy Manager
- SSL via Let's Encrypt

Security hardening:

- SSH key authentication
- UFW firewall
- Fail2Ban intrusion protection

AI backend evolution:

- Removed Gemini SDK
- Migrated to OpenAI GPT-4.1
- Introduced LLM abstraction layer

Operational improvements:

- Token usage logging implemented
- Cost calculation integrated
- Admin cost dashboard added
- Chat history token optimization implemented
- Repository hygiene improvements

Parent monitoring dashboard implemented:
- daily activity tracking
- recent questions view
- timestamp support in chat history

LLM provider migration (2026):
- Migrated from OpenAI (gpt-4.1) to Anthropic Claude (claude-sonnet-5)
- Fixed image upload (proper base64 encoding instead of a raw PIL object)
- Cost table decoupled from a single hardcoded model, keyed by `ANTHROPIC_MODEL`
- Old OpenAI API key revoked after migration was verified (text, web search, and
  image analysis tested against the live Claude API before cutover)