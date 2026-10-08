# 2차 기능테스트 리허설 점검표

운영사무국 2026-09-29 답변 기준으로, 2차 기능테스트는 **우리 노트북**에서 진행하고
대상은 **프로젝트 전체**다. 기능명세서 제출 전날까지 이 점검표를 따라 처음부터 끝까지 한 번
돌린다. `main` 동결 의무는 없다(운영사무국 2026-10-07 정정). 검증은 제출한 기능명세서와
라이선스 검증 때 스캔한 소스를 기준으로 하므로, 기능명세서를 낸 커밋을 기록해 두고 그 뒤
`main`에 코드가 머지되면 명세서의 시험 항목을 다시 돌려 깨지지 않았는지 확인한다.

이 문서는 "깨끗한 설치에서 시연까지 막힘 없이 되는가"를 확인하기 위한 리허설 기록지다. 실제
개인정보는 쓰지 않고, 모든 입력은 합성 예시만 사용한다.

## 리허설 기록

| 항목 | 1차 기록 | 2차 기록 |
|---|---|---|
| 실행자 | 현찬 노트북 | 다른 팀원 노트북 |
| 실행 날짜 |  |  |
| OS / 사양 |  |  |
| 검증 커밋 |  |  |
| Python / Node / Flutter |  |  |
| Ollama / 모델 |  |  |
| 시작-종료 시각 |  |  |
| 총 소요 시간 |  |  |
| 막힌 지점 / 이슈 |  |  |

커밋 기록:

```powershell
git rev-parse --short HEAD
git status --short --branch
```

예상 결과:

- `git status`에 수정 파일이 없어야 한다.
- 기록한 커밋이 기능명세서 제출 기준 커밋과 같아야 한다.

## 공통 준비물

| 준비물 | 확인 명령 | 기준 | 실패 시 대처 |
|---|---|---|---|
| Git | `git --version` | 명령이 출력됨 | Git for Windows 설치 |
| Python | `python --version` | 3.10 이상 | python.org 또는 pyenv 설치 |
| Node.js | `node --version` | 22.13 이상의 22.x 또는 24 이상(웹 의존성 engines가 겹치는 범위, CI는 24) | Node LTS 설치 후 새 터미널 |
| npm | `npm --version` | 명령이 출력됨 | Node 재설치 |
| Flutter | `flutter --version` | 데스크톱 README 기준 3.44.6 stable | Flutter SDK 설치, `flutter doctor` 확인 |
| Ollama | `ollama --version` | 로컬 LLM 시연 노트북에만 필수 | Ollama 설치, 인터넷 없으면 사전 설치본 사용 |
| Claude Code | `claude --version` | MCP 시연 노트북에만 필수 | Claude Code 설치 및 로그인 |

오프라인 대비:

- PyPI 설치 검증은 인터넷이 필요하다. 인터넷이 없으면 전날 `pip download maskingtape -d wheelhouse`로
  wheelhouse를 만들어 두고 `pip install --no-index --find-links wheelhouse maskingtape`로 대체한다.
- Ollama 모델(986MB)은 전날 인터넷이 되는 곳에서 `ollama pull hf.co/StayAlive1/maskingtape-name-1.5b-GGUF:Q4_K_M`를 끝내고,
  `ollama list`에 모델이 보이는지 확인한다.
- Node 패키지는 인터넷이 필요하다. 전날 `apps/web`에서 `npm install`을 한 번 끝내 두거나,
  기능테스트 노트북에서 안정적인 네트워크를 확보한다.

## 0. 터미널 인코딩

목표: Windows PowerShell 5.1에서 한글이 깨지지 않게 한다. **PowerShell 창을 새로 열 때마다 맨 먼저**
실행한다. 설정은 그 창에서만 유지된다.

```powershell
[Console]::OutputEncoding = [Text.Encoding]::UTF8; $OutputEncoding = [Console]::OutputEncoding
$OutputEncoding.WebName
```

예상 결과:

- `utf-8`이 출력된다.

이 설정을 빼면:

- 파이프(`Get-Content … | maskingtape`)로 넣은 한글이 `???`로 바뀌어 CLI에 들어간다. 번호만 가려지고
  이름·주소는 그대로 남아서, 동작하는 것처럼 보이지만 탐지가 빠진다.
- `curl.exe` 응답의 한글이 깨진 글자로 보인다.
- `Invoke-RestMethod`는 이 설정과 상관없이 요청 본문의 한글을 `???`로 보낸다(서버가 이름을 못 잡고
  전화번호만 돌려준다). API 확인은 8·10절처럼 `curl.exe`와 UTF-8 JSON 파일로 한다.

## 1. 깨끗한 clone

목표: 검증기관 앞에서 "내 PC에 우연히 남은 파일" 없이도 설치가 되는지 확인한다.

```powershell
mkdir C:\maskingtape-rehearsal
cd C:\maskingtape-rehearsal
git clone https://github.com/ChoHyeonChan/maskingtape.git
cd maskingtape
git checkout main
git pull --ff-only origin main
git status --short --branch
```

예상 시간: 1-3분.

예상 결과:

- `## main...origin/main`처럼 main 기준 브랜치가 보인다.
- `git status --short`에 수정 파일이 없다.

실패 시:

- clone이 느리거나 실패하면 네트워크를 바꾼다.
- 이미 받은 폴더가 있으면 새 폴더명으로 다시 받는다. 리허설용 폴더에서는 기존 작업물을 재사용하지 않는다.
- 기능명세서를 낸 직후에는 `git rev-parse --short HEAD` 값을 이 문서의 기록표에 적는다.

## 2. 가상환경

목표: Python 패키지 설치와 CLI/API/MCP가 서로 충돌하지 않는 환경을 만든다.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python --version
python -m pip --version
```

예상 시간: 1-2분.

예상 결과:

- 프롬프트 앞에 `(.venv)`가 붙는다.
- Python 3.10 이상이 출력된다.

실패 시:

- `running scripts is disabled`가 나오면 PowerShell을 관리자 권한 없이 열고
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`를 적용한 뒤 새 터미널에서 다시 실행한다.
- 회사/학교 보안 정책 때문에 venv activation이 막히면 `.\.venv\Scripts\python.exe -m pip ...`처럼
  activation 없이 실행한다.

## 3. 설치 확인: 소스 설치

목표: 깨끗한 clone에서 소스 설치가 되는지 확인한다. 루트에는 배포용 `pyproject.toml`이 있으므로
`pip install .`이 아니라 개별 패키지 경로를 설치한다.

```powershell
python -m pip install -e "packages/core[dev]"
python -m pip install -e "packages/mcp-server"
python -m pip install -e "apps/api[dev]"
maskingtape --help
maskingtape-mcp --help
```

예상 시간: 2-5분.

예상 결과:

- `maskingtape --help`에 CLI 옵션이 출력된다.
- `maskingtape-mcp --help`에 MCP 서버 옵션이 출력된다.

실패 시:

- `No module named maskingtape`가 나오면 venv가 활성화됐는지 확인하고 위 설치 명령을 다시 실행한다.
- `httpx2` 관련 FastAPI/TestClient 오류가 나오면 `python -m pip install -e "apps/api[dev]"`가
  끝까지 성공했는지 확인한다.
- 루트에서 `pip install .`을 실행해 실패했다면 정상이다. 다시 개별 패키지 경로로 설치한다.

## 4. 설치 확인: PyPI 설치

목표: 검증기관이 공개 배포 패키지를 설치해도 코어 CLI가 동작하는지 확인한다. 소스 설치 venv와
섞지 않기 위해 별도 폴더에서 새 venv를 만든다.

```powershell
cd C:\maskingtape-rehearsal
mkdir pypi-check
cd pypi-check
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install maskingtape
python -c "import maskingtape; print(maskingtape.__version__)"
maskingtape "주민번호 800101-1234560 문의주세요"
```

예상 시간: 2-4분.

예상 결과:

- `python -c ...` 명령이 PyPI 패키지 버전을 출력한다.
- `주민번호 ************** 문의주세요`처럼 주민등록번호가 가려진다.

실패 시:

- 인터넷이 없으면 공통 준비물의 wheelhouse 대안으로 설치한다.
- PyPI 버전이 기능명세서 기준보다 낮으면 릴리스 이슈로 남기고, 기능테스트는 소스 설치 경로 기준으로 진행한다.

## 5. CLI: 규칙 전용

목표: 핵심 엔진이 LLM 없이 동작하고, 탐지 리포트와 마스킹 전략 3종이 보이는지 확인한다.

소스 설치 venv로 돌아온 뒤 실행한다.

```powershell
cd C:\maskingtape-rehearsal\maskingtape
.\.venv\Scripts\activate

maskingtape "고객 김민수님 주민번호 800101-1234560, 연락처 010-1234-5678"
maskingtape --strategy label "고객 김민수님 주민번호 800101-1234560, 연락처 010-1234-5678"
maskingtape --strategy pseudonym "고객 김민수님 주민번호 800101-1234560, 연락처 010-1234-5678"
maskingtape --scan "고객 김민수님 주민번호 800101-1234560, 연락처 010-1234-5678"
```

파이프 입력(0단계 인코딩 설정이 된 창에서):

```powershell
Set-Content -Path C:\maskingtape-rehearsal\sample-pipe.txt -Encoding UTF8 -Value "담당자 김민수, 연락처 010-1234-5678", "주민번호 800101-1234560"
Get-Content C:\maskingtape-rehearsal\sample-pipe.txt -Encoding UTF8 | maskingtape
```

예상 시간: 1분 미만.

예상 결과:

- 기본 전략은 `*`로 값을 가린다.
- `label`은 `[이름]`, `[주민등록번호]`, `[전화번호]`처럼 종류 라벨을 보여 준다.
- `pseudonym`은 원문과 다른 가짜 값을 만든다.
- `--scan`은 JSON 탐지 리포트를 출력한다.
- 파이프 입력은 두 줄이 그대로 나뉘어 `담당자 ***, 연락처 *************`와 `주민번호 **************`로 출력된다.
  `담당자`가 `???`로 보이거나 이름이 안 가려지면 0단계를 빠뜨린 것이다.
- 파이프 출력 첫 줄 맨 앞에는 보이지 않는 BOM 문자(U+FEFF)가 하나 붙는다. PowerShell이 UTF-8 입력 앞에
  붙여 보내는 것이고, 화면과 탐지 결과에는 영향이 없다(문장 맨 앞의 이름도 가려진다). 출력을 파일로
  저장하면 그 파일의 첫 글자로 남는다.

실패 시:

- 이름이 일부 안 잡혀도 구조화된 번호가 잡히면 규칙 전용 한계일 수 있다. 다음 `--llm` 단계에서 비교한다.
- 주민등록번호가 안 잡히면 합성 번호가 체크섬을 통과하는 예시인지 확인한다. 위 예시는 통과해야 한다.

## 6. CLI: 로컬 LLM(`--llm`)

목표: 2차 기능테스트에서 로컬 LLM 기능을 우리 노트북에서 보여 줄 수 있는지 확인한다.

사전 준비:

```powershell
ollama serve
```

다른 터미널에서:

```powershell
ollama pull hf.co/StayAlive1/maskingtape-name-1.5b-GGUF:Q4_K_M
ollama list
```

예열:

```powershell
ollama run hf.co/StayAlive1/maskingtape-name-1.5b-GGUF:Q4_K_M "이름 판단 테스트"
```

기능 확인:

```powershell
maskingtape --llm --strategy label "작성자 정보 참고: 최지훈 담당자(010-1234-5678)"
maskingtape --llm --scan "회의 참석자: 박서준, 김서연. 연락처 010-1234-5678"
```

예상 시간:

- 모델이 이미 있으면 예열 10초-2분.
- 처음 `ollama pull`이면 네트워크와 PC 성능에 따라 10분 이상.

예상 결과:

- `최지훈`, `박서준`, `김서연` 같은 이름이 `[이름]` 또는 `kind: "name"`으로 잡힌다.
- 전화번호도 함께 가려진다.
- 원문은 이 PC의 Ollama로만 간다.

실패 시:

- `Ollama 미실행` 또는 연결 실패: `ollama serve`를 먼저 실행한다.
- 모델 없음: `ollama pull hf.co/StayAlive1/maskingtape-name-1.5b-GGUF:Q4_K_M`.
- 첫 호출이 느리면 정상이다. 시연 전 예열 명령을 한 번 실행한다.
- 인터넷이 없으면 전날 모델을 받아 둔 노트북을 사용한다. 기능테스트 현장에서 모델 다운로드부터 하지 않는다.
- 메모리 부족이면 브라우저/IDE를 닫고 다시 시도한다. 그래도 안 되면 규칙 전용과 한계 설명으로 대체하고 이슈로 남긴다.

## 7. MCP: Claude Code

목표: AI 에이전트가 원문 파일을 직접 보내기 전에 MCP 도구로 비식별화할 수 있음을 보여 준다.

등록:

```powershell
cd C:\maskingtape-rehearsal\maskingtape
.\.venv\Scripts\activate
claude mcp add maskingtape -- maskingtape-mcp
claude mcp add maskingtape-llm -- maskingtape-mcp --llm
claude mcp list
```

파일 도구용 샘플:

```powershell
mkdir C:\maskingtape-rehearsal\mcp-samples
Set-Content -Path C:\maskingtape-rehearsal\mcp-samples\sample.txt -Encoding UTF8 -Value "담당자 김민수, 연락처 010-1234-5678"
claude mcp add maskingtape-files -e MASKINGTAPE_MCP_ROOT=C:\maskingtape-rehearsal\mcp-samples -- maskingtape-mcp
```

Claude Code에서 확인할 프롬프트:

```text
maskingtape MCP의 scan_text로 "담당자 김민수, 연락처 010-1234-5678"을 검사하고,
anonymize_text로 label 전략 비식별화를 해줘.
```

파일 도구 확인 프롬프트:

```text
maskingtape-files MCP의 anonymize_file로 C:\maskingtape-rehearsal\mcp-samples\sample.txt를 label 전략으로 비식별화해줘.
```

예상 시간: 5-10분.

예상 결과:

- `scan_text`는 종류·위치·확신도만 반환하고 원문값은 싣지 않는다.
- `anonymize_text`는 `[이름]`, `[전화번호]`가 들어간 텍스트를 반환한다.
- `anonymize_file`은 같은 폴더에 `_masked` 사본을 만든다.
- `maskingtape-llm`은 Ollama 준비가 된 노트북에서만 성공한다.

실패 시:

- Claude Code가 `maskingtape-mcp`를 못 찾으면 venv Scripts 경로가 PATH에 있는지 확인한다.
- 파일 처리가 거부되면 `MASKINGTAPE_MCP_ROOT`가 샘플 폴더를 가리키는지 확인한다.
- `--llm` 서버가 실패하면 CLI LLM 단계와 같은 방식으로 Ollama 상태를 먼저 점검한다.

## 8. API + 웹 로컬 실행

목표: REST API와 웹 플레이그라운드가 같은 로컬 PC에서 함께 동작하는지 확인한다.

터미널 1: API

```powershell
cd C:\maskingtape-rehearsal\maskingtape
.\.venv\Scripts\activate
$env:MASKINGTAPE_API_ENV="development"
$env:MASKINGTAPE_API_CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
python -m uvicorn maskingtape_api.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

API 확인(새 PowerShell 창에서 0단계 인코딩 설정을 먼저 실행한다):

```powershell
cd C:\maskingtape-rehearsal
Set-Content -Path body-scan.json -Encoding UTF8 -Value '{"text":"담당자 김민수, 연락처 010-1234-5678"}'
Set-Content -Path body-label.json -Encoding UTF8 -Value '{"text":"담당자 김민수, 연락처 010-1234-5678","strategy":"label"}'
curl.exe -s http://127.0.0.1:8000/health
curl.exe -s -X POST http://127.0.0.1:8000/scan -H "Content-Type: application/json" --data-binary "@body-scan.json"
curl.exe -s -X POST http://127.0.0.1:8000/anonymize -H "Content-Type: application/json" --data-binary "@body-label.json"
```

`Invoke-RestMethod`는 쓰지 않는다. 요청 본문의 한글이 `???`로 바뀌어 서버로 가서 이름이 탐지되지 않는다.

터미널 2: 웹

```powershell
cd C:\maskingtape-rehearsal\maskingtape\apps\web
npm install
npm run dev
```

브라우저:

```text
http://localhost:5173
```

예상 시간:

- API 실행 1분.
- 첫 `npm install` 3-10분.
- 이후 웹 실행 1분.

예상 결과:

- `/health`는 `{"status":"ok","hybrid_available":false}`(로컬에 `OPENAI_API_KEY`가 없을 때. 키가 있으면 `true`).
- `/scan` 응답의 `detections`에는 `text` 원문값이 없고 `kind`, `start`, `end`가 있다. `name`과 `phone` 2건이 나온다.
- `/anonymize` 응답의 `text`는 `담당자 [이름], 연락처 [전화번호]`다.
- 웹에서 합성 문장을 넣으면 하이라이트와 마스킹 결과가 표시된다.
- 웹 상단에 데모/미저장 안내가 보인다.

실패 시:

- `/scan`에서 `phone` 1건만 나오면 본문 한글이 깨져서 간 것이다. 본문을 `Set-Content -Encoding UTF8`로 만든
  파일로 보냈는지(`--data-binary "@파일"`) 확인한다.
- 응답의 한글이 깨져 보이면 그 창에서 0단계를 빠뜨린 것이다.
- 웹에서 API 오류가 나면 API 터미널이 켜져 있는지, 포트가 8000인지 확인한다.
- 8000 포트가 이미 사용 중이면 API를 8001로 띄우고 웹 터미널에서
  `$env:VITE_API_TARGET="http://127.0.0.1:8001"`을 설정한다.
- CORS 오류가 나면 `MASKINGTAPE_API_CORS_ORIGINS`에 웹 주소가 들어 있는지 확인한다.
- `npm install`이 실패하면 Node 버전과 네트워크를 확인한다.

## 9. 데스크톱(exe, 준형)

목표: Windows 배포용 exe 또는 Flutter 실행본에서 파일 일괄 처리와 텍스트 입력 모드가 동작하는지 확인한다.

선행조건:

- Windows 개발자 모드 켬.
- 로컬 CLI가 PATH에 있거나, API 서버가 `127.0.0.1:8000`에서 실행 중이어야 한다.
- 이름 정밀 탐지를 보여 줄 경우 Ollama와 `hf.co/StayAlive1/maskingtape-name-1.5b-GGUF:Q4_K_M`가 준비되어 있어야 한다.

개발 실행:

```powershell
cd C:\maskingtape-rehearsal\maskingtape\apps\desktop
flutter pub get
flutter run -d windows
```

릴리스 빌드:

```powershell
flutter build windows
```

exe 위치:

```text
apps\desktop\build\windows\x64\runner\Release\
```

확인 시나리오:

1. 텍스트 입력 모드에서 `담당자 김민수, 연락처 010-1234-5678` 입력.
2. 전략을 `mask`, `label`, `pseudonym`으로 바꿔 결과 비교.
3. 「로컬 LLM 사용」 토글을 켜고 LLM 상태 칩이 `LLM 준비됨` 또는 `LLM 로드됨`인지 확인.
4. 샘플 `.txt` 파일을 드롭하고 `_masked` 파일이 생기는지 확인.
5. CLI를 PATH에서 빼거나 새 터미널에서 API만 켠 상태로 REST 폴백 안내가 맞는지 확인.

예상 시간:

- 첫 `flutter pub get` 3-10분.
- `flutter run` 1-3분.
- `flutter build windows` 5-15분.

예상 결과:

- 앱이 Windows에서 열린다.
- CLI가 있으면 로컬 CLI 우선으로 처리된다.
- CLI가 없고 API가 떠 있으면 REST 폴백으로 규칙 기반 처리된다.
- 이름 정밀 탐지는 CLI 경로에서만 허용된다.

실패 시:

- symlink 권한 오류: Windows 개발자 모드를 켠다.
- `flutter test`/실행이 한글 사용자명 임시 폴더에서 멈추면 ASCII 임시 폴더를 지정한다.
  ```powershell
  mkdir C:\tmp
  $env:TEMP="C:\tmp"
  $env:TMP="C:\tmp"
  ```
- `LNK1104`로 exe를 열 수 없으면 실행 중인 앱 창을 닫고 다시 빌드한다.
- 모든 파일이 백엔드 연결 실패이면 CLI 설치 또는 API 실행 상태를 확인한다.

## 10. 웹 데모 URL

목표: 공개 URL에서 규칙 기반 웹 데모가 실제로 동작하고, 기능명세서의 웹 데모 항목과 맞는지 확인한다.

URL:

```text
https://maskingtape-lilac.vercel.app
```

브라우저 확인:

1. 페이지가 HTTPS로 열린다.
2. 데모/미저장 안내 배너가 보인다.
3. 합성 예시 버튼 또는 직접 입력으로 탐지 실행.
4. 결과 하이라이트와 마스킹 결과가 표시된다.
5. 실제 개인정보 입력 금지 문구가 보인다.

API 직접 확인(0단계 인코딩 설정이 된 창에서, 8절에서 만든 본문 파일을 그대로 쓴다):

```powershell
cd C:\maskingtape-rehearsal
curl.exe -s https://maskingtape-lilac.vercel.app/api/health
curl.exe -s -X POST https://maskingtape-lilac.vercel.app/api/scan -H "Content-Type: application/json" --data-binary "@body-scan.json"
```

예상 시간: 3-5분.

예상 결과:

- `/api/health`가 정상 응답한다.
- `/api/scan`은 탐지 metadata를 돌려주며 `detections[].text` 원문값을 담지 않는다. `name`과 `phone` 2건이 나온다.
- 웹 데모는 공개 URL이므로 실제 개인정보를 넣지 않는다.

실패 시:

- 배포가 오래된 화면을 보여 주면 강력 새로고침 또는 시크릿 창에서 확인한다.
- API가 실패하면 로컬 API+웹 시연으로 대체하고 배포 이슈로 남긴다.
- 인터넷이 없으면 공개 URL 시연은 불가능하다. 기능테스트 노트북의 핫스팟/유선망 대안을 준비한다.

## 11. 기능명세서 대조표

기능명세서에 들어갈 항목은 아래 표와 맞춘다. "가능"이라고 쓸 항목은 위 단계에서 직접 확인한
것만 넣고, 표면별 차이는 숨기지 않는다.

| 기능명세서 항목 | 검증 단계 | 표기 가이드 |
|---|---|---|
| Python 라이브러리/CLI 규칙 기반 비식별화 | 3, 5 | `pip install maskingtape` 및 소스 설치 모두 가능 |
| CLI 표준입력(파이프) 입력 | 0, 5 | 테스트 환경에 PowerShell UTF-8 설정을 적고, 그 설정 뒤에 시연 |
| CLI 로컬 LLM 이름 정밀 탐지 | 6 | 우리 노트북의 Ollama(`hf.co/StayAlive1/maskingtape-name-1.5b-GGUF:Q4_K_M`)에서 시연, 외부 상용 API 아님 |
| 마스킹 전략 3종 | 5, 8, 9 | `mask`, `label`, `pseudonym` |
| MCP 서버 | 7 | Claude Code에서 `scan_text`, `anonymize_text`, `anonymize_file` 확인 |
| REST API | 8 | `POST /scan`, `POST /anonymize`, 웹·데스크톱 공용 계약 |
| 웹 로컬 실행 | 8 | API와 웹 dev server를 함께 실행 |
| 웹 공개 데모 | 10 | 공개 URL은 데모용, 실제 개인정보 입력 금지 |
| 데스크톱 앱 | 9 | Windows 전용, 로컬 CLI 우선 + REST 폴백 |
| 입력/출력 개인정보 처리 | 5-10 | 로컬 CLI/MCP/데스크톱 CLI 경로는 PC 안 처리, 웹 데모는 서버 전송·미저장 |
| 알려진 한계 | 6, 9, 10 | 규칙 전용 이름 한계, 웹 데모는 실제 개인정보 입력 금지, 데스크톱 LLM은 CLI 경로 전용 |

## 12. 막힌 곳을 이슈로 남기는 규칙

리허설 중 10분 이상 막히면 그 자리에서 해결하더라도 이슈로 남긴다.

이슈 제목 형식:

```text
[rehearsal] <표면>: <막힌 증상>
```

이슈 본문에 넣을 것:

- 실행자 / 날짜 / 노트북 OS
- 커밋 SHA
- 실행한 명령
- 기대 결과와 실제 결과
- 임시 우회 방법
- 기능명세서에 영향이 있는지

## 13. 최종 통과 기준

- 현찬 노트북에서 1회, 다른 팀원 노트북에서 1회 돌렸다.
- 최소 1회는 이 문서 순서대로 처음부터 끝까지 막힘 없이 완료했다.
- 완료 기록에 날짜와 커밋 SHA가 있다.
- 기능명세서의 기능 목록이 이 문서의 대조표와 맞는다.
- 막힌 곳은 이슈로 남겼고, 기능명세서를 낸 커밋을 기록했다.
