import streamlit as st
import json, os, datetime, calendar
import pandas as pd
import matplotlib.pyplot as plt
import random
import string

# -----------------------
# CONFIG PATHS
# -----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ATHLETES_DIR = os.path.join(DATA_DIR, "athletes")
SHARED_DIR = os.path.join(DATA_DIR, "shared")

DROPBOX_SYNC_FOLDER = r"C:\Users\User\Dropbox\GAA_Shared"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ATHLETES_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)
os.makedirs(DROPBOX_SYNC_FOLDER, exist_ok=True)

FAMILIES_FILE = os.path.join(DATA_DIR, "families.json")
TEAMS_FILE = os.path.join(DATA_DIR, "teams.json")

ATHLETE_COLORS = [
    "#2E7D32",  # green
    "#1565C0",  # blue
    "#F9A825",  # amber
    "#C62828",  # red
    "#6A1B9A",  # purple
    "#00897B",  # teal
    "#F57C00",  # orange
]

# -----------------------
# UTILITY FUNCTIONS
# -----------------------
def load_json(path, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def athlete_file(username: str) -> str:
    return os.path.join(ATHLETES_DIR, username + ".json")

def compute_weekly_summary(entries, minutes_key="minutes"):
    """Assumes entries contain 'date' (YYYY-MM-DD) and a minutes_key."""
    week = datetime.date.today().isocalendar()[1]
    year = datetime.date.today().year
    total_minutes = 0
    for e in entries:
        try:
            d = datetime.datetime.strptime(e["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        w = d.isocalendar()[1]
        if w == week and d.year == year:
            total_minutes += int(e.get(minutes_key, 0))
    return {"total_minutes": total_minutes}

def generate_overtraining_alerts(entries):
    alerts = []
    today = datetime.date.today()
    daily_minutes = 0
    for e in entries:
        try:
            d = datetime.datetime.strptime(e["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        if d == today:
            daily_minutes += int(e.get("minutes", 0))
    if daily_minutes > 120:
        alerts.append(("day", "red", f"High daily load! {daily_minutes} minutes today."))
    weekly_summary = compute_weekly_summary(entries)
    if weekly_summary["total_minutes"] > 300:
        alerts.append(
            ("week", "yellow", f"Weekly load high: {weekly_summary['total_minutes']} minutes.")
        )
    return alerts

def generate_share_code(length=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

# -------- Families helpers --------
def load_families():
    data = load_json(FAMILIES_FILE, {})
    # normalise children to list of dicts with username+color
    changed = False
    for code, fam in data.items():
        children = fam.get("children", [])
        new_children = []
        used_colors = set()
        for child in children:
            if isinstance(child, str):
                # old format: just username
                username = child
                color = None
            else:
                username = child.get("username")
                color = child.get("color")
            if not username:
                continue
            if not color:
                # assign first unused color
                for c in ATHLETE_COLORS:
                    if c not in used_colors:
                        color = c
                        break
                else:
                    color = random.choice(ATHLETE_COLORS)
                changed = True
            used_colors.add(color)
            new_children.append({"username": username, "color": color})
        fam["children"] = new_children
    if changed:
        save_json(FAMILIES_FILE, data)
    return data

def save_families(families):
    save_json(FAMILIES_FILE, families)

def assign_child_color(family, username):
    children = family.get("children", [])
    # if already exists, return its color
    for c in children:
        if c.get("username") == username:
            return c.get("color", ATHLETE_COLORS[0])
    used = {c.get("color") for c in children if c.get("color")}
    color = None
    for col in ATHLETE_COLORS:
        if col not in used:
            color = col
            break
    if not color:
        color = random.choice(ATHLETE_COLORS)
    children.append({"username": username, "color": color})
    family["children"] = children
    return color

def find_families_for_athlete(username):
    families = load_families()
    result = []
    for code, fam in families.items():
        for child in fam.get("children", []):
            if child.get("username") == username:
                result.append((code, fam.get("family_name", "Family")))
                break
    return result

def get_family_child_color(family, username):
    for child in family.get("children", []):
        if child.get("username") == username:
            return child.get("color", ATHLETE_COLORS[0])
    return ATHLETE_COLORS[0]

# -------- Teams helpers --------
def load_teams():
    return load_json(TEAMS_FILE, {})

def save_teams(teams):
    save_json(TEAMS_FILE, teams)

def generate_team_code(length=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def team_status_colour(total_minutes):
    """Return (emoji, label) for weekly minutes."""
    if total_minutes >= 300:
        return "🔴", "High"
    elif total_minutes >= 150:
        return "🟠", "Moderate"
    else:
        return "🟢", "Light"

# -----------------------
# LOGIN / AUTH FUNCTIONS
# -----------------------
def save_athlete(u, data):
    save_json(athlete_file(u), data)

def check_athlete_login(u, p):
    file = athlete_file(u)
    if not os.path.exists(file):
        return False, None
    data = load_json(file)
    return (data.get("pin") == p), data

def register_coach(user, pin):
    path = os.path.join(DATA_DIR, "coaches.json")
    data = load_json(path, {})
    if user in data:
        return False, "Coach already exists"
    data[user] = pin
    save_json(path, data)
    return True, "Coach registered"

def check_coach(user, pin):
    data = load_json(os.path.join(DATA_DIR, "coaches.json"), {})
    return data.get(user) == pin

# -----------------------
# STREAMLIT APP CONFIG
# -----------------------
st.set_page_config(
    page_title="Performance Pulse",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- GLOBAL STYLING / DESIGN ----------
st.markdown(
    """
<style>
/* App background */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #f0f5f0 0%, #ffffff 40%, #f0f5f0 100%);
}

/* Main block container padding */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #213c29;
}
[data-testid="stSidebar"] * {
    color: #f0f5f0 !important;
}

/* Headings */
h1, h2, h3, h4 {
    color: #213c29;
    font-family: "Segoe UI", system-ui, sans-serif;
}
h1 {
    font-weight: 700;
}
h2, h3 {
    border-left: 4px solid #438951;
    padding-left: 10px;
    margin-top: 1.2rem;
}

/* Base text */
body, p, label {
    font-family: "Segoe UI", system-ui, sans-serif;
}

/* Buttons */
.stButton>button {
    background-color: #438951;
    color: white;
    border-radius: 999px;
    border: none;
    padding: 0.4rem 1.2rem;
    font-weight: 600;
}
.stButton>button:hover {
    background-color: #376941;
}

/* Metrics */
div[data-testid="stMetricValue"] {
    color: #213c29;
    font-weight: 700;
}

/* Tables */
[data-testid="stTable"] {
    border-radius: 10px;
    overflow: hidden;
}

/* Select / dropdown background */
[data-baseweb="select"] > div {
    background-color: #e0f2e9 !important;
}

/* Info separation lines */
hr {
    border: none;
    border-top: 1px solid #ced9ce;
    margin: 1rem 0;
}
</style>
""",
    unsafe_allow_html=True,
)

st.sidebar.title("Navigation")
mode = st.sidebar.selectbox(
    "Choose Mode",
    ["Athlete Portal", "Coach Dashboard", "Parent / Guardian", "Admin / Settings"],
)

# -----------------------
# SESSION STATE INIT
# -----------------------
if "athlete_logged_in" not in st.session_state:
    st.session_state["athlete_logged_in"] = False
    st.session_state["athlete_user"] = ""
    st.session_state["athlete_data"] = None

if "family_dashboard_code" not in st.session_state:
    st.session_state["family_dashboard_code"] = ""

# -----------------------
# ATHLETE PORTAL
# -----------------------
if mode == "Athlete Portal":
    st.header("🏋️ Athlete Portal")
    sub_mode = st.radio("Select:", ["Register", "Login"])

    # --- Athlete Registration ---
    if sub_mode == "Register":
        st.subheader("New Athlete Registration")
        new_user = st.text_input("Username", key="reg_user")
        new_pin = st.text_input("PIN", type="password", key="reg_pin")
        confirm_pin = st.text_input("Confirm PIN", type="password", key="reg_confirm")
        if st.button("Register Athlete"):
            if not new_user or not new_pin:
                st.error("Enter username and PIN")
            elif new_pin != confirm_pin:
                st.error("PINs do not match")
            elif os.path.exists(athlete_file(new_user)):
                st.error("Username already exists")
            else:
                save_athlete(
                    new_user,
                    {
                        "pin": new_pin,
                        "username": new_user,
                        "training_log": [],
                        "gym_sessions": [],
                        "diet_log": [],
                        "chat": [],
                        "fixtures": [],
                        "homework_log": [],
                        "wellbeing_log": [],
                    },
                )
                st.success(f"Athlete {new_user} registered! You can now log in.")

    # --- Athlete Login ---
    elif sub_mode == "Login" and not st.session_state["athlete_logged_in"]:
        st.subheader("Athlete Login")
        u = st.text_input("Username", key="login_user")
        p = st.text_input("PIN", type="password", key="login_pin")
        if st.button("Log In"):
            ok, data = check_athlete_login(u, p)
            if not ok:
                st.error("Invalid login")
            else:
                st.session_state["athlete_logged_in"] = True
                st.session_state["athlete_user"] = u
                st.session_state["athlete_data"] = data
                st.success(f"Welcome {u}")

    # --- Athlete Main Area ---
    if st.session_state["athlete_logged_in"]:
        u = st.session_state["athlete_user"]
        data = st.session_state["athlete_data"]
        st.success(f"Welcome back {u}")

        athlete_tab = st.radio(
            "Select Feature",
            [
                "Training Log",
                "Gym/Cardio & Goals",
                "Diet / Macros",
                "Fixtures",
                "Homework / Study",
                "Mental Wellbeing",
                "Teams & Coach Codes",
                "Chat / CoachBot",
                "Recovery Advice",
                "Account / Family Info",
            ],
        )

        # -------------------
        # Training Log + Calendar + Share with Coach
        # -------------------
        if athlete_tab == "Training Log":
            st.subheader("📅 Log Training Session")
            logs = data.get("training_log", [])
            date = st.date_input("Date", datetime.date.today())
            minutes = st.number_input("Minutes trained", 0, 300)
            desc = st.text_input("Description")
            if st.button("Add Session"):
                logs.append({"date": str(date), "minutes": int(minutes), "desc": desc})
                data["training_log"] = logs
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Session saved!")

            st.markdown("---")
            st.subheader("📊 Weekly & Daily Load Alerts")
            alerts = generate_overtraining_alerts(logs)
            if alerts:
                for _, level, msg in alerts:
                    if level == "red":
                        st.error(msg)
                    else:
                        st.warning(msg)
            else:
                st.success("Training load is within safe limits.")

            if logs:
                df = pd.DataFrame(logs)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")
                st.write("### Training Calendar (List View)")
                st.dataframe(df[["date", "minutes", "desc"]])

                # Line graph
                fig, ax = plt.subplots(figsize=(8, 4))
                if len(df) > 1:
                    ax.plot(df["date"], df["minutes"], marker="o", linestyle="-")
                else:
                    ax.plot(df["date"], df["minutes"], "o")
                ax.set_title("Training Minutes Over Time")
                ax.set_ylabel("Minutes")
                ax.set_xlabel("Date")
                plt.xticks(rotation=45)
                plt.tight_layout()
                st.pyplot(fig)

                # Download + Share with Coach
                st.markdown("---")
                st.subheader("📥 Download / Share Training Data")

                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Training Log (CSV)",
                    data=csv_bytes,
                    file_name=f"{u}_training_log.csv",
                    mime="text/csv",
                )

                json_bytes = json.dumps(logs, indent=2).encode("utf-8")
                st.download_button(
                    label="📥 Download Training Log (JSON)",
                    data=json_bytes,
                    file_name=f"{u}_training_log.json",
                    mime="application/json",
                )

                st.info(
                    "You can download the CSV file and email or share it directly with your coach."
                )

                st.markdown("---")
                st.subheader("📤 Share Weekly Snapshot to Coach (with Code)")

                if st.button("Share Weekly Snapshot"):
                    weekly_summary = compute_weekly_summary(logs)

                    homework_log = data.get("homework_log", [])
                    homework_summary = (
                        compute_weekly_summary(homework_log)
                        if homework_log
                        else {"total_minutes": 0}
                    )

                    share_code = generate_share_code()

                    snapshot = {
                        "username": data.get("username", u),
                        "generated_at": str(datetime.datetime.now()),
                        "weekly_summary": weekly_summary,
                        "training_log": logs,
                        "homework_summary": homework_summary,
                        "homework_log": homework_log,
                        "share_code": share_code,
                    }

                    snap_file_json = f"{u}_snapshot_{share_code}.json"
                    snap_path_json = os.path.join(SHARED_DIR, snap_file_json)
                    save_json(snap_path_json, snapshot)

                    drop_target_json = os.path.join(
                        DROPBOX_SYNC_FOLDER, snap_file_json
                    )
                    save_json(drop_target_json, snapshot)

                    snap_file_csv = f"{u}_training_log_{share_code}.csv"
                    snap_path_csv = os.path.join(SHARED_DIR, snap_file_csv)
                    df.to_csv(snap_path_csv, index=False)

                    drop_target_csv = os.path.join(
                        DROPBOX_SYNC_FOLDER, snap_file_csv
                    )
                    df.to_csv(drop_target_csv, index=False)

                    st.success(
                        "Weekly snapshot (JSON + CSV) saved to the shared/Dropbox folder for coaches!"
                    )
                    st.info(
                        f"Share this code with your coach so they can view your training and homework/study data: **{share_code}**"
                    )
            else:
                st.info(
                    "No sessions logged yet. Add your first session above to enable download and sharing."
                )

        # -------------------
        # Gym / Cardio goals & RPE
        # -------------------
        elif athlete_tab == "Gym/Cardio & Goals":
            st.subheader("🏃 Gym / Cardio Sessions & Goals")
            gym_sessions = data.get("gym_sessions", [])

            g_date = st.date_input("Date", datetime.date.today(), key="gym_date")
            g_type = st.selectbox("Session type", ["Cardio", "Gym / Weights", "Other"])
            g_minutes = st.number_input("Minutes", 0, 300, key="gym_minutes")
            g_goal = st.text_input("Goal (e.g. '5k in 30 mins')", key="gym_goal")
            g_rpe = st.slider("How hard was this session? (1 = very easy, 10 = max effort)", 1, 10, 5)
            g_notes = st.text_area("Notes (what you did, how it felt)", key="gym_notes")

            if st.button("Add Gym/Cardio Session"):
                gym_sessions.append(
                    {
                        "date": str(g_date),
                        "type": g_type,
                        "minutes": int(g_minutes),
                        "goal": g_goal,
                        "rpe": int(g_rpe),
                        "notes": g_notes,
                    }
                )
                data["gym_sessions"] = gym_sessions
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Gym/Cardio session saved!")

            if gym_sessions:
                gdf = pd.DataFrame(gym_sessions)
                gdf["date"] = pd.to_datetime(gdf["date"])
                gdf = gdf.sort_values("date", ascending=False)
                st.write("### Recent Gym/Cardio Sessions")
                st.dataframe(gdf[["date", "type", "minutes", "goal", "rpe", "notes"]].head(20))

                # Simple RPE guidance
                st.markdown("### 🔍 Load & RPE Check")
                last_7 = gdf.head(7).sort_values("date")
                high_rpe_days = last_7[last_7["rpe"] >= 8]
                if len(high_rpe_days) >= 2:
                    # Check consecutive high RPE days
                    dates = list(high_rpe_days["date"].dt.date)
                    dates_sorted = sorted(dates)
                    consecutive = False
                    for i in range(1, len(dates_sorted)):
                        if (dates_sorted[i] - dates_sorted[i-1]).days == 1:
                            consecutive = True
                            break
                    if consecutive:
                        st.warning(
                            "You have **two or more very hard days in a row** (RPE 8+). Try not to stack 'red' days back-to-back."
                        )
                    else:
                        st.info(
                            "You have a few very hard sessions (RPE 8+), but they are spaced out — nice balance."
                        )
                else:
                    st.success(
                        "No repeated 'red' days detected in your recent sessions. Keep mixing hard, medium, and easy days."
                    )

        # -------------------
        # Diet / Macros
        # -------------------
        elif athlete_tab == "Diet / Macros":
            st.subheader("🍎 Log Diet / Macros")
            diet_log = data.get("diet_log", [])

            meal = st.text_input("Meal / Snack")
            calories = st.number_input("Calories", 0, 5000, key="calories")
            protein = st.number_input("Protein (g)", 0, 500, key="protein")
            carbs = st.number_input("Carbs (g)", 0, 500, key="carbs")
            fat = st.number_input("Fat (g)", 0, 500, key="fat")

            if st.button("Add Meal"):
                diet_log.append(
                    {
                        "date": str(datetime.date.today()),
                        "meal": meal,
                        "calories": int(calories),
                        "protein": int(protein),
                        "carbs": int(carbs),
                        "fat": int(fat),
                    }
                )
                data["diet_log"] = diet_log
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Meal saved!")

            if diet_log:
                df = pd.DataFrame(diet_log)
                df["date"] = pd.to_datetime(df["date"])
                st.write("### Diet Log")
                st.dataframe(df)

                today = datetime.date.today()
                today_df = df[df["date"].dt.date == today]

                # Use presence checks to avoid KeyError if older entries lack fields
                total_calories = today_df["calories"].sum() if "calories" in today_df else 0
                total_protein = today_df["protein"].sum() if "protein" in today_df else 0
                total_carbs = today_df["carbs"].sum() if "carbs" in today_df else 0
                total_fat = today_df["fat"].sum() if "fat" in today_df else 0

                st.write(f"**Today – Calories:** {int(total_calories)} kcal")
                st.write(
                    f"**Today – Protein:** {int(total_protein)} g | Carbs: {int(total_carbs)} g | Fat: {int(total_fat)} g"
                )

        # -------------------
        # Fixtures
        # -------------------
        elif athlete_tab == "Fixtures":
            st.subheader("📆 Upcoming Match Fixtures")
            fixtures = data.get("fixtures", [])

            col1, col2 = st.columns(2)
            with col1:
                f_date = st.date_input("Match date", datetime.date.today())
                f_time = st.time_input("Match time", datetime.time(19, 0))
                opponent = st.text_input("Opponent / Team")
            with col2:
                venue = st.text_input("Venue / Pitch")
                notes = st.text_area("Notes (e.g., competition, position, kit)")

            if st.button("Add Fixture"):
                fixtures.append(
                    {
                        "date": str(f_date),
                        "time": f_time.strftime("%H:%M"),
                        "opponent": opponent,
                        "venue": venue,
                        "notes": notes,
                    }
                )
                data["fixtures"] = fixtures
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Fixture added!")

            if fixtures:
                fdf = pd.DataFrame(fixtures)
                fdf["datetime"] = pd.to_datetime(fdf["date"] + " " + fdf["time"])
                fdf = fdf.sort_values("datetime")

                today = datetime.date.today()
                upcoming = fdf[fdf["datetime"].dt.date >= today]

                st.write("### All Fixtures")
                st.dataframe(fdf[["date", "time", "opponent", "venue", "notes"]])

                if not upcoming.empty:
                    st.write("### Upcoming Fixtures")
                    st.dataframe(upcoming[["date", "time", "opponent", "venue", "notes"]])
                else:
                    st.info("No upcoming fixtures.")

        # -------------------
        # Homework / Study
        # -------------------
        elif athlete_tab == "Homework / Study":
            st.subheader("📚 Homework & Study Log")
            homework_log = data.get("homework_log", [])

            h_date = st.date_input("Date", datetime.date.today(), key="hw_date")
            subject = st.text_input("Subject / Topic", key="hw_subject")
            h_minutes = st.number_input("Minutes studied", 0, 600, key="hw_minutes")
            h_notes = st.text_area("Notes (e.g., type of work done)", key="hw_notes")

            if st.button("Add Study Session"):
                homework_log.append(
                    {
                        "date": str(h_date),
                        "subject": subject,
                        "minutes": int(h_minutes),
                        "notes": h_notes,
                    }
                )
                data["homework_log"] = homework_log
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Study session saved!")

            if homework_log:
                hdf = pd.DataFrame(homework_log)
                hdf["date"] = pd.to_datetime(hdf["date"])
                hdf = hdf.sort_values("date")
                st.write("### Homework / Study History")
                st.dataframe(hdf[["date", "subject", "minutes", "notes"]])

                today = datetime.date.today()
                today_minutes = hdf[hdf["date"].dt.date == today]["minutes"].sum()
                week_summary = compute_weekly_summary(homework_log)

                st.write(f"**Total study minutes today:** {today_minutes}")
                st.write(f"**Total study minutes this week:** {week_summary['total_minutes']}")

                st.info(
                    "Your homework/study log is included automatically when you share a weekly snapshot with your coach in the Training Log tab."
                )
            else:
                st.info("No homework/study sessions logged yet.")

        # -------------------
        # Mental Wellbeing
        # -------------------
        elif athlete_tab == "Mental Wellbeing":
            st.subheader("🧠 Mental Wellbeing Check-In")
            wellbeing_log = data.get("wellbeing_log", [])

            w_date = st.date_input("Date", datetime.date.today(), key="wb_date")
            mood = st.slider("Overall mood today (1 = low, 10 = great)", 1, 10, 5)
            stress = st.slider("Stress level today (1 = calm, 10 = very stressed)", 1, 10, 5)
            sleep_hours = st.number_input("Hours of sleep last night", 0.0, 24.0, 8.0, 0.5)
            wb_notes = st.text_area("Anything on your mind? (what went well, worries, etc.)")

            if st.button("Save Check-In"):
                wellbeing_log.append(
                    {
                        "date": str(w_date),
                        "mood": mood,
                        "stress": stress,
                        "sleep_hours": float(sleep_hours),
                        "notes": wb_notes,
                    }
                )
                data["wellbeing_log"] = wellbeing_log
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Wellbeing check-in saved.")

            if wellbeing_log:
                wdf = pd.DataFrame(wellbeing_log)
                wdf["date"] = pd.to_datetime(wdf["date"])
                wdf = wdf.sort_values("date", ascending=False)

                st.write("### Recent Check-Ins")
                st.dataframe(wdf[["date", "mood", "stress", "sleep_hours", "notes"]].head(14))

                last_7 = wdf.head(7)
                avg_mood = last_7["mood"].mean()
                avg_stress = last_7["stress"].mean()
                avg_sleep = last_7["sleep_hours"].mean()

                st.write(f"**Average mood (last {len(last_7)} days):** {avg_mood:.1f}")
                st.write(f"**Average stress (last {len(last_7)} days):** {avg_stress:.1f}")
                st.write(f"**Average sleep (last {len(last_7)} days):** {avg_sleep:.1f} hours")

                if avg_stress > 7:
                    st.warning(
                        "Stress has been high recently. Consider taking breaks and talking to a coach, teacher, or someone you trust."
                    )
                if avg_sleep < 7:
                    st.info(
                        "Sleep has been on the low side. Aim for consistent, good-quality sleep to support performance and wellbeing."
                    )

        # -------------------
        # Teams & Coach Codes
        # -------------------
        elif athlete_tab == "Teams & Coach Codes":
            st.subheader("👥 Teams & Family / Coach Codes")

            st.markdown("#### Family codes you are linked to")
            fam_links = find_families_for_athlete(u)
            if fam_links:
                for code, name in fam_links:
                    st.write(f"- **{name}** – code: `{code}`")
            else:
                st.info("You are not currently linked to any family codes.")

            st.markdown("---")
            st.markdown("#### Join a Team (from your coach)")
            team_code_input = st.text_input("Enter team code from your coach")
            if st.button("Join Team"):
                tcode = team_code_input.strip().upper()
                if not tcode:
                    st.error("Please enter a team code.")
                else:
                    teams = load_teams()
                    if tcode not in teams:
                        st.error("Team code not found.")
                    else:
                        team = teams[tcode]
                        athletes = team.get("athletes", [])
                        if u in athletes:
                            st.info(f"You are already in team **{team.get('team_name', tcode)}**.")
                        else:
                            athletes.append(u)
                            team["athletes"] = athletes
                            teams[tcode] = team
                            save_teams(teams)
                            st.success(f"You have joined team **{team.get('team_name', tcode)}**")

            st.markdown("#### Teams you are in")
            teams = load_teams()
            joined = []
            for code_, team in teams.items():
                if u in team.get("athletes", []):
                    joined.append((code_, team.get("team_name", "Team")))
            if joined:
                for code_, name in joined:
                    st.write(f"- **{name}** – team code: `{code_}`")
            else:
                st.info("You have not joined any teams yet.")

            st.markdown("---")
            st.info(
                "To share detailed weekly data with a coach, go to **Training Log → Share Weekly Snapshot**, "
                "then give your coach the generated share code."
            )

        # -------------------
        # Chat / CoachBot
        # -------------------
        elif athlete_tab == "Chat / CoachBot":
            st.subheader("💬 Chat / Motivation Bot")

            chat_log = data.get("chat", [])

            if chat_log:
                st.write("### Recent Messages")
                for entry in chat_log[-20:]:
                    role = entry.get("role", "athlete")
                    text = entry.get("text", entry.get("msg", ""))
                    ts = entry.get("time", entry.get("date", ""))
                    prefix = "🧍‍♂️ You" if role == "athlete" else "🤖 CoachBot"
                    st.markdown(f"**{prefix}** ({ts}): {text}")

            message = st.text_area("Type a message to CoachBot")
            if st.button("Send to CoachBot"):
                if message.strip():
                    now = str(datetime.datetime.now())
                    chat_log.append(
                        {"role": "athlete", "text": message.strip(), "time": now}
                    )

                    # very simple motivational logic
                    lower = message.lower()
                    if any(word in lower for word in ["tired", "wrecked", "exhausted", "sore"]):
                        reply = (
                            "Totally normal to feel tired after big sessions. "
                            "Listen to your body – mixing in an easier day, stretching, or an early night "
                            "can actually make you stronger for the next hard block. 💪"
                        )
                    elif any(word in lower for word in ["exam", "study", "school", "homework"]):
                        reply = (
                            "Balancing exams and sport is a challenge, but you’re building brilliant habits. "
                            "Try planning your week so heavy study days get lighter training, and vice versa. "
                            "Small, consistent blocks beat last-minute panic every time. 📚⚽"
                        )
                    elif any(word in lower for word in ["nervous", "anxious", "worried"]):
                        reply = (
                            "Nerves usually mean you care – that’s a strength. "
                            "Control the controllables: sleep, food, warm-up, and your first few minutes in a game or session. "
                            "One action at a time. You’ve got this. 💚"
                        )
                    else:
                        reply = (
                            "You’re putting in the work, and that matters. "
                            "Keep an eye on balance: training, school, friends, and downtime all play a part. "
                            "Proud of the effort you’re making – keep going, but don’t forget to breathe. 🌟"
                        )

                    chat_log.append(
                        {"role": "bot", "text": reply, "time": now}
                    )

                    data["chat"] = chat_log
                    save_athlete(u, data)
                    st.session_state["athlete_data"] = data
                    st.success("Message sent — scroll up to see CoachBot's reply.")

        # -------------------
        # Recovery Advice
        # -------------------
        elif athlete_tab == "Recovery Advice":
            st.subheader("🛌 Recovery Advice")
            training_log = data.get("training_log", [])
            gym_log = data.get("gym_sessions", [])

            week_train = compute_weekly_summary(training_log)["total_minutes"]
            week_gym = compute_weekly_summary(gym_log)["total_minutes"]
            total = week_train + week_gym

            col1, col2, col3 = st.columns(3)
            col1.metric("Field training (min/week)", week_train)
            col2.metric("Gym/Cardio (min/week)", week_gym)
            col3.metric("Total load (min/week)", total)

            if total > 450:
                st.error(
                    "Overall load is very high this week. Prioritise sleep, nutrition, and consider adding a full rest day."
                )
            elif total > 300:
                st.warning(
                    "Solid training week. Make sure at least one day is genuinely easy or full rest."
                )
            else:
                st.success("Load looks manageable. Keep building steadily and listening to your body.")

        # -------------------
        # Account / Family Info (+ Logout)
        # -------------------
        elif athlete_tab == "Account / Family Info":
            st.subheader("👤 Account & Family Info")

            st.write(f"**Username:** {u}")

            fam_links = find_families_for_athlete(u)
            if fam_links:
                st.markdown("### Linked Families")
                for code, name in fam_links:
                    st.write(f"- **{name}** – family code: `{code}`")
            else:
                st.info("You are not currently linked to any family codes.")

            teams = load_teams()
            joined = []
            for code_, team in teams.items():
                if u in team.get("athletes", []):
                    joined.append((code_, team.get("team_name", "Team")))
            if joined:
                st.markdown("### Teams")
                for code_, name in joined:
                    st.write(f"- **{name}** – team code: `{code_}`")

            st.markdown("---")
            if st.button("Log Out"):
                st.session_state["athlete_logged_in"] = False
                st.session_state["athlete_user"] = ""
                st.session_state["athlete_data"] = None
                st.success("You have been logged out. You can close this tab or log in as another athlete.")

# -----------------------
# COACH DASHBOARD
# -----------------------
elif mode == "Coach Dashboard":
    st.header("🎓 Coach Dashboard")

    coach_tab = st.radio(
        "Choose view",
        ["Individual Athlete (share code)", "Team Overview"],
    )

    # ---- Individual Athlete via share code ----
    if coach_tab == "Individual Athlete (share code)":
        st.write("Ask the athlete for their **share code**, then enter it below to view their data.")

        share_code_input = st.text_input("Enter athlete share code")

        if st.button("Load Athlete Data"):
            if not share_code_input:
                st.error("Please enter a share code.")
            else:
                files = [f for f in os.listdir(SHARED_DIR) if f.endswith(".json")]
                matched_snapshot = None

                for fname in files:
                    path = os.path.join(SHARED_DIR, fname)
                    snap = load_json(path, {})
                    if snap.get("share_code") == share_code_input.strip():
                        matched_snapshot = snap
                        break

                if matched_snapshot is None:
                    st.error("No athlete data found for that share code.")
                else:
                    logs = matched_snapshot.get("training_log", [])
                    hw_logs = matched_snapshot.get("homework_log", [])

                    athlete_name = matched_snapshot.get("username", "Unknown")
                    weekly_train = matched_snapshot.get(
                        "weekly_summary",
                        compute_weekly_summary(logs)
                    )
                    if hw_logs:
                        weekly_hw = matched_snapshot.get(
                            "homework_summary",
                            compute_weekly_summary(hw_logs)
                        )
                    else:
                        weekly_hw = {"total_minutes": 0}

                    combined_total = weekly_train["total_minutes"] + weekly_hw["total_minutes"]

                    st.success("Athlete data loaded successfully.")
                    st.write(f"**Athlete:** {athlete_name}")
                    st.write(f"**Share code:** {matched_snapshot.get('share_code')}")
                    st.write(f"**Generated at:** {matched_snapshot.get('generated_at')}")

                    st.markdown("### 📋 Weekly Load Summary")

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Training (min/week)", weekly_train["total_minutes"])
                    col2.metric("Study (min/week)", weekly_hw["total_minutes"])
                    col3.metric("Combined load (min/week)", combined_total)

                    if weekly_train["total_minutes"] > 300:
                        st.warning("Training load alone is high this week — consider monitoring recovery.")
                    if weekly_hw["total_minutes"] > 300:
                        st.info("Academic load is also high — check in on sleep and stress levels.")
                    if combined_total > 600:
                        st.error("Overall load (training + study) is very high — worth a conversation about balance.")

                    st.markdown("---")
                    st.write("### 🏋️ Training Detail")
                    st.write(f"**Weekly training minutes:** {weekly_train['total_minutes']}")

                    alerts = generate_overtraining_alerts(logs)
                    for _, level, msg in alerts:
                        if level == "red":
                            st.error(msg)
                        else:
                            st.warning(msg)

                    if logs:
                        df = pd.DataFrame(logs)
                        df["date"] = pd.to_datetime(df["date"])
                        df = df.sort_values("date")

                        st.write("#### Training Calendar")
                        st.dataframe(df)

                        csv_bytes = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📥 Download Athlete Training Log (CSV)",
                            data=csv_bytes,
                            file_name=f"{athlete_name}_training_log.csv",
                            mime="text/csv",
                        )

                    if hw_logs:
                        st.markdown("---")
                        st.write("### 📚 Homework / Study Detail")

                        hw_df = pd.DataFrame(hw_logs)
                        hw_df["date"] = pd.to_datetime(hw_df["date"])
                        hw_df = hw_df.sort_values("date")

                        st.dataframe(hw_df)

                        st.write(f"**Weekly study minutes:** {weekly_hw['total_minutes']}")

    # ---- Team Overview ----
    elif coach_tab == "Team Overview":
        st.subheader("Create a Team Code")
        team_name = st.text_input("Team name (e.g. 'U16A Football')")
        coach_name = st.text_input("Coach name (optional)")
        if st.button("Create Team Code"):
            if not team_name:
                st.error("Please enter a team name.")
            else:
                teams = load_teams()
                code = generate_team_code()
                while code in teams:
                    code = generate_team_code()
                teams[code] = {
                    "team_name": team_name,
                    "coach_name": coach_name,
                    "athletes": [],
                }
                save_teams(teams)
                st.success(f"Team created! Give this code to your players: **{code}**")

        st.markdown("---")
        st.subheader("View Team Weekly Training")

        team_code_input = st.text_input("Enter team code to view")
        if st.button("Load Team Overview"):
            tcode = team_code_input.strip().upper()
            if not tcode:
                st.error("Please enter a team code.")
            else:
                teams = load_teams()
                if tcode not in teams:
                    st.error("Team code not found.")
                else:
                    team = teams[tcode]
                    st.write(f"**Team:** {team.get('team_name', tcode)}")
                    athletes = team.get("athletes", [])
                    if not athletes:
                        st.info("No athletes have joined this team yet.")
                    else:
                        rows = []
                        for athlete in athletes:
                            afile = athlete_file(athlete)
                            if not os.path.exists(afile):
                                continue
                            adata = load_json(afile, {})
                            tlog = adata.get("training_log", [])
                            glog = adata.get("gym_sessions", [])
                            week_train = compute_weekly_summary(tlog)["total_minutes"]
                            week_gym = compute_weekly_summary(glog)["total_minutes"]
                            total = week_train + week_gym
                            emoji, label = team_status_colour(total)
                            rows.append(
                                {
                                    "Athlete": athlete,
                                    "Weekly minutes": total,
                                    "Status": f"{emoji} {label}",
                                }
                            )
                        if rows:
                            df = pd.DataFrame(rows).sort_values("Weekly minutes", ascending=False)
                            st.write("### Team Weekly Load")
                            st.dataframe(df)
                        else:
                            st.info("No training data found yet for this team.")

# -----------------------
# PARENT / GUARDIAN DASHBOARD
# -----------------------
elif mode == "Parent / Guardian":
    st.header("👨‍👩‍👦 Parent / Guardian Dashboard")

    parent_tab = st.radio(
        "Select:",
        ["Create / Manage Family", "Family Weekly & Monthly Calendar"],
    )

    families = load_families()

    # ---- Create / Manage Family ----
    if parent_tab == "Create / Manage Family":
        st.subheader("Create a Family Code")
        family_name = st.text_input("Family name (e.g. 'Murphy Family')")

        if st.button("Create Family Code"):
            if not family_name:
                st.error("Please enter a family name.")
            else:
                code = generate_share_code()
                families = load_families()
                while code in families:
                    code = generate_share_code()
                families[code] = {
                    "family_name": family_name,
                    "children": [],
                }
                save_families(families)
                st.success(f"Family created! Your family code is: **{code}**")
                st.info("Share this code with your children so you can link their athlete accounts.")

        st.markdown("---")
        st.subheader("Link an Athlete to Your Family")

        family_code_input = st.text_input("Enter your family code")
        child_username = st.text_input("Athlete username")
        child_pin = st.text_input("Athlete PIN (for verification)", type="password")

        if st.button("Link Athlete"):
            families = load_families()
            code = family_code_input.strip()
            if code not in families:
                st.error("Family code not found.")
            else:
                ok, child_data = check_athlete_login(child_username, child_pin)
                if not ok:
                    st.error("Could not verify athlete username/PIN.")
                else:
                    fam = families[code]
                    # assign color and add if needed
                    existing = [c.get("username") for c in fam.get("children", [])]
                    if child_username in existing:
                        st.info("This athlete is already linked to your family.")
                    else:
                        assign_child_color(fam, child_username)
                        families[code] = fam
                        save_families(families)
                        st.success(
                            f"Athlete **{child_username}** linked to family **{fam.get('family_name', 'Family')}**."
                        )

    # ---- Family Weekly & Monthly Calendar ----
    elif parent_tab == "Family Weekly & Monthly Calendar":
        st.subheader("Family View")

        family_code_input = st.text_input(
            "Enter your family code to view your dashboard",
            value=st.session_state.get("family_dashboard_code", ""),
        )
        if family_code_input.strip():
            code = family_code_input.strip()
            families = load_families()
            if code not in families:
                st.error("Family code not found. Please check and try again.")
            else:
                st.session_state["family_dashboard_code"] = code
                family = families[code]
                st.success(f"Loaded family: **{family.get('family_name', 'Family')}**")

                children = family.get("children", [])
                if not children:
                    st.info("No athletes linked to this family yet.")
                else:
                    # --- Build weekly calendar ---
                    today = datetime.date.today()
                    current_week = today.isocalendar()[1]
                    current_year = today.year

                    family_calendar_rows = []
                    per_child_weekly = {}

                    training_by_day = {}

                    for child in children:
                        username = child.get("username")
                        color = child.get("color", ATHLETE_COLORS[0])
                        afile = athlete_file(username)
                        if not os.path.exists(afile):
                            continue
                        adata = load_json(afile, {})
                        logs = adata.get("training_log", [])
                        gym = adata.get("gym_sessions", [])
                        combined = logs + gym

                        per_child_weekly[username] = compute_weekly_summary(combined)["total_minutes"]

                        for e in combined:
                            try:
                                d = datetime.datetime.strptime(e["date"], "%Y-%m-%d").date()
                            except Exception:
                                continue
                            if d.year == current_year and d.isocalendar()[1] == current_week:
                                family_calendar_rows.append(
                                    {
                                        "Date": d,
                                        "Athlete": username,
                                        "Minutes": int(e.get("minutes", 0)),
                                        "Description": e.get("desc", e.get("goal", "")),
                                    }
                                )
                            # for monthly view mapping
                            if d.month == today.month and d.year == today.year:
                                key = d
                                if key not in training_by_day:
                                    training_by_day[key] = []
                                training_by_day[key].append((username, color))

                    if family_calendar_rows:
                        cal_df = pd.DataFrame(family_calendar_rows)
                        cal_df = cal_df.sort_values("Date")

                        st.write("### 📅 This Week's Family Training Calendar (List View)")
                        st.dataframe(cal_df)
                    else:
                        st.info("No training sessions logged for this week yet.")

                    # --- Per child weekly overview ---
                    st.markdown("---")
                    st.write("### 🧒 Per-Athlete Weekly Summary")

                    cols = st.columns(min(len(children), 4) or 1)
                    for idx, child in enumerate(children):
                        username = child.get("username")
                        minutes = per_child_weekly.get(username, 0)
                        color = child.get("color", ATHLETE_COLORS[0])
                        with cols[idx % len(cols)]:
                            st.metric(label=f"{username} – min this week", value=minutes)
                            st.markdown(
                                f"<span style='color:{color}; font-size: 20px;'>●</span> Colour tag",
                                unsafe_allow_html=True,
                            )

                    # --- Log training for a selected child ---
                    st.markdown("---")
                    st.write("### ✏️ Log Training for a Family Member")

                    usernames = [c.get("username") for c in children]
                    selected_child = st.selectbox(
                        "Choose athlete to log a session for",
                        options=usernames,
                    )

                    log_date = st.date_input("Date", today, key="parent_log_date")
                    log_minutes = st.number_input("Minutes trained", 0, 300, key="parent_log_minutes")
                    log_desc = st.text_input("Description (e.g. 'gym', 'pitch session')", key="parent_log_desc")

                    if st.button("Save Training Session for Athlete"):
                        afile = athlete_file(selected_child)
                        if not os.path.exists(afile):
                            st.error("Could not find athlete data for that user.")
                        else:
                            adata = load_json(afile, {})
                            logs = adata.get("training_log", [])
                            logs.append(
                                {
                                    "date": str(log_date),
                                    "minutes": int(log_minutes),
                                    "desc": log_desc,
                                }
                            )
                            adata["training_log"] = logs
                            save_athlete(selected_child, adata)
                            st.success(
                                f"Training session saved for **{selected_child}** on {log_date}."
                            )

                    # --- Monthly calendar with coloured dots ---
                    st.markdown("---")
                    st.write("### 📆 Month View (Current Month)")

                    year = today.year
                    month = today.month
                    cal = calendar.monthcalendar(year, month)

                    # Build HTML table
                    html = "<table style='border-collapse: collapse; width: 100%;'>"
                    # Header
                    html += "<tr>"
                    for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                        html += "<th style='border: 1px solid #ced9ce; padding: 4px; text-align: center;'>" + day_name + "</th>"
                    html += "</tr>"

                    for week in cal:
                        html += "<tr>"
                        for day in week:
                            if day == 0:
                                html += "<td style='border: 1px solid #ced9ce; padding: 6px; height: 60px;'></td>"
                            else:
                                date_obj = datetime.date(year, month, day)
                                dots_html = ""
                                for username, color in training_by_day.get(date_obj, []):
                                    dots_html += f"<span style='color:{color};'>●</span> "
                                html += (
                                    "<td style='border: 1px solid #ced9ce; padding: 6px; vertical-align: top; height: 60px;'>"
                                    f"<div style='font-weight:bold;'>{day}</div>"
                                    f"<div>{dots_html}</div>"
                                    "</td>"
                                )
                        html += "</tr>"
                    html += "</table>"

                    st.markdown(html, unsafe_allow_html=True)

        else:
            st.info("Enter a valid family code above to view the calendar.")

# -----------------------
# ADMIN / SETTINGS
# -----------------------
elif mode == "Admin / Settings":
    st.header("⚙️ Admin Settings")

    st.subheader("(Optional) Legacy Coach Registration")
    st.write(
        "The coach username/PIN system is no longer required if using share codes and team codes, "
        "but you can still register if you want."
    )
    cu = st.text_input("Coach username")
    cp = st.text_input("Coach PIN", type="password")
    if st.button("Register Coach"):
        ok, msg = register_coach(cu, cp)
        st.success(msg) if ok else st.error(msg)

    st.markdown("---")
    st.subheader("Dropbox sync folder")
    st.write(f"Currently: {DROPBOX_SYNC_FOLDER}")
