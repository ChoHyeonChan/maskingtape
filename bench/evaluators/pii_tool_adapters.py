# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""KDPII 타 도구 비교에 쓰는 도구 어댑터. 도구마다 탐지 결과를 {label, kind, start, end}로 맞춘다.

ko-pii와 Presidio는 저장소 의존성이 아니다. 비교용 가상환경에만 설치하고(bench README 「KDPII 타 도구
비교」), 여기서는 함수 안에서 import한다. 매핑표에 없는 라벨은 kind=None으로 남긴다. 종류별 채점에서는
빠지지만, 「가렸나」와 「엉뚱한 곳을 가렸나」 채점에는 들어간다(compare_kdpii_tools.py).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module, metadata
from types import ModuleType

from maskingtape.pipeline import Pipeline

# 각 도구의 라벨 → 우리 종류.
KOPII_TO_KIND = {
    "PERSON": "name",
    "PHONE": "phone",
    "FAX": "phone",
    "EMAIL": "email",
    "RRN": "rrn",
    "FRN": "rrn",
    "ADDRESS": "address",
    "CARD": "card",
    "BUSINESS_REG": "biz_reg",
    "PASSPORT": "passport",
    "ACCOUNT": "account",
    "DT_BIRTH": "birth_date",
    "DRIVER_LICENSE": "driver_license",
}
# Presidio는 나라 구분 없이 같은 뜻이면 우리 종류로 본다(US_* 포함). 상대에게 유리한 쪽으로 잡은 것이다.
PRESIDIO_TO_KIND = {
    "PERSON": "name",
    "PHONE_NUMBER": "phone",
    "EMAIL_ADDRESS": "email",
    "KR_RRN": "rrn",
    "KR_FRN": "rrn",
    "LOCATION": "address",
    "CREDIT_CARD": "card",
    "KR_BRN": "biz_reg",
    "KR_PASSPORT": "passport",
    "US_PASSPORT": "passport",
    "IBAN_CODE": "account",
    "US_BANK_NUMBER": "account",
    "DATE_TIME": "birth_date",
    "KR_DRIVER_LICENSE": "driver_license",
    "US_DRIVER_LICENSE": "driver_license",
}

Predict = Callable[[str], list[dict]]


@dataclass(frozen=True)
class Tool:
    name: str
    versions: dict[str, str]
    predict: Predict


def to_pred(label: str, kind_map: dict[str, str], start: int, end: int) -> dict:
    return {"label": label, "kind": kind_map.get(label), "start": start, "end": end}


def _require(module: str, package: str) -> ModuleType:
    try:
        return import_module(module)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"{package}가 설치되지 않았다. bench README 「KDPII 타 도구 비교」의 비교용 가상환경에서 실행한다."
        ) from exc


def maskingtape_rules() -> Tool:
    pipeline = Pipeline()

    def predict(text: str) -> list[dict]:
        return [
            {"label": d.kind, "kind": d.kind, "start": d.start, "end": d.end}
            for d in pipeline.scan(text)
        ]

    return Tool("maskingtape-rules", {"maskingtape": metadata.version("maskingtape")}, predict)


def kopii(strict: bool) -> Tool:
    """ko-pii. strict는 STRICT 모드에서 막는(BLOCK) 탐지만, 아니면 detect_all 전부."""
    ko_pii = _require("ko_pii", "ko-pii")
    modes = import_module("ko_pii.core.modes")
    anonymizer = ko_pii.Anonymizer(mode=ko_pii.ProcessingMode.STRICT) if strict else None

    def predict(text: str) -> list[dict]:
        if anonymizer is not None:
            found = [
                r.detection
                for r in anonymizer.process(text).detections
                if r.action == modes.Action.BLOCK
            ]
        else:
            found = ko_pii.detect_all(text)
        return [to_pred(d.label, KOPII_TO_KIND, d.start, d.end) for d in found]

    name = "ko-pii-strict" if strict else "ko-pii-all"
    return Tool(name, {"ko-pii": metadata.version("ko-pii")}, predict)


def presidio(kr: bool) -> Tool:
    """Presidio 기본 설정(영어, spaCy en_core_web_lg). kr이면 꺼져 있는 한국 인식기 5개와 KR 전화를 켠다."""
    analyzer = _require("presidio_analyzer", "presidio-analyzer")
    recognizers = import_module("presidio_analyzer.predefined_recognizers")
    # 모델이 없으면 AnalyzerEngine이 묻지 않고 받아 온다(버전도 그날 것). 먼저 확인하고 멈춘다.
    try:
        versions = {
            p: metadata.version(p) for p in ("presidio-analyzer", "spacy", "en_core_web_lg")
        }
    except metadata.PackageNotFoundError as exc:
        raise RuntimeError(
            "spaCy 모델 en_core_web_lg가 설치되지 않았다. bench README 「KDPII 타 도구 비교」의 설치 명령으로 먼저 깐다."
        ) from exc
    engine = analyzer.AnalyzerEngine()
    if kr:
        # 한국 인식기는 언어가 ko로 잡혀 있다. 영어 NLP 엔진을 그대로 쓰고 인식기 언어만 en으로 바꿔 켠다.
        # 전화는 기본 지역에 KR이 없어 KR을 더한다.
        registry = engine.registry
        registry.remove_recognizer("PhoneRecognizer")
        phone = recognizers.PhoneRecognizer
        regions = tuple(phone.DEFAULT_SUPPORTED_REGIONS) + ("KR",)
        registry.add_recognizer(phone(supported_language="en", supported_regions=regions))
        for cls_name in (
            "KrRrnRecognizer",
            "KrBrnRecognizer",
            "KrDriverLicenseRecognizer",
            "KrFrnRecognizer",
            "KrPassportRecognizer",
        ):
            registry.add_recognizer(getattr(recognizers, cls_name)(supported_language="en"))

    def predict(text: str) -> list[dict]:
        return [
            to_pred(r.entity_type, PRESIDIO_TO_KIND, r.start, r.end)
            for r in engine.analyze(text=text, language="en")
        ]

    return Tool("presidio-kr" if kr else "presidio", versions, predict)


BUILDERS: dict[str, Callable[[], Tool]] = {
    "maskingtape-rules": maskingtape_rules,
    "ko-pii-strict": lambda: kopii(strict=True),
    "ko-pii-all": lambda: kopii(strict=False),
    "presidio-kr": lambda: presidio(kr=True),
    "presidio": lambda: presidio(kr=False),
}


def build_tools(names: list[str]) -> list[Tool]:
    unknown = sorted(set(names) - set(BUILDERS))
    if unknown:
        raise ValueError(f"알 수 없는 비교 도구: {', '.join(unknown)}")
    return [BUILDERS[name]() for name in names]
