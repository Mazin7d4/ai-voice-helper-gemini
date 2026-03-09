import os, json, base64
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

if not PROJECT_ID:
    raise RuntimeError("Missing GCP_PROJECT_ID in .env")

# Use Vertex AI backend with service account credentials
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

SYSTEM_PROMPT = """
You are a UI navigation agent.

Given:
- a user goal
- a screenshot of the current page

Return EXACTLY ONE next action in JSON.

Allowed actions:
- click: click an element described by target_text
- type: click target_text then type into it
- scroll: scroll direction + amount
- done: if goal is completed

Output ONLY valid JSON with this schema:
{
  "type": "click|type|scroll|done",
  "target_text": "string",
  "text": "string",
  "scroll": {"direction":"down|up", "amount": 1},
  "explanation": "string"
}

Rules:
- Prefer clicking links/buttons with visible text.
- If typing, target_text should be the input label/placeholder near it.
- If unsure, click the most relevant obvious navigation.
"""

def decide_action(goal: str, screenshot_bytes: bytes) -> dict:
    prompt = f"""
User goal: {goal}

Decide the next ONE action based on the screenshot.
"""

    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Content(role="user", parts=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png"),
            ]),
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        ),
    )

    text = resp.text.strip()

    # Hard guard: extract JSON even if wrapped
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError(f"Model did not return JSON. Got:\n{text}")

    return json.loads(text[start : end + 1])
