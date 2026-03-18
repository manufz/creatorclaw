"""
Story generation via Nemotron-30B running in llama-server.
Converts a raw user idea into a structured comic script.
"""
import json
import requests

LLAMA_SERVER = "http://localhost:8080"

SYSTEM_PROMPT = """You are a professional comic book writer and storyboard artist.
Your job is to take a story idea and break it down into comic panels.
Each panel should have:
- A vivid scene description for the artist (setting, characters, action, mood)
- Dialogue or caption text
- The visual style note

Respond ONLY with valid JSON. No explanation. No markdown fences."""

PANEL_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "style": {"type": "string"},
        "panels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "panel_number": {"type": "integer"},
                    "scene": {"type": "string"},
                    "image_prompt": {"type": "string"},
                    "dialogue": {"type": "string"},
                    "caption": {"type": "string"}
                }
            }
        }
    }
}


def generate_script(idea: str, num_panels: int = 4, style: str = "manga") -> dict:
    """Call Nemotron via llama-server to generate a comic script."""
    user_msg = f"""Create a {num_panels}-panel comic in {style} style for this idea:

"{idea}"

Return JSON with this structure:
{{
  "title": "Comic title",
  "style": "{style}",
  "panels": [
    {{
      "panel_number": 1,
      "scene": "Detailed visual description of the scene for the artist. Include setting, characters appearance, action, lighting, camera angle.",
      "image_prompt": "Optimized text-to-image prompt for this panel: {style} style, [scene details], high quality, detailed linework",
      "dialogue": "Character: spoken words (or empty string if no dialogue)",
      "caption": "Narration text shown in caption box (or empty string)"
    }}
  ]
}}"""

    payload = {
        "model": "nemotron",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"}
    }

    resp = requests.post(f"{LLAMA_SERVER}/v1/chat/completions", json=payload, timeout=120)
    resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"]

    # Strip any accidental markdown fences
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip().rstrip("```").strip()

    return json.loads(content)


def server_ready() -> bool:
    """Check if llama-server is up and healthy."""
    try:
        r = requests.get(f"{LLAMA_SERVER}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
