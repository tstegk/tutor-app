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
│ OpenAI API Integration │
└─────────────┬───────────┘
│
▼
┌─────────────────────────┐
│ OpenAI API │
│ GPT-4.1 + Web Search │
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

Approximate pricing model (gpt-4.1):

- Prompt tokens: $0.03 / 1K tokens
- Completion tokens: $0.06 / 1K tokens

Cost estimate calculated per request.

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