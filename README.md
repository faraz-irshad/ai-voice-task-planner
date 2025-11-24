# AI Voice Task Planner

Turn voice notes into organized, prioritized tasks with scheduling helpers and an Eisenhower matrix.

## Features
- Upload audio (wav, mp3, m4a) and transcribe to text.
- Extract tasks, auto-categorize, and rank by urgency/importance.
- To-do list with checkboxes to track completion.
- Eisenhower matrix and simple day buckets (Today, Tomorrow, Later).
- Focus blocks grouping deep work vs. micro tasks.

## Setup
1) Create a virtual env and install deps:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
2) Add your Gemini API key to `.env`:
```
GEMINI_API_KEY=your_key_here
```
3) Run the app:
```bash
streamlit run app.py
```

## Notes
- Keep `.env` out of git (already in `.gitignore`).
- If you hit Gemini quota errors, wait or adjust your billing/quota.***
