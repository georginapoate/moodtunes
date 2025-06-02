from ytmusicapi import YTMusic
from typing import List, Dict, Any

# Initialize anonymous client
try:
    ytmusic = YTMusic()
except Exception as e:
    print(f"Failed to initialize YTMusic (anonymous): {e}")
    ytmusic = None # Allow app to run but this service will fail gracefully

# For authenticated client (if needed later):
# try:
#     ytmusic = YTMusic(settings.YTMUSIC_HEADERS_JSON)
# except Exception as e:
#     print(f"Failed to initialize YTMusic (authenticated): {e}")
#     # Fallback to anonymous if auth fails
#     try:
#         ytmusic = YTMusic()
#     except Exception as e_anon:
#         print(f"Failed to initialize YTMusic (anonymous fallback): {e_anon}")
#         ytmusic = None


async def search_ytmusic_for_tracks(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches YouTube Music for tracks based on a query.
    Returns a list of dicts: [{"title": "Track Title", "artist": "Artist Name"}, ...]
    """
    if not ytmusic:
        print("YTMusic client not initialized. Skipping YouTube Music search.")
        return []

    tracks_found = []
    try:
        # We are primarily interested in songs.
        search_results = ytmusic.search(query=query, filter="songs", limit=limit)

        for item in search_results:
            if item.get('category') == 'Songs' or item.get('resultType') == 'song': # Check for different API versions/responses
                title = item.get('title')
                artists = item.get('artists') # This is usually a list of dicts
                duration_seconds = item.get('duration_seconds') # Useful for filtering very short/long tracks

                if title and artists:
                    # Take the first artist as primary, or join names
                    artist_name = artists[0].get('name', 'Unknown Artist')
                    if len(artists) > 1:
                        # You might want to join all artist names:
                        # artist_name = ", ".join([a.get('name', '') for a in artists])
                        pass # For simplicity, using first artist

                    tracks_found.append({
                        "title": title,
                        "artist": artist_name,
                        "duration_seconds": duration_seconds, # Store for potential filtering
                        "source": "YouTube Music"
                    })
    except Exception as e:
        print(f"Error searching YouTube Music for '{query}': {e}")
        # This can happen due to API changes, network issues, etc.

    return tracks_found

# Example Usage (for testing this service directly)
# if __name__ == "__main__":
#     import asyncio
#     async def main():
#         query_term = "upbeat electronic"
#         tracks = await search_ytmusic_for_tracks(query_term, limit=5)
#         for track in tracks:
#             print(f"{track['title']} by {track['artist']} (Duration: {track.get('duration_seconds', 'N/A')}s)")
#     asyncio.run(main())