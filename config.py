import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not all([GITHUB_TOKEN, GROQ_API_KEY, WEBHOOK_SECRET]):
    raise ValueError("Missing env vars. Check your .env file.")