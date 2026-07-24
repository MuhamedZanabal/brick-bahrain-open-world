param(
  [Parameter(Mandatory=$true)][string]$Apk,
  [Parameter(Mandatory=$true)][string]$Package,
  [Parameter(Mandatory=$true)][ValidateSet('gl_compatibility','mobile')][string]$Renderer,
  [Parameter(Mandatory=$true)][string]$OutputDir,
  [string]$QualityPreset='frozen_baseline'
)
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$adb=if($env:ADB){$env:ADB}else{'adb'}
& $adb get-state | Select-String 'device' | Out-Null
$apkHash=(Get-FileHash -Algorithm SHA256 $Apk).Hash.ToLowerInvariant()
$apkHash | Set-Content "$OutputDir/apk.sha256"
$props=[ordered]@{
 manufacturer=((& $adb shell getprop ro.product.manufacturer)-join '').Trim()
 model=((& $adb shell getprop ro.product.model)-join '').Trim()
 soc=((& $adb shell getprop ro.soc.model)-join '').Trim()
 android=((& $adb shell getprop ro.build.version.release)-join '').Trim()
 api=((& $adb shell getprop ro.build.version.sdk)-join '').Trim()
 abi=((& $adb shell getprop ro.product.cpu.abi)-join '').Trim()
 fingerprint=((& $adb shell getprop ro.build.fingerprint)-join '').Trim()
 resolution=((& $adb shell wm size)-join ' ').Trim()
 renderer=$Renderer
 quality=$QualityPreset
}
$props.GetEnumerator()|ForEach-Object{"$($_.Key)=$($_.Value)"}|Set-Content "$OutputDir/device.properties"
& $adb shell dumpsys SurfaceFlinger | Set-Content "$OutputDir/surfaceflinger.txt"
& $adb shell dumpsys thermalservice | Set-Content "$OutputDir/thermal-start.txt"
& $adb uninstall $Package *> "$OutputDir/uninstall-before.txt"
& $adb install -r -t $Apk *> "$OutputDir/install.txt"
& $adb logcat -c
$started=Get-Date
& $adb shell monkey -p $Package -c android.intent.category.LAUNCHER 1 *> "$OutputDir/launch.txt"
$pid='';1..60|ForEach-Object{if(-not $pid){$pid=((& $adb shell pidof $Package)-join '').Trim();if(-not $pid){Start-Sleep 1}}}
$pid|Set-Content "$OutputDir/pid.txt"
[Math]::Round(((Get-Date)-$started).TotalMilliseconds)|Set-Content "$OutputDir/cold-start-ms.txt"
1..300|ForEach-Object{& $adb logcat -d -v threadtime|Set-Content "$OutputDir/logcat-runtime.txt";if(Select-String -Quiet -Path "$OutputDir/logcat-runtime.txt" -Pattern 'G0_ANDROID_CAPTURE_FRAME frame=300'){break};Start-Sleep 2}
cmd /c "`"$adb`" exec-out screencap -p > `"$OutputDir\screenshot.png`""
& $adb shell dumpsys gfxinfo $Package reset *> "$OutputDir/gfxinfo-reset.txt"
Write-Host 'Perform the required traversal on the device for five minutes now.'
Start-Sleep 300
& $adb shell dumpsys gfxinfo $Package framestats *> "$OutputDir/gfxinfo-framestats.txt"
& $adb shell dumpsys meminfo $Package *> "$OutputDir/app-meminfo.txt"
& $adb shell dumpsys thermalservice *> "$OutputDir/thermal-end.txt"
& $adb shell input keyevent 3;Start-Sleep 4
& $adb shell monkey -p $Package -c android.intent.category.LAUNCHER 1 *> "$OutputDir/resume.txt";Start-Sleep 8
& $adb logcat -d -v threadtime | Set-Content "$OutputDir/logcat-final.txt"
Select-String -Path "$OutputDir/logcat-final.txt" -Pattern 'FATAL EXCEPTION|ANR in |am_anr|Fatal signal|SIGSEGV|DEBUG.*backtrace|tombstone'|Set-Content "$OutputDir/crash-scan.txt"
$result=[ordered]@{schema_version=1;test_status='INCOMPLETE';device=[ordered]@{manufacturer=$props.manufacturer;exact_model=$props.model;soc=$props.soc;gpu='See surfaceflinger.txt';ram_bytes=$null;android_version=$props.android;api_level=[int]$props.api;screen_resolution=$props.resolution;build_fingerprint=$props.fingerprint};renderer=$Renderer;quality_preset=$QualityPreset;apk_sha256=$apkHash;cold_start=[ordered]@{launch_exit_code=0;process_alive=[bool]$pid;milliseconds=[int](Get-Content "$OutputDir/cold-start-ms.txt")};scene_readiness=[ordered]@{ready_marker=$false;mission_marker=$false;seconds=$null};traversal=[ordered]@{duration_seconds=300;completed=$false;frame_metrics_file='gfxinfo-framestats.txt'};memory=[ordered]@{peak_pss_kb=$null;peak_rss_kb=$null};thermal=[ordered]@{start_state='thermal-start.txt';end_state='thermal-end.txt'};lifecycle=[ordered]@{pause_observed=$false;resume_observed=$false;process_alive_after_resume=$false};crash_scan=[ordered]@{fatal_count=0;anr_count=0;native_crash_count=0;log_file='logcat-final.txt'};notes=@('Human must confirm traversal completion, thermal acceptability, and device tier.')}
$result|ConvertTo-Json -Depth 8|Set-Content "$OutputDir/device_result.json"
Write-Host "Raw device evidence written to $OutputDir"
