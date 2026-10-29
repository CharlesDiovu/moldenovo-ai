"""
parse_sam.py
Reads the saved SAM reply (sam_raw.jsonl), finds the boxes, draws them on the
image, and saves each boxed region as its own cropped picture.
Makes NO calls to Meta, so it costs nothing.
"""

import os
import re
import sys
import json
from PIL import Image, ImageDraw

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "test_figure.jpg"

# 1. Find the final text inside the saved reply
final_text = None
with open("sam_raw.jsonl", encoding="utf-8") as f:
    for line in f:
        try:
            event = json.loads(line)
        except Exception:
            continue
        if event.get("type") == "response.completed":
            for item in event["response"]["output"]:
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        final_text = block["text"]

if final_text is None:
    raise SystemExit("Could not find the final text in sam_raw.jsonl")

print("Reply text length:", len(final_text), "characters")

# 2. Show the structure of the reply with the huge mask data removed
stripped = re.sub(r"<\|mask;.*?\|>", "<|mask...|>", final_text, flags=re.DOTALL)
print("\nReply with mask data removed (first 1500 characters):")
print(stripped[:1500])

# 3. Find every box
BOX = re.compile(
    r"<\|box;x1=([\d.]+);y1=([\d.]+);x2=([\d.]+);y2=([\d.]+);w=([\d.]+);h=([\d.]+)\|>"
)
boxes = [tuple(float(v) for v in m.groups()) for m in BOX.finditer(final_text)]
print(f"\nBoxes found: {len(boxes)}")

# 4. Draw the boxes and save each crop
original = Image.open(IMAGE).convert("RGB")
print("Image size:", original.size)
canvas = original.copy()
draw = ImageDraw.Draw(canvas)
os.makedirs("crops", exist_ok=True)

for i, (x1, y1, x2, y2, w, h) in enumerate(boxes):
    sx, sy = original.width / w, original.height / h
    left, top, right, bottom = x1 * sx, y1 * sy, x2 * sx, y2 * sy
    print(f"  box {i}: ({left:.0f}, {top:.0f}) to ({right:.0f}, {bottom:.0f})")

    pad = 25
    crop = original.crop((
        max(0, left - pad), max(0, top - pad),
        min(original.width, right + pad), min(original.height, bottom + pad),
    ))
    crop.save(f"crops/crop_{i}.png")

    draw.rectangle((left, top, right, bottom), outline="red", width=3)
    draw.text((left + 4, top + 4), str(i), fill="red")

canvas.save("sam_boxes.png")
print("\nSaved sam_boxes.png and the crops folder.")