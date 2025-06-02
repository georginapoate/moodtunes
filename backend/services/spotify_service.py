# backend/services/spotify_service.py
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from ..config import settings
from typing import List, Dict, Any

# This scope allows creating public and private playlists and modifying them.
# Also allows reading user's library to check if song is already saved (optional).
SPOTIFY_SCOPE = "playlist-modify-public playlist-modify-private user-library-read"

# Initialize SpotifyOAuth.
# In a real web app, the user would be redirected to Spotify to authorize.
# The token would then be stored (e.g., in a session or database associated with the user).
# For this backend-only example, it might try to use a cached token or prompt on console
# if run directly, but for FastAPI, a proper OAuth flow is needed.

# One way to handle auth in FastAPI:
# 1. Frontend has a "Login with Spotify" button.
# 2. This button links to a backend endpoint (e.g., /login/spotify).
# 3. This backend endpoint generates sp_oauth.get_authorize_url() and redirects the user.
# 4. User authorizes on Spotify, gets redirected back to your SPOTIFY_REDIRECT_URI (e.g., /callback).
# 5. The /callback endpoint receives an auth code, uses sp_oauth.get_access_token(code).
# 6. Store this token (access_token, refresh_token, expires_at) securely, associated with the user.
# 7. When creating a playlist, retrieve the user's token and initialize Spotipy with it.

# For simplicity in this initial setup, we'll rely on Spotipy's default behavior
# which might cache tokens locally or use environment variables if set (SPOTIPY_CLIENT_ID, etc.)
# This is NOT suitable for a multi-user web app without further adaptation.

# A global Spotipy client instance using Client Credentials flow (for searching, not user-specific actions)
# sp_search_client = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=settings.SPOTIFY_CLIENT_ID,
#                                                               client_secret=settings.SPOTIFY_CLIENT_SECRET))
# However, playlist creation REQUIRES user authorization.

def get_spotify_client_for_user(access_token: str = None) -> spotipy.Spotify:
    """
    Returns a Spotipy client.
    If access_token is provided, uses it.
    Otherwise, attempts to use SpotifyOAuth (which might require user interaction or cached token).
    THIS IS A SIMPLIFIED AUTH HANDLING.
    """
    if access_token:
        return spotipy.Spotify(auth=access_token)
    else:
        # This will try to use cached token or prompt if run interactively.
        # For a web server, you need a proper OAuth flow where the token is obtained
        # via browser redirection and then passed to this function.
        auth_manager = SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE,
            # cache_path=".spotify_cache" # Useful for local dev, add .spotify_cache to .gitignore
        )
        # Try to get a cached token
        token_info = auth_manager.get_cached_token()
        if not token_info:
            # This part is problematic for a non-interactive server.
            # You'd typically redirect the user to auth_manager.get_authorize_url()
            # For now, we'll let it fail if no token is cached and no access_token is passed.
            # This indicates the user needs to go through the OAuth flow.
            raise SpotifyOauthError("No cached Spotify token. User needs to authenticate.")

        # Refresh token if needed
        if auth_manager.is_token_expired(token_info):
            token_info = auth_manager.refresh_access_token(token_info['refresh_token'])

        return spotipy.Spotify(auth=token_info['access_token'])


async def map_tracks_to_spotify_ids(sp: spotipy.Spotify, tracks: List[Dict[str, Any]], limit_per_search=1) -> List[str]:
    """
    Maps a list of {"title": ..., "artist": ...} to Spotify Track IDs.
    """
    track_ids = []
    for track_info in tracks:
        title = track_info['title']
        artist = track_info['artist']
        query = f"track:{title} artist:{artist}"
        try:
            results = sp.search(q=query, type="track", limit=limit_per_search)
            items = results['tracks']['items']
            if items:
                # Take the first result (most relevant by Spotify's search)
                track_ids.append(items[0]['id'])
                print(f"Found Spotify ID for: {title} - {artist} -> {items[0]['id']}")
            else:
                print(f"Could not find Spotify ID for: {title} - {artist}")
        except spotipy.SpotifyException as e:
            print(f"Spotify API error while searching for '{query}': {e}")
        except Exception as e:
            print(f"Unexpected error searching Spotify for '{query}': {e}")
    return track_ids


async def create_spotify_playlist_from_tracks(
    tracks: List[Dict[str, Any]],
    playlist_name: str = "MoodTunes Generated Playlist",
    # access_token: str = None # Pass user's access token here
) -> str:
    """
    Creates a Spotify playlist from a list of track titles and artists.
    Returns the URL of the created playlist.
    `tracks` is a list of dicts: [{"title": "Track Title", "artist": "Artist Name"}, ...]
    This function needs to handle Spotify authentication for the user.
    """
    try:
        # IMPORTANT: In a real app, get_spotify_client_for_user() would need
        # the user's specific access_token obtained via OAuth.
        # For now, it relies on cached token or environment variables for Spotipy.
        sp = get_spotify_client_for_user() # Pass access_token if available
    except SpotifyOauthError as e:
        # This means the user needs to authenticate. The main API endpoint
        # should handle this by initiating the OAuth flow.
        # e.g., return an error instructing frontend to redirect to Spotify login.
        print(f"Spotify Auth Error: {e}")
        raise Exception("Spotify authentication required. Please log in with Spotify.") from e


    user_profile = sp.current_user()
    if not user_profile:
        raise Exception("Could not get Spotify user profile. Authentication might have failed.")
    user_id = user_profile['id']

    spotify_track_ids = await map_tracks_to_spotify_ids(sp, tracks, limit_per_search=1)

    if not spotify_track_ids:
        raise Exception("No tracks could be mapped to Spotify IDs.")

    # Spotify API limits adding 100 items at a time
    valid_track_ids = [tid for tid in spotify_track_ids if tid] # Filter out None if any
    if not valid_track_ids:
        raise Exception("No valid Spotify Track IDs found to add to playlist.")

    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True) # Or public=False
    playlist_id = playlist['id']
    playlist_url = playlist['external_urls']['spotify']

    # Add tracks in chunks of 100
    for i in range(0, len(valid_track_ids), 100):
        chunk = valid_track_ids[i:i + 100]
        sp.playlist_add_items(playlist_id, chunk)

    print(f"Playlist '{playlist_name}' created successfully: {playlist_url}")
    return playlist_url

# To test this service (requires Spotify credentials set up for Spotipy to find, or cached token):
# if __name__ == "__main__":
#     import asyncio
#     async def main_spotify_test():
#         sample_tracks_to_create = [
#             {"title": "Bohemian Rhapsody", "artist": "Queen"},
#             {"title": "Stairway to Heaven", "artist": "Led Zeppelin"},
#             {"title": "Hotel California", "artist": "Eagles"},
#             {"title": "NonExistent Song XYZ", "artist": "Unknown Artist ABC"} # Test non-match
#         ]
#         try:
#             # In a real app, you'd get the access_token after user logs in via OAuth
#             # and pass it to create_spotify_playlist_from_tracks
#             # For this direct test, get_spotify_client_for_user() will try to use cached token
#             # or env vars. You might be prompted to authenticate in the browser the first time.
#             url = await create_spotify_playlist_from_tracks(
#                 tracks=sample_tracks_to_create,
#                 playlist_name="Test MoodTunes Playlist"
#             )
#             print(f"Playlist created: {url}")
#         except Exception as e: 
#             print(f"Error in Spotify test: {e}")
#             print("Ensure SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI are set in your environment,")
#             print("or you have a cached token (run a simple Spotipy script once to authenticate via browser).")
#             print("The redirect URI for CLI testing can be http://localhost:8888/callback or similar.")

#     asyncio.run(main_spotify_test())