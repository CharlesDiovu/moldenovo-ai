"""
meta_client.py
One place for all calls to the Meta Model API.
"""

import os
import json
import time
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.meta.ai/v1/responses"
DEFAULT_MODEL = "muse-spark-1.3"


def _get_key():
    key = os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY")
    if not key:
        raise RuntimeError("No API key found in backend/.env")
    return key


def _post_with_retries(payload, timeout, tries):
    """Send a request, retrying if the network drops. Returns the parsed reply."""
    resp = None
    last_error = None
    for attempt in range(tries):
        try:
            resp = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {_get_key()}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
            break
        except requests.exceptions.RequestException as e:
            last_error = e
            time.sleep(2 * (attempt + 1))
    if resp is None:
        raise RuntimeError(f"Could not reach Meta API after {tries} tries: {last_error}")
    if resp.status_code != 200:
        raise RuntimeError(f"Meta API error {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def _extract_text(data):
    """Pull the answer text out of a Meta reply."""
    parts = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    parts.append(block.get("text", ""))
    return "".join(parts).strip()


def ask(prompt, model=DEFAULT_MODEL, effort="low", timeout=120):
    """Send one prompt to a Muse model and return its reply as plain text."""
    payload = {
        "model": model,
        "input": [
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]}
        ],
        "stream": False,
        "reasoning": {"effort": effort},
    }
    return _extract_text(_post_with_retries(payload, timeout, tries=3))


def ask_json(prompt, **kwargs):
    """Ask for a JSON reply and parse it. Raises ValueError if it isn't valid JSON."""
    text = ask(prompt, **kwargs)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in reply: {text[:300]}")
    return json.loads(text[start : end + 1])


def ask_with_image(prompt, image_path, model="muse-wonder-1.0", effort="low", timeout=180):
    """Send a prompt plus an image to a Muse vision model. Returns the reply text."""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = image_path.lower().rsplit(".", 1)[-1]
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"},
                ],
            }
        ],
        "stream": False,
        "reasoning": {"effort": effort},
    }
    return _extract_text(_post_with_retries(payload, timeout, tries=2))


if __name__ == "__main__":
    from edits import list_edits

    menu = "\n".join(f"- {eid}: {i['name']} ({i['why']})" for eid, i in list_edits().items())
    prompt = f"""You are a medicinal chemistry assistant.
The molecule is ibuprofen, SMILES CC(C)Cc1ccc(cc1)C(C)C(=O)O.
Its LogP is 3.07 (a bit high) and its QED is 0.822.
You may ONLY choose one edit from this menu:
{menu}

Reply with JSON only, no other text, in exactly this shape:
{{"edit_id": "<one id from the menu>", "rationale": "<two sentences>"}}"""

    t0 = time.time()
    result = ask_json(prompt)
    print(f"Took {time.time() - t0:.1f} seconds")
    print(json.dumps(result, indent=2))
    print("edit_id is on the menu:", result.get("edit_id") in list_edits())