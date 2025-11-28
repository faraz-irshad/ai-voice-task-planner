# AI Voice Task Planner

A Streamlit app that turns voice notes or text into organized, prioritized plans with scheduling helpers and focus blocks.

## Features
- Audio upload (wav, mp3, m4a) with Gemini transcription.
- Task extraction, categorization, and prioritization.
- To-do list with Today / Tomorrow / Later buckets and an Eisenhower matrix.
- Focus blocks for deep work vs. micro tasks.
- User login/registration with per-user saved plans.
- Demo mode to explore without recording.

## Quickstart
1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables in `.env`:
   ```
   GEMINI_API_KEY=your_key_here
   # Optional (defaults to sqlite:///planner.db):
   DB_URL=your_database_url
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Using the app
- Log in or register to access the planner.
- Upload audio and transcribe, or paste text directly.
- Click “Extract tasks” to generate tasks, schedules, and focus blocks.
- Save plans to revisit later; use “Load demo day” to see a sample flow.

## Notes
- Keep `.env` out of version control (already in `.gitignore`).
- If you encounter Gemini quota errors, retry later or adjust your billing/quota.***
