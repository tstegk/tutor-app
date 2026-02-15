import streamlit as st
import google.generativeai as genai
import os
import json
from PIL import Image
import io
import fitz  # PyMuPDF für PDF-Verarbeitung

# =========================================================
# 1. Konfiguration
# =========================================================

# API-Key aus .env laden
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("Kein GEMINI_API_KEY gefunden. Bitte .env prüfen.")
    st.stop()

genai.configure(api_key=api_key)

# Modell mit korrekt konfiguriertem Google Search Tool
tutor_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
)

# =========================================================
# 2. Sokratischer System-Prompt
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
# 3. Persistenter Chat-Verlauf
# =========================================================

HISTORY_FILE = "chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(messages):
    with open(HISTORY_FILE, "w") as f:
        json.dump(messages, f, indent=4)

# =========================================================
# 4. Streamlit UI
# =========================================================

st.set_page_config(page_title="Sokratischer KI-Tutor", page_icon="🧠")
st.title("🧠 Sokratischer KI-Tutor")
st.info("Ich gebe dir keine Lösungen – ich helfe dir beim Denken.")

if "messages" not in st.session_state:
    st.session_state.messages = load_history()

# Chat anzeigen
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# =========================================================
# 5. Datei-Upload (Bild oder PDF)
# =========================================================

uploaded_file = st.file_uploader(
    "Lade ein Aufgabenblatt oder Foto hoch:",
    type=["png", "jpg", "jpeg", "pdf"]
)

uploaded_image = None
uploaded_text = None

if uploaded_file:

    # --- PDF ---
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

    # --- Bild ---
    else:
        try:
            image_bytes = uploaded_file.read()
            uploaded_image = Image.open(io.BytesIO(image_bytes))
            st.image(uploaded_image, caption="Hochgeladene Aufgabe")
        except Exception as e:
            st.error(f"Fehler beim Laden des Bildes: {e}")

# =========================================================
# 6. Chat-Interaktion
# =========================================================

if prompt := st.chat_input("Was möchtest du verstehen?"):

    # User speichern
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # =============================================
            # Prompt-Konstruktion
            # =============================================

            conversation = SYSTEM_PROMPT + "\n\n"

            for msg in st.session_state.messages:
                conversation += f"{msg['role'].upper()}: {msg['content']}\n"

            # PDF-Text anhängen (falls vorhanden)
            if uploaded_text:
                conversation += "\n\nAUFGABENBLATT:\n"
                conversation += uploaded_text + "\n"

            # =============================================
            # Anfrage an Gemini
            # =============================================

            if uploaded_image:
                response = tutor_model.generate_content(
                    [conversation, uploaded_image]
                )
            else:
                response = tutor_model.generate_content(conversation)

            full_response = response.text

            st.markdown(full_response)

            # Speichern
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )

            save_history(st.session_state.messages)

        except Exception as e:
            st.error(f"Fehler bei der Generierung: {e}")

# =========================================================
# 7. Reset-Funktion
# =========================================================

if st.button("🔄 Neues Thema beginnen"):
    st.session_state.messages = []
    save_history([])
    st.rerun()

