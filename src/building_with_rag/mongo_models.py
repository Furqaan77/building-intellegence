"""Document shapes later stories will store in MongoDB. Types only: no connection or indexes."""

from datetime import datetime

from pydantic import BaseModel, Field


class SectionDocument(BaseModel):
    section_id: str
    act: str
    section_number: str
    chapter: str | None = None
    heading: str | None = None
    text: str
    source_file: str | None = None
    status: str | None = None
    access_level: str | None = None


class ChunkDocument(BaseModel):
    chunk_id: str
    section_id: str
    act: str
    text: str
    heading: str | None = None
    source_file: str | None = None
    status: str | None = None
    access_level: str | None = None
    embedding: list[float] | None = None
    embedding_model: str = "voyage-3.5"
    embedding_dimensions: int = 1024


class CallerDocument(BaseModel):
    caller_id: str
    access_levels: list[str] = Field(default_factory=list)


class IngestRunDocument(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    counts: dict[str, int] = Field(default_factory=dict)
