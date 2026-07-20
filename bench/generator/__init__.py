"""합성 문서 생성기. entities가 개별 개인정보 값을 만들고, documents가 문장에 심어 라벨을 붙인다."""

from __future__ import annotations

from bench.generator.documents import generate_document
from bench.generator.entities import Entity

__all__ = ["Entity", "generate_document"]
