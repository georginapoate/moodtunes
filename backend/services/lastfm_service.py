import pylast
from ..config import settings
from typing import List, Dict, Any

network = pylast.LastFMNetwork(
    api_key=settings.LASTFM_API_KEY,
    api_secret=settings.LASTFM_API_SECRET
)

# backend/services/lastfm_service.py
import pylast
from ..config import settings
from typing import List, Optional, Dict, Any
import asyncio

# ... (network initialization as before) ...

async def get_tags_for_track(title: str, artist: str) -> List[str]:
    """
    Fetches top tags for a specific track from Last.fm.
    """
    if not network:
        print("Last.fm network not initialized.")
        return []

    try:
        # pylast methods are synchronous, run them in a thread
        track_obj = await asyncio.to_thread(network.get_track, artist, title)
        if not track_obj:
            print(f"Last.fm: Track '{title}' by '{artist}' not found.")
            return []

        top_tags_items = await asyncio.to_thread(track_obj.get_top_tags, limit=5) # Get top 5 tags
        
        tags = [tag_item.item.name.lower() for tag_item in top_tags_items if hasattr(tag_item, 'item') and hasattr(tag_item.item, 'name')]
        
        # print(f"Last.fm: Tags for '{title}' by '{artist}': {tags}")
        return tags
    except pylast.WSError as e:
        # Common errors: "Track not found" (code 6), "Artist not found"
        if e.status == '6': # Error 6 often means "not found"
            print(f"Last.fm: Track or artist not found for '{title}' by '{artist}'. Details: {e.details}")
        else:
            print(f"Last.fm API WSError for '{title}' by '{artist}': {e}")
        return []
    except Exception as e:
        print(f"Unexpected error fetching tags from Last.fm for '{title}' by '{artist}': {e}")
        return []
