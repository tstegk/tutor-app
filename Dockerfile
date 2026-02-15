# 1. Basis-Image mit Python 3.11
FROM python:3.11-slim

# 2. Arbeitsverzeichnis im Container festlegen
WORKDIR /app

# 3. System-Abhängigkeiten installieren (für Pillow und Netzwerk)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Requirements kopieren und Bibliotheken installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Den Rest des Codes kopieren (app.py etc.)
COPY . .

# 6. Den Port für Streamlit freigeben
EXPOSE 8501

# 7. Startbefehl für die App
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
