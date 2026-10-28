"""
test_meta.py
A first, tiny call to Muse Spark. It only prints what comes back.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()  # reads your .env file

api_key = os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY")
if not api_key:
    raise SystemExit("No API key found. Check that backend/.env exists and has your key.")

url = "https://api.meta.ai/v1/responses"

payload = {
    "model": "muse-spark-1.3",
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "In two sentences, why do medicinal chemists try to keep LogP below 5?",
                }
            ],
        }
    ],
    "stream": False,
}

response = requests.post(
    url,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    },
    json=payload,
    timeout=60,
)

print("STATUS:", response.status_code)
try:
    print(json.dumps(response.json(), indent=2))
except Exception:
    print(response.text)