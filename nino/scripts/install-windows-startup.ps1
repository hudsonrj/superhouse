param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$name = 'Nino'
if ($Remove) {
    Unregister-ScheduledTask -TaskName 'Nino-Startup' -Confirm:$false -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $key -Name $name -ErrorAction SilentlyContinue
    Write-Output 'Inicializacao automatica do Nino removida.'
    exit
}
$script = Join-Path $PSScriptRoot 'start-windows.ps1'
if (-not (Test-Path -LiteralPath $script)) { throw 'Script de inicializacao ausente.' }
& node (Join-Path $PSScriptRoot 'ensure-atomic.js') --capture
if ($LASTEXITCODE -ne 0) { throw 'Falha ao salvar o modelo Atomic para retomada.' }
$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $script + '"'
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments -WorkingDirectory (Split-Path $PSScriptRoot -Parent)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
Register-ScheduledTask -TaskName 'Nino-Startup' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
$installed = Get-ScheduledTask -TaskName 'Nino-Startup'
if ($installed.Actions.Arguments -ne $arguments -or -not $installed.Triggers) { throw 'Falha ao verificar a tarefa de inicializacao.' }
Remove-ItemProperty -Path $key -Name $name -ErrorAction SilentlyContinue
Write-Output 'Nino e servico Atom configurados para iniciar no login deste usuario.'
