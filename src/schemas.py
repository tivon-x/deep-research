"""Shared Pydantic schemas for tool inputs."""

from pydantic import BaseModel, Field, field_validator


class SourceMetadataInput(BaseModel):
    """Structured source metadata for the source log tool."""

    citation_id: str | None = Field(
        default=None,
        description="Optional citation identifier such as [1] or S1.",
    )
    title: str = Field(min_length=1, description="Title of the source.")
    url: str = Field(min_length=1, description="Source URL.")
    publisher: str | None = Field(
        default=None,
        description="Publisher or organization responsible for the source.",
    )
    authors: str | None = Field(
        default=None,
        description="Author name or a comma-separated author list.",
    )
    published_date: str | None = Field(
        default=None,
        description="Published date in a human-readable or ISO-like format.",
    )
    evidence_type: str | None = Field(
        default=None,
        description="Evidence category such as report, article, filing, or dataset.",
    )
    relevance: str | None = Field(
        default=None,
        description="Short note explaining why this source matters.",
    )

    @field_validator(
        "citation_id",
        "title",
        "url",
        "publisher",
        "authors",
        "published_date",
        "evidence_type",
        "relevance",
    )
    @classmethod
    def _strip_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class SourceMetadataRequest(BaseModel):
    """Top-level payload for generating a source metadata log."""

    question_title: str = Field(
        min_length=1,
        description="Human-readable title for this research question.",
    )
    sources: list[SourceMetadataInput] = Field(
        min_length=1,
        description="List of source metadata objects to include in the log.",
    )

    @field_validator("question_title")
    @classmethod
    def _strip_question_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question_title must not be empty.")
        return stripped
