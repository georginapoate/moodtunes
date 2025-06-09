# backend/config.py
import os
from typing import Optional
from pydantic_settings import BaseSettings # Use pydantic-settings
from dotenv import load_dotenv

# Load .env file variables into environment
# Make sure your .env file is in the root of your 'moodtunes' project
# (i.e., same level as the 'backend' and 'frontend' folders)
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env") # Path to .env from config.py
load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    APP_NAME: str = "MoodTunes AI"
    API_V1_STR: str = "/api/v1"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Spotify
    SPOTIFY_CLIENT_ID: Optional[str] = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET: Optional[str] = os.getenv("SPOTIFY_CLIENT_SECRET")
    SPOTIFY_REDIRECT_URI: str = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/v1/spotify/callback")
    SPOTIFY_PLAYLIST_MAX_TRACKS: int = int(os.getenv("SPOTIFY_PLAYLIST_MAX_TRACKS", 25)) # Cast to int
    SPOTIFY_SCOPE: str = "playlist-modify-public playlist-modify-private user-library-read" # Add scope here

    # Last.fm
    LASTFM_API_KEY: Optional[str] = os.getenv("LASTFM_API_KEY")
    LASTFM_API_SECRET: Optional[str] = os.getenv("LASTFM_API_SECRET")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./moodtunes.db")
    
    class Config:
        # If your .env file is named something else or you want to specify its path explicitly
        # and the relative path above doesn't work well with uvicorn's CWD.
        # env_file = ".env"
        # env_file_encoding = "utf-8"
        pass

# Instantiate the settings
settings = Settings()

# You can add a check here to ensure critical keys are loaded
if not settings.OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY is not set in .env file or environment.")
if not settings.SPOTIFY_CLIENT_ID:
    print("WARNING: SPOTIFY_CLIENT_ID is not set.")
# Add more checks for other critical keys