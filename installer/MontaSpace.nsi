Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"

!define PRODUCT_NAME "MontaSpace"
!define PRODUCT_VERSION "0.8.3"
!define PRODUCT_PUBLISHER "BC Shin Studio"
!define PRODUCT_URL "https://www.bcshinstudio.com"
!define PRODUCT_EXE "MontaSpace.exe"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\MontaSpace"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\installer-output\MontaSpace_Setup_${PRODUCT_VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\MontaSpace"
RequestExecutionLevel user
SetCompressor /SOLID lzma

VIProductVersion "0.8.3.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "FileDescription" "MontaSpace Installer"
VIAddVersionKey "FileVersion" "0.8.3.0"
VIAddVersionKey "ProductVersion" "0.8.3"
VIAddVersionKey "LegalCopyright" "Copyright (C) 2026 BC Shin Studio. All rights reserved."

!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\MontaSpace.ico"
!define MUI_UNICON "..\assets\MontaSpace.ico"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${PRODUCT_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch MontaSpace"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Section "MontaSpace application (required)" SecApp
  SetShellVarContext current
  SectionIn RO
  SetOutPath "$INSTDIR"
  ; Include the full PyInstaller one-folder bundle, including _internal.
  File /r "..\dist\MontaSpace\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\MontaSpace"
  CreateShortCut "$SMPROGRAMS\MontaSpace\MontaSpace.lnk" "$INSTDIR\${PRODUCT_EXE}"
  CreateShortCut "$SMPROGRAMS\MontaSpace\Uninstall MontaSpace.lnk" "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "MontaSpace ${PRODUCT_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "URLInfoAbout" "${PRODUCT_URL}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\${PRODUCT_EXE}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section /o "Desktop shortcut" SecDesktop
  CreateShortCut "$DESKTOP\MontaSpace.lnk" "$INSTDIR\${PRODUCT_EXE}"
SectionEnd

LangString DESC_APP ${LANG_ENGLISH} "Install MontaSpace and add Start menu shortcuts."
LangString DESC_DESKTOP ${LANG_ENGLISH} "Create an optional desktop shortcut."
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecApp} $(DESC_APP)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(DESC_DESKTOP)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  SetShellVarContext current
  Delete "$DESKTOP\MontaSpace.lnk"
  Delete "$SMPROGRAMS\MontaSpace\MontaSpace.lnk"
  Delete "$SMPROGRAMS\MontaSpace\Uninstall MontaSpace.lnk"
  RMDir "$SMPROGRAMS\MontaSpace"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  ; Only application files inside the install folder are removed.
  ; User projects saved elsewhere are not touched.
  RMDir /r "$INSTDIR"
SectionEnd
