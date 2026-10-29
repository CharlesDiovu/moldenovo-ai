"""
sam_client.py
Finds structures in a figure with SAM 3.1 and cuts each one out.
"""

import os
import re
import json
import statistics
import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

BOX = re.compile(
    r"<\|box;x1=([\d.]+);y1=([\d.]+);x2=([\d.]+);y2=([\d.]+);w=([\d.]+);h=([\d.]+)\|>"
)


def _key():
    key = os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY")
    if not key:
        raise RuntimeError("No API key found in backend/.env")
    return key


def find_structures(image_path, phrase="chemical structure"):
    """Return a list of (left, top, right, bottom) boxes in reading order."""
    ext = image_path.lower().rsplit(".", 1)[-1]
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    key = _key()

    with open(image_path, "rb") as f:
        up = requests.post(
            "https://api.meta.ai/v1/files",
            headers={"Authorization": f"Bearer {key}"},
            data={"purpose": "user_data"},
            files={"file": (os.path.basename(image_path), f, mime)},
            timeout=120,
        )
    if up.status_code != 200:
        raise RuntimeError(f"File upload failed {up.status_code}: {up.text[:300]}")
    file_id = up.json().get("id")

    payload = {
        "model": "sam-3.1",
        "input": [{
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": phrase},
                {"type": "input_image", "file_id": file_id},
            ],
        }],
        "stream": True,
        "metadata": {"mask_encoding": "lossless"},
    }

    final_text = None
    with requests.post(
        "https://api.meta.ai/v1/responses",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        json=payload,
        stream=True,
        timeout=180,
    ) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"SAM call failed {resp.status_code}: {resp.text[:300]}")
        for line in resp.iter_lines():
            if not line.startswith(b"data: "):
                continue
            data = line[6:].decode("utf-8", errors="replace")
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
            except Exception:
                continue
            if event.get("type") == "response.completed":
                for item in event["response"].get("output", []):
                    for block in item.get("content", []):
                        if block.get("type") == "output_text":
                            final_text = block["text"]

    if not final_text:
        return []

    img = Image.open(image_path)
    boxes = []
    for m in BOX.finditer(final_text):
        x1, y1, x2, y2, w, h = (float(v) for v in m.groups())
        sx, sy = img.width / w, img.height / h
        boxes.append((x1 * sx, y1 * sy, x2 * sx, y2 * sy))

    # Reading order: group into rows by vertical position, then left to right.
    if boxes:
        row_height = statistics.median(b[3] - b[1] for b in boxes)
        boxes.sort(key=lambda b: (round(((b[1] + b[3]) / 2) / row_height), b[0]))
    return boxes


def crop_structures(image_path, boxes, pad=25):
    """Cut each box out of the image, with a margin so labels are not clipped."""
    img = Image.open(image_path).convert("RGB")
    crops = []
    for left, top, right, bottom in boxes:
        crops.append(img.crop((
            max(0, left - pad), max(0, top - pad),
            min(img.width, right + pad), min(img.height, bottom + pad),
        )))
    return crops