# test_openrouter_key.py

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env
load_dotenv()





api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found in .env")

# OpenRouter client
client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)

try:
    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "user", "content": "which moddel you are?"}
        ],
        max_tokens=10,
        temperature=0
    )

    print("API key valid.")
    print("Response:", response.choices[0].message.content)

except Exception as e:
    print("API key test failed.")
    print(str(e))