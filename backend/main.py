from fastapi import FastAPI, HTTPException
from .schemas import PromptRequest, PlaylistResponse
from .services.ai_service import predict_tags_from_prompt # We'll create this
from .services.lastfm_service import find_tracks_by_tags as find_lastfm_tracks
from .services.ytmusic_service import search_ytmusic_for_tracks
from .services.spotify_service import create_spotify_playlist_from_tracks
from .config import settings

app = FastAPI(title=settings.APP_NAME)

# This will be implemented later
# from .services.spotify_service import sp_oauth, get_spotify_client

# @app.get(settings.SPOTIFY_REDIRECT_URI.replace(settings.API_V1_STR, "")) # If backend handles callback
# async def spotify_callback(code: str):
#     # Handle Spotify OAuth callback
#     # This is a simplified placeholder; actual implementation is more involved
#     token_info = sp_oauth.get_access_token(code)
#     # Store token_info securely (e.g., session, database per user)
#     return {"message": "Spotify authentication successful. You can now create playlists."}


@app.post(f"{settings.API_V1_STR}/generate-playlist", response_model=PlaylistResponse)
async def generate_playlist_endpoint(request: PromptRequest):
    # Step 2: Predict Tags
    predicted_tags = await predict_tags_from_prompt(request.prompt)
    if not predicted_tags:
        raise HTTPException(status_code=400, detail="Could not predict tags from prompt.")

    # Step 3 & 4: Find Songs
    lastfm_tracks = await find_lastfm_tracks(predicted_tags, limit_per_tag=5)
    yt_query_tags = " ".join(predicted_tags[:3]) # Use top 3 tags for YT Music search
    yt_tracks = await search_ytmusic_for_tracks(yt_query_tags, limit=10)

    # Combine and deduplicate (simple deduplication by title)
    candidate_tracks = []
    seen_titles = set()
    for track in lastfm_tracks + yt_tracks: # Prioritize Last.fm or mix as you see fit
        # Normalize title for better deduplication if needed
        if track['title'].lower() not in seen_titles:
            candidate_tracks.append(track)
            seen_titles.add(track['title'].lower())

    if not candidate_tracks:
        raise HTTPException(status_code=404, detail="No tracks found for the predicted tags.")

    # For simplicity, let's limit to N tracks for the playlist
    final_tracks_for_playlist = candidate_tracks[:20] # Max 20 songs

    # Step 5 & 6: Create Spotify Playlist
    # Spotify auth needs to be handled. For now, assume a pre-authenticated client for backend testing.
    # In a real app, you'd redirect the user through Spotify's OAuth flow first.
    # This example will require SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI to be set
    # in environment for user-specific playlist creation.
    try:
        # This function will need to handle auth if not already done
        playlist_url = await create_spotify_playlist_from_tracks(
            tracks=final_tracks_for_playlist,
            playlist_name=f"MoodTunes: {request.prompt[:30]}"
        )
        return PlaylistResponse(playlist_url=playlist_url, message="Playlist created successfully!")
    except Exception as e:
        # Catch specific Spotify exceptions later
        raise HTTPException(status_code=500, detail=f"Failed to create Spotify playlist: {str(e)}")

# Placeholder for AI service integration
# backend/services/ai_service.py
async def predict_tags_from_prompt(prompt: str) -> list[str]:
    # This will call the actual AI model
    # For now, mock it
    print(f"AI Service: Predicting tags for prompt: '{prompt}'")
    # In reality, call ai.tag_predictor.predict(prompt)
    # Example:
    # if "sad" in prompt.lower(): return ["sad", "mellow", "ballad"]
    # if "happy" in prompt.lower(): return ["happy", "upbeat", "pop"]
    # return ["electronic", "dance"] # Default mock
    # This will be replaced by the actual model call
    from ai.tag_predictor import predictor # Assuming predictor is an instance
    tags = predictor.predict(prompt)
    return tags