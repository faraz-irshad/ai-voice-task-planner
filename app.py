import streamlit as st

from core.ai_processing import (
    transcribe_audio_with_gemini,
    extract_tasks_with_gemini,
    categorize_and_prioritize_tasks_with_gemini,
)
from core.scheduling import build_schedule


st.set_page_config(
    page_title="AI Voice Task Planner",
    page_icon="🎙️",
    layout="centered",
)

if "transcript" not in st.session_state:
    st.session_state.transcript = ""

if "tasks" not in st.session_state:
    st.session_state.tasks = []

if "prioritized_tasks" not in st.session_state:
    st.session_state.prioritized_tasks = []

if "schedule" not in st.session_state:
    st.session_state.schedule = {"today": [], "tomorrow": [], "later": []}

st.title("🎙 AI Voice Task Planner")
st.caption("Say everything you need to do. Get back a calm, prioritized list.")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ Voice memo")
    audio_file = st.file_uploader(
        "Upload a short voice note (WAV / MP3 / M4A)",
        type=["wav", "mp3", "m4a"],
        label_visibility="collapsed",
    )
    st.caption(
        "Example: “Tomorrow I need to email my professor, finish my assignment and buy groceries.”"
    )
    transcribe_clicked = st.button("Transcribe audio", use_container_width=True)

with col2:
    st.subheader("2️⃣ Transcript")
    st.session_state.transcript = st.text_area(
        "You can edit this before extracting tasks:",
        value=st.session_state.transcript,
        height=200,
    )

if transcribe_clicked:
    if audio_file is None:
        st.warning("Please upload an audio file first.")
    else:
        try:
            with st.spinner("Transcribing audio with Gemini…"):
                transcript = transcribe_audio_with_gemini(audio_file)

            if not transcript:
                st.error("Gemini returned an empty transcript. Try a clearer recording.")
            else:
                st.session_state.transcript = transcript
                st.success("Transcription complete. You can edit the text before extracting tasks.")
        except Exception as e:
            st.error(f"Transcription failed: {e}")

st.markdown("---")

st.subheader("3️⃣ Tasks & plan")
c1, c2 = st.columns(2)
with c1:
    extract_clicked = st.button("🧠 Extract tasks", use_container_width=True)
with c2:
    plan_clicked = st.button("📊 Prioritize & build plan", use_container_width=True)

if extract_clicked:
    if not st.session_state.transcript.strip():
        st.warning("Transcript is empty. Transcribe or type something first.")
    else:
        try:
            with st.spinner("Extracting tasks from transcript…"):
                tasks = extract_tasks_with_gemini(st.session_state.transcript)

            if not tasks:
                st.error("No clear tasks found in this text. Try speaking more concretely.")
            else:
                st.session_state.tasks = tasks
                st.success(f"Found {len(tasks)} task(s). Scroll down to see the list.")
        except Exception as e:
            st.error(f"Task extraction failed: {e}")

if plan_clicked:
    if not st.session_state.tasks:
        st.warning("No tasks found yet. Extract tasks first.")
    else:
        try:
            with st.spinner("Categorizing and prioritizing tasks…"):
                prioritized = categorize_and_prioritize_tasks_with_gemini(st.session_state.tasks)
                schedule = build_schedule(prioritized)

            if not prioritized:
                st.error("Planning failed – I couldn't parse any tasks. Try extracting again.")
            else:
                st.session_state.prioritized_tasks = prioritized
                st.session_state.schedule = schedule
                st.success("Plan generated. Scroll down to see the matrix and day split.")
        except Exception as e:
            st.error(f"Planning failed: {e}")

st.markdown("---")

st.subheader("4️⃣ Task list")
if st.session_state.tasks:
    for t in st.session_state.tasks:
        st.markdown(f"- {t}")
else:
    st.caption("No tasks yet. Start by transcribing and extracting.")
st.markdown("---")

st.subheader("5️⃣ Eisenhower matrix")

col_u_i, col_u_n, col_i_n, col_n_n = st.columns(4)

def show_priority(col, title, prefix):
    with col:
        st.markdown(f"**{title}**")
        found = False
        for item in st.session_state.prioritized_tasks:
            if item["priority"].startswith(prefix):
                st.markdown(f"- {item['task']}  _( {item['category']} )_")
                found = True
        if not found:
            st.caption("No tasks here yet.")

show_priority(col_u_i, "🔴 Urgent & important", "Urgent & Important")
show_priority(col_u_n, "🟠 Urgent & not important", "Urgent & Not Important")
show_priority(col_i_n, "🟢 Important & not urgent", "Important & Not Urgent")
show_priority(col_n_n, "⚪ Not urgent & not important", "Not Urgent & Not Important")

st.markdown("---")

st.subheader("6️⃣ Simple plan")

st.markdown("**Today**")
if st.session_state.schedule["today"]:
    for t in st.session_state.schedule["today"]:
        st.markdown(f"- {t['task']}  _( {t['priority']} )_")
else:
    st.caption("Nothing planned for today yet.")

st.markdown("**Tomorrow**")
if st.session_state.schedule["tomorrow"]:
    for t in st.session_state.schedule["tomorrow"]:
        st.markdown(f"- {t['task']}  _( {t['priority']} )_")
else:
    st.caption("Nothing planned for tomorrow.")

st.markdown("**Later**")
if st.session_state.schedule["later"]:
    for t in st.session_state.schedule["later"]:
        st.markdown(f"- {t['task']}  _( {t['priority']} )_")
else:
    st.caption("Nothing pushed to later.")
