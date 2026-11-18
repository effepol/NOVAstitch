; Script di Inno Setup 6 per NOVAstitch (Windows).
; Si compila DOPO PyInstaller: serve la cartella dist\NOVAstitch.
; Se cambi versione: aggiorna AppVersion qui, version_info.txt e info_app.py.

#define AppName "NOVAstitch"
#define AppVersion "0.1"
#define AppPublisher "Poletti Centro Cucito"
#define AppExe "NOVAstitch.exe"

[Setup]
; AppId: NON cambiarlo mai, e' lui che permette di aggiornare una versione gia' installata
AppId={{F898DFD8-DD8D-4A62-8D98-3C236CA3EBAA}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
; installa per l'utente corrente: niente richiesta di password amministratore
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=NOVAstitch-Setup-{#AppVersion}
SetupIconFile=risorse\icona.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"; LicenseFile: "LICENZA_it.txt"
Name: "en"; MessagesFile: "compiler:Default.isl"; LicenseFile: "LICENSE_en.txt"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\NOVAstitch\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENZA_it.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE_en.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "licenze\*"; DestDir: "{app}\licenze"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; la cache delle anteprime sta fuori dalla cartella del programma
Type: filesandordirs; Name: "{%USERPROFILE}\.novastitch"

[Registry]
; impostazioni salvate dal programma (lingua scelta): rimosse alla disinstallazione
Root: HKCU; Subkey: "Software\NOVAstitch"; Flags: uninsdeletekey
