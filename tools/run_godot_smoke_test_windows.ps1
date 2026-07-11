$ErrorActionPreference = 'Stop'
$Godot = if ($env:GODOT_BIN) { $env:GODOT_BIN } else { 'godot' }
New-Item -ItemType Directory -Force -Path 'build/ci_logs' | Out-Null
& $Godot --headless --path . --editor --quit 2>&1 | Tee-Object -FilePath 'build/ci_logs/local-import-windows.log'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Godot --headless --path . --script res://tests/runtime_smoke_test_v14.gd 2>&1 | Tee-Object -FilePath 'build/ci_logs/local-runtime-windows.log'
exit $LASTEXITCODE
