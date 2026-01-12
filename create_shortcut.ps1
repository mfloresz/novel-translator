# Script para crear un acceso directo a Novel Translator sin consola
# Uso: powershell -ExecutionPolicy Bypass -File create_shortcut.ps1

$ErrorActionPreference = "Stop"

# Obtener el directorio del script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($scriptDir)) {
    $scriptDir = Get-Location
}

# Rutas
$pythonwPath = Join-Path $scriptDir ".venv\Scripts\pythonw.exe"
$mainPyPath = Join-Path $scriptDir "main.pyw"
$shortcutPath = Join-Path $scriptDir "Novel Translator.lnk"
$iconPath = Join-Path $scriptDir "src\gui\icons\app.ico"

# Verificar archivos
if (-not (Test-Path $pythonwPath)) {
    Write-Error "No se encontró: $pythonwPath"
    exit 1
}

if (-not (Test-Path $mainPyPath)) {
    Write-Error "No se encontró: $mainPyPath"
    exit 1
}

# Crear objeto de acceso directo
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)

# Configurar acceso directo
$Shortcut.TargetPath = $pythonwPath
$Shortcut.Arguments = "`"$mainPyPath`""
$Shortcut.WorkingDirectory = $scriptDir

# Usar icono si existe, sino usar el default
if (Test-Path $iconPath) {
    $Shortcut.IconLocation = "$iconPath,0"
}

# Guardar acceso directo
$Shortcut.Save()

Write-Host "Acceso directo creado: $shortcutPath" -ForegroundColor Green
Write-Host ""
Write-Host "Para ejecutar sin consola, haz doble clic en el acceso directo."
Write-Host "O usa: run_nt.vbs (ejecuta con ventana oculta)"
