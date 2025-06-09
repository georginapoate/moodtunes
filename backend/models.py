# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# Association table for Song and Tag (many-to-many)
song_tag_association = Table(
    'song_tag_association', Base.metadata,
    Column('song_id', Integer, ForeignKey('songs.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

# Association table for Prompt and Song (many-to-many for recommendations)
prompt_song_recommendation = Table(
    'prompt_song_recommendation', Base.metadata,
    Column('prompt_id', Integer, ForeignKey('prompts.id'), primary_key=True),
    Column('song_id', Integer, ForeignKey('songs.id'), primary_key=True),
    Column('recommended_at', DateTime(timezone=True), server_default=func.now()),
    Column('source', String, default="openai") # To track where recommendation came from
)

class Prompt(Base):
    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to songs recommended for this prompt
    recommended_songs = relationship(
        "Song",
        secondary=prompt_song_recommendation,
        back_populates="recommended_for_prompts"
    )

class Song(Base):
    __tablename__ = "songs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    artist = Column(String, index=True, nullable=False)
    # Optional: Add spotify_id, lastfm_url etc.
    spotify_id = Column(String, unique=True, nullable=True)

    # Many-to-many relationship with Tag
    tags = relationship(
        "Tag",
        secondary=song_tag_association,
        back_populates="songs"
    )
    # Relationship back to prompts
    recommended_for_prompts = relationship(
        "Prompt",
        secondary=prompt_song_recommendation,
        back_populates="recommended_songs"
    )
    __table_args__ = (UniqueConstraint('title', 'artist', name='_title_artist_uc'),)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    # Many-to-many relationship with Song
    songs = relationship(
        "Song",
        secondary=song_tag_association,
        back_populates="tags"
    )