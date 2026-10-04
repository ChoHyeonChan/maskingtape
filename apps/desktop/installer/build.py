# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""Windows 설치파일(setup.exe)을 만든다 (#617).

동작 원리:
1. `flutter build windows --release` 결과물을 묶음 폴더(bundle)로 복사한다.
2. Python 임베디드 배포판을 받아(SHA-256 고정) `bundle/python/`에 풀고, core wheel을
   `python/Lib/site-packages/`에 푼다. pip은 넣지 않는다 — 앱은 `python.exe -X utf8 -m maskingtape.cli`로
   CLI를 부른다(`lib/services/cli_locator.dart`). 묶은 CLI가 실제로 도는지 합성 문장으로 확인한다.
3. 함께 실리는 제3자 구성요소의 고지문을 `bundle/licenses/*.txt`로 모으고(앱의 ⓘ 화면이 읽는다),
   파일별 SHA-256 목록(`BUNDLE_MANIFEST.txt`)을 쓴 뒤 Inno Setup으로 setup.exe를 만든다.

폴더 배치는 `lib/services/install_layout.dart`와 같아야 한다. 표준 라이브러리만 쓴다.

사용법 (저장소 루트, Windows):
    python apps/desktop/installer/build.py [--version 0.1.0] [--skip-flutter-build] [--no-installer]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DESKTOP = REPO / "apps" / "desktop"
RELEASE_DIR = DESKTOP / "build" / "windows" / "x64" / "runner" / "Release"
WORK = DESKTOP / "build" / "installer"  # apps/desktop/.gitignore가 /build/를 무시한다
BUNDLE = WORK / "bundle"
CACHE = WORK / "cache"
DIST = WORK / "dist"
ISS = Path(__file__).with_name("maskingtape.iss")

# 동봉물의 출처와 해시 — 바꾸면 팀장에게 알려 SBOM.md·THIRD_PARTY_NOTICES.md를 함께 고친다(§2-8).
PYTHON_VERSION = "3.13.2"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
PYTHON_EMBED_SHA256 = "1e803610b140cbf69dfa2ceaaeb39651bef75a239c381289e827c30862a27b93"
# Python 공식 문서의 「Licenses and Acknowledgements for Incorporated Software」 원문 —
# .pyd에 정적으로 들어간 expat·libmpdec 등의 고지가 여기 있다.
CPYTHON_LICENSE_URL = f"https://raw.githubusercontent.com/python/cpython/v{PYTHON_VERSION}/Doc/license.rst"
CPYTHON_LICENSE_SHA256 = "62f2c9c2c75d511170eb464ad5f83b78cc1f37eb2eb49c2846c9aa6c4557ee99"
# 임베디드 zip의 LICENSE.txt에는 OpenSSL 고지가 없어 따로 넣는다. 버전은 libssl-3.dll의 제품 버전.
OPENSSL_VERSION = "3.0.15"
OPENSSL_LICENSE_URL = f"https://raw.githubusercontent.com/openssl/openssl/openssl-{OPENSSL_VERSION}/LICENSE.txt"
OPENSSL_LICENSE_SHA256 = "7d5450cb2d142651b8afa315b5f238efc805dad827d91ba367d8516bc9d49e7a"
SQLITE_VERSION = "3.45.3"  # sqlite3.dll의 제품 버전

# 묶은 CLI 확인용 문장 — 합성 값이다(실제 개인정보 없음).
SMOKE_TEXT = "문의 전화는 010-1234-5678 입니다."


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, expected_sha256: str) -> Path:
    """받아서 해시를 확인한다. 이미 받은 파일이 맞으면 다시 받지 않는다."""
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / url.rsplit("/", 1)[1]
    if not (dest.exists() and sha256_of(dest) == expected_sha256):
        print(f"받는 중: {url}")
        urllib.request.urlretrieve(url, dest)  # noqa: S310 — 위에 고정한 https 주소만 받는다
    actual = sha256_of(dest)
    if actual != expected_sha256:
        raise SystemExit(f"해시가 다릅니다: {dest.name}\n  기대 {expected_sha256}\n  실제 {actual}")
    return dest


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print("실행:", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kwargs)


def default_version() -> str:
    for line in (DESKTOP / "pubspec.yaml").read_text(encoding="utf-8").splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip().split("+", 1)[0]
    raise SystemExit("pubspec.yaml에서 version을 찾지 못했습니다")


def build_flutter() -> None:
    flutter = shutil.which("flutter")
    if flutter is None:
        raise SystemExit("flutter를 PATH에서 찾지 못했습니다")
    run([flutter, "build", "windows", "--release"], cwd=DESKTOP)


def copy_app() -> None:
    if not (RELEASE_DIR / "maskingtape_desktop.exe").exists():
        raise SystemExit(f"릴리스 빌드가 없습니다: {RELEASE_DIR} (--skip-flutter-build를 빼고 다시 실행)")
    if BUNDLE.exists():
        shutil.rmtree(BUNDLE)
    shutil.copytree(RELEASE_DIR, BUNDLE)
    shutil.copy2(REPO / "LICENSE", BUNDLE / "LICENSE.txt")
    shutil.copy2(REPO / "THIRD_PARTY_NOTICES.md", BUNDLE / "THIRD_PARTY_NOTICES.md")


def add_python() -> None:
    python_dir = BUNDLE / "python"
    with zipfile.ZipFile(fetch(PYTHON_EMBED_URL, PYTHON_EMBED_SHA256)) as z:
        z.extractall(python_dir)
    # ._pth가 import 경로를 정한다 — site-packages를 더해야 풀어 넣은 maskingtape를 찾는다.
    pth = next(python_dir.glob("python*._pth"))
    lines = pth.read_text(encoding="utf-8").splitlines()
    lines.insert(lines.index(".") + 1, r"Lib\site-packages")
    pth.write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_core() -> str:
    """core wheel을 만들어 site-packages에 푼다. 넣은 버전을 돌려준다."""
    wheel_dir = CACHE / "wheel"
    if wheel_dir.exists():
        shutil.rmtree(wheel_dir)
    run([sys.executable, "-m", "pip", "wheel", str(REPO / "packages" / "core"), "--no-deps", "-w", str(wheel_dir)])
    wheel = next(wheel_dir.glob("maskingtape-*.whl"))
    site_packages = BUNDLE / "python" / "Lib" / "site-packages"
    with zipfile.ZipFile(wheel) as z:
        metadata = next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))
        requires = [
            line for line in z.read(metadata).decode("utf-8").splitlines()
            if line.startswith("Requires-Dist:") and "extra ==" not in line
        ]
        if requires:
            # 의존성 해석을 하지 않고 wheel만 풀기 때문에, core에 런타임 의존성이 생기면 여기서 멈춘다.
            raise SystemExit(f"core에 런타임 의존성이 생겼습니다 — 묶는 방법을 다시 정해야 합니다: {requires}")
        z.extractall(site_packages)
    return wheel.name.split("-")[1]


def smoke_test() -> None:
    """묶은 Python으로 CLI를 실제로 돌려 본다 — 앱이 부르는 것과 같은 인자다."""
    # -B: 확인 실행이 __pycache__를 남기면 그게 설치파일에 같이 묶인다.
    result = subprocess.run(
        [str(BUNDLE / "python" / "python.exe"), "-B", "-X", "utf8", "-m", "maskingtape.cli", "--scan"],
        input=SMOKE_TEXT.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"묶은 CLI가 실패했습니다:\n{result.stderr.decode('utf-8', 'replace')}")
    kinds = {d["kind"] for d in json.loads(result.stdout.decode("utf-8"))}
    if "phone" not in kinds:
        raise SystemExit(f"묶은 CLI가 합성 전화번호를 못 잡았습니다: {kinds}")
    print("묶은 CLI 확인: 통과")


def find_iscc() -> Path | None:
    candidates = [
        shutil.which("iscc"),
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    return next((Path(c) for c in candidates if c and Path(c).exists()), None)


def add_licenses(iscc: Path | None) -> None:
    """고지문을 licenses/이름.txt로 모은다 — 파일 이름이 앱 ⓘ 화면의 항목 이름이 된다."""
    out = BUNDLE / "licenses"
    out.mkdir()
    python_dir = BUNDLE / "python"
    shutil.copy2(python_dir / "LICENSE.txt", out / f"Python {PYTHON_VERSION} (CPython).txt")
    shutil.copy2(
        fetch(CPYTHON_LICENSE_URL, CPYTHON_LICENSE_SHA256),
        out / f"Python {PYTHON_VERSION} - incorporated software.txt",
    )
    openssl = fetch(OPENSSL_LICENSE_URL, OPENSSL_LICENSE_SHA256).read_text(encoding="utf-8")
    (out / f"OpenSSL {OPENSSL_VERSION}.txt").write_text(
        f"OpenSSL {OPENSSL_VERSION} (python\\libssl-3.dll, python\\libcrypto-3.dll)\n"
        "Copyright (c) The OpenSSL Project Authors. All Rights Reserved.\n"
        "https://www.openssl.org/\n\n" + openssl,
        encoding="utf-8",
    )
    (out / f"SQLite {SQLITE_VERSION}.txt").write_text(
        f"SQLite {SQLITE_VERSION} (python\\sqlite3.dll)\n"
        "https://www.sqlite.org/copyright.html\n\n"
        "SQLite is in the public domain. No license is required to use it.\n",
        encoding="utf-8",
    )
    (out / "Microsoft Visual C++ Runtime.txt").write_text(
        "Microsoft Visual C++ Runtime (python\\vcruntime140.dll, python\\vcruntime140_1.dll)\n"
        "Copyright (c) Microsoft Corporation.\n\n"
        "Microsoft Distributable Code, redistributed as part of the Python embeddable package.\n"
        "The redistribution conditions are in the section \"Additional Conditions for this\n"
        f"Windows binary build\" of the Python license (see \"Python {PYTHON_VERSION} (CPython)\").\n",
        encoding="utf-8",
    )
    if iscc is not None:
        # setup.exe 안에 Inno Setup의 설치 실행부가 들어간다 — 쓰는 컴파일러와 같은 판의 고지문을 넣는다.
        shutil.copy2(iscc.with_name("license.txt"), out / "Inno Setup (installer).txt")


def write_manifest(app_version: str, core_version: str) -> None:
    """제3자 파일별 SHA-256 — SBOM에 옮겨 적을 근거(우리 코드인 maskingtape 패키지는 뺀다)."""
    ours = BUNDLE / "python" / "Lib" / "site-packages"
    rows = [
        f"{sha256_of(p)}  {p.stat().st_size:>9}  {p.relative_to(BUNDLE).as_posix()}"
        for p in sorted(BUNDLE.rglob("*"))
        if p.is_file() and ours not in p.parents and (BUNDLE / "python" in p.parents or p.suffix == ".dll")
    ]
    header = [
        f"maskingtape desktop {app_version} (core {core_version}) - bundled third-party files",
        f"Python embeddable {PYTHON_VERSION} amd64  sha256={PYTHON_EMBED_SHA256}",
        f"  source: {PYTHON_EMBED_URL}",
        f"OpenSSL {OPENSSL_VERSION}, SQLite {SQLITE_VERSION} (inside the Python package)",
        "",
        "sha256  size  path",
    ]
    (BUNDLE / "BUNDLE_MANIFEST.txt").write_text("\n".join(header + rows) + "\n", encoding="utf-8")


def compile_installer(iscc: Path, version: str) -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    run([str(iscc), f"/DAppVersion={version}", f"/DBundleDir={BUNDLE}", f"/DOutputDir={DIST}", str(ISS)])
    return DIST / f"maskingtape-desktop-{version}-windows-x64-setup.exe"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="마스킹테이프 데스크톱 설치파일을 만든다 (#617)")
    parser.add_argument("--version", default=None, help="설치파일 버전 (기본: pubspec.yaml의 version)")
    parser.add_argument("--skip-flutter-build", action="store_true", help="이미 있는 릴리스 빌드를 그대로 쓴다")
    parser.add_argument("--no-installer", action="store_true", help="묶음 폴더까지만 만들고 Inno Setup은 돌리지 않는다")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Windows에서만 만들 수 있습니다")

    version = args.version or default_version()
    iscc = None if args.no_installer else find_iscc()
    if iscc is None and not args.no_installer:
        raise SystemExit("Inno Setup 6(ISCC.exe)을 찾지 못했습니다 — 설치하거나 --no-installer로 실행")

    if not args.skip_flutter_build:
        build_flutter()
    copy_app()
    add_python()
    core_version = add_core()
    smoke_test()
    add_licenses(iscc)
    write_manifest(version, core_version)
    print(f"묶음 폴더: {BUNDLE}")
    if iscc is not None:
        setup = compile_installer(iscc, version)
        print(f"설치파일: {setup} ({setup.stat().st_size / 1e6:.1f} MB, sha256 {sha256_of(setup)})")


if __name__ == "__main__":
    main()
