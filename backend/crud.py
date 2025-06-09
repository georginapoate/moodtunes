# backend/crud.py
from sqlalchemy.orm import Session
from . import models, schemas # schemas might need updates
from typing import List, Optional

# --- Prompt CRUD ---
def get_prompt_by_text(db: Session, text: str) -> Optional[models.Prompt]:
    return db.query(models.Prompt).filter(models.Prompt.text == text).first()

def create_prompt(db: Session, text: str) -> models.Prompt:
    db_prompt = models.Prompt(text=text)
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

# --- Song CRUD ---
def get_song_by_title_artist(db: Session, title: str, artist: str) -> Optional[models.Song]:
    return db.query(models.Song).filter(models.Song.title == title, models.Song.artist == artist).first()

def create_song(db: Session, title: str, artist: str) -> models.Song:
    db_song = models.Song(title=title, artist=artist)
    db.add(db_song)
    db.commit()
    db.refresh(db_song)
    return db_song

def get_or_create_song(db: Session, title: str, artist: str) -> models.Song:
    db_song = get_song_by_title_artist(db, title, artist)
    if db_song:
        return db_song
    return create_song(db, title, artist)

# --- Tag CRUD ---
def get_tag_by_name(db: Session, name: str) -> Optional[models.Tag]:
    return db.query(models.Tag).filter(models.Tag.name == name).first()

def create_tag(db: Session, name: str) -> models.Tag:
    db_tag = models.Tag(name=name)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag

def get_or_create_tag(db: Session, name: str) -> models.Tag:
    db_tag = get_tag_by_name(db, name)
    if db_tag:
        return db_tag
    return create_tag(db, name)

# --- Association CRUD ---
def add_tags_to_song(db: Session, song: models.Song, tag_names: List[str]):
    for tag_name in tag_names:
        tag = get_or_create_tag(db, name=tag_name.lower().strip())
        if tag not in song.tags:
            song.tags.append(tag)
    db.commit()

def link_prompt_to_song(db: Session, prompt: models.Prompt, song: models.Song, source: str = "openai"):
    # Check if association already exists to prevent duplicate entries if this function is called multiple times
    # For prompt_song_recommendation, a simple check if song is already in prompt.recommended_songs
    if song not in prompt.recommended_songs:
        prompt.recommended_songs.append(song)
        # If you stored 'source' directly on the association table object (more complex setup)
        # you'd create the association object explicitly here.
        # For this simple secondary relationship, SQLAlchemy handles the junction table.
        # To set the `source` on the association, you'd need an Association Object pattern for `prompt_song_recommendation`.
        # For now, we'll assume 'source' is implicit or handled differently if strictly needed on that row.
        db.commit()

# If using an association object for prompt_song_recommendation to store 'source'
# from .models import prompt_song_recommendation # The table object
# def link_prompt_to_song_with_source(db: Session, prompt_id: int, song_id: int, source: str = "openai"):
#     # Check if exists
#     existing_link = db.query(prompt_song_recommendation).filter_by(prompt_id=prompt_id, song_id=song_id).first()
#     if not existing_link:
#         stmt = prompt_song_recommendation.insert().values(prompt_id=prompt_id, song_id=song_id, source=source)
#         db.execute(stmt)
#         db.commit()