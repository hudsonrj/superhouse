$ErrorActionPreference = "SilentlyContinue"
$listen = Get-NetTCPConnection -LocalPort 8788 -State Listen
if ($listen) { exit 0 }
$busy = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*placa_gateway.py*" }
if ($busy) { exit 0 }
$cmd = "C:\Users\hudsons\placamarela\companion2\firmware-cyd\run_gateway.cmd"
Start-Process -FilePath $cmd -WorkingDirectory (Split-Path $cmd) -WindowStyle Minimized
exit 0
