from dotenv import load_dotenv
import os

# Load environment variables from a .env file at project root.
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY is not set in the environment.")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
