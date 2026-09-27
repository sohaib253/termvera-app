; Inno Setup script for the Termvera desktop installer. Built by
; build.ps1, which passes AppVersion and the source/output folders.
;
; Installs per user (no administrator rights needed) into
; %LOCALAPPDATA%\Programs\Termvera. User data (database, uploaded
; documents, logs) lives separately in %LOCALAPPDATA%\Termvera, so an
; upgrade or reinstall never touches it; uninstalling asks before deleting it.

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\build\desktop\dist\Termvera"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\build\desktop\installer"
#endif

[Setup]
AppId={{2F8A5C3D-91B4-4E6F-A7D2-5C0E8B1F3A64}
AppName=Termvera
AppVersion={#AppVersion}
AppPublisher=Termvera
AppPublisherURL=https://termvera.app
AppSupportURL=mailto:support@termvera.app
VersionInfoVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\Termvera
DefaultGroupName=Termvera
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=Termvera-Setup-{#AppVersion}
SetupIconFile=termvera.ico
UninstallDisplayIcon={app}\Termvera.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\Termvera"; Filename: "{app}\Termvera.exe"
Name: "{userdesktop}\Termvera"; Filename: "{app}\Termvera.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Termvera.exe"; Description: "Start Termvera now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop a running copy so its files can be removed.
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM Termvera.exe /T"; Flags: runhidden; RunOnceId: "StopApp"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\Termvera');
    // Suppressible: a silent uninstall keeps the data (the IDNO default).
    if DirExists(DataDir) and
       (SuppressibleMsgBox('Also delete your Termvera data (projects, contracts, uploaded documents)?' + #13#10 +
               'Choose No to keep it for a later reinstall.',
               mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES) then
      DelTree(DataDir, True, True, True);
  end;
end;
