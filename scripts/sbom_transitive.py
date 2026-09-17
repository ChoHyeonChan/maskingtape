# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""SBOM.md의 전이 의존성 부록을 lock 파일과 공개 레지스트리에서 다시 뽑는다(#438).

2026년 9월 OpenUP 오픈소스 라이선스 컨설팅은 "배포에 포함되는 모든 의존성을 적는 것이
원칙"이라고 권고했다. 손으로 옮기면 버전이 금방 어긋나므로 표를 기계로 만든다.

동작 원리:
1. 배포물마다 의존성 그래프를 따라간다. 웹 데모는 apps/web/package-lock.json, REST API 서버는
   루트 uv.lock(Vercel 배포가 쓰는 파일), MCP 서버는 설치본 메타데이터, 데스크톱은 pubspec.lock이다.
2. 패키지마다 라이선스와 저장소 주소를 npm·PyPI·pub.dev 공개 API에서 읽는다(조회만 한다).
3. 결과를 SBOM.md의 표시 구간에 넣고, 팀 허용 목록 밖 라이선스는 따로 모은다.
   --check는 SBOM.md가 최신인지만 확인한다.

사용(저장소 루트에서):
    python scripts/sbom_transitive.py            # 화면에 출력
    python scripts/sbom_transitive.py --write    # SBOM.md 갱신
    python scripts/sbom_transitive.py --check    # 최신이 아니면 1로 끝남

준비: 인터넷 연결, Python 3.11 이상. 개발 도구 표까지 정확하려면 깨끗한 가상환경에
`pip install -e "packages/core[dev]" -e packages/mcp-server -e "apps/api[dev]"`를 해 두고 실행한다.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import urllib.request
from collections import Counter, deque
from functools import cache
from importlib import metadata
from pathlib import Path

import tomllib
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parent.parent
SBOM = ROOT / "SBOM.md"
BEGIN, END = "<!-- sbom-transitive:begin -->", "<!-- sbom-transitive:end -->"
ENV = f"Python {platform.python_version()}, {platform.system()}"

# 팀 허용 목록(CLAUDE.md §2: MIT·Apache-2.0·BSD·ISC)과 그보다 느슨한 변형(MIT-0·0BSD).
# "BSD"는 변형을 밝히지 않은 PyPI 분류자를 받기 위해 둔다.
ALLOWED = {"MIT", "MIT-0", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "BSD", "0BSD", "ISC"}
FLUTTER_SDK = ("BSD-3-Clause", "https://github.com/flutter/flutter")
# 빌드 결과물을 직접 열어 확인한 사실. 레지스트리 정보만으로는 알 수 없다.
NODE_ONLY_OPTIONAL = {
    "@napi-rs/canvas": "Node 전용 선택 의존성. 브라우저 번들에는 코드가 없다(불러오는 문자열만 있음)",
}
_TEXT_TO_SPDX = {
    "mit": "MIT", "mit license": "MIT", "apache 2.0": "Apache-2.0", "apache-2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0", "bsd": "BSD", "bsd-3-clause": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause", "isc": "ISC", "mpl-2.0": "MPL-2.0", "psf": "PSF-2.0",
    "psf-2.0": "PSF-2.0",
}
_CLASSIFIER_TO_SPDX = {
    "MIT License": "MIT", "Apache Software License": "Apache-2.0", "BSD License": "BSD",
    "ISC License (ISCL)": "ISC", "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "Python Software Foundation License": "PSF-2.0",
}
_PUB_TAG_TO_SPDX = {
    "mit": "MIT", "apache-2.0": "Apache-2.0", "bsd-3-clause": "BSD-3-Clause", "bsd-2-clause": "BSD-2-Clause",
}
_REPO_KEYS = {"source", "source code", "repository", "github", "code"}


@cache
def fetch_json(url: str) -> dict:
    """공개 레지스트리 조회. 주소는 코드에 고정된 세 곳(npm·PyPI·pub.dev)이고 보내는 데이터는 없다."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "maskingtape-sbom", "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def clean_repo(url: str | None) -> str:
    """git+https://…/x.git 같은 표기를 브라우저로 열 수 있는 주소로 바꾼다."""
    if not url:
        return ""
    # 조각(#…)을 먼저 지워야 "…/x.git#main"의 .git이 끝으로 드러난다. 한 번에 치환하면 남는다.
    url = re.sub(r"#.*$", "", url.strip())
    url = re.sub(r"^git\+", "", url)
    url = re.sub(r"\.git$", "", url)
    url = re.sub(r"^(git|ssh)://(git@)?", "https://", url)
    if url.startswith("github:"):
        url = "https://github.com/" + url[len("github:"):]
    if re.fullmatch(r"[\w.-]+/[\w.-]+", url):
        url = "https://github.com/" + url
    return url


def is_allowed(expression: str) -> bool:
    """SPDX 식의 OR 선택지 중 하나라도 AND 항목이 전부 허용 목록이면 허용이다."""
    for alternative in re.split(r"\s+OR\s+", expression.strip("() ")):
        terms = [term.strip("() ") for term in re.split(r"\s+AND\s+", alternative)]
        if all(term in ALLOWED for term in terms):
            return True
    return False


def row(name: str, version: str, license_: str, repo: str, note: str) -> dict:
    return {"name": name, "version": version, "license": license_, "repo": repo, "note": note}


# --- 레지스트리별 라이선스·저장소 조회 ---


def pypi_meta(name: str, version: str) -> tuple[str, str]:
    info = fetch_json(f"https://pypi.org/pypi/{name}/{version}/json")["info"]
    license_ = (info.get("license_expression") or "").strip()
    text = (info.get("license") or "").strip()
    if not license_ and text and "\n" not in text and len(text) <= 60:
        license_ = _TEXT_TO_SPDX.get(text.lower(), text)
    if not license_:
        names = {c.rsplit(" :: ", 1)[-1] for c in info.get("classifiers", []) if c.startswith("License :: OSI")}
        license_ = " OR ".join(sorted(_CLASSIFIER_TO_SPDX.get(n, n) for n in names)) or "확인 필요"
    urls = info.get("project_urls") or {}
    repo = next((v for k, v in urls.items() if k.lower() in _REPO_KEYS), "")
    return license_, clean_repo(repo or urls.get("Homepage") or info.get("home_page"))


def npm_repo(name: str, version: str) -> str:
    repo = fetch_json(f"https://registry.npmjs.org/{name}/{version}").get("repository")
    return clean_repo(repo.get("url") if isinstance(repo, dict) else repo)


def pub_meta(name: str, version: str) -> tuple[str, str]:
    """라이선스는 pub.dev가 LICENSE 파일에서 판별한 태그(최신 버전 기준)를 쓴다."""
    tags = fetch_json(f"https://pub.dev/api/packages/{name}/score").get("tags", [])
    found = {
        _PUB_TAG_TO_SPDX.get(tag.split(":", 1)[1], tag.split(":", 1)[1])
        for tag in tags
        if tag.startswith("license:") and tag not in {"license:osi-approved", "license:fsf-libre"}
    }
    pubspec = fetch_json(f"https://pub.dev/api/packages/{name}/versions/{version}")["pubspec"]
    repo = clean_repo(pubspec.get("repository") or pubspec.get("homepage"))
    return " OR ".join(sorted(found)) or "확인 필요", repo


# --- 배포물별 의존성 그래프 ---


def npm_graph() -> tuple[dict, dict, dict]:
    """package-lock에서 런타임(dependencies)과 개발(devDependencies) 그래프를 따로 걷는다."""
    lock_path = ROOT / "apps/web/package-lock.json"
    packages = json.loads(lock_path.read_text(encoding="utf-8"))["packages"]

    def resolve(parent: str, name: str) -> str | None:
        base = parent  # node 해석 규칙: 가장 가까운 node_modules부터 위로 올라간다
        while True:
            candidate = f"{base}/node_modules/{name}" if base else f"node_modules/{name}"
            if candidate in packages:
                return candidate
            if not base:
                return None
            cut = base.rfind("/node_modules/")
            base = base[:cut] if cut != -1 else ""

    def walk(direct: dict) -> dict[str, list[str]]:
        seen: dict[str, list[str]] = {}
        queue = deque((resolve("", name), [name]) for name in direct)
        while queue:
            path, via = queue.popleft()
            if path is None or path in seen:
                continue  # 설치되지 않은 선택·peer 의존성은 None으로 건너뛴다
            seen[path] = via
            meta = packages[path]
            children = {
                **meta.get("dependencies", {}),
                **meta.get("optionalDependencies", {}),
                **meta.get("peerDependencies", {}),
            }
            for dep in children:
                queue.append((resolve(path, dep), via + [dep]))
        return seen

    root = packages[""]
    return packages, walk(root.get("dependencies", {})), walk(root.get("devDependencies", {}))


def web_rows() -> list[dict]:
    packages, runtime, _ = npm_graph()
    rows: list[dict] = []
    binaries: dict[str, list[dict]] = {}
    for path, via in sorted(runtime.items()):
        name, meta = path.rsplit("node_modules/", 1)[-1], packages[path]
        parent = next((p for p in NODE_ONLY_OPTIONAL if name.startswith(p + "-")), None)
        if parent:  # 플랫폼별 바이너리(…-win32-x64-msvc 등)는 한 줄로 묶는다
            binaries.setdefault(parent, []).append(meta)
            continue
        note = "직접 의존성(본표)" if len(via) == 1 else "경로: " + " → ".join(via)
        if meta.get("optional"):
            note += ". " + NODE_ONLY_OPTIONAL.get(name, "선택 의존성")
        rows.append(row(name, meta["version"], meta.get("license", "확인 필요"), npm_repo(name, meta["version"]), note))
    for parent, metas in binaries.items():
        versions = ", ".join(sorted({m["version"] for m in metas}))
        licenses = " / ".join(sorted({m.get("license", "확인 필요") for m in metas}))
        note = f"{parent}의 플랫폼별 바이너리 {len(metas)}개. 브라우저 번들에 없음"
        rows.append(row(f"{parent}-*", versions, licenses, "", note))
    return rows


def npm_dev_rows() -> list[dict]:
    """개발 도구로만 쓰이는 npm 패키지(런타임 그래프에 없는 것)."""
    packages, runtime, dev = npm_graph()
    rows = []
    for path, via in sorted(dev.items()):
        if path in runtime:
            continue
        name, meta = path.rsplit("node_modules/", 1)[-1], packages[path]
        rows.append(row(name, meta["version"], meta.get("license", "확인 필요"), "", "경로: " + " → ".join(via)))
    return rows


def api_rows() -> list[dict]:
    """루트 uv.lock에서 maskingtape-api가 끌어오는 패키지. 로컬 패키지(core·api)는 표에서 뺀다."""
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = {p["name"]: p for p in lock["package"]}
    local = {name for name, p in packages.items() if {"editable", "virtual"} & set(p.get("source", {}))}
    rows, seen = [], set()
    queue = deque([("maskingtape-api", [], "")])
    while queue:
        name, via, marker = queue.popleft()
        if name in seen:
            continue
        seen.add(name)
        chain = [] if name in local else via + [name]
        for dep in packages[name].get("dependencies", []):
            queue.append((dep["name"], chain, dep.get("marker", "")))
        if name in local:
            continue
        license_, repo = pypi_meta(name, packages[name]["version"])
        note = "직접 의존성(본표)" if not via else "경로: " + " → ".join(chain)
        if marker:
            note += f". 조건: `{marker}`"
        rows.append(row(name, packages[name]["version"], license_, repo, note))
    return sorted(rows, key=lambda r: r["name"])


def installed_rows(start: list[str], skip: set[str]) -> list[dict]:
    """설치본 메타데이터로 그래프를 걷는다. extra(선택 기능) 요구사항은 따라가지 않는다."""
    rows, seen = [], set()
    queue = deque((canonicalize_name(name), [], "") for name in start)
    while queue:
        name, via, marker = queue.popleft()
        if name in seen:
            continue
        seen.add(name)
        condition = f". 조건: `{marker}`" if marker else ""
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            rows.append(row(name, "-", "-", "", "이 환경에 설치되지 않음" + condition))
            continue
        for text in dist.requires or []:
            req = Requirement(text)
            if req.marker is None or "extra" not in str(req.marker):
                queue.append((canonicalize_name(req.name), via + [name], str(req.marker or "")))
        if name in skip:
            continue
        license_, repo = pypi_meta(name, dist.version)
        note = "경로: " + " → ".join(via + [name]) if len(via) > 1 else "직접 의존성"
        rows.append(row(name, dist.version, license_, repo, note + condition))
    return sorted(rows, key=lambda r: r["name"])


def desktop_rows() -> list[dict]:
    entries, current = [], None
    for line in (ROOT / "apps/desktop/pubspec.lock").read_text(encoding="utf-8").splitlines():
        if m := re.match(r"^  ([A-Za-z0-9_]+):\s*$", line):
            current = {"name": m.group(1)}
            entries.append(current)
        elif current is not None and (m := re.match(r'^    (dependency|source|version): "?([^"]+?)"?\s*$', line)):
            current[m.group(1)] = m.group(2)
    labels = {"direct main": "직접(런타임)", "direct dev": "직접(개발)", "transitive": "전이"}
    rows = []
    for entry in entries:
        note = labels.get(entry["dependency"], entry["dependency"])
        if entry["source"] == "sdk":
            license_, repo = FLUTTER_SDK
            note += ". Flutter SDK에 포함"
        else:
            license_, repo = pub_meta(entry["name"], entry["version"])
        rows.append(row(entry["name"], entry["version"], license_, repo, note))
    return rows


# --- 출력 ---


def _cell(value: str) -> str:
    return str(value).replace("|", "\\|")


def table(rows: list[dict]) -> str:
    lines = ["| 패키지 | 버전 | 라이선스 | 저장소 | 비고 |", "|---|---|---|---|---|"]
    for r in rows:
        cells = (r["name"], r["version"], r["license"], r["repo"], r["note"])
        lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    return "\n".join(lines)


def tally(rows: list[dict]) -> str:
    counts = Counter(r["license"] for r in rows)
    return " · ".join(f"{lic} {n}" for lic, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def build() -> str:
    web, api = web_rows(), api_rows()
    mcp = installed_rows(["maskingtape-mcp"], skip={"maskingtape-mcp", "maskingtape"})
    desktop, npm_dev = desktop_rows(), npm_dev_rows()
    py_dev = installed_rows(["pytest", "ruff", "httpx2"], skip=set())
    groups = [
        ("웹 데모 빌드 결과물", web), ("REST API 서버", api), ("MCP 서버", mcp),
        ("데스크톱 앱", desktop), ("개발 도구(npm)", npm_dev), ("개발 도구(Python)", py_dev),
    ]
    flagged = [
        {**r, "note": f"{group}. {r['note']}"}
        for group, rows in groups
        for r in rows
        if r["license"] != "-" and not is_allowed(r["license"])
    ]
    missing = [r["name"] for _, rows in groups for r in rows if r["license"] == "-"]
    return "\n\n".join([
        "> 이 구간은 `python scripts/sbom_transitive.py --write`가 만든다. 손으로 고치지 않는다.",
        "PyPI 코어 패키지(`maskingtape`)는 런타임 외부 의존성이 없어 표가 없다.",
        "### A-1. 웹 데모 빌드 결과물 (npm, 방문자 브라우저로 전송)",
        (
            "`apps/web/package-lock.json`에서 `dependencies`로부터 이어지는 패키지다. "
            "코드가 번들에 들어가는 것은 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에 고지한다."
        ),
        table(web),
        "### A-2. REST API 서버 (Python, 공개 데모 서버에 설치)",
        (
            "`uv.lock`(Vercel 배포가 쓰는 lock)에서 `maskingtape-api`로부터 이어지는 패키지다. "
            "조건이 붙은 패키지는 그 환경에서만 설치된다."
        ),
        table(api),
        "### A-3. MCP 서버 (Python, 소스로 배포, 사용자가 설치할 때 받음)",
        (
            f"표를 만든 환경({ENV})의 설치본 기준이다. "
            "조건이 붙은 패키지는 운영체제나 파이썬 버전에 따라 설치 여부가 달라진다."
        ),
        table(mcp),
        "### A-4. 데스크톱 앱 (Dart·Flutter, 소스로 배포, 빌드할 때 받음)",
        (
            "`apps/desktop/pubspec.lock` 전체다. 전이 의존성에는 `flutter_test`·`flutter_lints`가 끌어오는 "
            "개발용 패키지도 섞여 있다. 라이선스는 pub.dev가 각 패키지의 LICENSE에서 판별한 값이다."
        ),
        table(desktop),
        "### A-5. 개발 도구 (배포물에 포함되지 않음)",
        f"npm 개발 의존성 {len(npm_dev)}개: {tally(npm_dev)}",
        f"Python 개발 도구(pytest·ruff·httpx2와 그 전이, {ENV}) {len(py_dev)}개: {tally(py_dev)}",
        *([f"설치되지 않아 확인하지 못한 패키지: {', '.join(sorted(set(missing)))}"] if missing else []),
        "### A-6. 팀 허용 목록(MIT·Apache-2.0·BSD·ISC와 그 변형) 밖 라이선스",
        "각 항목의 판단 근거는 아래 부록 B에 있다.",
        table(flagged),
    ])


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="SBOM.md 전이 의존성 부록 생성")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="SBOM.md의 표시 구간을 갈아 끼운다")
    mode.add_argument("--check", action="store_true", help="SBOM.md가 최신인지만 확인한다")
    args = parser.parse_args()

    block = build()
    if not (args.write or args.check):
        print(block)
        return 0

    raw = SBOM.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    start, end = text.find(BEGIN), text.find(END)
    if start == -1 or end == -1:
        print(f"SBOM.md에 {BEGIN} / {END} 구간이 없습니다.", file=sys.stderr)
        return 2
    updated = text[: start + len(BEGIN)] + "\n" + block + "\n" + text[end:]
    if args.check:
        if updated != text:
            print("SBOM.md 전이 의존성 표가 최신이 아닙니다. --write로 갱신하세요.", file=sys.stderr)
            return 1
        print("SBOM.md 전이 의존성 표: 최신")
        return 0
    SBOM.write_bytes(updated.replace("\n", newline).encode("utf-8"))
    print("SBOM.md 전이 의존성 표를 갱신했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
