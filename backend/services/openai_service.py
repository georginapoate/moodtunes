# backend/services/openai_service.py
import openai
from ..config import settings
from typing import List, Optional
import re # For parsing

# ... (OpenAI API key setup as before) ...

async def get_song_recommendations_from_openai(prompt: str, max_songs: int = 10) -> Optional[List[Dict[str, str]]]:
    """
    Uses OpenAI's ChatCompletion to get song recommendations (title and artist)
    based on a user prompt.
    Returns a list of dicts: [{"title": "...", "artist": "..."}, ...]
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API key is not configured.")

    system_prompt = f"""
    You are an expert music curator for an application called MoodTunes.
    Given a user's text prompt describing a mood, vibe, or desired music, your task is to recommend a list of songs.
    Return a list of up to {max_songs} songs.
    Format EACH song as "Track Title by Artist Name", with each song on a new line.
    Do NOT include numbering, bullet points, or any other text before or after the list.
    Only provide the song list.

    Example user prompt: "energetic 80s synthpop for dancing"
    Your response should be ONLY:
    Take on Me by a-ha
    Girls Just Want to Have Fun by Cyndi Lauper
    Blue Monday by New Order

    Example user prompt: "sad rainy day acoustic guitar"
    Your response should be ONLY:
    Hallelujah by Jeff Buckley
    Yesterday by The Beatles
    Skinny Love by Bon Iver
    """

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo", # Or "gpt-4"
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5, # Slightly higher for more diverse recommendations
            max_tokens=300  # Adjust based on max_songs
        )
        
        content = response.choices[0].message.content.strip()
        
        if not content:
            return []

        # Parse "Track Title by Artist Name" lines
        recommended_songs = []
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Regex to capture title and artist, robust to "by" variations
            match = re.match(r"^(.*?)\s+by\s+(.*?)$", line, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                artist = match.group(2).strip()
                # Basic cleaning for common AI artifacts like quotes
                title = title.replace('"', '')
                artist = artist.replace('"', '')
                if title and artist:
                    recommended_songs.append({"title": title, "artist": artist})
            else:
                print(f"OpenAI Service: Could not parse song line: '{line}'")
        
        return recommended_songs[:max_songs]

    except openai.error.OpenAIError as e:
        print(f"OpenAI API error in get_song_recommendations_from_openai: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error in get_song_recommendations_from_openai: {e}")
        return None
