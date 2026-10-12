import streamlit as st
import requests

# Titel der Website
st.title("🎉 UCSD Internationals Events")
st.write("Hier sind alle Events aus unserem WhatsApp-Chat, die der Bot gefunden hat:")

# Funktion, um Events von deinem Render-Server zu holen
def get_events_from_server():
    try:
        response = requests.get("https://appdev-test.onrender.com/events")
        if response.status_code == 200:
            data = response.json()
            # Wir wandeln das JSON in dasselbe Format um, das deine Schleife erwartet (name, datum, ort, created_at)
            rows = []
            for item in data.get("events", []):
                rows.append((
                    item.get("name"),
                    item.get("datum"),
                    item.get("ort"),
                    item.get("created_at")
                ))
            return rows
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
    return []

# Events laden
events = get_events_from_server()

if not events:
    st.info("Noch keine Events gespeichert. Schicke Screenshots in die WhatsApp-Gruppe, damit sie hier auftauchen!")
else:
    # Tabelle oder schöne Karten anzeigen
    for name, datum, ort, created in events:
        with st.container(border=True):
            st.subheader(name if name else "Unbekanntes Event")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"📅 **Datum:** {datum}")
            with col2:
                st.write(f"📍 **Ort:** {ort}")
            st.caption(f"Hinzugefügt am: {created}")

# Sidebar mit einem kleinen Refresh-Button
if st.button("Aktualisieren"):
    st.rerun()