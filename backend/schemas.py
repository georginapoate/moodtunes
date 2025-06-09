from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class PromptRequest(BaseModel):
    prompt: str

class SongDetail(BaseModel):
    title: str
    artist: str
    tags: List[str] = [] # Tags associated with this song

    class Config:
        from_attributes = True # For Pydantic v2, was orm_mode = True

class PlaylistResponse(BaseModel):
    playlist_url: HttpUrl
    message: str
    songs: List[SongDetail] = [] # Return the list of songs in the playlist

class SpotifyAuthData(BaseModel): # If you were to return token info to frontend
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int
    token_type: str