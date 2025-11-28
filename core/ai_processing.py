from google.api_core import exceptions as google_exceptions

from core.gemini_client import get_client


class GeminiQuotaError(Exception):
    """Raised when the Gemini API reports quota exhaustion."""


class GeminiClientError(Exception):
    """Raised for other Gemini API failures."""


def _call_model(model, parts):
    try:
        return model.generate_content(parts)
    except google_exceptions.ResourceExhausted as exc:
        raise GeminiQuotaError(
            "Gemini quota exceeded. Please wait and retry or update your plan/billing."
        ) from exc
    except google_exceptions.GoogleAPICallError as exc:
        raise GeminiClientError("Gemini API call failed.") from exc
    except Exception as exc:  # pragma: no cover - catch-all for SDK edge cases
        raise GeminiClientError("Unexpected Gemini error.") from exc


def transcribe_audio(audio_bytes, mime_type):
    model = get_client()
    prompt = "Transcribe this audio to clean readable English text. No summarizing. Pure transcription only."
    response = _call_model(model, [prompt, {"mime_type": mime_type, "data": audio_bytes}])
    return response.text.strip()


def extract_tasks(transcript):
    model = get_client()
    prompt = f"""Extract actionable tasks from this transcript.
Rules:
- Start with a verb
- Short
- No feelings
- No summaries
- No filler
Output each task on its own line.

Transcript:
{transcript}"""
    response = _call_model(model, prompt)
    tasks = [t.strip() for t in response.text.strip().split("\n") if t.strip()]
    return tasks


def categorize_and_prioritize(tasks):
    model = get_client()
    task_list = "\n".join([f"{i+1}. {t}" for i, t in enumerate(tasks)])
    prompt = f"""For each task, assign category and priority.

Categories: Work, Study, Errand, Personal, Health, Finance, Other
Priorities: Urgent & Important, Urgent & Not Important, Important & Not Urgent, Not Urgent & Not Important

Output format (one per line):
<task> || <category> || <priority>

Tasks:
{task_list}"""
    response = _call_model(model, prompt)
    results = []
    for line in response.text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        category = "Other"
        priority = "Not Urgent & Not Important"
        task = None
        if "||" in line:
            parts = [p.strip() for p in line.split("||")]
            if len(parts) == 3:
                task, category, priority = parts
            else:
                task = parts[0] if parts and parts[0] else None
        else:
            task = line
        if task:
            results.append({"task": task, "category": category, "priority": priority})
    existing_tasks = {r["task"] for r in results}
    for original in tasks:
        if original not in existing_tasks:
            results.append({"task": original, "category": "Other", "priority": "Not Urgent & Not Important"})
    return results


def classify_cognitive_load(tasks):
    model = get_client()
    task_list = "\n".join([f"{i+1}. {t['task']}" for i, t in enumerate(tasks)])
    prompt = f"""Classify each task as:
- Deep Task (high cognitive load, requires uninterrupted attention)
- Micro Task (quick, low cognitive load, 1-5 minutes)
- Other

Output format (one per line):
<task> || <type>

Tasks:
{task_list}"""
    response = _call_model(model, prompt)
    for line in response.text.strip().split("\n"):
        if "||" in line:
            parts = [p.strip() for p in line.split("||")]
            if len(parts) == 2:
                for task in tasks:
                    if task["task"] == parts[0]:
                        task["type"] = parts[1]
                        break
    for task in tasks:
        # Ensure every task has a type even if the model response didn't map perfectly.
        task.setdefault("type", "Other")
    return tasks
