# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""표기 변형 평가 세트(#531)를 두 커밋의 core로 각각 재서 비교한다.

동작 원리:
1. 각 커밋의 `packages/core`를 `git archive`로 임시 폴더에 풀어낸다.
2. 커밋마다 **격리된 임시 가상환경**을 만들어 그 커밋의 `maskingtape`만 설치한다 — PYTHONPATH로
   경로만 바꾸는 방식은 시도해봤지만, 이 저장소의 editable install(PEP 660) 방식이 만든 임포트
   후크가 새 파일(`overlaps.py` 등)을 옛 커밋 환경에서도 찾아내 버려서(같은 프로세스의 sys.path
   조작으로는 못 막음) 신뢰할 수 없었다. 완전히 별도 프로세스·별도 설치라야 확실히 갈린다.
3. 각 가상환경의 파이썬으로 `evaluate_variants.py`를 실행해 태그별 결과를 JSON으로 받는다 —
   이 스크립트는 `maskingtape`와 표준 라이브러리만 써서, 가상환경에 `bench`를 설치할 필요가 없다.
4. 두 결과를 합쳐 "커밋별 재현율·오탐" 표를 만든다.

사용법:
    python -m bench.evaluators.compare_variants_across_commits \\
        bench/datasets/variants_v1.jsonl --before 1086044 --after HEAD
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EVALUATE_VARIANTS_SCRIPT = Path(__file__).resolve().with_name("evaluate_variants.py")


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False, **kwargs)
    if result.returncode != 0:
        raise RuntimeError(f"명령 실패: {cmd}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def _extract_core_at_commit(commit: str, dest: Path) -> Path:
    """commit 시점의 packages/core를 dest에 풀어내고 그 경로를 반환한다."""
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.Popen(
        ["git", "archive", commit, "--", "packages/core"], cwd=_REPO_ROOT, stdout=subprocess.PIPE
    )
    tar = subprocess.run(["tar", "-x", "-C", str(dest)], stdin=archive.stdout, check=False)
    archive.wait()
    if archive.returncode != 0 or tar.returncode != 0:
        raise RuntimeError(f"{commit} 커밋의 packages/core를 추출하지 못했다")
    return dest / "packages" / "core"


def _venv_python(venv_dir: Path) -> Path:
    candidate = venv_dir / "Scripts" / "python.exe"
    return candidate if candidate.exists() else venv_dir / "bin" / "python"


def _score_at_commit(commit: str, dataset: Path, workdir: Path) -> dict:
    core_src = _extract_core_at_commit(commit, workdir / "src")
    venv_dir = workdir / "venv"
    venv.create(venv_dir, with_pip=True)
    python = _venv_python(venv_dir)

    _run([str(python), "-m", "pip", "install", "-q", str(core_src)])

    result_json = workdir / "result.json"
    _run([str(python), str(_EVALUATE_VARIANTS_SCRIPT), str(dataset), "--json", str(result_json)])
    return json.loads(result_json.read_text(encoding="utf-8"))


def compare(dataset: Path, before: str, after: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="maskingtape-variant-compare-") as tmp:
        tmp_path = Path(tmp)
        before_result = _score_at_commit(before, dataset, tmp_path / "before")
        after_result = _score_at_commit(after, dataset, tmp_path / "after")
    return {"before": before_result, "after": after_result}


def format_comparison_table(result: dict, before_label: str, after_label: str) -> str:
    before_tags, after_tags = result["before"]["per_tag"], result["after"]["per_tag"]
    all_tags = sorted(set(before_tags) | set(after_tags))
    lines = [
        f"{'tag':<28} {before_label + ' recall':>16} {after_label + ' recall':>16}",
    ]
    for tag in all_tags:
        before_r = before_tags.get(tag, {}).get("recall", 0.0)
        after_r = after_tags.get(tag, {}).get("recall", 0.0)
        lines.append(f"{tag:<28} {before_r:>16.3f} {after_r:>16.3f}")
    lines.append("")
    lines.append(f"전체 오탐(fp): {before_label} {result['before']['total_fp']}건 → {after_label} {result['after']['total_fp']}건")
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="표기 변형 평가 세트를 두 커밋의 core로 비교")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--before", required=True, help="비교 기준 커밋(예: 9/28 오전 main)")
    parser.add_argument("--after", default="HEAD", help="비교 대상 커밋(기본 HEAD)")
    parser.add_argument("--json", type=Path, default=None, help="원시 결과를 JSON으로도 저장 (선택)")
    args = parser.parse_args()

    result = compare(args.dataset.resolve(), args.before, args.after)
    print(format_comparison_table(result, args.before, args.after))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
