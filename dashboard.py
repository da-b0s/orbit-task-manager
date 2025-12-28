import streamlit as st
import json
import os
import time
import random 
from datetime import datetime, date, timedelta
import google.generativeai as genai

# --- 1. ADMIN CONFIGURATION (SECURE) ---
try:
    ADMIN_API_KEY = st.secrets["GEMINI_API_KEY"]
except FileNotFoundError:
    st.error("🚨 API Key missing! Please create a .streamlit/secrets.toml file.")
    st.stop()
except KeyError:
    st.error("🚨 API Key missing! Check your secrets file for 'GEMINI_API_KEY'.")
    st.stop()

# --- 2. FILE SETUP ---
working_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(working_dir, "tasks.json")

# --- 3. LOAD/SAVE FUNCTIONS ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
            return data
        except:
            return {"profiles": {}}
    return {"profiles": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, default=str)

# --- 4. PAGE CONFIG ---
st.set_page_config(page_title="Orbit", layout="wide", page_icon="🪐")

# --- 5. STYLING ---
def apply_custom_styling():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #E0E0E0;
        }
        
        .stApp {
            background: #0E1117;
        }

        [data-testid="stSidebar"] {
            background-color: #161B22;
            border-right: 1px solid #30363D;
        }

        .stTextInput > div > div, 
        .stDateInput > div > div {
            background-color: #0D1117; 
            border: 1px solid #30363D; 
            border-radius: 6px;
            color: white;
        }
        
        div.stButton > button {
            background-color: #238636; 
            color: white;
            border: 1px solid rgba(240, 246, 252, 0.1); 
            border-radius: 6px; 
            padding: 5px 15px;
            font-weight: 500;
        }

        div.stButton > button:hover {
            background-color: #2EA043;
            border-color: #8B949E;
        }

        .stTabs [aria-selected="true"] {
            background-color: transparent !important;
            color: #58A6FF !important;
            border-bottom: 2px solid #58A6FF !important;
        }
        
        .briefing-card {
            background-color: #161B22;
            border: 1px solid #30363D;
            border-left: 4px solid #58A6FF; 
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 20px;
            font-size: 1.1em;
        }
        
        .fact-card {
            background-color: #161B22;
            border: 1px dashed #30363D;
            border-radius: 8px;
            padding: 15px;
            margin-top: 5px;
            color: #C9D1D9;
            font-style: italic;
        }
        
        h1, h2, h3 { color: #F0F6FC !important; }
        p, li { color: #C9D1D9 !important; line-height: 1.6; }
        strong { color: #58A6FF !important; }
        
        #MainMenu {visibility: hidden;} 
        footer {visibility: hidden;}
        header {background: transparent !important;}
        </style>
    """, unsafe_allow_html=True)

apply_custom_styling()

# --- 6. INITIALIZE STATE & AUTO-LOGIN ---
if 'db' not in st.session_state:
    st.session_state['db'] = load_data()

if 'current_user' not in st.session_state:
    if 'user' in st.query_params:
        st.session_state['current_user'] = st.query_params['user'].lower()
    else:
        st.session_state['current_user'] = None

if 'edit_target' not in st.session_state:
    st.session_state['edit_target'] = None 
if 'timer_active' not in st.session_state:
    st.session_state['timer_active'] = False
if 'timer_interest' not in st.session_state:
    st.session_state['timer_interest'] = None
if 'random_fact' not in st.session_state:
    st.session_state['random_fact'] = ""

# --- 7. HELPER FUNCTIONS ---
def get_user_data():
    user = st.session_state['current_user']
    if user and user in st.session_state['db']['profiles']:
        return st.session_state['db']['profiles'][user]
    return None

def update_interests():
    user_data = get_user_data()
    if user_data:
        user_data['interests_str'] = st.session_state['interests_input']
        save_data(st.session_state['db'])

def login_user():
    raw_input = st.session_state['login_name_input'].strip()
    username = raw_input.lower()
    
    if username:
        if "profiles" not in st.session_state['db']:
            st.session_state['db']['profiles'] = {}
        if username not in st.session_state['db']['profiles']:
            st.session_state['db']['profiles'][username] = {
                "interests_str": "Coding, Fitness",
                "tasks": {},
                "last_briefing_date": "",
                "daily_briefing": "",
                "onboarding_time": None
            }
            save_data(st.session_state['db'])
        
        st.session_state['current_user'] = username
        st.query_params["user"] = username
        check_and_run_briefing(username)

def logout():
    st.session_state['current_user'] = None
    st.session_state['timer_active'] = False
    st.session_state['random_fact'] = ""
    st.query_params.clear()

def format_due_date(date_str):
    if not date_str or date_str == "None":
        return None
    try:
        due_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()
        delta = (due_date - today).days
        if delta < 0: return f"⚠️ Overdue by {abs(delta)} days"
        elif delta == 0: return "🔥 Due Today!"
        elif delta == 1: return "🕒 Due Tomorrow"
        elif 1 < delta <= 7: return f"⏳ {delta} days left"
        else: return f"📅 {due_date.strftime('%b %d')}"
    except:
        return date_str

# --- THE EXECUTIVE BRAIN ---
def check_and_run_briefing(username):
    if username in st.session_state['db']['profiles']:
        user_data = st.session_state['db']['profiles'][username]
        today_str = str(date.today())
        last_date = user_data.get('last_briefing_date', "")
        
        # Scenario 1: Daily Cycle
        if last_date != "":
            if last_date != today_str:
                generate_daily_briefing(user_data, username, today_str)
                
        # Scenario 2: First Time (5-Minute Wait)
        else:
            onboarding_start = user_data.get('onboarding_time')
            if not onboarding_start:
                return 

            try:
                start_dt = datetime.strptime(onboarding_start, "%Y-%m-%d %H:%M:%S.%f")
                now = datetime.now()
                elapsed_minutes = (now - start_dt).total_seconds() / 60
                
                if elapsed_minutes >= 5:
                    generate_daily_briefing(user_data, username, today_str)
            except:
                pass

def generate_daily_briefing(user_data, username, today_str):
    if "PASTE_YOUR" in ADMIN_API_KEY:
        user_data['daily_briefing'] = "⚠️ **System Notice:** Admin API Key not configured."
        return

    all_tasks_text = ""
    task_count = 0
    for category, tasks in user_data['tasks'].items():
        if tasks:
            for t in tasks:
                if not t.get("done", False): 
                    task_count += 1
                    if isinstance(t, str): title = t; due = "None"
                    else: title = t['title']; due = t.get('due_date', 'None')
                    all_tasks_text += f"- {title} (Due: {due})\n"

    display_name = username.title()
    
    # EMPTY STATE (No AI)
    if task_count == 0:
        user_data['daily_briefing'] = f"👋 **Welcome, {display_name}!**<br><br>Your dashboard is currently empty. Add your first task below to start the 5-minute analysis timer!"
        save_data(st.session_state['db'])
        return

    # AI GENERATION
    prompt = f"""
    You are a personal assistant. The date is {today_str}. The user is {display_name}.
    
    User's Pending Tasks:
    {all_tasks_text}
    
    INSTRUCTIONS:
    1. Check if any tasks are due TODAY ({today_str}).
    2. Pick ONE "Priority Task" (most urgent or important).
    3. Write a short letter following this TONE/STRUCTURE:

    "Hello {display_name}, how are you feeling today?
    
    [If tasks are due today, list them: "Today you have to..."]. 
    [If NO tasks are due today, say: "You have no urgent deadlines today."]

    I would recommend you get to [Priority Task Name] because [Reason].

    Do have a lovely day"
    """

    try:
        genai.configure(api_key=ADMIN_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        user_data['daily_briefing'] = response.text
        user_data['last_briefing_date'] = today_str
        save_data(st.session_state['db'])
    except Exception as e:
        user_data['daily_briefing'] = f"❌ **Connection Error:** {str(e)}"

# --- RANDOM FACT (FUN & WITTY) ---
def generate_random_fact():
    user_data = get_user_data()
    
    if "PASTE_YOUR" in ADMIN_API_KEY:
        st.session_state['random_fact'] = "⚠️ System not configured."
        return

    interests_str = user_data.get('interests_str', "General")
    interests_list = [x.strip() for x in interests_str.split(',') if x.strip()]
    if not interests_list: interests_list = ["Science", "History", "Technology"]
    
    chosen_topic = random.choice(interests_list)
    
    try:
        genai.configure(api_key=ADMIN_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Tell me a mind-blowing, weird, or incredibly fun fact about {chosen_topic} that most people don't know.
        Make it witty and interesting, not boring or textbook-like.
        Do NOT mention the topic name explicitly in the sentence.
        Max 2 sentences.
        """
        
        response = model.generate_content(prompt)
        st.session_state['random_fact'] = response.text
    except Exception as e:
        st.session_state['random_fact'] = f"Error fetching fact: {str(e)}"

# --- TASK LOGIC ---
def add_task(interest):
    user_data = get_user_data()
    input_key = f"input_{interest}"
    date_key = f"date_{interest}"
    new_task_title = st.session_state[input_key]
    due_date = st.session_state[date_key]
    if new_task_title and user_data:
        if interest not in user_data['tasks']: user_data['tasks'][interest] = []
        task_obj = {"title": new_task_title, "due_date": str(due_date) if due_date else None, "done": False}
        user_data['tasks'][interest].append(task_obj)
        
        if not user_data.get('onboarding_time'):
            user_data['onboarding_time'] = str(datetime.now())
            
        save_data(st.session_state['db'])
        st.session_state[input_key] = "" 
        
        check_and_run_briefing(st.session_state['current_user'])

def enable_edit_mode(interest, index): 
    st.session_state['edit_target'] = (interest, index)

def save_edit(interest, index):
    user_data = get_user_data()
    new_text = st.session_state[f"edit_input_{interest}_{index}"]
    new_date = st.session_state[f"edit_date_{interest}_{index}"]
    if new_text and user_data:
        current_task = user_data['tasks'][interest][index]
        date_str = str(new_date) if new_date else None
        if isinstance(current_task, str): user_data['tasks'][interest][index] = {"title": new_text, "due_date": date_str, "done": False}
        else: user_data['tasks'][interest][index]["title"] = new_text; user_data['tasks'][interest][index]["due_date"] = date_str
        save_data(st.session_state['db'])
    st.session_state['edit_target'] = None 

def delete_task(interest, index):
    user_data = get_user_data()
    if user_data: del user_data['tasks'][interest][index]; save_data(st.session_state['db'])
    if st.session_state['edit_target'] == (interest, index): st.session_state['edit_target'] = None

def toggle_done(interest, index):
    user_data = get_user_data()
    if user_data:
        task = user_data['tasks'][interest][index]
        if isinstance(task, str): task = {"title": task, "due_date": None, "done": False}; user_data['tasks'][interest][index] = task
        user_data['tasks'][interest][index]["done"] = not task.get("done", False)
        save_data(st.session_state['db'])

# ==========================================
#        UI LAYOUT
# ==========================================

if st.session_state['current_user'] is None:
    # NAME HERE
    st.markdown("<div style='text-align: center; margin-top: 100px;'><h1 style='color: white;'>Orbit</h1><p style='color:#888;'>Your Tasks Revolve Around You</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.text_input("Username", key="login_name_input")
        if st.button("Login", use_container_width=True, on_click=login_user): st.rerun()
else:
    current_name = st.session_state['current_user']
    
    if current_name not in st.session_state['db']['profiles']:
        st.session_state['db']['profiles'][current_name] = {
            "interests_str": "Coding, Fitness",
            "tasks": {},
            "last_briefing_date": "",
            "daily_briefing": "",
            "onboarding_time": None
        }
    
    user_data = st.session_state['db']['profiles'][current_name]
    
    with st.sidebar:
        st.markdown(f"## {current_name.title()}")
        st.caption("Settings")
        st.text_area("Interests", value=user_data['interests_str'], key="interests_input", on_change=update_interests)
        st.markdown("---")
        if st.button("Log Out", on_click=logout): st.rerun()

    interests_list = [x.strip() for x in user_data['interests_str'].split(',') if x.strip()]
    
    # --- HOME TAB ---
    all_tabs = ["Home"] + interests_list
    tabs = st.tabs(all_tabs)
    
    with tabs[0]:
        st.markdown("### 📋 Daily Briefing")
        
        briefing_content = user_data.get('daily_briefing', "")
        
        # Display logic
        if not briefing_content:
            onboarding_start = user_data.get('onboarding_time')
            if onboarding_start:
                # UPDATED NAME HERE
                briefing_content = "⏳ **Analyzing...**<br>Orbit is reviewing your initial tasks. Your first briefing will arrive in a few minutes."
            else:
                briefing_content = f"👋 **Welcome, {current_name.title()}!**<br><br>Your dashboard is currently empty. Add your first task below to start."
        
        st.markdown(f"""<div class="briefing-card">{briefing_content}</div>""", unsafe_allow_html=True)
        
        st.write("")
        col_fact1, col_fact2 = st.columns([1, 4])
        with col_fact1:
            if st.button("🎲 Random Fact"):
                generate_random_fact()
        with col_fact2:
            if st.session_state['random_fact']:
                st.markdown(f"""<div class="fact-card">{st.session_state['random_fact']}</div>""", unsafe_allow_html=True)

    # --- INTEREST TABS ---
    for i, interest in enumerate(interests_list):
        with tabs[i+1]:
            st.subheader(f"{interest}")
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1: st.text_input(f"New task", key=f"input_{interest}", placeholder="Task name")
            with col2: st.date_input("Due", value=None, key=f"date_{interest}", label_visibility="hidden")
            with col3: st.write(""); st.button("Add", key=f"btn_{interest}", on_click=add_task, args=(interest,), use_container_width=True)
            
            st.write("---")
            current_tasks = user_data['tasks'].get(interest, [])
            if not current_tasks: st.caption("No tasks pending.")
            else:
                for idx, task_obj in enumerate(current_tasks):
                    if isinstance(task_obj, str): title = task_obj; due = None; is_done = False
                    else: title = task_obj["title"]; due = task_obj.get("due_date"); is_done = task_obj.get("done", False)
                    
                    if st.session_state['edit_target'] == (interest, idx):
                         c1, c2, c3 = st.columns([2,1,1])
                         with c1: st.text_input("Edit:", value=title, key=f"edit_input_{interest}_{idx}")
                         with c2: 
                             try: d = datetime.strptime(due, "%Y-%m-%d").date() if due else None
                             except: d = None
                             st.date_input("Date:", value=d, key=f"edit_date_{interest}_{idx}")
                         with c3: st.write(""); st.button("Save", key=f"s_{interest}_{idx}", on_click=save_edit, args=(interest, idx))
                    else:
                        c1, c2, c3, c4, c5 = st.columns([0.3, 4, 0.5, 0.5, 0.5])
                        with c1: st.checkbox("", value=is_done, key=f"c_{interest}_{idx}", on_change=toggle_done, args=(interest, idx))
                        with c2: 
                            st.markdown(f"**{'~~'+title+'~~' if is_done else title}**")
                            if due: 
                                smart_date = format_due_date(due)
                                st.caption(smart_date)
                        with c3:
                            if st.button("⏱️", key=f"t_{interest}_{idx}", help="Start Focus Timer"):
                                st.session_state['timer_task'] = title; st.session_state['timer_active'] = True; st.session_state['timer_interest'] = interest
                        with c4: 
                            st.button("✏️", key=f"e_{interest}_{idx}", on_click=enable_edit_mode, args=(interest, idx), help="Edit Task")
                        with c5: 
                            st.button("🗑️", key=f"d_{interest}_{idx}", on_click=delete_task, args=(interest, idx), help="Delete Task")

            if st.session_state.get('timer_active') and st.session_state.get('timer_task') and st.session_state.get('timer_interest') == interest:
                st.markdown("---")
                st.info(f"Focus: {st.session_state['timer_task']}")
                mins = st.number_input("Mins", 1, 120, 25, key=f"tm_{interest}")
                if st.button("Start", key=f"st_{interest}"):
                    p = st.progress(0); t = st.empty(); tot = mins*60
                    for s in range(tot): p.progress((s+1)/tot); t.metric("Time", f"{divmod(tot-s,60)[0]:02d}:{divmod(tot-s,60)[1]:02d}"); time.sleep(1)
                    st.success("Done!"); st.session_state['timer_active'] = False