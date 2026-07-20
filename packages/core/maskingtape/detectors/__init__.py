"""탐지기 모음. 새 탐지기를 만들면 default_detectors()에 등록한다."""

from __future__ import annotations

from maskingtape.detectors.address import AddressDetector
from maskingtape.detectors.base import Detector
from maskingtape.detectors.email import EmailDetector
from maskingtape.detectors.phone import PhoneDetector
from maskingtape.detectors.rrn import RRNDetector

__all__ = [
    "AddressDetector",
    "Detector",
    "EmailDetector",
    "PhoneDetector",
    "RRNDetector",
    "default_detectors",
]


def default_detectors() -> list[Detector]:
    """기본 탐지기 세트 (규칙 전용 — LLM 불필요)."""
    return [RRNDetector(), PhoneDetector(), EmailDetector(), AddressDetector()]
