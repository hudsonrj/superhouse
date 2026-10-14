# Coloca o mapeador do macropad para subir no logon, sem janela de console.

$scriptPath = Join-Path $PSScriptRoot "global_shortcuts.py"
$pythonExe = "C:\Python313\pythonw.exe"
$startupFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$shortcutPath = "$startupFolder\Mini Teclado.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortCut($shortcutPath)
$shortcut.TargetPath = $pythonExe
$shortcut.Arguments = "`"$scriptPath`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.WindowStyle = 7
$shortcut.Description = "Macropad ALLOET"
$shortcut.Save()

Write-Host "Atalho atualizado em: $shortcutPath"
Write-Host "Alvo: $pythonExe $scriptPath"
