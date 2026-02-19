# KI Tutor – System Architecture

## 1. Server Infrastructure

- VServer
- 2 vCPU
- 4 GB RAM
- 60+ GB SSD
- Ubuntu Cloud Image
- Docker Engine + Docker Compose v2

---

## 2. Security Configuration

### SSH
- SSH Key Authentication only
- PasswordAuthentication: disabled
- PermitRootLogin: disabled
- Dedicated sudo user (tobias)
- User added to docker group

### HTTPS / Reverse Proxy
- Nginx Proxy Manager
- Let's Encrypt SSL certificates
- No external Basic Authentication
- Authentication handled exclusively at application layer

### Firewall
- UFW enabled
- Default deny incoming
- Allowed ports: 22, 80, 443

---

## 3. Container Architecture

Docker Compose services:

- tutor-app (Streamlit)
- nginx-proxy (Reverse Proxy)

Ports:
- 80 / 443 → Nginx
- 8501 → internal Streamlit

- Log rotation enabled (max-size 10m, max-file 3)

---

## 4. Application Architecture

### Backend
- Streamlit
- Google Gemini API (gemini-2.0-flash)
- SQLite (users.db)
- bcrypt password hashing
- PyMuPDF for PDF parsing

### Role Model
- child
- parent
- admin

### Authentication
- Role-based login
- Session state stored in Streamlit
- Passwords hashed with bcrypt

---

## 5. Data Persistence

- users.db → user credentials
- chat_history_<username>.json → user-specific chat history
- data/ directory for extensions

---

## 6. AI Behavior

- Socratic tutoring approach
- No direct solution policy
- Supports:
  - Text prompts
  - Image uploads
  - PDF text extraction

---

## 7. Current Security Level

- Encrypted transport (HTTPS)
- SSH hardened
- No root login
- No password authentication
- Hashed credentials
- API key not stored in source code

---

## 8. Future Extensions

- Parent dashboard
- Admin UI
- Learning progress tracking
- Multi-app setup (Support Bot)
- Monitoring & log management
