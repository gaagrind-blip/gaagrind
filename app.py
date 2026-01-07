import streamlit as st
import json, os, datetime
import pandas as pd
import random
import string
import calendar as cal_mod

# -----------------------------
# File/Folder Setup
# -----------------------------
DATA_DIR = "data"
ATHLETES_DIR = os.path.join(DATA_DIR, "athletes")

TEAMS_FILE = os.path.join(DATA_DIR, "teams.json")
FAMILY_LINKS_FILE = os.path.join(DATA_DIR, "family_links.json")   # single-child codes
FAMILIES_FILE = os.path.join(DATA_DIR, "families.json")           # multi-child families (calendar)
TRAINING_PLANS_DIR = os.path.join(DATA_DIR, "training_plans")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ATHLETES_DIR, exist_ok=True)
os.makedirs(TRAINING_PLANS_DIR, exist_ok=True)

ATHLETE_COLORS = [
    "#2E8B57", "#1E90FF", "#FF6347", "#FFD700", "#8A2BE2",
    "#00CED1", "#FF69B4", "#A0522D", "#2F4F4F", "#7FFF00",
]

# -----------------------------
# Helpers
# -----------------------------
def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def safe_filename(name: str) -> str:
    keep = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- "
    cleaned = "".join(c for c in name if c in keep).strip().replace(" ", "_")
    return cleaned[:80] if cleaned else "plan"

def clean_username(raw: str) -> str:
    """Normalise usernames so Register/Login always point to the same stored profile."""
    raw = (raw or "").strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    cleaned = "".join(ch for ch in raw if ch in allowed)
    return cleaned.lower()

def athlete_file(username: str) -> str:
    """Always store athlete profiles under a normalised filename."""
    return os.path.join(ATHLETES_DIR, clean_username(username) + ".json")

def compute_weekly_summary(entries, minutes_key="minutes"):
    week = datetime.date.today().isocalendar()[1]
    year = datetime.date.today().year
    total_minutes = 0
    for e in entries:
        try:
            d = datetime.datetime.strptime(e["date"], "%Y-%m-%d").date()
            if d.isocalendar()[1] == week and d.year == year:
                total_minutes += int(e.get(minutes_key, 0))
        except Exception:
            pass
    return total_minutes

def weekly_color(total_minutes):
    # Keeping your existing labels/thresholds as-is
    if total_minutes >= 300:
        return "🟢", "Excellent"
    elif total_minutes >= 240:
        return "🟢", "Very Good"
    elif total_minutes >= 180:
        return "🟡", "Good"
    elif total_minutes >= 120:
        return "🔴", "High"
    elif total_minutes >= 150:
        return "🟠", "Moderate"
    else:
        return "🟢", "Light"

def stress_label(stress: int):
    """
    ✅ Correct mapping:
    1 = low stress (good)
    10 = very high stress (not good)
    """
    if stress <= 3:
        return "🟢 Great", "Low stress"
    elif stress <= 6:
        return "🟡 Okay", "Moderate stress"
    elif stress <= 8:
        return "🟠 High", "High stress"
    else:
        return "🔴 Struggling", "Very high stress"

# -----------------------------
# Training Plans helpers
# -----------------------------
def plans_folder_for_team(team_code: str) -> str:
    return os.path.join(TRAINING_PLANS_DIR, f"team_{team_code}")

def plans_folder_for_athlete(username: str) -> str:
    return os.path.join(TRAINING_PLANS_DIR, f"athlete_{clean_username(username)}")

def ensure_folder(path: str):
    os.makedirs(path, exist_ok=True)

def list_plan_files(folder: str):
    ensure_folder(folder)
    return sorted([fn for fn in os.listdir(folder) if fn.lower().endswith(".json")])

def save_plan(folder: str, plan_name: str, plan_data: dict):
    ensure_folder(folder)
    fn = safe_filename(plan_name) + ".json"
    save_json(os.path.join(folder, fn), plan_data)

def load_plan(folder: str, filename: str):
    return load_json(os.path.join(folder, filename), {})

# -----------------------------
# Teams helpers
# -----------------------------
def generate_team_code(length=6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))

def load_teams():
    return load_json(TEAMS_FILE, {})

def save_teams(teams):
    save_json(TEAMS_FILE, teams)

# -----------------------------
# Family helpers (single-child + multi-child)
# -----------------------------
def load_family_links():
    return load_json(FAMILY_LINKS_FILE, {})

def save_family_links(links):
    save_json(FAMILY_LINKS_FILE, links)

def link_family_code_to_athlete(code: str, athlete_username: str):
    links = load_family_links()
    links[code] = clean_username(athlete_username)
    save_family_links(links)

def get_athlete_for_family_code(code: str):
    links = load_family_links()
    return links.get(code)

def load_families():
    """Multi-child families: {code: {family_name, children:[{username,color},...]}}"""
    data = load_json(FAMILIES_FILE, {})
    changed = False
    for code, fam in data.items():
        children = fam.get("children", [])
        new_children = []
        used_colors = set()
        for child in children:
            if isinstance(child, str):
                username = child
                color = None
            else:
                username = child.get("username")
                color = child.get("color")
            if not username:
                continue
            if not color:
                # assign first unused colour
                for c in ATHLETE_COLORS:
                    if c not in used_colors:
                        color = c
                        break
                else:
                    color = random.choice(ATHLETE_COLORS)
                changed = True
            used_colors.add(color)
            new_children.append({"username": clean_username(username), "color": color})
        fam["children"] = new_children
    if changed:
        save_json(FAMILIES_FILE, data)
    return data

def save_families(families):
    save_json(FAMILIES_FILE, families)

def add_child_to_family(code: str, username: str):
    """Ensures a family exists and includes this athlete (for compatibility + future)."""
    code = (code or "").strip()
    if not code:
        return False
    username = clean_username(username)
    families = load_families()
    fam = families.get(code, {"family_name": "Family", "children": []})
    # Already exists?
    for c in fam.get("children", []):
        if c.get("username") == username:
            families[code] = fam
            save_families(families)
            return True
    used = {c.get("color") for c in fam.get("children", []) if c.get("color")}
    col = next((c for c in ATHLETE_COLORS if c not in used), random.choice(ATHLETE_COLORS))
    fam.setdefault("children", []).append({"username": username, "color": col})
    families[code] = fam
    save_families(families)
    return True

# -----------------------------
# Login Functions
# -----------------------------
def save_athlete(u, data):
    u_clean = clean_username(u)
    if isinstance(data, dict):
        data.setdefault("username", u_clean)
    save_json(athlete_file(u_clean), data)

def check_athlete_login(u, p):
    u_clean = clean_username(u)
    file = athlete_file(u_clean)

    # Legacy fallback (older versions used raw typed username filenames)
    legacy = os.path.join(ATHLETES_DIR, (u or "").strip() + ".json")
    if not os.path.exists(file) and os.path.exists(legacy):
        file = legacy

    if not os.path.exists(file):
        return False, None

    data = load_json(file)
    ok = (data.get("pin") == p)

    # Auto-migrate legacy file if login succeeds
    if ok and file == legacy:
        data["username"] = u_clean
        save_json(athlete_file(u_clean), data)

    return ok, data

def register_coach(user, pin):
    path = os.path.join(DATA_DIR, "coaches.json")
    data = load_json(path, {})
    user_clean = clean_username(user)
    if user_clean in data:
        return False, "Coach already exists"
    data[user_clean] = pin
    save_json(path, data)
    return True, "Coach registered"

def check_coach(user, pin):
    data = load_json(os.path.join(DATA_DIR, "coaches.json"), {})
    return data.get(clean_username(user)) == pin

# -----------------------------
# Streamlit App Configuration
# -----------------------------
st.set_page_config(page_title="Performance Pulse", page_icon="🏐", layout="wide")

st.markdown(
    """
<style>
.block-container { padding-top: 1rem; padding-bottom: 4rem; }
hr { border: none; border-top: 1px solid #ced9ce; margin: 1rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

st.sidebar.title("Navigation")
mode = st.sidebar.selectbox(
    "Choose Mode",
    ["Athlete Portal", "Coach Dashboard", "Parent / Guardian", "Admin / Settings"],
)

# Session State
if "athlete_logged_in" not in st.session_state:
    st.session_state["athlete_logged_in"] = False
    st.session_state["athlete_user"] = ""
    st.session_state["athlete_data"] = None

if "coach_logged_in" not in st.session_state:
    st.session_state["coach_logged_in"] = False
    st.session_state["coach_user"] = ""

# -----------------------------
# Athlete Portal
# -----------------------------
if mode == "Athlete Portal":
    st.header("🏋️ Athlete Portal")
    sub_mode = st.radio("Select:", ["Register", "Login"])

    if sub_mode == "Register":
        st.subheader("New Athlete Registration")
        new_user_raw = st.text_input("Username", key="reg_user")
        new_user = clean_username(new_user_raw)
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
                        "created": datetime.datetime.now().isoformat(),
                        "color": random.choice(ATHLETE_COLORS),
                        "training_log": [],
                        "gym_log": [],
                        "diet_log": [],
                        "fixtures": [],
                        "study_log": [],
                        "wellbeing_log": [],
                        "goals": {"gym": "", "cardio": "", "diet": "", "study": "", "wellbeing": ""},
                        "family_info": {"parent_name": "", "parent_email": "", "phone": "", "notes": ""},
                        "teams": [],
                    },
                )
                st.success(f"Athlete {new_user} registered! You can now log in.")

    elif sub_mode == "Login" and not st.session_state["athlete_logged_in"]:
        st.subheader("Athlete Login")
        u_raw = st.text_input("Username", key="login_user")
        u = clean_username(u_raw)
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

        if athlete_tab == "Training Log":
            st.subheader("📅 Training Log")
            entries = data.get("training_log", [])
            total = compute_weekly_summary(entries, "minutes")
            icon, label = weekly_color(total)
            st.info(f"Weekly total: **{total} mins** — {icon} {label}")

            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date", value=datetime.date.today(), key="train_date")
                minutes = st.number_input("Minutes trained", min_value=0, max_value=600, value=60, key="train_mins")
            with col2:
                session_type = st.selectbox("Session type", ["Pitch", "Gym", "Match", "Recovery", "Other"], key="train_type")
                notes = st.text_area("Notes", key="train_notes")

            if st.button("Add Training Entry"):
                entries.append({"date": date.strftime("%Y-%m-%d"), "minutes": int(minutes), "type": session_type, "notes": notes})
                data["training_log"] = entries
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Training entry added.")

            if entries:
                df = pd.DataFrame(entries)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date", ascending=False)
                st.dataframe(df, use_container_width=True)

        elif athlete_tab == "Gym/Cardio & Goals":
            st.subheader("🏋️ Gym/Cardio & Goals")
            goals = data.get("goals", {})
            st.write("### Goals")
            goals["gym"] = st.text_input("Gym goal", value=goals.get("gym", ""), key="goal_gym")
            goals["cardio"] = st.text_input("Cardio goal", value=goals.get("cardio", ""), key="goal_cardio")
            if st.button("Save Goals"):
                data["goals"] = goals
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Goals saved.")

            st.write("---")
            st.write("### Log a Gym/Cardio Session")
            gdate = st.date_input("Date", value=datetime.date.today(), key="gym_date")
            gtype = st.selectbox("Type", ["Gym", "Cardio"], key="gym_type")
            gmins = st.number_input("Minutes", min_value=0, max_value=600, value=45, key="gym_mins")
            gnotes = st.text_area("Notes", key="gym_notes")
            if st.button("Add Gym/Cardio Entry"):
                glog = data.get("gym_log", [])
                glog.append({"date": gdate.strftime("%Y-%m-%d"), "type": gtype, "minutes": int(gmins), "notes": gnotes})
                data["gym_log"] = glog
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Entry added.")

            glog = data.get("gym_log", [])
            if glog:
                df = pd.DataFrame(glog)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date", ascending=False)
                st.dataframe(df, use_container_width=True)

        elif athlete_tab == "Diet / Macros":
            st.subheader("🥗 Diet / Macros")
            ddate = st.date_input("Date", value=datetime.date.today(), key="diet_date")
            meal = st.selectbox("Meal", ["Breakfast", "Lunch", "Dinner", "Snack"], key="diet_meal")
            desc = st.text_area("What did you eat?", key="diet_desc")
            if st.button("Add Diet Entry"):
                dlog = data.get("diet_log", [])
                dlog.append({"date": ddate.strftime("%Y-%m-%d"), "meal": meal, "desc": desc})
                data["diet_log"] = dlog
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Diet entry added.")
            dlog = data.get("diet_log", [])
            if dlog:
                df = pd.DataFrame(dlog)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date", ascending=False)
                st.dataframe(df, use_container_width=True)

        elif athlete_tab == "Training Plans":
            st.subheader("🗂️ Training Plans")
            teams = data.get("teams", [])
            colA, colB = st.columns(2)
            with colA:
                st.write("### Personal Plans")
                folder = plans_folder_for_athlete(u)
                files = list_plan_files(folder)
                if files:
                    selected = st.selectbox("Select a personal plan", files, key="ath_plan_select")
                    st.json(load_plan(folder, selected))
                else:
                    st.info("No personal plans yet.")
            with colB:
                st.write("### Team Plans")
                if not teams:
                    st.info("Join a team in **Teams & Coach Codes** to access team plans.")
                else:
                    team_code = st.selectbox("Select team", teams, key="ath_team_select")
                    team_folder = plans_folder_for_team(team_code)
                    team_files = list_plan_files(team_folder)
                    if team_files:
                        sel = st.selectbox("Select a team plan", team_files, key="ath_team_plan_select")
                        st.json(load_plan(team_folder, sel))
                    else:
                        st.info("No team plans available yet for this team.")

        elif athlete_tab == "Fixtures":
            st.subheader("📆 Fixtures")
            fixtures = data.get("fixtures", [])
            fdate = st.date_input("Fixture date", value=datetime.date.today(), key="fix_date")
            opp = st.text_input("Opponent", key="fix_opp")
            venue = st.text_input("Venue", key="fix_venue")
            if st.button("Add Fixture"):
                fixtures.append({"date": fdate.strftime("%Y-%m-%d"), "opponent": opp, "venue": venue})
                data["fixtures"] = fixtures
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Fixture added.")
            if fixtures:
                df = pd.DataFrame(fixtures)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date", ascending=False)
                st.dataframe(df, use_container_width=True)

        elif athlete_tab == "Homework / Study":
            st.subheader("📚 Homework / Study")
            slog = data.get("study_log", [])
            sdate = st.date_input("Date", value=datetime.date.today(), key="study_date")
            subject = st.text_input("Subject", key="study_subject")
            mins = st.number_input("Minutes", min_value=0, max_value=600, value=30, key="study_mins")
            snote = st.text_area("What did you do?", key="study_notes")
            if st.button("Add Study Entry"):
                slog.append({"date": sdate.strftime("%Y-%m-%d"), "subject": subject, "minutes": int(mins), "notes": snote})
                data["study_log"] = slog
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Study entry added.")
            if slog:
                df = pd.DataFrame(slog)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date", ascending=False)
                st.dataframe(df, use_container_width=True)

        elif athlete_tab == "Mental Wellbeing":
            st.subheader("🧠 Mental Wellbeing")
            wlog = data.get("wellbeing_log", [])
            wdate = st.date_input("Date", value=datetime.date.today(), key="wb_date")
            mood = st.selectbox("Mood", ["😀 Great", "🙂 Good", "😐 Ok", "😟 Low", "😢 Struggling"], key="wb_mood")
            stress = st.slider("Stress level (1-10)", 1, 10, 5, key="wb_stress")
            band, desc = stress_label(int(stress))
            st.info(f"Current selection: **{stress}/10** — **{band}** ({desc})")
            wnote = st.text_area("Notes", key="wb_notes")
            if st.button("Add Wellbeing Entry"):
                wlog.append({"date": wdate.strftime("%Y-%m-%d"), "mood": mood, "stress": int(stress), "notes": wnote})
                data["wellbeing_log"] = wlog
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Wellbeing entry added.")
            if wlog:
                df = pd.DataFrame(wlog)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date", ascending=False)
                st.dataframe(df, use_container_width=True)

        elif athlete_tab == "Teams & Coach Codes":
            st.subheader("👥 Teams & Coach Codes")
            teams = data.get("teams", [])
            st.write("Your Teams:", teams if teams else "None")

            join_code = st.text_input("Enter Team Code to Join", key="join_team_code")
            if st.button("Join Team"):
                join_code = (join_code or "").strip().upper()
                teams_data = load_teams()
                if join_code not in teams_data:
                    st.error("Team code not found.")
                else:
                    if join_code not in teams:
                        teams.append(join_code)
                        data["teams"] = teams
                        save_athlete(u, data)
                        st.session_state["athlete_data"] = data
                        st.success(f"Joined team {join_code}.")
                    else:
                        st.info("Already joined that team.")

        elif athlete_tab == "Chat / CoachBot":
            st.subheader("💬 Chat / CoachBot")
            st.info("Placeholder chat area.")
            st.text_area("Message", key="chat_msg")
            st.button("Send")

        elif athlete_tab == "Recovery Advice":
            st.subheader("🧊 Recovery Advice")
            st.write("- Sleep 8-10 hours\n- Hydration\n- Balanced meals\n- Light recovery session\n- Stretching & mobility")

        elif athlete_tab == "Account / Family Info":
            st.subheader("👨‍👩‍👧 Account / Family Info")
            fam = data.get("family_info", {})
            fam["parent_name"] = st.text_input("Parent/Guardian Name", value=fam.get("parent_name", ""))
            fam["parent_email"] = st.text_input("Parent/Guardian Email", value=fam.get("parent_email", ""))
            fam["phone"] = st.text_input("Phone", value=fam.get("phone", ""))
            fam["notes"] = st.text_area("Notes", value=fam.get("notes", ""))

            if st.button("Save Family Info"):
                data["family_info"] = fam
                save_athlete(u, data)
                st.session_state["athlete_data"] = data
                st.success("Saved.")

            st.write("---")
            st.write("### Family Dashboard Code (optional)")
            code = st.text_input("Create / use a family code to share with parent/guardian", key="fam_code_input")
            if st.button("Link Code"):
                if not code:
                    st.error("Enter a code.")
                else:
                    # Save in BOTH systems for max compatibility:
                    link_family_code_to_athlete(code, u)        # single-child
                    add_child_to_family(code, u)               # multi-child calendar
                    st.success("Code linked. Parent/guardian can use this in Parent / Guardian mode.")

        st.write("---")
        if st.button("Log Out"):
            st.session_state["athlete_logged_in"] = False
            st.session_state["athlete_user"] = ""
            st.session_state["athlete_data"] = None
            st.success("Logged out.")

# -----------------------------
# Coach Dashboard
# -----------------------------
if mode == "Coach Dashboard":
    st.header("🎓 Coach Dashboard")

    if not st.session_state.get("coach_logged_in", False):
        st.subheader("Coach Login (PIN required)")
        cu_raw = st.text_input("Coach username", key="coach_login_user")
        cu = clean_username(cu_raw)
        cp = st.text_input("Coach PIN", type="password", key="coach_login_pin")
        if st.button("Log In", key="coach_login_btn"):
            if check_coach(cu, cp):
                st.session_state["coach_logged_in"] = True
                st.session_state["coach_user"] = cu
                st.success("Logged in.")
            else:
                st.error("Invalid coach username or PIN.")
        st.info("If you don't have a coach account yet, create one in **Admin / Settings**.")
    else:
        coach_user = st.session_state.get("coach_user", "Coach")
        st.success(f"Welcome {coach_user}")

        coach_tab = st.radio(
            "Select Feature",
            ["Team Overview", "Create/Assign Training Plans", "View Athlete Logs (by username)"],
        )

        if coach_tab == "Team Overview":
            st.subheader("Create a Team Code")
            team_name = st.text_input("Team name (e.g. 'U16A Football')", key="coach_team_name")
            if st.button("Create Team Code", key="coach_create_team_btn"):
                if not team_name:
                    st.error("Please enter a team name.")
                else:
                    teams = load_teams()
                    code = generate_team_code()
                    while code in teams:
                        code = generate_team_code()
                    teams[code] = {"team_name": team_name, "created": datetime.datetime.now().isoformat()}
                    save_teams(teams)
                    st.success(f"Team created! Code: **{code}** (share with athletes)")

            st.write("---")
            st.subheader("Existing Teams")
            teams = load_teams()
            if teams:
                for code, info in teams.items():
                    st.write(f"**{code}** — {info.get('team_name','')}")
            else:
                st.info("No teams created yet.")

        elif coach_tab == "Create/Assign Training Plans":
            st.subheader("📋 Create a Training Plan (Team)")
            teams = load_teams()
            if not teams:
                st.info("Create a team first in Team Overview.")
            else:
                team_code = st.selectbox("Select Team Code", list(teams.keys()), key="coach_plan_team")
                plan_name = st.text_input("Plan name", key="coach_plan_name")
                plan_text = st.text_area("Plan content", key="coach_plan_text")
                if st.button("Save Team Plan", key="coach_save_team_plan"):
                    if not plan_name:
                        st.error("Enter a plan name.")
                    else:
                        folder = plans_folder_for_team(team_code)
                        save_plan(folder, plan_name, {"name": plan_name, "content": plan_text, "team_code": team_code})
                        st.success("Plan saved to team.")

                st.write("---")
                st.subheader("Existing Team Plans")
                folder = plans_folder_for_team(team_code)
                files = list_plan_files(folder)
                if files:
                    sel = st.selectbox("Select a plan to view", files, key="coach_view_team_plan")
                    st.json(load_plan(folder, sel))
                else:
                    st.info("No plans saved yet.")

        elif coach_tab == "View Athlete Logs (by username)":
            st.subheader("🔎 View Athlete Logs")
            athlete_username = st.text_input("Athlete username", key="coach_view_athlete_user")
            if st.button("Load Athlete"):
                au = clean_username(athlete_username)
                file = athlete_file(au)
                legacy = os.path.join(ATHLETES_DIR, (athlete_username or "").strip() + ".json")
                if not os.path.exists(file) and os.path.exists(legacy):
                    file = legacy
                if not os.path.exists(file):
                    st.error("Athlete not found.")
                else:
                    ad = load_json(file, {})
                    st.success(f"Loaded athlete: {au}")
                    st.write("### 🏋️ Training Log Detail")
                    st.dataframe(pd.DataFrame(ad.get("training_log", [])), use_container_width=True)
                    st.write("### 🏋️ Gym/Cardio Detail")
                    st.dataframe(pd.DataFrame(ad.get("gym_log", [])), use_container_width=True)
                    st.write("### 🧠 Wellbeing Detail")
                    st.dataframe(pd.DataFrame(ad.get("wellbeing_log", [])), use_container_width=True)
                    st.write("### 📚 Homework / Study Detail")
                    st.dataframe(pd.DataFrame(ad.get("study_log", [])), use_container_width=True)

        st.write("---")
        if st.button("Log Out (Coach)", key="coach_logout"):
            st.session_state["coach_logged_in"] = False
            st.session_state["coach_user"] = ""
            st.success("Logged out.")

# -----------------------------
# Parent / Guardian (✅ Calendar restored)
# -----------------------------
if mode == "Parent / Guardian":
    st.header("👨‍👩‍👧 Parent / Guardian Dashboard")
    st.write("Enter the family code given by the athlete.")

    code = st.text_input("Family Code", key="parent_code")

    if st.button("Open Dashboard"):
        st.session_state["parent_code_active"] = (code or "").strip()

    active_code = st.session_state.get("parent_code_active", "").strip()

    if not active_code:
        st.info("Enter a valid family code above to view the dashboard.")
    else:
        # 1) Try multi-child families first
        families = load_families()
        children = []
        family_name = "Family"

        if active_code in families:
            family = families.get(active_code, {})
            family_name = family.get("family_name", "Family")
            children = family.get("children", [])  # list of {username,color}
        else:
            # 2) Fallback to single-child code mapping
            single_user = get_athlete_for_family_code(active_code)
            if single_user:
                children = [{"username": clean_username(single_user), "color": ATHLETE_COLORS[0]}]

        if not children:
            st.error("Family code not found. Please check and try again.")
        else:
            tab1, tab2 = st.tabs(["Dashboard", "Family Weekly & Monthly Calendar"])

            # ---------------- Dashboard (kept simple)
            with tab1:
                # If multiple kids, choose one for the standard dashboard view
                if len(children) > 1:
                    pick = st.selectbox("Select athlete", [c["username"] for c in children], key="parent_pick_child")
                    child_obj = next((c for c in children if c["username"] == pick), children[0])
                else:
                    child_obj = children[0]

                athlete_user = clean_username(child_obj["username"])
                file = athlete_file(athlete_user)

                if not os.path.exists(file):
                    st.error("Linked athlete profile not found.")
                else:
                    ad = load_json(file, {})
                    st.success(f"{family_name} — dashboard for athlete: **{athlete_user}**")

                    tlog = ad.get("training_log", [])
                    glog = ad.get("gym_log", [])
                    wlog = ad.get("wellbeing_log", [])
                    slog = ad.get("study_log", [])

                    st.write("### Weekly Summary")
                    st.metric("Training minutes (this week)", compute_weekly_summary(tlog, "minutes"))
                    st.metric("Gym/Cardio minutes (this week)", compute_weekly_summary(glog, "minutes"))
                    st.metric("Study minutes (this week)", compute_weekly_summary(slog, "minutes"))

                    st.write("---")
                    st.write("### Recent Entries")
                    if tlog:
                        df = pd.DataFrame(tlog)
                        df["date"] = pd.to_datetime(df["date"], errors="coerce")
                        df = df.dropna(subset=["date"]).sort_values("date", ascending=False).head(10)
                        st.write("**Training**")
                        st.dataframe(df, use_container_width=True)
                    if glog:
                        df = pd.DataFrame(glog)
                        df["date"] = pd.to_datetime(df["date"], errors="coerce")
                        df = df.dropna(subset=["date"]).sort_values("date", ascending=False).head(10)
                        st.write("**Gym/Cardio**")
                        st.dataframe(df, use_container_width=True)
                    if wlog:
                        df = pd.DataFrame(wlog)
                        df["date"] = pd.to_datetime(df["date"], errors="coerce")
                        df = df.dropna(subset=["date"]).sort_values("date", ascending=False).head(10)
                        st.write("**Wellbeing**")
                        st.dataframe(df, use_container_width=True)
                    if slog:
                        df = pd.DataFrame(slog)
                        df["date"] = pd.to_datetime(df["date"], errors="coerce")
                        df = df.dropna(subset=["date"]).sort_values("date", ascending=False).head(10)
                        st.write("**Study**")
                        st.dataframe(df, use_container_width=True)

            # ---------------- Family Weekly & Monthly Calendar (RESTORED)
            with tab2:
                st.subheader("Family View")
                st.caption("Weekly view shows training minutes per day; monthly view shows total training minutes per day.")

                today = datetime.date.today()
                current_week = today.isocalendar()[1]
                current_year = today.year

                # --- Collect training log entries for all children
                weekly_rows = []
                monthly_totals = {}   # date -> total minutes
                per_child_weekly = {} # child -> weekly total minutes

                for child in children:
                    username = clean_username(child.get("username"))
                    per_child_weekly.setdefault(username, 0)

                    afile = athlete_file(username)
                    if not os.path.exists(afile):
                        continue
                    ad = load_json(afile, {})
                    tlog = ad.get("training_log", [])

                    for e in tlog:
                        try:
                            d = datetime.datetime.strptime(e.get("date", ""), "%Y-%m-%d").date()
                        except Exception:
                            continue

                        mins = int(e.get("minutes", 0))

                        # weekly
                        if d.year == current_year and d.isocalendar()[1] == current_week:
                            weekly_rows.append(
                                {
                                    "Date": d,
                                    "Athlete": username,
                                    "Minutes": mins,
                                    "Type": e.get("type", ""),
                                    "Notes": e.get("notes", ""),
                                }
                            )
                            per_child_weekly[username] += mins

                        # monthly (current month)
                        if d.year == today.year and d.month == today.month:
                            monthly_totals[d] = monthly_totals.get(d, 0) + mins

                # Weekly table + totals
                if weekly_rows:
                    wdf = pd.DataFrame(weekly_rows)
                    wdf["Date"] = pd.to_datetime(wdf["Date"])
                    wdf = wdf.sort_values("Date", ascending=True)
                    st.write("### Weekly Calendar (Training)")
                    st.dataframe(wdf, use_container_width=True)

                    st.write("### Weekly Totals (Training Minutes)")
                    totals_df = pd.DataFrame(
                        [{"Athlete": k, "Minutes": v} for k, v in sorted(per_child_weekly.items(), key=lambda x: x[0])]
                    )
                    st.dataframe(totals_df, use_container_width=True)
                else:
                    st.info("No training entries found for the current week.")

                st.write("---")

                # Monthly view as a calendar-like grid (text)
                st.write(f"### Monthly Calendar — {today.strftime('%B %Y')}")
                first_day = datetime.date(today.year, today.month, 1)
                last_day_num = cal_mod.monthrange(today.year, today.month)[1]
                last_day = datetime.date(today.year, today.month, last_day_num)

                # Build a simple day-by-day table for the month
                month_rows = []
                d = first_day
                while d <= last_day:
                    month_rows.append(
                        {
                            "Date": d,
                            "Day": d.strftime("%a"),
                            "Training Minutes": monthly_totals.get(d, 0),
                        }
                    )
                    d += datetime.timedelta(days=1)

                mdf = pd.DataFrame(month_rows)
                mdf["Date"] = pd.to_datetime(mdf["Date"])
                st.dataframe(mdf, use_container_width=True)

# -----------------------------
# Admin / Settings
# -----------------------------
if mode == "Admin / Settings":
    st.header("⚙️ Admin Settings")

    st.subheader("(Optional) Coach Registration")
    cu = st.text_input("Coach username")
    cp = st.text_input("Coach PIN", type="password")
    if st.button("Register Coach"):
        ok, msg = register_coach(cu, cp)
        st.success(msg) if ok else st.error(msg)

    st.write("---")
    st.subheader("Debug: List Saved Athletes")
    if st.button("Show athlete files"):
        files = sorted([f for f in os.listdir(ATHLETES_DIR) if f.lower().endswith(".json")])
        st.info("No athlete files found.") if not files else st.write(files)
