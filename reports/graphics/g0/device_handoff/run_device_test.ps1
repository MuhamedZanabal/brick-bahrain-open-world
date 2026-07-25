param([Parameter(Mandatory=$true)][string]$GlApk,[Parameter(Mandatory=$true)][string]$MobileApk,[string]$OutDir="device-results")
$ErrorActionPreference="Stop"
function Run-Variant($Key,$Package,$Apk) {
  $Out=Join-Path $OutDir $Key; New-Item -ItemType Directory -Force -Path $Out | Out-Null
  adb install -r -t $Apk | Tee-Object (Join-Path $Out "install.txt")
  adb shell pm path $Package | Tee-Object (Join-Path $Out "pm-path.txt")
  $Component=(adb shell cmd package resolve-activity --brief $Package | Select-Object -Last 1).Trim()
  $Component | Set-Content (Join-Path $Out "resolved-component.txt")
  adb logcat -c
  $Log=Start-Process adb -ArgumentList @("logcat","-v","threadtime") -RedirectStandardOutput (Join-Path $Out "logcat_full.txt") -PassThru
  adb shell am force-stop $Package; adb shell pm clear $Package
  adb shell am start -W -S -n $Component | Set-Content (Join-Path $Out "am-start.txt")
  Start-Sleep -Seconds 60
  adb shell pidof $Package | Set-Content (Join-Path $Out "pid.txt")
  adb shell dumpsys activity activities | Set-Content (Join-Path $Out "activity.txt")
  adb shell dumpsys window windows | Set-Content (Join-Path $Out "window.txt")
  adb exec-out screencap -p > (Join-Path $Out "screenshot.png")
  adb shell dumpsys gfxinfo $Package framestats | Set-Content (Join-Path $Out "gfxinfo.txt")
  adb shell dumpsys meminfo $Package | Set-Content (Join-Path $Out "meminfo.txt")
  adb shell dumpsys thermalservice | Set-Content (Join-Path $Out "thermal.txt")
  adb shell input keyevent 3; Start-Sleep -Seconds 4; adb shell am start -W -n $Component | Set-Content (Join-Path $Out "resume.txt")
  Stop-Process -Id $Log.Id -ErrorAction SilentlyContinue
}
Run-Variant "gl_compatibility" "com.brickbahrain.g0gl" $GlApk
Run-Variant "mobile_vulkan" "com.brickbahrain.g0mobile" $MobileApk
Write-Host "Template capture completed. tests_performed remains false until reviewed and signed."
