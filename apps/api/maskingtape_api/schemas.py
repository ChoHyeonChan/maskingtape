# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


MAX_TEXT_LENGTH = 100_000


class DetectionKind(str, Enum):
    """Personal information categories currently emitted by packages/core."""

    RRN = "rrn"
    PHONE = "phone"
    EMAIL = "email"
    NAME = "name"
    ADDRESS = "address"
    CARD = "card"


class AnonymizeStrategy(str, Enum):
    """Supported anonymization strategies exposed by the API contract."""

    MASK = "mask"
    LABEL = "label"


class TextRequest(BaseModel):
    """Base request body for endpoints that process one text payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "테스트 문서에 예시 번호 000000-0000000이 포함되어 있습니다."
            }
        }
    )

    text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="합성 또는 사용자가 입력한 처리 대상 텍스트. 서버는 이 값을 저장하지 않는다.",
    )


class ScanRequest(TextRequest):
    """Request body for detecting personal information without anonymizing text."""


class DetectionResponse(BaseModel):
    """One personal information span detected from the input text."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kind": "rrn",
                "start": 10,
                "end": 24,
                "text": "000000-0000000",
                "confidence": 1.0,
                "detector": "RRNDetector",
            }
        }
    )

    kind: DetectionKind = Field(..., description="개인정보 종류.")
    start: int = Field(..., ge=0, description="원문 기준 시작 위치. Python 슬라이스 규약.")
    end: int = Field(..., ge=0, description="원문 기준 끝 위치. Python 슬라이스 규약.")
    text: str = Field(..., description="탐지된 원문 조각.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="탐지 확신도.")
    detector: str = Field(..., description="탐지를 수행한 core detector 이름.")


class ScanResponse(BaseModel):
    """Response body for scan results."""

    detections: list[DetectionResponse] = Field(default_factory=list)


class AnonymizeRequest(TextRequest):
    """Request body for anonymizing text after detection."""

    strategy: AnonymizeStrategy = Field(
        default=AnonymizeStrategy.MASK,
        description="비식별화 전략. mask는 별표 치환, label은 종류 라벨 치환.",
    )


class AnonymizeResponse(BaseModel):
    """Response body for anonymized text and the detections used to produce it."""

    text: str = Field(..., description="비식별화가 적용된 텍스트.")
    detections: list[DetectionResponse] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Liveness response body."""

    status: str = Field(..., description="서비스 상태.")


class ErrorResponse(BaseModel):
    """Shared error response body."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "invalid_request",
                "message": "요청 형식이 올바르지 않습니다.",
                "details": {"field": "text"},
            }
        }
    )

    code: str = Field(..., description="기계가 읽을 수 있는 에러 코드.")
    message: str = Field(..., description="사용자 또는 클라이언트 개발자가 읽을 수 있는 설명.")
    details: dict[str, Any] | None = Field(default=None, description="선택적 추가 정보.")
