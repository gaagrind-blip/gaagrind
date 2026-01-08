import streamlit as st
import json, os, datetime, calendar
import pandas as pd
import random
import string

# -----------------------------
# File/Folder Setup
# -----------------------------
DATA_DIR = "data"
ATHLETES_DIR = os.path.join(DATA_DIR, "athletes")
TEAMS_FILE = os.path.join(DATA_DIR, "teams.json")
FAMILIES_FILE = os.path.join(DATA_DIR, "families.json")
FAMILY_LINKS_FILE = os.path.join(DATA_DIR, "family_links.json")
TRAINING_PLANS_DIR = os.path.join(DATA_DIR, "training_plans")

# Coach Staffroom forum file (your original feature)
COACH_FORUM_FILE = os.path.join(DATA_DIR, "coach_forum.json")

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
    """Normalise usernames so Register/Login always match saved profiles."""
    raw = (raw or "").strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    cleaned = "".join(ch for ch in raw if ch in allowed)
    return cleaned.lower()

def athlete_file(username: str) -> str:
    return os.path.join(ATHLETES_DIR, clean_username(username) + ".json")

def generate_share_code(length=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

# -----------------------------
# Coach staffroom helpers
# -----------------------------
def load_forum():
    return load_json(COACH_FORUM_FILE, {"messages": []})

def save_forum(forum):
    save_json(COACH_FORUM_FILE, forum)

# -----------------------------
# Training plan helpers
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
def load_teams():
    return load_json(TEAMS_FILE, {})

def save_teams(teams):
    save_json(TEAMS_FILE, teams)

def generate_team_code(length=6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))

# -----------------------------
# Families helpers
# -----------------------------
def load_families():
    return load_json(FAMILIES_FILE, {})

def save_families(families):
    save_json(FAMILIES_FILE, families)

def load_family_links():
    return load_json(FAMILY_LINKS_FILE, {})

def save_family_links(links):
    save_json(FAMILY_LINKS_FILE, links)

def link_family_code_to_athlete(code: str, athlete_username: str):
    links = load_family_links()
    links[(code or "").strip()] = clean_username(athlete_username)
    save_family_links(links)

def get_athlete_for_family_code(code: str):
    links = load_family_links()
    return links.get((code or "").strip())

# -----------------------------
# Login Functions (patched for reliable saving)
# -----------------------------
def save_athlete(u, data):
    # Always save under canonical username filename
    u_clean = clean_username(u)
    if isinstance(data, dict):
        data.setdefault("username", u_clean)
    save_json(athlete_file(u_clean), data)

def check_athlete_login(u, p):
    u_clean = clean_username(u)
    file = athlete_file(u_clean)

    # Legacy fallback (older versions saved raw-typed usernames)
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
st.set_page_config(
    page_title="Performance Pulse",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Design (your original styling)
st.markdown(
    """
<style>
/* App background */
[data-testid="stAppViewContainer"] {
    background-color: #f0f5f0;
}

/* Sidebar background */
[data-testid="stSidebar"] {
    background-color: #213c29;
}

[data-testid="stSidebar"] * {
    color: white !important;
}

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

# Session State Initiation
if "athlete_logged_in" not in st.session_state:
    st.session_state["athlete_logged_in"] = False
    st.session_state["athlete_user"] = ""
    st.session_state["athlete_data"] = None

if "coach_logged_in" not in st.session_state:
    st.session_state["coach_logged_in"] = False
    st.session_state["coach_user"] = ""

if "family_dashboard_code" not in st.session_state:
    st.session_state["family_dashboard_code"] = ""

# -----------------------------
# ATHLETE PORTAL
# -----------------------------
if mode == "Athlete Portal":
    st.header("🏋️ Athlete Portal")

    athlete_tab = st.radio("Select:", ["Register", "Login", "Athlete Home"])

    # Register
    if athlete_tab == "Register":
        st.subheader("New Athlete Registration")
        new_user = clean_username(st.text_input("Username", key="reg_user"))
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
                        "gym_sessions": [],
                        "diet_log": [],
                        "fixtures": [],
                        "study_log": [],
                        "wellbeing_log": [],
                        "teams": [],
                    },
                )
                st.success(f"Athlete {new_user} registered! You can now log in.")

    # Login
    elif athlete_tab == "Login" and not st.session_state["athlete_logged_in"]:
        st.subheader("Athlete Login")
        u = clean_username(st.text_input("Username", key="login_user"))
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

    # Athlete Home
    elif athlete_tab == "Athlete Home":
        if not st.session_state["athlete_logged_in"]:
            st.info("Please log in first.")
        else:
            u = st.session_state["athlete_user"]
            data = st.session_state["athlete_data"]

            st.subheader(f"Welcome, {u}")

            inner_tab = st.radio(
                "Select:",
                [
                    "Training Log",
                    "Gym Sessions",
                    "Diet Log",
                    "Fixtures",
                    "Homework / Study",
                    "Mental Wellbeing",
                    "Training Plans",
                    "Teams",
                    "Account / Family Code",
                ],
            )

            if inner_tab == "Training Log":
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
                if logs:
                    df = pd.DataFrame(logs)
                    st.dataframe(df, use_container_width=True)

            elif inner_tab == "Gym Sessions":
                st.subheader("🏋️ Log Gym Session")
                gym = data.get("gym_sessions", [])
                g_date = st.date_input("Date", datetime.date.today(), key="gym_date")
                g_minutes = st.number_input("Minutes", 0, 300, key="gym_minutes")
                g_desc = st.text_input("What did you do?", key="gym_desc")
                if st.button("Add Gym Session"):
                    gym.append({"date": str(g_date), "minutes": int(g_minutes), "desc": g_desc})
                    data["gym_sessions"] = gym
                    save_athlete(u, data)
                    st.session_state["athlete_data"] = data
                    st.success("Gym session saved!")

                st.markdown("---")
                if gym:
                    st.dataframe(pd.DataFrame(gym), use_container_width=True)

            elif inner_tab == "Diet Log":
                st.subheader("🥗 Diet Log")
                diet = data.get("diet_log", [])
                d_date = st.date_input("Date", datetime.date.today(), key="diet_date")
                meal = st.selectbox("Meal", ["Breakfast", "Lunch", "Dinner", "Snack"])
                notes = st.text_area("What did you eat?")
                if st.button("Save Diet Entry"):
                    diet.append({"date": str(d_date), "meal": meal, "notes": notes})
                    data["diet_log"] = diet
                    save_athlete(u, data)
                    st.session_state["athlete_data"] = data
                    st.success("Diet saved!")
                if diet:
                    st.dataframe(pd.DataFrame(diet), use_container_width=True)

            elif inner_tab == "Fixtures":
                st.subheader("📆 Fixtures")
                fixtures = data.get("fixtures", [])
                f_date = st.date_input("Fixture date", datetime.date.today(), key="fix_date")
                opp = st.text_input("Opponent", key="fix_opp")
                venue = st.text_input("Venue", key="fix_venue")
                if st.button("Add Fixture"):
                    fixtures.append({"date": str(f_date), "opponent": opp, "venue": venue})
                    data["fixtures"] = fixtures
                    save_athlete(u, data)
                    st.session_state["athlete_data"] = data
                    st.success("Fixture added.")
                if fixtures:
                    st.dataframe(pd.DataFrame(fixtures), use_container_width=True)

            elif inner_tab == "Homework / Study":
                st.subheader("📚 Homework / Study")
                study = data.get("study_log", [])
                s_date = st.date_input("Date", datetime.date.today(), key="study_date")
                subject = st.text_input("Subject")
                mins = st.number_input("Minutes", 0, 600, 30)
                notes = st.text_area("What did you do?")
                if st.button("Add Study Entry"):
                    study.append({"date": str(s_date), "subject": subject, "minutes": int(mins), "notes": notes})
                    data["study_log"] = study
                    save_athlete(u, data)
                    st.session_state["athlete_data"] = data
                    st.success("Study entry added.")
                if study:
                    st.dataframe(pd.DataFrame(study), use_container_width=True)

            elif inner_tab == "Mental Wellbeing":
                st.subheader("🧠 Daily Wellbeing Check-In")
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
                            "mood": int(mood),
                            "stress": int(stress),
                            "sleep": float(sleep_hours),
                            "notes": wb_notes,
                        }
                    )
                    data["wellbeing_log"] = wellbeing_log
                    save_athlete(u, data)
                    st.session_state["athlete_data"] = data
                    st.success("Check-in saved!")

                st.markdown("---")
                if wellbeing_log:
                    df = pd.DataFrame(wellbeing_log)
                    st.dataframe(df, use_container_width=True)

                    last_7 = wellbeing_log[-7:]
                    avg_mood = sum([x.get("mood", 0) for x in last_7]) / max(len(last_7), 1)
                    avg_stress = sum([x.get("stress", 0) for x in last_7]) / max(len(last_7), 1)
                    avg_sleep = sum([x.get("sleep", 0) for x in last_7]) / max(len(last_7), 1)

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

            elif inner_tab == "Training Plans":
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
                        st.info("Join a team to access team plans.")
                    else:
                        team_code = st.selectbox("Select team", teams, key="ath_team_select")
                        team_folder = plans_folder_for_team(team_code)
                        team_files = list_plan_files(team_folder)
                        if team_files:
                            sel = st.selectbox("Select a team plan", team_files, key="ath_team_plan_select")
                            st.json(load_plan(team_folder, sel))
                        else:
                            st.info("No team plans available yet for this team.")

            elif inner_tab == "Teams":
                st.subheader("👥 Teams")
                teams = data.get("teams", [])
                st.write("Your teams:", teams if teams else "None")
                join_code = st.text_input("Enter Team Code to Join")
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

            elif inner_tab == "Account / Family Code":
                st.subheader("👨‍👩‍👦 Family Code (for Parent Dashboard)")
                code = st.text_input("Create / use a family code to share with parent/guardian")
                if st.button("Link Code to Me"):
                    if not code:
                        st.error("Enter a code.")
                    else:
                        link_family_code_to_athlete(code, u)
                        # also add into families system if it exists
                        families = load_families()
                        fam = families.get(code, {"family_name": "Family", "children": []})
                        existing = [c.get("username") for c in fam.get("children", [])]
                        if u not in existing:
                            fam.setdefault("children", []).append({"username": u, "color": data.get("color", ATHLETE_COLORS[0])})
                        families[code] = fam
                        save_families(families)
                        st.success("Code linked. Parent/guardian can use this in Parent / Guardian mode.")

            st.markdown("---")
            if st.button("Log Out"):
                st.session_state["athlete_logged_in"] = False
                st.session_state["athlete_user"] = ""
                st.session_state["athlete_data"] = None
                st.success("Logged out.")

# -----------------------------
# COACH DASHBOARD (includes Coach Staffroom again)
# -----------------------------
elif mode == "Coach Dashboard":
    st.header("🎓 Coach Dashboard")

    if not st.session_state.get("coach_logged_in", False):
        st.subheader("Coach Login")
        cu = clean_username(st.text_input("Coach username", key="coach_login_user"))
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
            [
                "Team Overview",
                "Create/Assign Training Plans",
                "View Athlete Logs (by username)",
                "Coach Staffroom",
            ],
        )

        if coach_tab == "Team Overview":
            st.subheader("Create a Team Code")
            team_name = st.text_input("Team name (e.g. 'U16A Football')")
            if st.button("Create Team Code"):
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

            st.markdown("---")
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
                team_code = st.selectbox("Select Team Code", list(teams.keys()))
                plan_name = st.text_input("Plan name")
                plan_text = st.text_area("Plan content")
                if st.button("Save Team Plan"):
                    if not plan_name:
                        st.error("Enter a plan name.")
                    else:
                        folder = plans_folder_for_team(team_code)
                        save_plan(folder, plan_name, {"name": plan_name, "content": plan_text, "team_code": team_code})
                        st.success("Plan saved to team.")

                st.markdown("---")
                st.subheader("Existing Team Plans")
                folder = plans_folder_for_team(team_code)
                files = list_plan_files(folder)
                if files:
                    sel = st.selectbox("Select a plan to view", files)
                    st.json(load_plan(folder, sel))
                else:
                    st.info("No plans saved yet.")

        elif coach_tab == "View Athlete Logs (by username)":
            st.subheader("🔎 View Athlete Logs")
            athlete_username = st.text_input("Athlete username")
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
                    st.write("### Training Log")
                    st.dataframe(pd.DataFrame(ad.get("training_log", [])), use_container_width=True)
                    st.write("### Gym Sessions")
                    st.dataframe(pd.DataFrame(ad.get("gym_sessions", [])), use_container_width=True)
                    st.write("### Wellbeing Log")
                    st.dataframe(pd.DataFrame(ad.get("wellbeing_log", [])), use_container_width=True)
                    st.write("### Study Log")
                    st.dataframe(pd.DataFrame(ad.get("study_log", [])), use_container_width=True)

        elif coach_tab == "Coach Staffroom":
            st.subheader("☕ Coach Staffroom")
            forum = load_forum()
            messages = forum.get("messages", [])

            st.write("Post updates, reminders, or notes for other coaches.")
            msg = st.text_area("Message")
            if st.button("Post Message"):
                if msg.strip():
                    messages.append(
                        {
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "coach": coach_user,
                            "message": msg.strip(),
                        }
                    )
                    forum["messages"] = messages
                    save_forum(forum)
                    st.success("Posted!")
                else:
                    st.error("Type a message first.")

            st.markdown("---")
            if messages:
                for m in reversed(messages[-30:]):
                    st.markdown(f"**{m.get('coach','Coach')}** — {m.get('timestamp','')}")
                    st.write(m.get("message", ""))
                    st.markdown("---")
            else:
                st.info("No messages yet.")

        st.markdown("---")
        if st.button("Log Out (Coach)"):
            st.session_state["coach_logged_in"] = False
            st.session_state["coach_user"] = ""
            st.success("Logged out.")

# -----------------------------
# PARENT + GUARDIAN DASHBOARD (month selector restored)
# -----------------------------
elif mode == "Parent / Guardian":
    st.header("👨‍👩‍👦 Parent / Guardian Dashboard")

    parent_tab = st.radio(
        "Select:",
        ["Create / Manage Family", "Family Weekly & Monthly Calendar"],
    )

    families = load_families()

    if parent_tab == "Create / Manage Family":
        st.subheader("Create a Family Code")
        family_name = st.text_input("Family name (e.g. 'Murphy Family')")

        if st.button("Create Family Code"):
            if not family_name:
                st.error("Please enter a family name.")
            else:
                code = generate_share_code()
                while code in families:
                    code = generate_share_code()
                families[code] = {"family_name": family_name, "children": []}
                save_families(families)
                st.success(f"Family created! Code: **{code}**")

        st.markdown("---")
        st.subheader("Load Family Code")
        code = st.text_input("Enter your family code")
        if st.button("Load Family"):
            if code not in families:
                # fallback to single-child system
                single_user = get_athlete_for_family_code(code)
                if single_user:
                    st.session_state["family_dashboard_code"] = code
                    if code not in families:
                        families[code] = {"family_name": "Family", "children": [{"username": single_user, "color": ATHLETE_COLORS[0]}]}
                        save_families(families)
                    st.success("Loaded (single athlete code).")
                else:
                    st.error("Code not found.")
            else:
                st.session_state["family_dashboard_code"] = code
                family = families[code]
                st.success(f"Loaded family: **{family.get('family_name', 'Family')}**")

        if st.session_state["family_dashboard_code"]:
            code = st.session_state["family_dashboard_code"]
            families = load_families()
            family = families.get(code, {})
            st.markdown("---")
            st.subheader(f"Manage Family: {family.get('family_name','Family')} (Code: {code})")

            children = family.get("children", [])

            st.write("Current linked athletes:")
            if children:
                for c in children:
                    st.write(f"- {c.get('username')}")
            else:
                st.info("No athletes linked yet.")

            st.markdown("### Add an athlete")
            username = st.text_input("Athlete username to add")
            if st.button("Add Athlete"):
                if not username:
                    st.error("Enter a username.")
                else:
                    username = clean_username(username)
                    if not os.path.exists(athlete_file(username)):
                        st.error("That athlete profile doesn't exist yet.")
                    else:
                        # avoid duplicates
                        existing = [c.get("username") for c in children]
                        if username in existing:
                            st.info("Already linked.")
                        else:
                            # assign a color
                            used = {c.get("color") for c in children}
                            col = next((x for x in ATHLETE_COLORS if x not in used), random.choice(ATHLETE_COLORS))
                            children.append({"username": username, "color": col})
                            family["children"] = children
                            families[code] = family
                            save_families(families)
                            st.success("Added!")

    else:
        st.subheader("Family Weekly & Monthly Calendar")

        code = st.session_state.get("family_dashboard_code", "")
        if not code:
            st.info("Load a family code first in 'Create / Manage Family'.")
        else:
            families = load_families()
            family = families.get(code, {})
            children = family.get("children", [])

            if not children:
                st.info("No athletes linked to this family yet.")
            else:
                today = datetime.date.today()
                current_week = today.isocalendar()[1]
                current_year = today.year

                family_calendar_rows = []
                per_child_weekly = {}
                training_by_day = {}

                for child in children:
                    username = clean_username(child.get("username"))
                    color = child.get("color", ATHLETE_COLORS[0])
                    afile = athlete_file(username)
                    if not os.path.exists(afile):
                        continue

                    adata = load_json(afile, {})
                    logs = adata.get("training_log", [])
                    gym = adata.get("gym_sessions", [])
                    combined = logs + gym

                    per_child_weekly.setdefault(username, 0)

                    for entry in combined:
                        try:
                            d = datetime.datetime.strptime(entry.get("date", ""), "%Y-%m-%d").date()
                        except Exception:
                            try:
                                d = datetime.datetime.strptime(entry.get("date", ""), "%Y-%m-%d %H:%M:%S").date()
                            except Exception:
                                continue

                        mins = int(entry.get("minutes", 0))
                        desc = entry.get("desc", entry.get("notes", ""))

                        if d.isocalendar()[1] == current_week and d.year == current_year:
                            family_calendar_rows.append(
                                {"Date": d, "Athlete": username, "Minutes": mins, "Notes": desc}
                            )
                            per_child_weekly[username] += mins

                        # monthly view mapping (we’ll filter later by selected month/year)
                        key = d
                        if key not in training_by_day:
                            training_by_day[key] = []
                        training_by_day[key].append((username, color))

                if family_calendar_rows:
                    cal_df = pd.DataFrame(family_calendar_rows)
                    cal_df["Date"] = pd.to_datetime(cal_df["Date"], errors="coerce")
                    cal_df = cal_df.dropna(subset=["Date"]).sort_values("Date", ascending=True)
                    st.write("### Weekly View (Current Week)")
                    st.dataframe(cal_df, use_container_width=True)
                else:
                    st.info("No training/gym entries found for the current week.")

                st.markdown("---")
                st.write("### Weekly Totals")
                cols = st.columns(3)
                for idx, child in enumerate(children):
                    username = clean_username(child.get("username"))
                    color = child.get("color", ATHLETE_COLORS[0])
                    minutes = per_child_weekly.get(username, 0)
                    with cols[idx % len(cols)]:
                        st.metric(label=f"{username} – min this week", value=minutes)
                        st.markdown(
                            f"<span style='color:{color}; font-size: 20px;'>●</span> Colour tag",
                            unsafe_allow_html=True,
                        )

                # ✅ Month selector added
                st.markdown("---")
                st.write("### 📆 Month View")

                month_names = ["January","February","March","April","May","June","July","August","September","October","November","December"]
                col_m1, col_m2 = st.columns([2, 1])
                with col_m1:
                    selected_month_name = st.selectbox("Month", month_names, index=today.month - 1, key="fam_cal_month")
                    month = month_names.index(selected_month_name) + 1
                with col_m2:
                    year = st.number_input("Year", min_value=2000, max_value=2100, value=today.year, step=1, key="fam_cal_year")

                cal = calendar.monthcalendar(int(year), int(month))

                html = "<table style='border-collapse: collapse; width: 100%;'>"
                html += "<tr>"
                for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                    html += "<th style='border: 1px solid #ced9ce; padding: 4px; text-align: center;'>" + day_name + "</th>"
                html += "</tr>"

                for week in cal:
                    html += "<tr>"
                    for day in week:
                        if day == 0:
                            html += "<td style='border: 1px solid #ced9ce; padding: 8px; height: 60px;'></td>"
                        else:
                            day_date = datetime.date(int(year), int(month), int(day))
                            dots = ""
                            if day_date in training_by_day:
                                for (uname, color) in training_by_day[day_date]:
                                    dots += f"<span title='{uname}' style='color:{color}; font-size:18px;'>●</span> "
                            html += "<td style='border: 1px solid #ced9ce; padding: 6px; vertical-align: top; height: 60px;'>"
                            html += f"<div style='font-weight:600; text-align:right;'>{day}</div>"
                            html += f"<div style='margin-top:4px; text-align:left;'>{dots}</div>"
                            html += "</td>"
                    html += "</tr>"

                html += "</table>"
                st.markdown(html, unsafe_allow_html=True)

# -----------------------------
# ADMIN / SETTINGS
# -----------------------------
elif mode == "Admin / Settings":
    st.header("⚙️ Admin Settings")

    st.subheader("Coach Registration")
    cu = st.text_input("Coach username")
    cp = st.text_input("Coach PIN", type="password")
    if st.button("Register Coach"):
        ok, msg = register_coach(cu, cp)
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    st.markdown("---")
    st.subheader("Debug: List Saved Athletes")
    if st.button("Show athlete files"):
        files = sorted([f for f in os.listdir(ATHLETES_DIR) if f.lower().endswith(".json")])
        if not files:
            st.info("No athlete files found.")
        else:
            st.write(files)
