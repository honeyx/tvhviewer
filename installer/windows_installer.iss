; Inno Setup script for TVHviewer.
; Version is passed in from CI via: ISCC.exe /DAppVersion=1.2.3 windows_installer.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8F2B6E1A-3C4D-4E5F-9A1B-2C3D4E5F6A7B}}
AppName=TVHviewer
AppVersion={#AppVersion}
AppPublisher=honeyx
AppPublisherURL=https://github.com/honeyx/tvhviewer
DefaultDirName={autopf}\TVHviewer
DefaultGroupName=TVHviewer
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=tvhviewer-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\tvhviewer-windows.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\tvhviewer-windows\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\TVHviewer"; Filename: "{app}\tvhviewer-windows.exe"
Name: "{group}\Uninstall TVHviewer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\TVHviewer"; Filename: "{app}\tvhviewer-windows.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\tvhviewer-windows.exe"; Description: "Launch TVHviewer"; Flags: nowait postinstall skipifsilent
