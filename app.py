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
.main > div {
    padding-top: 2rem;
}
h1 {
    font-size: 2.5rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
h2 {
    font-size: 1.5rem;
    font-weight: 500;
    margin-top: 2rem;
    margin-bottom: 1rem;
}
h3 {
    font-size: 1.2rem;
    font-weight: 500;
}
.stButton > button {
    width: 100%;
    border-radius: 12px;
    height: 3rem;
    font-weight: 500;
}
div[data-testid="stFileUploader"] {
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

init_db()

def get_demo_plan():
    demo_transcript = (
        "Quick recap: finalize the proposal deck for the client review tomorrow, send them a timeline update, "
        "study data structures for the interview prep, pick up prescriptions and groceries on the way home, "
        "book a dentist appointment for next month, and prep a 20-minute cardio session tonight."
    )
    base_tasks = [
        {"task": "Finalize proposal deck for client review", "category": "Work", "priority": "Urgent & Important", "type": "Deep Task"},
        {"task": "Email client with updated project timeline", "category": "Work", "priority": "Urgent & Not Important", "type": "Micro Task"},
        {"task": "Study data structures for interview prep", "category": "Study", "priority": "Important & Not Urgent", "type": "Deep Task"},
        {"task": "Pick up prescriptions and groceries", "category": "Errand", "priority": "Urgent & Not Important", "type": "Micro Task"},
        {"task": "Book dentist appointment for next month", "category": "Health", "priority": "Important & Not Urgent", "type": "Micro Task"},
        {"task": "Plan meals for the week and grocery list", "category": "Personal", "priority": "Not Urgent & Not Important", "type": "Other"},
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
    st.title("🎙️ AI Voice Task Planner")
    st.markdown("Transform voice notes into organized, actionable tasks")
    st.markdown("---")
    
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
    st.stop()

st.sidebar.markdown(f"**Logged in as:** {st.session_state.user['username']}")

st.title("🎙️ AI Voice Task Planner")
st.markdown("Transform voice notes into organized, actionable tasks")

if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "scheduled_tasks" not in st.session_state:
    st.session_state.scheduled_tasks = {}
if "blocks" not in st.session_state:
    st.session_state.blocks = []

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📤 Upload Audio")
    audio_file = st.file_uploader(
        "Upload audio file",
        type=["wav", "mp3", "m4a"],
        label_visibility="collapsed",
    )

    if audio_file:
        st.audio(audio_file)
        if st.button("🎯 Transcribe Audio"):
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

with col2:
    st.markdown("### 📝 Transcript or Text Input")
    if st.button("Load Demo Plan", key="load_demo_plan"):
        demo_transcript, demo_tasks, demo_scheduled, demo_blocks = get_demo_plan()
        st.session_state.transcript = demo_transcript
        st.session_state.tasks = demo_tasks
        st.session_state.scheduled_tasks = demo_scheduled
        st.session_state.blocks = demo_blocks
        st.rerun()
    transcript_input = st.text_area(
        "Transcript",
        value=st.session_state.transcript,
        height=200,
        label_visibility="collapsed",
        placeholder="Paste or type notes here, or transcribe audio on the left.",
        key="transcript_editor",
    )
    # Keep session state in sync with any manual transcript edits.
    st.session_state.transcript = transcript_input

    if st.button("✨ Extract Tasks"):
        if not st.session_state.transcript.strip():
            st.warning("Add some text first, or transcribe audio.")
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

if st.session_state.tasks:
    st.markdown("---")
    st.markdown("## ✅ To-Do List")
    for idx, task in enumerate(st.session_state.tasks):
        task["done"] = st.checkbox(
            task["task"],
            key=f"todo_{idx}",
            value=task.get("done", False),
        )
    st.markdown("")

    st.markdown("---")
    st.markdown("## 📋 Scheduled Tasks")

    for schedule in ["Today", "Tomorrow", "Later"]:
        if st.session_state.scheduled_tasks[schedule]:
            st.markdown(f"### {schedule}")
            for idx, task in enumerate(st.session_state.scheduled_tasks[schedule]):
                with st.container():
                    st.markdown(f"**{task['task']}**")
                    st.markdown(
                        f"🏷️ {task.get('category', 'Uncategorized')} • "
                        f"⚡ {task.get('priority', 'Unprioritized')} • "
                        f"🧠 {task.get('type', 'Unclassified')}"
                    )
                    st.markdown("")

    st.markdown("---")
    st.markdown("## 🧭 Eisenhower Matrix")
    matrix = {
        "Urgent & Important": [],
        "Urgent & Not Important": [],
        "Important & Not Urgent": [],
        "Not Urgent & Not Important": [],
    }
    for task in st.session_state.tasks:
        if task.get("priority") in matrix:
            matrix[task["priority"]].append(task)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Urgent & Important")
        if matrix["Urgent & Important"]:
            for task in matrix["Urgent & Important"]:
                st.markdown(
                    f"- {task['task']} ("
                    f"{task.get('category', 'Uncategorized')} • "
                    f"{task.get('type', 'Unclassified')})"
                )
        else:
            st.markdown("_No tasks yet_")
    with col_b:
        st.markdown("### Urgent & Not Important")
        if matrix["Urgent & Not Important"]:
            for task in matrix["Urgent & Not Important"]:
                st.markdown(
                    f"- {task['task']} ("
                    f"{task.get('category', 'Uncategorized')} • "
                    f"{task.get('type', 'Unclassified')})"
                )
        else:
            st.markdown("_No tasks yet_")

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown("### Important & Not Urgent")
        if matrix["Important & Not Urgent"]:
            for task in matrix["Important & Not Urgent"]:
                st.markdown(
                    f"- {task['task']} ("
                    f"{task.get('category', 'Uncategorized')} • "
                    f"{task.get('type', 'Unclassified')})"
                )
        else:
            st.markdown("_No tasks yet_")
    with col_d:
        st.markdown("### Not Urgent & Not Important")
        if matrix["Not Urgent & Not Important"]:
            for task in matrix["Not Urgent & Not Important"]:
                st.markdown(
                    f"- {task['task']} ("
                    f"{task.get('category', 'Uncategorized')} • "
                    f"{task.get('type', 'Unclassified')})"
                )
        else:
            st.markdown("_No tasks yet_")

    st.markdown("---")
    st.markdown("## 🎯 Focus Blocks")

    blocks = create_focus_blocks(st.session_state.tasks)
    for block in blocks:
        st.markdown(f"### {block['type']}")
        for task in block["tasks"]:
            st.markdown(f"- {task['task']}")
        st.markdown("")

    st.markdown("---")
    st.markdown("## 💾 Save Plan")

    plan_title = st.text_input("Plan title (optional)")

    if st.button("Save this plan"):
        if not st.session_state.tasks:
            st.warning("Nothing to save yet. Generate tasks and a plan first.")
        else:
            plan = save_plan(
                st.session_state.user["id"],
                plan_title,
                st.session_state.transcript,
                st.session_state.tasks,
                st.session_state.tasks,
                st.session_state.scheduled_tasks,
                blocks,
            )
            st.success(f'Saved plan as "{plan.title}".')

st.markdown("---")
st.markdown("## 📚 Previous Plans")

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
                st.error("Unable to load this saved plan; the stored data is corrupted.")
            else:
                if not isinstance(tasks, list) or not isinstance(schedule, dict) or not isinstance(loaded_blocks, list):
                    st.error("Unable to load this saved plan; the stored data is corrupted.")
                else:
                    st.session_state.transcript = p.transcript
                    st.session_state.tasks = tasks
                    st.session_state.scheduled_tasks = schedule
                    st.session_state.blocks = loaded_blocks
                    st.rerun()
