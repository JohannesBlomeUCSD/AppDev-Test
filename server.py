import os
import json
import sqlite3
from fastapi import FastAPI, Request
from openai import OpenAI
from datetime import datetime
import requests
import base64

app = FastAPI()
client = OpenAI()
DB_NAME = "events.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            datum TEXT,
            ort TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def analyze_image_from_url(image_url: str):
    """Lädt ein Bild von einer URL herunter und schickt es an OpenAI"""
    today_str = datetime.now().strftime("%Y-%m-%d (%A)")
    
    # Bild von der URL herunterladen
    response = requests.get(image_url)
    if response.status_code != 200:
        return None
        
    base64_image = base64.b64encode(response.content).decode('utf-8')

    prompt = f"""
    Du bist ein präziser Event-Assistent. Analysiere diesen Screenshot eines Event-Posters.
    Extrahiere folgende Informationen:
    - Name des Events (titel)
    - Datum des Events im Format YYYY-MM-DD (datum). Heute ist der {today_str}. Wenn ein relativer Begriff wie "Morgen" da steht, rechne es in das echte Datum um.
    - Ort des Events / Adresse / Club / Online (ort)

    Antworte AUSSCHLIESSLICH als valides JSON-Objekt mit genau diesen drei Schlüsseln:
    {{"name": "...", "datum": "...", "ort": "..."}}

    Wenn eine Information im Bild absolut nicht zu finden ist, setze stattdessen ein einzelnes Fragezeichen '?' ein.
    """

    ai_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        response_format={"type": "json_object"}
    )

    return json.loads(ai_response.choices[0].message.content)

@app.post("/whatsapp-webhook")
async def whatsapp_webhook(request: Request):
    """
    Empfängt die Daten vom WhatsApp-Dienst, filtert Bilder heraus und verarbeitet sie.
    """
    data = await request.json()
    
    # Hinweis: Die Struktur hängt leicht vom genauen WhatsApp-Dienst ab (z.B. Green-API).
    # Hier fangen wir typischerweise die Bild-URL ab:
    try:
        # Beispielhafter Zugriff auf das Bild (abhängig vom Gateway)
        # Viele Dienste senden eine Nachricht, die einen Bild-Link enthält.
        message_data = data.get("messageData", {})
        file_message_data = message_data.get("fileMessageData", {})
        image_url = file_message_data.get("downloadUrl") # URL des Bildes bei WhatsApp
        
        if image_url:
            print("Bild empfangen, starte KI-Analyse...")
            event_data = analyze_image_from_url(image_url)
            
            if event_data:
                # In SQLite-Datenbank speichern
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO events (name, datum, ort)
                    VALUES (?, ?, ?)
                """, (event_data.get("name"), event_data.get("datum"), event_data.get("ort")))
                conn.commit()
                conn.close()
                print("✅ Event erfolgreich aus WhatsApp-Bild extrahiert und gespeichert!")
                
    except Exception as e:
        print("Fehler beim Verarbeiten des Webhooks:", e)

    return {"status": "success"}

@app.get("/")
def home():
    return {"message": "EventBot Server läuft!"}

import uvicorn

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)