import streamlit as st
import sqlite3

# Titel der Website
st.title("🎉 Unser Gruppen-Event-Tracker")
st.write("Hier sind alle Events aus unserem WhatsApp-Chat, die der Bot gefunden hat:")

# Funktion, um Events aus der Datenbank zu holen
def get_events():
    conn = sqlite3.connect("events.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, datum, ort, created_at FROM events ORDER BY datum ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

# Events laden
events = get_events()

if not events:
    st.info("Noch keine Events gespeichert. Schicke Screenshots an den Bot, damit sie hier auftauchen!")
else:
    # Tabelle oder schöne Karten anzeigen
    for name, datum, ort, created in events:
        with st.container(border=True):
            st.subheader(name)
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"📅 **Datum:** {datum}")
            with col2:
                st.write(f"📍 **Ort:** {ort}")
            st.caption(f"Hinzugefügt am: {created}")

# Sidebar mit einem kleinen Refresh-Button
if st.button("Aktualisieren"):
    st.rerun()