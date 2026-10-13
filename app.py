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
            rows = []
            for item in data.get("events", []):
                rows.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "datum": item.get("datum"),
                    "uhrzeit": item.get("uhrzeit"),
                    "ort": item.get("ort"),
                    "created_at": item.get("created_at")
                })
            return rows
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
    return []

# Funktion, um Teilnehmer für ein Event zu laden
def get_attendees(event_id):
    try:
        response = requests.get(f"https://appdev-test.onrender.com/events/{event_id}/attendees")
        if response.status_code == 200:
            return response.json().get("attendees", [])
    except:
        pass
    return []

# Funktion, um sich einzutragen
def add_attendee(event_id, name):
    try:
        requests.post(f"https://appdev-test.onrender.com/events/{event_id}/attendees", json={"name": name})
    except:
        pass

# Events laden
events = get_events_from_server()

if not events:
    st.info("Noch keine Events gespeichert. Schicke Screenshots in die WhatsApp-Gruppe, damit sie hier auftauchen!")
else:
    for event in events:
        event_id = event["id"]
        name = event["name"]
        datum = event["datum"]
        uhrzeit = event["uhrzeit"]
        ort = event["ort"]
        
        with st.container(border=True):
            st.subheader(name if name else "Unbekanntes Event")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"📅 **Datum:** {datum}")
            with col2:
                st.write(f"⏰ **Uhrzeit:** {uhrzeit if uhrzeit else '?'}")
            with col3:
                st.write(f"📍 **Ort:** {ort}")
            
            st.markdown("---")
            
            # Teilnehmerbereich
            st.write("👥 **Teilnehmerliste:**")
            attendees = get_attendees(event_id)
            
            if attendees:
                st.write(", ".join(attendees))
            else:
                st.write("_Noch niemand eingetragen._")
            
            # Formular zum Eintragen
            with st.form(key=f"rsvp_form_{event_id}"):
                col_input, col_btn = st.columns([3, 1])
                with col_input:
                    participant_name = st.text_input("Dein Name", key=f"name_input_{event_id}", placeholder="Vorname / Name", label_visibility="collapsed")
                with col_btn:
                    submitted = st.form_submit_button("Mitmachen!")
                
                if submitted:
                    if participant_name.strip():
                        add_attendee(event_id, participant_name.strip())
                        st.success(f"{participant_name} eingetragen!")
                        st.rerun()
                    else:
                        st.warning("Bitte gib einen Namen ein.")

# Sidebar mit einem kleinen Refresh-Button
if st.button("Aktualisieren"):
    st.rerun()