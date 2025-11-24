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

st.title("🎙️ AI Voice Task Planner")
st.markdown("Transform voice notes into organized, actionable tasks")

if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "scheduled_tasks" not in st.session_state:
    st.session_state.scheduled_tasks = {}

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
                except Exception as exc:  # pragma: no cover - defensive
                    st.error(f"Unexpected transcription error: {exc}")

with col2:
    st.markdown("### 📝 Transcript")
    if st.session_state.transcript:
        st.text_area("Transcript", st.session_state.transcript, height=200, label_visibility="collapsed")
        if st.button("✨ Extract Tasks"):
            with st.spinner("Extracting tasks..."):
                try:
                    raw_tasks = extract_tasks(st.session_state.transcript)
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
                except Exception as exc:  # pragma: no cover - defensive
                    st.error(f"Unexpected task extraction error: {exc}")
    else:
        st.info("Upload and transcribe audio to see transcript")

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
                    st.markdown(f"🏷️ {task['category']} • ⚡ {task['priority']} • 🧠 {task['type']}")
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
                st.markdown(f"- {task['task']} ({task['category']} • {task['type']})")
        else:
            st.markdown("_No tasks yet_")
    with col_b:
        st.markdown("### Urgent & Not Important")
        if matrix["Urgent & Not Important"]:
            for task in matrix["Urgent & Not Important"]:
                st.markdown(f"- {task['task']} ({task['category']} • {task['type']})")
        else:
            st.markdown("_No tasks yet_")
    
    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown("### Important & Not Urgent")
        if matrix["Important & Not Urgent"]:
            for task in matrix["Important & Not Urgent"]:
                st.markdown(f"- {task['task']} ({task['category']} • {task['type']})")
        else:
            st.markdown("_No tasks yet_")
    with col_d:
        st.markdown("### Not Urgent & Not Important")
        if matrix["Not Urgent & Not Important"]:
            for task in matrix["Not Urgent & Not Important"]:
                st.markdown(f"- {task['task']} ({task['category']} • {task['type']})")
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
