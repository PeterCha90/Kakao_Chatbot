import json
import ollama
import base64
import requests

from PIL import Image
from pprint import pprint

from dateutil import parser

SYSTEM_PROMPT = """Act as an OCR assistant. Analyze the provided image and:
1. Recognize all visible text in the image as accurately as possible.
2. Maintain the original structure and formatting of the text.
3. If any words or phrases are unclear, indicate this with [unclear] in your transcription.
Provide only the transcription without any additional comments."""


def encode_image_to_base64(image_url):
    """Convert an image from a URL to a base64 encoded string."""
    response = requests.get(image_url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode('utf-8')
    else:
        raise Exception(
            f"Failed to retrieve image. Status code: {response.status_code}")


def perform_ocr(image_path):
    # 시작 시간
    """Perform OCR on the given image using Llama 3.2-Vision."""
    base64_image = encode_image_to_base64(image_path)
    response = ollama.chat(
        model='llama3.2-vision',
        messages=[{
            "role": "user",
            "content": SYSTEM_PROMPT,
            "images": [base64_image],
        }],
        # Set temperature to 0 for more deterministic output
        options={'temperature': 0},
    )
    result = json.loads(response.model_dump_json())
    date = parser.isoparse(result['created_at']).date()
    print("===========================")
    print(date)
    pprint(result['message']['content'])
    print("===========================")
    # 소요시간을 초단위로 계산

    return None
