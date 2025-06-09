# backend/main.py
import json
from venv import create
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orms import Session

from . import crud, models, schemas
from .database import SessionLocal, engine, create_db_and_tables, get_db

from .schemas import PromptRequest, PlaylistResponse, SpotifyAuthData
from .config import settings

from .services.openai_service import get_song_recommendations_from_openai
from .services.openai_service import extract_music_tags_from_prompt
from .services.lastfm_service import get_tags_for_track

from .services.spotify_service import (
    create_spotify_playlist_from_tracks,
    get_spotify_auth_url,
    handle_spotify_callback_and_get_token,
    SpotifyOAuthError
)

create_db_and_tables()  # Ensure database and tables are created at startup

# --- FastAPI App Initialization ---
app = FastAPI(
    title=settings.APP_NAME,
    description="MoodTunes API: Turn text prompts into Spotify playlists.",
    version="0.1.0"
)

# --- CORS Middleware ---
# Allows your React frontend (running on localhost:3000) to talk to this backend
origins = [
    "http://localhost:3000", # Default React dev server
    # Add other origins if needed (e.g., your deployed frontend URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Important for cookies or auth headers if you use them
    allow_methods=["*"],    # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],    # Allows all headers
)

# todo:
# --- Spotify Authentication Endpoints (Simplified for Dev) ---
# In a real app, you'd store tokens securely (e.g., in a database linked to users or secure session)
# For now, this uses a simple file cache or relies on Spotipy's default caching.

@app.get(f"{settings.API_V1_STR}/spotify/login", tags=["Spotify Auth"])
async def spotify_login():
    """
    Redirects the user to Spotify for authentication.
    """
    try:
        auth_url = get_spotify_auth_url()
        return RedirectResponse(auth_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not generate Spotify auth URL: {str(e)}")

@app.get(settings.SPOTIFY_REDIRECT_URI.replace(settings.API_V1_STR, ""), tags=["Spotify Auth"]) # Path must match exactly
async def spotify_callback(code: str, request: Request): # FastAPI automatically gets 'code' from query params
    """
    Handles the callback from Spotify after user authentication.
    Exchanges the authorization code for an access token.
    For demo, stores token in a simple way (NOT production-ready).
    """
    try:
        token_info = await handle_spotify_callback_and_get_token(code)
        # DO NOT USE THIS IN PRODUCTION.
        # In production: Store token_info securely (e.g., encrypted in session, DB per user).
        print(f"Spotify token info obtained: {token_info}")
        frontend_redirect_url = "http://localhost:3000/auth-success" # Example
        return RedirectResponse(f"{frontend_redirect_url}?status=spotify_auth_success")

    except SpotifyOAuthError as e:
        raise HTTPException(status_code=400, detail=f"Spotify OAuth Error: {str(e)}")
    except Exception as e:
        print(f"Error in Spotify callback: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing Spotify callback: {str(e)}")


# --- Core Playlist Generation Endpoint ---
@app.post(f"{settings.API_V1_STR}/generate-playlist", response_model=schemas.PlaylistResponse, tags=["Playlist Generation"])
async def generate_playlist_endpoint(
    prompt_request: PromptRequest,
    db: Session = Depends(get_db)
):
    print(f"Received prompt: {prompt_request.prompt}")
    db_prompt = crud.create_prompt(db, prompt_request.prompt)
    if not db_prompt:
        db_prompt = crud.get_prompt_by_text(db, prompt_request.prompt)

    try:
        openai_recommended_song = await get_song_recommendations_from_openai(
            prompt_request.prompt,
            max_songs=settings.SPOTIFY_PLAYLIST_MAX_TRACKS + 5)
        if not openai_recommended_song:
            raise HTTPException(status_code=404, detail="OpenAI could not recommend any songs for this prompt.")
    except ValueError as ve:
        raise HTTPException(status_code=503, detail=f"OpenAI error: {str(ve)}")
    except Exception as e:
        print(f"Error calling OpenAI service: {e}")
        raise HTTPException(status_code=503, detail=f"AI service unavailable or failed: {str(e)}")
    
    print(f"OpenAI recommended the following Songs: {openai_recommended_song}")

    final_list_for_spotify = []
    song_details_for_fe = []

    processed_song_identifiers = set() # set for avoiding duplicates

    for song in openai_recommended_song:
        title = song.get("title")
        artist = song.get("artist")
        if not title or not artist:
            print(f"Skipping song with missing title/artist: {song}")
            continue
        
        # Check for duplicates based on title and artist
        identifier = f"{title.lower()} - {artist.lower()}"
        if identifier in processed_song_identifiers:
            print(f"Skipping duplicate song: {title} by {artist}")
            continue
        
        processed_song_identifiers.add(identifier)
        db_song = crud.get_or_create_song(db, title=title, artist=artist)
        crud.link_prompt_to_song_with_source(db, prompt_id=db_prompt.id, song_id=db_song.id, source="openai")

        # get tags for each song using Last.fm
        await asyncio.sleep(0.1)  # Small delay to avoid rate limiting
        lfm_tags = await get_tags_for_track(title, artist)
        if lfm_tags:
            crud.add_tags_to_song(db, db_song, lfm_tags)
            print(f"Added tags {lfm_tags} to song {title} by {artist}")
        else:
            print(f"No tags found for {title} by {artist}, skipping.")
        
        final_list_for_spotify.append({
            "title": title,
            "artist": artist,
        })
        song_details_for_fe.append({
            "title": title,
            "artist": artist,
            "tags": lfm_tags  # Include tags for the song
        })

        if len(final_list_for_spotify) >= settings.SPOTIFY_PLAYLIST_MAX_TRACKS:
            break
        
    if not final_list_for_spotify:
        raise HTTPException(status_code=404, detail="No valid songs processed for playlist creation.")

    # Creating the Spotify Playlist
    try:
        playlist_url = await create_spotify_playlist_from_tracks(
            tracks_info=final_list_for_spotify, 
            playlist_name=f"MoodTunes: {prompt_request.prompt[:30]}..."
            # access_token would be passed here in a multi-user app from their session
        )
        return PlaylistResponse(
            playlist_url=playlist_url,
            message="Awesome playlist created successfully!",
            songs=song_details_for_fe
            )
    except SpotifyOAuthError as e:
        print(f"Spotify OAuth Error during playlist creation: {e}")
        raise HTTPException(
            status_code=401, # Unauthorized
            detail=f"Spotify authentication required or token invalid. Please login via /api/v1/spotify/login. Error: {str(e)}"
        )
    except Exception as e:
        print(f"Failed to create Spotify playlist: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create Spotify playlist: {str(e)}")

# --- Health Check Endpoint ---
@app.get("/health", tags=["Utilities"])
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok", "message": "MoodTunes API is running!"}