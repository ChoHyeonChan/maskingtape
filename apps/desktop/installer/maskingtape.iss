; SPDX-FileCopyrightText: 2026 The maskingtape Authors
; SPDX-License-Identifier: Apache-2.0
;
; 마스킹테이프 데스크톱 설치파일 정의 (#617). build.py가 묶음 폴더를 만든 뒤 이 파일을 컴파일한다:
;   ISCC /DAppVersion=0.1.0 /DBundleDir=<묶음 폴더> /DOutputDir=<출력 폴더> maskingtape.iss
; 이 파일은 UTF-8(BOM)로 저장한다 — 한글 문구 때문이다.
;
; 로컬 LLM(선택): Ollama와 모델은 설치파일에 넣지 않고 **설치 시점에 내려받는다** — 설치파일 크기(+1GB)와
; 고지 대상(Ollama 안의 CUDA 런타임 등)을 늘리지 않기 위해서다. 사용자가 고르면 Ollama 공식 설치파일을
; 받아 조용히 설치하고, 이름 판정 모델(hf.co/…, 986MB)을 `ollama pull`로 받는다. 둘 다 없어도 앱은
; 규칙 탐지로 동작한다.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef BundleDir
  #define BundleDir "..\build\installer\bundle"
#endif
#ifndef OutputDir
  #define OutputDir "..\build\installer\dist"
#endif
; core name_llm.py의 DEFAULT_MODEL과 같은 값이어야 한다 — 앱이 이 이름으로 모델을 찾는다.
#define NameModel "hf.co/StayAlive1/maskingtape-name-1.5b-GGUF:Q4_K_M"
#define OllamaSetupUrl "https://ollama.com/download/OllamaSetup.exe"

[Setup]
; AppId는 설치된 프로그램을 식별한다 — 바꾸면 업그레이드가 아니라 별개 프로그램으로 깔린다.
AppId={{8F1C2B7E-6C1D-4B5A-9E55-6D2A7B0F4C31}
AppName=마스킹테이프
AppVersion={#AppVersion}
AppPublisher=The maskingtape Authors
AppPublisherURL=https://github.com/ChoHyeonChan/maskingtape
AppSupportURL=https://github.com/ChoHyeonChan/maskingtape/issues
; 관리자 권한 없이 사용자 폴더에 설치한다 — {autopf}가 %LOCALAPPDATA%\Programs로 풀린다.
PrivilegesRequired=lowest
DefaultDirName={autopf}\maskingtape
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile={#BundleDir}\LICENSE.txt
OutputDir={#OutputDir}
OutputBaseFilename=maskingtape-desktop-{#AppVersion}-windows-x64-setup
SetupIconFile=..\windows\runner\resources\app_icon.ico
UninstallDisplayIcon={app}\maskingtape_desktop.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
; Ollama가 이미 있으면 항목 자체를 숨긴다. 둘 다 인터넷이 필요하다.
Name: "ollama"; Description: "Ollama 설치 — 로컬 LLM 실행기 (공식 설치파일 약 1GB를 지금 내려받음)"; GroupDescription: "로컬 LLM — 「로컬 LLM 사용」에 필요합니다. 없어도 규칙 탐지는 동작합니다:"; Check: not OllamaInstalled
Name: "model"; Description: "이름 판정 모델 받기 — maskingtape-name-1.5b (986MB, 허깅페이스에서)"; GroupDescription: "로컬 LLM — 「로컬 LLM 사용」에 필요합니다. 없어도 규칙 탐지는 동작합니다:"

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\마스킹테이프"; Filename: "{app}\maskingtape_desktop.exe"
Name: "{autodesktop}\마스킹테이프"; Filename: "{app}\maskingtape_desktop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\maskingtape_desktop.exe"; Description: "{cm:LaunchProgram,마스킹테이프}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 동봉 Python이 실행 중에 만든 __pycache__까지 지운다. Ollama와 모델은 사용자 것이므로 지우지 않는다.
Type: filesandordirs; Name: "{app}\python"

[Code]
var
  DownloadPage: TDownloadWizardPage;
  OllamaDownloaded: Boolean;

function OllamaExe(): String;
begin
  Result := ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe');
end;

function OllamaInstalled(): Boolean;
begin
  Result := FileExists(OllamaExe());
end;

// Flutter 앱은 Visual C++ 런타임(msvcp140.dll 등)이 있어야 뜬다. 대부분의 PC에는 이미 있지만,
// 없으면 설치 후 실행이 실패하므로 미리 알려 준다(런타임 자체는 함께 넣지 않는다).
function InitializeSetup(): Boolean;
var
  Installed: Cardinal;
begin
  Result := True;
  if not (RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed)
          and (Installed = 1)) then
    MsgBox('이 PC에 Microsoft Visual C++ 재배포 가능 패키지(x64)가 없는 것 같습니다.' + #13#10 +
           '설치 후 프로그램이 실행되지 않으면 아래 주소에서 받아 설치해 주세요.' + #13#10#13#10 +
           'https://aka.ms/vs/17/release/vc_redist.x64.exe', mbInformation, MB_OK);
end;

procedure InitializeWizard();
begin
  DownloadPage := CreateDownloadPage('Ollama 내려받는 중', '공식 설치파일(OllamaSetup.exe)을 ollama.com에서 받습니다.', nil);
  OllamaDownloaded := False;
end;

// 작업 선택 뒤: Ollama를 설치하기로 했으면 설치 직전에 공식 설치파일을 받는다.
// 받기에 실패해도 앱 설치는 계속한다(규칙 탐지는 Ollama 없이 동작).
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpSelectTasks) and WizardIsTaskSelected('model') and not OllamaInstalled() and not WizardIsTaskSelected('ollama') then
    MsgBox('모델을 받으려면 Ollama가 필요합니다. 「Ollama 설치」도 함께 고르거나, 나중에 Ollama를 설치한 뒤 앱의 안내대로 모델을 받아 주세요.', mbInformation, MB_OK);
  if (CurPageID = wpReady) and WizardIsTaskSelected('ollama') and not OllamaInstalled() then begin
    DownloadPage.Clear;
    DownloadPage.Add('{#OllamaSetupUrl}', 'OllamaSetup.exe', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
        OllamaDownloaded := True;
      except
        if not DownloadPage.AbortedByUser then
          MsgBox('Ollama 설치파일을 받지 못했습니다: ' + GetExceptionMessage + #13#10 +
                 '앱은 그대로 설치합니다. Ollama는 나중에 https://ollama.com/download 에서 받아 주세요.', mbError, MB_OK);
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
end;

function OllamaServerUp(): Boolean;
var
  Http: Variant;
begin
  Result := False;
  try
    Http := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    Http.SetTimeouts(2000, 2000, 2000, 2000);
    Http.Open('GET', 'http://127.0.0.1:11434/api/tags', False);
    Http.Send('');
    Result := Http.Status = 200;
  except
    Result := False;
  end;
end;

// Ollama 서버가 안 떠 있으면 트레이 앱(서버 포함)을 띄우고 최대 60초 기다린다.
function EnsureOllamaServer(): Boolean;
var
  ResultCode, I: Integer;
  App: String;
begin
  Result := OllamaServerUp();
  if Result then exit;
  App := ExpandConstant('{localappdata}\Programs\Ollama\ollama app.exe');
  if FileExists(App) then
    ShellExec('', App, '', '', SW_HIDE, ewNoWait, ResultCode)
  else
    Exec(OllamaExe(), 'serve', '', SW_HIDE, ewNoWait, ResultCode);
  for I := 1 to 30 do begin
    Sleep(2000);
    if OllamaServerUp() then begin Result := True; exit; end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep <> ssPostInstall then exit;

  // 1) Ollama 설치 (공식 설치파일, 조용히)
  if OllamaDownloaded and not OllamaInstalled() then begin
    WizardForm.StatusLabel.Caption := 'Ollama를 설치하는 중…';
    if not Exec(ExpandConstant('{tmp}\OllamaSetup.exe'), '/VERYSILENT /NORESTART', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
      MsgBox('Ollama 설치가 끝나지 않았습니다(코드 ' + IntToStr(ResultCode) + '). 나중에 https://ollama.com/download 에서 다시 설치해 주세요.', mbError, MB_OK);
  end;

  // 2) 이름 판정 모델 받기 — 진행률이 보이도록 콘솔 창으로 ollama pull을 돌린다
  if WizardIsTaskSelected('model') then begin
    if not OllamaInstalled() then begin
      MsgBox('Ollama가 없어 모델을 받지 못했습니다. Ollama 설치 후 아래를 실행하면 됩니다:' + #13#10#13#10 +
             'ollama pull {#NameModel}', mbInformation, MB_OK);
      exit;
    end;
    WizardForm.StatusLabel.Caption := '이름 판정 모델을 받는 중 (986MB)…';
    if not EnsureOllamaServer() then begin
      MsgBox('Ollama 서버가 응답하지 않아 모델을 받지 못했습니다. Ollama를 실행한 뒤 아래를 실행하면 됩니다:' + #13#10#13#10 +
             'ollama pull {#NameModel}', mbError, MB_OK);
      exit;
    end;
    if not Exec(OllamaExe(), 'pull {#NameModel}', '', SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
      MsgBox('모델을 받지 못했습니다(코드 ' + IntToStr(ResultCode) + '). 인터넷 연결을 확인한 뒤 아래를 실행하면 됩니다:' + #13#10#13#10 +
             'ollama pull {#NameModel}', mbError, MB_OK);
  end;
end;
