from pydantic import BaseModel
from typing import List

class PromptRequest(BaseModel):
    prompt: str

class TagPredictionResponse(BaseModel):
    tags: List[str]

class PlaylistResponse(BaseModel):
    playlist_url: str
    message: str