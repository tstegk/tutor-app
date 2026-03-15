import streamlit as st
import os
import json
from PIL import Image
import io
import fitz
import sqlite3
import bcrypt

from llm_service import generate_response
from usage_logger import log_usage


# =========================================================
# 1. AUTHENTIFIZIERUNG
# =========================================================

def authenticate(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT password_hash, role FROM users WHERE username = ?",
        (username,)
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        stored_hash, role = result
        if bcrypt.checkpw(password.encode(), stored_hash.encode()):
            return True, role

    return False, None


if "user" not in st.session_state:
    st.session_state.user = None

if "role" not in st.session_state:
    st.session_state.role = None


# =========================================================
# 2. UI HEADER
# =========================================================

st.set_page_config(page_title="Sokratischer KI-Tutor", page_icon="🧠")
st.title("🧠 Sokratischer KI-Tutor")
st.info("Ich gebe dir keine Lösungen – ich helfe dir beim Denken.")


# =========================================================
# 3. LOGIN
# =========================================================

if not st.session_state.user:
    st.subheader("Login")

    username = st.text_input("Benutzername")
    password = st.text_input("Passwort", type="password")

    if st.button("Anmelden"):
        success, role = authenticate(username, password)

        if success:
            st.session_state.user = username
            st.session_state.role = role
            st.success(f"Willkommen {username} ({role})")
            st.rerun()
        else:
            st.error("Falsche Zugangsdaten")

    st.stop()


# =========================================================
# 4. SIDEBAR
# =========================================================

st.sidebar.write(f"Angemeldet als: {st.session_state.user}")
st.sidebar.write(f"Rolle: {st.session_state.role}")

if st.sidebar.button("Abmelden"):
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

# ADMIN KOSTENÜBERSICHT

if st.session_state.role == "admin":

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Systemkosten")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Gesamtkosten
    cursor.execute("SELECT SUM(cost_estimate) FROM usage")
    total_cost = cursor.fetchone()[0]

    if total_cost:
        st.sidebar.write(f"Gesamtkosten: ${total_cost:.2f}")
    else:
        st.sidebar.write("Noch keine Kosten")

    st.sidebar.markdown("#### Kosten pro Nutzer")

    cursor.execute("""
    SELECT username, SUM(cost_estimate)
    FROM usage
    GROUP BY username
    """)

    rows = cursor.fetchall()

    for user, cost in rows:
        st.sidebar.write(f"{user}: ${cost:.2f}")

    conn.close()


# =========================================================
# 5. SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
Du bist ein sokratischer KI-Tutor für Kinder.

Regeln:
- Gib niemals direkt die vollständige Lösung einer Aufgabe.
- Stelle gezielte, schrittweise Fragen.
- Zerlege komplexe Probleme in kleine Denk-Schritte.
- Fordere aktives Mitdenken.
- Wenn das Kind ausdrücklich nach der Lösung fragt:
  -> Gib Hinweise, aber keine vollständige Lösung.
- Verwende einfache Sprache.
- Lobe Denkansätze und korrigiere sanft.
- Wenn du Informationen aus dem Internet nutzt:
  -> Verwende nur seriöse Quellen.
  -> Gib die Quelle am Ende kurz an.

Ziel:
Nicht Antworten liefern, sondern Denkfähigkeit fördern.
"""

MAX_HISTORY = 10
# =========================================================
# 6. USER-SPEZIFISCHE HISTORY
# =========================================================

def get_history_file():
    return f"chat_history_{st.session_state.user}.json"

def load_history():
    file = get_history_file()
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(messages):
    file = get_history_file()
    with open(file, "w") as f:
        json.dump(messages, f, indent=4)

if "messages" not in st.session_state:
    st.session_state.messages = load_history()


# =========================================================
# 7. CHAT ANZEIGEN
# =========================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# =========================================================
# 8. DATEI-UPLOAD
# =========================================================

uploaded_file = st.file_uploader(
    "Lade ein Aufgabenblatt oder Foto hoch:",
    type=["png", "jpg", "jpeg", "pdf"]
)

uploaded_image = None
uploaded_text = None

if uploaded_file:

    if uploaded_file.type == "application/pdf":
        try:
            pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            text = ""

            for page in pdf:
                text += page.get_text()

            uploaded_text = text.strip()

            if uploaded_text:
                st.success("PDF-Text erfolgreich extrahiert.")
                with st.expander("Extrahierter Text anzeigen"):
                    st.text(uploaded_text)
            else:
                st.warning("Kein Text im PDF gefunden (evtl. Scan ohne OCR).")

        except Exception as e:
            st.error(f"Fehler beim Verarbeiten des PDFs: {e}")

    else:
        try:
            image_bytes = uploaded_file.read()
            uploaded_image = Image.open(io.BytesIO(image_bytes))
            st.image(uploaded_image, caption="Hochgeladene Aufgabe")
        except Exception as e:
            st.error(f"Fehler beim Laden des Bildes: {e}")


# =========================================================
# 9. CHAT INTERAKTION
# =========================================================

if prompt := st.chat_input("Was möchtest du verstehen?"):

    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        try:
            # Nachrichtenstruktur für OpenAI
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
            ]

            recent_messages = st.session_state.messages[-MAX_HISTORY:]

            for msg in recent_messages:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            if uploaded_text:
                messages.append({
                    "role": "user",
                    "content": f"AUFGABENBLATT:\n{uploaded_text}"
                })

            if uploaded_image:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Bitte analysiere dieses Bild:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": uploaded_image
                            }
                        }
                    ]
                })

            llm_result = generate_response(
                messages,
                enable_web_search=True,
                max_tokens=800
            )

            full_response = llm_result["text"]
            usage = llm_result["usage"]

            # Gebühren-Logging
            cost = log_usage(
                st.session_state.user,
                usage["prompt_tokens"],
                usage["completion_tokens"],
                usage["total_tokens"]
            )

            st.markdown(full_response)

            # Optional: Kosten unter prompt anzeigen anzeigen
            # st.caption(f"Geschätzte API-Kosten dieser Antwort: ${cost:.4f}")

            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )

            save_history(st.session_state.messages)

        except Exception as e:
            st.error(f"Fehler bei der Generierung: {e}")


# =========================================================
# 10. RESET
# =========================================================

if st.button("🔄 Neues Thema beginnen"):
    st.session_state.messages = []
    save_history([])
    st.rerun()