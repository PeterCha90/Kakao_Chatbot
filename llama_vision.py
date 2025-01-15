import json
import ollama
import base64
import requests

from PIL import Image
from pprint import pprint

from dateutil import parser

OCR_PROMPT = """Act as an OCR assistant. Analyze the provided image and:
1. Recognize all visible text in the image as accurately as possible.
2. Maintain the original structure and formatting of the text.
3. If any words or phrases are unclear, indicate this with [unclear] in your transcription.
Provide only the transcription without any additional comments."""

CHAT_PROMPT = """The following conversation contains a customer's order for a specific product. 
Please summarize the conversation and provide a response in JSON format according following rules:
1. store the customer's name with the key 'customer'
2. store the ordered product with the key 'item'
3. store the order quantity with the key 'count'.
4. store all the orders of customers as a list of order objects.
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
    ocr_res = ollama.chat(
        model='llama3.2-vision',
        messages=[{
            "role": "user",
            "content": OCR_PROMPT,
            "images": [base64_image],
        }],
        # Set temperature to 0 for more deterministic output
        options={'temperature': 0},
    )
    # parsing the data
    date = parser.isoparse(ocr_res['created_at']).date()
    ocr_result = json.loads(ocr_res.model_dump_json())
    ocr_content = ocr_result['message']['content']

    print("===========================")
    print(date)
    pprint(ocr_content)
    print("===========================")
    # 소요시간을 초단위로 계산
    chat_res = ollama.chat(
        model='phi4',
        messages=[{
            "role": "user",
            "content": CHAT_PROMPT + f"\n{ocr_content}",
        }],
        # Set temperature to 0 for more deterministic output
        options={'temperature': 0},
    )
    chat_result = json.loads(chat_res.model_dump_json())
    chat_content = chat_result['message']['content']
    print("===========================")
    pprint(chat_content)
    print("===========================")

    return date, chat_res
