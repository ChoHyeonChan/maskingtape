; SPDX-FileCopyrightText: 2026 The maskingtape Authors
; SPDX-License-Identifier: Apache-2.0
;
; 마스킹테이프 데스크톱 설치파일 정의 (#617). build.py가 묶음 폴더를 만든 뒤 이 파일을 컴파일한다:
;   ISCC /DAppVersion=0.1.0 /DBundleDir=<묶음 폴더> /DOutputDir=<출력 폴더> maskingtape.iss
; 이 파일은 UTF-8(BOM)로 저장한다 — 한글 문구 때문이다.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef BundleDir
  #define BundleDir "..\build\installer\bundle"
#endif
#ifndef OutputDir
  #define OutputDir "..\build\installer\dist"
#endif

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

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\마스킹테이프"; Filename: "{app}\maskingtape_desktop.exe"
Name: "{autodesktop}\마스킹테이프"; Filename: "{app}\maskingtape_desktop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\maskingtape_desktop.exe"; Description: "{cm:LaunchProgram,마스킹테이프}"; Flags: nowait postinstall skipifsilent
; Ollama와 모델(4.7GB)은 함께 넣지 않는다. 없어도 규칙 탐지는 그대로 동작한다.
Filename: "https://ollama.com/download"; Description: "Ollama 설치 페이지 열기 (「로컬 LLM 사용」에 필요 — 없어도 규칙 탐지는 동작합니다)"; Flags: shellexec nowait postinstall skipifsilent unchecked

[UninstallDelete]
; 동봉 Python이 실행 중에 만든 __pycache__까지 지운다.
Type: filesandordirs; Name: "{app}\python"

[Code]
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
