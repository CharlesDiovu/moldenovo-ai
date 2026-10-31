"""
generate_hero.py
Generates the website's hero picture with Muse Image.
Decoration only: abstract shapes, no chemistry, no text.
Run once, then commit the saved file.
"""

import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY")
if not key:
    raise SystemExit("No API key found in backend/.env")

PROMPT = (
    "Soft aqua and white background, translucent glass spheres and hexagonal glass "
    "crystals with teal-blue textured cell-like forms, clean medical-tech aesthetic, "
    "bright airy lighting, wide composition with empty space on the left, "
    "no text, no letters, no diagrams"
)

payload = {
    "input": [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": PROMPT}],
        }
    ],
    "max_output_tokens": 2048,
    "model": "muse-image-1.0",
    "store": True,
    "stream": False,
    "temperature": 0.6,
    "top_p": 0.9,
    "tools": [
        {
            "type": "image_generation",
            "output_format": "png",
            "reasoning_strength": "high",
            "enable_image_search": False,
            "enable_shell": False,
            "enable_web_search": False,
        }
    ],
}

print("Asking Muse Image (this can take a minute or two)...")
resp = requests.post(
    "https://api.meta.ai/v1/responses",
    headers={"Authorization": f"Bearer {key}"},
    json=payload,
    timeout=300,
)
if resp.status_code != 200:
    raise SystemExit(f"Meta API error {resp.status_code}: {resp.text[:600]}")

result = resp.json()
if result.get("error") or result.get("status") != "completed":
    raise SystemExit(f"Not completed: {result.get('error') or result.get('incomplete_details') or result.get('status')}")

here = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(here, "..", "frontend", "public")
os.makedirs(out_dir, exist_ok=True)

saved = 0
for item in result.get("output", []):
    if item.get("type") == "image_generation_call" and item.get("result"):
        saved += 1
        path = os.path.join(out_dir, "hero.png" if saved == 1 else f"hero-{saved}.png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(item["result"]))
        print("Saved", os.path.normpath(path))

if saved == 0:
    raise SystemExit("No image came back. Reply status: " + str(result.get("status")))
print("Response ID:", result.get("id"))