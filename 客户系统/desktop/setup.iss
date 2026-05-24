; Estimate Studio 安装脚本
; 使用 Inno Setup 编译: https://jrsoftware.org/isinfo.php
; 编译前请先使用 PyInstaller 打包 desktop_app.py:
;   pip install pyinstaller
;   pyinstaller --onefile --windowed --name "EstimateStudio" --icon=app.ico desktop_app.py
;   pyinstaller --onefile --name "EstimateStudioConsole" desktop_app.py

#define MyAppName "Estimate Studio"
#define MyAppVersion "5.0.1"
#define MyAppPublisher "Estimate Studio"
#define MyAppURL "http://127.0.0.1:5005"
#define MyAppExeName "EstimateStudio.exe"

[Setup]
AppId={{B8F4A3D2-1C5E-4A7B-9D6F-8E2C1A3B5D7F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=.\installer
OutputBaseFilename=EstimateStudio_v{#MyAppVersion}_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableDirPage=no
DirLabel=选择系统安装路径
DisableFinishedPage=no
LicenseFile=license.txt

[Languages]
Name: "chinese"; MessagesFile: "compiler:Languages\Chinese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: checkedonce

[Files]
; 主程序
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\EstimateStudioConsole.exe"; DestDir: "{app}"; Flags: ignoreversion

; Web 端文件
Source: "..\web\*"; DestDir: "{app}\web"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\license_manager.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; 桌面端文件
Source: "..\desktop\*"; DestDir: "{app}\desktop"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "installer,__pycache__,.pyc,node_modules"

; Python 运行时（嵌入 Python）
Source: "runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{src}\runtime'))

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; 清理用户数据目录（可选，默认不删除用户数据）
; Filename: "{cmd}"; Parameters: "/c rmdir /s /q ""{localappdata}\EstimateStudio"""; Flags: runhidden

[Code]
var
  DataPage: TInputDirWizardPage;
  DataRoot: String;

procedure InitializeWizard;
begin
  DataPage := CreateInputDirPage(
    wpSelectDir,
    '选择文件存储路径',
    '请选择项目文件、上传文件和测算数据的存储位置。',
    '选择您希望存储所有项目数据的目录，系统将在此目录下按项目自动创建文件夹。'#13#10#13#10 +
    '建议：选择一个空闲空间较大的磁盘分区。',
    False,
    ''
  );
  DataPage.Add('');

  if GetPreviousData('DataDir', DataRoot) then
    DataPage.Values[0] := DataRoot
  else
    DataPage.Values[0] := ExpandConstant('{commonappdata}\EstimateStudio\Data');
end;

procedure RegisterPreviousData(PreviousDataKey: Integer);
begin
  SetPreviousData(PreviousDataKey, 'DataDir', DataPage.Values[0]);
end;

function NextButtonClick(PageId: Integer): Boolean;
begin
  Result := True;
  if PageId = DataPage.ID then
  begin
    if DataPage.Values[0] = '' then
    begin
      MsgBox('请选择文件存储路径。', mbError, MB_OK);
      Result := False;
    end
    else if not DirExists(DataPage.Values[0]) and not CreateDir(DataPage.Values[0]) then
    begin
      MsgBox('无法创建所选目录，请选择其他路径。', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: String;
  ConfigContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigPath := ExpandConstant('{app}\desktop\config.json');
    DataRoot := DataPage.Values[0];
    ConfigContent :=
      '{'#13#10 +
      '  "server_url": "http://127.0.0.1:5001",'#13#10 +
      '  "data_root": "' + DataRoot + '"'#13#10 +
      '}';
    SaveStringToFile(ConfigPath, ConfigContent, False);
  end;
end;

function GetUninstallString: String;
begin
  Result := ExpandConstant('{uninstallexe}');
end;
