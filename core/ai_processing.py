from google.genai import types

from .gemini_client import get_gemini_client


def transcribe_audio_with_gemini(uploaded_file):
    client = get_gemini_client()

    audio_bytes = uploaded_file.read()
    mime_type = uploaded_file.type or "audio/mp3"

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            (
                "Transcribe this voice memo into clear, punctuated English. "
                "Keep it faithful to what is said. Don't summarize, don't invent anything."
            ),
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
        ],
    )

    return (response.text or "").strip()


def extract_tasks_with_gemini(transcript: str) -> list[str]:
    client = get_gemini_client()

    prompt = f"""
You will receive a transcript of a person's voice note about their day and plans.

Your job: extract ONLY clear, actionable tasks.

Rules:
- Each task should start with a verb (e.g. "Email the professor", "Buy groceries").
- Ignore vague feelings and complaints (e.g. "I'm tired", "I'm stressed").
- Ignore dreams or very hypothetical ideas ("Someday I might move to Japan").
- Use short, simple English.
- Do NOT number the tasks.

Transcript:
\"\"\"{transcript}\"\"\"

Output format (strict):
Write one task per line, and start each line with "- ".
Example:
- Email the database professor about the assignment deadline
- Buy milk and eggs
- Clean the kitchen
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt],
    )

    raw = (response.text or "").strip()
    tasks: list[str] = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line[0] in ["-", "•"]:
            task = line[1:].strip()
        else:
            task = line
        if task:
            tasks.append(task)

    return tasks


def categorize_and_prioritize_tasks_with_gemini(tasks: list[str]) -> list[dict]:
    client = get_gemini_client()

    tasks_block = "\n".join(f"- {t}" for t in tasks)

    prompt = f"""
You will receive a list of TODO tasks.

For EACH task, you must:
1. Assign ONE category from this list:
   [Work, Study, Errand, Personal, Health, Finance, Other]

2. Assign ONE priority using the Eisenhower Matrix:
   - Urgent & Important
   - Urgent & Not Important
   - Important & Not Urgent
   - Not Urgent & Not Important

Think like a normal busy student/young professional.

Input tasks:
{tasks_block}

Output format (strict):
One line per task, in this exact format:
<task> || <category> || <priority>

Example:
Email the database professor about the assignment || Study || Important & Not Urgent
Buy groceries for dinner || Errand || Urgent & Not Important
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt],
    )

    raw = (response.text or "").strip()
    results: list[dict] = []

    for line in raw.splitlines():
        if "||" not in line:
            continue
        parts = [p.strip() for p in line.split("||")]
        if len(parts) != 3:
            continue
        task_text, category, priority = parts
        if not task_text:
            continue
        results.append(
            {
                "task": task_text,
                "category": category,
                "priority": priority,
            }
        )

    return results
