import streamlit as st
import json
import os
import datetime
import calendar
import pandas as pd
import matplotlib.pyplot as plt
import random
import string

# ============================================================
# Performance Pulse (GAA Grind) — Full App
# Includes:
# - Athlete login/register/logout + dashboards
# - Training log + weekly load + share snapshot code (coach view)
# - Gym/Cardio sessions + goals + RPE guidance
# - Diet/macros (legacy-safe)
# - Wellbeing + homework/study
# - Parent/guardian family dashboard + weekly + month calendar (colour coded)
# - Coach dashboard (PIN login) + Team Overview (join codes)
# - NEW: Coach Staffroom (coach-to-coach)
# - NEW: Training Plans upload + assign to athlete/team + athlete download
# ============================================================

# -----------------------
# CONFIG PATHS
# -----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ATHLETES_DIR = os.path.join(DATA_DIR, "athletes")
SHARED_DIR = os.path.join(DATA_DIR, "shared")

DROPBOX_SYNC_FOLDER = r"C:\Users\User\Dropbox\GAA_Shared"

FAMILIES_FILE = os.path.join(DATA_DIR, "families.json")
TEAMS_FILE = os.path.join(DATA_DIR, "teams.json")
COACHES_FILE = os.path.join(DATA_DIR, "coaches.json")

COACH_FORUM_FILE = os.path.join(DATA_DIR, "coach_forum.json")
TRAINING_PLANS_DIR = os.path.join(DATA_DIR, "training_plans")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ATHLETES_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)
os.makedirs(TRAINING_PLANS_DIR, exist_ok=True)

# Dropbox is optional; ensure folder exists if path is valid
try:
    os.makedirs(DROPBOX_SYNC_FOLDER, exist_ok=True)
except Exception:
    # If the folder can't be created on another machine, the app still works locally.
    pass

# -----------------------
# STREAMLIT PAGE CONFIG
# -----------------------
st.set_page_config(
    page_title="Performance Pulse",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------
# STYLING (STEM Team green vibe)
# -----------------------
st.markdown(
    """
<style>
/* App background */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #f0f5f0 0%, #ffffff 40%, #f0f5f0 100%);
}
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* Sidebar */
[data-testid="stSidebar"] { background-color: #213c29; }
[data-testid="stSidebar"] * { color: #f0f5f0 !important; }

/* Headings */
h1,h2,h3,h4 { color:#213c29; font-family: "Segoe UI", system-ui, sans-serif; }
h2,h3 { border-left:4px solid #438951; padding-left:10px; margin-top:1.2rem; }
body,p,label { font-family: "Segoe UI", system-ui, sans-serif; }

/* Buttons */
.stButton>button {
    background-color:#438951; color:white;
    border-radius:999px; border:none; padding:0.4rem 1.2rem; font-weight:600;
}
.stButton>button:hover { background-color:#376941; }

/* Dropdown background */
[data-baseweb="select"] > div { background-color:#e0f2e9 !important; }

/* Lines */
hr { border:none; border-top:1px solid #ced9ce; margin:1rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# HELPERS
# ============================================================
def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def athlete_file(username: str) -> str:
    return os.path.join(ATHLETES_DIR, f"{username}.json")

def safe_filename(name: str) -> str:
    keep = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- "
    cleaned = "".join(c for c in name if c in keep).strip().replace(" ", "_")
    return cleaned[:80] if cleaned else "plan"

def compute_weekly_total(entries, minutes_key="minutes") -> int:
    """Sum minutes_key for entries in the current ISO week."""
    week = datetime.date.today().isocalendar()[1]
    year = datetime.date.today().year
    total = 0
    for e in entries:
        try:
            d = datetime.datetime.strptime(e.get("date", ""), "%Y-%m-%d").date()
        except Exception:
            continue
        if d.year == year and d.isocalendar()[1] == week:
            total += int(e.get(minutes_key, 0))
    return total

def generate_overtraining_alerts(training_entries):
    alerts = []
    today = datetime.date.today()
    daily = 0
    for e in training_entries:
        try:
            d = datetime.datetime.strptime(e.get("date", ""), "%Y-%m-%d").date()
        except Exception:
            continue
        if d == today:
            daily += int(e.get("minutes", 0))
    if daily > 120:
        alerts.append(("red", f"High daily load: {daily} minutes today."))

    weekly = compute_weekly_total(training_entries, minutes_key="minutes")
    if weekly > 300:
        alerts.append(("yellow", f"Weekly load is high: {weekly} minutes this week."))

    return alerts

def code6() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def code8() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

# -----------------------
# COACH AUTH
# -----------------------
def register_coach(username: str, pin: str):
    coaches = load_json(COACHES_FILE, {})
    if username in coaches:
        return False, "Coach already exists."
    coaches[username] = pin
    save_json(COACHES_FILE, coaches)
    return True, "Coach registered."

def check_coach(username: str, pin: str) -> bool:
    coaches = load_json(COACHES_FILE, {})
    return coaches.get(username) == pin

# -----------------------
# ATHLETE AUTH
# -----------------------
def save_athlete(username: str, data: dict):
    save_json(athlete_file(username), data)

def check_athlete_login(username: str, pin: str):
    fp = athlete_file(username)
    if not os.path.exists(fp):
        return False, None
    data = load_json(fp, {})
    return data.get("pin") == pin, data

# -----------------------
# FAMILY / TEAM DATA
# -----------------------
def load_families():
    return load_json(FAMILIES_FILE, {})

def save_families(families):
    save_json(FAMILIES_FILE, families)

def load_teams():
    return load_json(TEAMS_FILE, {})

def save_teams(teams):
    save_json(TEAMS_FILE, teams)

# -----------------------
# COACH STAFFROOM
# -----------------------
def load_forum():
    return load_json(COACH_FORUM_FILE, {"messages": []})

def save_forum(forum):
    save_json(COACH_FORUM_FILE, forum)

# -----------------------
# TRAINING PLANS
# -----------------------
def plans_folder_for_team(team_code: str) -> str:
    return os.path.join(TRAINING_PLANS_DIR, f"team_{team_code}")

def plans_folder_for_athlete(username: str) -> str:
    return os.path.join(TRAINING_PLANS_DIR, f"athlete_{username}")

def load_plans_index(folder: str):
    return load_json(os.path.join(folder, "index.json"), {"plans": []})

def save_plans_index(folder: str, idx: dict):
    save_json(os.path.join(folder, "index.json"), idx)

# ============================================================
# SESSION STATE
# ============================================================
if "athlete_logged_in" not in st.session_state:
    st.session_state["athlete_logged_in"] = False
    st.session_state["athlete_user"] = ""
    st.session_state["athlete_data"] = None

if "coach_logged_in" not in st.session_state:
    st.session_state["coach_logged_in"] = False
    st.session_state["coach_user"] = ""

# ============================================================
# NAV
# ============================================================
st.sidebar.title("Navigation")
mode = st.sidebar.selectbox(
    "Choose Mode",
    ["Athlete Portal", "Coach Dashboard", "Parent / Guardian", "Admin / Settings"],
)

# ============================================================
# ATHLETE PORTAL
# ============================================================
if mode == "Athlete Portal":
    st.header("🏋️ Athlete Portal")

    # Logout (top-right-ish)
    if st.session_state["athlete_logged_in"]:
        if st.button("Log Out", key="athlete_logout_top"):
            st.session_state["athlete_logged_in"] = False
            st.session_state["athlete_user"] = ""
            st.session_state["athlete_data"] = None
            st.success("Logged out. You can now log in as another athlete.")

    sub_mode = st.radio("Select:", ["Login", "Register"], horizontal=True)

    # Register
    if sub_mode == "Register" and not st.session_state["athlete_logged_in"]:
        st.subheader("New Athlete Registration")
        new_user = st.text_input("Username", key="reg_user")
        new_pin = st.text_input("PIN", type="password", key="reg_pin")
        confirm_pin = st.text_input("Confirm PIN", type="password", key="reg_confirm")

        if st.button("Register Athlete"):
            if not new_user.strip() or not new_pin:
                st.error("Please enter a username and PIN.")
            elif new_pin != confirm_pin:
                st.error("PINs do not match.")
            elif os.path.exists(athlete_file(new_user.strip())):
                st.error("Username already exists.")
            else:
                u = new_user.strip()
                save_athlete(
                    u,
                    {
                        "pin": new_pin,
                        "username": u,
                        "training_log": [],
                        "gym_sessions": [],
                        "diet_log": [],
                        "chat": [],
                        "fixtures": [],
                        "homework_log": [],
                        "wellbeing_log": [],
                    },
                )
                st.success("Registered! Switch to Login to access your dashboard.")

    # Login
    if sub_mode == "Login" and not st.session_state["athlete_logged_in"]:
        st.subheader("Athlete Login")
        u = st.text_input("Username", key="login_user")
        p = st.text_input("PIN", type="password", key="login_pin")
        if st.button("Log In"):
            ok, data = check_athlete_login(u.strip(), p)
            if not ok:
                st.error("Invalid username or PIN.")
            else:
                st.session_state["athlete_logged_in"] = True
                st.session_state["athlete_user"] = u.strip()
                st.session_state["athlete_data"] = data
                st.success(f"Welcome {u.strip()}!")

    # Athlete dashboard
    if st.session_state["athlete_logged_in"]:
        u = st.session_state["athlete_user"]
        data = st.session_state["athlete_data"] or {}
        st.success(f"Logged in as: {u}")

        athlete_tab = st.radio(
            "Select Feature",
            [
                "Training Log",
                "Gym/Cardio & Goals",
                "Diet / Macros",
                "Training Plans",
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
        # Training Log
        # -------------------
        if athlete_tab == "Training Log":
            st.subheader("📅 Log Training Session")
            logs = data.get("training_log", [])

            date = st.date_input("Date", datetime.date.today(), key="train_date")
            minutes = st.number_input("Minutes trained", 0, 300, key="train_minutes")
            desc = st.text_input("Description", key="train_desc")

            if st.button("Add Session"):
                logs.append({"date": str(date), "minutes": int(minutes), "desc": desc})
                data["training_log"] = logs
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Session saved!")

            st.markdown("---")
            st.subheader("📊 Load Alerts")
            alerts = generate_overtraining_alerts(logs)
            if alerts:
                for level, msg in alerts:
                    st.error(msg) if level == "red" else st.warning(msg)
            else:
                st.success("Load is within safe limits.")

            if logs:
                df = pd.DataFrame(logs)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date")
                st.write("### Training Log")
                st.dataframe(df[["date", "minutes", "desc"]], use_container_width=True)

                fig, ax = plt.subplots(figsize=(8, 4))
                ax.plot(df["date"], df["minutes"], marker="o")
                ax.set_title("Training Minutes Over Time")
                ax.set_ylabel("Minutes")
                ax.set_xlabel("Date")
                plt.xticks(rotation=45)
                plt.tight_layout()
                st.pyplot(fig)

                # share snapshot code
                st.markdown("---")
                st.subheader("📤 Share Weekly Snapshot to Coach")
                if st.button("Generate Share Code"):
                    share_code = code8()
                    homework_log = data.get("homework_log", [])

                    snapshot = {
                        "username": u,
                        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                        "share_code": share_code,
                        "training_log": logs,
                        "gym_sessions": data.get("gym_sessions", []),
                        "homework_log": homework_log,
                        "weekly_training_minutes": compute_weekly_total(logs),
                        "weekly_gym_minutes": compute_weekly_total(data.get("gym_sessions", [])),
                        "weekly_study_minutes": compute_weekly_total(homework_log),
                    }

                    fname = f"{u}_snapshot_{share_code}.json"
                    local_path = os.path.join(SHARED_DIR, fname)
                    save_json(local_path, snapshot)

                    # Dropbox copy (best-effort)
                    try:
                        drop_path = os.path.join(DROPBOX_SYNC_FOLDER, fname)
                        save_json(drop_path, snapshot)
                    except Exception:
                        pass

                    st.success(f"Share Code: **{share_code}**")
                    st.info("Give this code to your coach to view your weekly snapshot.")

            else:
                st.info("No sessions logged yet.")

        # -------------------
        # Gym/Cardio & Goals
        # -------------------
        elif athlete_tab == "Gym/Cardio & Goals":
            st.subheader("🏃 Gym / Cardio Sessions & Goals")
            gym = data.get("gym_sessions", [])

            g_date = st.date_input("Date", datetime.date.today(), key="gym_date")
            g_type = st.selectbox("Session type", ["Cardio", "Gym / Weights", "Pitch session", "Other"], key="gym_type")
            g_minutes = st.number_input("Minutes", 0, 300, key="gym_minutes")
            g_goal = st.text_input("Goal (e.g. '5k in 30 mins')", key="gym_goal")
            g_rpe = st.slider("RPE (1 easy → 10 max)", 1, 10, 5, key="gym_rpe")
            g_notes = st.text_area("Notes", key="gym_notes")

            if st.button("Add Gym/Cardio Session"):
                gym.append(
                    {
                        "date": str(g_date),
                        "type": g_type,
                        "minutes": int(g_minutes),
                        "goal": g_goal,
                        "rpe": int(g_rpe),
                        "notes": g_notes,
                    }
                )
                data["gym_sessions"] = gym
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Saved!")

            if gym:
                gdf = pd.DataFrame(gym)
                gdf["date"] = pd.to_datetime(gdf["date"], errors="coerce")
                gdf = gdf.dropna(subset=["date"]).sort_values("date", ascending=False)
                st.dataframe(gdf[["date", "type", "minutes", "goal", "rpe", "notes"]].head(25), use_container_width=True)

                # RPE guidance
                recent = gdf.head(7).sort_values("date")
                if not recent.empty and "rpe" in recent.columns:
                    hard = recent[recent["rpe"] >= 8]
                    if len(hard) >= 2:
                        st.warning("Multiple hard sessions (RPE 8–10) recently. Try to avoid two red days in a row.")
                    else:
                        st.success("RPE balance looks good — keep mixing hard and easy days.")

        # -------------------
        # Diet / Macros (legacy safe)
        # -------------------
        elif athlete_tab == "Diet / Macros":
            st.subheader("🍎 Diet / Macros")
            diet = data.get("diet_log", [])

            meal = st.text_input("Meal / Snack", key="diet_meal")
            calories = st.number_input("Calories", 0, 5000, key="diet_calories")
            protein = st.number_input("Protein (g)", 0, 500, key="diet_protein")
            carbs = st.number_input("Carbs (g)", 0, 500, key="diet_carbs")
            fat = st.number_input("Fat (g)", 0, 500, key="diet_fat")

            if st.button("Add Meal"):
                diet.append(
                    {
                        "date": str(datetime.date.today()),
                        "meal": meal,
                        "calories": int(calories),
                        "protein": int(protein),
                        "carbs": int(carbs),
                        "fat": int(fat),
                    }
                )
                data["diet_log"] = diet
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Saved!")

            if diet:
                df = pd.DataFrame(diet)
                # ensure columns exist even for older entries
                for col in ["calories", "protein", "carbs", "fat"]:
                    if col not in df.columns:
                        df[col] = 0
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)

                today = datetime.date.today()
                today_df = df[df["date"].dt.date == today]
                st.write(
                    f"**Today totals:** {int(today_df['calories'].sum())} kcal • "
                    f"P {int(today_df['protein'].sum())}g • C {int(today_df['carbs'].sum())}g • F {int(today_df['fat'].sum())}g"
                )
            else:
                st.info("No meals logged yet.")

        # -------------------
        # Training Plans (download)
        # -------------------
        elif athlete_tab == "Training Plans":
            st.subheader("📄 Training Plans")

            # team memberships
            teams = load_teams()
            team_codes = [code for code, t in teams.items() if u in t.get("athletes", [])]

            direct_folder = plans_folder_for_athlete(u)
            team_folders = [plans_folder_for_team(code) for code in team_codes]

            found_any = False

            # direct plans
            if os.path.exists(direct_folder):
                idx = load_plans_index(direct_folder)
                plans = idx.get("plans", [])
                if plans:
                    found_any = True
                    st.write("### Assigned to you")
                    for p in reversed(plans[-30:]):
                        fpath = os.path.join(direct_folder, p.get("file", ""))
                        if not os.path.exists(fpath):
                            continue
                        st.markdown(f"**{p.get('title','Training Plan')}**  \nUploaded: {p.get('uploaded_at','')}")
                        with open(fpath, "rb") as f:
                            st.download_button(
                                "Download",
                                data=f.read(),
                                file_name=p.get("file", "plan"),
                                mime="application/octet-stream",
                                key=f"dl_ath_{p.get('file','')}",
                            )
                        st.markdown("---")

            # team plans
            if team_codes:
                for code in team_codes:
                    folder = plans_folder_for_team(code)
                    if not os.path.exists(folder):
                        continue
                    idx = load_plans_index(folder)
                    plans = idx.get("plans", [])
                    if plans:
                        found_any = True
                        st.write(f"### Team plans — `{code}`")
                        for p in reversed(plans[-30:]):
                            fpath = os.path.join(folder, p.get("file", ""))
                            if not os.path.exists(fpath):
                                continue
                            st.markdown(f"**{p.get('title','Training Plan')}**  \nUploaded: {p.get('uploaded_at','')}")
                            with open(fpath, "rb") as f:
                                st.download_button(
                                    "Download",
                                    data=f.read(),
                                    file_name=p.get("file", "plan"),
                                    mime="application/octet-stream",
                                    key=f"dl_team_{code}_{p.get('file','')}",
                                )
                            st.markdown("---")

            if not found_any:
                st.info("No training plans uploaded for you yet.")

        # -------------------
        # Fixtures
        # -------------------
        elif athlete_tab == "Fixtures":
            st.subheader("📆 Fixtures")
            fixtures = data.get("fixtures", [])

            f_date = st.date_input("Match date", datetime.date.today(), key="fix_date")
            f_time = st.time_input("Match time", datetime.time(19, 0), key="fix_time")
            opponent = st.text_input("Opponent / Team", key="fix_opp")
            venue = st.text_input("Venue / Pitch", key="fix_venue")
            notes = st.text_area("Notes", key="fix_notes")

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
                st.dataframe(fdf.sort_values("date"), use_container_width=True)
            else:
                st.info("No fixtures yet.")

        # -------------------
        # Homework / Study
        # -------------------
        elif athlete_tab == "Homework / Study":
            st.subheader("📚 Homework / Study Log")
            hw = data.get("homework_log", [])

            h_date = st.date_input("Date", datetime.date.today(), key="hw_date")
            subject = st.text_input("Subject / Topic", key="hw_subject")
            minutes = st.number_input("Minutes studied", 0, 600, key="hw_minutes")
            h_notes = st.text_area("Notes", key="hw_notes")

            if st.button("Add Study Session"):
                hw.append({"date": str(h_date), "subject": subject, "minutes": int(minutes), "notes": h_notes})
                data["homework_log"] = hw
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Saved!")

            if hw:
                hdf = pd.DataFrame(hw)
                st.dataframe(hdf.sort_values("date", ascending=False), use_container_width=True)
                st.write(f"**Study minutes this week:** {compute_weekly_total(hw)}")
            else:
                st.info("No study logged yet.")

        # -------------------
        # Mental Wellbeing
        # -------------------
        elif athlete_tab == "Mental Wellbeing":
            st.subheader("🧠 Wellbeing Check-In")
            wb = data.get("wellbeing_log", [])

            w_date = st.date_input("Date", datetime.date.today(), key="wb_date")
            mood = st.slider("Mood (1 low → 10 great)", 1, 10, 5, key="wb_mood")
            stress = st.slider("Stress (1 calm → 10 high)", 1, 10, 5, key="wb_stress")
            sleep = st.number_input("Sleep (hours)", 0.0, 24.0, 8.0, 0.5, key="wb_sleep")
            w_notes = st.text_area("Notes", key="wb_notes")

            if st.button("Save Check-In"):
                wb.append({"date": str(w_date), "mood": mood, "stress": stress, "sleep": float(sleep), "notes": w_notes})
                data["wellbeing_log"] = wb
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Saved!")

            if wb:
                wdf = pd.DataFrame(wb)
                st.dataframe(wdf.sort_values("date", ascending=False).head(14), use_container_width=True)

        # -------------------
        # Teams & Coach Codes
        # -------------------
        elif athlete_tab == "Teams & Coach Codes":
            st.subheader("👥 Teams & Coach Codes")

            st.write("Join a team using a code given by your coach.")
            team_code = st.text_input("Enter team code", key="team_join_code").strip().upper()

            if st.button("Join Team"):
                if not team_code:
                    st.error("Enter a team code.")
                else:
                    teams = load_teams()
                    if team_code not in teams:
                        st.error("Team code not found.")
                    else:
                        roster = teams[team_code].get("athletes", [])
                        if u in roster:
                            st.info("You're already in this team.")
                        else:
                            roster.append(u)
                            teams[team_code]["athletes"] = roster
                            save_teams(teams)
                            st.success("Joined team!")

            # show joined teams
            teams = load_teams()
            joined = [(code, t.get("team_name", code)) for code, t in teams.items() if u in t.get("athletes", [])]
            if joined:
                st.write("### Your teams")
                for code, name in joined:
                    st.write(f"- **{name}** — `{code}`")
            else:
                st.info("You haven't joined a team yet.")

        # -------------------
        # Chat / CoachBot
        # -------------------
        elif athlete_tab == "Chat / CoachBot":
            st.subheader("💬 CoachBot — Motivation & Balance")
            chat = data.get("chat", [])

            if chat:
                for entry in chat[-12:]:
                    role = entry.get("role", "athlete")
                    prefix = "🧍‍♂️ You" if role == "athlete" else "🤖 CoachBot"
                    st.markdown(f"**{prefix}:** {entry.get('msg','')}")
                st.markdown("---")

            msg = st.text_input("Message CoachBot", key="cb_msg")

            def coachbot_reply(m: str) -> str:
                m = (m or "").lower()
                if any(w in m for w in ["tired", "wrecked", "sore"]):
                    return "If you're tired, that's information. Consider an easier session, stretch, hydrate, and get sleep — recovery is training."
                if any(w in m for w in ["exam", "school", "homework", "study"]):
                    return "Plan short focused study blocks around training. Consistency beats last-minute panic. Balance wins."
                if any(w in m for w in ["nervous", "anxious", "worried"]):
                    return "Nerves mean you care. Control sleep, food, and your warm-up. Focus on the next action — not the whole game."
                return "Keep the balance: school + training + recovery. Small habits daily build big results."

            if st.button("Send"):
                if msg.strip():
                    now = datetime.datetime.now().isoformat(timespec="seconds")
                    chat.append({"role": "athlete", "msg": msg.strip(), "time": now})
                    reply = coachbot_reply(msg)
                    chat.append({"role": "coachbot", "msg": reply, "time": now})
                    data["chat"] = chat
                    save_athlete(u, data)
                    st.session_state["athlete_data"] = data
                    st.success("Sent!")

        # -------------------
        # Recovery Advice
        # -------------------
        elif athlete_tab == "Recovery Advice":
            st.subheader("🛌 Recovery Advice")
            train_week = compute_weekly_total(data.get("training_log", []))
            gym_week = compute_weekly_total(data.get("gym_sessions", []))
            study_week = compute_weekly_total(data.get("homework_log", []))
            total = train_week + gym_week

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Field minutes/week", train_week)
            c2.metric("Gym minutes/week", gym_week)
            c3.metric("Total minutes/week", total)
            c4.metric("Study minutes/week", study_week)

            if total > 450:
                st.error("Very high load this week. Prioritise sleep, nutrition and consider a full rest day.")
            elif total > 300:
                st.warning("Solid week. Add a genuine easy day or rest day.")
            else:
                st.success("Load looks manageable. Keep building steadily.")

        # -------------------
        # Account / Family Info
        # -------------------
        elif athlete_tab == "Account / Family Info":
            st.subheader("👤 Account")
            st.write(f"**Username:** {u}")

            # find family codes by scanning families file (recovery-friendly)
            fams = load_families()
            linked = []
            for code, fam in fams.items():
                if u in fam.get("children", []):
                    linked.append(code)
            if linked:
                st.write("### Linked family code(s)")
                st.write(", ".join(f"`{c}`" for c in linked))
            else:
                st.info("No family linked yet.")

# ============================================================
# COACH DASHBOARD (PIN login required)
# ============================================================
elif mode == "Coach Dashboard":
    st.header("🎓 Coach Dashboard")

    if not st.session_state["coach_logged_in"]:
        st.subheader("Coach Login")
        cu = st.text_input("Coach username", key="coach_login_user")
        cp = st.text_input("Coach PIN", type="password", key="coach_login_pin")
        if st.button("Log in as Coach"):
            if check_coach(cu.strip(), cp):
                st.session_state["coach_logged_in"] = True
                st.session_state["coach_user"] = cu.strip()
                st.success("Coach login successful.")
            else:
                st.error("Invalid coach username or PIN.")
        st.info("Coach accounts are created in **Admin / Settings**.")
    else:
        coach_user = st.session_state["coach_user"]
        st.success(f"Logged in as Coach: {coach_user}")

        if st.button("Coach Log Out"):
            st.session_state["coach_logged_in"] = False
            st.session_state["coach_user"] = ""
            st.success("Logged out.")

        coach_tab = st.radio(
            "Choose view",
            ["Individual Athlete (share code)", "Team Overview", "Training Plans", "Coach Staffroom"],
        )

        # ---- Individual Athlete via share code ----
        if coach_tab == "Individual Athlete (share code)":
            st.write("Enter an athlete share code to view their weekly snapshot.")

            share_code_input = st.text_input("Athlete share code", key="coach_share_code")

            if st.button("Load Athlete Snapshot"):
                if not share_code_input.strip():
                    st.error("Enter a share code.")
                else:
                    files = [f for f in os.listdir(SHARED_DIR) if f.endswith(".json")]
                    matched = None
                    for fname in files:
                        fp = os.path.join(SHARED_DIR, fname)
                        snap = load_json(fp, {})
                        if snap.get("share_code") == share_code_input.strip():
                            matched = snap
                            break

                    if not matched:
                        st.error("No snapshot found for that code.")
                    else:
                        st.success("Snapshot loaded.")
                        st.write(f"**Athlete:** {matched.get('username','')}")
                        st.write(f"**Generated:** {matched.get('generated_at','')}")

                        col1, col2, col3 = st.columns(3)
                        col1.metric("Training min/week", int(matched.get("weekly_training_minutes", 0)))
                        col2.metric("Gym min/week", int(matched.get("weekly_gym_minutes", 0)))
                        col3.metric("Study min/week", int(matched.get("weekly_study_minutes", 0)))

                        st.markdown("---")
                        st.write("### Training Log")
                        tlog = matched.get("training_log", [])
                        if tlog:
                            st.dataframe(pd.DataFrame(tlog), use_container_width=True)
                        else:
                            st.info("No training log in snapshot.")

                        st.write("### Gym Sessions")
                        glog = matched.get("gym_sessions", [])
                        if glog:
                            st.dataframe(pd.DataFrame(glog), use_container_width=True)
                        else:
                            st.info("No gym sessions in snapshot.")

                        st.write("### Study Log")
                        hw = matched.get("homework_log", [])
                        if hw:
                            st.dataframe(pd.DataFrame(hw), use_container_width=True)
                        else:
                            st.info("No study log in snapshot.")

        # ---- Team Overview (join code) ----
        elif coach_tab == "Team Overview":
            st.subheader("Team Codes")

            st.markdown("### Create a team")
            team_name = st.text_input("Team name (e.g. U16A Football)", key="team_name")
            if st.button("Create Team Code"):
                if not team_name.strip():
                    st.error("Enter a team name.")
                else:
                    teams = load_teams()
                    code = code6()
                    while code in teams:
                        code = code6()
                    teams[code] = {"team_name": team_name.strip(), "coach": coach_user, "athletes": []}
                    save_teams(teams)
                    st.success(f"Team code created: **{code}** (players use this to join)")

            st.markdown("---")
            st.markdown("### View a team")
            view_code = st.text_input("Enter team code", key="team_view_code").strip().upper()
            if st.button("Load Team"):
                teams = load_teams()
                if view_code not in teams:
                    st.error("Team code not found.")
                else:
                    team = teams[view_code]
                    st.write(f"**Team:** {team.get('team_name', view_code)}")
                    roster = team.get("athletes", [])
                    if not roster:
                        st.info("No athletes joined yet.")
                    else:
                        rows = []
                        for athlete in roster:
                            fp = athlete_file(athlete)
                            if not os.path.exists(fp):
                                continue
                            ad = load_json(fp, {})
                            train_week = compute_weekly_total(ad.get("training_log", []))
                            gym_week = compute_weekly_total(ad.get("gym_sessions", []))
                            total = train_week + gym_week

                            if total >= 300:
                                status = "🔴 High"
                            elif total >= 150:
                                status = "🟠 Moderate"
                            else:
                                status = "🟢 Light"

                            rows.append({"Athlete": athlete, "Weekly minutes": total, "Status": status})
                        df = pd.DataFrame(rows).sort_values("Weekly minutes", ascending=False)
                        st.dataframe(df, use_container_width=True)

        # ---- Training Plans (upload + assign) ----
        elif coach_tab == "Training Plans":
            st.subheader("📄 Training Plans (Upload & Assign)")

            assign_type = st.radio("Assign plan to:", ["Team", "Individual Athlete"], horizontal=True, key="plan_assign_type")
            team_code = ""
            athlete_user = ""

            if assign_type == "Team":
                team_code = st.text_input("Team code", key="plan_team_code").strip().upper()
            else:
                athlete_user = st.text_input("Athlete username", key="plan_athlete_user").strip()

            uploaded = st.file_uploader(
                "Upload plan (PDF/DOCX/PNG/JPG)",
                type=["pdf", "docx", "png", "jpg", "jpeg"],
                key="plan_uploader"
            )
            plan_title = st.text_input("Plan title (optional)", key="plan_title")

            if st.button("Save Training Plan"):
                if uploaded is None:
                    st.error("Choose a file.")
                elif assign_type == "Team" and not team_code:
                    st.error("Enter a team code.")
                elif assign_type == "Individual Athlete" and not athlete_user:
                    st.error("Enter an athlete username.")
                else:
                    folder = plans_folder_for_team(team_code) if assign_type == "Team" else plans_folder_for_athlete(athlete_user)
                    os.makedirs(folder, exist_ok=True)

                    original = safe_filename(uploaded.name)
                    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    fname = f"{stamp}_{original}"
                    fpath = os.path.join(folder, fname)

                    with open(fpath, "wb") as f:
                        f.write(uploaded.getbuffer())

                    idx = load_plans_index(folder)
                    idx["plans"].append({
                        "file": fname,
                        "title": plan_title.strip() if plan_title.strip() else original,
                        "uploaded_at": datetime.datetime.now().isoformat(timespec="seconds"),
                        "assigned_to": team_code if assign_type == "Team" else athlete_user,
                        "type": "team" if assign_type == "Team" else "athlete",
                        "uploaded_by": coach_user,
                    })
                    save_plans_index(folder, idx)

                    st.success("Training plan uploaded!")

            st.markdown("---")
            st.write("### Browse existing plans")
            browse_team = st.text_input("Browse team code (optional)", key="browse_team").strip().upper()
            browse_ath = st.text_input("Browse athlete username (optional)", key="browse_ath").strip()

            folders = []
            if browse_team:
                folders.append(("Team", browse_team, plans_folder_for_team(browse_team)))
            if browse_ath:
                folders.append(("Athlete", browse_ath, plans_folder_for_athlete(browse_ath)))

            if folders:
                for label, who, folder in folders:
                    if not os.path.exists(folder):
                        st.info(f"No folder for {label} {who}.")
                        continue
                    idx = load_plans_index(folder)
                    plans = idx.get("plans", [])
                    st.write(f"**{label}: {who}**")
                    if not plans:
                        st.info("No plans.")
                        continue
                    for p in reversed(plans[-20:]):
                        st.write(f"- {p.get('title','Plan')} ({p.get('uploaded_at','')}) by {p.get('uploaded_by','')}")
            else:
                st.caption("Enter a team code or athlete username above to browse plans.")

        # ---- Coach Staffroom ----
        elif coach_tab == "Coach Staffroom":
            st.subheader("🧑‍🏫 Coach Staffroom (Coach-to-Coach)")

            forum = load_forum()
            msgs = forum.get("messages", [])

            col1, col2 = st.columns([2, 1])
            with col1:
                team_code = st.text_input("Team code (optional)", key="forum_team").strip().upper()
                text = st.text_area("Message", key="forum_text", height=120)
                if st.button("Post Message"):
                    if not text.strip():
                        st.error("Write a message first.")
                    else:
                        msgs.append({
                            "time": datetime.datetime.now().isoformat(timespec="seconds"),
                            "coach": coach_user,
                            "team_code": team_code,
                            "text": text.strip(),
                        })
                        forum["messages"] = msgs
                        save_forum(forum)
                        st.success("Posted.")

            with col2:
                st.write("### Filter")
                filter_team = st.text_input("Filter by team code", key="forum_filter").strip().upper()

            st.markdown("---")
            st.write("### Recent messages")
            for m in reversed(msgs[-80:]):
                if filter_team and m.get("team_code", "") != filter_team:
                    continue
                tag = f" · Team: `{m['team_code']}`" if m.get("team_code") else ""
                st.markdown(f"**{m.get('coach','Coach')}** ({m.get('time','')}){tag}")
                st.write(m.get("text", ""))
                st.markdown("---")

# ============================================================
# PARENT / GUARDIAN
# ============================================================
elif mode == "Parent / Guardian":
    st.header("👨‍👩‍👦 Parent / Guardian Dashboard")

    parent_tab = st.radio("Select:", ["Create / Manage Family", "Family Weekly & Monthly Calendar"])

    families = load_families()

    if parent_tab == "Create / Manage Family":
        st.subheader("Create a Family Code")
        family_name = st.text_input("Family name (e.g. Murphy Family)", key="fam_name")
        if st.button("Create Family"):
            if not family_name.strip():
                st.error("Enter a family name.")
            else:
                families = load_families()
                code = code6()
                while code in families:
                    code = code6()
                families[code] = {"family_name": family_name.strip(), "children": [], "colours": {}}
                save_families(families)
                st.success(f"Family code: **{code}**")

        st.markdown("---")
        st.subheader("Link an Athlete to Your Family")

        fam_code = st.text_input("Family code", key="link_fam_code").strip().upper()
        ath_user = st.text_input("Athlete username", key="link_user").strip()
        ath_pin = st.text_input("Athlete PIN (verification)", type="password", key="link_pin")

        if st.button("Link Athlete"):
            families = load_families()
            if fam_code not in families:
                st.error("Family code not found.")
            else:
                ok, adata = check_athlete_login(ath_user, ath_pin)
                if not ok:
                    st.error("Could not verify athlete username/PIN.")
                else:
                    children = families[fam_code].get("children", [])
                    if ath_user in children:
                        st.info("Athlete already linked.")
                    else:
                        children.append(ath_user)
                        families[fam_code]["children"] = children
                        save_families(families)
                        st.success("Linked!")

    else:
        st.subheader("Family Calendar")
        fam_code = st.text_input("Enter your family code", key="fam_view_code").strip().upper()

        if not fam_code:
            st.info("Enter a family code to view.")
        else:
            families = load_families()
            if fam_code not in families:
                st.error("Family code not found.")
            else:
                family = families[fam_code]
                st.success(f"Family: {family.get('family_name','Family')}")
                children = family.get("children", [])
                if not children:
                    st.info("No athletes linked yet.")
                else:
                    today = datetime.date.today()
                    year, month = today.year, today.month

                    # Assign colours per athlete
                    colours = family.get("colours", {})
                    for child in children:
                        if child not in colours:
                            colours[child] = random.choice(["#81c784","#64b5f6","#ffb74d","#e57373","#ba68c8","#4db6ac"])
                    family["colours"] = colours
                    families[fam_code] = family
                    save_families(families)

                    # Month mapping
                    day_entries = {}

                    # Weekly list view
                    week = today.isocalendar()[1]
                    rows = []
                    per_child_week = {}

                    for child in children:
                        fp = athlete_file(child)
                        if not os.path.exists(fp):
                            continue
                        ad = load_json(fp, {})
                        combined = ad.get("training_log", []) + ad.get("gym_sessions", [])
                        per_child_week[child] = compute_weekly_total(combined)

                        for e in combined:
                            try:
                                d = datetime.datetime.strptime(e.get("date",""), "%Y-%m-%d").date()
                            except Exception:
                                continue
                            if d.year == today.year and d.isocalendar()[1] == week:
                                rows.append({
                                    "Date": d,
                                    "Athlete": child,
                                    "Minutes": int(e.get("minutes", 0)),
                                    "Description": e.get("desc", e.get("goal","")),
                                })
                            if d.year == year and d.month == month:
                                day_entries.setdefault(d, []).append((child, colours.get(child)))

                    if rows:
                        df = pd.DataFrame(rows).sort_values("Date")
                        st.write("### This Week (List View)")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No sessions logged this week.")

                    st.markdown("---")
                    st.write("### Weekly Minutes (per athlete)")
                    cols = st.columns(min(len(children), 4))
                    for i, child in enumerate(children):
                        with cols[i % len(cols)]:
                            st.metric(child, per_child_week.get(child, 0))
                            st.markdown(f"<span style='color:{colours.get(child)}; font-size:22px;'>●</span>", unsafe_allow_html=True)

                    st.markdown("---")
                    st.write("### Month View")
                    cal = calendar.monthcalendar(year, month)

                    def dot(hex_colour):
                        return f"<span style='color:{hex_colour}; font-size:18px;'>●</span>"

                    html = "<table style='border-collapse: collapse; width: 100%;'>"
                    html += "<tr>" + "".join([f"<th style='border:1px solid #ced9ce; padding:4px; text-align:center;'>{d}</th>" for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]]) + "</tr>"
                    for wk in cal:
                        html += "<tr>"
                        for day in wk:
                            if day == 0:
                                html += "<td style='border:1px solid #ced9ce; padding:6px; height:65px;'></td>"
                            else:
                                dt = datetime.date(year, month, day)
                                dots = " ".join([dot(c) for _, c in day_entries.get(dt, [])])
                                html += (
                                    "<td style='border:1px solid #ced9ce; padding:6px; vertical-align:top; height:65px;'>"
                                    f"<div style='font-weight:700;'>{day}</div>"
                                    f"<div>{dots}</div>"
                                    "</td>"
                                )
                        html += "</tr>"
                    html += "</table>"
                    st.markdown(html, unsafe_allow_html=True)

# ============================================================
# ADMIN / SETTINGS
# ============================================================
elif mode == "Admin / Settings":
    st.header("⚙️ Admin / Settings")

    st.subheader("Coach Accounts (PIN)")
    st.write("Create coach accounts here. Coaches must log in with username + PIN to access Coach Dashboard features.")

    cu = st.text_input("New coach username", key="admin_coach_user")
    cp = st.text_input("New coach PIN", type="password", key="admin_coach_pin")
    cp2 = st.text_input("Confirm coach PIN", type="password", key="admin_coach_pin2")

    if st.button("Create Coach Account"):
        if not cu.strip() or not cp:
            st.error("Enter a username and PIN.")
        elif cp != cp2:
            st.error("PINs do not match.")
        else:
            ok, msg = register_coach(cu.strip(), cp)
            st.success(msg) if ok else st.error(msg)

    st.markdown("---")
    st.subheader("Dropbox sync folder")
    st.write(f"Configured: {DROPBOX_SYNC_FOLDER}")
