# Script de PowerShell para crear un acceso directo en el escritorio para Novel Translator

# Obtener la ruta del escritorio del usuario
$DesktopPath = [Environment]::GetFolderPath("Desktop")

# Definir la ruta de instalación
$InstallPath = "$env:USERPROFILE\novel-translator"

# Crear el acceso directo
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut("$DesktopPath\Novel Translator.lnk")
$Shortcut.TargetPath = "$InstallPath\run_nt.vbs"
$Shortcut.WorkingDirectory = "$InstallPath"
$Shortcut.Description = "Novel Translator"
$Shortcut.IconLocation = "$InstallPath\src\gui\icons\app.png"
$Shortcut.Save()

Write-Host "Acceso directo creado en el escritorio: $DesktopPath\Novel Translator.lnk"