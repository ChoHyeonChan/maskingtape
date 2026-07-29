# 릴리스 절차 (PyPI 배포)

`maskingtape`(코어 패키지)를 [PyPI](https://pypi.org/project/maskingtape/)에 배포하는 절차. **런타임 의존성이 없어** 배포가 단순하다.

> ⚠️ **실제 업로드(6번)는 팀장(PyPI 토큰 보유)만 수행한다.** PyPI 업로드는 되돌릴 수 없다(버전 삭제 불가, 첫 업로드로 이름이 선점된다). 5번 TestPyPI 리허설로 먼저 확인하는 것을 권장한다.

## 사전 준비 (최초 1회)

- [PyPI 계정](https://pypi.org/account/register/) + [API 토큰](https://pypi.org/manage/account/token/) 발급 (username은 `__token__`, password는 `pypi-...` 토큰)
- 빌드 도구: `pip install build twine`

## 절차

```bash
# 1. 버전 올리기 — packages/core/pyproject.toml 의 version (예: 0.1.0 → 0.1.1)
#    유의적 버전: 버그수정 z, 기능추가 y, 호환성 깨짐 x (x.y.z)

# 2. 검증 (통과 못 하면 배포 금지)
pip install -e "packages/core[dev]"
pytest packages/core
ruff check packages/core

# 3. 빌드 (sdist + wheel)
rm -rf dist
python -m build packages/core --outdir dist

# 4. 패키지 검사 (PyPI 렌더링·메타데이터 유효성)
twine check dist/*

# 5. (권장) TestPyPI 리허설 — 진짜 PyPI를 더럽히지 않고 확인
twine upload --repository testpypi dist/*
#   → 깨끗한 venv에서 설치 확인:
#     pip install --index-url https://test.pypi.org/simple/ maskingtape
#     maskingtape "주민번호 800101-1234560"

# 6. 실제 업로드 (팀장만)
twine upload dist/*

# 7. git 태그로 릴리스 지점 기록
git tag v0.1.0
git push origin v0.1.0
```

## 릴리스 전 체크리스트

- [ ] `pytest packages/core` 전부 통과
- [ ] `ruff check packages/core` 통과
- [ ] `pyproject.toml`의 version을 올렸다
- [ ] `twine check dist/*` PASSED
- [ ] 새 의존성을 추가했다면 [SBOM.md](SBOM.md) 갱신 + `pyproject.toml`의 `dependencies` 반영
- [ ] LICENSE가 배포물에 포함된다 (`packages/core/LICENSE` — wheel의 `dist-info/licenses/`에 담긴다)

## 참고

- **패키지 이름 `maskingtape`** 은 첫 업로드로 PyPI에 선점된다. 이름 변경은 불가하며, 바꾸려면 새 프로젝트로 다시 올려야 한다.
- `dist/` 는 빌드 산출물이므로 커밋하지 않는다(`.gitignore` 처리).
- 코어는 **런타임 의존성이 없다** — `pip install maskingtape` 만으로 끝난다. MCP 서버(`packages/mcp-server`)는 별도 패키지로, 배포한다면 같은 절차를 밟는다.
