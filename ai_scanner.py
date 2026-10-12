import os
import json
import sqlite3
from openai import OpenAI
from datetime import datetime

client = OpenAI()
DB_NAME = "events.db"

def init_db():
    """Erstellt die Datenbank und die Tabelle, falls sie noch nicht existieren."""
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

def save_event_to_db(event_data: dict):
    """Speichert ein extrahiertes Event in der SQLite-Datenbank."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (name, datum, ort)
        VALUES (?, ?, ?)
    """, (event_data.get("name"), event_data.get("datum"), event_data.get("ort")))
    conn.commit()
    conn.close()
    print("✅ Event erfolgreich in der Datenbank gespeichert!")

def get_all_events():
    """Gibt alle gespeicherten Events aus der Datenbank zurück."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, datum, ort, created_at FROM events")
    rows = cursor.fetchall()
    conn.close()
    return rows

def analyze_event_image(image_path: str):
    today_str = datetime.now().strftime("%Y-%m-%d (%A)")
    
    ext = os.path.splitext(image_path)[1].lower()
    if ext == ".png":
        mime_type = "image/png"
    elif ext in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    else:
        mime_type = "image/jpeg"

    import base64
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')

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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        response_format={"type": "json_object"}
    )

    result_json = json.loads(response.choices[0].message.content)
    return result_json

if __name__ == "__main__":
    # 1. Datenbank initialisieren
    init_db()

    test_image = "test_event.png" # oder .jpg
    
    if os.path.exists(test_image):
        print(f"Analysiere Bild '{test_image}'...")
        event_data = analyze_event_image(test_image)
        print("\nErgebnis von der KI:")
        print(json.dumps(event_data, indent=4, ensure_ascii=False))
        
        # 2. In Datenbank speichern
        save_event_to_db(event_data)
        
        # 3. Alle gespeicherten Events anzeigen, um zu testen
        print("\n--- Aktuelle Events in der Datenbank ---")
        all_events = get_all_events()
        for ev in all_events:
            print(f"ID: {ev[0]} | Event: {ev[1]} | Datum: {ev[2]} | Ort: {ev[3]}")
            
    else:
        print(f"Hinweis: Bitte lege ein Testbild namens '{test_image}' in denselben Ordner!")