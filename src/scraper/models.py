import hashlib
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class RawNewsArticle(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=False,
        extra="forbid",
        populate_by_name=True
    )

    article_id: str = Field(..., serialization_alias="id")
    url: str = Field(..., serialization_alias="source_url")
    portal: str = Field(...)
    termo_busca: str = Field(..., min_length=2)
    data_coleta: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_publicacao: Optional[datetime] = Field(default=None, serialization_alias="published_at")
    titulo: str = Field(..., min_length=5, max_length=500, serialization_alias="title")
    subtitulo: Optional[str] = Field(default=None)
    corpo_texto: str = Field(..., min_length=30, serialization_alias="body")

    @classmethod
    def gerar_article_id(cls, url: str) -> str:
        url_normalizada = url.strip().split("?")[0].lower()
        return hashlib.sha256(url_normalizada.encode("utf-8")).hexdigest()[:16]

    @field_validator("corpo_texto")
    @classmethod
    def validar_corpo(cls, v: str) -> str:
        if len(v.split()) < 10:
            raise ValueError("Corpo do texto insuficiente para compor uma matéria.")
        return v