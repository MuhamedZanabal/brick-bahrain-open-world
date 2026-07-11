param([string]$Output = 'build/brick_bahrain_v14-debug.apk')
$ErrorActionPreference = 'Stop'
$Godot = if ($env:GODOT_BIN) { $env:GODOT_BIN } else { 'godot' }
New-Item -ItemType Directory -Force -Path (Split-Path $Output), 'build/ci_logs' | Out-Null
& $Godot --headless --path . --editor --quit 2>&1 | Tee-Object -FilePath 'build/ci_logs/local-android-import-windows.log'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Godot --headless --path . --export-debug Android $Output 2>&1 | Tee-Object -FilePath 'build/ci_logs/local-android-export-windows.log'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not (Test-Path $Output) -or (Get-Item $Output).Length -le 0) { throw 'APK was not created' }
$hash = (Get-FileHash -Algorithm SHA256 $Output).Hash.ToLower()
"$hash  $(Split-Path $Output -Leaf)" | Set-Content -Encoding ascii "$Output.sha256"
