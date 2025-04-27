import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta
from plyer import notification
import time
from bson import ObjectId

# ---- MongoDB Connection ----
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client["pregnancy_reminders"]
reminders_collection = db["reminders"]

# ---- Streamlit UI Styling ----
st.set_page_config(page_title="Pregnancy Reminder System", page_icon="🤰", layout="wide")

# Sidebar
with st.sidebar:
    st.image("https://img.freepik.com/free-vector/pregnant-woman-holding-belly-cartoon-illustration_138676-2915.jpg", width=250)
    st.markdown("### 🤰 **Pregnancy Reminder System**")
    st.write("Keep track of your important pregnancy milestones with reminders.")
    st.info("🔔 Get notifications for doctor visits, medication, hydration, diet, and more!")

# ---- Main Title ----
st.markdown("<h1 style='text-align: center; color: #E75480;'>Pregnancy Reminder System</h1>", unsafe_allow_html=True)
st.write("👶 Welcome to the **Pregnancy Reminder System**. Keep track of your pregnancy milestones and important dates.")

# ---- Reminder Input ----
st.subheader("📅 Add a New Reminder")
col1, col2 = st.columns(2)

with col1:
    reminder_type = st.selectbox(
        "Select Reminder Type:",
        ["Doctor Visit", "Medication", "Hydration", "Exercise", "Diet", "Others"]
    )
    message = st.text_area("Enter Reminder Message:")

with col2:
    date = st.date_input("Select Date:")
    reminder_time = st.time_input("Select Time:")
    recurrence = st.selectbox("Set Recurrence", ["None", "Daily", "Weekly", "Monthly"])

if st.button("➕ Add Reminder", use_container_width=True):
    reminder_data = {
        "type": reminder_type,
        "message": message,
        "date_time": datetime.combine(date, reminder_time),
        "status": "Pending",
        "recurrence": recurrence
    }

    # Set next reminder based on recurrence
    if recurrence == "Daily":
        reminder_data["next_reminder"] = reminder_data["date_time"] + timedelta(days=1)
    elif recurrence == "Weekly":
        reminder_data["next_reminder"] = reminder_data["date_time"] + timedelta(days=7)
    elif recurrence == "Monthly":
        reminder_data["next_reminder"] = reminder_data["date_time"] + timedelta(days=30)
    else:
        reminder_data["next_reminder"] = reminder_data["date_time"]

    reminders_collection.insert_one(reminder_data)
    st.success("✅ Reminder added successfully!")

# ---- Function to Check & Send Notifications ----
def check_reminders():
    now = datetime.now()
    reminders = list(reminders_collection.find({"date_time": {"$lte": now}, "status": "Pending"}))

    for reminder in reminders:
        # Desktop Notification
        notification.notify(
            title="🍼 Pregnancy Reminder",
            message=f"{reminder['type']}: {reminder['message']}",
            timeout=5
        )

        # Streamlit Toast Notification
        st.toast(f"🔔 {reminder['type']}: {reminder['message']}")

        # Mark as Sent
        reminders_collection.update_one({"_id": reminder["_id"]}, {"$set": {"status": "Sent"}})

# ---- Function to Edit a Reminder ----
def edit_reminder(reminder_id):
    reminder = reminders_collection.find_one({"_id": ObjectId(reminder_id)})

    if reminder:
        with st.form(f"edit_form_{reminder_id}"):
            new_message = st.text_area("Update Message", reminder["message"])
            new_date = st.date_input("Update Date", reminder["date_time"].date())
            new_time = st.time_input("Update Time", reminder["date_time"].time())
            new_recurrence = st.selectbox(
                "Update Recurrence",
                ["None", "Daily", "Weekly", "Monthly"],
                index=["None", "Daily", "Weekly", "Monthly"].index(reminder.get("recurrence", "None"))
            )

            submitted = st.form_submit_button("Update Reminder")

            if submitted:
                updated_data = {
                    "message": new_message,
                    "date_time": datetime.combine(new_date, new_time),
                    "recurrence": new_recurrence,
                    "status": "Pending"
                }

                # Update next_reminder based on recurrence
                if new_recurrence == "Daily":
                    updated_data["next_reminder"] = updated_data["date_time"] + timedelta(days=1)
                elif new_recurrence == "Weekly":
                    updated_data["next_reminder"] = updated_data["date_time"] + timedelta(days=7)
                elif new_recurrence == "Monthly":
                    updated_data["next_reminder"] = updated_data["date_time"] + timedelta(days=30)
                else:
                    updated_data["next_reminder"] = updated_data["date_time"]

                # Update in MongoDB
                reminders_collection.update_one({"_id": ObjectId(reminder_id)}, {"$set": updated_data})

                st.success("✅ Reminder updated successfully!")
                st.experimental_rerun()
    else:
        st.error("🚫 Reminder not found!")

# ---- Display Upcoming Reminders ----
st.subheader("📌 Upcoming Reminders")

reminders = list(reminders_collection.find({"date_time": {"$gte": datetime.now()}}))

if reminders:
    df = pd.DataFrame(reminders, columns=["type", "message", "date_time", "status"])
    st.dataframe(df.style.set_properties(**{'background-color': '#FFE4E1', 'color': 'black'}))
else:
    st.write("🚫 No upcoming reminders found.")

# ---- Start Notification Service ----
if st.button("🔔 Start Notification Service", use_container_width=True):
    st.warning("⏳ Notifications are running in the background...")
    while True:
        check_reminders()
        time.sleep(60)

# ---- Search Functionality ----
search_term = st.text_input("🔍 Search Reminders by Keyword")

if search_term:
    reminders = list(reminders_collection.find({
        "$or": [
            {"message": {"$regex": search_term, "$options": "i"}},
            {"type": {"$regex": search_term, "$options": "i"}}
        ]
    }))
else:
    reminders = list(reminders_collection.find({"date_time": {"$gte": datetime.now()}}))

# Display Search Results
st.subheader("📌 Search Results" if search_term else "📌 Upcoming Reminders")

if reminders:
    df = pd.DataFrame(reminders, columns=["type", "message", "date_time", "status"])
    st.dataframe(df.style.set_properties(**{'background-color': '#FFE4E1', 'color': 'black'}))
else:
    st.write("🚫 No matching reminders found.")

# ---- Editing Feature ----
for reminder in reminders:
    with st.expander(f"Reminder: {reminder['type']}"):
        st.write(f"Message: {reminder['message']}")
        st.write(f"Date: {reminder['date_time']}")
        st.button("Edit", key=str(reminder["_id"]), on_click=edit_reminder, args=(str(reminder["_id"]),))

# ---- Statistics ----
total_reminders = reminders_collection.count_documents({})
completed_reminders = reminders_collection.count_documents({"status": "Sent"})
pending_reminders = total_reminders - completed_reminders

st.subheader("📊 Statistics")
st.write(f"Total Reminders: {total_reminders}")
st.write(f"Completed Reminders: {completed_reminders}")
st.write(f"Pending Reminders: {pending_reminders}")
