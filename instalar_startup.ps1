# Inicia no logon e reinicia após falha, na sessão interativa do usuário.
$ErrorActionPreference = 'Stop'

$scriptPath = Join-Path $PSScriptRoot "global_shortcuts.py"
$pythonExe = "C:\Python313\pythonw.exe"
$startupFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$shortcutPath = "$startupFolder\Mini Teclado.lnk"

if (!(Test-Path -LiteralPath $pythonExe) -or !(Test-Path -LiteralPath $scriptPath)) {
    throw 'Python ou ativador não encontrado.'
}
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument "`"$scriptPath`"" -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'CH8 Macropad' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Atalhos do teclado CH8, com reinício após falha.' -Force | Out-Null

# Remove apenas o atalho antigo deste mesmo ativador, evitando dois mecanismos de startup.
if (Test-Path -LiteralPath $shortcutPath) {
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
    if ($shortcut.TargetPath -eq $pythonExe -and $shortcut.Arguments -eq "`"$scriptPath`"") {
        Remove-Item -LiteralPath $shortcutPath
    }
}

Write-Host 'Inicialização automática configurada: CH8 Macropad. Reinício após falha: 1 minuto.'
Write-Host "Alvo: $pythonExe $scriptPath"
