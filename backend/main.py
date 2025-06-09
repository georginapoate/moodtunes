# backend/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from .schemas import PromptRequest, PlaylistResponse, SpotifyAuthData
from .config import settings
from .services.openai_service import extract_music_tags_from_prompt
from .services.lastfm_service import find_tracks_by_tags as find_lastfm_tracks
from .services.ytmusic_service import search_ytmusic_for_tracks
from .services.spotify_service import (
    create_spotify_playlist_controller,
    get_spotify_auth_url,
    handle_spotify_callback_and_get_token,
    get_spotify_client_for_user_from_token_info, # If you store token_info
    SpotifyOAuthError # Import the specific error
)

import json # For potentially storing/retrieving token_info

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
        
        # VERY SIMPLIFIED token "storage" for single-developer testing.
        # DO NOT USE THIS IN PRODUCTION.
        # In production: Store token_info securely (e.g., encrypted in session, DB per user).
        # For this example, we'll write to a temporary file or rely on Spotipy's cache.
        # Spotipy's default cache path is often ./.cache-<username> or similar.
        # If handle_spotify_callback_and_get_token already caches it via SpotipyOAuth, this is redundant.
        print(f"Spotify token info obtained: {token_info}")
        # Let's assume SpotipyOAuth handles caching sufficiently for dev.
        
        # Redirect user back to frontend, perhaps with a success message or to a specific page
        # The frontend can then know that authentication was successful.
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
@app.post(f"{settings.API_V1_STR}/generate-playlist", response_model=PlaylistResponse, tags=["Playlist Generation"])
async def generate_playlist_endpoint(prompt_request: PromptRequest):
    """
    Generates a Spotify playlist based on a user's text prompt.
    """
    print(f"Received prompt: {prompt_request.prompt}")

    # Step 1: Analyze Prompt with OpenAI (or your local AI if you revert)
    try:
        extracted_tags = await extract_music_tags_from_prompt(prompt_request.prompt, max_tags=7)
        if not extracted_tags:
            print("OpenAI didn't return tags. This might be an issue or a very unspecific prompt.")
            # Decide on fallback: use raw prompt for YT, or error out
            # For now, let's proceed and see if Last.fm/YT can use an empty list or the raw prompt
    except Exception as e:
        print(f"Error calling OpenAI service: {e}")
        raise HTTPException(status_code=503, detail=f"AI service unavailable or failed: {str(e)}")
    
    print(f"OpenAI Extracted Tags: {extracted_tags}")

    # Step 2: Find Songs using Last.fm with extracted tags
    lastfm_tracks = []
    if extracted_tags: # Only query Last.fm if we have tags
        try:
            # Get more tracks from Last.fm initially to have a larger pool
            lastfm_tracks = await find_lastfm_tracks(extracted_tags, limit_per_tag=5, total_limit=30)
            print(f"Found {len(lastfm_tracks)} tracks from Last.fm.")
        except Exception as e:
            print(f"Error fetching from Last.fm: {e}") # Log error but continue

    # Step 3: Find Songs using YouTube Music (as fallback or augmentation)
    # Query YT Music with original prompt for broader context, or joined tags
    yt_query = prompt_request.prompt # Using original prompt can be effective for YT Music
    # Alternatively, if extracted_tags are good:
    # yt_query = " ".join(extracted_tags) + " music"
    
    yt_tracks = []
    try:
        # Get a decent number of YT tracks if Last.fm results are sparse or for variety
        yt_limit = 20 if not lastfm_tracks else 10 
        yt_tracks = await search_ytmusic_for_tracks(yt_query, limit=yt_limit)
        print(f"Found {len(yt_tracks)} tracks from YouTube Music.")
    except Exception as e:
        print(f"Error fetching from YouTube Music: {e}") # Log error but continue

    # Step 4: Combine and Deduplicate Tracks
    # Prioritize Last.fm tracks as they are more likely to be canonical artists/titles
    candidate_tracks_with_source = []
    for track in lastfm_tracks:
        candidate_tracks_with_source.append({**track, "source": "Last.fm"})
    for track in yt_tracks:
        candidate_tracks_with_source.append({**track, "source": "YouTube Music"})

    final_candidate_tracks = []
    seen_identifiers = set() # (normalized_title, normalized_artist)

    for track in candidate_tracks_with_source:
        title_norm = track.get("title", "").lower().strip()
        artist_norm = track.get("artist", "").lower().strip()
        
        if not title_norm or not artist_norm: # Skip tracks with missing info
            continue

        identifier = (title_norm, artist_norm)
        if identifier not in seen_identifiers:
            final_candidate_tracks.append({
                "title": track["title"], # Use original case for Spotify search
                "artist": track["artist"],
                "source": track["source"]
            })
            seen_identifiers.add(identifier)

    if not final_candidate_tracks:
        raise HTTPException(status_code=404, detail="No tracks found from Last.fm or YouTube Music for the given prompt.")

    # Limit total playlist size for Spotify
    tracks_for_playlist = final_candidate_tracks[:settings.SPOTIFY_PLAYLIST_MAX_TRACKS] # Add SPOTIFY_PLAYLIST_MAX_TRACKS to config
    print(f"Total unique candidate tracks for Spotify: {len(tracks_for_playlist)}")


    # Step 5 & 6: Create Spotify Playlist
    # This step requires the user to have authenticated with Spotify via the /spotify/login flow.
    # The spotify_service will attempt to use a cached token.
    try:
        playlist_url = await create_spotify_playlist_controller(
            tracks_info=tracks_for_playlist, # List of {"title": ..., "artist": ...}
            playlist_name=f"MoodTunes: {prompt_request.prompt[:30]}..."
            # access_token would be passed here in a multi-user app from their session
        )
        return PlaylistResponse(playlist_url=playlist_url, message="Playlist created successfully!")
    except SpotifyOAuthError as e:
        # This error means Spotipy couldn't get a token (e.g., not logged in, cache expired, scope issue)
        print(f"Spotify OAuth Error during playlist creation: {e}")
        # Frontend should interpret this as "user needs to log in to Spotify"
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

# --- (Optional) Load any startup data or models ---
# For example, if you were using the local Moodify CSV:
# from .services.moodify_service import load_moodify_dataset
# @app.on_event("startup")
# async def startup_event():
#     print("Application startup: Loading necessary data...")
#     load_moodify_dataset() # If you were using it
#     print("Startup data loading complete.")