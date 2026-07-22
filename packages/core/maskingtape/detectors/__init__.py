"""탐지기 모음. 새 탐지기를 만들면 default_detectors()에 등록한다."""

from __future__ import annotations

from maskingtape.detectors.address import AddressDetector
from maskingtape.detectors.base import Detector
from maskingtape.detectors.email import EmailDetector
from maskingtape.detectors.name import NameDetector
from maskingtape.detectors.name_llm import DEFAULT_MODEL, LLMNameDetector
from maskingtape.detectors.phone import PhoneDetector
from maskingtape.detectors.rrn import RRNDetector

__all__ = [
    "AddressDetector",
    "Detector",
    "EmailDetector",
    "LLMNameDetector",
    "NameDetector",
    "PhoneDetector",
    "RRNDetector",
    "default_detectors",
    "llm_detectors",
]


def default_detectors() -> list[Detector]:
    """기본 탐지기 세트 (규칙 전용 — LLM 불필요)."""
    return [RRNDetector(), PhoneDetector(), EmailDetector(), AddressDetector(), NameDetector()]


def llm_detectors(model: str = DEFAULT_MODEL) -> list[Detector]:
    """이름만 로컬 LLM으로 판단하는 세트 (**로컬 Ollama 필요**).

    규칙 이름 탐지기(NameDetector)는 빼고 LLMNameDetector로 대체한다 — 둘을 같이 쓰면
    규칙판이 오탐한 이름("이용 안내"의 '이용')이 그대로 남기 때문이다.
    """
    return [
        RRNDetector(),
        PhoneDetector(),
        EmailDetector(),
        AddressDetector(),
        LLMNameDetector(model=model),
    ]
