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
    # Tabelle erstellen, falls sie noch gar nicht existiert
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            datum TEXT,
            uhrzeit TEXT,
            ort TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ),
        CREATE TABLE IF NOT EXISTS event_attendees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            participant_name TEXT,
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    """)

    # Automatisch prüfen, ob die Spalte 'uhrzeit' in einer älteren DB fehlt, und hinzufügen
    cursor.execute("PRAGMA table_info(events)")
    columns = [col[1] for col in cursor.fetchall()]
    if "uhrzeit" not in columns:
        cursor.execute("ALTER TABLE events ADD COLUMN uhrzeit TEXT")

    conn.commit()
    conn.close()

init_db()

def analyze_image_from_url(image_url: str):
    """Lädt ein Bild von einer URL herunter und schickt es an OpenAI"""
    today_str = datetime.now().strftime("%Y-%m-%d (%A)")
    
    response = requests.get(image_url)
    if response.status_code != 200:
        return None
        
    base64_image = base64.b64encode(response.content).decode('utf-8')

    prompt = f"""
    Du bist ein präziser Event-Assistent. Analysiere diesen Screenshot eines Event-Posters.
    Extrahiere folgende Informationen:
    - Name des Events (titel)
    - Datum des Events im Format YYYY-MM-DD (datum). Heute ist der {today_str}. Wenn ein relativer Begriff wie "Morgen" da steht, rechne es in das echte Datum um.
    - Uhrzeit des Events im Format HH:MM (z.B. "19:00" oder "20:30") (uhrzeit). Falls keine Uhrzeit das steht, setze '?'.
    - Ort des Events / Adresse / Club / Online (ort)

    Antworte AUSSCHLIESSLICH als valides JSON-Objekt mit genau diesen vier Schlüsseln:
    {{"name": "...", "datum": "...", "uhrzeit": "...", "ort": "..."}}

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
    data = await request.json()
    print("--- NEUER WEBHOOK EINGETROFFEN ---")
    print(json.dumps(data, indent=2))
    
    try:
        type_webhook = data.get("typeWebhook")
        
        if type_webhook in ["incomingMessageReceived", "outgoingMessageReceived"]:
            message_data = data.get("messageData", {})
            
            image_url = None
            if "fileMessageData" in message_data:
                image_url = message_data.get("fileMessageData", {}).get("downloadUrl")
            if not image_url and "imageMessageData" in message_data:
                image_url = message_data.get("imageMessageData", {}).get("downloadUrl")

            if image_url:
                print(f"📸 Bild-URL gefunden: {image_url}, starte KI-Analyse...")
                event_data = analyze_image_from_url(image_url)
                print(f"🤖 KI-Ergebnis: {event_data}")
                
                if event_data:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO events (name, datum, uhrzeit, ort)
                        VALUES (?, ?, ?, ?)
                    """, (
                        event_data.get("name"), 
                        event_data.get("datum"), 
                        event_data.get("uhrzeit"), 
                        event_data.get("ort")
                    ))
                    conn.commit()
                    conn.close()
                    print("✅ Event mit Uhrzeit erfolgreich gespeichert!")
            else:
                print("ℹ️ Webhook empfangen, aber keine Bild-URL (downloadUrl) in messageData gefunden.")
                
    except Exception as e:
        print("❌ Fehler beim Verarbeiten des Webhooks:", e)

    return {"status": "success"}

@app.get("/events")
def get_events_json():
    """Gibt alle gespeicherten Events als JSON zurück (für die Website)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, datum, uhrzeit, ort, created_at FROM events ORDER BY datum ASC")
    rows = cursor.fetchall()
    conn.close()
    
    events_list = []
    for row in rows:
        events_list.append({
                    "id": row[0],       
                    "name": row[1],
                    "datum": row[2],
                    "uhrzeit": row[3],
                    "ort": row[4],
                    "created_at": row[5]
        })
    return {"events": events_list}

@app.get("/events/{event_id}/attendees")
def get_attendees(event_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT participant_name FROM event_attendees WHERE event_id = ?", (event_id,))
    rows = cursor.fetchall()
    conn.close()
    return {"attendees": [row[0] for row in rows]}

@app.post("/events/{event_id}/attendees")
def add_attendee(event_id: int, data: dict):
    name = data.get("name", "").strip()
    if name:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO event_attendees (event_id, participant_name) VALUES (?, ?)", (event_id, name))
        conn.commit()
        conn.close()
        return {"status": "success"}
    return {"status": "error", "message": "Name ist leer"}

@app.get("/")
def home():
    return {"message": "EventBot Server läuft!"}

import uvicorn

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)