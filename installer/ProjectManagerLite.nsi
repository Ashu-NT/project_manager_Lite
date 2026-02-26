; ------------------------------------------
; ProjectManagerLite NSIS Installer Script
; ------------------------------------------

!include "MUI2.nsh"
!include "LogicLib.nsh"

!define APP_NAME       "ProjectManagerLite"
!ifndef APP_VERSION
!define APP_VERSION    "2.1.0"
!endif
!define APP_PUBLISHER  "TECHBASE"
!define APP_EXE        "ProjectManagerLite.exe"
!ifndef APP_SOURCE_DIR
!define APP_SOURCE_DIR "..\dist\ProjectManagerLite"
!endif

; NOTE: NSIS does not provide a simple "if file exists" preprocessor directive that works across
; platforms. Make sure you've already built the project with PyInstaller and that
; the executable exists at
;   ${APP_SOURCE_DIR}\${APP_EXE}
;
; If makensis fails later while processing the File /r command, re-run PyInstaller first.

; Provide a friendly output name for the installer
OutFile "Setup_${APP_NAME}_${APP_VERSION}.exe"
Name "${APP_NAME} ${APP_VERSION}"

InstallDir "$PROGRAMFILES\${APP_NAME}"

; Store install dir in HKLM so updates find it machine-wide
InstallDirRegKey HKLM "Software\${APP_NAME}" "InstallDir"

RequestExecutionLevel admin

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  ; Detect existing install and show update/repair prompt.
  ReadRegStr $1 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion"
  StrCmp $1 "" check_running
    MessageBox MB_OKCANCEL|MB_ICONINFORMATION \
      "${APP_NAME} version $1 is already installed.$\r$\n$\r$\nSetup will install version ${APP_VERSION} over it (update/repair).$\r$\nContinue?" \
      IDCANCEL cancel

check_running:
  ; Optional basic running-app check (best-effort)
  FindWindow $0 "" "${APP_NAME}"
  StrCmp $0 0 done
    MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "${APP_NAME} is running. Please close it before installing the update." IDCANCEL cancel
    Goto done
  cancel:
    Abort
  done:
FunctionEnd

Function RefreshShellIcons
  ; Ask Explorer to refresh icon cache associations.
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
FunctionEnd

Section "MainSection" SEC01
  SetShellVarContext all
  SetOutPath "$INSTDIR"

  File /r "${APP_SOURCE_DIR}\*"

  WriteRegStr HKLM "Software\${APP_NAME}" "InstallDir" "$INSTDIR"

  ; Remove old shortcuts from both current-user and all-users scopes.
  SetShellVarContext current
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  SetShellVarContext all
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1

  WriteUninstaller "$INSTDIR\Uninstall.exe"
  Call RefreshShellIcons
SectionEnd

Section "Uninstall"
  SetShellVarContext all

  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APP_NAME}"

  Delete "$DESKTOP\${APP_NAME}.lnk"

  RMDir /r "$INSTDIR"

  DeleteRegKey HKLM "Software\${APP_NAME}"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd
