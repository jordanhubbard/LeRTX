; LeRTX Windows installer.
;
; This installer copies the application source (the same files
; desktop/manage.py already knows how to operate on) into a per-user
; install directory, then runs bootstrap.ps1, which ensures a real Python
; 3.11 interpreter is present and delegates to the existing, tested
; `desktop/manage.py setup` / `install` flow for dependency installation
; and Start Menu shortcut creation. It does not vendor the multi-gigabyte
; NVIDIA SDK wheels into the installer itself; those are downloaded by
; `manage.py setup` on first install, same as the manual flow.
;
; Build with Inno Setup 6 (https://jrsoftware.org/isinfo.php):
;   ISCC.exe LeRTX.iss
; Produces dist\LeRTX-Setup-<version>.exe relative to the repository root.

#ifndef AppVersion
  #define AppVersion "0.2.0"
#endif

[Setup]
AppId={{FFB05A3D-C86C-404A-8C16-899C133C3634}
AppName=LeRTX
AppVersion={#AppVersion}
AppPublisher=LeRTX
DefaultDirName={localappdata}\Programs\LeRTX
DefaultGroupName=LeRTX
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\..\dist
OutputBaseFilename=LeRTX-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=LeRTX

[Files]
Source: "..\..\manage.py"; DestDir: "{app}\desktop"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}\desktop"; Flags: ignoreversion
Source: "..\..\source\*"; DestDir: "{app}\desktop\source"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,*.pyo"
Source: "..\..\locks\*"; DestDir: "{app}\desktop\locks"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\wheels\*"; DestDir: "{app}\desktop\wheels"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\..\docs\user\hardware.md"; DestDir: "{app}\docs\user"; Flags: ignoreversion
Source: "bootstrap.ps1"; DestDir: "{app}\desktop\packaging\windows"; Flags: ignoreversion

[Icons]
Name: "{group}\LeRTX"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: "manage.py run"; WorkingDir: "{app}\desktop"; IconFilename: "{app}\.venv\Scripts\pythonw.exe"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\desktop\packaging\windows\bootstrap.ps1"" -InstallDir ""{app}"""; StatusMsg: "Setting up LeRTX (downloads NVIDIA SDK components; this can take several minutes)..."; Flags: waituntilterminated

[UninstallDelete]
; Inno only removes files/directories it tracked in [Files] and empty
; directories; runtime-created content (the venv manage.py setup builds,
; __pycache__, logs, caches) is untracked and would otherwise block
; directory removal. Removing {app} wholesale guarantees a clean uninstall;
; user data (settings, saved poses, scenes) lives outside {app} and is
; untouched.
Type: filesandordirs; Name: "{app}"
