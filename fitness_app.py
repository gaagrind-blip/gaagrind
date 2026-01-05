import streamlit as st
import pandas as pd
import os
import json
import uuid
from datetime import datetime

# ------------------------------------
# Setup
# ------------------------------------
st.set_page_config(page_title="Fitness Training App", layout="wide")
st.title("Fitness Training & Recovery App")

# Ensure local data folder exists
os.makedirs("shared_data", exist_ok=True)


# ------------------------------------
# Session State Setup
# ------------------------------------
if "training_log" not in st.session_state:
    st.session_state.training_log = []

if "calorie_log" not in st.session_state:
    st.session_state.calorie_log = []

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


# ------------------------------------
# Sidebar Navigation
# ------------------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to:",
    [
        "Athlete Mode",
        "Coach Mode",
        "Dietary Tracker",
        "Chat Room / Help Line",
        "Recovery Advice"
    ],
)

# ------------------------------------
# ATHLETE MODE (Training Calendar + Sharing)
# ------------------------------------
if page == "Athlete Mode":
    st.header("Athlete Mode — Training Calendar & Sharing")

    # Input fields
    date = st.date_input("Training Date")
    training_type = st.text_input("Training Type (Hurling, Football, Gym, etc.)")
    duration = st.number_input("Duration (minutes)", min_value=0)

    if st.button("Add Training Session"):
        st.session_state.training_log.append(
            {"Date": str(date), "Training Type": training_type, "Duration": duration}
        )
        st.success("Training session added!")

    st.subheader("Your Training Sessions")
    if st.session_state.training_log:
        df = pd.DataFrame(st.session_state.training_log)
        st.table(df)
    else:
        st.info("No training sessions logged yet.")

    st.markdown("---")

    # -----------------------------------
    # SHARE DATA WITH COACH
    # -----------------------------------
    st.subheader("Share Your Training With a Coach")

    if st.button("Generate Share Code"):
        share_code = str(uuid.uuid4())[:8]  # short code
        save_path = f"shared_data/{share_code}.json"

        data_to_save = {
            "training_log": st.session_state.training_log,
            "calorie_log": st.session_state.calorie_log,
            "timestamp": datetime.now().isoformat(),
        }

        with open(save_path, "w") as f:
            json.dump(data_to_save, f, indent=4)

        st.success(f"Share Code Generated: **{share_code}**")
        st.info("Give this code to your coach so they can view your logs.")


# ------------------------------------
# COACH MODE (View Athlete Data)
# ------------------------------------
elif page == "Coach Mode":
    st.header("Coach Mode — View Athlete Training Data")

    share_code = st.text_input("Enter Athlete Share Code")

    if st.button("Load Athlete Data"):
        file_path = f"shared_data/{share_code}.json"

        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)

            st.success("Athlete data loaded successfully!")

            st.subheader("Training Log")
            st.table(pd.DataFrame(data["training_log"]))

            st.subheader("Calorie Log")
            st.table(pd.DataFrame(data["calorie_log"]))

            st.caption(f"Last updated: {data['timestamp']}")

        else:
            st.error("Invalid code. No athlete data found.")


# ------------------------------------
# DIETARY TRACKER
# ------------------------------------
elif page == "Dietary Tracker":
    st.header("Dietary & Calorie Tracker")

    food = st.text_input("Food Item")
    calories = st.number_input("Calories", min_value=0)

    if st.button("Add Food Entry"):
        st.session_state.calorie_log.append({"Food": food, "Calories": calories})
        st.success("Food entry added!")

    if st.session_state.calorie_log:
        df = pd.DataFrame(st.session_state.calorie_log)
        st.table(df)
        st.write(f"**Total Calories:** {df['Calories'].sum()} kcal")


# ------------------------------------
# CHAT ROOM
# ------------------------------------
elif page == "Chat Room / Help Line":
    st.header("Chat Room / Help Line")

    message = st.text_input("Enter your message:")

    if st.button("Send"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.chat_messages.append(f"[{timestamp}] You: {message}")

    st.subheader("Chat Messages")
    for msg in st.session_state.chat_messages:
        st.write(msg)


# ------------------------------------
# RECOVERY ADVICE
# ------------------------------------
elif page == "Recovery Advice":
    st.header("Recovery Advice After Training")

    st.write("""
### General Recovery Tips
- Cool down 5–10 minutes  
- Stretch after training  
- Hydrate properly  
- Eat protein + carbs within 2 hours  
- Aim for 7–9 hours sleep  
- Foam rolling helps reduce soreness  

### Hydration  
Aim for 2–3L of water daily.

### Nutrition  
Post-workout ideas:
- Protein shake  
- Chicken + rice  
- Oatmeal + nuts  
- Yogurt + fruit  

### Overtraining Signs  
- Persistent fatigue  
- Low motivation  
- Poor sleep  
- Lasting soreness  

If symptoms appear, increase rest days.
""")

