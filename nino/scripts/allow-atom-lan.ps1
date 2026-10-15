$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$atomConfig = Get-Content -LiteralPath 'data/atom-config.json' -Raw | ConvertFrom-Json
if (-not (Get-NetFirewallRule -DisplayName 'Nino Atom Voice LAN' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'Nino Atom Voice LAN' -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort 3082 -LocalAddress $atomConfig.host -RemoteAddress LocalSubnet `
        -InterfaceAlias 'Wi-Fi' -Profile Any -Program (Get-Command node).Source | Out-Null
}
