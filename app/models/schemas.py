from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class JobStatus(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    RESEARCHING = "researching"
    EXTRACTING = "extracting"
    CRITIQUING = "critiquing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    max_sub_questions: int | None = Field(default=None, ge=3, le=5)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 3:
            raise ValueError("query must be at least 3 characters after trimming")
        return stripped


class ResearchCreatedResponse(BaseModel):
    id: UUID
    status: JobStatus


class SourceRef(BaseModel):
    url: str
    title: str
    excerpt: str


class EvidenceItem(BaseModel):
    claim: str
    sources: list[SourceRef]


class ContradictionItem(BaseModel):
    topic: str
    positions: list[str]


class RecommendationItem(BaseModel):
    name: str
    rank: int | None = None
    reason: str
    best_for: str = ""
    sources: list[SourceRef] = Field(default_factory=list)


class SynthesizerOutput(BaseModel):
    summary: str
    key_findings: list[str]
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    evidence: list[EvidenceItem]
    contradictions: list[ContradictionItem] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    confidence: str = Field(pattern=r"^(high|medium|low)$")


class ResearchReport(BaseModel):
    query: str
    summary: str
    key_findings: list[str]
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    evidence: list[EvidenceItem]
    contradictions: list[ContradictionItem]
    gaps: list[str]
    confidence: str = Field(pattern=r"^(high|medium|low)$")
    generated_at: datetime


class Passage(BaseModel):
    text: str
    url: str
    title: str
    source: str
    sub_question: str = ""
    score: float | None = None


class PlannerOutput(BaseModel):
    sub_questions: list[str] = Field(..., min_length=3, max_length=5)


class CriticOutput(BaseModel):
    contradictions: list[ContradictionItem] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class PipelineEvent(BaseModel):
    stage: str
    status: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResearchJobResponse(BaseModel):
    id: UUID
    query: str
    status: JobStatus
    progress: dict[str, Any] | None = None
    report: ResearchReport | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
