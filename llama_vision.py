import base64
import requests

from PIL import Image
from pprint import pprint
# from langchain_community.chat_models import ChatOllama
# from langchain_ollama import ChatOllama
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.prompts import ChatPromptTemplate


# # LangChain이 지원하는 다른 채팅 모델을 사용합니다. 여기서는 Ollama를 사용합니다.
# llm = ChatOllama(model="llama-vision:4Q")

# # 프롬프트 설정
# prompt = ChatPromptTemplate.from_template("{topic} 에 대하여 간략히 설명해 줘.")

# # LangChain 표현식 언어 체인 구문을 사용합니다.
# chain = prompt | llm | StrOutputParser()


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
    """Perform OCR on the given image using Llama 3.2-Vision."""
    base64_image = encode_image_to_base64(image_path)
    response = requests.post(
        # Ensure this URL matches your Ollama service endpoint
        "http://localhost:11434/api/chat",
        json={
            "model": "llama3.2-vision",
            "messages": [
                {
                    "role": "user",
                    "content": SYSTEM_PROMPT,
                    "images": [base64_image],
                },
            ],
        }
    )
    if response.status_code == 200:
        print("===========================")
        pprint(response.json())
        pprint(response.content)
        print("===========================")
        return response.json()
    else:
        print("Error:", response.status_code, response.text)
        return None
