import json
import streamlit as st

from core.ai_processing import (
    categorize_and_prioritize,
    classify_cognitive_load,
    extract_tasks,
    transcribe_audio,
    GeminiClientError,
    GeminiQuotaError,
)
from core.scheduling import create_focus_blocks, schedule_task
from core.storage import init_db, save_plan, list_plans, create_user, authenticate_user

st.set_page_config(page_title="AI Voice Task Planner", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body {
    background: #000000;
    color: #e5e7eb;
    font-family: 'Inter', sans-serif;
    font-size: 17px;
    line-height: 1.6;
}
.main .block-container {
    max-width: 980px;
    margin: 0 auto;
    padding-top: 2rem;
    padding-bottom: 2rem;
}
.app-card {
    background: #111111;
    border: 1px solid #2a2040;
    box-shadow: 0 12px 30px rgba(168, 85, 255, 0.18);
    border-radius: 18px;
    padding: 1.75rem 1.5rem 1.5rem 1.5rem;
    margin-bottom: 1.25rem;
}
.app-card h1, .app-card h2, .app-card h3, .app-card h4 {
    color: #f8fafc;
    letter-spacing: -0.01em;
}
.accent {
    color: #c084fc;
}
.stButton > button {
    width: 100%;
    border-radius: 12px;
    height: 3rem;
    font-weight: 600;
    background: linear-gradient(90deg, #a855ff, #c084fc);
    color: #ffffff;
    border: none;
    box-shadow: 0 6px 18px rgba(168, 85, 255, 0.35);
}
.stButton > button:hover {
    box-shadow: 0 0 0 2px rgba(192, 132, 252, 0.45), 0 8px 22px rgba(168, 85, 255, 0.35);
}
.stTextInput > div > div > input,
.stTextArea textarea {
    background: #0c0c0c;
    color: #e5e7eb;
    border-radius: 12px;
    border: 1px solid #2a2340;
}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
    border: 1px solid #c084fc;
    box-shadow: 0 0 0 1px #c084fc;
}
.stFileUploader {
    border-radius: 12px;
    background: #0c0c0c;
    border: 1px dashed #2a2340;
}
.stFileUploader label {
    color: #e5e7eb;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
}
.stTabs [data-baseweb="tab"] {
    color: #c084fc;
    background: #0f0f10;
}
</style>
""", unsafe_allow_html=True)

init_db()

def get_demo_plan():
    demo_transcript = (
        "Mission log: confirm the portal sensors, prep snacks for the crew, schedule a Hawkins town hall, "
        "train the squad on walkie-talkie etiquette, hunt demogorgons lurking near the old mall, "
        "patch bike tires before the next chase, and queue up 80s synth tracks for morale."
    )
    base_tasks = [
        {"task": "Check portal sensors before nightfall", "category": "Work", "priority": "Urgent & Important", "type": "Deep Task"},
        {"task": "Prep Eggo snack stash for the crew", "category": "Personal", "priority": "Urgent & Not Important", "type": "Micro Task"},
        {"task": "Schedule Hawkins town hall briefing", "category": "Errand", "priority": "Important & Not Urgent", "type": "Micro Task"},
        {"task": "Train squad on walkie-talkie etiquette", "category": "Study", "priority": "Important & Not Urgent", "type": "Deep Task"},
        {"task": "Hunt demogorgons near the old mall", "category": "Health", "priority": "Urgent & Important", "type": "Deep Task"},
        {"task": "Patch bike tires for next chase", "category": "Personal", "priority": "Urgent & Not Important", "type": "Micro Task"},
        {"task": "Queue 80s synth tracks for morale", "category": "Personal", "priority": "Not Urgent & Not Important", "type": "Other"},
    ]
    tasks = []
    scheduled = {"Today": [], "Tomorrow": [], "Later": []}
    for t in base_tasks:
        task = dict(t)
        task["schedule"] = schedule_task(task["priority"])
        task["done"] = False
        tasks.append(task)
        scheduled[task["schedule"]].append(task)
    blocks = create_focus_blocks(tasks)
    return demo_transcript, tasks, scheduled, blocks

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    with st.container():
        st.markdown("<div class='app-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color:#e5e7eb;'>🎙️ AI Voice Task Planner</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#c084fc;'>Log in or create an account to turn voice notes into action.</p>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            st.markdown("### Login")
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", key="login_button"):
                if login_username and login_password:
                    user = authenticate_user(login_username, login_password)
                    if user:
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter username and password")
        with tab2:
            st.markdown("### Register")
            reg_username = st.text_input("Username", key="reg_username")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
            if st.button("Register", key="register_button"):
                if reg_username and reg_password and reg_password_confirm:
                    if reg_password != reg_password_confirm:
                        st.error("Passwords do not match")
                    else:
                        user = create_user(reg_username, reg_password)
                        if user:
                            st.success("Registration successful! Please login.")
                        else:
                            st.error("Username already exists")
                else:
                    st.warning("Please fill all fields")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

st.sidebar.markdown(f"**Logged in as:** {st.session_state.user['username']}")

if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "scheduled_tasks" not in st.session_state:
    st.session_state.scheduled_tasks = {}
if "blocks" not in st.session_state:
    st.session_state.blocks = []

with st.container():
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center; color:#e5e7eb;'>🎙️ AI Voice Task Planner</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#c084fc;'>Turn messy voice notes or brain dumps into a clear, prioritized plan in under a minute.</p>", unsafe_allow_html=True)
    st.markdown("<h4 class='accent' style='margin-top:1rem;'>How it works</h4>", unsafe_allow_html=True)
    st.markdown("1. **Capture** – Upload audio or paste your thoughts as text.<br>2. **Understand** – The AI extracts action items, tags them, and prioritizes them.<br>3. **Plan** – See your day organized into Today / Tomorrow / Later and an Eisenhower matrix.<br>4. **Focus** – Get deep-work blocks and micro-task sprints.", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.markdown("<h3 class='accent'>Input</h3>", unsafe_allow_html=True)
    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown("#### 🎤 1. Capture your thoughts")
        st.markdown("Don’t want to record right now? Load a sample day to see how the planner works.")
        if st.button("🔍 Load demo day", key="load_demo_plan"):
            demo_transcript, demo_tasks, demo_scheduled, demo_blocks = get_demo_plan()
            st.session_state.transcript = demo_transcript
            st.session_state.tasks = demo_tasks
            st.session_state.scheduled_tasks = demo_scheduled
            st.session_state.blocks = demo_blocks
            st.rerun()
        st.markdown("#### 📤 Upload a voice note (optional)")
        audio_file = st.file_uploader(
            "Upload audio file",
            type=["wav", "mp3", "m4a"],
            label_visibility="collapsed",
        )
        st.caption("Short notes (2–3 minutes) work best. Supported: WAV, MP3, M4A.")
        if audio_file:
            st.audio(audio_file)
            if st.button("🎯 Transcribe audio"):
                with st.spinner("Transcribing..."):
                    mime_map = {"wav": "audio/wav", "mp3": "audio/mp3", "m4a": "audio/mp4"}
                    mime_type = mime_map.get(audio_file.name.split(".")[-1], "audio/wav")
                    audio_bytes = audio_file.read()
                    try:
                        st.session_state.transcript = transcribe_audio(audio_bytes, mime_type)
                        st.rerun()
                    except GeminiQuotaError as exc:
                        st.error(str(exc))
                    except GeminiClientError as exc:
                        st.error(f"Transcription failed: {exc}")
                    except Exception as exc:
                        st.error(f"Unexpected transcription error: {exc}")
    with right_col:
        st.markdown("#### 📝 2. Edit text & extract tasks")
        st.caption("Paste your notes here, or use the left panel to transcribe an audio note.")
        transcript_input = st.text_area(
            "Transcript or free-form text",
            value=st.session_state.transcript,
            height=220,
            placeholder="Write or paste anything you want turned into tasks.",
            key="transcript_editor",
        )
        st.session_state.transcript = transcript_input
        if st.button("✨ Extract tasks from this text"):
            if not st.session_state.transcript.strip():
                st.warning("Please add some text first, or transcribe audio.")
            else:
                with st.spinner("Extracting tasks..."):
                    try:
                        raw_tasks = extract_tasks(st.session_state.transcript)
                        if not raw_tasks:
                            st.warning("No actionable tasks detected. Try adding more concrete actions or clearer phrasing.")
                        else:
                            categorized = categorize_and_prioritize(raw_tasks)
                            classified = classify_cognitive_load(categorized)
                            for task in classified:
                                task["schedule"] = schedule_task(task["priority"])
                                task["done"] = False
                            st.session_state.tasks = classified
                            scheduled = {"Today": [], "Tomorrow": [], "Later": []}
                            for task in classified:
                                scheduled[task["schedule"]].append(task)
                            st.session_state.scheduled_tasks = scheduled
                            st.rerun()
                    except GeminiQuotaError as exc:
                        st.error(str(exc))
                    except GeminiClientError as exc:
                        st.error(f"Task extraction failed: {exc}")
                    except Exception as exc:
                        st.error(f"Unexpected task extraction error: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.tasks:
    with st.container():
        st.markdown("<div class='app-card'>", unsafe_allow_html=True)
        st.markdown("<h3 class='accent'>📋 3. Your plan for this note</h3>", unsafe_allow_html=True)
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            st.markdown("#### ✅ To-do list")
            for idx, task in enumerate(st.session_state.tasks):
                task["done"] = st.checkbox(
                    task["task"],
                    key=f"todo_{idx}",
                    value=task.get("done", False),
                )
                st.caption(f"🏷️ {task.get('category', 'Uncategorized')} · 🧠 {task.get('type', 'Unclassified')}")
        with row1_col2:
            st.markdown("#### 📅 When to do them")
            today_col, tomorrow_col, later_col = st.columns(3)
            for label, column in zip(["Today", "Tomorrow", "Later"], [today_col, tomorrow_col, later_col]):
                with column:
                    st.markdown(f"**{label}**")
                    tasks_for_day = st.session_state.scheduled_tasks.get(label, [])
                    if tasks_for_day:
                        for task in tasks_for_day:
                            st.markdown(f"- {task['task']}")
                    else:
                        st.caption("Nothing here yet.")
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            st.markdown("#### 🧭 Priority matrix")
            matrix = {
                "Urgent & Important": [],
                "Urgent & Not Important": [],
                "Important & Not Urgent": [],
                "Not Urgent & Not Important": [],
            }
            for task in st.session_state.tasks:
                if task.get("priority") in matrix:
                    matrix[task["priority"]].append(task)
            top_left, top_right = st.columns(2)
            with top_left:
                st.markdown("**Urgent & Important**")
                if matrix["Urgent & Important"]:
                    for task in matrix["Urgent & Important"]:
                        st.markdown(f"- {task['task']} ({task.get('category', 'Uncategorized')} • {task.get('type', 'Unclassified')})")
                else:
                    st.caption("No tasks yet.")
            with top_right:
                st.markdown("**Urgent & Not Important**")
                if matrix["Urgent & Not Important"]:
                    for task in matrix["Urgent & Not Important"]:
                        st.markdown(f"- {task['task']} ({task.get('category', 'Uncategorized')} • {task.get('type', 'Unclassified')})")
                else:
                    st.caption("No tasks yet.")
            bottom_left, bottom_right = st.columns(2)
            with bottom_left:
                st.markdown("**Important & Not Urgent**")
                if matrix["Important & Not Urgent"]:
                    for task in matrix["Important & Not Urgent"]:
                        st.markdown(f"- {task['task']} ({task.get('category', 'Uncategorized')} • {task.get('type', 'Unclassified')})")
                else:
                    st.caption("No tasks yet.")
            with bottom_right:
                st.markdown("**Not Urgent & Not Important**")
                if matrix["Not Urgent & Not Important"]:
                    for task in matrix["Not Urgent & Not Important"]:
                        st.markdown(f"- {task['task']} ({task.get('category', 'Uncategorized')} • {task.get('type', 'Unclassified')})")
                else:
                    st.caption("No tasks yet.")
        with row2_col2:
            st.markdown("#### 🎯 Focus blocks")
            blocks_view = create_focus_blocks(st.session_state.tasks)
            for block in blocks_view:
                st.markdown(f"**{block['type']}**")
                for task in block["tasks"]:
                    st.markdown(f"- {task['task']}")
                st.markdown("")
        st.markdown("</div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.markdown("<h3 class='accent'>🕒 4. Saved plans & history</h3>", unsafe_allow_html=True)
    st.markdown("#### Save current plan")
    plan_title = st.text_input("Plan title (optional)", placeholder="e.g. 'Monday study sprint' or 'Weekend errands'")
    if st.button("Save this plan"):
        if not st.session_state.tasks:
            st.warning("Nothing to save yet. Generate tasks and a plan first.")
        else:
            blocks_to_save = create_focus_blocks(st.session_state.tasks)
            plan = save_plan(
                st.session_state.user["id"],
                plan_title,
                st.session_state.transcript,
                st.session_state.tasks,
                st.session_state.tasks,
                st.session_state.scheduled_tasks,
                blocks_to_save,
            )
            st.success(f'Saved plan as "{plan.title}".')
    st.markdown("#### Recent plans")
    plans = list_plans(st.session_state.user["id"], limit=5)
    if not plans:
        st.caption("No saved plans yet.")
    else:
        for p in plans:
            if st.button(
                f"{p.title} – {p.created_at.strftime('%Y-%m-%d %H:%M')}",
                key=f"plan_{p.id}",
            ):
                try:
                    tasks = json.loads(p.tasks_json)
                    prioritized = json.loads(p.prioritized_json)
                    schedule = json.loads(p.schedule_json)
                    loaded_blocks = json.loads(p.blocks_json)
                except Exception:
                    st.error("This saved plan could not be loaded; it looks corrupted. Your current plan is unchanged.")
                else:
                    if not isinstance(tasks, list) or not isinstance(schedule, dict) or not isinstance(loaded_blocks, list):
                        st.error("This saved plan could not be loaded; it looks corrupted. Your current plan is unchanged.")
                    else:
                        st.session_state.transcript = p.transcript
                        st.session_state.tasks = tasks
                        st.session_state.scheduled_tasks = schedule
                        st.session_state.blocks = loaded_blocks
                        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
