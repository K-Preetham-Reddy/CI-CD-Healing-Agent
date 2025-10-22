from dotenv import load_dotenv
import os

load_dotenv()
class Settings:
    GITHUB_TOKEN=os.getenv("GITHUB_TOKEN")
    ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY")

settings=Settings()