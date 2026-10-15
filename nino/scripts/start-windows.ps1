$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$logDir = Join-Path $projectRoot 'data\startup'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir 'startup.log'
function Write-StartupLog($text) { Add-Content -LiteralPath $logFile -Value "$(Get-Date -Format s) $text" }
$mutex = New-Object System.Threading.Mutex($false, 'Local\NinoWindowsStartup')
if (-not $mutex.WaitOne(0)) { $mutex.Dispose(); exit }
try {
    $env:OLLAMA_HOST = 'http://127.0.0.1:1337/v1'
    $env:OPENAI_COMPATIBLE = 'true'
    $electron = Join-Path $projectRoot 'node_modules\electron\dist\electron.exe'
    if (-not (Test-Path -LiteralPath $electron)) { throw 'Electron ausente; execute npm install.' }
    $node = (Get-Command node.exe -ErrorAction Stop).Source
    if (-not (Get-Process -Name 'Atomic-Chat' -ErrorAction SilentlyContinue)) {
        $atomicApp = Join-Path $env:LOCALAPPDATA 'Atomic Chat\Atomic-Chat.exe'
        if (-not (Test-Path -LiteralPath $atomicApp)) { throw 'Aplicativo Atomic Chat nao encontrado.' }
        Start-Process -FilePath $atomicApp -WindowStyle Hidden
        Write-StartupLog 'Atomic Chat iniciado.'
    }
    $atom = Get-Content -LiteralPath (Join-Path $projectRoot 'data\atom-config.json') -Raw | ConvertFrom-Json
    Start-Process -FilePath $electron -ArgumentList ('"' + $projectRoot + '"') -WorkingDirectory $projectRoot -WindowStyle Hidden
    Write-StartupLog 'Nino iniciado.'
    $deadline = (Get-Date).AddMinutes(2)
    while (-not (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object IPAddress -eq $atom.host)) {
        if ((Get-Date) -ge $deadline) { throw "Endereco LAN $($atom.host) indisponivel; confira atom-config.json." }
        Start-Sleep -Seconds 2
    }
    $listener = Get-NetTCPConnection -State Listen -LocalPort 3082 -ErrorAction SilentlyContinue
    if (-not $listener) {
        $running = Get-CimInstance Win32_Process -Filter "name='node.exe'" | Where-Object { $_.CommandLine -match 'src[\\/]server[\\/]atom\.js' }
        if (-not $running) {
            Start-Process -FilePath $node -ArgumentList 'src\server\atom.js' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'atom.log') -RedirectStandardError (Join-Path $logDir 'atom-error.log')
        }
        $deadline = (Get-Date).AddMinutes(1)
        do {
            Start-Sleep -Seconds 2
            $listener = Get-NetTCPConnection -State Listen -LocalPort 3082 -ErrorAction SilentlyContinue
        } while (-not $listener -and (Get-Date) -lt $deadline)
        if (-not $listener) { throw 'Servico Atom nao abriu a porta 3082; confira atom-error.log.' }
        Write-StartupLog 'Servico Atom pronto na porta 3082.'
    } else { Write-StartupLog 'Porta 3082 ja possui servico; nenhuma copia iniciada.' }
    $atomicOutput = & $node (Join-Path $PSScriptRoot 'ensure-atomic.js') 2>&1
    foreach ($line in $atomicOutput) { Write-StartupLog $line }
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao retomar API/modelo Atomic; confira startup.log.' }
    $models = $null
    $deadline = (Get-Date).AddMinutes(3)
    do {
        try {
            $models = Invoke-RestMethod 'http://127.0.0.1:1337/v1/models' -TimeoutSec 5
            if (@($models.data).Count -gt 0) { Write-StartupLog 'API Atomic Chat respondeu com modelo disponivel.'; break }
        } catch { }
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)
    if (-not $models -or @($models.data).Count -eq 0) { Write-StartupLog 'Atomic Chat ainda sem modelo disponivel; confira API e carregamento no aplicativo.' }
} catch { Write-StartupLog $_.Exception.Message; exit 1 }
finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
