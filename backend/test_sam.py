"""
test_sam.py
Send a figure to SAM 3.1 and print the SHAPE of what comes back.
Long values (like mask data) are shortened so the output stays readable.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY")
if not api_key:
    raise SystemExit("No API key found in backend/.env")

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "test_figure.png"
PHRASE = sys.argv[2] if len(sys.argv) > 2 else "chemical structure"

ext = IMAGE.lower().rsplit(".", 1)[-1]
mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"


def shorten(x, limit=80):
    """Shrink long strings and long lists so we can see the structure."""
    if isinstance(x, dict):
        return {k: shorten(v, limit) for k, v in x.items()}
    if isinstance(x, list):
        head = [shorten(v, limit) for v in x[:3]]
        return head + [f"... ({len(x)} items total)"] if len(x) > 3 else head
    if isinstance(x, str) and len(x) > limit:
        return x[:limit] + f"... ({len(x)} chars)"
    return x


# 1. Upload the image
print("Uploading image...")
with open(IMAGE, "rb") as f:
    up = requests.post(
        "https://api.meta.ai/v1/files",
        headers={"Authorization": f"Bearer {api_key}"},
        data={"purpose": "user_data"},
        files={"file": (os.path.basename(IMAGE), f, mime)},
        timeout=120,
    )
print("Upload status:", up.status_code)
up.raise_for_status()
file_id = up.json().get("id")
print("file id received:", bool(file_id))

# 2. Ask SAM to segment
payload = {
    "model": "sam-3.1",
    "input": [
        {
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": PHRASE},
                {"type": "input_image", "file_id": file_id},
            ],
        }
    ],
    "stream": True,
    "metadata": {"mask_encoding": "lossless"},
}

print(f"\nAsking SAM 3.1 to find: '{PHRASE}'\n")
raw_events = []
with requests.post(
    "https://api.meta.ai/v1/responses",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    },
    json=payload,
    stream=True,
    timeout=180,
) as response:
    print("Status:", response.status_code)
    if response.status_code != 200:
        print(response.text[:500])
        raise SystemExit(1)
    for line in response.iter_lines():
        if not line.startswith(b"data: "):
            continue
        data = line[6:].decode("utf-8", errors="replace")
        if data == "[DONE]":
            break
        raw_events.append(data)

print(f"Received {len(raw_events)} events\n")

# 3. Show the shape of the first 3 and the last 2 events
for i in list(range(min(3, len(raw_events)))) + list(range(max(3, len(raw_events) - 2), len(raw_events))):
    try:
        shown = json.dumps(shorten(json.loads(raw_events[i])), indent=2)
    except Exception:
        shown = raw_events[i][:300]
    print(f"--- event {i} ---")
    print(shown)

# 4. Save everything for later (this file stays on your computer only)
with open("sam_raw.jsonl", "w", encoding="utf-8") as f:
    f.write("\n".join(raw_events))
print("\nFull raw reply saved to sam_raw.jsonl")