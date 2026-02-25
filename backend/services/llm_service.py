from dotenv import load_dotenv
import os

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# API keys from .env
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# --- OpenRouter LLM ---
openrouter_llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0.1,
    max_tokens=2048,  # Reduced from 4096 for faster responses
)


# --- OpenAI LLM ---
openai_llm = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_key=OPENAI_API_KEY,
    temperature=0.1,
    max_tokens=2048,  # Reduced from 4096 for faster responses
)


# --- Gemini LLM ---
gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",  # Faster experimental model
    google_api_key=GEMINI_API_KEY,
    temperature=0.1,
    max_output_tokens=8192,  # Reduced from 16384
)

def generate_response(prompt: str) -> str:
    response = gemini_llm.invoke(prompt)
    return response.content
