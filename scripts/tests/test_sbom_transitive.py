# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""SBOM 전이 의존성 생성기 테스트. 네트워크 조회는 가짜로 바꿔 lock 파일 해석만 검사한다."""

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "sbom_transitive", Path(__file__).resolve().parents[1] / "sbom_transitive.py"
)
sbom = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sbom)


@pytest.mark.parametrize(
    ("expression", "allowed"),
    [
        ("MIT", True),
        ("MIT-0", True),
        ("Apache-2.0 OR BSD-2-Clause", True),
        ("(MIT OR GPL-3.0-only)", True),  # 선택지 중 하나만 허용이면 그걸 고르면 된다
        ("MIT AND MPL-2.0", False),  # 둘 다 지켜야 하는 조합은 전부 허용이어야 한다
        ("MPL-2.0", False),
        ("PSF-2.0", False),
        ("GPL-3.0-only", False),
        ("확인 필요", False),
        # 괄호 우선순위(#500): AND가 걸린 쪽은 GPL을 피할 수 없다
        ("GPL-3.0-only AND (MIT OR Apache-2.0)", False),
        ("(MIT OR Apache-2.0) AND BSD-3-Clause", True),
        ("Apache-2.0 OR BSD-3-Clause", True),  # cryptography
        ("Apache-2.0 WITH LLVM-exception", False),  # 예외 조항은 사람이 본다
        ("MIT OR", False),
    ],
)
def test_allow_list(expression, allowed):
    assert sbom.is_allowed(expression) is allowed


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("git+https://github.com/a/b.git", "https://github.com/a/b"),
        ("git://github.com/a/b.git#main", "https://github.com/a/b"),
        ("ssh://git@github.com/a/b.git", "https://github.com/a/b"),
        ("github:a/b", "https://github.com/a/b"),
        ("a/b", "https://github.com/a/b"),
        ("https://example.org/project", "https://example.org/project"),
        (None, ""),
    ],
)
def test_repository_url_cleanup(raw, clean):
    assert sbom.clean_repo(raw) == clean


def test_npm_runtime_and_dev_graphs_are_separated():
    packages, runtime, dev = sbom.npm_graph()
    names = {path.rsplit("node_modules/", 1)[-1] for path in runtime}
    # 번들에 들어가는 것은 직접 의존성과 그 전이뿐이고, 빌드 도구는 섞이지 않는다
    assert {"react", "react-dom", "scheduler", "pdfjs-dist"} <= names
    assert "vite" not in names
    dev_names = {path.rsplit("node_modules/", 1)[-1] for path in dev}
    assert {"vite", "vitest", "jsdom"} <= dev_names
    # lock 파일이 개발용으로 표시한 패키지를 개발 그래프가 빠짐없이 찾는다(peer 의존성 포함)
    flagged = {p for p, meta in packages.items() if p and (meta.get("dev") or meta.get("devOptional"))}
    assert flagged <= set(dev)


def test_api_graph_skips_local_packages(monkeypatch):
    monkeypatch.setattr(sbom, "pypi_meta", lambda name, version: ("MIT", ""))
    rows = {r["name"]: r for r in sbom.api_rows()}
    assert {"fastapi", "starlette", "pydantic", "uvicorn"} <= set(rows)
    assert "maskingtape" not in rows and "maskingtape-api" not in rows
    assert rows["fastapi"]["note"] == "직접 의존성(본표)"
    assert rows["starlette"]["note"].startswith("경로: fastapi → starlette")


def test_desktop_rows_cover_the_whole_lockfile(monkeypatch):
    monkeypatch.setattr(sbom, "pub_meta", lambda name, version: ("BSD-3-Clause", ""))
    rows = {r["name"]: r for r in sbom.desktop_rows()}
    lock = (sbom.ROOT / "apps/desktop/pubspec.lock").read_text(encoding="utf-8")
    assert len(rows) == lock.count("\n    dependency:")
    assert rows["flutter"]["repo"] == "https://github.com/flutter/flutter"
    assert rows["desktop_drop"]["note"] == "직접(런타임)"


def test_pub_meta_joins_several_license_tags_with_and(monkeypatch):
    # 태그가 여럿이면 LICENSE 한 파일에 함께 든 라이선스라 둘 다 지켜야 한다(#634)
    def fake_fetch(url):
        if url.endswith("/score"):
            tags = ["license:apache-2.0", "license:bsd-3-clause", "license:fsf-libre", "license:osi-approved"]
            return {"tags": tags}
        return {"pubspec": {"repository": "https://github.com/flutter/packages"}}

    monkeypatch.setattr(sbom, "fetch_json", fake_fetch)
    license_, _ = sbom.pub_meta("file_selector_android", "0.5.2+8")
    assert license_ == "Apache-2.0 AND BSD-3-Clause"


def test_checked_pub_license_replaces_registry_tag(monkeypatch):
    # pub.dev 태그는 BSD-3-Clause 하나지만 vector_math 2.2.0 LICENSE에는 zlib 전문도 있다(#634)
    monkeypatch.setattr(sbom, "pub_meta", lambda name, version: ("BSD-3-Clause", ""))
    rows = {r["name"]: r for r in sbom.desktop_rows()}
    assert rows["vector_math"]["license"] == "BSD-3-Clause AND Zlib"
    assert not sbom.is_allowed(rows["vector_math"]["license"])  # 부록 A-6으로 모인다


def test_checked_pub_license_needs_recheck_when_version_moves(monkeypatch):
    # lock의 버전이 확인한 버전과 다르면 레지스트리 태그로 조용히 돌아가지 않는다
    monkeypatch.setattr(sbom, "pub_meta", lambda name, version: ("BSD-3-Clause", ""))
    monkeypatch.setitem(sbom.PUB_LICENSE_CHECKED, "vector_math", ("0.0.1", "BSD-3-Clause AND Zlib"))
    rows = {r["name"]: r for r in sbom.desktop_rows()}
    assert rows["vector_math"]["license"] == "확인 필요"
    assert not sbom.is_allowed(rows["vector_math"]["license"])


def test_sbom_has_exactly_one_generated_section():
    text = sbom.SBOM.read_text(encoding="utf-8")
    assert text.count(sbom.BEGIN) == 1 and text.count(sbom.END) == 1
    assert text.index(sbom.BEGIN) < text.index(sbom.END)


class _FakeDist:
    def __init__(self, version, requires):
        self.version = version
        self.requires = requires


def test_installed_rows_follow_extras_the_parent_requested(monkeypatch):
    # mcp → pyjwt[crypto] → cryptography → cffi → pycparser. pyjwt의 dev extra는 아무도 요청하지 않았다(#500).
    dists = {
        "mcp": _FakeDist("1.0", ["pyjwt[crypto]>=2"]),
        "pyjwt": _FakeDist("2.0", ['cryptography>=3.4; extra == "crypto"', 'pytest; extra == "dev"']),
        "cryptography": _FakeDist("46.0", ["cffi>=1.12"]),
        "cffi": _FakeDist("2.0", ["pycparser"]),
        "pycparser": _FakeDist("2.22", []),
    }

    def distribution(name):
        if name not in dists:
            raise sbom.metadata.PackageNotFoundError(name)
        return dists[name]

    monkeypatch.setattr(sbom.metadata, "distribution", distribution)
    monkeypatch.setattr(sbom, "pypi_meta", lambda name, version: ("MIT", ""))

    names = [r["name"] for r in sbom.installed_rows(["mcp"], skip={"mcp"})]

    assert names == ["cffi", "cryptography", "pycparser", "pyjwt"]
