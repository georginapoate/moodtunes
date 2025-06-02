import pylast
from ..config import settings
from typing import List, Dict, Any

network = pylast.LastFMNetwork(
    api_key=settings.LASTFM_API_KEY,
    api_secret=settings.LASTFM_API_SECRET
)

async def find_tracks_by_tags(tags: List[str], limit_per_tag: int = 5) -> List[Dict[str, Any]]:
    """
    Finds top tracks for a list of tags using Last.fm.
    Returns a list of dicts: [{"title": "Track Title", "artist": "Artist Name"}, ...]
    """
    all_tracks = []
    seen_tracks = set() # To avoid duplicates based on (title, artist)

    for tag_name in tags:
        try:
            tag = network.get_tag(tag_name)
            if not tag:
                print(f"Tag '{tag_name}' not found on Last.fm.")
                continue

            # pylast.Tag.get_top_tracks returns TopItem instances
            top_tracks_items = tag.get_top_tracks(limit=limit_per_tag)

            for item in top_tracks_items:
                track = item.item # This is a pylast.Track object
                track_title = track.title
                artist_name = track.artist.name
                track_identifier = (track_title.lower(), artist_name.lower())

                if track_identifier not in seen_tracks:
                    all_tracks.append({"title": track_title, "artist": artist_name, "source": "Last.fm"})
                    seen_tracks.add(track_identifier)

        except pylast.WSError as e:
            print(f"Last.fm API error for tag '{tag_name}': {e}")
        except Exception as e:
            print(f"An unexpected error occurred with tag '{tag_name}': {e}")
            # Potentially rate limit hit, or malformed response
            # Consider adding a small delay or backoff here if frequent.

    return all_tracks

# Example Usage (for testing this service directly)
# if __name__ == "__main__":
#     import asyncio
#     async def main():
#         sample_tags = ["chill", "electronic"]
#         tracks = await find_tracks_by_tags(sample_tags, limit_per_tag=3)
#         for track in tracks:
#             print(f"{track['title']} by {track['artist']}")
#     asyncio.run(main())