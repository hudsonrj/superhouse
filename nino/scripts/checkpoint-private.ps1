[CmdletBinding(SupportsShouldProcess)]
param(
  [Parameter(Mandatory)][string]$Name,
  [switch]$Restore
)
$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Nome de checkpoint invalido.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
$checkpointRoot = Join-Path $projectRoot "data/checkpoints/$Name"
$encryptedFile = Join-Path $checkpointRoot 'private.dpapi'
$vaultRoot = if ($env:NINO_CONFIG_DIR) { $env:NINO_CONFIG_DIR } else { Join-Path ([Environment]::GetFolderPath('UserProfile')) '.config/nino' }
$files = [ordered]@{}
foreach ($relative in @('data/atom-config.json', 'data/ch8-config.json', 'data/ponte-config.json', 'data/settings.json', 'firmware/atom-voice/include/secrets.h')) {
  $files[$relative] = Join-Path $projectRoot $relative
}
$files['private/credenciais.json'] = Join-Path $vaultRoot 'credenciais.json'
foreach ($binary in @('firmware.bin', 'bootloader.bin', 'partitions.bin')) {
  $files["firmware/$binary"] = Join-Path $projectRoot "firmware/atom-voice/.pio/build/atom-voice/$binary"
}
Add-Type -AssemblyName System.Security
Add-Type -AssemblyName System.IO.Compression
$scope = [System.Security.Cryptography.DataProtectionScope]::CurrentUser
if ($Restore) {
  $bytes = [System.Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($encryptedFile), $null, $scope)
  $memory = [IO.MemoryStream]::new($bytes)
  $archive = [IO.Compression.ZipArchive]::new($memory, [IO.Compression.ZipArchiveMode]::Read)
  try {
    foreach ($entry in $archive.Entries) {
      if (-not $files.Contains($entry.FullName)) { throw 'Arquivo inesperado no checkpoint.' }
      $target = $files[$entry.FullName]
      if ($PSCmdlet.ShouldProcess($target, 'Restaurar arquivo do checkpoint')) {
        [IO.Directory]::CreateDirectory((Split-Path -Parent $target)) | Out-Null
        $inputStream = $entry.Open()
        $outputStream = [IO.File]::Create($target)
        try { $inputStream.CopyTo($outputStream) } finally { $inputStream.Dispose(); $outputStream.Dispose() }
      }
    }
  } finally { $archive.Dispose(); $memory.Dispose(); [Array]::Clear($bytes, 0, $bytes.Length) }
  if ($WhatIfPreference) { Write-Output 'Simulacao concluida. Nenhum arquivo foi restaurado.' }
  else { Write-Output 'Configuracao e artefatos restaurados. Nenhum firmware foi gravado no dispositivo.' }
  return
}
if (Test-Path -LiteralPath $encryptedFile) { throw 'Checkpoint ja existe; use outro nome para preservar o original.' }
[IO.Directory]::CreateDirectory($checkpointRoot) | Out-Null
$memory = [IO.MemoryStream]::new()
$archive = [IO.Compression.ZipArchive]::new($memory, [IO.Compression.ZipArchiveMode]::Create, $true)
$saved = @()
try {
  foreach ($item in $files.GetEnumerator()) {
    if (Test-Path -LiteralPath $item.Value -PathType Leaf) {
      $entry = $archive.CreateEntry($item.Key)
      $stream = $entry.Open()
      $bytes = [IO.File]::ReadAllBytes($item.Value)
      try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose(); [Array]::Clear($bytes, 0, $bytes.Length) }
      $saved += $item.Key
    }
  }
} finally { $archive.Dispose() }
$plain = $memory.ToArray()
try {
  $protected = [System.Security.Cryptography.ProtectedData]::Protect($plain, $null, $scope)
  [IO.File]::WriteAllBytes($encryptedFile, $protected)
  $verified = [System.Security.Cryptography.ProtectedData]::Unprotect($protected, $null, $scope)
  $hasher = [System.Security.Cryptography.SHA256]::Create()
  try {
    if ([Convert]::ToBase64String($hasher.ComputeHash($plain)) -cne [Convert]::ToBase64String($hasher.ComputeHash($verified))) { throw 'Falha ao validar o backup privado.' }
  } finally { $hasher.Dispose() }
  [Array]::Clear($verified, 0, $verified.Length)
} finally { [Array]::Clear($plain, 0, $plain.Length); $memory.Dispose() }
@{ name=$Name; created=(Get-Date -Format o); files=$saved; protection='Windows DPAPI CurrentUser'; codeTag=$Name } |
  ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $checkpointRoot 'manifest.json') -Encoding utf8
Write-Output "Backup privado validado: $Name ($($saved.Count) arquivos). Somente este usuario Windows pode descriptografar."
