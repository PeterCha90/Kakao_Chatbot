import json
import ollama
import base64
import requests

from PIL import Image
from pprint import pprint

from dateutil import parser

from utils import extract_json_str

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


def encode_image_to_base64(image_path, url=True):
    try:
        if url:
            """Convert an image from a URL to a base64 encoded string."""
            response = requests.get(image_path)
            if response.status_code == 200:
                return base64.b64encode(response.content).decode('utf-8')
        else:
            """Convert an image from a local file path to a base64 encoded string."""
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        raise Exception(
            f"Failed to retrieve image: {e}")


def perform_ocr(image_path, url=True):
    """Perform OCR on the given image using Llama 3.2-Vision."""
    base64_image = encode_image_to_base64(image_path, url)
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
    ocr_result = json.loads(ocr_res.model_dump_json())
    ocr_content = ocr_result['message']['content']

    # phi4 chat model to get the final result.
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
    json_data = json.loads(extract_json_str(chat_content))
    return json_data


if __name__ == "__main__":
    image_path = "/Users/peter/Downloads/test.jpeg"
    perform_ocr(image_path, False)
