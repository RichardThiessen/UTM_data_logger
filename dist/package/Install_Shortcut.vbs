' UTM Data Logger - Desktop Shortcut Installer
' Creates a desktop shortcut with the application icon

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get paths
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strDesktop = objShell.SpecialFolders("Desktop")

strShortcutPath = strDesktop & "\UTM Data Logger.lnk"
strTargetPath = strScriptDir & "\UTM_Logger.bat"
strIconPath = strScriptDir & "\UTM_Logger.ico"

' Create shortcut
Set objShortcut = objShell.CreateShortcut(strShortcutPath)
objShortcut.TargetPath = strTargetPath
objShortcut.WorkingDirectory = strScriptDir
objShortcut.IconLocation = strIconPath
objShortcut.Description = "UTM Data Logger - Thwing Albert UTS Interface"
objShortcut.Save

MsgBox "Desktop shortcut created!", vbInformation, "UTM Data Logger"
