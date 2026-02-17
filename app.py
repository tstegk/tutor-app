import streamlit as st
import google.generativeai as genai
import os
import json
from PIL import Image
import io
import fitz
import sqlite3
import bcrypt

# =========================================================
# 1. Konfiguration
# =========================================================

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("Kein GEMINI_API_KEY gefunden. Bitte .env prüfen.")
    st.stop()

genai.configure(api_key=api_key)

tutor_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
)

# =========================================================
# 2. AUTHENTIFIZIERUNG (NEU)
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
# 3. UI HEADER
# =========================================================

st.set_page_config(page_title="Sokratischer KI-Tutor", page_icon="🧠")
st.title("🧠 Sokratischer KI-Tutor")
st.info("Ich gebe dir keine Lösungen – ich helfe dir beim Denken.")

# =========================================================
# 4. LOGIN-MASKE
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
# 5. SIDEBAR (User + Rolle + Logout)
# =========================================================

st.sidebar.write(f"Angemeldet als: {st.session_state.user}")
st.sidebar.write(f"Rolle: {st.session_state.role}")

if st.sidebar.button("Abmelden"):
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

# =========================================================
# 6. Sokratischer System-Prompt
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

Ziel:
Nicht Antworten liefern, sondern Denkfähigkeit fördern.
"""

# =========================================================
# 7. USER-SPEZIFISCHE HISTORY (NEU)
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
# 8. CHAT ANZEIGEN
# =========================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# =========================================================
# 9. Datei-Upload (Bild oder PDF)
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
# 10. CHAT-INTERAKTION
# =========================================================

if prompt := st.chat_input("Was möchtest du verstehen?"):

    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            conversation = SYSTEM_PROMPT + "\n\n"

            for msg in st.session_state.messages:
                conversation += f"{msg['role'].upper()}: {msg['content']}\n"

            if uploaded_text:
                conversation += "\n\nAUFGABENBLATT:\n"
                conversation += uploaded_text + "\n"

            if uploaded_image:
                response = tutor_model.generate_content(
                    [conversation, uploaded_image]
                )
            else:
                response = tutor_model.generate_content(conversation)

            full_response = response.text

            st.markdown(full_response)

            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )

            save_history(st.session_state.messages)

        except Exception as e:
            st.error(f"Fehler bei der Generierung: {e}")

# =========================================================
# 11. RESET
# =========================================================

if st.button("🔄 Neues Thema beginnen"):
    st.session_state.messages = []
    save_history([])
    st.rerun()
