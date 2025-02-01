from dotenv import load_dotenv
load_dotenv()  # Load the .env file first

import openai
import os

api_key = os.getenv("OPENAI_API_KEY", "")
print("Using API key:", api_key[:4] + "..." + api_key[-4:])

openai.api_key = api_key

try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=10
    )
    print("Success:", response)
except Exception as e:
    print("Error:", e)
